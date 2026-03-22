"""
Inline Data Editor Widget
Embeddable editor for Add/Edit/Remove operations in RHS panels.
Replaces dialog-based editing with inline editing in the info panel.
"""

import json
from typing import Dict, List, Optional, Any, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox,
    QComboBox, QPushButton, QTextEdit, QGroupBox, QFrame,
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from periodica.data.data_manager import get_data_manager, DataCategory


class InlineDataEditor(QWidget):
    """
    Inline editor widget for editing JSON data in the RHS panel.

    Signals:
        data_saved: Emitted when data is saved successfully (with the data dict)
        edit_cancelled: Emitted when editing is cancelled
    """

    data_saved = Signal(dict)
    edit_cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.category: Optional[DataCategory] = None
        self.existing_data: Optional[Dict] = None
        self.field_widgets: Dict[str, QWidget] = {}
        self.is_edit_mode = False
        self._original_filename: Optional[str] = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title
        self.title_label = QLabel("Add New Item")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #4fc3f7;")
        layout.addWidget(self.title_label)

        # Scroll area for fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: rgb(20, 20, 35); }
            QScrollBar:vertical {
                background: rgba(40, 40, 60, 100);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(79, 195, 247, 150);
                border-radius: 4px;
            }
        """)

        self.form_container = QWidget()
        self.form_container.setStyleSheet("background: rgb(20, 20, 35);")
        self.form_layout = QFormLayout(self.form_container)
        self.form_layout.setSpacing(8)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        scroll.setWidget(self.form_container)
        layout.addWidget(scroll, 1)

        # JSON Preview (collapsible)
        self.preview_group = QGroupBox("JSON Preview")
        self.preview_group.setCheckable(True)
        self.preview_group.setChecked(False)
        self.preview_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        preview_layout = QVBoxLayout(self.preview_group)

        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setMaximumHeight(150)
        self.json_preview.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: monospace;
                font-size: 10px;
                border: none;
            }
        """)
        preview_layout.addWidget(self.json_preview)
        layout.addWidget(self.preview_group)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #4caf50;
                color: white;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background: #45a049; }
            QPushButton:disabled { background: #666; }
        """)
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background: #da190b; }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def start_add(self, category: DataCategory, template_data: Optional[Dict] = None):
        """
        Start adding a new item.

        Args:
            category: The data category to add to
            template_data: Optional template data to populate fields
        """
        self.category = category
        self.existing_data = None
        self.is_edit_mode = False
        self._original_filename = None

        self.title_label.setText(f"Add New {category.value.replace('_', ' ').title()}")
        self.title_label.setStyleSheet("color: #4caf50;")

        # Get schema for category
        schema = self._get_schema_for_category(category)
        self._build_form(schema, template_data or {})
        self._update_preview()

    def start_edit(self, category: DataCategory, data: Dict):
        """
        Start editing an existing item.

        Args:
            category: The data category
            data: The existing data to edit
        """
        self.category = category
        self.existing_data = data.copy()
        self.is_edit_mode = True
        self._original_filename = data.get('_filename', '')

        name = data.get('name', data.get('Name', data.get('symbol', 'Item')))
        self.title_label.setText(f"Edit: {name}")
        self.title_label.setStyleSheet("color: #ff9800;")

        # Get schema for category
        schema = self._get_schema_for_category(category)
        self._build_form(schema, data)
        self._update_preview()

    def _get_schema_for_category(self, category: DataCategory) -> List[Dict]:
        """Get field schema for a category"""
        schemas = {
            DataCategory.ELEMENTS: [
                {"name": "symbol", "type": "string", "required": True, "label": "Symbol"},
                {"name": "name", "type": "string", "required": True, "label": "Name"},
                {"name": "atomic_number", "type": "int", "label": "Atomic Number", "min": 1, "max": 200},
                {"name": "atomic_mass", "type": "float", "label": "Atomic Mass (u)", "decimals": 4},
                {"name": "period", "type": "int", "label": "Period", "min": 1, "max": 10},
                {"name": "group", "type": "int", "label": "Group", "min": 1, "max": 18},
                {"name": "block", "type": "choice", "label": "Block", "choices": ["s", "p", "d", "f"]},
                {"name": "category", "type": "string", "label": "Category"},
                {"name": "electron_configuration", "type": "string", "label": "Electron Config"},
                {"name": "electronegativity", "type": "float", "label": "Electronegativity", "decimals": 2},
                {"name": "ionization_energy", "type": "float", "label": "Ionization Energy (eV)", "decimals": 2},
                {"name": "atomic_radius", "type": "float", "label": "Atomic Radius (pm)", "decimals": 1},
                {"name": "melting_point", "type": "float", "label": "Melting Point (K)", "decimals": 1},
                {"name": "boiling_point", "type": "float", "label": "Boiling Point (K)", "decimals": 1},
                {"name": "density", "type": "float", "label": "Density (g/cm³)", "decimals": 3},
                {"name": "color", "type": "string", "label": "Color (hex)"},
            ],
            DataCategory.QUARKS: [
                {"name": "Name", "type": "string", "required": True, "label": "Name"},
                {"name": "Symbol", "type": "string", "required": True, "label": "Symbol"},
                {"name": "Mass_MeVc2", "type": "float", "label": "Mass (MeV/c²)", "decimals": 3},
                {"name": "Charge_e", "type": "float", "label": "Charge (e)", "decimals": 3},
                {"name": "Spin_hbar", "type": "float", "label": "Spin (ℏ)", "decimals": 1},
                {"name": "ColorCharge", "type": "choice", "label": "Color Charge",
                 "choices": ["red", "green", "blue", "antired", "antigreen", "antiblue"]},
                {"name": "Generation", "type": "int", "label": "Generation", "min": 1, "max": 3},
                {"name": "BaryonNumber_B", "type": "float", "label": "Baryon Number", "decimals": 3},
                {"name": "Isospin_I", "type": "float", "label": "Isospin (I)", "decimals": 2},
                {"name": "Isospin_I3", "type": "float", "label": "Isospin (I₃)", "decimals": 2},
            ],
            DataCategory.SUBATOMIC: [
                {"name": "Name", "type": "string", "required": True, "label": "Name"},
                {"name": "Symbol", "type": "string", "required": True, "label": "Symbol"},
                {"name": "Mass_MeVc2", "type": "float", "label": "Mass (MeV/c²)", "decimals": 3},
                {"name": "Charge_e", "type": "float", "label": "Charge (e)", "decimals": 3},
                {"name": "Spin_hbar", "type": "float", "label": "Spin (ℏ)", "decimals": 2},
                {"name": "ParticleType", "type": "choice", "label": "Particle Type",
                 "choices": ["Baryon", "Meson", "Lepton", "Boson", "Hadron"]},
                {"name": "QuarkContent", "type": "string", "label": "Quark Content"},
                {"name": "BaryonNumber", "type": "float", "label": "Baryon Number", "decimals": 3},
                {"name": "Strangeness", "type": "int", "label": "Strangeness"},
                {"name": "MeanLifetime_s", "type": "float", "label": "Mean Lifetime (s)", "decimals": 10},
                {"name": "IsStable", "type": "bool", "label": "Is Stable"},
            ],
            DataCategory.MOLECULES: [
                {"name": "Name", "type": "string", "required": True, "label": "Name"},
                {"name": "Formula", "type": "string", "required": True, "label": "Formula"},
                {"name": "MolecularMass_amu", "type": "float", "label": "Molecular Mass (amu)", "decimals": 3},
                {"name": "BondType", "type": "choice", "label": "Bond Type",
                 "choices": ["Covalent", "Ionic", "Polar Covalent", "Metallic", "Hydrogen"]},
                {"name": "Geometry", "type": "string", "label": "Geometry"},
                {"name": "Polarity", "type": "choice", "label": "Polarity", "choices": ["Polar", "Nonpolar"]},
                {"name": "MeltingPoint_K", "type": "float", "label": "Melting Point (K)", "decimals": 1},
                {"name": "BoilingPoint_K", "type": "float", "label": "Boiling Point (K)", "decimals": 1},
                {"name": "Density_g_cm3", "type": "float", "label": "Density (g/cm³)", "decimals": 3},
                {"name": "DipoleMoment_D", "type": "float", "label": "Dipole Moment (D)", "decimals": 2},
                {"name": "State_STP", "type": "choice", "label": "State at STP",
                 "choices": ["Solid", "Liquid", "Gas"]},
            ],
            DataCategory.ALLOYS: [
                {"name": "name", "type": "string", "required": True, "label": "Name"},
                {"name": "formula", "type": "string", "label": "Formula"},
                {"name": "category", "type": "choice", "label": "Category",
                 "choices": ["Steel", "Aluminum", "Titanium", "Copper", "Nickel", "Cobalt", "Other"]},
                {"name": "density", "type": "float", "label": "Density (g/cm³)", "decimals": 3},
                {"name": "melting_point", "type": "float", "label": "Melting Point (K)", "decimals": 1},
                {"name": "tensile_strength", "type": "float", "label": "Tensile Strength (MPa)", "decimals": 1},
                {"name": "yield_strength", "type": "float", "label": "Yield Strength (MPa)", "decimals": 1},
                {"name": "youngs_modulus", "type": "float", "label": "Young's Modulus (GPa)", "decimals": 1},
                {"name": "hardness", "type": "float", "label": "Hardness (HB)", "decimals": 1},
                {"name": "thermal_conductivity", "type": "float", "label": "Thermal Cond. (W/m·K)", "decimals": 1},
                {"name": "corrosion_resistance", "type": "choice", "label": "Corrosion Resistance",
                 "choices": ["Poor", "Fair", "Good", "Excellent"]},
            ],
        }
        return schemas.get(category, [])

    def _build_form(self, schema: List[Dict], data: Dict):
        """Build form fields from schema"""
        # Clear existing fields
        self.field_widgets.clear()
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create fields
        for field_def in schema:
            name = field_def["name"]
            label = field_def.get("label", name)
            field_type = field_def.get("type", "string")
            required = field_def.get("required", False)

            # Get value from data
            value = data.get(name, field_def.get("default", None))

            # Create label
            label_text = f"{label}{'*' if required else ''}:"
            field_label = QLabel(label_text)
            field_label.setStyleSheet("color: white; font-size: 11px;")

            # Create input widget based on type
            widget = self._create_field_widget(field_def, value)
            if widget:
                widget.setStyleSheet(self._get_input_style())
                self.field_widgets[name] = widget
                self.form_layout.addRow(field_label, widget)

                # Connect change signals for preview update
                self._connect_change_signal(widget, field_type)

    def _create_field_widget(self, field_def: Dict, value: Any) -> Optional[QWidget]:
        """Create appropriate widget for field type"""
        field_type = field_def.get("type", "string")

        if field_type == "string":
            widget = QLineEdit()
            widget.setText(str(value) if value is not None else "")
            widget.setPlaceholderText(field_def.get("placeholder", ""))
            return widget

        elif field_type == "int":
            widget = QSpinBox()
            widget.setRange(field_def.get("min", -999999), field_def.get("max", 999999))
            widget.setValue(int(value) if value is not None else 0)
            return widget

        elif field_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(field_def.get("min", -1e12), field_def.get("max", 1e12))
            widget.setDecimals(field_def.get("decimals", 4))
            widget.setValue(float(value) if value is not None else 0.0)
            return widget

        elif field_type == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(value) if value is not None else False)
            return widget

        elif field_type == "choice":
            widget = QComboBox()
            choices = field_def.get("choices", [])
            widget.addItems(choices)
            if value and str(value) in choices:
                widget.setCurrentText(str(value))
            return widget

        return None

    def _connect_change_signal(self, widget: QWidget, field_type: str):
        """Connect widget's change signal to preview update"""
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._update_preview)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.valueChanged.connect(self._update_preview)
        elif isinstance(widget, QCheckBox):
            widget.stateChanged.connect(self._update_preview)
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(self._update_preview)

    def _get_input_style(self) -> str:
        """Get stylesheet for input widgets"""
        return """
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #4fc3f7;
            }
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: rgba(30, 30, 50, 250);
                color: white;
                selection-background-color: #4fc3f7;
            }
        """

    def _collect_data(self) -> Dict:
        """Collect data from form fields"""
        data = {}

        for name, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                data[name] = widget.text()
            elif isinstance(widget, QSpinBox):
                data[name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                data[name] = widget.value()
            elif isinstance(widget, QCheckBox):
                data[name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                data[name] = widget.currentText()

        return data

    def _update_preview(self):
        """Update JSON preview"""
        data = self._collect_data()
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        self.json_preview.setPlainText(json_str)

    def _validate(self) -> tuple[bool, str]:
        """Validate form data"""
        schema = self._get_schema_for_category(self.category)

        for field_def in schema:
            name = field_def["name"]
            required = field_def.get("required", False)

            if required and name in self.field_widgets:
                widget = self.field_widgets[name]
                if isinstance(widget, QLineEdit) and not widget.text().strip():
                    return False, f"{field_def.get('label', name)} is required"

        return True, ""

    def _on_save(self):
        """Handle save button click"""
        # Validate
        valid, error = self._validate()
        if not valid:
            QMessageBox.warning(self, "Validation Error", error)
            return

        # Collect data
        data = self._collect_data()

        # Get filename
        if self.category == DataCategory.ELEMENTS:
            filename = f"{data.get('atomic_number', 0):03d}_{data.get('symbol', 'X')}"
        elif self.category in [DataCategory.QUARKS, DataCategory.SUBATOMIC]:
            filename = data.get('Name', data.get('Symbol', 'unknown')).replace(' ', '_')
        elif self.category == DataCategory.MOLECULES:
            filename = data.get('Name', data.get('Formula', 'unknown')).replace(' ', '_')
        elif self.category == DataCategory.ALLOYS:
            filename = data.get('name', 'unknown').replace(' ', '_')
        else:
            filename = 'item'

        # Save to data manager
        manager = get_data_manager()

        if self.is_edit_mode and self._original_filename:
            # Remove old entry if filename changed
            if self._original_filename != filename:
                manager.remove_item(self.category, self._original_filename)

        if manager.add_item(self.category, filename, data):
            self.data_saved.emit(data)
        else:
            QMessageBox.warning(self, "Error", "Failed to save data")

    def _on_cancel(self):
        """Handle cancel button click"""
        self.edit_cancelled.emit()


class CreateFromParticleEditor(QWidget):
    """
    Specialized editor for creating items from constituent particles.
    Used for Create from Quarks, Create from Atoms, etc.
    """

    item_created = Signal(dict)
    creation_cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the creation UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        self.title_label = QLabel("Create from Particles")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #9c27b0;")
        layout.addWidget(self.title_label)

        # Content will be set by subclasses or start_creation
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        layout.addWidget(self.content_widget, 1)

        # Buttons
        btn_layout = QHBoxLayout()

        self.create_btn = QPushButton("Create")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                color: white;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #764ba2, stop:1 #667eea);
            }
        """)
        self.create_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(self.create_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #666;
                color: white;
                padding: 10px 25px;
                border-radius: 5px;
            }
            QPushButton:hover { background: #777; }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_create(self):
        """Handle create button - override in subclass"""
        pass

    def _on_cancel(self):
        """Handle cancel button"""
        self.creation_cancelled.emit()
