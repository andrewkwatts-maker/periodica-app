"""
Predictor Settings Dialog
Provides UI controls for configuring biological predictor parameters.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QDoubleSpinBox, QComboBox, QGroupBox,
                                QPushButton, QTabWidget, QWidget, QFormLayout,
                                QCheckBox, QSpinBox, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, Signal

from periodica_app.ui.theme_constants import ThemeColors


class PredictorSettingsDialog(QDialog):
    """Dialog for configuring biological predictor parameters."""

    settings_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Predictor Settings")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Tab widget for different predictor categories
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_cell_settings(), "Cell Predictor")
        self.tabs.addTab(self._create_biomaterial_settings(), "Biomaterial")
        self.tabs.addTab(self._create_nucleic_acid_settings(), "Nucleic Acid")
        self.tabs.addTab(self._create_protein_settings(), "Protein")
        layout.addWidget(self.tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(self.reset_btn)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._apply_settings)
        btn_layout.addWidget(self.apply_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._ok_clicked)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _create_cell_settings(self) -> QWidget:
        """Create cell predictor settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Kleiber's Law parameters
        kleiber_group = QGroupBox("Kleiber's Law Parameters")
        form = QFormLayout(kleiber_group)

        self.b0_spin = QDoubleSpinBox()
        self.b0_spin.setDecimals(15)
        self.b0_spin.setRange(1e-15, 1e-9)
        self.b0_spin.setValue(3.5e-12)
        self.b0_spin.setSingleStep(1e-13)
        form.addRow("B₀ (metabolic coefficient, W):", self.b0_spin)

        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setDecimals(3)
        self.alpha_spin.setRange(0.5, 1.0)
        self.alpha_spin.setValue(0.75)
        self.alpha_spin.setSingleStep(0.01)
        form.addRow("α (scaling exponent):", self.alpha_spin)

        layout.addWidget(kleiber_group)

        # Temperature settings
        temp_group = QGroupBox("Temperature Settings")
        temp_form = QFormLayout(temp_group)

        self.ref_temp_spin = QSpinBox()
        self.ref_temp_spin.setRange(0, 50)
        self.ref_temp_spin.setValue(37)
        self.ref_temp_spin.setSuffix(" °C")
        temp_form.addRow("Reference temperature:", self.ref_temp_spin)

        self.temp_correction_check = QCheckBox("Enable Arrhenius temperature correction")
        self.temp_correction_check.setChecked(True)
        temp_form.addRow(self.temp_correction_check)

        layout.addWidget(temp_group)

        # Physical constants
        const_group = QGroupBox("Physical Constants")
        const_form = QFormLayout(const_group)

        self.cell_density_spin = QDoubleSpinBox()
        self.cell_density_spin.setDecimals(3)
        self.cell_density_spin.setRange(0.9, 1.5)
        self.cell_density_spin.setValue(1.05)
        self.cell_density_spin.setSuffix(" g/cm³")
        const_form.addRow("Default cell density:", self.cell_density_spin)

        layout.addWidget(const_group)
        layout.addStretch()

        return widget

    def _create_biomaterial_settings(self) -> QWidget:
        """Create biomaterial predictor settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Porosity model
        porosity_group = QGroupBox("Porosity Model")
        porosity_form = QFormLayout(porosity_group)

        self.porosity_model_combo = QComboBox()
        self.porosity_model_combo.addItems([
            "Gibson-Ashby (n=2.0)",
            "Exponential (n=1.5)",
            "Linear (n=1.0)"
        ])
        porosity_form.addRow("Model:", self.porosity_model_combo)

        self.custom_exponent_spin = QDoubleSpinBox()
        self.custom_exponent_spin.setDecimals(2)
        self.custom_exponent_spin.setRange(0.5, 4.0)
        self.custom_exponent_spin.setValue(2.0)
        porosity_form.addRow("Custom exponent:", self.custom_exponent_spin)

        layout.addWidget(porosity_group)

        # Composite calculation model
        composite_group = QGroupBox("Composite Calculation")
        composite_form = QFormLayout(composite_group)

        self.composite_model_combo = QComboBox()
        self.composite_model_combo.addItems([
            "Voigt-Reuss Average",
            "Voigt (Upper Bound)",
            "Reuss (Lower Bound)",
            "Hashin-Shtrikman"
        ])
        composite_form.addRow("Modulus model:", self.composite_model_combo)

        layout.addWidget(composite_group)
        layout.addStretch()

        return widget

    def _create_nucleic_acid_settings(self) -> QWidget:
        """Create nucleic acid predictor settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Thermodynamic parameters
        thermo_group = QGroupBox("Default Concentrations")
        thermo_form = QFormLayout(thermo_group)

        self.na_conc_spin = QDoubleSpinBox()
        self.na_conc_spin.setDecimals(3)
        self.na_conc_spin.setRange(0.001, 2.0)
        self.na_conc_spin.setValue(0.050)
        self.na_conc_spin.setSuffix(" M")
        thermo_form.addRow("Na⁺ concentration:", self.na_conc_spin)

        self.mg_conc_spin = QDoubleSpinBox()
        self.mg_conc_spin.setDecimals(4)
        self.mg_conc_spin.setRange(0.0, 0.5)
        self.mg_conc_spin.setValue(0.0)
        self.mg_conc_spin.setSuffix(" M")
        thermo_form.addRow("Mg²⁺ concentration:", self.mg_conc_spin)

        self.oligo_conc_spin = QDoubleSpinBox()
        self.oligo_conc_spin.setDecimals(9)
        self.oligo_conc_spin.setRange(1e-12, 1e-3)
        self.oligo_conc_spin.setValue(0.25e-6)
        self.oligo_conc_spin.setSuffix(" M")
        thermo_form.addRow("Oligo concentration:", self.oligo_conc_spin)

        layout.addWidget(thermo_group)

        # Tm calculation method
        tm_group = QGroupBox("Tm Calculation")
        tm_form = QFormLayout(tm_group)

        self.tm_method_combo = QComboBox()
        self.tm_method_combo.addItems([
            "Nearest-Neighbor (SantaLucia 1998)",
            "GC Content Method",
            "Basic 4+2 Rule"
        ])
        tm_form.addRow("Method:", self.tm_method_combo)

        layout.addWidget(tm_group)
        layout.addStretch()

        return widget

    def _create_protein_settings(self) -> QWidget:
        """Create protein predictor settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Secondary structure prediction
        ss_group = QGroupBox("Secondary Structure Prediction")
        ss_form = QFormLayout(ss_group)

        self.ss_window_spin = QSpinBox()
        self.ss_window_spin.setRange(3, 15)
        self.ss_window_spin.setValue(6)
        ss_form.addRow("Window size:", self.ss_window_spin)

        self.helix_threshold_spin = QDoubleSpinBox()
        self.helix_threshold_spin.setDecimals(2)
        self.helix_threshold_spin.setRange(0.8, 1.5)
        self.helix_threshold_spin.setValue(1.03)
        ss_form.addRow("Helix threshold:", self.helix_threshold_spin)

        layout.addWidget(ss_group)

        # Disulfide bond prediction
        ds_group = QGroupBox("Disulfide Bond Prediction")
        ds_form = QFormLayout(ds_group)

        self.min_cys_distance_spin = QSpinBox()
        self.min_cys_distance_spin.setRange(1, 50)
        self.min_cys_distance_spin.setValue(10)
        ds_form.addRow("Min Cys distance:", self.min_cys_distance_spin)

        layout.addWidget(ds_group)

        # pI calculation
        pi_group = QGroupBox("pI Calculation")
        pi_form = QFormLayout(pi_group)

        self.pi_precision_spin = QSpinBox()
        self.pi_precision_spin.setRange(1, 4)
        self.pi_precision_spin.setValue(2)
        pi_form.addRow("Decimal precision:", self.pi_precision_spin)

        layout.addWidget(pi_group)
        layout.addStretch()

        return widget

    def _apply_styles(self):
        """Apply theme styles."""
        self.setStyleSheet(f"""
            QDialog {{
                background: {ThemeColors.BG_DARK};
                color: {ThemeColors.TEXT_PRIMARY};
            }}
            QTabWidget::pane {{
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                background: {ThemeColors.BG_MEDIUM};
            }}
            QTabBar::tab {{
                background: {ThemeColors.BG_DARK};
                color: {ThemeColors.TEXT_SECONDARY};
                padding: 8px 16px;
                border: 1px solid {ThemeColors.BORDER};
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            QTabBar::tab:selected {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
            }}
            QGroupBox {{
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {ThemeColors.TEXT_PRIMARY};
            }}
            QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {{
                background: {ThemeColors.BG_DARK};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 3px;
                padding: 5px;
            }}
            QCheckBox {{
                color: {ThemeColors.TEXT_PRIMARY};
            }}
            QPushButton {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {ThemeColors.ACCENT};
                border-color: {ThemeColors.ACCENT};
            }}
        """)

    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        # Cell settings
        self.b0_spin.setValue(3.5e-12)
        self.alpha_spin.setValue(0.75)
        self.ref_temp_spin.setValue(37)
        self.temp_correction_check.setChecked(True)
        self.cell_density_spin.setValue(1.05)

        # Biomaterial settings
        self.porosity_model_combo.setCurrentIndex(0)
        self.custom_exponent_spin.setValue(2.0)
        self.composite_model_combo.setCurrentIndex(0)

        # Nucleic acid settings
        self.na_conc_spin.setValue(0.050)
        self.mg_conc_spin.setValue(0.0)
        self.oligo_conc_spin.setValue(0.25e-6)
        self.tm_method_combo.setCurrentIndex(0)

        # Protein settings
        self.ss_window_spin.setValue(6)
        self.helix_threshold_spin.setValue(1.03)
        self.min_cys_distance_spin.setValue(10)
        self.pi_precision_spin.setValue(2)

    def get_settings(self) -> dict:
        """Get all current settings as a dictionary."""
        return {
            'cell': {
                'B0': self.b0_spin.value(),
                'ALPHA': self.alpha_spin.value(),
                'reference_temperature_C': self.ref_temp_spin.value(),
                'temperature_correction': self.temp_correction_check.isChecked(),
                'cell_density': self.cell_density_spin.value(),
            },
            'biomaterial': {
                'porosity_model': self.porosity_model_combo.currentText(),
                'custom_exponent': self.custom_exponent_spin.value(),
                'composite_model': self.composite_model_combo.currentText(),
            },
            'nucleic_acid': {
                'Na_concentration_M': self.na_conc_spin.value(),
                'Mg_concentration_M': self.mg_conc_spin.value(),
                'oligo_concentration_M': self.oligo_conc_spin.value(),
                'tm_method': self.tm_method_combo.currentText(),
            },
            'protein': {
                'ss_window_size': self.ss_window_spin.value(),
                'helix_threshold': self.helix_threshold_spin.value(),
                'min_cys_distance': self.min_cys_distance_spin.value(),
                'pI_precision': self.pi_precision_spin.value(),
            }
        }

    def set_settings(self, settings: dict):
        """Load settings from a dictionary."""
        if 'cell' in settings:
            cell = settings['cell']
            if 'B0' in cell:
                self.b0_spin.setValue(cell['B0'])
            if 'ALPHA' in cell:
                self.alpha_spin.setValue(cell['ALPHA'])
            if 'reference_temperature_C' in cell:
                self.ref_temp_spin.setValue(cell['reference_temperature_C'])
            if 'temperature_correction' in cell:
                self.temp_correction_check.setChecked(cell['temperature_correction'])
            if 'cell_density' in cell:
                self.cell_density_spin.setValue(cell['cell_density'])

        # Similar for other categories...

    def _apply_settings(self):
        """Apply current settings and emit signal."""
        self.settings_changed.emit(self.get_settings())

    def _ok_clicked(self):
        """Apply settings and close dialog."""
        self._apply_settings()
        self.accept()
