"""Tier B: the shell screens, drawer and Fbo view with a real GL context.

Run with ``pytest -m gpu``.  Each test builds widgets against the hidden
window from the ``gl_window`` fixture; the app itself is not started.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import time

import pytest

pytestmark = pytest.mark.gpu


def _pump(seconds=0.0, frames=1):
    """Run the Kivy clock: due callbacks fire, scheduled intervals advance."""
    from kivy.clock import Clock

    end = time.perf_counter() + seconds
    done = 0
    while done < frames or time.perf_counter() < end:
        Clock.tick()
        done += 1


def _rgba(fbo):
    import numpy as np

    w, h = (int(v) for v in fbo.size)
    return np.frombuffer(fbo.pixels, np.uint8).reshape(h, w, 4)


# ── DomainScreen on ShellScreen: the quarks screen is unchanged ─────────────


def test_quarks_screen_keeps_its_canvas_view_and_drawer(gl_window):
    from periodica_app.screens.quarks_screen import QuarksScreen
    from periodica_app.widgets.canvas_view import CanvasView
    from periodica_app.widgets.control_drawer import SectionLabel

    screen = QuarksScreen()
    assert isinstance(screen.view, CanvasView)
    assert screen.ids.canvas_view is screen.view
    assert screen.view in screen.ids.view_host.children  # ids hold WeakProxies

    _pump()  # DomainScreen._initialize is scheduled for the next frame
    assert screen.ids.canvas_view.items, "quark data never reached the canvas"
    assert screen.ids.canvas_view.renderer is not None

    drawer = screen.ids.control_drawer
    headings = [w.text for w in reversed(drawer.ids.controls_box.children)
                if isinstance(w, SectionLabel)]
    assert headings == ["Layout Mode", "Fill Color", "Border Color", "Glow Effect",
                        "Sort By", "Display Options", "Data Operations"]
    assert drawer.layout_spinner.text == "Standard Model"
    assert len(drawer.layout_spinner.values) == 8
    assert drawer.fill_spinner.text == "Particle Type"
    assert drawer.border_spinner.text == "Charge (e)"
    assert drawer.glow_spinner.text == "None"
    assert drawer.sort_spinner.text == "Mass (MeV/c²)"
    assert drawer.control_values == {}

    drawer._on_toggle("show_connections", True)
    assert screen.ids.canvas_view.show_connections is True


def test_shell_toggles_drawer_and_info(gl_window):
    from periodica_app.screens.shell_screen import ShellScreen

    screen = ShellScreen()
    assert screen.view is None and "view" not in screen.ids
    screen.toggle_controls()
    screen.toggle_info()
    assert (screen.show_controls, screen.show_info) == (False, True)


# ── ControlDrawer generic sections ───────────────────────────────────────────


def test_drawer_generic_sections_report_through_on_control(gl_window):
    from kivy.uix.button import Button
    from kivy.uix.slider import Slider
    from kivy.uix.togglebutton import ToggleButton

    from periodica_app.widgets.control_drawer import ControlDrawer
    from test_control_specs import SCENE_CONFIG

    drawer = ControlDrawer()
    events = []
    drawer.on_control = lambda key, value: events.append((key, value))
    drawer.build_controls(SCENE_CONFIG)
    assert drawer.control_values == {"state": "2s", "mode": "Averaged", "kappa": 3.0}

    def walk(widget):
        yield widget
        for child in widget.children:
            yield from walk(child)

    widgets = list(walk(drawer.ids.controls_box))
    spinner = next(w for w in widgets if getattr(w, "values", None) == ["1s", "2s", "2p"])
    segments = {w.text: w for w in widgets if isinstance(w, ToggleButton)}
    slider = next(w for w in widgets if isinstance(w, Slider))
    button = next(w for w in widgets if isinstance(w, Button)
                  and not isinstance(w, ToggleButton) and w.text == "Reset camera")

    assert segments["Averaged"].state == "down"
    spinner.text = "2p"
    segments["Collapse"].state = "down"
    slider.value = 7.3
    button.dispatch("on_release")

    assert events == [("state", "2p"), ("mode", "Collapse"),
                      ("kappa", pytest.approx(7.5)), ("reset_camera", None)]
    assert segments["Averaged"].state == "normal", "segmented options are not exclusive"
    assert drawer.control_values == {"state": "2p", "mode": "Collapse",
                                     "kappa": pytest.approx(7.5)}


# ── Fbo-backed placeholder view ───────────────────────────────────────────────


def test_solid_colour_view_renders_through_its_fbo(gl_window):
    import numpy as np

    from periodica_app.views.fbo_view import SolidColourView

    view = SolidColourView(size=(64, 32), render_scale=0.5, colour=(0.2, 0.4, 0.6, 1.0))
    view.redraw()
    assert view.compile_error == ""
    assert tuple(view.fbo.size) == (32, 16)
    img = _rgba(view.fbo)
    assert (img == np.array([51, 102, 153, 255], np.uint8)).all()

    view.colour = (1.0, 0.0, 0.0, 1.0)
    view.redraw()
    assert (_rgba(view.fbo)[0, 0] == [255, 0, 0, 255]).all()

    view.size = (40, 40)
    view.render_scale = 1.0
    view.redraw()
    assert tuple(view.fbo.size) == (40, 40)
    assert (_rgba(view.fbo)[39, 39] == [255, 0, 0, 255]).all()


def test_broken_fragment_source_keeps_the_last_good_program(gl_window):
    from periodica_app.views.fbo_view import SolidColourView

    view = SolidColourView(size=(8, 8), colour=(0.0, 1.0, 0.0, 1.0))
    view.redraw()
    view.fragment_source = "void main(void) { gl_FragColor = vec4(undefined_name); }"
    assert view.compile_error, "a failed compile must be reported"
    view.redraw()
    assert (_rgba(view.fbo)[4, 4] == [0, 255, 0, 255]).all()


# ── SceneScreen frame loop ──────────────────────────────────────────────────


def test_scene_screen_frame_loop_drives_its_view(gl_window):
    from periodica_app.screens.scene_screen import SceneScreen
    from periodica_app.views.fbo_view import SolidColourView

    screen = SceneScreen()
    assert isinstance(screen.view, SolidColourView)
    assert screen.ids.control_drawer.control_values == {"render_scale": 1.0}

    screen.dispatch("on_enter")
    _pump(seconds=0.25)
    frames = screen.frame_loop.frames
    assert frames > 0 and screen.view.time > 0.0

    screen.dispatch("on_leave")
    _pump(seconds=0.1)
    assert screen.frame_loop.frames == frames, "loop kept running after on_leave"

    screen.on_control_change("render_scale", 0.5)
    assert screen.view.render_scale == 0.5


# ── whole app ───────────────────────────────────────────────────────────────


def test_app_starts_on_the_quarks_screen_and_exits_cleanly():
    """Launch the real app in a subprocess (hidden window) and stop it once the
    quarks screen has data.

    Two hidden-window workarounds: pin the metrics density (0 otherwise) and
    drop the Windows wm_pen / wm_touch input providers, whose stop() raises a
    ctypes ArgumentError when the window was never shown.
    """
    script = textwrap.dedent("""
        import os
        os.environ.setdefault("KIVY_NO_ARGS", "1")
        os.environ.setdefault("KIVY_METRICS_DENSITY", "1")
        from kivy.config import Config
        Config.set("graphics", "window_state", "hidden")
        for provider in ("wm_pen", "wm_touch"):
            if Config.has_option("input", provider):
                Config.remove_option("input", provider)
        from kivy.clock import Clock
        from periodica_app.app import PeriodicaApp

        app = PeriodicaApp()
        report = {"current": None, "items": 0, "waited": 0.0}

        def poll(dt):
            report["waited"] += dt
            sm = app.root.ids.screen_manager
            report["current"] = sm.current
            report["items"] = len(sm.current_screen.ids.canvas_view.items)
            if report["items"] or report["waited"] > 20.0:
                app.stop()
                return False

        app.bind(on_start=lambda *_: Clock.schedule_interval(poll, 0.25))
        app.run()
        print("REPORT", report["current"], report["items"])
    """)
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                          text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("REPORT"))
    _, current, items = line.split()
    assert current == "quarks" and int(items) >= 12
