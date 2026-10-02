# Kivy GL capability spike (P0c)

**Question:** can the Kivy graphics stack carry the in-house GLSL ES 1.00 volume
renderer planned for the Orbitals / Atoms / Molecules screens (master plan,
Phase 6 "Renderer" and "App integration")?

**Answer: yes, on all three GL paths tested.** Every capability (a)–(g) works.
Two need a documented workaround: point sprites on desktop GL, and the
precision query that Kivy does not expose. The frame-time budget has a lot of
headroom: the 128-step ray march takes **0.6–0.9 ms at 1080p** for a 4-state
hydrogen-like superposition and **1.8 ms** for an H2O/STO-3G-shaped density.
That is well under the plan's 3–6 ms and 6–10 ms budgets. The real limit is
**shader compile time** for large per-scene specialisations, especially under
ANGLE.

Reproduce:

```bash
python tools/gl_spike.py                 # Kivy default backend (glew on Windows)
python tools/gl_spike.py --angle         # ANGLE -> Direct3D 11 (strict GLSL ES)
python tools/gl_spike.py --matrix        # all backends, one summary table
python tools/gl_spike.py --json out.json # machine-readable results
```

The script opens a hidden window, never enters the event loop, and exits
non-zero if any check fails. A run takes about 2 s with `--quick` and about 15 s
for the full matrix.

## Test machine (2026-10-02)

| | |
|---|---|
| GPU / driver | NVIDIA GeForce RTX 3070 Ti, driver 616.92 |
| OS / Python | Windows 11 Pro, CPython 3.13.14 |
| Kivy / KivyMD | 2.3.1 (kivy_deps.angle 0.4.0, glew 0.3.1, sdl2 0.8.0) / 1.2.0 |

| `--backend` | How | Context reported |
|---|---|---|
| `default` | Kivy default on Windows (`glew`) | OpenGL 4.6 compatibility, GLSL 4.60 (`GL_ES` undefined) |
| `angle` | `KIVY_GL_BACKEND=angle_sdl2` **and** `SDL_OPENGL_ES_DRIVER=1` | OpenGL ES 3.0 (ANGLE 2.1.21998, Direct3D11) |
| `gles-native` | `KIVY_GL_BACKEND=angle_sdl2` without the SDL hint | OpenGL ES 3.2 (native NVIDIA ES context) |

> `angle_sdl2` alone does **not** give you ANGLE on an NVIDIA machine. SDL asks
> the native driver for an ES context. Set `SDL_OPENGL_ES_DRIVER=1` so SDL loads
> ANGLE's `libEGL`/`libGLESv2`. ANGLE's translator enforces GLSL ES 1.00 rules
> (Appendix A loop rules, no implicit int→float conversion, and so on). That
> makes it a useful local stand-in for the tier-C `glslangValidator` gate.

All shaders in the spike are written to GLSL ES 1.00 rules: no `#version` line,
`precision highp float;` inside `#ifdef GL_ES`, float literals always contain a
`.` or an exponent, and loops have constant bounds. All of them compiled on
every backend.

## Findings

Status: **PASS** = works as-is, **WORKAROUND** = works with the documented
workaround, **LIMIT** = works, but there is a ceiling to design around.

| # | Capability | Status | Evidence (desktop GL / ANGLE / native ES) |
|---|---|---|---|
| a | Full-screen-quad ES 1.00 fragment shader in an `Fbo` (`RenderContext` + `Shader`) at render scale 0.5 of 1920×1080, upscaled back with LINEAR | **PASS** | 960×540 target. Max error vs analytic `gl_FragCoord` gradient is ≤ 1 LSB over every pixel, and the upscaled centre is exact. Same on all three backends. |
| b | Runtime recompilation of generated per-scene source (unrolled baked literals) | **PASS / LIMIT** | Every specialised variant was active after the swap (read back correctly), and uniforms survive the relink. A broken source sets `shader.success = 0` without raising; the error text is captured from the Kivy logger, and reassigning the last good source recovers. Cold compile cost by term count (8 / 32 / 128 / 512 Gaussian terms, i.e. 1.5 / 4.6 / 17 / 67 KB of source): **desktop** 5 / 9–11 / 31–35 / 133–135 ms, **native ES** 5 / 10 / 32 / 134–150 ms, **ANGLE** 8 / 19–32 / 93–124 / 1030–1120 ms, plus up to 147 ms on the first draw. An identical source recompiles in 0.1–3 ms on NVIDIA, which keeps a driver cache. ANGLE does not (76–1146 ms again). A steady draw takes 0.04–0.15 ms. |
| c | `fbo.pixels` readback vs expected colour | **PASS** | 1920×1080 solid (51,102,153,255): 0 mismatched pixels. 8.3 MB read back in 2.5–7.8 ms (median varies run to run). Rows come bottom-first (GL order) on every backend. |
| d | RGBA8 `Texture`, NEAREST, `blit_buffer`, exact sampling + atlas fallback | **PASS** | Identity copy of random 64×64 (POT) and 48×40 (NPOT) textures has **max diff 0**. A 16³ grid of 16-bit fixed-point values (R = hi, G = lo) packed as 16 slices in a 4×4 atlas, fetched with manual addressing plus manual trilinear in the shader, matches a float64 numpy reference with **max error 0 LSB16** at 3 × 61² sample points. `Texture.size` is not padded to a power of two. |
| e | `Mesh(mode='points')` with `gl_PointSize` from the vertex shader | **WORKAROUND** (desktop) / **PASS** (ES) | Desktop GL compat profile: 5 points at `gl_PointSize = 8` light **5 px** (1 px each), and `gl_PointCoord` is constant. With `GL_PROGRAM_POINT_SIZE` (0x8642) and `GL_POINT_SPRITE` (0x8861) enabled, they light **320 px** (5 × 8²), and a round splat via `gl_PointCoord` lights 260 px. ANGLE and native ES give 320 / 260 with no state change (the two enums are `GL_INVALID_ENUM` there). Aliased point-size range: 1–2047 (desktop, native ES), 1–1024 (ANGLE). |
| f | `GL_FRAGMENT_PRECISION_HIGH` probe + `glGetIntegerv` limits | **WORKAROUND** | `glGetShaderPrecisionFormat` raises `NotImplementedError` in `kivy.graphics.opengl`, so the replacement is an empirical in-shader probe (mantissa-bit loop on uniforms plus an `exp(-80)` range test). Measured `highp` is **23 mantissa bits** (fp32) on all three backends. `GL_FRAGMENT_PRECISION_HIGH` is n/a on desktop GL (`GL_ES` undefined), *defined* on ANGLE, and **undefined on native NVIDIA ES** even though highp works there. `mediump` is fp32 on desktop and ANGLE but a **real fp16 (10 bits, `exp(-80)` → 0)** on native ES. See the limits table below. |
| g | 128-step ray march, constant loop bounds, emission–absorption, bounding sphere, IGN jitter | **PASS** | See the frame-time table below. Cost scales linearly with step count: 32 / 128 / 512 / 2048 steps take 0.27 / 0.89 / 3.4 / 12.2 ms at 1080p on desktop. The timing is genuine GPU time: the same 128-step frame measures 0.09 ms without `glFinish`. |

### Frame time (g), median of 120 frames, `fbo.draw()` + `glFinish()`

Camera at 30 bohr, 45° vertical FOV, bounding sphere R = 12 bohr. 48 % of
pixels hit the sphere, so this is close to the worst case for a centred atom.

| Workload | Target | desktop GL | ANGLE (D3D11) | native ES |
|---|---|---|---|---|
| H-like, 4 complex states, early-out | 1920×1080 | 0.83 ms (p95 1.09) | 0.66 ms (p95 0.69) | 0.85 ms (p95 0.99) |
| H-like, 4 complex states, early-out | 960×540 (scale 0.5) | 0.32 ms | 0.21 ms | 0.35 ms |
| H-like, 4 states, no early-out | 1920×1080 | 0.87 ms | 0.61 ms | 0.93 ms |
| H-like, 4 states, no early-out | 960×540 | 0.27 ms | 0.21 ms | 0.34 ms |
| H2O-like STO-3G (21 Gaussian exps + 28-term χᵀPχ per sample), early-out | 1920×1080 | 1.87 ms (p95 2.2) | 1.82 ms | 1.83 ms |
| same | 960×540 | 0.57 ms | 0.54 ms | 0.56 ms |

Early-out (`T < 1e-3`) makes no measurable difference at τ_ref ≈ 3, as expected:
transmittance rarely gets that low.

### Limits (f)

| `glGetIntegerv` | desktop GL | ANGLE | native ES | ES 2.0 guaranteed minimum |
|---|---|---|---|---|
| MAX_TEXTURE_SIZE | 32768 | 16384 | 32768 | 64 |
| MAX_FRAGMENT_UNIFORM_VECTORS | 1024 | 1024 | 1024 | 16 |
| MAX_VERTEX_UNIFORM_VECTORS | 1024 | 4095 | 1024 | 128 |
| MAX_VARYING_VECTORS | 31 | 30 | 31 | 8 |
| MAX_TEXTURE_IMAGE_UNITS | 32 | 16 | 32 | 8 |
| MAX_VERTEX_ATTRIBS | 16 | 16 | 16 | 8 |
| MAX_RENDERBUFFER_SIZE | 32768 | 16384 | 32768 | 1 |
| MAX_VIEWPORT_DIMS | 32768² | 32767² | 32768² | — |

The plan's ≤ 9 vec4 per-frame uniforms fits even the ES 2.0 minimum of 16.

## Gotchas and the rule each one implies

1. **`Fbo.draw()` is a no-op unless the canvas is dirty.** It re-renders only
   when an instruction or uniform changed since the last draw. Setting a
   uniform such as the frame index or a phase marks it dirty. Otherwise, call
   `fbo.ask_update()` before `fbo.draw()`. A static camera that idles
   (accumulation finished) gets this for free.
2. **The uniform's GL type follows the Python type.** `fbo['u'] = 1` on a
   `float` uniform causes `GL_INVALID_OPERATION`, and the value never arrives.
   Kivy also skips re-uploading a value that compares equal, so a later
   `fbo['u'] = 1.0` is ignored too. Always pass `float(...)`. Pass `int` only
   for samplers.
3. **`tex_coord0` of an untextured `Rectangle` is flipped vertically.** Kivy's
   default texture is an image with flipped `tex_coords`. Derive rays from
   `gl_FragCoord.xy / u_resolution`, or pass explicit
   `tex_coords=(0,0,1,0,1,1,0,1)`.
4. **`fbo.pixels` is bottom-row-first.** Flip with `img[::-1]` before saving.
   It is a synchronous `glReadPixels` that stalls the pipeline (3–8 ms at
   1080p), so it belongs in tests and golden capture, not in the frame loop.
5. **Compile errors never raise.** Check `shader.success`. The driver's error
   text only goes to `kivy.logger.Logger` as `Shader: …` lines; attach a
   `logging.Handler` to capture it. Keep the last good source and reassign it
   on failure. The program keeps its uniform values across relinks.
6. **Build passes with `Fbo(vs=..., fs=...)`.** Assigning `shader.vs` and then
   `shader.fs` links once against Kivy's default stage in between, which logs
   a spurious link error whenever the varying interface differs.
7. **Desktop point sprites need two enables:** `GL_PROGRAM_POINT_SIZE`
   (0x8642) and `GL_POINT_SPRITE` (0x8861). Issue them from a `Callback`
   instruction placed before the `Mesh`, so they are re-applied every draw.
   Skip them on ES, where they are `GL_INVALID_ENUM`, and clear `glGetError`.
8. **Precision:** always write `precision highp float;` under `#ifdef GL_ES`.
   Never fall back to mediump via `#ifdef GL_FRAGMENT_PRECISION_HIGH`:
   NVIDIA's native ES driver leaves the macro undefined, and its mediump really
   is fp16, which would silently ruin densities, `exp()` arguments and phases.
   At start-up, gate the GPU path on the measured mantissa bits (≥ 23).
9. **`kivy.graphics.opengl` gaps:** `glGetShaderPrecisionFormat` raises
   `NotImplementedError`. `glGetIntegerv` raises `KeyError` for pnames missing
   from Kivy's size table (for example the desktop-only
   `GL_MAX_FRAGMENT_UNIFORM_COMPONENTS`). Wrap capability queries.
10. **Extra textures:** bind with `BindTexture(texture=t, index=n)` and set the
    sampler uniform to the int `n`. Use `wrap='clamp_to_edge'` for NPOT
    textures (NPOT with repeat is incomplete on strict ES 2.0).
11. **Literal emission:** GLSL ES has no implicit int→float conversion, so a
    baked `1` is an `int`. Emit every literal as `%.9e`; 9 significant digits
    round-trip an f32.

## Implications for the plan

- **The renderer budget has headroom.** The planned "auto render-scale 0.5"
  is unlikely to be needed for H-like or small molecules on this class of GPU.
  Keep it for integrated GPUs and llvmpipe. D8 should still measure benzene and
  a real HF density.
- **Compile cost is the real limit (C3/D3).** Recompile on scene change only,
  never per frame. Cache programs per scene keyed by source hash. Show a
  "compiling…" state. Expect about 0.25 ms per baked Gaussian term on native
  drivers. Under ANGLE it is 0.8–2.2 ms per term and grows faster than
  linearly. ANGLE also does not reuse an
  identical source, so the view must keep compiled `Fbo`/`RenderContext`
  objects alive rather than reassigning source. Once a specialisation goes
  past roughly 150–200 terms, prefer the atlas path, which has proven exact.
  The alternative is a uniform-driven generic shader for the bulky part.
- **The atlas fallback is proven bit-exact** (NEAREST + 16-bit fixed point +
  manual trilinear = 0 LSB error), so C5 can rely on it.
- **Hits layer (D4):** `Mesh(mode='points')` with `gl_PointSize` works. The
  view must apply gotcha 7 on desktop GL.
- **`gl_caps.py` (D3):** record the context strings, `es_context`, the
  measured highp bits, the point-size range, and the `glGetIntegerv` limits
  above. Choose GPU / atlas / CPU on that basis.
- **Tier B tests:** `--angle` gives a strict ES 1.00 compile locally on
  Windows. CI should keep `glslangValidator` (tier C) plus Mesa llvmpipe.
