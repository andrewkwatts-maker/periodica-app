"""
Alloy Creation Dialog
Dialog for creating custom alloys from constituent elements.
Enhanced with grain structure preview and microstructure controls.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSpinBox, QLineEdit, QGroupBox, QComboBox, QTextEdit, QWidget,
    QMessageBox, QDoubleSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import json
from typing import Dict, List, Optional

from periodica.utils.alloy_calculator import AlloyCalculator, AlloyConstants
from periodica.data.data_manager import get_data_manager, DataCategory
from periodica_app.ui.grain_visualization import GrainVisualizationWidget


class AlloyCreationDialog(QDialog):
    """
    Dialog for creating alloys from constituent elements.
    """
    alloy_created = Signal(dict)  # Emitted when alloy is created

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Alloy from Elements")
        self.setMinimumSize(900, 700)
        self.components = []  # List of {'Element': str, 'Percent': float}
        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Create Custom Alloy")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Input
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Element addition group
        add_group = QGroupBox("Add Component Elements")
        add_group.setStyleSheet(self._get_group_style())
        add_layout = QGridLayout(add_group)

        element_label = QLabel("Element:")
        element_label.setToolTip("Select the element to add to the alloy composition")
        add_layout.addWidget(element_label, 0, 0)
        self.element_combo = QComboBox()
        self.element_combo.setToolTip("Choose from common alloying elements or type a custom symbol")
        # Add common alloying elements
        elements = ['Fe', 'Al', 'Cu', 'Ni', 'Cr', 'Ti', 'Zn', 'Sn', 'Mn', 'Mo',
                   'W', 'V', 'Co', 'Nb', 'Si', 'C', 'N', 'P', 'S', 'Ag', 'Au', 'Pb', 'Mg', 'B']
        for elem in elements:
            self.element_combo.addItem(elem, elem)
        self.element_combo.setEditable(True)
        add_layout.addWidget(self.element_combo, 0, 1)

        weight_label = QLabel("Weight %:")
        weight_label.setToolTip("Weight percentage of this element in the alloy (0.001% - 100%)")
        add_layout.addWidget(weight_label, 1, 0)
        self.percent_spin = QDoubleSpinBox()
        self.percent_spin.setToolTip("Enter the weight percentage for this element")
        self.percent_spin.setRange(0.001, 100.0)
        self.percent_spin.setDecimals(3)
        self.percent_spin.setValue(1.0)
        add_layout.addWidget(self.percent_spin, 1, 1)

        add_btn = QPushButton("Add Element")
        add_btn.setStyleSheet("background-color: #4caf50; color: white; padding: 8px; border-radius: 4px;")
        add_btn.clicked.connect(self.add_element)
        add_layout.addWidget(add_btn, 2, 0, 1, 2)

        left_layout.addWidget(add_group)

        # Quick presets
        preset_group = QGroupBox("Quick Presets")
        preset_group.setStyleSheet(self._get_group_style())
        preset_layout = QHBoxLayout(preset_group)

        presets = [
            ("304 SS", [('Fe', 70), ('Cr', 19), ('Ni', 9), ('Mn', 1), ('C', 0.08)]),
            ("Brass", [('Cu', 65), ('Zn', 35)]),
            ("Bronze", [('Cu', 88), ('Sn', 12)]),
            ("Duralumin", [('Al', 93.5), ('Cu', 4.4), ('Mg', 1.5), ('Mn', 0.6)]),
        ]

        for name, comp in presets:
            btn = QPushButton(name)
            btn.setStyleSheet("padding: 5px 10px;")
            btn.clicked.connect(lambda checked, c=comp: self.set_preset(c))
            preset_layout.addWidget(btn)

        left_layout.addWidget(preset_group)

        # Components table
        comp_group = QGroupBox("Current Composition")
        comp_group.setStyleSheet(self._get_group_style())
        comp_layout = QVBoxLayout(comp_group)

        self.comp_table = QTableWidget(0, 3)
        self.comp_table.setHorizontalHeaderLabels(['Element', 'Weight %', 'Remove'])
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
        comp_layout.addWidget(self.comp_table)

        self.total_label = QLabel("Total: 0.000%")
        self.total_label.setStyleSheet("color: #667eea; font-weight: bold;")
        comp_layout.addWidget(self.total_label)

        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet("background: rgba(255, 87, 34, 180); color: white; padding: 6px; border-radius: 4px;")
        clear_btn.clicked.connect(self.clear_components)
        comp_layout.addWidget(clear_btn)

        left_layout.addWidget(comp_group)

        # Alloy settings
        settings_group = QGroupBox("Alloy Settings")
        settings_group.setStyleSheet(self._get_group_style())
        settings_layout = QGridLayout(settings_group)

        name_label = QLabel("Name:")
        name_label.setToolTip("A unique name to identify your custom alloy")
        settings_layout.addWidget(name_label, 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("Enter a descriptive name for the alloy (required)")
        self.name_edit.setPlaceholderText("e.g., Custom Steel Alloy")
        self.name_edit.textChanged.connect(self.update_preview)
        settings_layout.addWidget(self.name_edit, 0, 1)

        structure_label = QLabel("Crystal Structure:")
        structure_label.setToolTip("The primary crystal lattice structure of the alloy")
        settings_layout.addWidget(structure_label, 1, 0)
        self.structure_combo = QComboBox()
        self.structure_combo.setToolTip(
            "FCC: Face-Centered Cubic (e.g., aluminum, copper)\n"
            "BCC: Body-Centered Cubic (e.g., iron, chromium)\n"
            "HCP: Hexagonal Close-Packed (e.g., titanium, zinc)\n"
            "BCT: Body-Centered Tetragonal\n"
            "Mixed: Multiple crystal structures present"
        )
        self.structure_combo.addItems(['FCC', 'BCC', 'HCP', 'BCT', 'Mixed'])
        self.structure_combo.currentIndexChanged.connect(self.update_preview)
        settings_layout.addWidget(self.structure_combo, 1, 1)

        left_layout.addWidget(settings_group)
        left_layout.addStretch()

        splitter.addWidget(left_panel)

        # Right panel - Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Grain structure preview - using unified visualization widget
        grain_preview_group = QGroupBox("Grain Structure Preview")
        grain_preview_group.setStyleSheet(self._get_group_style())
        grain_preview_layout = QVBoxLayout(grain_preview_group)

        self.grain_preview = GrainVisualizationWidget(editable=True)
        self.grain_preview.setMinimumHeight(280)
        self.grain_preview.grains_changed.connect(self._on_grain_centers_changed)
        # Generate initial grains
        self.grain_preview.viz.generate_random_grains(12, 42, 'poisson')
        grain_preview_layout.addWidget(self.grain_preview)

        right_layout.addWidget(grain_preview_group)

        # Properties summary
        props_group = QGroupBox("Calculated Properties")
        props_group.setStyleSheet(self._get_group_style())
        props_layout = QVBoxLayout(props_group)

        self.props_summary = QLabel()
        self.props_summary.setWordWrap(True)
        self.props_summary.setStyleSheet("color: #ccc; font-family: monospace;")
        props_layout.addWidget(self.props_summary)

        right_layout.addWidget(props_group)

        # JSON Preview
        preview_label = QLabel("JSON Preview")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        right_layout.addWidget(preview_label)

        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                border: 1px solid #444;
                border-radius: 4px;
            }
        """)
        right_layout.addWidget(self.json_preview)

        splitter.addWidget(right_panel)
        splitter.setSizes([450, 450])

        layout.addWidget(splitter)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.create_btn = QPushButton("Create Alloy")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8B5CF6;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.create_btn.clicked.connect(self.create_alloy)
        self.create_btn.setEnabled(False)
        btn_layout.addWidget(self.create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _get_group_style(self):
        return """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """

    def _on_grain_centers_changed(self):
        """Handle grain structure changes"""
        self.update_preview()

    def add_element(self):
        """Add element to composition"""
        element = self.element_combo.currentText().strip()
        if not element:
            return

        percent = self.percent_spin.value()

        # Check if element already exists
        for i, comp in enumerate(self.components):
            if comp['Element'] == element:
                # Update existing
                self.components[i]['Percent'] = percent
                self.update_table()
                self.update_preview()
                return

        self.components.append({'Element': element, 'Percent': percent})
        self.update_table()
        self.update_preview()

    def remove_element(self, row):
        """Remove element from composition"""
        if 0 <= row < len(self.components):
            del self.components[row]
            self.update_table()
            self.update_preview()

    def clear_components(self):
        """Clear all components"""
        self.components = []
        self.update_table()
        self.update_preview()

    def set_preset(self, composition):
        """Set composition from preset"""
        self.components = [{'Element': e, 'Percent': p} for e, p in composition]
        self.update_table()
        self.update_preview()

    def update_table(self):
        """Update the composition table"""
        self.comp_table.setRowCount(len(self.components))

        for i, comp in enumerate(self.components):
            # Element
            elem_item = QTableWidgetItem(comp['Element'])
            elem_item.setFlags(elem_item.flags() & ~Qt.ItemIsEditable)
            self.comp_table.setItem(i, 0, elem_item)

            # Percent
            pct_item = QTableWidgetItem(f"{comp['Percent']:.3f}")
            pct_item.setFlags(pct_item.flags() & ~Qt.ItemIsEditable)
            self.comp_table.setItem(i, 1, pct_item)

            # Remove button
            remove_btn = QPushButton("X")
            remove_btn.setStyleSheet("background: #f44336; color: white; padding: 2px 8px;")
            remove_btn.clicked.connect(lambda checked, r=i: self.remove_element(r))
            self.comp_table.setCellWidget(i, 2, remove_btn)

        # Update total
        total = sum(c['Percent'] for c in self.components)
        color = "#4CAF50" if abs(total - 100) < 0.5 else "#FF9800" if total < 100 else "#f44336"
        self.total_label.setText(f"Total: {total:.3f}%")
        self.total_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def update_preview(self):
        """Update the preview panels"""
        if not self.components:
            self.props_summary.setText("Add elements to see calculated properties")
            self.json_preview.clear()
            self.create_btn.setEnabled(False)
            return

        # Normalize to 100%
        total = sum(c['Percent'] for c in self.components)
        if total <= 0:
            return

        # Prepare data for calculator
        elements = [c['Element'] for c in self.components]
        weight_fractions = [c['Percent'] / 100 for c in self.components]

        name = self.name_edit.text() or None
        lattice = self.structure_combo.currentText()

        # Generate alloy data
        try:
            component_data = [{'symbol': e} for e in elements]
            alloy_data = AlloyCalculator.create_alloy_from_components(
                component_data, weight_fractions, lattice, name
            )

            # Update properties summary
            summary = f"""
Composition: {', '.join(f'{e}:{c["Percent"]:.1f}%' for e, c in zip(elements, self.components))}
Total: {total:.3f}%

--- Calculated Properties ---

Physical:
  Density: {alloy_data['PhysicalProperties']['Density_g_cm3']:.3f} g/cm³
  Melting Point: {alloy_data['PhysicalProperties']['MeltingPoint_K']:.0f} K
  Thermal Conductivity: {alloy_data['PhysicalProperties']['ThermalConductivity_W_mK']:.1f} W/m·K

Mechanical:
  Tensile Strength: {alloy_data['MechanicalProperties']['TensileStrength_MPa']:.0f} MPa
  Yield Strength: {alloy_data['MechanicalProperties']['YieldStrength_MPa']:.0f} MPa
  Hardness: {alloy_data['PhysicalProperties']['BrinellHardness_HB']:.0f} HB
  Elongation: {alloy_data['MechanicalProperties']['Elongation_percent']:.0f}%

Lattice:
  Structure: {lattice}
  Lattice Parameter: {alloy_data['LatticeProperties']['LatticeParameters']['a_pm']:.2f} pm
  Packing Factor: {alloy_data['LatticeProperties']['AtomicPackingFactor']:.2f}

Category: {alloy_data['Category']}
            """.strip()
            self.props_summary.setText(summary)

            # Add grain structure data from the unified visualization widget
            grain_data = self.grain_preview.get_grain_data()
            alloy_data['Microstructure'] = {
                'GrainStructure': grain_data
            }

            # Update JSON preview
            json_str = json.dumps(alloy_data, indent=2, ensure_ascii=False)
            self.json_preview.setPlainText(json_str)

            self._current_data = alloy_data

            # Enable create button if name is provided
            self.create_btn.setEnabled(bool(self.name_edit.text()))

        except Exception as e:
            self.props_summary.setText(f"Error calculating properties: {e}")
            self.json_preview.clear()
            self.create_btn.setEnabled(False)

    def create_alloy(self):
        """Create the alloy and save to data"""
        if not self.name_edit.text():
            QMessageBox.warning(self, "Missing Name", "Please enter an alloy name.")
            return

        if not self.components:
            QMessageBox.warning(self, "No Components", "Please add at least one element to the alloy composition.")
            return

        # Validate weight fractions sum to approximately 100%
        total = sum(c['Percent'] for c in self.components)
        if abs(total - 100.0) > 1.0:
            reply = QMessageBox.question(
                self, "Weight Percentage Warning",
                f"The total weight percentage is {total:.3f}%, which differs from 100%.\n\n"
                "Would you like to continue anyway, or go back and adjust the composition?\n\n"
                "(Note: Small deviations may be acceptable for trace elements)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Update name in data
        self._current_data['Name'] = self.name_edit.text()
        self._current_data['name'] = self.name_edit.text()

        # Save to data manager
        manager = get_data_manager()
        filename = self.name_edit.text().replace(' ', '_').replace('/', '-')

        if manager.add_item(DataCategory.ALLOYS, filename, self._current_data):
            self.alloy_created.emit(self._current_data)
            QMessageBox.information(self, "Success",
                                  f"Alloy '{self._current_data['Name']}' created successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error",
                              "Failed to create alloy. It may already exist.")


# Convenience function
def open_alloy_creation_dialog(parent=None) -> Optional[Dict]:
    """Open alloy creation dialog and return created data or None."""
    dialog = AlloyCreationDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog._current_data
    return None
