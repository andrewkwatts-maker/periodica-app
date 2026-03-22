# Periodica App — GUI Application

Scientific visualization app published as `pip install periodica-app`.

## Architecture

- **src layout**: `src/periodica_app/` — all source lives here
- **Backend**: All scientific computation comes from `periodica` library (`pip install periodica`)
- **Frontend**: PySide6/Qt — 12 interactive tabs for all scientific domains
- **Entry point**: `periodica_app.main:main` → `PeriodicsMainWindow(QMainWindow)`

## Key Modules

| Module | Purpose |
|--------|---------|
| `periodica_app.main` | 3020-line QMainWindow with 12 tabs |
| `periodica_app.ui/` | 62 files — control panels, info panels, dialogs, editors |
| `periodica_app.layouts/` | 36 files — QPainter-based layout renderers |
| `periodica_app.core/` | 7 files — QWidget unified table views |
| `periodica_app.utils/` | 5 files — Qt-dependent utilities (calculations, SDF renderer, workers) |
| `periodica_app.constants` | UI/visualization constants |
| `periodica_app.config/` | API key management (Gemini, etc.) |

## Import Rules

```python
# Library imports (computation, data, enums)
from periodica.core.pt_enums import PTPropertyName
from periodica.data.data_manager import DataManager
from periodica.utils.physics_calculator import AtomCalculator

# App-internal imports (UI, rendering)
from periodica_app.ui.control_panel import ControlPanel
from periodica_app.layouts.base_layout import BaseLayoutRenderer
from periodica_app.utils.calculations import wavelength_to_qcolor
```

## Commands

```bash
# Install editable (pulls periodica + PySide6)
pip install -e .

# Run the app
python -m periodica_app
# or
periodica-app

# Build desktop exe
pyinstaller periodica-app.spec
```

## Related Repos

- **periodica**: Backend library (`pip install periodica`) — data, calculators, predictors
- **Periodics**: Original monorepo (sunset)

## Conventions

- Library code (`from periodica.`) for ALL computation — never duplicate physics/data logic here
- Qt-dependent code stays in this repo (QColor, QPainter, QThread, QWidget)
- Each domain tab has 3 components: unified_table (core/), control_panel (ui/), info_panel (ui/)
- Layouts accept position data from `periodica.layout_math` and render with QPainter
- Graceful degradation: tabs wrapped in try/except with HAS_*_TAB flags
