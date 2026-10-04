"""Orbit / zoom / pan camera for the 3-D scene views.

Pure Python: no Kivy and no numpy, so it is unit-tested headless (tier A) and
its maths is independent of the GL stack.  The output, ``CameraBasis``, is
exactly what the ray-marching fragment shader consumes: an eye position, an
orthonormal right / up / forward frame, the vertical field of view and the
aspect ratio (``as_uniforms()``; see docs/dev/gl-spike.md).

Conventions
-----------
* World "up" is +z by default: the quantisation axis of atomic orbitals, so
  p_z lobes stand vertically.
* The camera orbits ``target`` on a sphere of radius ``distance``:
  ``azimuth`` is measured in the x-y plane from +x towards +y, ``elevation``
  from the x-y plane towards +z.  Elevation stops short of the poles, where
  the frame would be undefined.
* ``right x up = -forward``, so (right, up, -forward) is right-handed, as in
  the usual OpenGL camera looking down its -z axis.
* A ray for normalised device coordinates (ndc_x, ndc_y) in [-1, 1]^2 is
  ``forward + ndc_x * aspect * tan(fov/2) * right + ndc_y * tan(fov/2) * up``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

Vec3 = tuple[float, float, float]


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def normalize(a: Vec3) -> Vec3:
    length = norm(a)
    if length == 0.0 or not math.isfinite(length):
        raise ValueError(f"cannot normalise {a}")
    return _scale(a, 1.0 / length)


def _vec(value) -> Vec3:
    x, y, z = (float(c) for c in value)
    return (x, y, z)


@dataclass(frozen=True)
class CameraBasis:
    """A pinhole camera frame, ready for a fragment shader."""

    position: Vec3
    right: Vec3
    up: Vec3
    forward: Vec3
    fov_y: float  # vertical field of view, radians
    aspect: float  # width / height

    @property
    def tan_half_fov(self) -> float:
        return math.tan(0.5 * self.fov_y)

    def ray(self, ndc_x: float, ndc_y: float) -> Vec3:
        """Unit view-ray direction through a point in normalised device coords."""
        t = self.tan_half_fov
        d = _add(self.forward, _add(_scale(self.right, ndc_x * self.aspect * t),
                                    _scale(self.up, ndc_y * t)))
        return normalize(d)

    def as_uniforms(self) -> dict[str, tuple[float, ...] | float]:
        """Shader uniforms -- all Python floats.

        Kivy picks the GL uniform type from the Python type, so an int here
        would be a GL_INVALID_OPERATION on a float uniform (gl-spike.md, #2).
        """
        return {
            "u_cam_pos": tuple(float(c) for c in self.position),
            "u_cam_right": tuple(float(c) for c in self.right),
            "u_cam_up": tuple(float(c) for c in self.up),
            "u_cam_fwd": tuple(float(c) for c in self.forward),
            "u_tan_half_fov": float(self.tan_half_fov),
            "u_aspect": float(self.aspect),
        }


class OrbitCamera:
    """Orbit / zoom / pan state producing a ``CameraBasis``.

    ``revision`` increases on every change that moves the camera, so a view
    can tell a still camera (keep accumulating samples) from a moving one
    (restart accumulation) without comparing floats.
    """

    #: closest approach to the poles, radians (keeps right = forward x up finite)
    POLE_MARGIN = math.radians(0.5)

    def __init__(
        self,
        target: Vec3 = (0.0, 0.0, 0.0),
        distance: float = 30.0,
        azimuth: float = math.radians(-90.0),
        elevation: float = math.radians(20.0),
        fov_y: float = math.radians(45.0),
        min_distance: float = 0.5,
        max_distance: float = 1.0e4,
        world_up: Vec3 = (0.0, 0.0, 1.0),
    ):
        if not 0.0 < min_distance < max_distance:
            raise ValueError("need 0 < min_distance < max_distance")
        if not 0.0 < fov_y < math.pi:
            raise ValueError("fov_y must lie in (0, pi) radians")
        self.min_distance = float(min_distance)
        self.max_distance = float(max_distance)
        self.world_up = normalize(_vec(world_up))
        self.fov_y = float(fov_y)
        self._home = (_vec(target), float(distance), float(azimuth), float(elevation))
        self.revision = 0
        self._target, self._distance, self._azimuth, self._elevation = self._home
        self._distance = self._clamp_distance(self._distance)
        self._elevation = self._clamp_elevation(self._elevation)

    # -- state -----------------------------------------------------------

    @property
    def target(self) -> Vec3:
        return self._target

    @property
    def distance(self) -> float:
        return self._distance

    @property
    def azimuth(self) -> float:
        return self._azimuth

    @property
    def elevation(self) -> float:
        return self._elevation

    @property
    def position(self) -> Vec3:
        ce = math.cos(self._elevation)
        offset = (
            ce * math.cos(self._azimuth),
            ce * math.sin(self._azimuth),
            math.sin(self._elevation),
        )
        # offset is expressed in a frame whose z axis is world_up
        return _add(self._target, _scale(self._to_world(offset), self._distance))

    def _to_world(self, v: Vec3) -> Vec3:
        """Map a z-up vector into the frame whose z axis is ``world_up``."""
        up = self.world_up
        if abs(up[2] - 1.0) < 1e-12:
            return v
        helper = (1.0, 0.0, 0.0) if abs(up[0]) < 0.9 else (0.0, 1.0, 0.0)
        ex = normalize(cross(helper, up))
        ey = cross(up, ex)
        return _add(_add(_scale(ex, v[0]), _scale(ey, v[1])), _scale(up, v[2]))

    def _clamp_distance(self, d: float) -> float:
        return min(self.max_distance, max(self.min_distance, d))

    def _clamp_elevation(self, e: float) -> float:
        limit = 0.5 * math.pi - self.POLE_MARGIN
        return min(limit, max(-limit, e))

    def _commit(self, target: Vec3, distance: float, azimuth: float, elevation: float):
        new = (target, self._clamp_distance(distance),
               math.remainder(azimuth, 2.0 * math.pi), self._clamp_elevation(elevation))
        old = (self._target, self._distance, self._azimuth, self._elevation)
        if new != old:
            self._target, self._distance, self._azimuth, self._elevation = new
            self.revision += 1

    # -- interaction -------------------------------------------------------

    def orbit(self, d_azimuth: float, d_elevation: float) -> None:
        """Rotate about the target by the given angles (radians)."""
        self._commit(self._target, self._distance,
                     self._azimuth + d_azimuth, self._elevation + d_elevation)

    def orbit_pixels(self, dx: float, dy: float, viewport_height: float,
                     radians_per_viewport: float = math.pi) -> None:
        """Drag-to-orbit: a drag across the full viewport height turns by
        ``radians_per_viewport``.  The scene follows the cursor: dragging
        right moves the camera left, dragging up (Kivy y grows upwards)
        moves the camera down."""
        if viewport_height <= 0:
            return
        k = radians_per_viewport / viewport_height
        self.orbit(-dx * k, -dy * k)

    def zoom(self, factor: float) -> None:
        """Move towards the target: factor 2 halves the distance."""
        if factor <= 0 or not math.isfinite(factor):
            raise ValueError("zoom factor must be a positive finite number")
        self._commit(self._target, self._distance / factor, self._azimuth, self._elevation)

    def pan(self, dx: float, dy: float) -> None:
        """Translate camera and target together along the screen axes
        (world units)."""
        basis = self.basis(1.0)
        delta = _add(_scale(basis.right, dx), _scale(basis.up, dy))
        self._commit(_add(self._target, delta), self._distance, self._azimuth, self._elevation)

    def pan_pixels(self, dx: float, dy: float, viewport_height: float) -> None:
        """Drag-to-pan so that a point at the target's depth follows the cursor."""
        if viewport_height <= 0:
            return
        world_per_pixel = 2.0 * self._distance * math.tan(0.5 * self.fov_y) / viewport_height
        self.pan(-dx * world_per_pixel, -dy * world_per_pixel)

    def fit_sphere(self, radius: float, center: Vec3 | None = None, margin: float = 1.0) -> None:
        """Frame a bounding sphere: it touches the top/bottom edges of the view
        (scaled by ``margin`` >= 1 for breathing room)."""
        if radius <= 0:
            raise ValueError("radius must be positive")
        target = self._target if center is None else _vec(center)
        distance = margin * radius / math.sin(0.5 * self.fov_y)
        self._commit(target, distance, self._azimuth, self._elevation)

    def reset(self) -> None:
        self._commit(*self._home)

    # -- output ------------------------------------------------------------

    def basis(self, aspect: float) -> CameraBasis:
        """The camera frame for a viewport of the given width / height."""
        if aspect <= 0 or not math.isfinite(aspect):
            raise ValueError("aspect must be a positive finite number")
        position = self.position
        forward = normalize(_sub(self._target, position))
        right = normalize(cross(forward, self.world_up))
        up = cross(right, forward)
        return CameraBasis(position, right, up, forward, self.fov_y, float(aspect))
