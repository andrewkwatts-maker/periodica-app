"""
Cell Creation Dialog
Dialog for creating custom cells from cell components.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QComboBox, QTextEdit, QWidget,
    QMessageBox, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import json
from pathlib import Path
from typing import Dict, List

from periodica_app.ui.theme_constants import ThemeColors


# Cell component types for selection
COMPONENT_TYPES = {
    'nucleus': {'name': 'Nucleus', 'base_volume': 500, 'required': True},
    'mitochondria': {'name': 'Mitochondria', 'base_volume': 0.5, 'per_unit': True},
    'ribosome': {'name': 'Ribosomes', 'base_volume': 0.00002, 'per_unit': True},
    'endoplasmic_reticulum': {'name': 'Endoplasmic Reticulum', 'base_volume': 200},
    'golgi': {'name': 'Golgi Apparatus', 'base_volume': 100},
    'lysosome': {'name': 'Lysosomes', 'base_volume': 0.5, 'per_unit': True},
    'peroxisome': {'name': 'Peroxisomes', 'base_volume': 0.1, 'per_unit': True},
    'cytoskeleton': {'name': 'Cytoskeleton', 'base_volume': 100},
}

# Cell types with typical compositions
CELL_PRESETS = {
    'Epithelial': {
        'mitochondria': 500, 'ribosome': 500000, 'nucleus': 1,
        'endoplasmic_reticulum': 1, 'golgi': 1, 'lysosome': 100
    },
    'Neuron': {
        'mitochondria': 2000, 'ribosome': 1000000, 'nucleus': 1,
        'endoplasmic_reticulum': 1, 'golgi': 1, 'lysosome': 50
    },
    'Muscle': {
        'mitochondria': 5000, 'ribosome': 300000, 'nucleus': 1,
        'endoplasmic_reticulum': 1, 'cytoskeleton': 1
    },
    'Hepatocyte': {
        'mitochondria': 2500, 'ribosome': 800000, 'nucleus': 1,
        'endoplasmic_reticulum': 1, 'golgi': 1, 'lysosome': 500, 'peroxisome': 300
    },
}


class CellCreationDialog(QDialog):
    """Dialog for creating cells from components."""
    cell_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Cell from Components")
        self.setMinimumSize(900, 700)
        self.components = {}
        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Build Cell from Components")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #EC407A;")
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Input
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Cell type presets
        preset_group = QGroupBox("Cell Type Presets")
        preset_group.setStyleSheet(self._get_group_style())
        preset_layout = QHBoxLayout(preset_group)

        for name in CELL_PRESETS.keys():
            btn = QPushButton(name)
            btn.setStyleSheet(self._get_button_style())
            btn.clicked.connect(lambda checked, n=name: self._set_preset(n))
            preset_layout.addWidget(btn)

        left_layout.addWidget(preset_group)

        # Component selection
        comp_group = QGroupBox("Add Components")
        comp_group.setStyleSheet(self._get_group_style())
        comp_layout = QGridLayout(comp_group)

        comp_label = QLabel("Component:")
        comp_layout.addWidget(comp_label, 0, 0)
        self.component_combo = QComboBox()
        self.component_combo.setStyleSheet(self._get_combo_style())
        for key, info in COMPONENT_TYPES.items():
            self.component_combo.addItem(info['name'], key)
        comp_layout.addWidget(self.component_combo, 0, 1)

        count_label = QLabel("Count:")
        comp_layout.addWidget(count_label, 1, 0)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 10000000)
        self.count_spin.setValue(1)
        self.count_spin.setStyleSheet(self._get_spin_style())
        comp_layout.addWidget(self.count_spin, 1, 1)

        add_btn = QPushButton("Add Component")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        add_btn.clicked.connect(self._add_component)
        comp_layout.addWidget(add_btn, 2, 0, 1, 2)

        left_layout.addWidget(comp_group)

        # Components table
        table_group = QGroupBox("Current Composition")
        table_group.setStyleSheet(self._get_group_style())
        table_layout = QVBoxLayout(table_group)

        self.comp_table = QTableWidget(0, 3)
        self.comp_table.setHorizontalHeaderLabels(['Component', 'Count', 'Remove'])
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.comp_table.setStyleSheet("""
            QTableWidget {
                background: rgba(40, 40, 60, 200);
                color: white;
                gridline-color: #555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background: #444;
                color: white;
                padding: 5px;
                border: none;
            }
        """)
        table_layout.addWidget(self.comp_table)

        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet("background: rgba(255, 87, 34, 180); color: white; padding: 6px; border-radius: 4px;")
        clear_btn.clicked.connect(self._clear_components)
        table_layout.addWidget(clear_btn)

        left_layout.addWidget(table_group)

        # Cell settings
        settings_group = QGroupBox("Cell Settings")
        settings_group.setStyleSheet(self._get_group_style())
        settings_layout = QGridLayout(settings_group)

        name_label = QLabel("Name:")
        settings_layout.addWidget(name_label, 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Custom Neuron")
        self.name_edit.setStyleSheet(self._get_input_style())
        self.name_edit.textChanged.connect(self.update_preview)
        settings_layout.addWidget(self.name_edit, 0, 1)

        type_label = QLabel("Cell Type:")
        settings_layout.addWidget(type_label, 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "epithelial", "neuron", "muscle", "blood", "immune",
            "stem", "gland", "connective", "other"
        ])
        self.type_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(self.type_combo, 1, 1)

        tissue_label = QLabel("Tissue:")
        settings_layout.addWidget(tissue_label, 2, 0)
        self.tissue_combo = QComboBox()
        self.tissue_combo.addItems([
            "epithelial", "connective", "muscle", "nervous"
        ])
        self.tissue_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(self.tissue_combo, 2, 1)

        diameter_label = QLabel("Diameter (μm):")
        settings_layout.addWidget(diameter_label, 3, 0)
        self.diameter_spin = QDoubleSpinBox()
        self.diameter_spin.setRange(1, 1000)
        self.diameter_spin.setValue(20)
        self.diameter_spin.setStyleSheet(self._get_spin_style())
        self.diameter_spin.valueChanged.connect(self.update_preview)
        settings_layout.addWidget(self.diameter_spin, 3, 1)

        left_layout.addWidget(settings_group)
        left_layout.addStretch()

        splitter.addWidget(left_panel)

        # Right panel - Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Component summary
        summary_group = QGroupBox("Component Summary")
        summary_group.setStyleSheet(self._get_group_style())
        summary_layout = QVBoxLayout(summary_group)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(40, 40, 60, 200);
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                font-size: 11px;
            }}
        """)
        summary_layout.addWidget(self.summary_text)

        right_layout.addWidget(summary_group)

        # Calculated properties
        props_group = QGroupBox("Calculated Properties")
        props_group.setStyleSheet(self._get_group_style())
        props_layout = QVBoxLayout(props_group)

        self.props_text = QTextEdit()
        self.props_text.setReadOnly(True)
        self.props_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(40, 40, 60, 200);
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                font-size: 11px;
            }}
        """)
        props_layout.addWidget(self.props_text)

        right_layout.addWidget(props_group)

        # Metabolic prediction
        metabolic_group = QGroupBox("Metabolic Prediction")
        metabolic_group.setStyleSheet(self._get_group_style())
        metabolic_layout = QVBoxLayout(metabolic_group)

        self.metabolic_text = QTextEdit()
        self.metabolic_text.setReadOnly(True)
        self.metabolic_text.setMaximumHeight(120)
        self.metabolic_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(40, 40, 60, 200);
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                font-size: 11px;
            }}
        """)
        metabolic_layout.addWidget(self.metabolic_text)

        right_layout.addWidget(metabolic_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([450, 450])

        layout.addWidget(splitter)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._get_button_style())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("Create Cell")
        create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EC407A, stop:1 #D81B60);
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D81B60, stop:1 #EC407A);
            }
        """)
        create_btn.clicked.connect(self.create_cell)
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)

    def _set_preset(self, preset_name: str):
        """Set components from a preset."""
        self.components = CELL_PRESETS[preset_name].copy()
        self._update_table()
        self.update_preview()

    def _add_component(self):
        """Add a component to the cell."""
        comp_key = self.component_combo.currentData()
        count = self.count_spin.value()

        if count > 0:
            self.components[comp_key] = self.components.get(comp_key, 0) + count
            self._update_table()
            self.update_preview()

    def _remove_component(self, comp_key: str):
        """Remove a component from the cell."""
        if comp_key in self.components:
            del self.components[comp_key]
            self._update_table()
            self.update_preview()

    def _clear_components(self):
        """Clear all components."""
        self.components = {}
        self._update_table()
        self.update_preview()

    def _update_table(self):
        """Update the components table."""
        self.comp_table.setRowCount(len(self.components))

        for row, (comp_key, count) in enumerate(self.components.items()):
            comp_info = COMPONENT_TYPES.get(comp_key, {'name': comp_key})

            name_item = QTableWidgetItem(comp_info['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.comp_table.setItem(row, 0, name_item)

            count_item = QTableWidgetItem(f"{count:,}")
            count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.comp_table.setItem(row, 1, count_item)

            remove_btn = QPushButton("X")
            remove_btn.setStyleSheet("background: #f44336; color: white; border-radius: 3px;")
            remove_btn.clicked.connect(lambda checked, k=comp_key: self._remove_component(k))
            self.comp_table.setCellWidget(row, 2, remove_btn)

    def update_preview(self):
        """Update preview panels."""
        if not self.components:
            self.summary_text.setText("Add components to see summary")
            self.props_text.setText("Add components to calculate properties")
            self.metabolic_text.setText("Add components for metabolic prediction")
            return

        # Component summary
        summary_lines = []
        for comp_key, count in sorted(self.components.items(), key=lambda x: -x[1]):
            comp_info = COMPONENT_TYPES.get(comp_key, {'name': comp_key})
            summary_lines.append(f"{comp_info['name']}: {count:,}")
        self.summary_text.setText("\n".join(summary_lines))

        # Calculate properties
        props = self._calculate_properties()
        props_text = f"""
Cell Volume: {props['volume']:.1f} μm³
Surface Area: {props['surface_area']:.1f} μm²
Total Components: {props['total_components']:,}
Mitochondria Count: {props['mitochondria_count']:,}
Ribosome Count: {props['ribosome_count']:,}
        """.strip()
        self.props_text.setText(props_text)

        # Metabolic prediction
        metabolic = self._predict_metabolic()
        metabolic_text = f"""
Metabolic Rate: {metabolic['rate']:.1f} fW
ATP Production: {metabolic['atp_production']:.0f} molecules/s
O2 Consumption: {metabolic['o2_consumption']:.2f} fmol/s
Energy Status: {metabolic['energy_status']}
        """.strip()
        self.metabolic_text.setText(metabolic_text)

    def _calculate_properties(self) -> dict:
        """Calculate cell properties from components."""
        diameter = self.diameter_spin.value()
        radius = diameter / 2

        volume = (4/3) * 3.14159 * (radius ** 3)
        surface_area = 4 * 3.14159 * (radius ** 2)

        total = sum(self.components.values())
        mito_count = self.components.get('mitochondria', 0)
        ribo_count = self.components.get('ribosome', 0)

        return {
            'volume': volume,
            'surface_area': surface_area,
            'total_components': total,
            'mitochondria_count': mito_count,
            'ribosome_count': ribo_count
        }

    def _predict_metabolic(self) -> dict:
        """Predict metabolic properties using Kleiber's Law."""
        mito_count = self.components.get('mitochondria', 0)
        volume = (4/3) * 3.14159 * ((self.diameter_spin.value() / 2) ** 3)

        # Simplified metabolic rate calculation (fW)
        # Based on mitochondria count and cell volume
        if mito_count > 0:
            rate = mito_count * 0.05  # ~50 aW per mitochondrion
        else:
            rate = volume * 0.001  # Minimal basal rate

        atp_production = rate * 1e6  # Rough conversion
        o2_consumption = rate * 0.01  # Rough conversion

        if rate > 100:
            status = "High (Active)"
        elif rate > 10:
            status = "Medium (Normal)"
        else:
            status = "Low (Quiescent)"

        return {
            'rate': rate,
            'atp_production': atp_production,
            'o2_consumption': o2_consumption,
            'energy_status': status
        }

    def create_cell(self):
        """Create the cell and emit signal."""
        name = self.name_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Name Required",
                              "Please enter a name for the cell.")
            return

        if not self.components:
            QMessageBox.warning(self, "Components Required",
                              "Please add at least one component.")
            return

        props = self._calculate_properties()
        metabolic = self._predict_metabolic()

        cell_data = {
            'name': name,
            'type': self.type_combo.currentText(),
            'tissue': self.tissue_combo.currentText(),
            'diameter_um': self.diameter_spin.value(),
            'volume_um3': props['volume'],
            'surface_area_um2': props['surface_area'],
            'mitochondria_count': props['mitochondria_count'],
            'ribosome_count': props['ribosome_count'],
            'metabolic_rate_fW': metabolic['rate'],
            'components': self.components.copy(),
            'is_custom': True
        }

        # Save to file
        cells_dir = Path(__file__).parent.parent / "data" / "active" / "cells"
        cells_dir.mkdir(parents=True, exist_ok=True)

        filename = name.replace(" ", "_").replace("/", "_")
        filepath = cells_dir / f"{filename}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cell_data, f, indent=2)

        self.cell_created.emit(cell_data)
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
            QSpinBox, QDoubleSpinBox {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 5px;
            }}
        """
