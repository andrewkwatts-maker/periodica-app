"""pytest configuration: test tiers and a headless Kivy environment.

Tier A (default)
    Pure logic, controllers and module imports.  Must never create a Kivy
    window, so it runs on headless CI.  This is enforced: while tier B is not
    selected, importing ``kivy.core.window`` raises ``ImportError`` naming the
    offending import, instead of silently opening a window on a developer
    machine and then failing on CI.

Tier B (``@pytest.mark.gpu``)
    Needs a real GL context (a hidden Kivy window).  Opt-in: run with
    ``pytest -m gpu`` (or set ``PERIODICA_APP_GPU=1``); otherwise these tests
    are reported as skipped.  Use the ``gl_window`` fixture.
"""
from __future__ import annotations

import os
import sys

# conftest is imported before any test module, so these take effect before
# the first ``import kivy``.
os.environ.setdefault("KIVY_NO_ARGS", "1")        # don't parse pytest's argv
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")  # keep Kivy's banner out of reports
os.environ.setdefault("KIVY_NO_FILELOG", "1")     # no ~/.kivy/logs file per run

import pytest  # noqa: E402

WINDOW_MODULE = "kivy.core.window"
GPU_ENV = "PERIODICA_APP_GPU"
_GPU_SELECTED = pytest.StashKey[bool]()


def gpu_tests_selected(markexpr: str, env: dict | None = None) -> bool:
    """True when the run opted into tier B (``-m gpu`` or ``PERIODICA_APP_GPU=1``)."""
    env = os.environ if env is None else env
    if env.get(GPU_ENV) == "1":
        return True
    compact = (markexpr or "").replace(" ", "")
    return "gpu" in compact and "notgpu" not in compact


class WindowImportGuard:
    """Meta-path finder that refuses ``kivy.core.window`` during tier-A runs."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname == WINDOW_MODULE:
            raise ImportError(
                "tier-A test imported kivy.core.window, which opens a window and "
                "fails on headless CI. Import it lazily inside the code that needs "
                "it, or mark the test @pytest.mark.gpu."
            )
        return None


def pytest_configure(config):
    selected = gpu_tests_selected(config.getoption("markexpr"))
    config.stash[_GPU_SELECTED] = selected
    if selected:
        # Must happen before anything imports kivy.core.window.
        from kivy.config import Config

        Config.set("graphics", "window_state", "hidden")
    elif WINDOW_MODULE not in sys.modules:
        sys.meta_path.insert(0, WindowImportGuard())


def pytest_collection_modifyitems(config, items):
    if config.stash[_GPU_SELECTED]:
        return
    skip = pytest.mark.skip(reason="tier B (needs a GL context): run with -m gpu")
    for item in items:
        if "gpu" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def gl_window():
    """The (hidden) Kivy window, i.e. a live GL context.  Tier B only."""
    from kivy.core.window import Window

    return Window
