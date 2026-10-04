"""Fbo-backed shader views.

``FboShaderView`` runs a GLSL ES 1.00 fragment shader over a quad covering an
``Fbo`` sized ``render_scale`` x the widget, then draws the Fbo's texture
stretched over the widget (LINEAR upscale).  It is the base the volume view
(master plan D3) builds on; ``SolidColourView`` is the placeholder used by
``SceneScreen`` until there is physics to draw.

Behaviour that follows from docs/dev/gl-spike.md:

* the program is built with ``Fbo(vs=..., fs=...)`` (one link, no spurious
  errors) and recompiled by assigning ``fragment_source``;
* a source that fails to compile never replaces a working one: the last good
  program is restored and ``compile_error`` carries the driver's message;
* uniforms are kept here and re-sent after every rebuild; pass floats;
* changing a uniform marks the Fbo dirty, which is what makes Kivy re-render
  it -- ``render(dt)`` advances ``u_time`` once per frame for that reason.
"""
from __future__ import annotations

from kivy.graphics import ClearBuffers, ClearColor, Color, Fbo, Rectangle
from kivy.properties import (
    BoundedNumericProperty, ColorProperty, NumericProperty, StringProperty,
)
from kivy.uix.widget import Widget

from periodica_app.views.glsl import (
    ERROR_FS, ES_HEADER, FULLSCREEN_QUAD_VS, ShaderLog, compile_fragment,
)


def scaled_size(size, scale: float) -> tuple[int, int]:
    """Render-target size for a widget size and render scale (never < 1 px)."""
    width, height = size
    return (max(1, int(round(width * scale))), max(1, int(round(height * scale))))


class FboShaderView(Widget):
    """A widget that shows a full-target fragment shader rendered off-screen."""

    render_scale = BoundedNumericProperty(1.0, min=0.1, max=2.0)
    fragment_source = StringProperty(ERROR_FS)
    compile_error = StringProperty("")
    time = NumericProperty(0.0)

    def __init__(self, **kwargs):
        self._fbo = None
        self._quad = None
        self._display = None
        self._good_source = None
        self._uniforms = {}
        super().__init__(**kwargs)
        self.bind(size=self._layout, pos=self._layout, render_scale=self._layout)

    # -- public API --------------------------------------------------------

    @property
    def fbo(self):
        """The off-screen target (None until the first layout)."""
        return self._fbo

    @property
    def target_size(self) -> tuple[int, int]:
        return scaled_size(self.size, self.render_scale)

    def set_uniform(self, name: str, value) -> None:
        """Set (and remember) a uniform.  Pass floats -- Kivy derives the GL
        type from the Python type."""
        self._uniforms[name] = value
        if self._fbo is not None:
            self._fbo[name] = value

    def render(self, dt: float) -> None:
        """Advance one frame (called by the screen's frame loop)."""
        self.time += dt
        self.set_uniform("u_time", float(self.time))

    def redraw(self) -> None:
        """Re-render the Fbo immediately (tests, one-off captures).
        ``Fbo.draw()`` alone is a no-op unless the Fbo is dirty."""
        self._ensure_fbo()
        self._fbo.ask_update()
        self._fbo.draw()

    # -- shader management ---------------------------------------------------

    def on_fragment_source(self, _instance, source):
        if self._fbo is None:
            return  # compiled when the Fbo is created
        ok, log = compile_fragment(self._fbo, source)
        if ok:
            self._good_source = source
            self.compile_error = ""
        else:
            self.compile_error = log or "fragment shader failed to compile"
            compile_fragment(self._fbo, self._good_source or ERROR_FS)

    def _create_fbo(self, size):
        source = self.fragment_source
        with ShaderLog() as log:
            fbo = Fbo(size=size, vs=FULLSCREEN_QUAD_VS, fs=source, with_depthbuffer=False)
        if fbo.shader.success:
            self._good_source = source
            self.compile_error = ""
        else:
            self.compile_error = log.text or "fragment shader failed to compile"
            compile_fragment(fbo, self._good_source or ERROR_FS)
        with fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            self._quad = Rectangle(pos=(0, 0), size=size)
        return fbo

    # -- layout ------------------------------------------------------------

    def _ensure_fbo(self):
        size = self.target_size
        if self._fbo is None:
            self._fbo = self._create_fbo(size)
            self.canvas.clear()
            self.canvas.add(self._fbo)
            with self.canvas:
                Color(1, 1, 1, 1)
                self._display = Rectangle(texture=self._fbo.texture, pos=self.pos, size=self.size)
            for name, value in self._uniforms.items():
                self._fbo[name] = value
        elif tuple(self._fbo.size) != size:
            self._fbo.size = size  # reallocates the texture
            self._quad.size = size
            self._display.texture = self._fbo.texture
        self._fbo["u_resolution"] = (float(size[0]), float(size[1]))

    def _layout(self, *_args):
        self._ensure_fbo()
        self._display.pos = self.pos
        self._display.size = self.size


SOLID_COLOUR_FS = ES_HEADER + """
uniform vec4 u_colour;
void main(void) {
    gl_FragColor = u_colour;
}
"""


class SolidColourView(FboShaderView):
    """Placeholder scene view: one colour, rendered through the full Fbo path."""

    colour = ColorProperty([0.11, 0.13, 0.22, 1.0])

    def __init__(self, **kwargs):
        kwargs.setdefault("fragment_source", SOLID_COLOUR_FS)
        super().__init__(**kwargs)
        self.bind(colour=self._push_colour)
        self._push_colour()

    def _push_colour(self, *_args):
        self.set_uniform("u_colour", tuple(float(c) for c in self.colour))
