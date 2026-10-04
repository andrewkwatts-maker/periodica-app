"""Tier A: the orbit camera is pure maths -- no Kivy, no window."""
from __future__ import annotations

import math
import subprocess
import sys

import pytest

from periodica_app.views.camera_controller import (
    CameraBasis, OrbitCamera, cross, dot, norm,
)

TOL = 1e-12


def close(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def angle_between(a, b):
    return math.acos(max(-1.0, min(1.0, dot(a, b) / (norm(a) * norm(b)))))


@pytest.fixture
def cam():
    return OrbitCamera(target=(1.0, -2.0, 0.5), distance=10.0,
                       azimuth=math.radians(30), elevation=math.radians(25))


def test_basis_is_orthonormal_and_right_handed(cam):
    b = cam.basis(16 / 9)
    for v in (b.right, b.up, b.forward):
        assert abs(norm(v) - 1.0) < TOL
    assert abs(dot(b.right, b.up)) < TOL
    assert abs(dot(b.right, b.forward)) < TOL
    assert abs(dot(b.up, b.forward)) < TOL
    assert close(cross(b.right, b.up), tuple(-c for c in b.forward))


def test_camera_looks_at_target_from_its_distance(cam):
    b = cam.basis(1.0)
    to_target = tuple(t - p for t, p in zip(cam.target, b.position))
    assert abs(norm(to_target) - 10.0) < 1e-9
    assert close(b.forward, tuple(c / 10.0 for c in to_target))


def test_up_vector_leans_towards_world_up(cam):
    b = cam.basis(1.0)
    assert dot(b.up, (0.0, 0.0, 1.0)) > 0.0
    assert abs(dot(b.right, (0.0, 0.0, 1.0))) < TOL  # no roll


def test_default_camera_sees_the_z_axis_upright():
    b = OrbitCamera(elevation=0.0).basis(1.0)
    assert close(b.up, (0.0, 0.0, 1.0))


def test_full_orbit_returns_to_start(cam):
    before = cam.position
    for _ in range(8):
        cam.orbit(math.pi / 4, 0.0)
    assert close(cam.position, before, 1e-9)


def test_elevation_stops_short_of_the_poles(cam):
    cam.orbit(0.0, 10.0)
    assert cam.elevation < math.pi / 2
    b = cam.basis(1.0)
    assert all(math.isfinite(c) for c in b.right + b.up + b.forward)
    cam.orbit(0.0, -20.0)
    assert cam.elevation > -math.pi / 2


def test_zoom_divides_distance_and_clamps():
    cam = OrbitCamera(distance=8.0, min_distance=1.0, max_distance=100.0)
    cam.zoom(2.0)
    assert cam.distance == pytest.approx(4.0)
    cam.zoom(1e6)
    assert cam.distance == 1.0
    cam.zoom(1e-6)
    assert cam.distance == 100.0
    with pytest.raises(ValueError):
        cam.zoom(0.0)


def test_pan_moves_target_and_eye_together(cam):
    before = cam.basis(1.0)
    target_before = cam.target
    cam.pan(2.0, -1.0)
    after = cam.basis(1.0)
    expected = tuple(t + 2.0 * r - 1.0 * u
                     for t, r, u in zip(target_before, before.right, before.up))
    assert close(cam.target, expected)
    assert close(after.forward, before.forward)
    assert cam.distance == pytest.approx(10.0)


def test_pan_pixels_keeps_the_target_under_the_cursor(cam):
    """Dragging by the full viewport height shifts the target by the height
    of the view frustum at the target's depth."""
    height_px = 600.0
    b = cam.basis(1.0)
    frustum_height = 2.0 * cam.distance * math.tan(cam.fov_y / 2)
    target_before = cam.target
    cam.pan_pixels(0.0, height_px, height_px)
    moved = tuple(a - c for a, c in zip(cam.target, target_before))
    assert close(moved, tuple(-frustum_height * u for u in b.up), 1e-9)


def test_orbit_pixels_follows_the_cursor():
    cam = OrbitCamera(azimuth=0.0, elevation=0.0)
    cam.orbit_pixels(100.0, 0.0, 400.0, radians_per_viewport=math.pi)
    assert cam.azimuth == pytest.approx(-math.pi / 4)
    cam.orbit_pixels(0.0, 100.0, 400.0, radians_per_viewport=math.pi)
    assert cam.elevation == pytest.approx(-math.pi / 4)


def test_fit_sphere_makes_the_sphere_touch_the_view_edges(cam):
    cam.fit_sphere(5.0, center=(0.0, 0.0, 0.0))
    assert cam.target == (0.0, 0.0, 0.0)
    assert cam.distance * math.sin(cam.fov_y / 2) == pytest.approx(5.0)
    b = cam.basis(1.0)
    # the ray through the top edge of the view grazes the sphere
    top = b.ray(0.0, 1.0)
    eye = b.position
    t = -dot(eye, top)
    closest = tuple(e + t * d for e, d in zip(eye, top))
    assert norm(closest) == pytest.approx(5.0)


def test_rays_span_the_field_of_view():
    cam = OrbitCamera(fov_y=math.radians(60))
    b = cam.basis(2.0)
    assert close(b.ray(0.0, 0.0), b.forward)
    assert angle_between(b.ray(0.0, 1.0), b.forward) == pytest.approx(math.radians(30))
    horizontal = math.atan(2.0 * math.tan(math.radians(30)))
    assert angle_between(b.ray(1.0, 0.0), b.forward) == pytest.approx(horizontal)


def test_uniforms_are_floats_for_kivy():
    uniforms = OrbitCamera().basis(1.5).as_uniforms()
    assert set(uniforms) == {"u_cam_pos", "u_cam_right", "u_cam_up", "u_cam_fwd",
                             "u_tan_half_fov", "u_aspect"}
    for value in uniforms.values():
        values = value if isinstance(value, tuple) else (value,)
        assert all(type(v) is float for v in values)


def test_revision_tracks_real_changes_only(cam):
    r0 = cam.revision
    cam.zoom(1.0)
    cam.pan(0.0, 0.0)
    assert cam.revision == r0
    cam.orbit(0.1, 0.0)
    assert cam.revision == r0 + 1
    cam.reset()
    assert cam.revision == r0 + 2
    assert cam.azimuth == pytest.approx(math.radians(30))


def test_custom_world_up_is_respected():
    cam = OrbitCamera(world_up=(0.0, 1.0, 0.0), elevation=0.0)
    b = cam.basis(1.0)
    assert close(b.up, (0.0, 1.0, 0.0))
    assert abs(dot(b.forward, (0.0, 1.0, 0.0))) < TOL


def test_invalid_construction_is_rejected():
    with pytest.raises(ValueError):
        OrbitCamera(min_distance=5.0, max_distance=1.0)
    with pytest.raises(ValueError):
        OrbitCamera(fov_y=math.pi)
    with pytest.raises(ValueError):
        OrbitCamera().basis(0.0)


def test_basis_is_a_value_object():
    b = OrbitCamera().basis(1.0)
    assert isinstance(b, CameraBasis)
    with pytest.raises(AttributeError):
        b.aspect = 2.0  # frozen


def test_module_imports_no_kivy():
    code = ("import sys, periodica_app.views.camera_controller; "
            "bad = [m for m in sys.modules if m == 'kivy' or m.startswith('kivy.')]; "
            "print(bad); sys.exit(1 if bad else 0)")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
