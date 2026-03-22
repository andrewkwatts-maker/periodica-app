# Periodica App

A scientific visualization application for exploring particle physics, atomic chemistry, molecular chemistry, materials science, alloy thermodynamics, and biological systems.

Built on the [periodica](https://pypi.org/project/periodica/) computation library with a PySide6 GUI.

## Installation

```bash
pip install periodica-app
```

## Quick Start

```bash
# From command line
periodica-app

# Or as a Python module
python -m periodica_app
```

## Features

- **12 interactive tabs**: Elements, Quarks, Subatomic Particles, Molecules, Alloys, Materials, Amino Acids, Proteins, Nucleic Acids, Cell Components, Cells, Biomaterials
- **35 layout modes**: Table, circular, spiral, linear, eightfold way, force network, and more
- **Property encoding**: Color-map any property across the visualization
- **Data editing**: Create, edit, and manage scientific data with built-in JSON editor
- **AI generation**: Generate new data entries using Gemini API integration
- **Derivation cascades**: Propagate changes through the full physics derivation chain
- **Spectroscopy**: Emission spectrum visualization for elements
- **SDF rendering**: Signed distance field particle visualization

## Architecture

This app depends on `periodica` for all scientific computation:

```
periodica-app (this package)     periodica (pip install periodica)
├── UI / visualization       ←── ├── Calculators
├── Layouts / rendering      ←── ├── Data loaders (627 JSON files)
├── Control panels           ←── ├── Predictors / derivation chains
└── Dialogs / editors        ←── └── Enums / constants
```

## License

Apache License 2.0
