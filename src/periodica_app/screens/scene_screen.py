"""
SceneScreen -- base for GPU-rendered 3-D screens (orbitals, atoms, molecules).

Adds a frame loop to ShellScreen.  The loop runs only while the screen is
shown: ``on_enter`` starts it, ``on_leave`` stops it, and the application's
``on_pause`` / ``on_resume`` events pause and resume it (on desktop Kivy only
dispatches those when ``[kivy] pause_on_minimize`` is enabled).  Each tick
calls ``on_frame(dt)``, which by default advances the main view.

The default view is a ``SolidColourView`` placeholder rendered through the
same Fbo path the volume renderer will use; there is no physics yet.  The
drawer is built from ``scene_controls()`` using the generic sections and
reports through ``on_control_change(key, value)``.
"""

from kivy.app import App
from kivy.properties import NumericProperty

from periodica_app.screens.shell_screen import ShellScreen
from periodica_app.views.fbo_view import SolidColourView
from periodica_app.views.frame_loop import FrameLoop


class SceneScreen(ShellScreen):
    """A ShellScreen whose main view is redrawn by a frame loop while shown."""

    target_fps = NumericProperty(60.0)

    def __init__(self, **kwargs):
        self._app = None
        super().__init__(**kwargs)
        self.frame_loop = FrameLoop(self.on_frame, fps=self.target_fps)
        drawer = self.ids.control_drawer
        drawer.on_control = self.on_control_change
        drawer.build_controls(self.scene_controls())

    # -- extension points --------------------------------------------------

    def create_view(self):
        return SolidColourView()

    def scene_controls(self):
        """Drawer config (generic sections).  Override per scene."""
        return {
            "sliders": [{
                "key": "render_scale", "label": "Render scale",
                "min": 0.25, "max": 1.0, "default": 1.0, "step": 0.05,
                "format": "{:.2f}",
            }],
        }

    def on_control_change(self, key, value):
        """A generic drawer control changed (buttons report value=None)."""
        if key == "render_scale" and self.view is not None:
            self.view.render_scale = float(value)

    def on_frame(self, dt):
        """One frame of the loop: advance the main view."""
        render = getattr(self.view, "render", None)
        if render is not None:
            render(dt)

    # -- lifecycle -----------------------------------------------------------

    def on_enter(self, *args):
        self._bind_app()
        self.frame_loop.start()

    def on_leave(self, *args):
        self.frame_loop.stop()

    def _bind_app(self):
        app = App.get_running_app()
        if app is None or app is self._app:
            return
        self._unbind_app()
        app.bind(on_pause=self._on_app_pause, on_resume=self._on_app_resume)
        self._app = app

    def _unbind_app(self):
        if self._app is not None:
            self._app.unbind(on_pause=self._on_app_pause, on_resume=self._on_app_resume)
            self._app = None

    # Handlers return None: a True return would stop the dispatch before
    # App.on_pause, whose True is what allows the app to pause at all.
    def _on_app_pause(self, *_args):
        self.frame_loop.pause()

    def _on_app_resume(self, *_args):
        self.frame_loop.resume()
