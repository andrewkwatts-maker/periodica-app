"""
Biomaterial Creation Dialog
Dialog for creating custom biological materials from cells and ECM components.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QComboBox, QTextEdit, QWidget,
    QMessageBox, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QDoubleSpinBox, QSlider
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import json
import math
from pathlib import Path
from typing import Dict

from periodica_app.ui.theme_constants import ThemeColors


# ECM component properties (modulus in MPa)
ECM_COMPONENTS = {
    'collagen_i': {'name': 'Collagen Type I', 'modulus': 1200, 'color': '#E3D5CA'},
    'collagen_ii': {'name': 'Collagen Type II', 'modulus': 10, 'color': '#D5E3CA'},
    'collagen_iii': {'name': 'Collagen Type III', 'modulus': 500, 'color': '#CAE3D5'},
    'collagen_iv': {'name': 'Collagen Type IV', 'modulus': 50, 'color': '#CAD5E3'},
    'elastin': {'name': 'Elastin', 'modulus': 0.6, 'color': '#E3CACA'},
    'proteoglycans': {'name': 'Proteoglycans', 'modulus': 0.001, 'color': '#CACAE3'},
    'hyaluronan': {'name': 'Hyaluronic Acid', 'modulus': 0.0001, 'color': '#E3E3CA'},
    'fibronectin': {'name': 'Fibronectin', 'modulus': 100, 'color': '#D5CAE3'},
    'laminin': {'name': 'Laminin', 'modulus': 50, 'color': '#E3CAD5'},
    'hydroxyapatite': {'name': 'Hydroxyapatite', 'modulus': 80000, 'color': '#FFFFFF'},
    'water': {'name': 'Water', 'modulus': 0.0, 'color': '#ADD8E6'},
}

# Tissue type presets
TISSUE_PRESETS = {
    'Cartilage': {
        'collagen_ii': 0.15, 'proteoglycans': 0.10, 'hyaluronan': 0.02, 'water': 0.70
    },
    'Tendon': {
        'collagen_i': 0.75, 'elastin': 0.02, 'proteoglycans': 0.02, 'water': 0.18
    },
    'Skin': {
        'collagen_i': 0.25, 'collagen_iii': 0.10, 'elastin': 0.04, 'water': 0.55
    },
    'Bone': {
        'hydroxyapatite': 0.45, 'collagen_i': 0.35, 'water': 0.10
    },
    'Muscle': {
        'collagen_i': 0.02, 'collagen_iii': 0.02, 'laminin': 0.01, 'water': 0.75
    },
}


class ECMSliderWidget(QWidget):
    """Widget for adjusting ECM component fraction."""
    value_changed = Signal(str, float)

    def __init__(self, comp_key: str, comp_info: dict, parent=None):
        super().__init__(parent)
        self.comp_key = comp_key
        self.comp_info = comp_info

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # Color indicator
        color_label = QLabel("●")
        color_label.setStyleSheet(f"color: {comp_info['color']}; font-size: 16px;")
        layout.addWidget(color_label)

        # Name label
        name_label = QLabel(comp_info['name'])
        name_label.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY}; min-width: 120px;")
        layout.addWidget(name_label)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {ThemeColors.BG_MEDIUM};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {comp_info['color']};
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
        """)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider, 1)

        # Value label
        self.value_label = QLabel("0%")
        self.value_label.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY}; min-width: 40px;")
        layout.addWidget(self.value_label)

    def _on_value_changed(self, value):
        self.value_label.setText(f"{value}%")
        self.value_changed.emit(self.comp_key, value / 100.0)

    def set_value(self, value: float):
        self.slider.setValue(int(value * 100))

    def get_value(self) -> float:
        return self.slider.value() / 100.0


class BiomaterialCreationDialog(QDialog):
    """Dialog for creating biological materials from ECM components."""
    biomaterial_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Biological Material from ECM")
        self.setMinimumSize(950, 750)
        self.ecm_sliders = {}
        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Build Biological Material from ECM Components")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #66BB6A;")
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Input
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Tissue presets
        preset_group = QGroupBox("Tissue Type Presets")
        preset_group.setStyleSheet(self._get_group_style())
        preset_layout = QHBoxLayout(preset_group)

        for name in TISSUE_PRESETS.keys():
            btn = QPushButton(name)
            btn.setStyleSheet(self._get_button_style())
            btn.clicked.connect(lambda checked, n=name: self._set_preset(n))
            preset_layout.addWidget(btn)

        left_layout.addWidget(preset_group)

        # ECM composition sliders
        ecm_group = QGroupBox("ECM Composition (fractions must sum to ≤1.0)")
        ecm_group.setStyleSheet(self._get_group_style())
        ecm_layout = QVBoxLayout(ecm_group)

        for comp_key, comp_info in ECM_COMPONENTS.items():
            slider_widget = ECMSliderWidget(comp_key, comp_info)
            slider_widget.value_changed.connect(self._on_ecm_changed)
            self.ecm_sliders[comp_key] = slider_widget
            ecm_layout.addWidget(slider_widget)

        # Total indicator
        self.total_label = QLabel("Total: 0%")
        self.total_label.setStyleSheet("color: #66BB6A; font-weight: bold; margin-top: 10px;")
        ecm_layout.addWidget(self.total_label)

        left_layout.addWidget(ecm_group)

        # Material settings
        settings_group = QGroupBox("Material Settings")
        settings_group.setStyleSheet(self._get_group_style())
        settings_layout = QGridLayout(settings_group)

        name_label = QLabel("Name:")
        settings_layout.addWidget(name_label, 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Custom Cartilage")
        self.name_edit.setStyleSheet(self._get_input_style())
        self.name_edit.textChanged.connect(self.update_preview)
        settings_layout.addWidget(self.name_edit, 0, 1)

        type_label = QLabel("Tissue Type:")
        settings_layout.addWidget(type_label, 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "cartilage", "tendon", "ligament", "bone_cortical", "bone_trabecular",
            "muscle_skeletal", "muscle_cardiac", "skin", "liver", "lung",
            "brain_gray", "brain_white", "adipose", "blood"
        ])
        self.type_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(self.type_combo, 1, 1)

        organ_label = QLabel("Organ System:")
        settings_layout.addWidget(organ_label, 2, 0)
        self.organ_combo = QComboBox()
        self.organ_combo.addItems([
            "skeletal", "muscular", "cardiovascular", "nervous",
            "digestive", "respiratory", "integumentary", "endocrine"
        ])
        self.organ_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(self.organ_combo, 2, 1)

        porosity_label = QLabel("Porosity:")
        settings_layout.addWidget(porosity_label, 3, 0)
        self.porosity_spin = QDoubleSpinBox()
        self.porosity_spin.setRange(0, 1)
        self.porosity_spin.setDecimals(2)
        self.porosity_spin.setSingleStep(0.05)
        self.porosity_spin.setValue(0.0)
        self.porosity_spin.setStyleSheet(self._get_spin_style())
        self.porosity_spin.valueChanged.connect(self.update_preview)
        settings_layout.addWidget(self.porosity_spin, 3, 1)

        left_layout.addWidget(settings_group)
        left_layout.addStretch()

        splitter.addWidget(left_panel)

        # Right panel - Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Composition summary
        comp_group = QGroupBox("Composition Summary")
        comp_group.setStyleSheet(self._get_group_style())
        comp_layout = QVBoxLayout(comp_group)

        self.comp_text = QTextEdit()
        self.comp_text.setReadOnly(True)
        self.comp_text.setMaximumHeight(150)
        self.comp_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(40, 40, 60, 200);
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                font-family: monospace;
                font-size: 10px;
            }}
        """)
        comp_layout.addWidget(self.comp_text)

        right_layout.addWidget(comp_group)

        # Mechanical properties
        mech_group = QGroupBox("Mechanical Properties")
        mech_group.setStyleSheet(self._get_group_style())
        mech_layout = QVBoxLayout(mech_group)

        self.mech_text = QTextEdit()
        self.mech_text.setReadOnly(True)
        self.mech_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(40, 40, 60, 200);
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                font-size: 11px;
            }}
        """)
        mech_layout.addWidget(self.mech_text)

        right_layout.addWidget(mech_group)

        # Stiffness category
        stiff_group = QGroupBox("Stiffness Classification")
        stiff_group.setStyleSheet(self._get_group_style())
        stiff_layout = QVBoxLayout(stiff_group)

        self.stiff_label = QLabel("")
        self.stiff_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.stiff_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stiff_layout.addWidget(self.stiff_label)

        self.stiff_desc = QLabel("")
        self.stiff_desc.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-size: 11px;")
        self.stiff_desc.setWordWrap(True)
        stiff_layout.addWidget(self.stiff_desc)

        right_layout.addWidget(stiff_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([500, 450])

        layout.addWidget(splitter)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._get_button_style())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("Create Biomaterial")
        create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #66BB6A, stop:1 #43A047);
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #43A047, stop:1 #66BB6A);
            }
        """)
        create_btn.clicked.connect(self.create_biomaterial)
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)

    def _set_preset(self, preset_name: str):
        """Set ECM composition from a preset."""
        # Reset all sliders
        for slider in self.ecm_sliders.values():
            slider.set_value(0)

        # Set preset values
        preset = TISSUE_PRESETS[preset_name]
        for comp_key, value in preset.items():
            if comp_key in self.ecm_sliders:
                self.ecm_sliders[comp_key].set_value(value)

        self.update_preview()

    def _on_ecm_changed(self, comp_key: str, value: float):
        """Handle ECM slider change."""
        self.update_preview()

    def update_preview(self):
        """Update preview panels."""
        # Get current composition
        composition = {}
        total = 0
        for comp_key, slider in self.ecm_sliders.items():
            value = slider.get_value()
            if value > 0:
                composition[comp_key] = value
                total += value

        # Update total label
        if total > 1.0:
            self.total_label.setStyleSheet("color: #F44336; font-weight: bold; margin-top: 10px;")
            self.total_label.setText(f"Total: {total*100:.1f}% (exceeds 100%!)")
        else:
            self.total_label.setStyleSheet("color: #66BB6A; font-weight: bold; margin-top: 10px;")
            self.total_label.setText(f"Total: {total*100:.1f}%")

        if not composition:
            self.comp_text.setText("Adjust sliders to add ECM components")
            self.mech_text.setText("Add components to calculate properties")
            self.stiff_label.setText("")
            self.stiff_desc.setText("")
            return

        # Composition summary
        comp_lines = []
        for comp_key, value in sorted(composition.items(), key=lambda x: -x[1]):
            comp_info = ECM_COMPONENTS[comp_key]
            comp_lines.append(f"{comp_info['name']}: {value*100:.1f}%")
        self.comp_text.setText("\n".join(comp_lines))

        # Calculate mechanical properties
        props = self._calculate_properties(composition)
        E = props['youngs_modulus']

        if E >= 1000:
            E_str = f"{E/1000:.2f} GPa"
        elif E >= 1:
            E_str = f"{E:.2f} MPa"
        else:
            E_str = f"{E*1000:.2f} kPa"

        mech_text = f"""
Young's Modulus (E): {E_str}
Voigt Bound: {props['voigt_bound']:.4f} MPa
Reuss Bound: {props['reuss_bound']:.4f} MPa
Effective Density: {props['density']:.2f} g/cm³
Porosity Effect: {(1-self.porosity_spin.value())*100:.0f}% solid
        """.strip()
        self.mech_text.setText(mech_text)

        # Stiffness classification
        category, color, description = self._classify_stiffness(E)
        self.stiff_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
        self.stiff_label.setText(category)
        self.stiff_desc.setText(description)

    def _calculate_properties(self, composition: dict) -> dict:
        """Calculate mechanical properties using Voigt-Reuss bounds."""
        if not composition:
            return {'youngs_modulus': 0, 'voigt_bound': 0, 'reuss_bound': 0, 'density': 1.0}

        # Normalize fractions
        total = sum(composition.values())
        if total == 0:
            total = 1

        normalized = {k: v/total for k, v in composition.items()}

        # Voigt bound (upper, iso-strain)
        voigt = sum(
            normalized[k] * ECM_COMPONENTS[k]['modulus']
            for k in normalized
        )

        # Reuss bound (lower, iso-stress)
        reuss_inv = sum(
            normalized[k] / max(ECM_COMPONENTS[k]['modulus'], 0.0001)
            for k in normalized
        )
        reuss = 1.0 / reuss_inv if reuss_inv > 0 else 0

        # Average (Hill average)
        E = (voigt + reuss) / 2

        # Apply porosity correction
        porosity = self.porosity_spin.value()
        E = E * (1 - porosity) ** 2

        # Estimate density
        density = 1.1 * (1 - porosity)  # Simplified

        return {
            'youngs_modulus': E,
            'voigt_bound': voigt,
            'reuss_bound': reuss,
            'density': density
        }

    def _classify_stiffness(self, E: float) -> tuple:
        """Classify stiffness and return category, color, and description."""
        if E < 0.01:
            return ("Ultra-Soft", "#64B5F6",
                   "Gel-like tissue (brain, adipose). High water content, minimal ECM structure.")
        elif E < 0.1:
            return ("Very Soft", "#4DD0E1",
                   "Soft parenchyma (liver, lung). Cellular with loose ECM network.")
        elif E < 1:
            return ("Soft", "#4DB6AC",
                   "Soft connective tissue (muscle). Organized ECM with elastic properties.")
        elif E < 10:
            return ("Medium", "#81C784",
                   "Dense connective tissue (skin). Well-organized collagen network.")
        elif E < 100:
            return ("Firm", "#AED581",
                   "Fibrous tissue (ligament, tendon). Highly aligned collagen fibers.")
        elif E < 1000:
            return ("Stiff", "#FFB74D",
                   "Calcified tissue (cartilage). Mineralization begins.")
        elif E < 10000:
            return ("Hard", "#FF8A65",
                   "Bone-like tissue. Significant mineral content.")
        else:
            return ("Rigid", "#BDBDBD",
                   "Fully mineralized (cortical bone). High hydroxyapatite content.")

    def create_biomaterial(self):
        """Create the biomaterial and emit signal."""
        name = self.name_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Name Required",
                              "Please enter a name for the biomaterial.")
            return

        # Get composition
        composition = {}
        for comp_key, slider in self.ecm_sliders.items():
            value = slider.get_value()
            if value > 0:
                composition[comp_key] = value

        if not composition:
            QMessageBox.warning(self, "Composition Required",
                              "Please add at least one ECM component.")
            return

        props = self._calculate_properties(composition)
        category, _, _ = self._classify_stiffness(props['youngs_modulus'])

        biomaterial_data = {
            'name': name,
            'type': self.type_combo.currentText(),
            'organ_system': self.organ_combo.currentText(),
            'ecm_composition': composition,
            'porosity': self.porosity_spin.value(),
            'mechanical_properties': {
                'youngs_modulus_MPa': props['youngs_modulus'],
                'voigt_bound_MPa': props['voigt_bound'],
                'reuss_bound_MPa': props['reuss_bound']
            },
            'physical_properties': {
                'density_g_cm3': props['density']
            },
            'derived_properties': {
                'stiffness_category': category.lower().replace('-', '_')
            },
            'is_custom': True
        }

        # Save to file
        materials_dir = Path(__file__).parent.parent / "data" / "active" / "biological_materials"
        materials_dir.mkdir(parents=True, exist_ok=True)

        filename = name.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        filepath = materials_dir / f"{filename}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(biomaterial_data, f, indent=2)

        self.biomaterial_created.emit(biomaterial_data)
        self.accept()

    def _get_group_style(self):
        return f"""
            QGroupBox {{
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """

    def _get_button_style(self):
        return f"""
            QPushButton {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background: {ThemeColors.ACCENT};
                border-color: {ThemeColors.ACCENT};
            }}
        """

    def _get_input_style(self):
        return f"""
            QLineEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 8px;
            }}
        """

    def _get_combo_style(self):
        return f"""
            QComboBox {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 5px 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {ThemeColors.BG_DARK};
                color: {ThemeColors.TEXT_PRIMARY};
                selection-background-color: {ThemeColors.ACCENT};
            }}
        """

    def _get_spin_style(self):
        return f"""
            QDoubleSpinBox {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 5px;
            }}
        """
