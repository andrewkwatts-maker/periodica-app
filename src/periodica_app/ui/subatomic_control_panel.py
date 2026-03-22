"""
Control Panel for Subatomic Particles Tab
Provides UI controls for layout mode, property mappings, and filters
Polished to match the Atoms tab feature set
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                                QScrollArea, QRadioButton, QComboBox, QCheckBox,
                                QPushButton, QFrame, QSlider, QToolButton)
from PySide6.QtCore import Qt, QPropertyAnimation, Signal
from PySide6.QtGui import QFont

from periodica.core.subatomic_enums import SubatomicLayoutMode, SubatomicProperty, ParticleCategory
from periodica.data.data_manager import get_data_manager, DataCategory
from periodica_app.ui.components import UnifiedPropertyMappingWidget
from periodica_app.ui.transform_controls import TransformControlsWidget, Transform3D
from periodica_app.ui.ai_generation_widget import AIGenerationWidget


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


class SubatomicPropertyControl(QWidget):
    """Expandable control for a single visual property with range controls and filtering"""
    def __init__(self, title, property_key, parent_panel, available_properties, control_type="color", default_index=0):
        super().__init__()
        self.property_key = property_key
        self.parent_panel = parent_panel
        self.control_type = control_type
        self.is_expanded = False
        self.default_index = default_index
        self.user_selected_index = default_index

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

        # Unified property mapping widget
        mapping_label = QLabel("Property Mapping & Filtering:")
        mapping_label.setStyleSheet("color: rgba(255,255,255,200); font-size: 9px; font-weight: bold;")
        details_layout.addWidget(mapping_label)

        self.unified_mapping = UnifiedPropertyMappingWidget(property_name="mass", property_type=control_type)
        self.unified_mapping.color_range_changed.connect(self.on_unified_color_range_changed)
        self.unified_mapping.filter_range_changed.connect(self.on_unified_filter_range_changed)
        self.unified_mapping.gradient_colors_changed.connect(self.on_unified_gradient_colors_changed)
        details_layout.addWidget(self.unified_mapping)

        # Fade slider (for color properties only)
        if self.control_type == "color":
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
        self.current_property_name = "none"

    def on_unified_color_range_changed(self, min_map, max_map):
        """Handle color mapping range change from unified widget"""
        if hasattr(self, 'property_key') and hasattr(self.parent_panel, 'table'):
            # Map property key to table attribute
            attr_map = {
                "fill_color": ("fill_property_min_map", "fill_property_max_map"),
                "border_color": ("border_property_min_map", "border_property_max_map"),
                "glow_color": ("glow_property_min_map", "glow_property_max_map"),
                "ring_color": ("ring_property_min_map", "ring_property_max_map"),
                "symbol_text_color": ("symbol_text_color_property_min_map", "symbol_text_color_property_max_map"),
            }

            if self.property_key in attr_map:
                min_attr, max_attr = attr_map[self.property_key]
                if hasattr(self.parent_panel.table, min_attr):
                    setattr(self.parent_panel.table, min_attr, min_map)
                if hasattr(self.parent_panel.table, max_attr):
                    setattr(self.parent_panel.table, max_attr, max_map)
                self.parent_panel.table.update()

    def on_unified_gradient_colors_changed(self, start_color, end_color):
        """Handle gradient color change from unified widget color pickers"""
        if hasattr(self, 'property_key') and hasattr(self.parent_panel, 'table'):
            gradient_attr_map = {
                "fill_color": ("custom_fill_gradient_start", "custom_fill_gradient_end"),
                "border_color": ("custom_border_gradient_start", "custom_border_gradient_end"),
                "ring_color": ("custom_ring_gradient_start", "custom_ring_gradient_end"),
                "glow_color": ("custom_glow_gradient_start", "custom_glow_gradient_end"),
                "symbol_text_color": ("custom_symbol_text_gradient_start", "custom_symbol_text_gradient_end"),
            }

            if self.property_key in gradient_attr_map:
                start_attr, end_attr = gradient_attr_map[self.property_key]
                if hasattr(self.parent_panel.table, start_attr):
                    setattr(self.parent_panel.table, start_attr, start_color)
                if hasattr(self.parent_panel.table, end_attr):
                    setattr(self.parent_panel.table, end_attr, end_color)
                self.parent_panel.table.update()

    def on_unified_filter_range_changed(self, min_filter, max_filter):
        """Handle filter range change from unified widget"""
        if self.current_property_name != "none" and hasattr(self.parent_panel, 'table'):
            if hasattr(self.parent_panel.table, 'filters'):
                if self.current_property_name not in self.parent_panel.table.filters:
                    self.parent_panel.table.filters[self.current_property_name] = {}
                self.parent_panel.table.filters[self.current_property_name]['min'] = min_filter
                self.parent_panel.table.filters[self.current_property_name]['max'] = max_filter
                self.parent_panel.table.filters[self.current_property_name]['active'] = self.unified_mapping.filter_enabled
                self.parent_panel.table.update()

    def on_property_selection_changed(self, idx):
        """Handle property selection change - update ranges and call parent"""
        property_display_name = self.available_properties[idx]
        property_name = property_display_name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_").replace("^", "")
        self.current_property_name = property_name

        # Get metadata for subatomic properties
        metadata = self._get_subatomic_property_metadata(property_name)
        if metadata:
            self.data_min = metadata.get("min_value", 0)
            self.data_max = metadata.get("max_value", 100)
            self.data_unit = metadata.get("unit", "")
        else:
            self.data_min = 0
            self.data_max = 100
            self.data_unit = ""

        # Update the unified mapping widget
        self.unified_mapping.set_property(property_name, self.control_type)
        self.unified_mapping.set_value_range(self.data_min, self.data_max)
        self.unified_mapping.set_color_map_range(self.data_min, self.data_max)
        self.unified_mapping.set_filter_range(self.data_min, self.data_max)

        # Call parent's handler
        self.parent_panel.on_property_changed(self.property_key, idx)

    def _get_subatomic_property_metadata(self, property_name):
        """Get metadata for subatomic particle properties - comprehensive list"""
        metadata_map = {
            # Mass properties
            "mass_mevc2": {"min_value": 0, "max_value": 12000, "unit": "MeV/c^2", "log_scale": False},
            "mass": {"min_value": 0, "max_value": 12000, "unit": "MeV/c^2", "log_scale": False},
            "mass_log_scale": {"min_value": 2.0, "max_value": 4.5, "unit": "log10(MeV)", "log_scale": True},

            # Charge properties
            "charge_e": {"min_value": -2, "max_value": 2, "unit": "e", "log_scale": False},
            "charge": {"min_value": -2, "max_value": 2, "unit": "e", "log_scale": False},
            "electric_charge": {"min_value": -2, "max_value": 2, "unit": "e", "log_scale": False},
            "electric_charge_e": {"min_value": -2, "max_value": 2, "unit": "e", "log_scale": False},

            # Spin properties
            "spin_hbar": {"min_value": 0, "max_value": 3.5, "unit": "h-bar", "log_scale": False},
            "spin": {"min_value": 0, "max_value": 3.5, "unit": "h-bar", "log_scale": False},

            # Baryon/Lepton numbers
            "baryonnumber_b": {"min_value": -1, "max_value": 1, "unit": "B", "log_scale": False},
            "baryon_number": {"min_value": -1, "max_value": 1, "unit": "B", "log_scale": False},
            "baryon_number_b": {"min_value": -1, "max_value": 1, "unit": "B", "log_scale": False},
            "leptonnumber_l": {"min_value": -1, "max_value": 1, "unit": "L", "log_scale": False},
            "lepton_number": {"min_value": -1, "max_value": 1, "unit": "L", "log_scale": False},
            "lepton_number_l": {"min_value": -1, "max_value": 1, "unit": "L", "log_scale": False},

            # Isospin properties
            "isospin_i": {"min_value": 0, "max_value": 1.5, "unit": "I", "log_scale": False},
            "isospin_i3": {"min_value": -1.5, "max_value": 1.5, "unit": "I3", "log_scale": False},
            "isospin": {"min_value": 0, "max_value": 1.5, "unit": "I", "log_scale": False},
            "isospin_i3": {"min_value": -1.5, "max_value": 1.5, "unit": "I3", "log_scale": False},

            # Flavor quantum numbers
            "strangeness": {"min_value": -3, "max_value": 0, "unit": "S", "log_scale": False},
            "strangeness_s": {"min_value": -3, "max_value": 0, "unit": "S", "log_scale": False},
            "charm": {"min_value": -2, "max_value": 2, "unit": "C", "log_scale": False},
            "charm_c": {"min_value": -2, "max_value": 2, "unit": "C", "log_scale": False},
            "bottomness": {"min_value": -1, "max_value": 1, "unit": "B'", "log_scale": False},
            "bottomness_b": {"min_value": -1, "max_value": 1, "unit": "B'", "log_scale": False},

            # Parity properties
            "parity": {"min_value": -1, "max_value": 1, "unit": "P", "log_scale": False},
            "parity_p": {"min_value": -1, "max_value": 1, "unit": "P", "log_scale": False},
            "c-parity": {"min_value": -1, "max_value": 1, "unit": "C", "log_scale": False},
            "cparity": {"min_value": -1, "max_value": 1, "unit": "C", "log_scale": False},

            # Lifetime/decay properties
            "half_life": {"min_value": 0, "max_value": 1e-8, "unit": "s", "log_scale": False},
            "half-life": {"min_value": 0, "max_value": 1e-8, "unit": "s", "log_scale": False},
            "half-life_log": {"min_value": -25, "max_value": -5, "unit": "log10(s)", "log_scale": True},
            "half_life_log": {"min_value": -25, "max_value": -5, "unit": "log10(s)", "log_scale": True},
            "mean_lifetime": {"min_value": 0, "max_value": 1e-8, "unit": "s", "log_scale": False},
            "mean_lifetime_log": {"min_value": -25, "max_value": -5, "unit": "log10(s)", "log_scale": True},
            "decay_width": {"min_value": 0, "max_value": 200, "unit": "MeV", "log_scale": False},
            "decay_width_mev": {"min_value": 0, "max_value": 200, "unit": "MeV", "log_scale": False},

            # Stability and misc
            "stability": {"min_value": 0, "max_value": 1, "unit": "", "log_scale": False},
            "quark_count": {"min_value": 2, "max_value": 3, "unit": "", "log_scale": False},
            "none": {"min_value": 0, "max_value": 100, "unit": "", "log_scale": False},
        }
        return metadata_map.get(property_name, None)

    def on_fade_changed(self, value):
        """Handle fade slider change"""
        self.fade_display.setText(f"{value}%")
        if hasattr(self.parent_panel, 'table'):
            fade_map = {
                "fill_color": "fill_fade",
                "border_color": "border_color_fade",
                "ring_color": "ring_color_fade",
                "glow_color": "glow_color_fade",
                "symbol_text_color": "symbol_text_color_fade"
            }
            if self.property_key in fade_map:
                attr = fade_map[self.property_key]
                if hasattr(self.parent_panel.table, attr):
                    setattr(self.parent_panel.table, attr, value / 100.0)
                    self.parent_panel.table.update()

    def toggle_expanded(self):
        """Toggle expanded/collapsed state"""
        self.is_expanded = not self.is_expanded
        self.expand_btn.setArrowType(Qt.ArrowType.DownArrow if self.is_expanded else Qt.ArrowType.RightArrow)
        self.details_widget.setVisible(self.is_expanded)

    def on_use_default_toggled(self, checked):
        """Toggle using default color/value for this property"""
        self.property_combo.setEnabled(not checked)

        if checked:
            self.user_selected_index = self.property_combo.currentIndex()
            self.property_combo.blockSignals(True)
            self.property_combo.setCurrentIndex(self.default_index)
            self.property_combo.blockSignals(False)
            self.on_property_selection_changed(self.default_index)
        else:
            self.property_combo.blockSignals(True)
            self.property_combo.setCurrentIndex(self.user_selected_index)
            self.property_combo.blockSignals(False)
            self.on_property_selection_changed(self.user_selected_index)

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


class SubatomicControlPanel(QWidget):
    """Control panel for subatomic particle visualization settings"""

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

    # 3D Transform signal (for quark composition visualization)
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

        title = QLabel("Subatomic Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        layout.addWidget(title)

        # Layout Mode Selection (always expanded)
        layout.addWidget(self._create_layout_mode_group())

        # Visual Property Encodings (collapsible with full controls)
        layout.addWidget(self._create_visual_properties_group())

        # Filter Options (collapsible)
        layout.addWidget(self._create_filter_group())

        # View Controls
        layout.addWidget(self._create_view_controls_group())

        # 3D Transform Controls (for quark composition visualization)
        layout.addWidget(self._create_transform_controls_group())

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
        """Create layout mode selection group - always expanded"""
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

        # Original 4 layout modes
        self.baryon_meson_radio = QRadioButton("Baryon/Meson Groups")
        self.baryon_meson_radio.setStyleSheet(radio_style)
        self.baryon_meson_radio.setChecked(True)
        self.baryon_meson_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.BARYON_MESON) if self.baryon_meson_radio.isChecked() else None)

        self.mass_radio = QRadioButton("Mass Order")
        self.mass_radio.setStyleSheet(radio_style)
        self.mass_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.MASS_ORDER) if self.mass_radio.isChecked() else None)

        self.charge_radio = QRadioButton("Charge Order")
        self.charge_radio.setStyleSheet(radio_style)
        self.charge_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.CHARGE_ORDER) if self.charge_radio.isChecked() else None)

        self.decay_radio = QRadioButton("Decay Chains")
        self.decay_radio.setStyleSheet(radio_style)
        self.decay_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.DECAY_CHAIN) if self.decay_radio.isChecked() else None)

        self.quark_radio = QRadioButton("Quark Content")
        self.quark_radio.setStyleSheet(radio_style)
        self.quark_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.QUARK_CONTENT) if self.quark_radio.isChecked() else None)

        # 4 New layout modes
        self.eightfold_radio = QRadioButton("Eightfold Way")
        self.eightfold_radio.setStyleSheet(radio_style)
        self.eightfold_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.EIGHTFOLD_WAY) if self.eightfold_radio.isChecked() else None)

        self.lifetime_radio = QRadioButton("Lifetime Spectrum")
        self.lifetime_radio.setStyleSheet(radio_style)
        self.lifetime_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.LIFETIME_SPECTRUM) if self.lifetime_radio.isChecked() else None)

        self.quark_tree_radio = QRadioButton("Quark Tree")
        self.quark_tree_radio.setStyleSheet(radio_style)
        self.quark_tree_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.QUARK_TREE) if self.quark_tree_radio.isChecked() else None)

        self.discovery_radio = QRadioButton("Discovery Timeline")
        self.discovery_radio.setStyleSheet(radio_style)
        self.discovery_radio.toggled.connect(
            lambda: self._on_layout_changed(SubatomicLayoutMode.DISCOVERY_TIMELINE) if self.discovery_radio.isChecked() else None)

        layout_box.addWidget(self.baryon_meson_radio)
        layout_box.addWidget(self.mass_radio)
        layout_box.addWidget(self.charge_radio)
        layout_box.addWidget(self.decay_radio)
        layout_box.addWidget(self.quark_radio)
        layout_box.addWidget(self.eightfold_radio)
        layout_box.addWidget(self.lifetime_radio)
        layout_box.addWidget(self.quark_tree_radio)
        layout_box.addWidget(self.discovery_radio)

        # Zoom controls info for all modes
        zoom_info = QLabel("Camera Controls (All Modes):\n  Scroll wheel: Zoom\n  Middle-click or Ctrl+drag: Pan")
        zoom_info.setStyleSheet("color: rgba(255,255,255,180); font-size: 9px; margin-top: 8px;")
        zoom_info.setWordWrap(True)
        layout_box.addWidget(zoom_info)

        # Reset zoom button
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
        layout_box.addWidget(reset_btn)

        layout_group.setLayout(layout_box)
        return layout_group

    def _create_visual_properties_group(self):
        """Create visual property encodings with expandable controls"""
        collapsible = CollapsibleBox("Visual Property Encodings", "#764ba2")
        properties_layout = QVBoxLayout()

        # Available property options for subatomic particles - comprehensive list
        color_properties = [
            "Mass (MeV/c^2)",
            "Mass (log scale)",
            "Electric Charge (e)",
            "Spin (hbar)",
            "Half-Life (log)",
            "Mean Lifetime (log)",
            "Decay Width (MeV)",
            "Strangeness (S)",
            "Charm (C)",
            "Bottomness (B')",
            "Isospin (I)",
            "Isospin I3",
            "Baryon Number (B)",
            "Lepton Number (L)",
            "Parity (P)",
            "C-Parity",
            "Stability",
            "Quark Count",
            "None"
        ]

        # Visual attribute controls with comprehensive property options
        # Index mapping for the new property list:
        # 0=Mass, 1=Mass(log), 2=Charge, 3=Spin, 4=Half-Life(log), 5=Mean Lifetime(log),
        # 6=Decay Width, 7=Strangeness, 8=Charm, 9=Bottomness, 10=Isospin(I),
        # 11=Isospin I3, 12=Baryon Number, 13=Lepton Number, 14=Parity, 15=C-Parity,
        # 16=Stability, 17=Quark Count, 18=None

        # 1. Fill Colour -> Mass (log scale for better visualization)
        self.fill_color_control = SubatomicPropertyControl(
            "Fill Colour", "fill_color", self, color_properties,
            control_type="color", default_index=1)  # Mass (log scale)
        self.fill_color_control.property_combo.setCurrentIndex(1)
        properties_layout.addWidget(self.fill_color_control)

        # 2. Border Colour -> Electric Charge
        self.border_color_control = SubatomicPropertyControl(
            "Border Colour", "border_color", self, color_properties,
            control_type="color", default_index=2)  # Electric Charge
        self.border_color_control.property_combo.setCurrentIndex(2)
        properties_layout.addWidget(self.border_color_control)

        # 3. Glow Colour -> Half-Life (log) - unstable particles glow more
        self.glow_color_control = SubatomicPropertyControl(
            "Glow Colour", "glow_color", self, color_properties,
            control_type="color", default_index=4)  # Half-Life (log)
        self.glow_color_control.property_combo.setCurrentIndex(4)
        properties_layout.addWidget(self.glow_color_control)

        # 4. Inner Ring Colour -> Strangeness (for strange baryons/mesons)
        self.ring_color_control = SubatomicPropertyControl(
            "Inner Ring Colour", "ring_color", self, color_properties,
            control_type="color", default_index=7)  # Strangeness
        self.ring_color_control.property_combo.setCurrentIndex(7)
        properties_layout.addWidget(self.ring_color_control)

        # 5. Symbol Text Colour -> Isospin I3
        self.symbol_text_color_control = SubatomicPropertyControl(
            "Symbol Text Colour", "symbol_text_color", self, color_properties,
            control_type="color", default_index=11)  # Isospin I3
        self.symbol_text_color_control.property_combo.setCurrentIndex(11)
        properties_layout.addWidget(self.symbol_text_color_control)

        # 6. Size Scaling -> Mass (log scale)
        size_properties = [
            "Mass (MeV/c^2)",
            "Mass (log scale)",
            "Electric Charge (e)",
            "Spin (hbar)",
            "Quark Count",
            "Isospin (I)",
            "None"
        ]
        self.size_scale_control = SubatomicPropertyControl(
            "Size Scaling", "size_scale", self, size_properties,
            control_type="size", default_index=1)  # Mass (log scale)
        self.size_scale_control.property_combo.setCurrentIndex(1)
        properties_layout.addWidget(self.size_scale_control)

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

        return collapsible

    def _create_filter_group(self):
        """Create particle type filter group (collapsible)"""
        collapsible = CollapsibleBox("Filter Options", "#764ba2")
        layout = QVBoxLayout()

        checkbox_style = """
            QCheckBox {
                color: white;
                spacing: 8px;
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
        """

        # Particle type section
        type_label = QLabel("Particle Type:")
        type_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px;")
        layout.addWidget(type_label)

        # Particle type checkboxes
        self.show_baryons_check = QCheckBox("Show Baryons")
        self.show_baryons_check.setStyleSheet(checkbox_style)
        self.show_baryons_check.setChecked(True)
        self.show_baryons_check.toggled.connect(self._on_filter_changed)
        layout.addWidget(self.show_baryons_check)

        self.show_mesons_check = QCheckBox("Show Mesons")
        self.show_mesons_check.setStyleSheet(checkbox_style)
        self.show_mesons_check.setChecked(True)
        self.show_mesons_check.toggled.connect(self._on_filter_changed)
        layout.addWidget(self.show_mesons_check)

        # Stability filter section
        stability_label = QLabel("Stability:")
        stability_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 10px;")
        layout.addWidget(stability_label)

        self.show_stable_check = QCheckBox("Show Stable")
        self.show_stable_check.setStyleSheet(checkbox_style)
        self.show_stable_check.setChecked(True)
        self.show_stable_check.toggled.connect(self._on_filter_changed)
        layout.addWidget(self.show_stable_check)

        self.show_unstable_check = QCheckBox("Show Unstable")
        self.show_unstable_check.setStyleSheet(checkbox_style)
        self.show_unstable_check.setChecked(True)
        self.show_unstable_check.toggled.connect(self._on_filter_changed)
        layout.addWidget(self.show_unstable_check)

        # Charge filter section
        charge_label = QLabel("Charge Filter:")
        charge_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 10px;")
        layout.addWidget(charge_label)

        charge_layout = QHBoxLayout()
        self.charge_combo = QComboBox()
        self.charge_combo.addItems(["All", "+2", "+1", "0", "-1", "-2"])
        self.charge_combo.setStyleSheet("""
            QComboBox {
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid #764ba2;
                padding: 5px;
                border-radius: 4px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: rgba(30, 30, 50, 250);
                color: white;
                selection-background-color: #764ba2;
            }
        """)
        self.charge_combo.currentIndexChanged.connect(self._on_charge_filter_changed)
        charge_layout.addWidget(self.charge_combo)
        charge_layout.addStretch()
        layout.addLayout(charge_layout)

        # Transfer widgets to collapsible box
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                collapsible.content_layout.addWidget(item.widget())
            elif item.layout():
                container = QWidget()
                container.setLayout(item.layout())
                collapsible.content_layout.addWidget(container)

        # Open by default
        collapsible.toggle_button.setChecked(True)
        collapsible.on_toggle()

        return collapsible

    def _create_view_controls_group(self):
        """Create view control buttons"""
        view_group = QGroupBox("View Controls")
        view_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid #4fc3f7;
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
        layout = QVBoxLayout()

        button_style = """
            QPushButton {
                background: rgba(79, 195, 247, 150);
                color: white;
                border: none;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(79, 195, 247, 200);
            }
        """

        # Reset view button
        reset_btn = QPushButton("Reset View")
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self._on_reset_view)
        reset_btn.setToolTip("Reset zoom and pan to default view")
        layout.addWidget(reset_btn)

        # Zoom info
        zoom_info = QLabel("Scroll: Zoom\nMiddle-click: Pan")
        zoom_info.setStyleSheet("color: rgba(255,255,255,150); font-size: 9px;")
        layout.addWidget(zoom_info)

        view_group.setLayout(layout)
        return view_group

    def _create_transform_controls_group(self):
        """Create 3D transform controls for quark composition visualization"""
        self.transform_controls = TransformControlsWidget(
            title="3D Transform Controls",
            show_rotation=True,
            show_translation=True,
            show_zoom=True,
            accent_color="#4fc3f7"
        )
        self.transform_controls.transform_changed.connect(self._on_transform_changed)
        return self.transform_controls

    def _on_transform_changed(self, transform: Transform3D):
        """Handle 3D transform changes for quark visualization"""
        self.transform_changed.emit(transform)
        if hasattr(self.table, 'transform_3d'):
            self.table.transform_3d = transform
            self.table.update()

    def _create_ai_generation_group(self):
        """Create AI generation controls group"""
        self.ai_widget = AIGenerationWidget("subatomic", self)
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
        group.setStyleSheet("""
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

        # Create button (for creating from quarks)
        self.create_btn = QPushButton("Create from Quarks")
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
        layout.addWidget(self.reset_data_btn)

        # Item count label
        self.item_count_label = QLabel("Items: 0")
        self.item_count_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px; margin-top: 5px;")
        layout.addWidget(self.item_count_label)

        group.setLayout(layout)
        return group

    def _on_layout_changed(self, mode):
        """Handle layout mode change"""
        self.table.set_layout_mode(mode)

    def _on_filter_changed(self):
        """Handle filter checkbox change"""
        self.table.set_filter(
            show_baryons=self.show_baryons_check.isChecked(),
            show_mesons=self.show_mesons_check.isChecked(),
            show_stable=self.show_stable_check.isChecked(),
            show_unstable=self.show_unstable_check.isChecked(),
            charge=self._get_charge_filter()
        )

    def _on_charge_filter_changed(self, index):
        """Handle charge filter combo change"""
        self._on_filter_changed()

    def _get_charge_filter(self):
        """Get current charge filter value"""
        charge_text = self.charge_combo.currentText()
        if charge_text == "All":
            return None
        elif charge_text == "+2":
            return 2
        elif charge_text == "+1":
            return 1
        elif charge_text == "0":
            return 0
        elif charge_text == "-1":
            return -1
        elif charge_text == "-2":
            return -2
        return None

    def on_property_changed(self, property_key, index):
        """Handle property selection change from property controls"""
        # Map property options to internal property names
        property_map = {
            0: SubatomicProperty.MASS,
            1: SubatomicProperty.CHARGE,
            2: SubatomicProperty.SPIN,
            3: SubatomicProperty.HALF_LIFE,
            4: SubatomicProperty.STRANGENESS,
            5: SubatomicProperty.ISOSPIN,
            6: SubatomicProperty.BARYON_NUMBER,
            7: SubatomicProperty.STABILITY,
            8: SubatomicProperty.NONE,
        }

        prop = property_map.get(index, SubatomicProperty.NONE)

        if property_key == "fill_color":
            self.table.fill_property = prop
        elif property_key == "border_color":
            self.table.border_property = prop
        elif property_key == "glow_color":
            self.table.glow_property = prop
        elif property_key == "ring_color":
            if hasattr(self.table, 'ring_property'):
                self.table.ring_property = prop
        elif property_key == "symbol_text_color":
            if hasattr(self.table, 'symbol_text_property'):
                self.table.symbol_text_property = prop
        elif property_key == "size_scale":
            if hasattr(self.table, 'size_scale_property'):
                self.table.size_scale_property = prop

        self.table.update()

    def _on_reset_view(self):
        """Reset view to default"""
        self.table.reset_view()

    def reset_property_mappings(self):
        """Reset all property controls to their default mappings"""
        # Reset to new default indices based on comprehensive property list:
        # 0=Mass, 1=Mass(log), 2=Charge, 3=Spin, 4=Half-Life(log), 5=Mean Lifetime(log),
        # 6=Decay Width, 7=Strangeness, 8=Charm, 9=Bottomness, 10=Isospin(I),
        # 11=Isospin I3, 12=Baryon Number, 13=Lepton Number, 14=Parity, 15=C-Parity,
        # 16=Stability, 17=Quark Count, 18=None

        # 1. Fill Colour -> Mass (log scale)
        self.fill_color_control.property_combo.setCurrentIndex(1)
        # 2. Border Colour -> Electric Charge
        self.border_color_control.property_combo.setCurrentIndex(2)
        # 3. Glow Colour -> Half-Life (log)
        self.glow_color_control.property_combo.setCurrentIndex(4)
        # 4. Inner Ring Colour -> Strangeness
        self.ring_color_control.property_combo.setCurrentIndex(7)
        # 5. Symbol Text Colour -> Isospin I3
        self.symbol_text_color_control.property_combo.setCurrentIndex(11)
        # 6. Size Scaling -> Mass (log scale) - index 1 in size properties
        self.size_scale_control.property_combo.setCurrentIndex(1)

        self.table.update()

    def set_item_selected(self, selected: bool):
        """Enable/disable edit and remove buttons based on selection state"""
        self.edit_btn.setEnabled(selected)
        self.remove_btn.setEnabled(selected)
        self.export_btn.setEnabled(selected)
        self.duplicate_btn.setEnabled(selected)

    def update_item_count(self, count):
        """Update the item count label"""
        self.item_count_label.setText(f"Items: {count}")
