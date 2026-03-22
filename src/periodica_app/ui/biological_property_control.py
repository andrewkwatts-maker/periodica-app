"""
Biological Property Control Widget
Reusable widget for visual property encodings across biological entity tabs.
Supports Amino Acids, Proteins, Nucleic Acids, Cell Components, Cells, and Biomaterials.

Based on the AlloyPropertyControl pattern from ui/alloy_control_panel.py.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QComboBox, QCheckBox, QPushButton, QFrame,
                                QSlider, QToolButton, QColorDialog)
from PySide6.QtCore import Qt, QPropertyAnimation, Signal
from PySide6.QtGui import QColor


class BiologicalPropertyControl(QWidget):
    """
    Expandable control for a single visual property with range controls and filtering
    for biological entities. Supports color gradients, fade, and min/max filtering.

    Signals:
        property_changed(str, int): Emitted when property selection changes (property_key, index)
        filter_changed(str, float, float): Emitted when filter range changes (property_key, min_val, max_val)
        color_changed(str, QColor, QColor): Emitted when gradient colors change (property_key, start, end)
    """

    # Signals for external listeners
    property_changed = Signal(str, int)
    filter_changed = Signal(str, float, float)
    color_changed = Signal(str, object, object)  # Using object for QColor compatibility

    # Biological property metadata organized by property name
    PROPERTY_METADATA = {
        # Amino Acid properties
        "None": {"min": 0, "max": 100, "unit": ""},
        "Category": {"min": 0, "max": 7, "unit": "", "type": "categorical",
                     "categories": ["Nonpolar", "Polar", "Basic", "Acidic", "Aromatic", "Sulfur", "Special"]},
        "Hydropathy": {"min": -4.5, "max": 4.5, "unit": ""},
        "Charge": {"min": -1, "max": 1, "unit": ""},
        "pI": {"min": 2.0, "max": 12.0, "unit": ""},
        "MW": {"min": 75, "max": 250, "unit": "Da"},
        "Molecular Weight": {"min": 75, "max": 250, "unit": "Da"},

        # Protein properties
        "Protein MW": {"min": 1000, "max": 1000000, "unit": "Da"},
        "Protein pI": {"min": 3.0, "max": 12.0, "unit": ""},
        "Structure %": {"min": 0, "max": 100, "unit": "%"},
        "Alpha Helix %": {"min": 0, "max": 100, "unit": "%"},
        "Beta Sheet %": {"min": 0, "max": 100, "unit": "%"},
        "Random Coil %": {"min": 0, "max": 100, "unit": "%"},
        "Function": {"min": 0, "max": 10, "unit": "", "type": "categorical",
                     "categories": ["Enzyme", "Structural", "Transport", "Signaling", "Defense", "Storage", "Motor", "Regulatory"]},

        # Nucleic Acid properties
        "Type": {"min": 0, "max": 5, "unit": "", "type": "categorical",
                 "categories": ["DNA", "RNA", "mRNA", "tRNA", "rRNA"]},
        "GC Content": {"min": 0, "max": 100, "unit": "%"},
        "Tm": {"min": 20, "max": 100, "unit": "C"},
        "Melting Temperature": {"min": 20, "max": 100, "unit": "C"},
        "Length": {"min": 1, "max": 10000, "unit": "bp"},

        # Cell Component properties
        "Component Type": {"min": 0, "max": 10, "unit": "", "type": "categorical",
                          "categories": ["Nucleus", "Mitochondria", "ER", "Golgi", "Ribosome", "Lysosome", "Peroxisome", "Cytoskeleton"]},
        "Compartment": {"min": 0, "max": 8, "unit": "", "type": "categorical",
                        "categories": ["Cytoplasm", "Nucleus", "Membrane", "Extracellular", "Organelle"]},
        "Size": {"min": 0.01, "max": 100, "unit": "um"},

        # Cell properties
        "Cell Type": {"min": 0, "max": 20, "unit": "", "type": "categorical",
                      "categories": ["Epithelial", "Muscle", "Nerve", "Blood", "Stem", "Immune", "Fat", "Bone"]},
        "Tissue": {"min": 0, "max": 15, "unit": "", "type": "categorical",
                   "categories": ["Epithelial", "Connective", "Muscle", "Nervous", "Blood", "Bone", "Cartilage"]},
        "Metabolic Rate": {"min": 0, "max": 100, "unit": ""},
        "Doubling Time": {"min": 0.5, "max": 72, "unit": "hr"},
        "Cell Size": {"min": 1, "max": 200, "unit": "um"},

        # Biomaterial properties
        "Material Type": {"min": 0, "max": 10, "unit": "", "type": "categorical",
                         "categories": ["Polymer", "Ceramic", "Metal", "Composite", "Hydrogel", "Natural"]},
        "Stiffness": {"min": 0.001, "max": 1000, "unit": "kPa"},
        "Young's Modulus": {"min": 0.001, "max": 1000, "unit": "kPa"},
        "Organ System": {"min": 0, "max": 12, "unit": "", "type": "categorical",
                        "categories": ["Cardiovascular", "Skeletal", "Muscular", "Nervous", "Digestive", "Respiratory", "Urinary", "Integumentary"]},
        "Porosity": {"min": 0, "max": 100, "unit": "%"},
        "Degradation Rate": {"min": 0, "max": 365, "unit": "days"},
        "Biocompatibility": {"min": 0, "max": 100, "unit": ""},
    }

    # Predefined property sets per biological tab
    TAB_PROPERTIES = {
        "amino_acids": {
            "color": ["None", "Category", "Hydropathy", "Charge", "pI", "MW"],
            "size": ["None", "MW", "Hydropathy", "Charge", "pI"],
            "defaults": {
                "fill_color": 1,       # Category
                "border_color": 2,     # Hydropathy
                "glow_color": 3,       # Charge
                "glow_intensity": 4,   # pI
                "symbol_text_color": 4, # pI
                "border_size": 1,      # MW
                "card_size": 2,        # Hydropathy
            }
        },
        "proteins": {
            "color": ["None", "Protein MW", "Protein pI", "Alpha Helix %", "Beta Sheet %",
                      "Random Coil %", "Function"],
            "size": ["None", "Protein MW", "Protein pI", "Alpha Helix %", "Beta Sheet %"],
            "defaults": {
                "fill_color": 6,       # Function
                "border_color": 2,     # pI
                "glow_color": 3,       # Alpha Helix %
                "glow_intensity": 4,   # Beta Sheet %
                "symbol_text_color": 1, # MW
                "border_size": 1,      # MW
                "card_size": 2,        # pI
            }
        },
        "nucleic_acids": {
            "color": ["None", "Type", "GC Content", "Tm", "Length"],
            "size": ["None", "Length", "GC Content", "Tm"],
            "defaults": {
                "fill_color": 1,       # Type
                "border_color": 2,     # GC Content
                "glow_color": 3,       # Tm
                "glow_intensity": 2,   # GC Content
                "symbol_text_color": 1, # Type
                "border_size": 1,      # Length
                "card_size": 2,        # GC Content
            }
        },
        "cell_components": {
            "color": ["None", "Component Type", "Compartment", "Size"],
            "size": ["None", "Size", "Component Type"],
            "defaults": {
                "fill_color": 1,       # Component Type
                "border_color": 2,     # Compartment
                "glow_color": 3,       # Size
                "glow_intensity": 3,   # Size
                "symbol_text_color": 1, # Component Type
                "border_size": 1,      # Size
                "card_size": 1,        # Size
            }
        },
        "cells": {
            "color": ["None", "Cell Type", "Tissue", "Metabolic Rate", "Doubling Time", "Cell Size"],
            "size": ["None", "Cell Size", "Metabolic Rate", "Doubling Time"],
            "defaults": {
                "fill_color": 1,       # Cell Type
                "border_color": 2,     # Tissue
                "glow_color": 3,       # Metabolic Rate
                "glow_intensity": 3,   # Metabolic Rate
                "symbol_text_color": 1, # Cell Type
                "border_size": 1,      # Cell Size
                "card_size": 3,        # Metabolic Rate
            }
        },
        "biomaterials": {
            "color": ["None", "Material Type", "Stiffness", "Organ System", "Porosity",
                      "Degradation Rate", "Biocompatibility"],
            "size": ["None", "Stiffness", "Porosity", "Degradation Rate", "Biocompatibility"],
            "defaults": {
                "fill_color": 1,       # Material Type
                "border_color": 2,     # Stiffness
                "glow_color": 3,       # Organ System
                "glow_intensity": 4,   # Porosity
                "symbol_text_color": 1, # Material Type
                "border_size": 1,      # Stiffness
                "card_size": 4,        # Porosity
            }
        }
    }

    def __init__(self, title: str, property_key: str, available_properties: list,
                 property_metadata: dict = None, control_type: str = "color",
                 default_index: int = 0, accent_color: str = "#66BB6A", parent=None):
        """
        Initialize BiologicalPropertyControl.

        Args:
            title: Display title for this control (e.g., "Fill Colour")
            property_key: Internal key for this control (e.g., "fill_color")
            available_properties: List of property names to show in dropdown
            property_metadata: Optional custom metadata dict (uses class defaults if None)
            control_type: "color" for gradient controls, "size" for size-only controls
            default_index: Default selection index in dropdown
            accent_color: Accent color for styling
            parent: Parent widget
        """
        super().__init__(parent)

        self.property_key = property_key
        self.control_type = control_type
        self.is_expanded = False
        self.default_index = default_index
        self.user_selected_index = default_index
        self.accent_color = accent_color
        self.available_properties = available_properties
        self.property_metadata = property_metadata if property_metadata else self.PROPERTY_METADATA

        # Initialize data bounds
        self.data_min = 0
        self.data_max = 100
        self.data_unit = ""
        self.current_property_name = "None"

        # Gradient colors
        self.gradient_start_color = QColor(64, 128, 255)
        self.gradient_end_color = QColor(255, 128, 64)

        self._setup_ui(title)

    def _setup_ui(self, title: str):
        """Build the widget UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 3, 5, 3)
        main_layout.setSpacing(3)

        # Header with expand/collapse button, title, and property selector
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        # Expand/collapse arrow button
        self.expand_btn = QToolButton()
        self.expand_btn.setArrowType(Qt.ArrowType.RightArrow)
        self.expand_btn.setStyleSheet("QToolButton { border: none; color: white; }")
        self.expand_btn.clicked.connect(self.toggle_expanded)
        header_layout.addWidget(self.expand_btn)

        # Title label
        title_label = QLabel(title + ":")
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px;")
        title_label.setMinimumWidth(110)
        header_layout.addWidget(title_label)

        # Property dropdown selector (ComboBox)
        self.property_combo = QComboBox()
        self.property_combo.addItems(self.available_properties)
        self.property_combo.setStyleSheet(self._get_combo_style())
        self.property_combo.currentIndexChanged.connect(self._on_property_selection_changed)
        header_layout.addWidget(self.property_combo, 1)

        # "Use Default" checkbox
        self.use_default_checkbox = QCheckBox("Default")
        self.use_default_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: rgba(255,255,255,200);
                font-size: 9px;
                spacing: 3px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {self.accent_color};
                border-radius: 3px;
                background: rgba(40, 40, 60, 150);
            }}
            QCheckBox::indicator:checked {{
                background: {self.accent_color};
            }}
        """)
        self.use_default_checkbox.toggled.connect(self._on_use_default_toggled)
        header_layout.addWidget(self.use_default_checkbox)

        main_layout.addWidget(header)

        # Expandable details section (CollapsibleBox-style)
        self.details_widget = QWidget()
        self.details_widget.setVisible(False)
        details_layout = QVBoxLayout(self.details_widget)
        details_layout.setContentsMargins(25, 5, 5, 5)
        details_layout.setSpacing(8)

        # Property mapping label
        mapping_label = QLabel("Property Mapping & Filtering:")
        mapping_label.setStyleSheet("color: rgba(255,255,255,200); font-size: 9px; font-weight: bold;")
        details_layout.addWidget(mapping_label)

        # Min/Max filter sliders container
        filter_container = QWidget()
        filter_layout = QVBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(5)

        # Min filter row
        min_row = QWidget()
        min_layout = QHBoxLayout(min_row)
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
        self.min_slider.valueChanged.connect(self._on_filter_range_changed)
        min_layout.addWidget(self.min_slider)

        self.min_display = QLabel("0")
        self.min_display.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 50px;")
        min_layout.addWidget(self.min_display)

        filter_layout.addWidget(min_row)

        # Max filter row
        max_row = QWidget()
        max_layout = QHBoxLayout(max_row)
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
        self.max_slider.valueChanged.connect(self._on_filter_range_changed)
        max_layout.addWidget(self.max_slider)

        self.max_display = QLabel("100")
        self.max_display.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 50px;")
        max_layout.addWidget(self.max_display)

        filter_layout.addWidget(max_row)
        details_layout.addWidget(filter_container)

        # Gradient color pickers (color properties only)
        if self.control_type == "color":
            gradient_container = QWidget()
            gradient_layout = QHBoxLayout(gradient_container)
            gradient_layout.setContentsMargins(0, 5, 0, 0)
            gradient_layout.setSpacing(10)

            gradient_label = QLabel("Gradient:")
            gradient_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px;")
            gradient_layout.addWidget(gradient_label)

            # Start color button
            self.start_color_btn = QPushButton()
            self.start_color_btn.setFixedSize(24, 24)
            self.start_color_btn.setStyleSheet(
                f"background: {self.gradient_start_color.name()}; "
                "border: 2px solid white; border-radius: 3px;"
            )
            self.start_color_btn.setToolTip("Choose gradient start color")
            self.start_color_btn.clicked.connect(lambda: self._pick_gradient_color("start"))
            gradient_layout.addWidget(self.start_color_btn)

            arrow_label = QLabel("->")
            arrow_label.setStyleSheet("color: rgba(255,255,255,150); font-size: 9px;")
            gradient_layout.addWidget(arrow_label)

            # End color button
            self.end_color_btn = QPushButton()
            self.end_color_btn.setFixedSize(24, 24)
            self.end_color_btn.setStyleSheet(
                f"background: {self.gradient_end_color.name()}; "
                "border: 2px solid white; border-radius: 3px;"
            )
            self.end_color_btn.setToolTip("Choose gradient end color")
            self.end_color_btn.clicked.connect(lambda: self._pick_gradient_color("end"))
            gradient_layout.addWidget(self.end_color_btn)

            gradient_layout.addStretch()
            details_layout.addWidget(gradient_container)

            # Fade slider
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
            self.fade_slider.valueChanged.connect(self._on_fade_changed)
            fade_layout.addWidget(self.fade_slider)

            self.fade_display = QLabel("0%")
            self.fade_display.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; min-width: 35px;")
            fade_layout.addWidget(self.fade_display)

            details_layout.addWidget(fade_container)

        main_layout.addWidget(self.details_widget)

    def _pick_gradient_color(self, which: str):
        """Open color picker dialog for gradient start or end color"""
        current = self.gradient_start_color if which == "start" else self.gradient_end_color
        color = QColorDialog.getColor(current, self, f"Choose Gradient {which.title()} Color")

        if color.isValid():
            if which == "start":
                self.gradient_start_color = color
                self.start_color_btn.setStyleSheet(
                    f"background: {color.name()}; border: 2px solid white; border-radius: 3px;"
                )
            else:
                self.gradient_end_color = color
                self.end_color_btn.setStyleSheet(
                    f"background: {color.name()}; border: 2px solid white; border-radius: 3px;"
                )

            # Emit color changed signal
            self.color_changed.emit(
                self.property_key,
                self.gradient_start_color,
                self.gradient_end_color
            )

    def _on_property_selection_changed(self, idx: int):
        """Handle property selection change"""
        property_name = self.available_properties[idx]
        self.current_property_name = property_name

        # Get property metadata for setting slider ranges
        metadata = self._get_property_metadata(property_name)
        if metadata:
            self.data_min = metadata.get("min", 0)
            self.data_max = metadata.get("max", 100)
            self.data_unit = metadata.get("unit", "")

        self._update_filter_displays()

        # Emit property changed signal
        self.property_changed.emit(self.property_key, idx)

    def _get_property_metadata(self, property_name: str) -> dict:
        """Get min/max/unit metadata for biological properties"""
        return self.property_metadata.get(property_name, {"min": 0, "max": 100, "unit": ""})

    def _on_filter_range_changed(self):
        """Handle filter range slider changes"""
        self._update_filter_displays()

        # Calculate actual values
        min_val = self.data_min + (self.min_slider.value() / 1000.0) * (self.data_max - self.data_min)
        max_val = self.data_min + (self.max_slider.value() / 1000.0) * (self.data_max - self.data_min)

        # Emit filter changed signal
        self.filter_changed.emit(self.property_key, min_val, max_val)

    def _update_filter_displays(self):
        """Update the filter display labels with formatted values"""
        min_val = self.data_min + (self.min_slider.value() / 1000.0) * (self.data_max - self.data_min)
        max_val = self.data_min + (self.max_slider.value() / 1000.0) * (self.data_max - self.data_min)

        # Format based on value magnitude
        if abs(self.data_max) > 1000:
            self.min_display.setText(f"{min_val:.0f}")
            self.max_display.setText(f"{max_val:.0f}")
        elif abs(self.data_max) < 1:
            self.min_display.setText(f"{min_val:.3f}")
            self.max_display.setText(f"{max_val:.3f}")
        else:
            self.min_display.setText(f"{min_val:.1f}")
            self.max_display.setText(f"{max_val:.1f}")

    def _on_fade_changed(self, value: int):
        """Handle fade slider change"""
        self.fade_display.setText(f"{value}%")

    def toggle_expanded(self):
        """Toggle expanded/collapsed state"""
        self.is_expanded = not self.is_expanded
        self.expand_btn.setArrowType(
            Qt.ArrowType.DownArrow if self.is_expanded else Qt.ArrowType.RightArrow
        )
        self.details_widget.setVisible(self.is_expanded)

    def _on_use_default_toggled(self, checked: bool):
        """Toggle using default value for this property"""
        self.property_combo.setEnabled(not checked)

        if checked:
            # Save current selection and revert to default
            self.user_selected_index = self.property_combo.currentIndex()
            self.property_combo.blockSignals(True)
            self.property_combo.setCurrentIndex(self.default_index)
            self.property_combo.blockSignals(False)
            self._on_property_selection_changed(self.default_index)
        else:
            # Restore user's previous selection
            self.property_combo.blockSignals(True)
            self.property_combo.setCurrentIndex(self.user_selected_index)
            self.property_combo.blockSignals(False)
            self._on_property_selection_changed(self.user_selected_index)

    def _get_combo_style(self) -> str:
        """Get stylesheet for combobox"""
        return f"""
            QComboBox {{
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid {self.accent_color};
                padding: 3px 5px;
                border-radius: 3px;
                font-size: 9px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: rgba(30, 30, 50, 250);
                color: white;
                selection-background-color: {self.accent_color};
            }}
        """

    def _get_slider_style(self) -> str:
        """Get stylesheet for sliders"""
        return f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(60, 60, 80, 200);
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {self.accent_color};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
        """

    # Public API methods

    def set_current_index(self, index: int):
        """Set the current property selection by index"""
        if 0 <= index < len(self.available_properties):
            self.property_combo.setCurrentIndex(index)

    def get_current_index(self) -> int:
        """Get the current property selection index"""
        return self.property_combo.currentIndex()

    def get_current_property(self) -> str:
        """Get the current property name"""
        return self.current_property_name

    def set_filter_range(self, min_val: float, max_val: float):
        """Set the filter range values"""
        # Convert to slider values (0-1000)
        if self.data_max > self.data_min:
            min_slider_val = int(((min_val - self.data_min) / (self.data_max - self.data_min)) * 1000)
            max_slider_val = int(((max_val - self.data_min) / (self.data_max - self.data_min)) * 1000)

            self.min_slider.blockSignals(True)
            self.max_slider.blockSignals(True)
            self.min_slider.setValue(max(0, min(1000, min_slider_val)))
            self.max_slider.setValue(max(0, min(1000, max_slider_val)))
            self.min_slider.blockSignals(False)
            self.max_slider.blockSignals(False)

            self._update_filter_displays()

    def get_filter_range(self) -> tuple:
        """Get the current filter range as (min, max)"""
        min_val = self.data_min + (self.min_slider.value() / 1000.0) * (self.data_max - self.data_min)
        max_val = self.data_min + (self.max_slider.value() / 1000.0) * (self.data_max - self.data_min)
        return (min_val, max_val)

    def set_gradient_colors(self, start: QColor, end: QColor):
        """Set the gradient colors"""
        if self.control_type == "color":
            self.gradient_start_color = start
            self.gradient_end_color = end
            self.start_color_btn.setStyleSheet(
                f"background: {start.name()}; border: 2px solid white; border-radius: 3px;"
            )
            self.end_color_btn.setStyleSheet(
                f"background: {end.name()}; border: 2px solid white; border-radius: 3px;"
            )

    def get_gradient_colors(self) -> tuple:
        """Get the gradient colors as (start_color, end_color)"""
        return (self.gradient_start_color, self.gradient_end_color)

    def set_fade(self, fade_percent: int):
        """Set the fade value (0-100)"""
        if self.control_type == "color":
            self.fade_slider.setValue(max(0, min(100, fade_percent)))

    def get_fade(self) -> int:
        """Get the fade value (0-100)"""
        if self.control_type == "color":
            return self.fade_slider.value()
        return 0

    def reset_to_default(self):
        """Reset control to default values"""
        self.property_combo.setCurrentIndex(self.default_index)
        self.min_slider.setValue(0)
        self.max_slider.setValue(1000)

        if self.control_type == "color":
            self.fade_slider.setValue(0)
            self.set_gradient_colors(QColor(64, 128, 255), QColor(255, 128, 64))

        self.use_default_checkbox.setChecked(False)
        self._update_filter_displays()


class CollapsibleBox(QWidget):
    """A collapsible widget container with animated expand/collapse"""

    def __init__(self, title: str = "", accent_color: str = "#66BB6A", parent=None):
        """
        Initialize CollapsibleBox.

        Args:
            title: Title displayed on the toggle button
            accent_color: Border/accent color for styling
            parent: Parent widget
        """
        super().__init__(parent)
        self.accent_color = accent_color

        # Toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: white;
                font-weight: bold;
                text-align: left;
                padding: 5px;
            }
        """)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.on_toggle)

        # Content area (starts collapsed)
        self.content_area = QFrame()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        self.content_area.setStyleSheet("""
            QFrame {
                border: none;
                background: transparent;
                padding: 5px;
            }
        """)

        # Content layout (for adding child widgets)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_area.setLayout(self.content_layout)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)
        self.setLayout(main_layout)

        # Animation for smooth expand/collapse
        self.toggle_animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.toggle_animation.setDuration(200)

    def on_toggle(self):
        """Handle toggle button click - expand or collapse content"""
        checked = self.toggle_button.isChecked()
        arrow_type = Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        self.toggle_button.setArrowType(arrow_type)

        if checked:
            # Expand
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
            pass

    def set_expanded(self, expanded: bool):
        """Programmatically set expanded state"""
        if expanded != self.toggle_button.isChecked():
            self.toggle_button.setChecked(expanded)
            self.on_toggle()

    def is_expanded(self) -> bool:
        """Check if box is currently expanded"""
        return self.toggle_button.isChecked()

    def add_widget(self, widget: QWidget):
        """Add a widget to the collapsible content area"""
        self.content_layout.addWidget(widget)


class BiologicalPropertyControlGroup(QWidget):
    """
    A complete group of BiologicalPropertyControl widgets for a biological entity tab.
    Provides all standard visual property controls with proper defaults for each tab type.

    Supported tab types:
        - amino_acids: Category, Hydropathy, Charge, pI, MW
        - proteins: MW, pI, Structure %, Function
        - nucleic_acids: Type, GC Content, Tm
        - cell_components: Type, Compartment
        - cells: Type, Tissue, Metabolic Rate
        - biomaterials: Type, Stiffness, Organ System
    """

    # Signals that aggregate individual control signals
    property_changed = Signal(str, int)
    filter_changed = Signal(str, float, float)
    color_changed = Signal(str, object, object)

    def __init__(self, tab_type: str, accent_color: str = "#66BB6A", parent=None):
        """
        Initialize BiologicalPropertyControlGroup.

        Args:
            tab_type: One of "amino_acids", "proteins", "nucleic_acids",
                      "cell_components", "cells", "biomaterials"
            accent_color: Accent color for styling
            parent: Parent widget
        """
        super().__init__(parent)

        self.tab_type = tab_type
        self.accent_color = accent_color
        self.controls = {}

        # Get tab-specific properties
        tab_config = BiologicalPropertyControl.TAB_PROPERTIES.get(
            tab_type,
            BiologicalPropertyControl.TAB_PROPERTIES["amino_acids"]
        )

        color_properties = tab_config["color"]
        size_properties = tab_config["size"]
        defaults = tab_config["defaults"]

        self._setup_ui(color_properties, size_properties, defaults)

    def _setup_ui(self, color_properties: list, size_properties: list, defaults: dict):
        """Build the control group UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create collapsible container
        self.collapsible = CollapsibleBox("Visual Property Encodings", self.accent_color)

        # Fill Colour control
        self.fill_color_control = BiologicalPropertyControl(
            "Fill Colour", "fill_color", color_properties,
            control_type="color", default_index=defaults.get("fill_color", 1),
            accent_color=self.accent_color
        )
        self.fill_color_control.set_current_index(defaults.get("fill_color", 1))
        self.fill_color_control.property_changed.connect(self.property_changed.emit)
        self.fill_color_control.filter_changed.connect(self.filter_changed.emit)
        self.fill_color_control.color_changed.connect(self.color_changed.emit)
        self.collapsible.add_widget(self.fill_color_control)
        self.controls["fill_color"] = self.fill_color_control

        # Border Colour control
        self.border_color_control = BiologicalPropertyControl(
            "Border Colour", "border_color", color_properties,
            control_type="color", default_index=defaults.get("border_color", 2),
            accent_color=self.accent_color
        )
        self.border_color_control.set_current_index(defaults.get("border_color", 2))
        self.border_color_control.property_changed.connect(self.property_changed.emit)
        self.border_color_control.filter_changed.connect(self.filter_changed.emit)
        self.border_color_control.color_changed.connect(self.color_changed.emit)
        self.collapsible.add_widget(self.border_color_control)
        self.controls["border_color"] = self.border_color_control

        # Glow Colour control
        self.glow_color_control = BiologicalPropertyControl(
            "Glow Colour", "glow_color", color_properties,
            control_type="color", default_index=defaults.get("glow_color", 3),
            accent_color=self.accent_color
        )
        self.glow_color_control.set_current_index(defaults.get("glow_color", 3))
        self.glow_color_control.property_changed.connect(self.property_changed.emit)
        self.glow_color_control.filter_changed.connect(self.filter_changed.emit)
        self.glow_color_control.color_changed.connect(self.color_changed.emit)
        self.collapsible.add_widget(self.glow_color_control)
        self.controls["glow_color"] = self.glow_color_control

        # Glow Intensity control (size-based, not color)
        self.glow_intensity_control = BiologicalPropertyControl(
            "Glow Intensity", "glow_intensity", size_properties,
            control_type="size", default_index=defaults.get("glow_intensity", 1),
            accent_color=self.accent_color
        )
        self.glow_intensity_control.set_current_index(defaults.get("glow_intensity", 1))
        self.glow_intensity_control.property_changed.connect(self.property_changed.emit)
        self.glow_intensity_control.filter_changed.connect(self.filter_changed.emit)
        self.collapsible.add_widget(self.glow_intensity_control)
        self.controls["glow_intensity"] = self.glow_intensity_control

        # Symbol Text Colour control
        self.symbol_text_color_control = BiologicalPropertyControl(
            "Symbol Text Colour", "symbol_text_color", color_properties,
            control_type="color", default_index=defaults.get("symbol_text_color", 1),
            accent_color=self.accent_color
        )
        self.symbol_text_color_control.set_current_index(defaults.get("symbol_text_color", 1))
        self.symbol_text_color_control.property_changed.connect(self.property_changed.emit)
        self.symbol_text_color_control.filter_changed.connect(self.filter_changed.emit)
        self.symbol_text_color_control.color_changed.connect(self.color_changed.emit)
        self.collapsible.add_widget(self.symbol_text_color_control)
        self.controls["symbol_text_color"] = self.symbol_text_color_control

        # Border Size control
        self.border_size_control = BiologicalPropertyControl(
            "Border Size", "border_size", size_properties,
            control_type="size", default_index=defaults.get("border_size", 1),
            accent_color=self.accent_color
        )
        self.border_size_control.set_current_index(defaults.get("border_size", 1))
        self.border_size_control.property_changed.connect(self.property_changed.emit)
        self.border_size_control.filter_changed.connect(self.filter_changed.emit)
        self.collapsible.add_widget(self.border_size_control)
        self.controls["border_size"] = self.border_size_control

        # Card Size control
        self.card_size_control = BiologicalPropertyControl(
            "Card Size", "card_size", size_properties,
            control_type="size", default_index=defaults.get("card_size", 1),
            accent_color=self.accent_color
        )
        self.card_size_control.set_current_index(defaults.get("card_size", 1))
        self.card_size_control.property_changed.connect(self.property_changed.emit)
        self.card_size_control.filter_changed.connect(self.filter_changed.emit)
        self.collapsible.add_widget(self.card_size_control)
        self.controls["card_size"] = self.card_size_control

        # Reset button
        reset_button = QPushButton("Reset Property Mappings")
        reset_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 {self.accent_color}, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #8B5CF6, stop:1 {self.accent_color});
            }}
        """)
        reset_button.clicked.connect(self.reset_all)
        self.collapsible.add_widget(reset_button)

        layout.addWidget(self.collapsible)

    def reset_all(self):
        """Reset all controls to their default values"""
        for control in self.controls.values():
            control.reset_to_default()

    def set_expanded(self, expanded: bool):
        """Set expanded state of the collapsible container"""
        self.collapsible.set_expanded(expanded)

    def get_control(self, property_key: str) -> BiologicalPropertyControl:
        """Get a specific control by property key"""
        return self.controls.get(property_key)

    def get_all_settings(self) -> dict:
        """Get all current settings as a dictionary"""
        settings = {}
        for key, control in self.controls.items():
            settings[key] = {
                "property_index": control.get_current_index(),
                "property_name": control.get_current_property(),
                "filter_range": control.get_filter_range(),
            }
            if control.control_type == "color":
                settings[key]["gradient_colors"] = control.get_gradient_colors()
                settings[key]["fade"] = control.get_fade()
        return settings

    def apply_settings(self, settings: dict):
        """Apply settings from a dictionary"""
        for key, values in settings.items():
            control = self.controls.get(key)
            if control:
                control.set_current_index(values.get("property_index", 0))

                filter_range = values.get("filter_range")
                if filter_range:
                    control.set_filter_range(*filter_range)

                if control.control_type == "color":
                    colors = values.get("gradient_colors")
                    if colors:
                        control.set_gradient_colors(*colors)

                    fade = values.get("fade")
                    if fade is not None:
                        control.set_fade(fade)


def create_property_control_for_tab(tab_type: str, accent_color: str = "#66BB6A",
                                     parent=None) -> BiologicalPropertyControlGroup:
    """
    Factory function to create a complete property control group for a given tab type.

    Args:
        tab_type: One of "amino_acids", "proteins", "nucleic_acids",
                  "cell_components", "cells", "biomaterials"
        accent_color: Accent color for styling (default green for biological)
        parent: Parent widget

    Returns:
        BiologicalPropertyControlGroup configured for the specified tab type
    """
    return BiologicalPropertyControlGroup(tab_type, accent_color, parent)
