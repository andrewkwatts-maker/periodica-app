# Periodica App

A desktop app for exploring the [periodica](https://pypi.org/project/periodica/)
scientific library, built with Kivy and KivyMD. It runs on Windows, macOS and
Linux. All the science (data, registries, layouts, calculators) comes from
`periodica`; this package only presents it.

> **Desktop only.** The Android/APK build (buildozer) was dropped on
> 2026-10-02. Mobile is not a supported target.

## Install and run

```bash
pip install periodica-app
periodica-app              # or: python -m periodica_app
```

## What is in it

- **Quarks:** the Standard Model and particle zoo. It offers eight layouts
  (Standard Model, circular, linear, alternative, force network, mass spiral,
  fermion/boson, charge vs mass). Fill, border, glow and sort can each encode
  any property, colour ranges follow the data, and there are toggles for
  antiparticles, composites and force lines. Tap a particle for details.
- **Coming next:** the other domains listed in the navigation panel (Subatomic,
  Atoms, Molecules, Alloys, Materials, Amino Acids, Proteins, Nucleic Acids,
  Cell Components, Cells, Biomaterials). These are greyed out until their
  screen is registered. Also planned: a physically accurate, in-house 3-D
  renderer for atomic orbitals and molecules, using GPU ray marching of
  hydrogen-like and Hartree–Fock densities.

## Architecture

```
periodica-app (this package)                periodica (pip install periodica)
├── app.py      MDApp shell + domain registry
├── screens/    DomainScreen = config + view ←── data registry, quark loader
├── renderers/  draw positioned items       ←── layout_math (positions)
└── widgets/    canvas, drawer, info sheet
```

A domain screen is configuration: layout modes mapped to renderers, the
properties to encode, toggles, and the info-panel layout. See
`src/periodica_app/screens/quarks_screen.py`.

## Development

```bash
pip install -e ".[dev]"   # editable install with pytest, ruff, pyinstaller

build.bat                 # Windows: ruff + headless tests
./build.sh                # macOS / Linux / Git Bash: the same
build.bat gpu             # ... plus GPU tests (needs a GL context)
build.bat exe             # ... plus a PyInstaller build in dist/PeriodicaApp/
```

There are two test tiers. The default **tier A** is pure logic and never opens
a window, so it runs on headless CI; the suite enforces this. **Tier B**
(`pytest -m gpu`) needs a GL context and runs in a hidden window.

`python tools/gl_spike.py --matrix` checks the GPU features the planned 3-D
renderer depends on. The results and Kivy pitfalls are written up in
[docs/dev/gl-spike.md](docs/dev/gl-spike.md).

## License

Apache License 2.0
