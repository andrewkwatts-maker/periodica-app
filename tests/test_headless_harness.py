"""Tier-A contract: the shell's modules import without a GL context.

Importing ``kivy.core.window`` creates the window.  Any module the tier-A
suite touches must therefore keep that import lazy (inside the function that
needs a window), or headless CI cannot even import it.
"""
from __future__ import annotations

import importlib
import sys

import pytest

from conftest import WINDOW_MODULE, WindowImportGuard, gpu_tests_selected

HEADLESS_MODULES = [
    "periodica_app.theme",
    "periodica_app.utils.color_utils",
    "periodica_app.renderers.base_renderer",
    "periodica_app.renderers.quark_renderers",
    "periodica_app.widgets.canvas_view",
    "periodica_app.widgets.control_specs",
    "periodica_app.widgets.control_drawer",
    "periodica_app.widgets.info_sheet",
    "periodica_app.views.camera_controller",
    "periodica_app.views.frame_loop",
    "periodica_app.views.glsl",
    "periodica_app.views.fbo_view",
    "periodica_app.screens.shell_screen",
    "periodica_app.screens.base_screen",
    "periodica_app.screens.quarks_screen",
    "periodica_app.screens.scene_screen",
]


@pytest.mark.parametrize("module", HEADLESS_MODULES)
def test_module_imports_without_creating_a_window(module, request):
    if gpu_tests_selected(request.config.getoption("markexpr")):
        pytest.skip("tier B selected: a window may legitimately exist")
    importlib.import_module(module)
    assert WINDOW_MODULE not in sys.modules, f"{module} pulled in {WINDOW_MODULE}"


def test_window_guard_refuses_only_the_window_module():
    guard = WindowImportGuard()
    with pytest.raises(ImportError, match="pytest.mark.gpu"):
        guard.find_spec(WINDOW_MODULE)
    assert guard.find_spec("kivy.core.text") is None
    assert guard.find_spec("kivy.graphics") is None


@pytest.mark.parametrize(
    ("markexpr", "env", "expected"),
    [
        ("", {}, False),
        ("gpu", {}, True),
        ("gpu or slow", {}, True),
        ("not gpu", {}, False),
        ("not  gpu and slow", {}, False),
        ("", {"PERIODICA_APP_GPU": "1"}, True),
        ("", {"PERIODICA_APP_GPU": "0"}, False),
    ],
)
def test_gpu_tier_is_opt_in(markexpr, env, expected):
    assert gpu_tests_selected(markexpr, env) is expected
