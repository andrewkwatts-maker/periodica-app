"""GLSL ES 1.00 building blocks shared by the GPU views.

Rules (measured in docs/dev/gl-spike.md, which ``tools/gl_spike.py``
reproduces):

* no ``#version`` line; ``precision highp float;`` only under ``#ifdef GL_ES``
  and never downgraded via ``GL_FRAGMENT_PRECISION_HIGH`` (a native ES driver
  leaves it undefined while its mediump is fp16);
* float literals always carry a '.' or an exponent (``glsl_float``);
* loops have constant bounds;
* derive pixel positions from ``gl_FragCoord`` (an untextured Rectangle's
  ``tex_coord0`` is flipped vertically).
"""
from __future__ import annotations

import logging

ES_HEADER = """#ifdef GL_ES
precision highp float;
#endif
"""

# Pass-through vertex stage for a quad covering the render target.  Kivy
# binds vPosition / vTexCoords0 by name and supplies the two matrices.
FULLSCREEN_QUAD_VS = ES_HEADER + """
attribute vec2 vPosition;
attribute vec2 vTexCoords0;
uniform mat4 modelview_mat;
uniform mat4 projection_mat;
void main(void) {
    gl_Position = projection_mat * modelview_mat * vec4(vPosition, 0.0, 1.0);
}
"""

# Shown when a view has never compiled successfully: unmistakably wrong.
ERROR_FS = ES_HEADER + """
void main(void) {
    gl_FragColor = vec4(1.0, 0.0, 1.0, 1.0);
}
"""


def glsl_float(x: float) -> str:
    """A GLSL ES float literal that round-trips an f32 (9 significant digits).

    ES has no implicit int -> float conversion, so ``1`` would be an int.
    """
    return f"{float(x):.9e}"


class _ListHandler(logging.Handler):
    def __init__(self, sink: list[str]):
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "shader" in message.lower():
            self.sink.append(message)


class ShaderLog:
    """Collect Kivy's ``Shader: ...`` log lines while compiling.

    Kivy never raises on a compile/link error: it sets ``shader.success`` to
    0 and logs the driver's message, which is the only place the text exists.
    """

    def __init__(self) -> None:
        self.lines: list[str] = []
        self._handler = _ListHandler(self.lines)

    def __enter__(self) -> "ShaderLog":
        from kivy.logger import Logger

        Logger.addHandler(self._handler)
        return self

    def __exit__(self, *exc) -> None:
        from kivy.logger import Logger

        Logger.removeHandler(self._handler)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def compile_fragment(context, source: str) -> tuple[bool, str]:
    """Assign ``source`` as the fragment stage of a RenderContext / Fbo.

    Returns ``(ok, log_text)``.  On failure the context is left with the
    broken program; callers restore their last good source.
    """
    with ShaderLog() as log:
        context.shader.fs = source
    return bool(context.shader.success), log.text
