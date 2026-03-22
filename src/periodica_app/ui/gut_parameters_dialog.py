"""
GUT Parameters Dialog
======================
Editor for fundamental constants (quark masses, coupling constants).
Allows editing quark JSON values and triggering cascade regeneration.
"""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QDoubleSpinBox, QGridLayout, QMessageBox,
    QTextEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from periodica.utils.logger import get_logger

logger = get_logger('gut_parameters')

# PDG 2024 reference values (current quark masses in MeV/c^2)
_PDG_REFERENCE = {
    'u': {'mass_mev': 2.16, 'charge': 2/3, 'spin': 0.5, 'label': 'Up'},
    'd': {'mass_mev': 4.67, 'charge': -1/3, 'spin': 0.5, 'label': 'Down'},
    's': {'mass_mev': 93.4, 'charge': -1/3, 'spin': 0.5, 'label': 'Strange'},
    'c': {'mass_mev': 1270, 'charge': 2/3, 'spin': 0.5, 'label': 'Charm'},
    'b': {'mass_mev': 4180, 'charge': -1/3, 'spin': 0.5, 'label': 'Bottom'},
    't': {'mass_mev': 172760, 'charge': 2/3, 'spin': 0.5, 'label': 'Top'},
}

# Quark JSON file mapping
_QUARK_FILES = {
    'u': 'UpQuark.json',
    'd': 'DownQuark.json',
    's': 'StrangeQuark.json',
    'c': 'CharmQuark.json',
    'b': 'BottomQuark.json',
    't': 'TopQuark.json',
}


class GUTParametersDialog(QDialog):
    """Dialog for editing fundamental quark constants."""

    parameters_changed = Signal()  # emitted when quark values are saved

    def __init__(self, parent=None):
        super().__init__(parent)
        self._quark_dir = Path(__file__).parent.parent / 'data' / 'active' / 'quarks'
        self._spinboxes = {}
        self._original_values = {}

        self.setWindowTitle("GUT Parameters - Fundamental Constants")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Fundamental Quark Constants")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        desc = QLabel(
            "Edit quark masses to explore Grand Unified Theory parameters.\n"
            "Changes propagate through the entire derivation chain when you\n"
            "click 'Apply & Regenerate'."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Quark mass editors
        mass_group = QGroupBox("Quark Masses (MeV/c\u00b2)")
        mass_layout = QGridLayout(mass_group)

        mass_layout.addWidget(QLabel("Quark"), 0, 0)
        mass_layout.addWidget(QLabel("Current Mass"), 0, 1)
        mass_layout.addWidget(QLabel("PDG 2024"), 0, 2)
        mass_layout.addWidget(QLabel("Change"), 0, 3)

        for i, (flavor, ref) in enumerate(_PDG_REFERENCE.items()):
            row = i + 1
            mass_layout.addWidget(QLabel(f"{ref['label']} ({flavor})"), row, 0)

            spin = QDoubleSpinBox()
            spin.setDecimals(3 if ref['mass_mev'] < 100 else 1)
            spin.setRange(0.001, 500000)
            spin.setValue(ref['mass_mev'])
            spin.setSuffix(" MeV")
            spin.valueChanged.connect(self._on_value_changed)
            self._spinboxes[flavor] = spin
            mass_layout.addWidget(spin, row, 1)

            pdg_label = QLabel(f"{ref['mass_mev']}")
            pdg_label.setStyleSheet("color: gray;")
            mass_layout.addWidget(pdg_label, row, 2)

            change_label = QLabel("0%")
            change_label.setObjectName(f"change_{flavor}")
            mass_layout.addWidget(change_label, row, 3)

        layout.addWidget(mass_group)

        # Impact preview
        preview_group = QGroupBox("Impact Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(120)
        preview_layout.addWidget(self.preview_text)
        layout.addWidget(preview_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self.reset_btn = QPushButton("Reset to PDG 2024")
        self.reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.apply_btn = QPushButton("Apply & Regenerate")
        self.apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.apply_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _load_current_values(self):
        """Load current quark masses from JSON files."""
        for flavor, filename in _QUARK_FILES.items():
            filepath = self._quark_dir / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    mass = data.get('mass_mev', data.get('mass_MeV',
                           _PDG_REFERENCE[flavor]['mass_mev']))
                    self._spinboxes[flavor].setValue(mass)
                    self._original_values[flavor] = mass
                except Exception as e:
                    logger.warning(f"Could not load {filename}: {e}")
            else:
                self._original_values[flavor] = _PDG_REFERENCE[flavor]['mass_mev']

    def _on_value_changed(self):
        """Update change labels and impact preview when any value changes."""
        lines = []
        for flavor, ref in _PDG_REFERENCE.items():
            current = self._spinboxes[flavor].value()
            pdg = ref['mass_mev']
            pct = (current - pdg) / pdg * 100 if pdg > 0 else 0

            # Update change label
            change_label = self.findChild(QLabel, f"change_{flavor}")
            if change_label:
                sign = "+" if pct > 0 else ""
                change_label.setText(f"{sign}{pct:.1f}%")
                if abs(pct) > 10:
                    change_label.setStyleSheet("color: red;")
                elif abs(pct) > 1:
                    change_label.setStyleSheet("color: orange;")
                else:
                    change_label.setStyleSheet("color: green;")

            if abs(pct) > 0.01:
                lines.append(f"{ref['label']} quark: {pdg} -> {current:.3f} MeV ({sign}{pct:.1f}%)")

        if lines:
            # Estimate proton mass change
            u_mass = self._spinboxes['u'].value()
            d_mass = self._spinboxes['d'].value()
            # Proton = uud: constituent masses scale approximately
            proton_change = (u_mass - 2.16) * 2 + (d_mass - 4.67)
            lines.append(f"\nEstimated proton mass change: {proton_change:+.1f} MeV")
            lines.append(f"(Current proton mass: ~938.3 MeV)")

        self.preview_text.setPlainText('\n'.join(lines) if lines else "No changes from PDG values.")

    def _on_reset(self):
        """Reset all values to PDG 2024 reference."""
        for flavor, ref in _PDG_REFERENCE.items():
            self._spinboxes[flavor].setValue(ref['mass_mev'])

    def _on_apply(self):
        """Save quark values and trigger regeneration."""
        reply = QMessageBox.question(
            self, "Apply Changes",
            "This will update quark JSON files and trigger\n"
            "cascade regeneration of all derived data.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Save to JSON files
        for flavor, filename in _QUARK_FILES.items():
            filepath = self._quark_dir / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Update mass
                    new_mass = self._spinboxes[flavor].value()
                    if 'mass_mev' in data:
                        data['mass_mev'] = new_mass
                    if 'mass_MeV' in data:
                        data['mass_MeV'] = new_mass
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    logger.info(f"Updated {filename}: mass = {new_mass} MeV")
                except Exception as e:
                    logger.error(f"Failed to update {filename}: {e}")

        # Reload quark provider cache
        try:
            from periodica.utils.quark_constants import get_quark_provider
            get_quark_provider().reload()
        except Exception as e:
            logger.warning(f"Could not reload quark provider: {e}")

        self.parameters_changed.emit()
        self.accept()

    def get_current_values(self) -> dict:
        """Return current spinbox values as {flavor: mass_mev}."""
        return {f: self._spinboxes[f].value() for f in _PDG_REFERENCE}
