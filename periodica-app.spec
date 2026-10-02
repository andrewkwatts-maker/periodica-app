# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the periodica-app desktop build (one-folder).

    build.bat exe        (Windows)    or    ./build.sh exe
    python -m PyInstaller --noconfirm periodica-app.spec

Output: dist/PeriodicaApp/PeriodicaApp[.exe]
"""
import importlib
import importlib.util
import os
import sys

# Before the first kivy import: keep Kivy from taking over the root logger
# (in its default mode it re-emits PyInstaller's TRACE records -- a
# multi-hundred-MB log and a build many times slower) and from parsing argv.
os.environ.setdefault("KIVY_LOG_MODE", "PYTHON")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
os.environ.setdefault("KIVY_NO_FILELOG", "1")
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.tools.packaging.pyinstaller_hooks import get_deps_minimal, hookspath, runtime_hooks  # noqa: E402
from PyInstaller.utils.hooks import collect_submodules  # noqa: E402

APP_NAME = "PeriodicaApp"

# Never needed at runtime.  metaphysica backs periodica's optional
# "simulated" quark source (periodica.data.quark_source falls back to the
# experimental data without it) and would drag in sympy and its simulations.
EXCLUDES = ["metaphysica", "pytest", "_pytest", "IPython", "tkinter"]

# periodica ships its datasheets inside the package (periodica/data).
periodica_pkg = importlib.import_module("periodica")
periodica_data = os.path.join(os.path.dirname(periodica_pkg.__file__), "data")

# KivyMD's PyInstaller hooks.  Located without importing kivymd, whose
# import creates a Kivy window.
kivymd_hooks = os.path.join(
    importlib.util.find_spec("kivymd").submodule_search_locations[0],
    "tools", "packaging", "pyinstaller",
)

# Kivy picks its window/text/image providers at runtime, so PyInstaller
# cannot see them; get_deps_minimal lists the ones this app uses.
kivy_deps = get_deps_minimal(video=None, audio=None, camera=None, spelling=None)

# SDL2 / GLEW / ANGLE DLLs come from the kivy_deps wheels on Windows.
dependency_trees = []
if sys.platform == "win32":
    from kivy_deps import angle, glew, sdl2

    dependency_trees = [Tree(path) for path in (*sdl2.dep_bins, *glew.dep_bins, *angle.dep_bins)]

a = Analysis(
    ["src/periodica_app/__main__.py"],
    pathex=["src"],
    binaries=kivy_deps["binaries"],
    datas=[
        (periodica_data, "periodica/data"),
        ("src/periodica_app/config", "periodica_app/config"),
    ],
    # Screens are created by lazy factories and periodica resolves some
    # modules dynamically, so collect both packages whole.
    hiddenimports=(
        kivy_deps["hiddenimports"]
        + collect_submodules("periodica")
        + collect_submodules("periodica_app")
    ),
    hookspath=hookspath() + [kivymd_hooks],
    hooksconfig={},
    runtime_hooks=runtime_hooks(),
    excludes=kivy_deps["excludes"] + EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    *dependency_trees,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
