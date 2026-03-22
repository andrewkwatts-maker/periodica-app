"""
Molecule Control Panel
Provides UI controls for molecule visualization settings.
Polished to match Atoms tab features with visual property encodings and filters.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                                QScrollArea, QRadioButton, QComboBox, QCheckBox,
                                QPushButton, QSlider, QToolButton, QFrame)
from PySide6.QtCore import Qt, QPropertyAnimation, Signal
from PySide6.QtGui import QFont

from periodica.core.molecule_enums import (MoleculeLayoutMode, MoleculeCategory, MoleculePolarity,
                                  MoleculeState, MoleculeProperty, BondType)
from periodica.data.data_manager import get_data_manager, DataCategory
from periodica_app.ui.transform_controls import TransformControlsWidget, Transform3D
from periodica_app.ui.ai_generation_widget import AIGenerationWidget


# Molecule property metadata for slider ranges and units
MOLECULE_PROPERTY_METADATA = {
    "molecular_mass": {
        "display_name": "Molecular Mass",
        "unit": "amu",
        "min_value": 1.0,
        "max_value": 500.0,
        "description": "Total mass of the molecule in atomic mass units"
    },
    "melting_point": {
        "display_name": "Melting Point",
        "unit": "K",
        "min_value": 0.0,
        "max_value": 1000.0,
        "description": "Temperature at which the molecule transitions from solid to liquid"
    },
    "boiling_point": {
        "display_name": "Boiling Point",
        "unit": "K",
        "min_value": 0.0,
        "max_value": 1500.0,
        "description": "Temperature at which the molecule transitions from liquid to gas"
    },
    "density": {
        "display_name": "Density",
        "unit": "g/cm3",
        "min_value": 0.0,
        "max_value": 5.0,
        "description": "Mass per unit volume at standard conditions"
    },
    "dipole_moment": {
        "display_name": "Dipole Moment",
        "unit": "D",
        "min_value": 0.0,
        "max_value": 10.0,
        "description": "Measure of molecular polarity (Debye units)"
    },
    "bond_angle": {
        "display_name": "Bond Angle",
        "unit": "deg",
        "min_value": 0.0,
        "max_value": 180.0,
        "description": "Angle between adjacent bonds in the molecule"
    },
    "vapor_pressure": {
        "display_name": "Vapor Pressure",
        "unit": "kPa",
        "min_value": 0.0,
        "max_value": 200.0,
        "description": "Pressure exerted by vapor in equilibrium with liquid"
    },
    "solubility": {
        "display_name": "Solubility",
        "unit": "g/L",
        "min_value": 0.0,
        "max_value": 1000.0,
        "description": "Amount that dissolves in water at standard conditions"
    },
    "num_atoms": {
        "display_name": "Number of Atoms",
        "unit": "",
        "min_value": 1.0,
        "max_value": 50.0,
        "description": "Total number of atoms in the molecule"
    },
    "num_bonds": {
        "display_name": "Number of Bonds",
        "unit": "",
        "min_value": 1.0,
        "max_value": 60.0,
        "description": "Total number of chemical bonds"
    },
    "electronegativity_diff": {
        "display_name": "Electronegativity Diff",
        "unit": "",
        "min_value": 0.0,
        "max_value": 3.5,
        "description": "Maximum electronegativity difference between bonded atoms"
    },
    "bond_length_avg": {
        "display_name": "Avg Bond Length",
        "unit": "pm",
        "min_value": 70.0,
        "max_value": 200.0,
        "description": "Average length of bonds in the molecule"
    },
    "none": {
        "display_name": "None",
        "unit": "",
        "min_value": 0.0,
        "max_value": 100.0,
        "description": "No property encoding"
    }
}

# Visual attribute types and their descriptions
VISUAL_ATTRIBUTE_TYPES = {
    "fill_color": {
        "display_name": "Card Color Gradient",
        "description": "Background color gradient based on property value",
        "type": "color"
    },
    "border_color": {
        "display_name": "Border Color",
        "description": "Border color intensity based on property value",
        "type": "color"
    },
    "glow_color": {
        "display_name": "Glow/Highlight",
        "description": "Glow effect intensity based on property value",
        "type": "color"
    },
    "symbol_text_color": {
        "display_name": "Text Color",
        "description": "Formula/name text color based on property value",
        "type": "color"
    },
    "border_size": {
        "display_name": "Border Intensity",
        "description": "Border thickness/weight based on property value",
        "type": "size"
    },
    "card_size": {
        "display_name": "Card Size",
        "description": "Overall card size scaling based on property value",
        "type": "size"
    },
    "glow_intensity": {
        "display_name": "Glow Intensity",
        "description": "Strength of the glow effect",
        "type": "size"
    },
    "opacity": {
        "display_name": "Opacity",
        "description": "Card transparency based on property value",
        "type": "size"
    }
}


def get_molecule_property_metadata(property_name):
    """Get metadata for a molecule property"""
    return MOLECULE_PROPERTY_METADATA.get(property_name, MOLECULE_PROPERTY_METADATA["none"])


def get_all_visual_encoding_options():
    """Get a comprehensive summary of all available visual encoding options for molecules.

    Returns:
        Dictionary containing:
        - numeric_properties: List of all numeric properties available for encoding
        - visual_attributes: List of all visual attributes that can be mapped
        - color_encodings: Properties suitable for color encoding
        - size_encodings: Properties suitable for size encoding
        - default_mappings: Default property-to-visual mappings
    """
    return {
        "numeric_properties": {
            "molecular_mass": {
                "display": "Molecular Mass",
                "unit": "amu",
                "range": (1.0, 500.0),
                "description": "Total mass of the molecule"
            },
            "density": {
                "display": "Density",
                "unit": "g/cm3",
                "range": (0.0, 5.0),
                "description": "Mass per unit volume"
            },
            "melting_point": {
                "display": "Melting Point",
                "unit": "K",
                "range": (0.0, 1000.0),
                "description": "Solid to liquid transition temperature"
            },
            "boiling_point": {
                "display": "Boiling Point",
                "unit": "K",
                "range": (0.0, 1500.0),
                "description": "Liquid to gas transition temperature"
            },
            "bond_angle": {
                "display": "Bond Angle",
                "unit": "deg",
                "range": (0.0, 180.0),
                "description": "Angle between adjacent bonds"
            },
            "dipole_moment": {
                "display": "Dipole Moment",
                "unit": "D",
                "range": (0.0, 10.0),
                "description": "Measure of molecular polarity"
            },
            "vapor_pressure": {
                "display": "Vapor Pressure",
                "unit": "kPa",
                "range": (0.0, 200.0),
                "description": "Equilibrium vapor pressure"
            },
            "solubility": {
                "display": "Solubility",
                "unit": "g/L",
                "range": (0.0, 1000.0),
                "description": "Water solubility at STP"
            },
            "num_atoms": {
                "display": "Number of Atoms",
                "unit": "",
                "range": (1, 50),
                "description": "Total atom count (derived)"
            },
            "num_bonds": {
                "display": "Number of Bonds",
                "unit": "",
                "range": (1, 60),
                "description": "Total bond count (derived)"
            },
            "electronegativity_diff": {
                "display": "Electronegativity Diff",
                "unit": "",
                "range": (0.0, 3.5),
                "description": "Max electronegativity difference"
            },
            "bond_length_avg": {
                "display": "Avg Bond Length",
                "unit": "pm",
                "range": (70.0, 200.0),
                "description": "Average bond length (derived)"
            }
        },
        "visual_attributes": {
            "color_encodings": [
                {"key": "fill_color", "display": "Card Color Gradient", "description": "Background gradient color"},
                {"key": "border_color", "display": "Border Color", "description": "Card border color"},
                {"key": "glow_color", "display": "Glow/Highlight", "description": "Glow effect color"},
                {"key": "symbol_text_color", "display": "Text Color", "description": "Formula/name text color"}
            ],
            "size_encodings": [
                {"key": "border_size", "display": "Border Intensity", "description": "Border thickness"},
                {"key": "card_size", "display": "Card Size", "description": "Overall card scaling"},
                {"key": "glow_intensity", "display": "Glow Intensity", "description": "Glow effect strength"},
                {"key": "opacity", "display": "Opacity", "description": "Card transparency"}
            ]
        },
        "default_mappings": {
            "fill_color": "molecular_mass",
            "border_color": "boiling_point",
            "glow_color": "dipole_moment",
            "symbol_text_color": "density",
            "border_size": "melting_point",
            "card_size": "num_atoms",
            "glow_intensity": "electronegativity_diff",
            "opacity": "num_bonds"
        }
    }


class CollapsibleBox(QWidget):
    """A collapsible widget that can expand/collapse its content"""
    def __init__(self, title="", border_color="#4fc3f7", parent=None):
        super().__init__(parent)

        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet(f"""
            QToolButton {{
                border: none;
                color: white;
                font-weight: bold;
                text-align: left;
                padding: 5px;
            }}
        """)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.on_toggle)

        self.content_area = QFrame()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        self.content_area.setStyleSheet(f"""
            QFrame {{
                border: none;
                background: transparent;
                padding: 5px;
            }}
        """)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_area.setLayout(self.content_layout)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)
        self.setLayout(main_layout)

        self.toggle_animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.toggle_animation.setDuration(200)

    def on_toggle(self):
        """Toggle the expanded/collapsed state"""
        checked = self.toggle_button.isChecked()
        arrow_type = Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        self.toggle_button.setArrowType(arrow_type)

        if checked:
            # Expand - use animation to grow, then remove max height constraint
            content_height = self.content_area.sizeHint().height()
            self.toggle_animation.setStartValue(0)
            self.toggle_animation.setEndValue(content_height)
            self.toggle_animation.finished.connect(self._on_expand_finished)
            self.toggle_animation.start()
        else:
            # Collapse
            self.content_area.setMaximumHeight(self.content_area.height())
            self.toggle_animation.setStartValue(self.content_area.height())
            self.toggle_animation.setEndValue(0)
            self.toggle_animation.start()

    def _on_expand_finished(self):
        """Remove height constraint after expand animation completes"""
        self.content_area.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
        try:
            self.toggle_animation.finished.disconnect(self._on_expand_finished)
        except RuntimeError:
            pass  # Already disconnected


class MoleculePropertyControl(QWidget):
    """Expandable control for a single visual property with range controls and filtering"""

    property_changed = Signal(str, str)  # property_key, property_name
    filter_range_changed = Signal(str, float, float)  # property_key, min, max
    gradient_colors_changed = Signal(str, object, object)  # property_key, start_color, end_color

    def __init__(self, title, property_key, parent_panel, available_properties,
                 control_type="color", default_property="molecular_mass"):
        super().__init__()
        self.property_key = property_key
        self.parent_panel = parent_panel
        self.control_type = control_type
        self.is_expanded = False
        self.default_property = default_property
        self.current_property = default_property

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 3, 5, 3)
        main_layout.setSpacing(3)

        # Header with expand/collapse and property selector
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        self.expand_btn = QToolButton()
        self.expand_btn.setArrowType(Qt.ArrowType.RightArrow)
        self.expand_btn.setStyleSheet("QToolButton { border: none; color: white; }")
        self.expand_btn.clicked.connect(self.toggle_expanded)
        header_layout.addWidget(self.expand_btn)

        title_label = QLabel(title + ":")
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px;")
        title_label.setMinimumWidth(110)
        header_layout.addWidget(title_label)

        self.property_combo = QComboBox()
        self.property_combo.addItems(available_properties)
        self.property_combo.setStyleSheet(self._get_combo_style())
        self.property_combo.currentIndexChanged.connect(self.on_property_selection_changed)
        self.available_properties = available_properties
        header_layout.addWidget(self.property_combo, 1)

        # Set default property
        if default_property in [p.lower().replace(" ", "_") for p in available_properties]:
            for i, prop in enumerate(available_properties):
                if prop.lower().replace(" ", "_") == default_property:
                    self.property_combo.setCurrentIndex(i)
                    break

        main_layout.addWidget(header)

        # Expandable details area
        self.details_widget = QWidget()
        self.details_widget.setVisible(False)
        details_layout = QVBoxLayout(self.details_widget)
        details_layout.setContentsMargins(25, 5, 5, 5)
        details_layout.setSpacing(8)

        # Filter range sliders
        filter_label = QLabel("Filter Range:")
        filter_label.setStyleSheet("color: rgba(255,255,255,200); font-size: 9px; font-weight: bold;")
        details_layout.addWidget(filter_label)

        # Min slider
        min_container = QWidget()
        min_layout = QHBoxLayout(min_container)
        min_layout.setContentsMargins(0, 0, 0, 0)
        min_layout.setSpacing(5)

        min_label = QLabel("Min:")
        min_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 30px;")
        min_layout.addWidget(min_label)

        self.min_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_slider.setMinimum(0)
        self.min_slider.setMaximum(1000)
        self.min_slider.setValue(0)
        self.min_slider.setStyleSheet(self._get_slider_style())
        self.min_slider.valueChanged.connect(self.on_filter_changed)
        min_layout.addWidget(self.min_slider)

        self.min_display = QLabel("0.0")
        self.min_display.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 50px;")
        min_layout.addWidget(self.min_display)

        details_layout.addWidget(min_container)

        # Max slider
        max_container = QWidget()
        max_layout = QHBoxLayout(max_container)
        max_layout.setContentsMargins(0, 0, 0, 0)
        max_layout.setSpacing(5)

        max_label = QLabel("Max:")
        max_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 30px;")
        max_layout.addWidget(max_label)

        self.max_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_slider.setMinimum(0)
        self.max_slider.setMaximum(1000)
        self.max_slider.setValue(1000)
        self.max_slider.setStyleSheet(self._get_slider_style())
        self.max_slider.valueChanged.connect(self.on_filter_changed)
        max_layout.addWidget(self.max_slider)

        self.max_display = QLabel("100.0")
        self.max_display.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 50px;")
        max_layout.addWidget(self.max_display)

        details_layout.addWidget(max_container)

        # Gradient color pickers (for color properties)
        if control_type == "color":
            gradient_label = QLabel("Gradient Colors:")
            gradient_label.setStyleSheet("color: rgba(255,255,255,200); font-size: 9px; font-weight: bold; margin-top: 5px;")
            details_layout.addWidget(gradient_label)

            colors_container = QWidget()
            colors_layout = QHBoxLayout(colors_container)
            colors_layout.setContentsMargins(0, 0, 0, 0)
            colors_layout.setSpacing(10)

            self.start_color_btn = QPushButton()
            self.start_color_btn.setFixedSize(30, 20)
            self.start_color_btn.setStyleSheet("background-color: #6495ED; border: 1px solid white; border-radius: 3px;")
            self.start_color_btn.clicked.connect(lambda: self.pick_gradient_color("start"))
            self.start_color = "#6495ED"

            start_label = QLabel("Start")
            start_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px;")

            self.end_color_btn = QPushButton()
            self.end_color_btn.setFixedSize(30, 20)
            self.end_color_btn.setStyleSheet("background-color: #FF6347; border: 1px solid white; border-radius: 3px;")
            self.end_color_btn.clicked.connect(lambda: self.pick_gradient_color("end"))
            self.end_color = "#FF6347"

            end_label = QLabel("End")
            end_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px;")

            colors_layout.addWidget(self.start_color_btn)
            colors_layout.addWidget(start_label)
            colors_layout.addWidget(self.end_color_btn)
            colors_layout.addWidget(end_label)
            colors_layout.addStretch()

            details_layout.addWidget(colors_container)

        # Fade slider (for color properties only)
        if control_type == "color":
            fade_container = QWidget()
            fade_layout = QHBoxLayout(fade_container)
            fade_layout.setContentsMargins(0, 5, 0, 0)
            fade_layout.setSpacing(5)

            fade_label = QLabel("Fade:")
            fade_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 35px;")
            fade_layout.addWidget(fade_label)

            self.fade_slider = QSlider(Qt.Orientation.Horizontal)
            self.fade_slider.setMinimum(0)
            self.fade_slider.setMaximum(100)
            self.fade_slider.setValue(0)
            self.fade_slider.setStyleSheet(self._get_slider_style())
            self.fade_slider.valueChanged.connect(self.on_fade_changed)
            fade_layout.addWidget(self.fade_slider)

            self.fade_display = QLabel("0%")
            self.fade_display.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 35px;")
            fade_layout.addWidget(self.fade_display)

            details_layout.addWidget(fade_container)

        main_layout.addWidget(self.details_widget)

        # Initialize with defaults
        self.data_min = 0
        self.data_max = 100
        self.data_unit = ""
        self._update_property_metadata()

    def _update_property_metadata(self):
        """Update slider ranges based on selected property"""
        prop_name = self.current_property.lower().replace(" ", "_")
        metadata = get_molecule_property_metadata(prop_name)

        self.data_min = metadata["min_value"]
        self.data_max = metadata["max_value"]
        self.data_unit = metadata["unit"]

        self._update_displays()

    def _update_displays(self):
        """Update slider display values"""
        # Guard against being called before sliders are created
        if not hasattr(self, 'min_slider') or not hasattr(self, 'max_slider'):
            return
        min_t = self.min_slider.value() / 1000.0
        max_t = self.max_slider.value() / 1000.0

        min_val = self.data_min + min_t * (self.data_max - self.data_min)
        max_val = self.data_min + max_t * (self.data_max - self.data_min)

        if self.data_unit:
            self.min_display.setText(f"{min_val:.1f} {self.data_unit}")
            self.max_display.setText(f"{max_val:.1f} {self.data_unit}")
        else:
            self.min_display.setText(f"{min_val:.1f}")
            self.max_display.setText(f"{max_val:.1f}")

    def on_property_selection_changed(self, idx):
        """Handle property selection change"""
        prop_display = self.available_properties[idx]
        self.current_property = prop_display.lower().replace(" ", "_")
        self._update_property_metadata()

        # Reset sliders to full range (guard against being called before sliders exist)
        if hasattr(self, 'min_slider') and hasattr(self, 'max_slider'):
            self.min_slider.setValue(0)
            self.max_slider.setValue(1000)

        self.property_changed.emit(self.property_key, self.current_property)

    def on_filter_changed(self):
        """Handle filter slider changes"""
        self._update_displays()

        min_t = self.min_slider.value() / 1000.0
        max_t = self.max_slider.value() / 1000.0

        min_val = self.data_min + min_t * (self.data_max - self.data_min)
        max_val = self.data_min + max_t * (self.data_max - self.data_min)

        self.filter_range_changed.emit(self.property_key, min_val, max_val)

    def on_fade_changed(self, value):
        """Handle fade slider change"""
        self.fade_display.setText(f"{value}%")
        # Notify parent panel
        if hasattr(self.parent_panel, 'on_fade_changed'):
            self.parent_panel.on_fade_changed(self.property_key, value / 100.0)

    def pick_gradient_color(self, which):
        """Open color picker for gradient start/end"""
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor

        current = self.start_color if which == "start" else self.end_color
        color = QColorDialog.getColor(QColor(current), self, f"Choose {which.title()} Color")

        if color.isValid():
            hex_color = color.name()
            if which == "start":
                self.start_color = hex_color
                self.start_color_btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid white; border-radius: 3px;")
            else:
                self.end_color = hex_color
                self.end_color_btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid white; border-radius: 3px;")

            self.gradient_colors_changed.emit(self.property_key, self.start_color, self.end_color)

    def toggle_expanded(self):
        """Toggle expanded/collapsed state"""
        self.is_expanded = not self.is_expanded
        self.expand_btn.setArrowType(Qt.ArrowType.DownArrow if self.is_expanded else Qt.ArrowType.RightArrow)
        self.details_widget.setVisible(self.is_expanded)

    def _get_combo_style(self):
        return """
            QComboBox {
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid #764ba2;
                padding: 3px 5px;
                border-radius: 3px;
                font-size: 9px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: rgba(30, 30, 50, 250);
                color: white;
                selection-background-color: #764ba2;
            }
        """

    def _get_slider_style(self):
        return """
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(60, 60, 80, 200);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #764ba2;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """


class MoleculeControlPanel(QWidget):
    """Control panel for molecule visualization settings"""

    # Data management signals
    add_requested = Signal()
    edit_requested = Signal()
    remove_requested = Signal()
    reset_requested = Signal()
    create_requested = Signal()
    export_requested = Signal()
    import_requested = Signal()
    duplicate_requested = Signal()

    # AI generation signals
    ai_generate_requested = Signal()
    ai_settings_requested = Signal()

    # 3D transform signal (replaces rotation_changed)
    transform_changed = Signal(Transform3D)

    # Legacy 3D rotation signal for backwards compatibility
    rotation_changed = Signal(float, float, float)

    def __init__(self, table_widget):
        super().__init__()
        self.table = table_widget
        self.setup_ui()

    def setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: rgb(20, 20, 35); }
            QScrollBar:vertical {
                background: rgba(40, 40, 60, 100);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(79, 195, 247, 150);
                border-radius: 5px;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background: rgb(20, 20, 35);")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        title = QLabel("Molecule Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        layout.addWidget(title)

        # Layout Mode Selection (always expanded)
        layout.addWidget(self._create_layout_mode_group())

        # Visual Property Encodings (collapsible)
        layout.addWidget(self._create_visual_properties_group())

        # Filter Options (collapsible)
        layout.addWidget(self._create_filter_options_group())

        # View Controls
        layout.addWidget(self._create_view_controls_group())

        # 3D Rotation Controls
        layout.addWidget(self._create_rotation_controls_group())

        # AI Generation
        layout.addWidget(self._create_ai_generation_group())

        # Data Management
        layout.addWidget(self._create_data_management_group())

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_layout_mode_group(self):
        """Create layout mode selection group with all 8+ modes"""
        group = QGroupBox("Layout Mode")
        group.setStyleSheet(self._get_group_style("#667eea"))
        layout = QVBoxLayout()

        # All layout modes
        self.grid_radio = QRadioButton("Grid View")
        self.mass_radio = QRadioButton("Mass Order")
        self.polarity_radio = QRadioButton("By Polarity")
        self.bond_radio = QRadioButton("By Bond Type")
        self.geometry_radio = QRadioButton("By Geometry")
        self.phase_diagram_radio = QRadioButton("Phase Diagram")
        self.dipole_radio = QRadioButton("Dipole-Polarity")
        self.density_radio = QRadioButton("Density-Mass")
        self.bond_complexity_radio = QRadioButton("Bond Complexity")

        self.grid_radio.setChecked(True)

        radio_style = self._get_radio_style()
        all_radios = [
            self.grid_radio, self.mass_radio, self.polarity_radio,
            self.bond_radio, self.geometry_radio, self.phase_diagram_radio,
            self.dipole_radio, self.density_radio, self.bond_complexity_radio
        ]

        for radio in all_radios:
            radio.setStyleSheet(radio_style)
            layout.addWidget(radio)

        # Connect signals
        self.grid_radio.toggled.connect(lambda: self._on_layout_changed("grid") if self.grid_radio.isChecked() else None)
        self.mass_radio.toggled.connect(lambda: self._on_layout_changed("mass_order") if self.mass_radio.isChecked() else None)
        self.polarity_radio.toggled.connect(lambda: self._on_layout_changed("polarity") if self.polarity_radio.isChecked() else None)
        self.bond_radio.toggled.connect(lambda: self._on_layout_changed("bond_type") if self.bond_radio.isChecked() else None)
        self.geometry_radio.toggled.connect(lambda: self._on_layout_changed("geometry") if self.geometry_radio.isChecked() else None)
        self.phase_diagram_radio.toggled.connect(lambda: self._on_layout_changed("phase_diagram") if self.phase_diagram_radio.isChecked() else None)
        self.dipole_radio.toggled.connect(lambda: self._on_layout_changed("dipole") if self.dipole_radio.isChecked() else None)
        self.density_radio.toggled.connect(lambda: self._on_layout_changed("density") if self.density_radio.isChecked() else None)
        self.bond_complexity_radio.toggled.connect(lambda: self._on_layout_changed("bond_complexity") if self.bond_complexity_radio.isChecked() else None)

        # Zoom controls info
        zoom_info = QLabel("Camera Controls:\n- Scroll wheel: Zoom\n- Ctrl+drag: Pan")
        zoom_info.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; margin-top: 8px;")
        zoom_info.setWordWrap(True)
        layout.addWidget(zoom_info)

        # Reset view button
        reset_btn = QPushButton("Reset View")
        reset_btn.clicked.connect(self._on_reset_view)
        reset_btn.setToolTip("Reset zoom and pan to default view")
        reset_btn.setStyleSheet("""
            QPushButton {
                background: rgba(102, 126, 234, 150);
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
                font-size: 10px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background: rgba(102, 126, 234, 200);
            }
        """)
        layout.addWidget(reset_btn)

        group.setLayout(layout)
        return group

    def _create_visual_properties_group(self):
        """Create visual property encodings with expandable controls"""
        collapsible = CollapsibleBox("Visual Property Encodings", "#764ba2")

        # Comprehensive property options for molecules (all numeric properties)
        color_properties = [
            "Molecular Mass", "Boiling Point", "Melting Point", "Density",
            "Dipole Moment", "Vapor Pressure", "Solubility", "Bond Angle",
            "Electronegativity Diff", "Number of Atoms", "Number of Bonds",
            "Avg Bond Length", "None"
        ]
        size_properties = [
            "Molecular Mass", "Density", "Dipole Moment", "Bond Angle",
            "Number of Atoms", "Number of Bonds", "Avg Bond Length",
            "Vapor Pressure", "Solubility", "Electronegativity Diff", "None"
        ]
        glow_properties = [
            "Dipole Moment", "Electronegativity Diff", "Molecular Mass",
            "Density", "Melting Point", "Boiling Point", "Vapor Pressure", "None"
        ]

        # Section header for color encodings
        color_header = QLabel("Color Encodings:")
        color_header.setStyleSheet("color: #f093fb; font-weight: bold; font-size: 11px; margin-top: 5px;")
        collapsible.content_layout.addWidget(color_header)

        # 1. Card Color Gradient -> Molecular Mass
        self.fill_color_control = MoleculePropertyControl(
            "Card Color Gradient", "fill_color", self, color_properties,
            control_type="color", default_property="molecular_mass"
        )
        self.fill_color_control.property_changed.connect(self._on_property_changed)
        self.fill_color_control.filter_range_changed.connect(self._on_filter_range_changed)
        self.fill_color_control.gradient_colors_changed.connect(self._on_gradient_colors_changed)
        collapsible.content_layout.addWidget(self.fill_color_control)

        # 2. Border Colour -> Boiling Point
        self.border_color_control = MoleculePropertyControl(
            "Border Colour", "border_color", self, color_properties,
            control_type="color", default_property="boiling_point"
        )
        self.border_color_control.property_changed.connect(self._on_property_changed)
        self.border_color_control.filter_range_changed.connect(self._on_filter_range_changed)
        self.border_color_control.gradient_colors_changed.connect(self._on_gradient_colors_changed)
        collapsible.content_layout.addWidget(self.border_color_control)

        # 3. Glow/Highlight -> Dipole Moment (polarity indicator)
        self.glow_color_control = MoleculePropertyControl(
            "Glow/Highlight", "glow_color", self, glow_properties,
            control_type="color", default_property="dipole_moment"
        )
        self.glow_color_control.property_changed.connect(self._on_property_changed)
        self.glow_color_control.filter_range_changed.connect(self._on_filter_range_changed)
        self.glow_color_control.gradient_colors_changed.connect(self._on_gradient_colors_changed)
        collapsible.content_layout.addWidget(self.glow_color_control)

        # 4. Symbol Text Colour -> Density
        self.symbol_text_color_control = MoleculePropertyControl(
            "Text Colour", "symbol_text_color", self, color_properties,
            control_type="color", default_property="density"
        )
        self.symbol_text_color_control.property_changed.connect(self._on_property_changed)
        self.symbol_text_color_control.filter_range_changed.connect(self._on_filter_range_changed)
        self.symbol_text_color_control.gradient_colors_changed.connect(self._on_gradient_colors_changed)
        collapsible.content_layout.addWidget(self.symbol_text_color_control)

        # Section header for size/intensity encodings
        size_header = QLabel("Size & Intensity Encodings:")
        size_header.setStyleSheet("color: #4fc3f7; font-weight: bold; font-size: 11px; margin-top: 10px;")
        collapsible.content_layout.addWidget(size_header)

        # 5. Border Intensity -> Melting Point
        self.border_size_control = MoleculePropertyControl(
            "Border Intensity", "border_size", self, size_properties,
            control_type="size", default_property="melting_point"
        )
        self.border_size_control.property_changed.connect(self._on_property_changed)
        self.border_size_control.filter_range_changed.connect(self._on_filter_range_changed)
        collapsible.content_layout.addWidget(self.border_size_control)

        # 6. Card Size Scaling -> Number of Atoms
        self.card_size_control = MoleculePropertyControl(
            "Card Size", "card_size", self, size_properties,
            control_type="size", default_property="num_atoms"
        )
        self.card_size_control.property_changed.connect(self._on_property_changed)
        self.card_size_control.filter_range_changed.connect(self._on_filter_range_changed)
        collapsible.content_layout.addWidget(self.card_size_control)

        # 7. Glow Intensity -> Electronegativity Diff
        self.glow_intensity_control = MoleculePropertyControl(
            "Glow Intensity", "glow_intensity", self, size_properties,
            control_type="size", default_property="electronegativity_diff"
        )
        self.glow_intensity_control.property_changed.connect(self._on_property_changed)
        self.glow_intensity_control.filter_range_changed.connect(self._on_filter_range_changed)
        collapsible.content_layout.addWidget(self.glow_intensity_control)

        # 8. Opacity -> Number of Bonds
        self.opacity_control = MoleculePropertyControl(
            "Opacity", "opacity", self, size_properties,
            control_type="size", default_property="num_bonds"
        )
        self.opacity_control.property_changed.connect(self._on_property_changed)
        self.opacity_control.filter_range_changed.connect(self._on_filter_range_changed)
        collapsible.content_layout.addWidget(self.opacity_control)

        # Reset button to restore default mappings
        reset_button = QPushButton("Reset to Defaults")
        reset_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #7688f0, stop:1 #8658b8);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #5567d0, stop:1 #653a92);
            }
        """)
        reset_button.clicked.connect(self._reset_property_mappings)
        collapsible.content_layout.addWidget(reset_button)

        # Open by default
        collapsible.toggle_button.setChecked(True)
        collapsible.on_toggle()

        return collapsible

    def _create_filter_options_group(self):
        """Create filter options with checkboxes for state, polarity, bond type, category"""
        collapsible = CollapsibleBox("Filter Options", "#4CAF50")

        # State Filter (Solid, Liquid, Gas)
        state_label = QLabel("State at STP:")
        state_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 5px;")
        collapsible.content_layout.addWidget(state_label)

        state_container = QWidget()
        state_layout = QHBoxLayout(state_container)
        state_layout.setContentsMargins(10, 0, 0, 0)
        state_layout.setSpacing(15)

        self.solid_check = QCheckBox("Solid")
        self.liquid_check = QCheckBox("Liquid")
        self.gas_check = QCheckBox("Gas")

        for check in [self.solid_check, self.liquid_check, self.gas_check]:
            check.setChecked(True)
            check.setStyleSheet(self._get_checkbox_style("#795548"))
            check.stateChanged.connect(self._on_state_filter_changed)
            state_layout.addWidget(check)

        state_layout.addStretch()
        collapsible.content_layout.addWidget(state_container)

        # Polarity Filter (Polar, Nonpolar)
        polarity_label = QLabel("Polarity:")
        polarity_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 10px;")
        collapsible.content_layout.addWidget(polarity_label)

        polarity_container = QWidget()
        polarity_layout = QHBoxLayout(polarity_container)
        polarity_layout.setContentsMargins(10, 0, 0, 0)
        polarity_layout.setSpacing(15)

        self.polar_check = QCheckBox("Polar")
        self.nonpolar_check = QCheckBox("Nonpolar")

        for check in [self.polar_check, self.nonpolar_check]:
            check.setChecked(True)
            check.setStyleSheet(self._get_checkbox_style("#2196F3"))
            check.stateChanged.connect(self._on_polarity_filter_changed)
            polarity_layout.addWidget(check)

        polarity_layout.addStretch()
        collapsible.content_layout.addWidget(polarity_container)

        # Bond Type Filter (Ionic, Covalent, Polar Covalent)
        bond_label = QLabel("Bond Type:")
        bond_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 10px;")
        collapsible.content_layout.addWidget(bond_label)

        bond_container = QWidget()
        bond_layout = QHBoxLayout(bond_container)
        bond_layout.setContentsMargins(10, 0, 0, 0)
        bond_layout.setSpacing(15)

        self.ionic_check = QCheckBox("Ionic")
        self.covalent_check = QCheckBox("Covalent")
        self.polar_covalent_check = QCheckBox("Polar Covalent")

        for check in [self.ionic_check, self.covalent_check, self.polar_covalent_check]:
            check.setChecked(True)
            check.setStyleSheet(self._get_checkbox_style("#9C27B0"))
            check.stateChanged.connect(self._on_bond_type_filter_changed)
            bond_layout.addWidget(check)

        bond_layout.addStretch()
        collapsible.content_layout.addWidget(bond_container)

        # Category Filter (Organic, Inorganic)
        category_label = QLabel("Category:")
        category_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 10px;")
        collapsible.content_layout.addWidget(category_label)

        category_container = QWidget()
        category_layout = QHBoxLayout(category_container)
        category_layout.setContentsMargins(10, 0, 0, 0)
        category_layout.setSpacing(15)

        self.organic_check = QCheckBox("Organic")
        self.inorganic_check = QCheckBox("Inorganic")

        for check in [self.organic_check, self.inorganic_check]:
            check.setChecked(True)
            check.setStyleSheet(self._get_checkbox_style("#8BC34A"))
            check.stateChanged.connect(self._on_category_filter_changed)
            category_layout.addWidget(check)

        category_layout.addStretch()
        collapsible.content_layout.addWidget(category_container)

        # Clear all filters button
        clear_btn = QPushButton("Clear All Filters")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 87, 34, 180);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 15px;
            }
            QPushButton:hover {
                background: rgba(255, 87, 34, 220);
            }
        """)
        clear_btn.clicked.connect(self._on_clear_filters)
        collapsible.content_layout.addWidget(clear_btn)

        # Open by default
        collapsible.toggle_button.setChecked(True)
        collapsible.on_toggle()

        return collapsible

    def _create_view_controls_group(self):
        """Create view control buttons"""
        collapsible = CollapsibleBox("View Controls", "#f093fb")

        # 3D Visualization toggle
        self.show_3d_check = QCheckBox("Show 3D Molecular Structure")
        self.show_3d_check.setStyleSheet(self._get_checkbox_style("#f093fb"))
        self.show_3d_check.setChecked(False)
        self.show_3d_check.stateChanged.connect(self._on_3d_toggle_changed)
        collapsible.content_layout.addWidget(self.show_3d_check)

        # Bond visualization toggle
        self.show_bonds_check = QCheckBox("Show Bond Lines")
        self.show_bonds_check.setStyleSheet(self._get_checkbox_style("#f093fb"))
        self.show_bonds_check.setChecked(True)
        self.show_bonds_check.stateChanged.connect(self._on_bonds_toggle_changed)
        collapsible.content_layout.addWidget(self.show_bonds_check)

        # Atom labels toggle
        self.show_labels_check = QCheckBox("Show Atom Labels")
        self.show_labels_check.setStyleSheet(self._get_checkbox_style("#f093fb"))
        self.show_labels_check.setChecked(True)
        self.show_labels_check.stateChanged.connect(self._on_labels_toggle_changed)
        collapsible.content_layout.addWidget(self.show_labels_check)

        # Info label
        info_label = QLabel("Scroll to zoom\nCtrl+drag to pan\nClick molecule for details")
        info_label.setStyleSheet("color: rgba(255,255,255,150); font-size: 9px; margin-top: 10px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        collapsible.content_layout.addWidget(info_label)

        return collapsible

    def _create_rotation_controls_group(self):
        """Create 3D transform controls using unified widget"""
        self.transform_controls = TransformControlsWidget(
            title="3D Transform Controls",
            show_rotation=True,
            show_translation=True,
            show_zoom=True,
            accent_color="#ff7043"
        )
        self.transform_controls.transform_changed.connect(self._on_transform_changed)
        return self.transform_controls

    def _create_ai_generation_group(self):
        """Create AI generation controls group"""
        self.ai_widget = AIGenerationWidget("molecule", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        return self.ai_widget

    def refresh_ai_status(self):
        """Refresh the AI API configuration status"""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()

    def _create_data_management_group(self):
        """Create data management controls group"""
        group = QGroupBox("Data Management")
        group.setStyleSheet(self._get_group_style("#26a69a"))
        layout = QVBoxLayout()

        # Buttons row
        btn_layout = QHBoxLayout()

        button_style = """
            QPushButton {
                background: rgba(38, 166, 154, 150);
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(38, 166, 154, 200);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """

        self.add_btn = QPushButton("Add")
        self.add_btn.setStyleSheet(button_style)
        self.add_btn.clicked.connect(self.add_requested.emit)
        self.add_btn.setToolTip("Add a new item to the collection (Ctrl+N)")
        self.add_btn.setShortcut("Ctrl+N")
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setStyleSheet(button_style)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.edit_requested.emit)
        self.edit_btn.setToolTip("Edit the selected item (Ctrl+E)")
        self.edit_btn.setShortcut("Ctrl+E")
        btn_layout.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setStyleSheet(button_style)
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_requested.emit)
        self.remove_btn.setToolTip("Remove the selected item (Del)")
        self.remove_btn.setShortcut("Del")
        btn_layout.addWidget(self.remove_btn)

        layout.addLayout(btn_layout)

        # Export/Import/Duplicate row
        btn_layout2 = QHBoxLayout()

        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet(button_style)
        self.export_btn.setEnabled(False)  # Enable when item selected
        self.export_btn.clicked.connect(self.export_requested.emit)
        self.export_btn.setToolTip("Export selected item to file (Ctrl+Shift+E)")
        self.export_btn.setShortcut("Ctrl+Shift+E")
        btn_layout2.addWidget(self.export_btn)

        self.import_btn = QPushButton("Import")
        self.import_btn.setStyleSheet(button_style)
        self.import_btn.clicked.connect(self.import_requested.emit)
        self.import_btn.setToolTip("Import item from file (Ctrl+Shift+I)")
        self.import_btn.setShortcut("Ctrl+Shift+I")
        btn_layout2.addWidget(self.import_btn)

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.setStyleSheet(button_style)
        self.duplicate_btn.setEnabled(False)  # Enable when item selected
        self.duplicate_btn.clicked.connect(self.duplicate_requested.emit)
        self.duplicate_btn.setToolTip("Create a copy of selected item (Ctrl+D)")
        self.duplicate_btn.setShortcut("Ctrl+D")
        btn_layout2.addWidget(self.duplicate_btn)

        layout.addLayout(btn_layout2)

        # Create from Elements button
        self.create_btn = QPushButton("Create from Elements")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #764ba2, stop:1 #667eea);
            }
        """)
        self.create_btn.clicked.connect(self.create_requested.emit)
        self.create_btn.setToolTip("Create new item from components")
        layout.addWidget(self.create_btn)

        # Reset to Defaults button
        self.reset_data_btn = QPushButton("Reset to Defaults")
        self.reset_data_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #ef5350, stop:1 #e53935);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #f44336, stop:1 #d32f2f);
            }
        """)
        self.reset_data_btn.clicked.connect(self.reset_requested.emit)
        self.reset_data_btn.setToolTip("Reset all data to defaults (cannot be undone)")
        layout.addWidget(self.reset_data_btn)

        # Item count label
        self.item_count_label = QLabel("Items: 0")
        self.item_count_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px; margin-top: 5px;")
        layout.addWidget(self.item_count_label)

        group.setLayout(layout)
        return group

    # === Event Handlers ===

    def _on_layout_changed(self, mode):
        """Handle layout mode change"""
        self.table.set_layout_mode(mode)

    def _on_property_changed(self, property_key, property_name):
        """Handle property mapping change"""
        # Route to specific methods for new visual encoding types
        if property_key == 'card_size':
            if hasattr(self.table, 'set_card_size_mapping'):
                self.table.set_card_size_mapping(property_name)
        elif property_key == 'glow_intensity':
            if hasattr(self.table, 'set_glow_intensity_mapping'):
                self.table.set_glow_intensity_mapping(property_name)
        elif property_key == 'opacity':
            if hasattr(self.table, 'set_opacity_mapping'):
                self.table.set_opacity_mapping(property_name)
        elif hasattr(self.table, 'set_property_mapping'):
            self.table.set_property_mapping(property_key, property_name)

    def _on_filter_range_changed(self, property_key, min_val, max_val):
        """Handle filter range change"""
        if hasattr(self.table, 'set_property_filter_range'):
            self.table.set_property_filter_range(property_key, min_val, max_val)

    def _on_gradient_colors_changed(self, property_key, start_color, end_color):
        """Handle gradient color change"""
        if hasattr(self.table, 'set_gradient_colors'):
            self.table.set_gradient_colors(property_key, start_color, end_color)

    def on_fade_changed(self, property_key, fade_value):
        """Handle fade value change"""
        if hasattr(self.table, 'set_fade_value'):
            self.table.set_fade_value(property_key, fade_value)

    def _on_state_filter_changed(self):
        """Handle state filter checkbox changes"""
        states = []
        if self.solid_check.isChecked():
            states.append("Solid")
        if self.liquid_check.isChecked():
            states.append("Liquid")
        if self.gas_check.isChecked():
            states.append("Gas")

        if hasattr(self.table, 'set_state_filters'):
            self.table.set_state_filters(states)
        elif hasattr(self.table, 'set_state_filter'):
            # Fallback: use single state if multiple not supported
            self.table.set_state_filter(states[0] if len(states) == 1 else None)

    def _on_polarity_filter_changed(self):
        """Handle polarity filter checkbox changes"""
        polarities = []
        if self.polar_check.isChecked():
            polarities.append("Polar")
        if self.nonpolar_check.isChecked():
            polarities.append("Nonpolar")

        if hasattr(self.table, 'set_polarity_filters'):
            self.table.set_polarity_filters(polarities)
        elif hasattr(self.table, 'set_polarity_filter'):
            self.table.set_polarity_filter(polarities[0] if len(polarities) == 1 else None)

    def _on_bond_type_filter_changed(self):
        """Handle bond type filter checkbox changes"""
        bond_types = []
        if self.ionic_check.isChecked():
            bond_types.append("Ionic")
        if self.covalent_check.isChecked():
            bond_types.append("Covalent")
        if self.polar_covalent_check.isChecked():
            bond_types.append("Polar Covalent")

        if hasattr(self.table, 'set_bond_type_filters'):
            self.table.set_bond_type_filters(bond_types)

    def _on_category_filter_changed(self):
        """Handle category filter checkbox changes"""
        categories = []
        if self.organic_check.isChecked():
            categories.append("Organic")
        if self.inorganic_check.isChecked():
            categories.append("Inorganic")

        if hasattr(self.table, 'set_category_filters'):
            self.table.set_category_filters(categories)
        elif hasattr(self.table, 'set_category_filter'):
            self.table.set_category_filter(categories[0] if len(categories) == 1 else None)

    def _on_3d_toggle_changed(self, state):
        """Handle 3D visualization toggle"""
        if hasattr(self.table, 'set_3d_mode'):
            self.table.set_3d_mode(state == Qt.CheckState.Checked.value)

    def _on_bonds_toggle_changed(self, state):
        """Handle bond lines toggle"""
        if hasattr(self.table, 'set_show_bonds'):
            self.table.set_show_bonds(state == Qt.CheckState.Checked.value)

    def _on_labels_toggle_changed(self, state):
        """Handle atom labels toggle"""
        if hasattr(self.table, 'set_show_labels'):
            self.table.set_show_labels(state == Qt.CheckState.Checked.value)

    def _on_reset_view(self):
        """Reset view to defaults"""
        if hasattr(self.table, 'reset_view'):
            self.table.reset_view()

    def _on_transform_changed(self, transform: Transform3D):
        """Handle 3D transform changes from unified control widget"""
        # Emit transform signal
        self.transform_changed.emit(transform)

        # Emit legacy rotation signal for backwards compatibility
        self.rotation_changed.emit(transform.pitch, transform.yaw, transform.roll)

        # Notify table widget directly
        if hasattr(self.table, 'set_rotation'):
            self.table.set_rotation(transform.pitch, transform.yaw, transform.roll)

        # Store full transform if table supports it
        if hasattr(self.table, 'transform_3d'):
            self.table.transform_3d = transform

    def _on_clear_filters(self):
        """Clear all filters"""
        # Reset all checkboxes to checked
        for check in [self.solid_check, self.liquid_check, self.gas_check,
                      self.polar_check, self.nonpolar_check,
                      self.ionic_check, self.covalent_check, self.polar_covalent_check,
                      self.organic_check, self.inorganic_check]:
            check.setChecked(True)

    def _reset_property_mappings(self):
        """Reset all property controls to their default mappings"""
        # Reset fill color (Card Color Gradient -> Molecular Mass)
        self.fill_color_control.property_combo.setCurrentIndex(0)  # Molecular Mass
        self.fill_color_control.min_slider.setValue(0)
        self.fill_color_control.max_slider.setValue(1000)

        # Reset border color (Border Colour -> Boiling Point)
        self.border_color_control.property_combo.setCurrentIndex(1)  # Boiling Point
        self.border_color_control.min_slider.setValue(0)
        self.border_color_control.max_slider.setValue(1000)

        # Reset glow color (Glow/Highlight -> Dipole Moment)
        self.glow_color_control.property_combo.setCurrentIndex(0)  # Dipole Moment
        self.glow_color_control.min_slider.setValue(0)
        self.glow_color_control.max_slider.setValue(1000)

        # Reset symbol text color (Text Colour -> Density)
        self.symbol_text_color_control.property_combo.setCurrentIndex(3)  # Density
        self.symbol_text_color_control.min_slider.setValue(0)
        self.symbol_text_color_control.max_slider.setValue(1000)

        # Reset border size (Border Intensity -> Melting Point)
        self.border_size_control.property_combo.setCurrentIndex(2)  # Melting Point (index 2 in size_properties)
        self.border_size_control.min_slider.setValue(0)
        self.border_size_control.max_slider.setValue(1000)

        # Reset card size (Card Size -> Number of Atoms)
        self.card_size_control.property_combo.setCurrentIndex(4)  # Number of Atoms
        self.card_size_control.min_slider.setValue(0)
        self.card_size_control.max_slider.setValue(1000)

        # Reset glow intensity (Glow Intensity -> Electronegativity Diff)
        self.glow_intensity_control.property_combo.setCurrentIndex(9)  # Electronegativity Diff
        self.glow_intensity_control.min_slider.setValue(0)
        self.glow_intensity_control.max_slider.setValue(1000)

        # Reset opacity (Opacity -> Number of Bonds)
        self.opacity_control.property_combo.setCurrentIndex(5)  # Number of Bonds
        self.opacity_control.min_slider.setValue(0)
        self.opacity_control.max_slider.setValue(1000)

    # === Public API ===

    def set_item_selected(self, selected: bool):
        """Enable/disable edit and remove buttons based on selection state"""
        self.edit_btn.setEnabled(selected)
        self.remove_btn.setEnabled(selected)
        self.export_btn.setEnabled(selected)
        self.duplicate_btn.setEnabled(selected)

    def update_item_count(self, count):
        """Update the item count label"""
        self.item_count_label.setText(f"Items: {count}")

    # === Style Helpers ===

    def _get_group_style(self, color):
        return f"""
            QGroupBox {{
                color: white;
                border: 2px solid {color};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """

    def _get_radio_style(self):
        return """
            QRadioButton {
                color: white;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #667eea;
                border-radius: 8px;
                background: rgba(40, 40, 60, 200);
            }
            QRadioButton::indicator:checked {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5, stop:0 #667eea, stop:1 rgba(102, 126, 234, 100));
            }
        """

    def _get_checkbox_style(self, color):
        return f"""
            QCheckBox {{
                color: white;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {color};
                border-radius: 4px;
                background: rgba(40, 40, 60, 200);
            }}
            QCheckBox::indicator:checked {{
                background: {color};
            }}
        """

    def _get_combo_style(self):
        return """
            QComboBox {
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid #764ba2;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 11px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: rgba(30, 30, 50, 250);
                color: white;
                selection-background-color: #764ba2;
            }
        """
