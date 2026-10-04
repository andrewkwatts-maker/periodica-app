"""Tier A: FrameLoop lifecycle against a fake scheduler, and the SceneScreen
lifecycle hooks that drive it (no window, no Kivy event loop)."""
from __future__ import annotations

import pytest

from periodica_app.views.frame_loop import FrameLoop


class FakeEvent:
    def __init__(self, clock, callback, interval):
        self.clock, self.callback, self.interval = clock, callback, interval
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
        self.clock.events.remove(self)


class FakeClock:
    def __init__(self):
        self.events = []

    def schedule_interval(self, callback, interval):
        event = FakeEvent(self, callback, interval)
        self.events.append(event)
        return event

    def advance(self, frames=1):
        for _ in range(frames):
            for event in list(self.events):
                event.callback(event.interval)


@pytest.fixture
def clock():
    return FakeClock()


def test_start_schedules_once_at_the_target_rate(clock):
    seen = []
    loop = FrameLoop(seen.append, fps=50.0, scheduler=clock)
    loop.start()
    loop.start()  # idempotent
    assert len(clock.events) == 1 and clock.events[0].interval == pytest.approx(0.02)
    clock.advance(3)
    assert seen == [pytest.approx(0.02)] * 3 and loop.frames == 3


def test_stop_cancels_and_is_idempotent(clock):
    loop = FrameLoop(lambda dt: None, scheduler=clock)
    loop.start()
    loop.stop()
    loop.stop()
    assert not loop.running and clock.events == []


def test_pause_and_resume_round_trip(clock):
    loop = FrameLoop(lambda dt: None, scheduler=clock)
    loop.start()
    loop.pause()
    assert not loop.running and loop.paused
    clock.advance(5)
    assert loop.frames == 0
    loop.resume()
    assert loop.running and not loop.paused
    clock.advance(2)
    assert loop.frames == 2


def test_resume_does_not_revive_a_stopped_loop(clock):
    loop = FrameLoop(lambda dt: None, scheduler=clock)
    loop.start()
    loop.stop()
    loop.resume()
    assert not loop.running


def test_pause_of_a_stopped_loop_is_a_no_op(clock):
    loop = FrameLoop(lambda dt: None, scheduler=clock)
    loop.pause()
    loop.resume()
    assert not loop.running and not loop.paused


def test_invalid_rate_is_rejected():
    with pytest.raises(ValueError):
        FrameLoop(lambda dt: None, fps=0.0)


def test_module_imports_no_kivy():
    """The default scheduler (Kivy's Clock) is imported only on first start."""
    import subprocess
    import sys

    code = ("import sys, periodica_app.views.frame_loop; "
            "bad = [m for m in sys.modules if m == 'kivy' or m.startswith('kivy.')]; "
            "print(bad); sys.exit(1 if bad else 0)")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── SceneScreen lifecycle hooks (pure logic, no widget tree) ────────────────


class FakeApp:
    def __init__(self):
        self.bound = {}

    def bind(self, **handlers):
        self.bound.update(handlers)

    def unbind(self, **handlers):
        for name in handlers:
            self.bound.pop(name, None)


def _bare_scene_screen(clock):
    from periodica_app.screens.scene_screen import SceneScreen

    screen = SceneScreen.__new__(SceneScreen)  # skip the widget tree
    screen._app = None
    screen.frame_loop = FrameLoop(lambda dt: None, scheduler=clock)
    return screen


def test_scene_screen_runs_its_loop_only_while_shown(clock, monkeypatch):
    from periodica_app.screens import scene_screen

    app = FakeApp()
    monkeypatch.setattr(scene_screen.App, "get_running_app", staticmethod(lambda: app))
    screen = _bare_scene_screen(clock)

    screen.on_enter()
    assert screen.frame_loop.running
    assert set(app.bound) == {"on_pause", "on_resume"}

    app.bound["on_pause"](app)
    assert not screen.frame_loop.running and screen.frame_loop.paused
    assert app.bound["on_resume"](app) is None  # never swallows the event
    assert screen.frame_loop.running

    screen.on_leave()
    assert not screen.frame_loop.running
    app.bound["on_resume"](app)
    assert not screen.frame_loop.running, "app resume revived a screen that was left"


def test_scene_screen_pause_handler_lets_app_on_pause_run(clock, monkeypatch):
    """A True return from a bound handler would stop the dispatch before
    App.on_pause, whose True is what permits pausing at all."""
    from periodica_app.screens import scene_screen

    app = FakeApp()
    monkeypatch.setattr(scene_screen.App, "get_running_app", staticmethod(lambda: app))
    screen = _bare_scene_screen(clock)
    screen.on_enter()
    assert app.bound["on_pause"](app) is None


def test_scene_screen_without_an_app_still_runs(clock, monkeypatch):
    from periodica_app.screens import scene_screen

    monkeypatch.setattr(scene_screen.App, "get_running_app", staticmethod(lambda: None))
    screen = _bare_scene_screen(clock)
    screen.on_enter()
    assert screen.frame_loop.running
    screen.on_leave()
    assert not screen.frame_loop.running
