#!/usr/bin/env python3
"""
Control Panel for the Quantum Orbit visualization
Provides UI controls for layout mode, property mappings, and filters
"""
import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                                QScrollArea, QRadioButton, QComboBox, QCheckBox,
                                QPushButton, QSlider, QToolButton, QFrame)
from PySide6.QtCore import Qt, QParallelAnimationGroup, QPropertyAnimation, Signal
from PySide6.QtGui import QFont

from periodica.data.data_manager import get_data_manager, DataCategory
from periodica_app.ui.ai_generation_widget import AIGenerationWidget

from periodica_app.ui.components import (ColorGradientBar, BorderThicknessLegend, GlowIntensityLegend, InnerRingLegend,
                           DistanceMappingVisualizer, SpectrumMappingVisualizer, ColorMappingVisualizer,
                           UnifiedPropertyMappingWidget, UnifiedPropertyControl)
from periodica_app.ui.transform_controls import TransformControlsWidget, Transform3D
from periodica.data.element_data import get_property_metadata
from periodica.core.pt_enums import PTPropertyName, PTEncodingKey, PTWavelengthMode, PTPropertyType, PTEncodingType, PTLayoutMode, ENCODING_KEY_TO_TYPE


class PropertyControl(QWidget):
    """Expandable control for a single visual property with range controls and filtering"""
    def __init__(self, title, property_key, parent_panel, available_properties, control_type="color", default_index=0):
        super().__init__()
        self.property_key = property_key
        self.parent_panel = parent_panel
        # Convert string to enum if needed
        if isinstance(control_type, str):
            self.control_type = PTPropertyType.from_string(control_type)
        else:
            self.control_type = control_type
        self.is_expanded = False
        self.default_index = default_index  # Index of default property
        self.user_selected_index = default_index  # Track user's last selection

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

        # "Use Default" checkbox
        self.use_default_checkbox = QCheckBox("Default")
        self.use_default_checkbox.setStyleSheet("""
            QCheckBox {
                color: rgba(255,255,255,200);
                font-size: 9px;
                spacing: 3px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #667eea;
                border-radius: 3px;
                background: rgba(40, 40, 60, 150);
            }
            QCheckBox::indicator:checked {
                background: #667eea;
            }
        """)
        self.use_default_checkbox.toggled.connect(self.on_use_default_toggled)
        header_layout.addWidget(self.use_default_checkbox)

        main_layout.addWidget(header)

        # Expandable details area
        self.details_widget = QWidget()
        self.details_widget.setVisible(False)
        details_layout = QVBoxLayout(self.details_widget)
        details_layout.setContentsMargins(25, 5, 5, 5)
        details_layout.setSpacing(8)

        # Unified property mapping widget (replaces old sliders and visualizers)
        mapping_label = QLabel("Property Mapping & Filtering:")
        mapping_label.setStyleSheet("color: rgba(255,255,255,200); font-size: 9px; font-weight: bold;")
        details_layout.addWidget(mapping_label)

        self.unified_mapping = UnifiedPropertyMappingWidget(property_name="ionization", property_type=control_type)
        self.unified_mapping.color_range_changed.connect(self.on_unified_color_range_changed)
        self.unified_mapping.filter_range_changed.connect(self.on_unified_filter_range_changed)
        self.unified_mapping.gradient_colors_changed.connect(self.on_unified_gradient_colors_changed)
        details_layout.addWidget(self.unified_mapping)

        # Fade slider (for color properties only)
        if self.control_type == PTPropertyType.COLOR:
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

            # Wavelength mode checkbox (only for wavelength properties)
            self.wavelength_mode_container = QWidget()
            wavelength_mode_layout = QHBoxLayout(self.wavelength_mode_container)
            wavelength_mode_layout.setContentsMargins(0, 5, 0, 0)
            wavelength_mode_layout.setSpacing(5)

            self.wavelength_mode_checkbox = QCheckBox("Use Rainbow Spectrum")
            self.wavelength_mode_checkbox.setChecked(True)  # Default to rainbow
            self.wavelength_mode_checkbox.setStyleSheet("""
                QCheckBox {
                    color: rgba(255,255,255,200);
                    font-size: 9px;
                    spacing: 3px;
                }
                QCheckBox::indicator {
                    width: 14px;
                    height: 14px;
                    border: 1px solid #667eea;
                    border-radius: 3px;
                    background: rgba(40, 40, 60, 150);
                }
                QCheckBox::indicator:checked {
                    background: #667eea;
                }
            """)
            self.wavelength_mode_checkbox.toggled.connect(self.on_wavelength_mode_toggled)
            wavelength_mode_layout.addWidget(self.wavelength_mode_checkbox)
            wavelength_mode_layout.addStretch()

            details_layout.addWidget(self.wavelength_mode_container)
            self.wavelength_mode_container.setVisible(False)  # Hidden by default

        main_layout.addWidget(self.details_widget)

        # Initialize with defaults
        self.data_min = 0
        self.data_max = 100
        self.data_unit = ""
        self.current_property_name = "none"
        self.viz_min = 0
        self.viz_max = 100

    def on_unified_color_range_changed(self, min_map, max_map):
        """Handle color mapping range change from unified widget"""
        # Store viz mapping values
        self.viz_min_value = min_map
        self.viz_max_value = max_map

        # Update the table's color/size mapping for this property
        if hasattr(self, 'property_key') and hasattr(self.parent_panel, 'table'):
            # Map property key to table attribute
            # Yellow tags control INPUT range (property values to map to full output range)
            attr_map = {
                "fill_color": ("fill_property_min_map", "fill_property_max_map"),
                "border_color": ("border_property_min_map", "border_property_max_map"),
                "border_size": ("border_size_property_min", "border_size_property_max"),
                "ring_color": ("ring_property_min_map", "ring_property_max_map"),
                "ring_size": ("ring_size_property_min", "ring_size_property_max"),
                "glow_color": ("glow_property_min_map", "glow_property_max_map"),
                "glow_intensity": ("glow_intensity_property_min", "glow_intensity_property_max"),
                "distance": ("distance_min", "distance_max"),
                "symbol_text_color": ("symbol_text_color_property_min_map", "symbol_text_color_property_max_map"),
                "atomic_number_text_color": ("atomic_number_text_color_property_min_map", "atomic_number_text_color_property_max_map"),
            }

            if self.property_key in attr_map:
                min_attr, max_attr = attr_map[self.property_key]
                setattr(self.parent_panel.table, min_attr, min_map)
                setattr(self.parent_panel.table, max_attr, max_map)

                # Special handling for color properties - also set *_color_range_min/max attributes used by rendering
                if self.property_key == "fill_color":
                    self.parent_panel.table.fill_color_range_min = min_map
                    self.parent_panel.table.fill_color_range_max = max_map
                elif self.property_key == "border_color":
                    self.parent_panel.table.border_color_range_min = min_map
                    self.parent_panel.table.border_color_range_max = max_map
                elif self.property_key == "ring_color":
                    self.parent_panel.table.ring_color_range_min = min_map
                    self.parent_panel.table.ring_color_range_max = max_map
                elif self.property_key == "glow_color":
                    self.parent_panel.table.glow_color_range_min = min_map
                    self.parent_panel.table.glow_color_range_max = max_map
                elif self.property_key == "symbol_text_color":
                    self.parent_panel.table.symbol_text_color_range_min = min_map
                    self.parent_panel.table.symbol_text_color_range_max = max_map
                elif self.property_key == "atomic_number_text_color":
                    self.parent_panel.table.atomic_number_text_color_range_min = min_map
                    self.parent_panel.table.atomic_number_text_color_range_max = max_map

                self.parent_panel.table.update()

    def on_unified_gradient_colors_changed(self, start_color, end_color):
        """Handle gradient color change from unified widget color pickers"""
        if hasattr(self, 'property_key') and hasattr(self.parent_panel, 'table'):
            # Map property key to custom gradient attribute names
            gradient_attr_map = {
                "fill_color": ("custom_fill_gradient_start", "custom_fill_gradient_end"),
                "border_color": ("custom_border_gradient_start", "custom_border_gradient_end"),
                "ring_color": ("custom_ring_gradient_start", "custom_ring_gradient_end"),
                "glow_color": ("custom_glow_gradient_start", "custom_glow_gradient_end"),
                "symbol_text_color": ("custom_symbol_text_gradient_start", "custom_symbol_text_gradient_end"),
                "atomic_number_text_color": ("custom_atomic_number_text_gradient_start", "custom_atomic_number_text_gradient_end"),
            }

            if self.property_key in gradient_attr_map:
                start_attr, end_attr = gradient_attr_map[self.property_key]
                setattr(self.parent_panel.table, start_attr, start_color)
                setattr(self.parent_panel.table, end_attr, end_color)
                self.parent_panel.table.update()

    def on_unified_filter_range_changed(self, min_filter, max_filter):
        """Handle filter range change from unified widget"""
        # Update the table's filter settings
        if self.current_property_name != PTPropertyName.NONE.value and hasattr(self.parent_panel, 'table'):
            if self.current_property_name in self.parent_panel.table.filters:
                self.parent_panel.table.filters[self.current_property_name]['min'] = min_filter
                self.parent_panel.table.filters[self.current_property_name]['max'] = max_filter
                # Filter is always active with unified widget (controlled by unified widget's filter checkbox)
                self.parent_panel.table.filters[self.current_property_name]['active'] = self.unified_mapping.filter_enabled
                self.parent_panel.table.update()

    def on_wavelength_mode_toggled(self, checked):
        """Handle wavelength mode checkbox toggle"""
        mode = PTWavelengthMode.SPECTRUM if checked else PTWavelengthMode.GRADIENT
        self.unified_mapping.wavelength_mode = mode
        self.unified_mapping.wavelength_mode_changed.emit(mode)
        self.unified_mapping.update()

        # Update table's wavelength mode for this property
        if hasattr(self, 'property_key') and hasattr(self.parent_panel, 'table'):
            # Use the ENCODING_KEY_TO_TYPE mapping and PTEncodingType helper method
            if self.property_key in ENCODING_KEY_TO_TYPE:
                encoding_type = ENCODING_KEY_TO_TYPE[self.property_key]
                mode_attr = encoding_type.get_wavelength_mode_attr()
                setattr(self.parent_panel.table, mode_attr, mode)
                self.parent_panel.table.update()

    def _get_actual_property_range(self, property_name):
        """Scan table elements to get actual min/max for a property"""
        if not hasattr(self.parent_panel, 'table') or not hasattr(self.parent_panel.table, 'base_elements'):
            return None, None

        elements = self.parent_panel.table.base_elements
        if not elements:
            return None, None

        # Map property name to element field
        property_field_map = {
            "atomic_number": "z",
            "atomic_mass": "atomic_mass",
            "ionization": "ie",
            "electronegativity": "electronegativity",
            "melting": "melting_point",
            "boiling": "boiling_point",
            "radius": "atomic_radius",
            "density": "density",
            "electron_affinity": "electron_affinity",
            "valence": "valence_electrons",
            "group": "group",
            "period": "period",
            "specific_heat": "specific_heat",
            "thermal_conductivity": "thermal_conductivity",
            "electrical_conductivity": "electrical_conductivity",
            "wavelength": "wavelength_nm",
            "emission_wavelength": "emission_wavelength",
            "visible_emission_wavelength": "visible_emission_wavelength",
            "ionization_wavelength": "ionization_wavelength"
        }

        field = property_field_map.get(property_name)
        if not field:
            return None, None

        # Collect all values
        values = []
        for elem in elements:
            if field in elem:
                val = elem[field]
                # Skip zero values for electronegativity (noble gases)
                if property_name == PTPropertyName.ELECTRONEGATIVITY.value and val == 0:
                    continue
                if val is not None:
                    values.append(val)

        if not values:
            return None, None

        return min(values), max(values)

    def on_property_selection_changed(self, idx):
        """Handle property selection change - update ranges and call parent"""
        # Get the property name from selection
        property_display_name = self.available_properties[idx]

        # Use enum to map display name to internal name
        property_enum = PTPropertyName.from_display_name(property_display_name)
        property_name = property_enum.value
        self.current_property_name = property_name  # Store for filter updates

        # Get metadata for this property
        if property_name != "none":
            metadata = get_property_metadata(property_name)
            self.current_metadata = metadata

            # Update slider ranges based on actual data from table elements
            if metadata["min_value"] is not None and metadata["max_value"] is not None:
                # Get actual min/max from table's element data
                actual_min, actual_max = self._get_actual_property_range(property_name)

                # Use actual values if available, otherwise fall back to metadata
                if actual_min is not None and actual_max is not None:
                    self.data_min = actual_min
                    self.data_max = actual_max
                else:
                    self.data_min = metadata["min_value"]
                    self.data_max = metadata["max_value"]

                # For wavelength properties, ensure data range is 0 to max(1000, actual_max)
                if PTPropertyName.is_wavelength_property(property_name):
                    self.data_min = 0
                    self.data_max = max(1000, self.data_max)

                self.data_unit = metadata["unit"]

                # Setup visualization ranges based on property and control type
                if self.control_type == PTPropertyType.COLOR:
                    # For color properties, viz range is the same as data range
                    self.viz_min = self.data_min
                    self.viz_max = self.data_max
                    self.viz_unit = self.data_unit
                elif self.control_type == PTPropertyType.SIZE:
                    # Size in pixels - this maps data values to pixel sizes
                    self.viz_min = 1
                    self.viz_max = 10
                    self.viz_unit = "px"
                else:  # PTPropertyType.INTENSITY
                    # Alpha 0-100%
                    self.viz_min = 0
                    self.viz_max = 100
                    self.viz_unit = "%"
        else:
            self.data_min = 0
            self.data_max = 100
            self.data_unit = ""
            self.viz_min = 0
            self.viz_max = 100
            self.viz_unit = "%"
            self.current_metadata = None

        # Call parent's handler
        self.parent_panel.on_property_changed(self.property_key, idx)
        self.update_preview()
        self._update_visual_mapping_widget()

    def _update_visual_mapping_widget(self):
        """Update the unified property mapping widget"""
        if not hasattr(self, 'current_property_name') or self.current_property_name == PTPropertyName.NONE.value:
            return

        # Update unified widget property and type
        self.unified_mapping.set_property(self.current_property_name, self.control_type)

        # Set value range from data
        if hasattr(self, 'data_min') and hasattr(self, 'data_max'):
            self.unified_mapping.set_value_range(self.data_min, self.data_max)

        # Set color mapping range (yellow tags)
        if hasattr(self, 'viz_min') and hasattr(self, 'viz_max'):
            # Special handling for wavelength properties - default to visible spectrum (380-780nm)
            if PTPropertyName.is_wavelength_property(self.current_property_name):
                # Default yellow tags to visible spectrum range
                self.unified_mapping.set_color_map_range(380.0, 780.0)
                # Also update table's fill_color_range for immediate effect
                if hasattr(self.parent_panel, 'table'):
                    self.parent_panel.table.fill_color_range_min = 380.0
                    self.parent_panel.table.fill_color_range_max = 780.0
            else:
                # For ALL non-wavelength properties, yellow tags control INPUT range (property values)
                # This applies to colors, sizes, and intensities
                self.unified_mapping.set_color_map_range(self.data_min, self.data_max)

        # Set default filter range to full data range
        if hasattr(self, 'data_min') and hasattr(self, 'data_max'):
            self.unified_mapping.set_filter_range(self.data_min, self.data_max)

        # Show/hide wavelength mode checkbox based on property type
        if self.control_type == PTPropertyType.COLOR and hasattr(self, 'wavelength_mode_container'):
            is_wavelength = PTPropertyName.is_wavelength_property(self.current_property_name)
            self.wavelength_mode_container.setVisible(is_wavelength)

    def _refresh_visual_mapping(self):
        """Legacy method - now handled by unified widget"""
        # Unified widget handles its own refresh
        pass

    def on_value_range_display_changed(self):
        """Update display when value range sliders move (not applied yet)"""
        # Map slider values (0-1000) to actual data range
        if hasattr(self, 'data_min') and hasattr(self, 'data_max'):
            min_normalized = self.min_value_slider.value() / 1000.0
            max_normalized = self.max_value_slider.value() / 1000.0

            min_val = self.data_min + min_normalized * (self.data_max - self.data_min)
            max_val = self.data_min + max_normalized * (self.data_max - self.data_min)

            # Format based on magnitude
            if self.data_unit == "K" or abs(max_val) > 100:
                self.min_value_display.setText(f"{min_val:.0f} {self.data_unit}")
                self.max_value_display.setText(f"{max_val:.0f} {self.data_unit}")
            elif self.data_unit == "":
                self.min_value_display.setText(f"{min_val:.2f}")
                self.max_value_display.setText(f"{max_val:.2f}")
            else:
                self.min_value_display.setText(f"{min_val:.2f} {self.data_unit}")
                self.max_value_display.setText(f"{max_val:.2f} {self.data_unit}")
        else:
            min_val = self.min_value_slider.value()
            max_val = self.max_value_slider.value()
            self.min_value_display.setText(f"{min_val}")
            self.max_value_display.setText(f"{max_val}")

        self._refresh_visual_mapping()
        self.update_preview()

    def on_value_range_applied(self):
        """Apply filter when value range sliders are released"""
        self.update_table_filter()

    def on_viz_mapping_display_changed(self):
        """Update display when visualization mapping sliders move (not applied yet)"""
        self._refresh_visual_mapping()
        self.on_viz_range_changed()

    def on_viz_mapping_applied(self):
        """Legacy method - now handled by on_unified_color_range_changed"""
        pass

    def on_viz_range_changed(self):
        """Legacy method - now handled by unified widget"""
        pass

    def on_filter_toggled(self, checked):
        """Handle filter checkbox toggle"""
        self.update_table_filter()

    def on_fade_changed(self, value):
        """Handle fade slider change"""
        fade = value / 100.0
        self.fade_display.setText(f"{value}%")
        # Update the table's fade value for this property
        if hasattr(self.parent_panel, 'table'):
            fade_map = {
                "fill_color": "fill_fade",
                "border_color": "border_color_fade",
                "ring_color": "ring_color_fade",
                "glow_color": "glow_color_fade",
                "symbol_text_color": "symbol_text_color_fade",
                "atomic_number_text_color": "atomic_number_text_color_fade"
            }
            if self.property_key in fade_map:
                setattr(self.parent_panel.table, fade_map[self.property_key], fade)
                self.parent_panel.table.update()

    def update_table_filter(self):
        """Legacy method - now handled by on_unified_filter_range_changed"""
        pass

    def update_preview(self):
        """Update the preview box to show current mapping - now handled by visual widgets"""
        # Visual widgets now handle the preview, this method kept for compatibility
        pass

    def toggle_expanded(self):
        """Toggle expanded/collapsed state"""
        self.is_expanded = not self.is_expanded
        self.expand_btn.setArrowType(Qt.ArrowType.DownArrow if self.is_expanded else Qt.ArrowType.RightArrow)
        self.details_widget.setVisible(self.is_expanded)
        if self.is_expanded:
            self.update_preview()

    def on_use_default_toggled(self, checked):
        """Toggle using default color/value for this property"""
        # Disable property combo when using default
        self.property_combo.setEnabled(not checked)

        if checked:
            # Save current user selection
            self.user_selected_index = self.property_combo.currentIndex()
            # Set to default
            self.property_combo.blockSignals(True)
            self.property_combo.setCurrentIndex(self.default_index)
            self.property_combo.blockSignals(False)
            # Manually trigger property selection changed to update sliders
            self.on_property_selection_changed(self.default_index)
        else:
            # Restore user's last selection
            self.property_combo.blockSignals(True)
            self.property_combo.setCurrentIndex(self.user_selected_index)
            self.property_combo.blockSignals(False)
            # Manually trigger property selection changed to update sliders
            self.on_property_selection_changed(self.user_selected_index)

        # Trigger update in parent panel
        self.parent_panel.on_property_changed(self.property_key, self.property_combo.currentIndex())

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
        self.toggle_animation.finished.disconnect(self._on_expand_finished)

    def set_content_layout(self, layout):
        """Set the content layout for this collapsible box"""
        # Clear existing layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add widgets from the provided layout
        if isinstance(layout, QVBoxLayout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    self.content_layout.addWidget(item.widget())


class ControlPanel(QWidget):
    """Control panel widget for adjusting visualization settings"""

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

    # 3D Transform signal (for orbital visualization, subatomic particles, etc.)
    transform_changed = Signal(Transform3D)

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

        title = QLabel("Visualization Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        layout.addWidget(title)

        # Layout Mode Selection (always expanded)
        layout.addWidget(self._create_layout_mode_group())

        # Visual Property Encodings (includes Fill, Border, Inner Ring, Glow with expandable submenus)
        layout.addWidget(self._create_visual_properties_group())

        # Display Overlays
        layout.addWidget(self._create_display_overlays_group())

        # Orbital/Atomic Visualization
        layout.addWidget(self._create_orbital_group())

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
        """Create the layout mode selection group - always expanded"""
        layout_group = QGroupBox("Layout Mode")
        layout_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid #667eea;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout_box = QVBoxLayout()

        self.circular_radio = QRadioButton("Circular Wedge Spiral")
        self.spiral_radio = QRadioButton("Isotope Spiral (7 Circles)")
        self.serpentine_radio = QRadioButton("Linear Property Graph")
        self.table_radio = QRadioButton("Traditional Table")
        self.circular_radio.setChecked(True)

        radio_style = """
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
        self.circular_radio.setStyleSheet(radio_style)
        self.spiral_radio.setStyleSheet(radio_style)
        self.serpentine_radio.setStyleSheet(radio_style)
        self.table_radio.setStyleSheet(radio_style)

        self.circular_radio.toggled.connect(lambda: self._on_layout_mode_changed("circular") if self.circular_radio.isChecked() else None)
        self.spiral_radio.toggled.connect(lambda: self._on_layout_mode_changed("spiral") if self.spiral_radio.isChecked() else None)
        self.serpentine_radio.toggled.connect(lambda: self._on_layout_mode_changed("serpentine") if self.serpentine_radio.isChecked() else None)
        self.table_radio.toggled.connect(lambda: self._on_layout_mode_changed("table") if self.table_radio.isChecked() else None)

        layout_box.addWidget(self.circular_radio)
        layout_box.addWidget(self.spiral_radio)
        layout_box.addWidget(self.serpentine_radio)
        layout_box.addWidget(self.table_radio)

        # Zoom controls info for all modes
        zoom_info = QLabel("Camera Controls (All Modes):\n• Scroll wheel: Zoom\n• Middle-click or Ctrl+drag: Pan")
        zoom_info.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; margin-top: 8px;")
        zoom_info.setWordWrap(True)
        layout_box.addWidget(zoom_info)

        # Reset zoom button
        reset_btn = QPushButton("Reset View")
        reset_btn.clicked.connect(self.reset_view)
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
        layout_box.addWidget(reset_btn)

        layout_group.setLayout(layout_box)
        return layout_group

    def _create_visual_properties_group(self):
        """Create visual property encodings with expandable controls"""
        collapsible = CollapsibleBox("Visual Property Encodings", "#764ba2")
        properties_layout = QVBoxLayout()

        # Available property options - use enum to generate display names
        color_properties = [PTPropertyName.get_display_name(prop) for prop in PTPropertyName.get_color_properties()]
        size_properties = [PTPropertyName.get_display_name(prop) for prop in PTPropertyName.get_size_properties()]
        intensity_properties = [PTPropertyName.get_display_name(prop) for prop in PTPropertyName.get_intensity_properties()]

        # 1. Fill Colour -> Emission Wavelength (index 16 in updated color_properties)
        self.fill_color_control = PropertyControl("Fill Colour", "fill_color", self, color_properties, control_type="color", default_index=16)
        self.fill_color_control.property_combo.setCurrentIndex(16)  # Emission Wavelength
        properties_layout.addWidget(self.fill_color_control)

        # 2. Border Colour -> Electron Affinity (index 8 in updated color_properties)
        self.border_color_control = PropertyControl("Border Colour", "border_color", self, color_properties, control_type="color", default_index=8)
        self.border_color_control.property_combo.setCurrentIndex(8)  # Electron Affinity
        properties_layout.addWidget(self.border_color_control)

        # 3. Border Size -> Valence Electrons (index 9 in updated size_properties)
        self.border_size_control = PropertyControl("Border Size", "border_size", self, size_properties, control_type="size", default_index=9)
        self.border_size_control.property_combo.setCurrentIndex(9)  # Valence Electrons
        properties_layout.addWidget(self.border_size_control)

        # 4. Inner Ring Colour -> Orbital Block (index 12 in updated color_properties)
        self.ring_color_control = PropertyControl("Inner Ring Colour", "ring_color", self, color_properties, control_type="color", default_index=12)
        self.ring_color_control.property_combo.setCurrentIndex(12)  # Orbital Block
        properties_layout.addWidget(self.ring_color_control)

        # 5. Inner Ring Size -> Electronegativity (index 4 in updated size_properties)
        self.ring_size_control = PropertyControl("Inner Ring Size", "ring_size", self, size_properties, control_type="size", default_index=4)
        self.ring_size_control.property_combo.setCurrentIndex(4)  # Electronegativity
        properties_layout.addWidget(self.ring_size_control)

        # 6. Glow Colour -> Atomic Radius (index 6 in updated color_properties)
        self.glow_color_control = PropertyControl("Glow Colour", "glow_color", self, color_properties, control_type="color", default_index=6)
        self.glow_color_control.property_combo.setCurrentIndex(6)  # Atomic Radius
        properties_layout.addWidget(self.glow_color_control)

        # 7. Glow Radius/Intensity -> Ionization Energy (index 3 in updated intensity_properties)
        self.glow_intensity_control = PropertyControl("Glow Radius/Intensity", "glow_intensity", self, intensity_properties, control_type="intensity", default_index=3)
        self.glow_intensity_control.property_combo.setCurrentIndex(3)  # Ionization Energy
        properties_layout.addWidget(self.glow_intensity_control)

        # 8. Symbol Text Colour -> Melting Point (index 4 in updated color_properties)
        self.symbol_text_color_control = PropertyControl("Symbol Text Colour", "symbol_text_color", self, color_properties, control_type="color", default_index=4)
        self.symbol_text_color_control.property_combo.setCurrentIndex(4)  # Melting Point
        properties_layout.addWidget(self.symbol_text_color_control)

        # 9. Atomic Number Text Colour -> Boiling Point (index 5 in updated color_properties)
        self.atomic_number_text_color_control = PropertyControl("Atomic Number Text Colour", "atomic_number_text_color", self, color_properties, control_type="color", default_index=5)
        self.atomic_number_text_color_control.property_combo.setCurrentIndex(5)  # Boiling Point
        properties_layout.addWidget(self.atomic_number_text_color_control)

        # Isotope layers toggle
        self.isotope_check = QCheckBox("Show Isotope Layers")
        self.isotope_check.setChecked(True)
        self.isotope_check.toggled.connect(self.on_isotope_toggled)
        self.isotope_check.setStyleSheet("""
            QCheckBox {
                color: white;
                spacing: 8px;
                margin-top: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #764ba2;
                border-radius: 4px;
                background: rgba(40, 40, 60, 200);
            }
            QCheckBox::indicator:checked {
                background: #764ba2;
            }
        """)
        properties_layout.addWidget(self.isotope_check)

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
        reset_button.clicked.connect(self.reset_property_mappings)
        properties_layout.addWidget(reset_button)

        # Transfer to collapsible
        while properties_layout.count():
            item = properties_layout.takeAt(0)
            if item.widget():
                collapsible.content_layout.addWidget(item.widget())

        # Open by default
        collapsible.toggle_button.setChecked(True)
        collapsible.on_toggle()

        # Apply initial settings
        self._apply_initial_settings()

        return collapsible

    def _apply_initial_settings(self):
        """Apply all default property settings when the app starts"""
        # List of all property controls
        property_controls = [
            self.fill_color_control,
            self.border_color_control,
            self.border_size_control,
            self.ring_color_control,
            self.ring_size_control,
            self.glow_color_control,
            self.glow_intensity_control,
            self.symbol_text_color_control,
            self.atomic_number_text_color_control
        ]

        # First pass: Initialize all property controls (sets up slider ranges, metadata, etc.)
        for control in property_controls:
            current_index = control.property_combo.currentIndex()
            # This sets up the slider ranges and metadata based on selected property
            # It also calls on_value_range_applied() and on_viz_mapping_applied() internally
            control.on_property_selection_changed(current_index)

        # Second pass: Apply property assignments to table
        for control in property_controls:
            current_index = control.property_combo.currentIndex()
            # This sets the table's property assignments (fill_property, border_property, etc.)
            # Each call triggers table.update() internally
            self.on_property_changed(control.property_key, current_index)

        # The table has been updated multiple times above, but colors might not be right
        # because each property overwrote color_range_min/max
        # Force fill_color control to re-apply its viz mapping as the final state
        # since fill is the most prominent visual property
        self.fill_color_control.on_viz_mapping_applied()

        # Force one final table update to ensure everything is rendered with correct colors
        self.table.update()

    def on_property_changed(self, property_key, index):
        """Handle property selection change"""
        # Map UI indices to internal property names using enums
        color_modes = [prop.value for prop in PTPropertyName.get_color_properties()]
        size_modes = [prop.value for prop in PTPropertyName.get_size_properties()]
        intensity_modes = [prop.value for prop in PTPropertyName.get_intensity_properties()]

        # Check the use_default checkbox state for this property
        use_default = False
        encoding_key = PTEncodingKey.from_string(property_key)

        if encoding_key == PTEncodingKey.FILL_COLOR:
            use_default = self.fill_color_control.use_default_checkbox.isChecked()
            self.table.use_default_fill = use_default
            self.table.fill_property = color_modes[index]
            self.table.update()
        elif encoding_key == PTEncodingKey.BORDER_COLOR:
            use_default = self.border_color_control.use_default_checkbox.isChecked()
            self.table.use_default_border_color = use_default
            self.table.border_color_property = color_modes[index]
            self.table.update()
        elif encoding_key == PTEncodingKey.BORDER_SIZE:
            use_default = self.border_size_control.use_default_checkbox.isChecked()
            self.table.use_default_border_size = use_default
            self.table.border_size_property = size_modes[index]
            self.table.border_property = size_modes[index]  # Legacy compatibility
            self.table.update()
        elif encoding_key == PTEncodingKey.RING_COLOR:
            use_default = self.ring_color_control.use_default_checkbox.isChecked()
            self.table.use_default_ring_color = use_default
            self.table.ring_property = color_modes[index]
            self.table.update()
        elif encoding_key == PTEncodingKey.RING_SIZE:
            use_default = self.ring_size_control.use_default_checkbox.isChecked()
            self.table.use_default_ring_size = use_default
            self.table.ring_size_property = size_modes[index]
            self.table.update()
        elif encoding_key == PTEncodingKey.GLOW_COLOR:
            use_default = self.glow_color_control.use_default_checkbox.isChecked()
            self.table.use_default_glow_color = use_default
            # Set both glow_property (used by rendering) and glow_color_property (legacy)
            self.table.glow_property = color_modes[index]
            if hasattr(self.table, 'glow_color_property'):
                self.table.glow_color_property = color_modes[index]
            self.table.update()
        elif encoding_key == PTEncodingKey.GLOW_INTENSITY:
            use_default = self.glow_intensity_control.use_default_checkbox.isChecked()
            self.table.use_default_glow_intensity = use_default
            # Set both glow radius and intensity properties (they use the same property selection)
            self.table.glow_radius_property = intensity_modes[index]
            self.table.glow_intensity_property = intensity_modes[index]
            self.table.update()
        elif encoding_key == PTEncodingKey.SYMBOL_TEXT_COLOR:
            use_default = self.symbol_text_color_control.use_default_checkbox.isChecked()
            self.table.use_default_symbol_text_color = use_default
            if hasattr(self.table, 'symbol_text_color_property'):
                self.table.symbol_text_color_property = color_modes[index]
            self.table.update()
        elif encoding_key == PTEncodingKey.ATOMIC_NUMBER_TEXT_COLOR:
            use_default = self.atomic_number_text_color_control.use_default_checkbox.isChecked()
            self.table.use_default_atomic_number_text_color = use_default
            if hasattr(self.table, 'atomic_number_text_color_property'):
                self.table.atomic_number_text_color_property = color_modes[index]
            self.table.update()

    def _on_layout_mode_changed(self, mode):
        """Handle layout mode change"""
        self.table.set_layout_mode(mode)
        # Show/hide isotope checkbox based on layout mode
        # Convert string to enum if needed
        if isinstance(mode, str):
            mode_enum = PTLayoutMode.from_string(mode)
        else:
            mode_enum = mode

        if hasattr(self, 'isotope_check'):
            if mode_enum == PTLayoutMode.SPIRAL:
                self.isotope_check.show()
            else:
                self.isotope_check.hide()
        # Show/hide neutron offset combo based on layout mode
        if hasattr(self, 'neutron_offset_container'):
            if mode_enum == PTLayoutMode.SPIRAL:
                self.neutron_offset_container.hide()
            else:
                self.neutron_offset_container.show()

    def _show_mode_ui(self, mode):
        """No longer needed - mode-specific UI removed"""
        pass

    def on_isotope_toggled(self, checked):
        """Handle isotope visibility toggle"""
        self.table.show_isotopes = checked
        self.table.update()

    def _create_display_overlays_group(self):
        """Create display overlay controls"""
        collapsible = CollapsibleBox("Display Overlays", "#4fc3f7")
        layout = QVBoxLayout()

        # Element table visibility toggle
        self.element_table_check = QCheckBox("Show Element Table")
        self.element_table_check.setStyleSheet("color: white;")
        self.element_table_check.setChecked(True)  # Default on
        self.element_table_check.stateChanged.connect(self.on_element_table_changed)
        layout.addWidget(self.element_table_check)

        # Subatomic particles toggle
        self.subatomic_check = QCheckBox("Show Subatomic Particles")
        self.subatomic_check.setStyleSheet("color: white;")
        self.subatomic_check.stateChanged.connect(self.on_subatomic_changed)
        layout.addWidget(self.subatomic_check)

        # Orbital cloud visibility toggle
        self.orbital_cloud_check = QCheckBox("Show Orbital Probability Cloud")
        self.orbital_cloud_check.setStyleSheet("color: white;")
        self.orbital_cloud_check.setChecked(True)  # Default on
        self.orbital_cloud_check.stateChanged.connect(self.on_orbital_cloud_changed)
        layout.addWidget(self.orbital_cloud_check)

        # Isotope visualization toggle
        self.isotope_check = QCheckBox("Show Isotope Layer")
        self.isotope_check.setStyleSheet("color: white;")
        self.isotope_check.setChecked(False)  # Default off
        self.isotope_check.stateChanged.connect(self.on_isotope_toggled)
        layout.addWidget(self.isotope_check)

        # Neutron offset selector (for non-spiral layouts)
        self.neutron_offset_container = QWidget()
        neutron_layout = QHBoxLayout(self.neutron_offset_container)
        neutron_layout.setContentsMargins(0, 5, 0, 0)
        neutron_layout.setSpacing(8)

        neutron_label = QLabel("Neutron Offset:")
        neutron_label.setStyleSheet("color: white; font-size: 10px; min-width: 100px;")
        neutron_layout.addWidget(neutron_label)

        self.neutron_offset_combo = QComboBox()
        self.neutron_offset_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(60, 60, 80, 200);
                color: white;
                border: 1px solid #4fc3f7;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 10px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: rgba(40, 40, 60, 250);
                color: white;
                selection-background-color: #4fc3f7;
            }
        """)

        # Populate with neutron offset options based on available isotopes
        self._populate_neutron_offset_combo()

        self.neutron_offset_combo.setCurrentIndex(0)  # Default to N = Z
        self.neutron_offset_combo.currentIndexChanged.connect(self.on_neutron_offset_changed)
        neutron_layout.addWidget(self.neutron_offset_combo)

        layout.addWidget(self.neutron_offset_container)

        # Spectrum lines overlay toggle
        self.spectrum_lines_check = QCheckBox("Show Spectrum Lines")
        self.spectrum_lines_check.setStyleSheet("color: white;")
        self.spectrum_lines_check.setChecked(False)  # Default off
        self.spectrum_lines_check.stateChanged.connect(self.on_spectrum_lines_changed)
        layout.addWidget(self.spectrum_lines_check)

        # Transfer widgets to collapsible box
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                collapsible.content_layout.addWidget(item.widget())

        return collapsible

    def _populate_neutron_offset_combo(self):
        """Populate neutron offset combo with only offsets that exist in isotope data"""
        from periodica.data.element_data import ISOTOPES, PERIODS, get_atomic_number

        # Collect all unique neutron offsets that exist in the data
        available_offsets = set()

        # Iterate through all elements in PERIODS
        for period in PERIODS:
            for symbol in period:
                z = get_atomic_number(symbol)
                isotopes = ISOTOPES.get(symbol, [])
                for mass, abundance in isotopes:
                    neutron_count = mass - z
                    offset = neutron_count - z
                    available_offsets.add(offset)

        # Sort offsets
        sorted_offsets = sorted(available_offsets)

        # Populate combo box
        self.neutron_offset_combo.clear()

        # Always add N = Z first
        self.neutron_offset_combo.addItem("N = Z (Equal)", 0)

        # Add available offsets in sorted order
        for offset in sorted_offsets:
            if offset == 0:
                continue  # Already added above
            elif offset < 0:
                self.neutron_offset_combo.addItem(f"N = Z {offset:+d}", offset)
            else:
                self.neutron_offset_combo.addItem(f"N = Z +{offset}", offset)

    def on_neutron_offset_changed(self, index):
        """Handle neutron offset selection change"""
        neutron_offset = self.neutron_offset_combo.itemData(index)
        self.table.selected_neutron_offset = neutron_offset
        self.table.update()

    def on_spectrum_lines_changed(self, state):
        """Handle spectrum lines overlay toggle"""
        self.table.show_spectrum_lines = (state == Qt.CheckState.Checked.value)
        self.table.update()

    def _create_orbital_group(self):
        """Create orbital and atomic visualization controls"""
        collapsible = CollapsibleBox("Orbital & Atomic Visualization", "#f093fb")
        layout = QVBoxLayout()

        # Nucleus to shell ratio slider (horizontal compact)
        ratio_container = QWidget()
        ratio_layout = QHBoxLayout(ratio_container)
        ratio_layout.setContentsMargins(0, 5, 0, 0)
        ratio_layout.setSpacing(8)

        ratio_label = QLabel("Nucleus/Shell Ratio:")
        ratio_label.setStyleSheet("color: white; font-size: 10px; min-width: 120px;")
        ratio_layout.addWidget(ratio_label)

        self.ratio_slider = QSlider(Qt.Orientation.Horizontal)
        self.ratio_slider.setMinimum(1)  # 1/1000 = 0.001x
        self.ratio_slider.setMaximum(2000)  # 2.0x
        self.ratio_slider.setValue(1000)  # 1.0x default
        self.ratio_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #666;
                height: 6px;
                background: rgba(40, 40, 60, 200);
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #f093fb;
                border: 1px solid #f093fb;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """)
        self.ratio_slider.valueChanged.connect(self.on_ratio_changed)
        ratio_layout.addWidget(self.ratio_slider)

        self.ratio_value_label = QLabel("1.0x")
        self.ratio_value_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px; min-width: 50px;")
        ratio_layout.addWidget(self.ratio_value_label)

        layout.addWidget(ratio_container)

        # Cloud opacity slider (horizontal compact)
        opacity_container = QWidget()
        opacity_layout = QHBoxLayout(opacity_container)
        opacity_layout.setContentsMargins(0, 5, 0, 0)
        opacity_layout.setSpacing(8)

        opacity_label = QLabel("Cloud Opacity:")
        opacity_label.setStyleSheet("color: white; font-size: 10px; min-width: 120px;")
        opacity_layout.addWidget(opacity_label)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(0)  # 0% opacity (invisible)
        self.opacity_slider.setMaximum(100)  # 100% opacity (fully visible)
        self.opacity_slider.setValue(33)  # Default 33% (1/3)
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #666;
                height: 6px;
                background: rgba(40, 40, 60, 200);
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #f093fb;
                border: 1px solid #f093fb;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)

        self.opacity_value_label = QLabel("33%")
        self.opacity_value_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px; min-width: 35px;")
        opacity_layout.addWidget(self.opacity_value_label)

        layout.addWidget(opacity_container)

        # Nucleus/Shell Ratio Power (Distance * (NucleusShellRatio)^power)
        power_container = QWidget()
        power_layout = QHBoxLayout(power_container)
        power_layout.setContentsMargins(0, 5, 0, 0)
        power_layout.setSpacing(8)

        power_label = QLabel("Ratio Power:")
        power_label.setStyleSheet("color: white; font-size: 10px; min-width: 120px;")
        power_layout.addWidget(power_label)

        self.ratio_power_slider = QSlider(Qt.Orientation.Horizontal)
        self.ratio_power_slider.setMinimum(0)   # 0.0
        self.ratio_power_slider.setMaximum(1000) # 100.0
        self.ratio_power_slider.setValue(500)    # 50.0 default (5.0 on 0-10 scale)
        self.ratio_power_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #666;
                height: 6px;
                background: rgba(40, 40, 60, 200);
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #f093fb;
                border: 1px solid #f093fb;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """)
        self.ratio_power_slider.valueChanged.connect(self.on_ratio_power_changed)
        power_layout.addWidget(self.ratio_power_slider)

        self.ratio_power_label = QLabel("50.0")
        self.ratio_power_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px; min-width: 45px;")
        power_layout.addWidget(self.ratio_power_label)

        layout.addWidget(power_container)

        # Orbital selector dropdown
        orbital_selector_container = QWidget()
        orbital_selector_layout = QHBoxLayout(orbital_selector_container)
        orbital_selector_layout.setContentsMargins(0, 5, 0, 0)
        orbital_selector_layout.setSpacing(8)

        orbital_selector_label = QLabel("Orbital:")
        orbital_selector_label.setStyleSheet("color: white; font-size: 10px; min-width: 50px;")
        orbital_selector_layout.addWidget(orbital_selector_label)

        self.orbital_selector = QComboBox()
        self.orbital_selector.setStyleSheet("""
            QComboBox {
                background: rgba(60, 60, 80, 180);
                color: white;
                border: 1px solid rgba(100, 100, 150, 100);
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 10px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid white;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background: rgba(40, 40, 60, 240);
                color: white;
                selection-background-color: rgba(100, 100, 150, 180);
                border: 1px solid rgba(100, 100, 150, 100);
            }
        """)
        self.orbital_selector.currentIndexChanged.connect(self.on_orbital_selected)
        orbital_selector_layout.addWidget(self.orbital_selector)

        layout.addWidget(orbital_selector_container)

        # Current orbital display (for additional info)
        self.current_orbital_label = QLabel("Current: 1s (n=1, l=0, m=0)")
        self.current_orbital_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; margin-left: 20px;")
        layout.addWidget(self.current_orbital_label)

        # Info label for orbital selection
        orbital_info = QLabel("Select orbital from dropdown or click electron in shell")
        orbital_info.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; font-style: italic; margin-top: 8px;")
        orbital_info.setWordWrap(True)
        layout.addWidget(orbital_info)

        # 3D Transform Controls (for nucleus, electron clouds, and subatomic particles)
        self.transform_controls = TransformControlsWidget(
            title="3D Transform Controls",
            show_rotation=True,
            show_translation=True,
            show_zoom=True,
            accent_color="#f093fb"
        )
        self.transform_controls.transform_changed.connect(self._on_transform_changed)
        layout.addWidget(self.transform_controls)

        # Transfer widgets to collapsible box
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                collapsible.content_layout.addWidget(item.widget())

        # Open by default
        collapsible.toggle_button.setChecked(True)
        collapsible.on_toggle()

        return collapsible

    def on_element_table_changed(self, state):
        """Toggle element table visibility"""
        self.table.show_element_table = (state == Qt.CheckState.Checked.value)
        self.table.update()

    def on_subatomic_changed(self, state):
        """Toggle subatomic particle overlay"""
        self.table.show_subatomic_particles = (state == Qt.CheckState.Checked.value)
        self.table.update()

    def on_orbital_cloud_changed(self, state):
        """Toggle orbital probability cloud visibility"""
        self.table.show_orbital_cloud = (state == Qt.CheckState.Checked.value)
        self.table.update()

    def update_orbital_selector(self):
        """Update the orbital selector dropdown based on selected element"""
        if not self.table.selected_element:
            self.orbital_selector.clear()
            self.orbital_selector.addItem("No element selected")
            self.orbital_selector.setEnabled(False)
            return

        z = self.table.selected_element.get('z', 1)
        available_orbitals = self.table.get_available_orbitals(z)

        # Block signals while updating
        self.orbital_selector.blockSignals(True)
        self.orbital_selector.clear()
        self.orbital_selector.setEnabled(True)

        # Store orbital data as item data
        for n, l, m, label in available_orbitals:
            self.orbital_selector.addItem(label)
            # Store n, l, m as user data
            self.orbital_selector.setItemData(self.orbital_selector.count() - 1, (n, l, m))

        # Select the current orbital if it exists in the list
        current_n = self.table.orbital_n
        current_l = self.table.orbital_l
        current_m = self.table.orbital_m

        for i in range(self.orbital_selector.count()):
            n, l, m = self.orbital_selector.itemData(i)
            if n == current_n and l == current_l and m == current_m:
                self.orbital_selector.setCurrentIndex(i)
                break

        self.orbital_selector.blockSignals(False)
        self.update_orbital_label()

    def on_orbital_selected(self, index):
        """Handle orbital selection from dropdown"""
        if index < 0 or not self.table.selected_element:
            return

        orbital_data = self.orbital_selector.itemData(index)
        if orbital_data:
            n, l, m = orbital_data
            self.table.orbital_n = n
            self.table.orbital_l = l
            self.table.orbital_m = m
            self.update_orbital_label()
            self.table.update()

    def update_orbital_label(self):
        """Update the current orbital label text"""
        n = self.table.orbital_n
        l = self.table.orbital_l
        m = self.table.orbital_m

        # Convert l to letter (0=s, 1=p, 2=d, 3=f)
        l_letter = ['s', 'p', 'd', 'f', 'g', 'h'][l] if l < 6 else str(l)
        orbital_name = f"{n}{l_letter}"

        self.current_orbital_label.setText(f"Current: {orbital_name} (n={n}, l={l}, m={m})")

    def on_ratio_changed(self, value):
        """Update nucleus to shell ratio"""
        # Map slider 1-2000 to 0.001-2.0 (1/1000 to 2)
        ratio = value / 1000.0
        self.table.nucleus_to_shell_ratio = ratio
        # Format based on size: use scientific notation for very small values
        if ratio < 0.01:
            self.ratio_value_label.setText(f"{ratio:.1e}x")
        else:
            self.ratio_value_label.setText(f"{ratio:.3f}x")
        self.table.update()

    def on_opacity_changed(self, value):
        """Update cloud opacity"""
        opacity = value / 100.0
        self.table.cloud_opacity = opacity
        self.opacity_value_label.setText(f"{value}%")
        self.table.update()

    def on_ratio_power_changed(self, value):
        """Update nucleus/shell ratio power using logarithmic lerp
        Formula: lerp(log10(base_value * ratio), 0, 10, slider_t)
        where slider_t ranges from 0 to 1 based on slider position
        """
        power = value / 10.0  # Convert 0-1000 slider to 0.0-100.0
        # Apply same power to both cloud and shell
        self.table.cloud_power = power
        self.table.shell_power = power
        self.ratio_power_label.setText(f"{power:.1f}")
        self.table.update()

    def _on_transform_changed(self, transform: Transform3D):
        """Handle 3D transform changes from the unified control widget"""
        # Update table rotation (convert degrees to radians for compatibility)
        self.table.rotation_x = math.radians(transform.pitch)
        self.table.rotation_y = math.radians(transform.yaw)

        # Store transform for more advanced usage
        if hasattr(self.table, 'transform_3d'):
            self.table.transform_3d = transform

        # Emit signal for external listeners
        self.transform_changed.emit(transform)

        self.table.update()

    def reset_property_mappings(self):
        """Reset all property controls to their default mappings"""
        # 1. Fill Colour -> Emission Wavelength (index 16)
        self.fill_color_control.property_combo.setCurrentIndex(16)

        # 2. Border Colour -> Electron Affinity (index 8)
        self.border_color_control.property_combo.setCurrentIndex(8)

        # 3. Border Size -> Valence Electrons (index 9)
        self.border_size_control.property_combo.setCurrentIndex(9)

        # 4. Inner Ring Colour -> Orbital Block (index 12)
        self.ring_color_control.property_combo.setCurrentIndex(12)

        # 5. Inner Ring Size -> Electronegativity (index 4)
        self.ring_size_control.property_combo.setCurrentIndex(4)

        # 6. Glow Colour -> Atomic Radius (index 6)
        self.glow_color_control.property_combo.setCurrentIndex(6)

        # 7. Glow Radius/Intensity -> Ionization Energy (index 3)
        self.glow_intensity_control.property_combo.setCurrentIndex(3)

        # 8. Symbol Text Colour -> Melting Point (index 4)
        self.symbol_text_color_control.property_combo.setCurrentIndex(4)

        # 9. Atomic Number Text Colour -> Boiling Point (index 5)
        self.atomic_number_text_color_control.property_combo.setCurrentIndex(5)

        self.table.update()

    def reset_view(self):
        """Reset zoom and pan to default"""
        self.table.zoom_level = 1.0
        self.table.pan_x = 0
        self.table.pan_y = 0
        self.table.update()

    def _create_ai_generation_group(self):
        """Create AI generation controls group"""
        self.ai_widget = AIGenerationWidget("element", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        return self.ai_widget

    def refresh_ai_status(self):
        """Refresh the AI API configuration status."""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()

    def _create_data_management_group(self):
        """Create data management controls group"""
        data_mgmt_group = QGroupBox("Data Management")
        data_mgmt_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid #26a69a;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        data_mgmt_layout = QVBoxLayout(data_mgmt_group)

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

        data_mgmt_layout.addLayout(btn_layout)

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

        data_mgmt_layout.addLayout(btn_layout2)

        # Create button (for creating from sub-components)
        self.create_btn = QPushButton("Create from Particles")
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
        data_mgmt_layout.addWidget(self.create_btn)

        # Reset button
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
        data_mgmt_layout.addWidget(self.reset_data_btn)

        # Item count label
        self.item_count_label = QLabel("Items: 0")
        self.item_count_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px; margin-top: 5px;")
        data_mgmt_layout.addWidget(self.item_count_label)

        return data_mgmt_group

    def set_item_selected(self, selected: bool):
        """Enable/disable edit and remove buttons based on selection state"""
        self.edit_btn.setEnabled(selected)
        self.remove_btn.setEnabled(selected)
        self.export_btn.setEnabled(selected)
        self.duplicate_btn.setEnabled(selected)

    def update_item_count(self, count):
        """Update the item count label"""
        self.item_count_label.setText(f"Items: {count}")

