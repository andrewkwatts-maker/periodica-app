"""Kivy GL capability spike (master plan P0c).

Proves, with printed evidence, that the Kivy graphics stack can carry the
in-house volume renderer planned for the orbital / molecule screens:

  a  full-screen-quad GLSL ES 1.00 fragment shader rendered into an ``Fbo``
     at a chosen render scale (and upscaled back to the logical size)
  b  runtime recompilation with generated, per-scene specialised source,
     its cost, uniform persistence and recovery from a broken source
  c  pixel readback (``fbo.pixels``) compared with an expected colour
  d  RGBA8 ``Texture`` with NEAREST filtering + ``blit_buffer`` sampled
     exactly, plus a 3-D grid packed as 2-D slices (16-bit fixed point,
     manual trilinear) -- the atlas fallback
  e  ``Mesh(mode='points')`` with ``gl_PointSize`` written in the vertex
     shader (and ``gl_PointCoord`` for round splats)
  f  ``GL_FRAGMENT_PRECISION_HIGH`` probe, an empirical float-precision
     probe, and ``glGetIntegerv`` limits
  g  frame time of a 128-step ray-march loop with constant bounds at 1080p
     and at render scale 0.5

Usage::

    python tools/gl_spike.py                  # Kivy's default GL backend
    python tools/gl_spike.py --angle          # GLSL ES via ANGLE (Windows)
    python tools/gl_spike.py --matrix         # every backend, one table
    python tools/gl_spike.py --json out.json  # machine-readable results

Each backend needs a fresh process (Kivy picks the GL backend at import),
which is why ``--matrix`` re-runs this script in subprocesses.  The script
opens a *hidden* window and never enters the Kivy event loop.  Exit status
is non-zero if any check fails.  Findings are recorded in
``docs/dev/gl-spike.md``.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import statistics
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from typing import Callable

# --------------------------------------------------------------------------
# Backend selection must happen before Kivy is imported.
# --------------------------------------------------------------------------

BACKENDS = {
    # name: (KIVY_GL_BACKEND or None for Kivy's default, extra env)
    "default": (None, {}),
    # Windows: SDL loads ANGLE's libEGL/libGLESv2 (D3D11) -- a strict
    # GLSL ES 1.00 front-end, the closest local stand-in for tier C.
    "angle": ("angle_sdl2", {"SDL_OPENGL_ES_DRIVER": "1"}),
    # Kivy's ES code path but SDL asks the native driver for an ES context
    # (NVIDIA returns a native "OpenGL ES 3.2" context).
    "gles-native": ("angle_sdl2", {}),
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--backend", choices=sorted(BACKENDS), default="default")
    parser.add_argument("--angle", action="store_true",
                        help="shorthand for --backend angle")
    parser.add_argument("--matrix", action="store_true",
                        help="run every backend in a subprocess and tabulate")
    parser.add_argument("--json", metavar="PATH",
                        help="write the results of this run as JSON")
    parser.add_argument("--frames", type=int, default=60,
                        help="timed frames per ray-march configuration")
    parser.add_argument("--quick", action="store_true",
                        help="fewer frames/compiles (smoke run)")
    args = parser.parse_args(argv)
    if args.angle:
        args.backend = "angle"
    return args


def _configure_environment(backend: str) -> None:
    gl_backend, extra = BACKENDS[backend]
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
    os.environ.setdefault("KIVY_NO_FILELOG", "1")
    if gl_backend:
        os.environ["KIVY_GL_BACKEND"] = gl_backend
    os.environ.update(extra)


# --------------------------------------------------------------------------
# Result model
# --------------------------------------------------------------------------

PASS, WORKAROUND, FAIL = "PASS", "WORKAROUND", "FAIL"


@dataclass
class CheckResult:
    key: str
    title: str
    status: str = FAIL
    metrics: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Shader sources -- every one is written to GLSL ES 1.00 rules: no
# ``#version`` line, precision only behind ``#ifdef GL_ES``, float literals
# always carry a '.', loops have constant bounds (ES 1.00 Appendix A).
# --------------------------------------------------------------------------

ES_HEADER = """#ifdef GL_ES
precision highp float;
#endif
"""

# Kivy binds the vertex attributes by name (vPosition, vTexCoords0) and
# supplies projection_mat / modelview_mat.  The fragment stages below use
# gl_FragCoord rather than tex_coord0: a Rectangle without an explicit
# texture samples Kivy's default *image* texture, whose tex_coords are
# flipped vertically, so tex_coord0.y runs top-down inside an Fbo.
QUAD_VS = ES_HEADER + """
attribute vec2 vPosition;
attribute vec2 vTexCoords0;
uniform mat4 modelview_mat;
uniform mat4 projection_mat;
varying vec2 v_uv;
void main(void) {
    v_uv = vTexCoords0;
    gl_Position = projection_mat * modelview_mat * vec4(vPosition, 0.0, 1.0);
}
"""

GRADIENT_FS = ES_HEADER + """
uniform vec2 u_resolution;
uniform float u_blue;
void main(void) {
    gl_FragColor = vec4(gl_FragCoord.xy / u_resolution, u_blue, 1.0);
}
"""

SOLID_FS = ES_HEADER + """
uniform vec4 u_colour;
void main(void) {
    gl_FragColor = u_colour;
}
"""

COPY_TEXEL_FS = ES_HEADER + """
uniform sampler2D u_tex;
uniform vec2 u_tex_size;
void main(void) {
    // gl_FragCoord sits on pixel centres (i + 0.5), i.e. on texel centres.
    gl_FragColor = texture2D(u_tex, gl_FragCoord.xy / u_tex_size);
}
"""

# A GRID^3 scalar field stored as GRID slices tiled TILES x TILES in a 2-D
# atlas; each texel holds a 16-bit fixed-point value as (R = hi, G = lo).
ATLAS_FS = ES_HEADER + """
uniform sampler2D u_atlas;
uniform vec2 u_atlas_size;
uniform float u_z;
const float GRID = 16.0;
const float TILES = 4.0;

float fetch(vec3 v) {
    vec3 c = clamp(v, 0.0, GRID - 1.0);
    float tile_x = mod(c.z, TILES);
    float tile_y = floor(c.z / TILES);
    vec2 texel = vec2(tile_x * GRID + c.x, tile_y * GRID + c.y) + 0.5;
    vec4 s = texture2D(u_atlas, texel / u_atlas_size);
    return floor(s.r * 255.0 + 0.5) * 256.0 + floor(s.g * 255.0 + 0.5);
}

void main(void) {
    // sample point in voxel units; exact binary fractions of the pixel index
    vec3 p = vec3((gl_FragCoord.x - 0.5) * 0.25, (gl_FragCoord.y - 0.5) * 0.25, u_z);
    vec3 i0 = floor(p);
    vec3 f = p - i0;
    float c000 = fetch(i0);
    float c100 = fetch(i0 + vec3(1.0, 0.0, 0.0));
    float c010 = fetch(i0 + vec3(0.0, 1.0, 0.0));
    float c110 = fetch(i0 + vec3(1.0, 1.0, 0.0));
    float c001 = fetch(i0 + vec3(0.0, 0.0, 1.0));
    float c101 = fetch(i0 + vec3(1.0, 0.0, 1.0));
    float c011 = fetch(i0 + vec3(0.0, 1.0, 1.0));
    float c111 = fetch(i0 + vec3(1.0, 1.0, 1.0));
    float c00 = mix(c000, c100, f.x);
    float c10 = mix(c010, c110, f.x);
    float c01 = mix(c001, c101, f.x);
    float c11 = mix(c011, c111, f.x);
    float v = floor(mix(mix(c00, c10, f.y), mix(c01, c11, f.y), f.z) + 0.5);
    float hi = floor(v / 256.0);
    gl_FragColor = vec4(hi / 255.0, (v - hi * 256.0) / 255.0, 0.0, 1.0);
}
"""

POINTS_VS = ES_HEADER + """
attribute vec2 vPosition;
attribute float vSize;
uniform mat4 modelview_mat;
uniform mat4 projection_mat;
void main(void) {
    gl_PointSize = vSize;
    gl_Position = projection_mat * modelview_mat * vec4(vPosition, 0.0, 1.0);
}
"""

POINTS_FS = ES_HEADER + """
void main(void) {
    // R: every rasterised fragment; G: fragments inside the round splat
    vec2 d = gl_PointCoord - vec2(0.5);
    gl_FragColor = vec4(1.0, 1.0 - step(0.25, dot(d, d)), 0.0, 1.0);
}
"""

PRECISION_MACRO_FS = ES_HEADER + """
void main(void) {
#if defined(GL_ES)
    float es = 1.0;
#else
    float es = 0.0;
#endif
#if defined(GL_FRAGMENT_PRECISION_HIGH)
    float hp = 1.0;
#else
    float hp = 0.0;
#endif
    gl_FragColor = vec4(es, hp, 0.0, 1.0);
}
"""

# Effective float precision under an explicit default precision.
PRECISION_BITS_FS_TEMPLATE = """#ifdef GL_ES
precision PRECISION float;
#endif
uniform float u_one;
uniform float u_k;
void main(void) {
    // mantissa bits: count halvings of eps for which (1 + eps) != 1.
    // u_one/u_k are uniforms (= 1.0) so the compiler cannot fold this.
    float eps = u_one;
    float bits = 0.0;
    for (int i = 0; i < 64; i++) {
        eps *= 0.5;
        if ((u_one + eps) * u_k > u_k) { bits += 1.0; }
    }
    // exponent range: exp(-80) = 1.8e-35 is a normal fp32 number but
    // underflows fp16 / fp24.
    float tiny = exp(-80.0 * u_one);
    gl_FragColor = vec4(bits / 255.0, tiny > 0.0 ? 1.0 : 0.0, 0.0, 1.0);
}
"""

# A 4-state hydrogen-like superposition (1s, 2s, 2p_z, 2p_x; atomic units,
# unnormalised shapes are fine for timing) evaluated by a 128-step
# emission-absorption ray march inside a bounding sphere -- the per-pixel
# workload of the planned Real-time mode.
RAYMARCH_FS_TEMPLATE = ES_HEADER + """
uniform vec2 u_resolution;
uniform vec3 u_cam_pos;
uniform vec3 u_cam_right;
uniform vec3 u_cam_up;
uniform vec3 u_cam_fwd;
uniform float u_tan_half_fov;
uniform float u_kappa;
uniform float u_frame;
uniform vec4 u_cos;
uniform vec4 u_sin;
const int STEPS = 128;
const float R_BOUND = 12.0;

DENSITY_FUNCTION

float ign(vec2 px) {
    return fract(52.9829189 * fract(dot(px, vec2(0.06711056, 0.00583715))));
}

void main(void) {
    vec2 ndc = (gl_FragCoord.xy / u_resolution) * 2.0 - 1.0;
    float aspect = u_resolution.x / u_resolution.y;
    vec3 rd = normalize(u_cam_fwd + ndc.x * aspect * u_tan_half_fov * u_cam_right
                        + ndc.y * u_tan_half_fov * u_cam_up);
    vec3 ro = u_cam_pos;
    float b = dot(ro, rd);
    float c = dot(ro, ro) - R_BOUND * R_BOUND;
    float h = b * b - c;
    vec3 colour = vec3(0.0);
    float transmittance = 1.0;
    if (h > 0.0) {
        float sq = sqrt(h);
        float t0 = max(-b - sq, 0.0);
        float t1 = -b + sq;
        float dt = (t1 - t0) / float(STEPS);
        float t = t0 + dt * ign(gl_FragCoord.xy + u_frame);
        for (int i = 0; i < STEPS; i++) {
            float rho = density(ro + rd * t);
            float alpha = 1.0 - exp(-u_kappa * rho * dt);
            colour += transmittance * alpha * vec3(0.40, 0.70, 1.00);
            transmittance *= 1.0 - alpha;
            EARLY_OUT
            t += dt;
        }
    }
    gl_FragColor = vec4(pow(colour, vec3(1.0 / 2.2)), 1.0 - transmittance);
}
"""


HYDROGENIC_DENSITY = """
float density(vec3 p) {
    float r = length(p);
    float e1 = exp(-r);
    float e2 = exp(-0.5 * r);
    vec4 phi = vec4(e1, (2.0 - r) * e2 * 0.35355339, p.z * e2 * 0.35355339, p.x * e2 * 0.35355339);
    vec4 c = vec4(0.5);
    float re = dot(c * phi, u_cos);
    float im = -dot(c * phi, u_sin);
    return re * re + im * im;
}
"""


def molecule_like_density() -> str:
    """An H2O/STO-3G-shaped density, baked as literals: 7 contracted
    functions (O 1s 2s 2p_xyz, H 1s x2) of 3 primitives each = 21 Gaussian
    exps per sample, then rho = chi^T P chi over the 28 unique pairs of a
    symmetric P.  Exponents/coefficients are STO-3G-like; the numbers only
    need to be representative of the per-sample cost."""
    import random

    rng = random.Random(7)
    centres = {"O": (0.0, 0.0, 0.22), "H1": (1.43, 0.0, -0.88), "H2": (-1.43, 0.0, -0.88)}
    s_prims = [(130.709, 0.1543), (23.809, 0.5353), (6.4436, 0.4446)]
    sp_prims = [(5.0332, 0.1), (1.1696, 0.4), (0.3804, 0.7)]
    h_prims = [(3.4253, 0.1543), (0.6239, 0.5353), (0.1689, 0.4446)]
    lines = ["float density(vec3 p) {", "    vec3 d; float r2; float g;"]
    chis = []

    def contracted(name, centre, prims, factor):
        cx, cy, cz = centre
        lines.append(f"    d = p - vec3({glsl_float(cx)}, {glsl_float(cy)}, {glsl_float(cz)});")
        lines.append("    r2 = dot(d, d);")
        terms = " + ".join(f"{glsl_float(c)} * exp({glsl_float(-a)} * r2)" for a, c in prims)
        lines.append(f"    g = {terms};")
        lines.append(f"    float {name} = {factor} * g;")
        chis.append(name)

    contracted("c0", centres["O"], s_prims, "1.0")
    contracted("c1", centres["O"], sp_prims, "1.0")
    # the three O 2p functions share the sp exponentials (one exp per prim)
    lines.append("    float c2 = d.x * g; float c3 = d.y * g; float c4 = d.z * g;")
    chis.extend(["c2", "c3", "c4"])
    contracted("c5", centres["H1"], h_prims, "1.0")
    contracted("c6", centres["H2"], h_prims, "1.0")
    terms = []
    for i in range(len(chis)):
        for j in range(i, len(chis)):
            pij = rng.uniform(-0.3, 0.9) * (1.0 if i == j else 2.0)
            terms.append(f"{glsl_float(pij)} * {chis[i]} * {chis[j]}")
    lines.append("    float rho = " + "\n        + ".join(terms) + ";")
    # keep the phase uniforms live so both workloads share one interface
    lines.append("    return max(rho, 0.0) * (u_cos.x * u_cos.x + u_sin.x * u_sin.x);")
    lines.append("}")
    return "\n".join(lines)


WORKLOADS = {
    "H-like 4 states": HYDROGENIC_DENSITY,
    "H2O-like STO-3G": None,  # generated lazily (molecule_like_density)
}


def raymarch_fs(early_out: bool, workload: str = "H-like 4 states") -> str:
    stmt = "if (transmittance < 1e-3) { break; }" if early_out else ""
    density = WORKLOADS[workload] or molecule_like_density()
    return (RAYMARCH_FS_TEMPLATE.replace("EARLY_OUT", stmt)
            .replace("DENSITY_FUNCTION", density))


def glsl_float(x: float) -> str:
    """A GLSL ES float literal.  ES has no implicit int->float conversion,
    so '1' would be an int; 9 significant digits round-trip an f32."""
    return f"{float(x):.9e}"


def specialised_fs(n_terms: int, colour: tuple, nonce: int) -> str:
    """Per-scene specialisation: every centre/exponent/coefficient is baked
    as a literal in unrolled code (no const arrays in ES 1.00, and literals
    do not use the uniform budget)."""
    import random

    rng = random.Random(1000 + n_terms)
    body = []
    for _ in range(n_terms):
        cx, cy, cz = (rng.uniform(-3, 3) for _ in range(3))
        alpha = rng.uniform(0.2, 2.0)
        coeff = rng.uniform(0.1, 1.0)
        body.append(
            f"    q = p - vec3({glsl_float(cx)}, {glsl_float(cy)}, {glsl_float(cz)});\n"
            f"    d += {glsl_float(coeff)} * exp({glsl_float(-alpha)} * dot(q, q));"
        )
    r, g, b = (glsl_float(c) for c in colour)
    return ES_HEADER + f"""
uniform vec2 u_resolution;
uniform vec4 u_tint;
void main(void) {{
    // nonce {nonce} defeats the driver's on-disk shader cache
    vec3 p = vec3(gl_FragCoord.xy / u_resolution * 6.0 - 3.0, {glsl_float(nonce * 1e-9)});
    vec3 q;
    float d = 0.0;
{chr(10).join(body)}
    // d >= 0 always, but the compiler cannot prove it, so the sum survives
    gl_FragColor = vec4({r}, {g}, {b}, 1.0) * step(-1.0, d) * u_tint;
}}
"""


# --------------------------------------------------------------------------
# The spike proper (Kivy imported lazily, after the environment is set)
# --------------------------------------------------------------------------

class Spike:
    def __init__(self, frames: int, quick: bool):
        from kivy.config import Config

        Config.set("graphics", "window_state", "hidden")
        Config.set("graphics", "width", "320")
        Config.set("graphics", "height", "240")
        from kivy.core.window import Window  # noqa: F401 -- creates the GL context
        from kivy.graphics import opengl
        from kivy.logger import Logger

        import numpy as np

        self.np = np
        self.gl = opengl
        self.frames = max(5, frames // 4) if quick else frames
        self.quick = quick
        self.shader_log: list[str] = []

        class _Capture(logging.Handler):
            def __init__(self, sink):
                super().__init__()
                self.sink = sink

            def emit(self, record):
                msg = record.getMessage()
                if "Shader" in msg or "shader" in msg:
                    self.sink.append(msg)

        Logger.addHandler(_Capture(self.shader_log))
        self.info = self._context_info()
        self.is_es = b"OpenGL ES" in self.info["version_bytes"]
        self.info.pop("version_bytes")

    # -- helpers ----------------------------------------------------------

    def _context_info(self) -> dict:
        from kivy.graphics.cgl import cgl_get_initialized_backend_name

        gl = self.gl
        version = gl.glGetString(gl.GL_VERSION)
        return {
            "kivy_gl_backend": cgl_get_initialized_backend_name(),
            "GL_VERSION": version.decode(errors="replace"),
            "GL_RENDERER": gl.glGetString(gl.GL_RENDERER).decode(errors="replace"),
            "GL_SHADING_LANGUAGE_VERSION":
                gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION).decode(errors="replace"),
            "version_bytes": version,
        }

    def make_pass(self, size, fs, vs=QUAD_VS, textures=(), uniforms=None):
        """An Fbo running ``fs`` over a full-target quad.

        ``Fbo(vs=..., fs=...)`` compiles and links both stages in one go;
        assigning ``shader.vs`` then ``shader.fs`` separately would link
        once against Kivy's default stage and log a spurious link error
        whenever the varying interface differs.
        """
        from kivy.graphics import BindTexture, ClearBuffers, ClearColor, Fbo, Rectangle

        fbo = Fbo(size=size, vs=vs, fs=fs, with_depthbuffer=False)
        for name, value in (uniforms or {}).items():
            fbo[name] = value
        with fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            for index, texture in textures:
                BindTexture(texture=texture, index=index)
            Rectangle(pos=(0, 0), size=size)
        return fbo

    def render(self, fbo):
        """Force a re-render.  ``Fbo.draw()`` is a no-op unless the canvas
        (or a uniform) changed since the last draw, so ask_update() first."""
        fbo.ask_update()
        fbo.draw()

    def finish(self):
        self.gl.glFinish()

    def read(self, fbo):
        """RGBA8 pixels as an (h, w, 4) array, row 0 = bottom (GL order)."""
        w, h = (int(v) for v in fbo.size)
        return self.np.frombuffer(fbo.pixels, self.np.uint8).reshape(h, w, 4)

    def clear_gl_errors(self) -> list[int]:
        errors = []
        for _ in range(16):
            err = self.gl.glGetError()
            if not err:
                break
            errors.append(err)
        return errors

    def timed(self, fn: Callable[[], None]) -> float:
        t0 = time.perf_counter()
        fn()
        return (time.perf_counter() - t0) * 1e3

    # -- (a) ----------------------------------------------------------------

    def check_a_fullscreen_quad(self) -> CheckResult:
        res = CheckResult("a", "Full-screen-quad ES 1.00 shader into an Fbo at render scale")
        np = self.np
        logical = (1920, 1080)
        scale = 0.5
        size = (int(logical[0] * scale), int(logical[1] * scale))
        fbo = self.make_pass(size, GRADIENT_FS, uniforms={
            "u_resolution": (float(size[0]), float(size[1])), "u_blue": 0.25})
        compiled = bool(fbo.shader.success)
        self.render(fbo)
        self.finish()
        img = self.read(fbo).astype(np.int32)
        xs = (np.arange(size[0]) + 0.5) / size[0] * 255.0
        ys = (np.arange(size[1]) + 0.5) / size[1] * 255.0
        err_r = np.abs(img[:, :, 0] - np.rint(xs)[None, :]).max()
        err_g = np.abs(img[:, :, 1] - np.rint(ys)[:, None]).max()
        err_b = np.abs(img[:, :, 2] - 64).max()

        # Upscale the low-res target back to the logical size (LINEAR), the
        # way the view will present an adaptive render scale.
        from kivy.graphics import ClearBuffers, ClearColor, Fbo, Rectangle

        up = Fbo(size=logical, with_depthbuffer=False)
        with up:
            ClearColor(0, 0, 0, 1)
            ClearBuffers()
            Rectangle(pos=(0, 0), size=logical, texture=fbo.texture)
        self.render(up)
        self.finish()
        up_img = self.read(up).astype(np.int32)
        cy, cx = logical[1] // 2, logical[0] // 2
        up_err = int(np.abs(up_img[cy, cx, :2] - np.array([128, 128])).max())

        # Uniform typing gotcha: an int sent to a float uniform is a
        # GL_INVALID_OPERATION and the value never arrives.
        probe = self.make_pass((4, 4), GRADIENT_FS, uniforms={
            "u_resolution": (4.0, 4.0), "u_blue": 1})
        self.render(probe)
        int_blue = int(self.read(probe)[0, 0, 2])
        int_errors = self.clear_gl_errors()

        res.metrics = {
            "fbo_size": f"{size[0]}x{size[1]} (scale {scale} of {logical[0]}x{logical[1]})",
            "shader_success": compiled,
            "max_err_lsb_rgb": [int(err_r), int(err_g), int(err_b)],
            "upscaled_centre_err_lsb": up_err,
            "int_to_float_uniform_blue": int_blue,
            "int_to_float_uniform_gl_errors": int_errors,
        }
        ok = compiled and max(err_r, err_g, err_b) <= 1 and up_err <= 2
        res.status = PASS if ok else FAIL
        res.notes.append("ray/pixel maths must use gl_FragCoord (or explicit tex_coords): "
                         "tex_coord0 of an untextured Rectangle is flipped vertically")
        if int_blue == 0:
            res.notes.append("uniform type follows the Python type: always pass floats "
                             "(fbo['u'] = 1 -> GL_INVALID_OPERATION; Kivy then skips "
                             "re-uploading an equal 1.0)")
        return res

    # -- (b) ----------------------------------------------------------------

    def check_b_recompile(self) -> CheckResult:
        res = CheckResult("b", "Runtime recompilation of generated per-scene shaders")
        np = self.np
        size = (256, 256)
        uniforms = {"u_resolution": (256.0, 256.0), "u_tint": (1.0, 0.5, 1.0, 1.0)}
        fbo = self.make_pass(size, SOLID_FS, uniforms=dict(uniforms, u_colour=(0.0, 0.0, 0.0, 1.0)))
        self.render(fbo)
        self.finish()

        term_counts = [8, 32, 128] if self.quick else [8, 32, 128, 512]
        rows = []
        all_correct = True
        nonce_base = int(time.time() * 1000) % 1_000_000
        for i, n in enumerate(term_counts):
            colour = (0.2 + 0.1 * i, 0.8, 0.4)
            expected = np.rint(np.array([colour[0], colour[1] * 0.5, colour[2]]) * 255)
            cold_src = specialised_fs(n, colour, nonce_base + i)
            # cold: unique source -> real compile; warm: identical source
            # again -> the driver's shader cache (NVIDIA/ANGLE keep one).
            row = {"terms": n, "source_kb": round(len(cold_src) / 1024, 1)}
            for label, src in (("cold", cold_src), ("warm", cold_src)):
                if label == "warm":
                    # flip away and back so the program really is relinked
                    fbo.shader.fs = SOLID_FS
                compile_ms = self.timed(lambda: setattr(fbo.shader, "fs", src))
                success = bool(fbo.shader.success)
                first_ms = self.timed(lambda: (self.render(fbo), self.finish()))
                img = self.read(fbo)
                got = img[size[1] // 2, size[0] // 2, :3].astype(int)
                correct = success and int(np.abs(got - expected).max()) <= 1
                all_correct &= correct
                row[f"{label}_compile_ms"] = round(compile_ms, 2)
                row[f"{label}_first_draw_ms"] = round(first_ms, 2)
                row[f"{label}_correct"] = correct
            steady = [self.timed(lambda: (self.render(fbo), self.finish())) for _ in range(10)]
            row["steady_draw_ms"] = round(statistics.median(steady), 3)
            rows.append(row)

        # Broken source: no exception, shader.success == 0, error text only in
        # the Kivy log.  Recovery = re-assign the last good source.
        self.shader_log.clear()
        good = fbo.shader.fs
        fbo.shader.fs = ES_HEADER + "void main(void) { gl_FragColor = vec4(undefined_symbol); }"
        broken_success = bool(fbo.shader.success)
        log_lines = [line for line in self.shader_log if "fail" in line.lower() or "error" in line.lower()]
        fbo.shader.fs = good
        self.render(fbo)
        self.finish()
        recovered = bool(fbo.shader.success)
        uniform_kept = int(self.read(fbo)[size[1] // 2, size[0] // 2, 1])

        res.metrics = {
            "per_size": rows,
            "broken_source_success_flag": broken_success,
            "broken_source_log_captured": bool(log_lines),
            "recovered_after_reassign": recovered,
            "u_tint_survives_relink_G": uniform_kept,
        }
        ok = all_correct and not broken_success and recovered
        res.status = PASS if ok else FAIL
        res.notes.append("compile errors never raise: check shader.success and capture "
                         "the 'Shader:' lines from kivy.logger.Logger; keep the last good source")
        res.notes.append("uniform values live in the RenderContext and are re-sent after a relink")
        return res

    # -- (c) ----------------------------------------------------------------

    def check_c_readback(self) -> CheckResult:
        res = CheckResult("c", "Pixel readback via fbo.pixels")
        np = self.np
        size = (1920, 1080)
        colour = (0.2, 0.4, 0.6, 1.0)
        fbo = self.make_pass(size, SOLID_FS, uniforms={"u_colour": colour})
        self.render(fbo)
        self.finish()
        times = []
        img = None
        for _ in range(3 if self.quick else 10):
            t0 = time.perf_counter()
            img = self.read(fbo)
            times.append((time.perf_counter() - t0) * 1e3)
        expected = np.array([51, 102, 153, 255])
        mismatched = int((np.abs(img.astype(int) - expected).max(axis=2) > 0).sum())

        # Row order: a gl_FragCoord.y gradient must increase with row index.
        grad = self.make_pass((8, 8), GRADIENT_FS, uniforms={"u_resolution": (8.0, 8.0), "u_blue": 0.0})
        self.render(grad)
        g = self.read(grad)[:, 0, 1]
        bottom_first = bool(g[0] < g[-1])

        res.metrics = {
            "size": f"{size[0]}x{size[1]}",
            "expected_rgba": expected.tolist(),
            "mismatched_pixels": mismatched,
            "readback_ms_median": round(statistics.median(times), 2),
            "bytes": int(img.nbytes),
            "row0_is_bottom": bottom_first,
        }
        res.status = PASS if mismatched == 0 and bottom_first else FAIL
        res.notes.append("fbo.pixels is a synchronous glReadPixels (stalls the pipeline): "
                         "fine for goldens/tests, keep it out of the frame loop; flip rows "
                         "(img[::-1]) before saving as an image")
        return res

    # -- (d) ----------------------------------------------------------------

    def check_d_texture(self) -> CheckResult:
        from kivy.graphics.texture import Texture

        res = CheckResult("d", "NEAREST RGBA8 texture via blit_buffer, exact sampling + 3-D atlas")
        np = self.np
        rng = np.random.default_rng(1234)
        outcomes = {}

        def make_texture(data):
            h, w = data.shape[:2]
            tex = Texture.create(size=(w, h), colorfmt="rgba", bufferfmt="ubyte")
            tex.min_filter = "nearest"
            tex.mag_filter = "nearest"
            tex.wrap = "clamp_to_edge"  # NPOT + repeat is incomplete on ES 2.0
            tex.blit_buffer(np.ascontiguousarray(data).tobytes(),
                            colorfmt="rgba", bufferfmt="ubyte")
            return tex

        # 1) exact copy, POT and NPOT
        for w, h in ((64, 64), (48, 40)):
            data = rng.integers(0, 256, size=(h, w, 4), dtype=np.uint8)
            data[..., 3] = 255  # blending is on in Kivy; keep alpha opaque
            tex = make_texture(data)
            fbo = self.make_pass((w, h), COPY_TEXEL_FS, textures=[(1, tex)],
                                 uniforms={"u_tex": 1, "u_tex_size": (float(w), float(h))})
            self.render(fbo)
            self.finish()
            out = self.read(fbo)
            # blit_buffer row 0 is the texture's t = 0 row, i.e. the bottom
            diff = int(np.abs(out.astype(int) - data.astype(int)).max())
            outcomes[f"copy_{w}x{h}_max_diff"] = diff
            outcomes[f"tex_size_{w}x{h}"] = list(tex.size)

        # 2) 16^3 grid as 16 slices in a 4x4 atlas, 16-bit fixed point,
        #    manual trilinear vs a float64 CPU reference.
        grid = 16
        values = rng.integers(0, 65536, size=(grid, grid, grid), dtype=np.int64)  # [z, y, x]
        atlas = np.zeros((64, 64, 4), np.uint8)
        for z in range(grid):
            ty, tx = divmod(z, 4)
            block = values[z]
            atlas[ty * grid:(ty + 1) * grid, tx * grid:(tx + 1) * grid, 0] = block >> 8
            atlas[ty * grid:(ty + 1) * grid, tx * grid:(tx + 1) * grid, 1] = block & 255
        atlas[..., 3] = 255
        tex = make_texture(atlas)
        out_n = 61  # (61 - 1) * 0.25 = 15 voxels -> covers the grid
        worst = 0
        for z in (0.0, 7.3125, 14.75):
            fbo = self.make_pass((out_n, out_n), ATLAS_FS, textures=[(1, tex)],
                                 uniforms={"u_atlas": 1, "u_atlas_size": (64.0, 64.0),
                                           "u_z": float(z)})
            self.render(fbo)
            self.finish()
            out = self.read(fbo).astype(np.int64)
            gpu = out[..., 0] * 256 + out[..., 1]
            ref = self._trilinear_reference(values, out_n, z)
            worst = max(worst, int(np.abs(gpu - ref).max()))
        outcomes["atlas_trilinear_max_err_lsb16"] = worst

        res.metrics = outcomes
        exact = all(v == 0 for k, v in outcomes.items() if k.startswith("copy_") and k.endswith("diff"))
        res.status = PASS if exact and worst <= 1 else FAIL
        res.notes.append("bind extra textures with BindTexture(texture=t, index=n) and set the "
                         "sampler uniform to the int n; set wrap='clamp_to_edge' for NPOT")
        return res

    def _trilinear_reference(self, values, out_n, z):
        np = self.np
        coords = np.arange(out_n) * 0.25
        px, py = np.meshgrid(coords, coords)  # rows = y
        pz = np.full_like(px, z)

        def fetch(ix, iy, iz):
            ix = np.clip(ix, 0, 15).astype(int)
            iy = np.clip(iy, 0, 15).astype(int)
            iz = np.clip(iz, 0, 15).astype(int)
            return values[iz, iy, ix].astype(np.float64)

        x0, y0, z0 = np.floor(px), np.floor(py), np.floor(pz)
        fx, fy, fz = px - x0, py - y0, pz - z0
        c = {}
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    c[dx, dy, dz] = fetch(x0 + dx, y0 + dy, z0 + dz)
        c00 = c[0, 0, 0] * (1 - fx) + c[1, 0, 0] * fx
        c10 = c[0, 1, 0] * (1 - fx) + c[1, 1, 0] * fx
        c01 = c[0, 0, 1] * (1 - fx) + c[1, 0, 1] * fx
        c11 = c[0, 1, 1] * (1 - fx) + c[1, 1, 1] * fx
        v = (c00 * (1 - fy) + c10 * fy) * (1 - fz) + (c01 * (1 - fy) + c11 * fy) * fz
        return np.floor(v + 0.5).astype(np.int64)

    # -- (e) ----------------------------------------------------------------

    def check_e_points(self) -> CheckResult:
        from kivy.graphics import Callback, ClearBuffers, ClearColor, Fbo, Mesh

        res = CheckResult("e", "Mesh(mode='points') with gl_PointSize from the vertex shader")
        gl = self.gl
        GL_PROGRAM_POINT_SIZE, GL_POINT_SPRITE = 0x8642, 0x8861
        size, point_px = 64, 8.0
        centres = [(12.0, 12.0), (52.0, 12.0), (12.0, 52.0), (52.0, 52.0), (32.0, 32.0)]
        vertices = [v for (x, y) in centres for v in (x, y, point_px)]
        fmt = [(b"vPosition", 2, "float"), (b"vSize", 1, "float")]

        def draw(enable_desktop_state: bool):
            fbo = Fbo(size=(size, size), vs=POINTS_VS, fs=POINTS_FS, with_depthbuffer=False)
            with fbo:
                ClearColor(0, 0, 0, 1)
                ClearBuffers()
                if enable_desktop_state:
                    # Re-applied every draw from inside the canvas, so it
                    # survives anything else that touches global GL state.
                    def _enable(_instr):
                        gl.glEnable(GL_PROGRAM_POINT_SIZE)
                        gl.glEnable(GL_POINT_SPRITE)
                    Callback(_enable)
                Mesh(vertices=vertices, indices=list(range(len(centres))),
                     mode="points", fmt=fmt)
            self.render(fbo)
            self.finish()
            img = self.read(fbo)
            errors = self.clear_gl_errors()
            if not enable_desktop_state:
                # leave no state behind for the next measurement
                gl.glDisable(GL_PROGRAM_POINT_SIZE)
                gl.glDisable(GL_POINT_SPRITE)
                self.clear_gl_errors()
            return int((img[..., 0] > 127).sum()), int((img[..., 1] > 127).sum()), errors

        gl.glDisable(GL_PROGRAM_POINT_SIZE)
        gl.glDisable(GL_POINT_SPRITE)
        self.clear_gl_errors()
        plain_px, plain_round, _ = draw(False)
        expected_square = int(len(centres) * point_px * point_px)
        if plain_px == expected_square:
            fixed_px, fixed_round, errors = plain_px, plain_round, []
            needs_workaround = False
        else:
            fixed_px, fixed_round, errors = draw(True)
            needs_workaround = True
        try:
            size_range = list(gl.glGetFloatv(gl.GL_ALIASED_POINT_SIZE_RANGE))
        except Exception as exc:  # pragma: no cover - driver specific
            size_range = f"unavailable ({exc!r})"

        res.metrics = {
            "points": len(centres),
            "gl_PointSize": point_px,
            "lit_px_expected_square": expected_square,
            "lit_px_without_state": plain_px,
            "lit_px_with_state": fixed_px,
            "round_splat_px": fixed_round,
            "round_splat_px_without_state": plain_round,
            "aliased_point_size_range": size_range,
            "gl_errors_after_enable": errors,
        }
        round_ok = 0 < fixed_round < fixed_px
        if fixed_px == expected_square and round_ok:
            res.status = WORKAROUND if needs_workaround else PASS
        else:
            res.status = FAIL
        if needs_workaround:
            res.notes.append("desktop GL (compat profile) ignores gl_PointSize unless "
                             "GL_PROGRAM_POINT_SIZE (0x8642) is enabled, and gl_PointCoord is "
                             "constant unless GL_POINT_SPRITE (0x8861) is enabled; enable both "
                             "from a Callback instruction (ES contexts: not needed, the enums "
                             "are GL_INVALID_ENUM)")
        return res

    # -- (f) ----------------------------------------------------------------

    def check_f_precision_limits(self) -> CheckResult:
        res = CheckResult("f", "Fragment precision probe + glGetIntegerv limits")
        gl = self.gl
        macro = self.make_pass((4, 4), PRECISION_MACRO_FS)
        self.render(macro)
        self.finish()
        m = self.read(macro)[1, 1]
        is_es_glsl = bool(m[0] > 127)
        if not is_es_glsl:
            flag = "n/a (desktop GLSL: GL_ES undefined, floats are IEEE fp32)"
        else:
            flag = "defined" if m[1] > 127 else "UNDEFINED"

        probes = {}
        for precision in ("highp", "mediump"):
            src = PRECISION_BITS_FS_TEMPLATE.replace("PRECISION", precision)
            fbo = self.make_pass((4, 4), src, uniforms={"u_one": 1.0, "u_k": 1.0})
            compiled = bool(fbo.shader.success)
            self.render(fbo)
            self.finish()
            px = self.read(fbo)[1, 1]
            probes[precision] = (compiled, int(px[0]), bool(px[1] > 127))
        hp_ok, hp_bits, hp_tiny = probes["highp"]
        mp_ok, mp_bits, mp_tiny = probes["mediump"]

        limits = {}
        names = {
            "MAX_TEXTURE_SIZE": gl.GL_MAX_TEXTURE_SIZE,
            "MAX_FRAGMENT_UNIFORM_VECTORS": 0x8DFD,
            "MAX_VERTEX_UNIFORM_VECTORS": 0x8DFB,
            "MAX_VARYING_VECTORS": 0x8DFC,
            "MAX_TEXTURE_IMAGE_UNITS": gl.GL_MAX_TEXTURE_IMAGE_UNITS,
            "MAX_VERTEX_ATTRIBS": gl.GL_MAX_VERTEX_ATTRIBS,
            "MAX_RENDERBUFFER_SIZE": gl.GL_MAX_RENDERBUFFER_SIZE,
            "MAX_VIEWPORT_DIMS": gl.GL_MAX_VIEWPORT_DIMS,
        }
        for label, pname in names.items():
            try:
                value = gl.glGetIntegerv(pname)
                limits[label] = value[0] if len(value) == 1 else list(value)
            except Exception as exc:
                limits[label] = f"unavailable ({type(exc).__name__})"
        self.clear_gl_errors()
        try:
            gl.glGetShaderPrecisionFormat(gl.GL_FRAGMENT_SHADER, 0x8DF2)
            precision_api = "available"
        except NotImplementedError:
            precision_api = "NotImplementedError in kivy.graphics.opengl"
        except Exception as exc:  # pragma: no cover
            precision_api = f"{type(exc).__name__}"

        res.metrics = {
            "GL_FRAGMENT_PRECISION_HIGH": flag,
            "highp_mantissa_bits": hp_bits if hp_ok else "compile failed",
            "highp_exp(-80)_nonzero": hp_tiny,
            "mediump_mantissa_bits": mp_bits if mp_ok else "compile failed",
            "mediump_exp(-80)_nonzero": mp_tiny,
            "glGetShaderPrecisionFormat": precision_api,
            **limits,
        }
        ok = hp_ok and hp_bits >= 23 and hp_tiny
        res.status = WORKAROUND if ok and precision_api != "available" else (PASS if ok else FAIL)
        res.notes.append("glGetShaderPrecisionFormat is not implemented by Kivy: probe precision "
                         "empirically in a shader (mantissa-bit loop on uniforms)")
        if is_es_glsl and m[1] <= 127 and hp_ok and hp_bits >= 23:
            res.notes.append("this ES driver leaves GL_FRAGMENT_PRECISION_HIGH undefined yet "
                             "compiles highp as fp32: declare 'precision highp float' "
                             "unconditionally under GL_ES and gate on the measured bits, "
                             "never fall back to mediump via the macro")
        if mp_ok and mp_bits < 23:
            res.notes.append(f"mediump is a real {mp_bits}-bit mantissa here: densities, "
                             "exp() arguments and phases must be highp")
        res.notes.append("kivy.graphics.opengl.glGetIntegerv raises KeyError for pnames missing "
                         "from its size table (e.g. desktop-only GL_MAX_FRAGMENT_UNIFORM_COMPONENTS)")
        return res

    # -- (g) ----------------------------------------------------------------

    def check_g_raymarch(self) -> CheckResult:
        res = CheckResult("g", "128-step ray-march frame time (constant loop bounds)")
        configs = [((1920, 1080), 1.0), ((1920, 1080), 0.5)]
        rows = []
        compiled_all = True
        coverage = None
        variants = [("H-like 4 states", True), ("H-like 4 states", False),
                    ("H2O-like STO-3G", True)]
        for workload, early_out in variants:
            src = raymarch_fs(early_out, workload)
            for logical, scale in configs:
                size = (int(logical[0] * scale), int(logical[1] * scale))
                fov = math.radians(45.0)
                fbo = self.make_pass(size, src, uniforms={
                    "u_resolution": (float(size[0]), float(size[1])),
                    "u_cam_pos": (0.0, 0.0, -30.0),
                    "u_cam_right": (1.0, 0.0, 0.0),
                    "u_cam_up": (0.0, 1.0, 0.0),
                    "u_cam_fwd": (0.0, 0.0, 1.0),
                    "u_tan_half_fov": math.tan(fov / 2.0),
                    "u_kappa": 40.0,
                    "u_frame": 0.0,
                    "u_cos": (1.0, 1.0, 1.0, 1.0),
                    "u_sin": (0.0, 0.0, 0.0, 0.0),
                })
                compiled_all &= bool(fbo.shader.success)
                # warm-up: let clocks ramp and the driver finish compiling
                warm_until = time.perf_counter() + (0.2 if self.quick else 0.6)
                frame = 0
                while time.perf_counter() < warm_until:
                    self._raymarch_frame(fbo, frame)
                    frame += 1
                samples = []
                for _ in range(self.frames):
                    samples.append(self.timed(lambda f=frame: self._raymarch_frame(fbo, f)))
                    frame += 1
                samples.sort()
                rows.append({
                    "workload": workload,
                    "early_out": early_out,
                    "target": f"{size[0]}x{size[1]}",
                    "scale": scale,
                    "median_ms": round(statistics.median(samples), 2),
                    "p95_ms": round(samples[int(0.95 * (len(samples) - 1))], 2),
                    "min_ms": round(samples[0], 2),
                })
                if coverage is None:
                    img = self.read(fbo)
                    coverage = round(float((img[..., 3] > 0).mean()), 3)
        res.metrics = {"frames_per_config": self.frames, "rows": rows,
                       "pixels_with_density": coverage}
        res.status = PASS if compiled_all else FAIL
        res.notes.append("timed as fbo.draw() + glFinish() (CPU wall clock, GPU-synchronous); "
                         "H-like = 4-state complex superposition with phases as vec4 cos/sin "
                         "uniforms; H2O-like = 21 Gaussian exps + 28-term chi^T P chi per sample")
        return res

    def _raymarch_frame(self, fbo, frame: int):
        # changing a uniform flags the Fbo dirty, so draw() really renders
        phase = 0.05 * frame
        fbo["u_frame"] = float(frame % 64)
        fbo["u_cos"] = (1.0, math.cos(phase), math.cos(2.0 * phase), math.cos(3.0 * phase))
        fbo["u_sin"] = (0.0, math.sin(phase), math.sin(2.0 * phase), math.sin(3.0 * phase))
        fbo.draw()
        self.finish()

    # -- driver ---------------------------------------------------------------

    def run(self) -> list[CheckResult]:
        checks = [
            self.check_a_fullscreen_quad,
            self.check_b_recompile,
            self.check_c_readback,
            self.check_d_texture,
            self.check_e_points,
            self.check_f_precision_limits,
            self.check_g_raymarch,
        ]
        results = []
        for check in checks:
            try:
                results.append(check())
            except Exception as exc:  # keep going: one broken check != no evidence
                key = check.__name__.split("_")[1]
                results.append(CheckResult(key, check.__name__, FAIL,
                                           notes=[f"{type(exc).__name__}: {exc}",
                                                  traceback.format_exc(limit=3)]))
        return results



# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def _print_report(info: dict, results: list[CheckResult]) -> None:
    print("=" * 78)
    print("Kivy GL capability spike")
    for key, value in info.items():
        print(f"  {key:<28} {value}")
    print("=" * 78)
    for r in results:
        print(f"[{r.status:<10}] ({r.key}) {r.title}")
        for k, v in r.metrics.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                print(f"      {k}:")
                for row in v:
                    print("        " + ", ".join(f"{a}={b}" for a, b in row.items()))
            else:
                print(f"      {k}: {v}")
        for note in r.notes:
            print(f"      note: {note}")
    print("=" * 78)
    counts = {s: sum(r.status == s for r in results) for s in (PASS, WORKAROUND, FAIL)}
    print("summary: " + ", ".join(f"{k}={v}" for k, v in counts.items()))


def _run_matrix(args: argparse.Namespace) -> int:
    import tempfile

    worst = 0
    summary = []
    for backend in ("default", "angle", "gles-native"):
        if backend != "default" and sys.platform != "win32":
            continue
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "result.json")
            cmd = [sys.executable, os.path.abspath(__file__), "--backend", backend,
                   "--json", out, "--frames", str(args.frames)]
            if args.quick:
                cmd.append("--quick")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            print(proc.stdout)
            if proc.returncode not in (0, 1) or not os.path.exists(out):
                print(f"[{backend}] did not produce results (exit {proc.returncode})")
                print(proc.stderr[-2000:])
                worst = max(worst, 2)
                continue
            worst = max(worst, proc.returncode)
            with open(out, encoding="utf-8") as fh:
                summary.append((backend, json.load(fh)))
    print("\nBackend matrix")
    for backend, data in summary:
        statuses = " ".join(f"{c['key']}:{c['status']}" for c in data["checks"])
        print(f"  {backend:<12} {data['info']['GL_RENDERER'][:60]:<60} {statuses}")
    return worst


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.matrix:
        return _run_matrix(args)
    _configure_environment(args.backend)
    spike = Spike(frames=args.frames, quick=args.quick)
    info = dict(spike.info, spike_backend=args.backend, es_context=spike.is_es)
    results = spike.run()
    _print_report(info, results)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"info": info, "checks": [asdict(r) for r in results]}, fh, indent=2)
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
