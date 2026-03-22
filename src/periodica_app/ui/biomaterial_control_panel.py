"""
Biomaterial Control Panel
Control panel for biological material visualization settings including type filtering,
color encoding, mechanical property analysis, and composition tools.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QComboBox, QGroupBox, QPushButton, QCheckBox,
                                QScrollArea, QGridLayout, QRadioButton)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from periodica_app.ui.theme_constants import ThemeColors
from periodica_app.ui.biological_property_control import BiologicalPropertyControl, CollapsibleBox
from periodica_app.ui.biological_data_management import BiologicalDataManagement
from periodica_app.ui.biological_search_widget import BiologicalSearchWidget
from periodica_app.ui.ai_generation_widget import AIGenerationWidget
from periodica.core.biomaterial_enums import BiomaterialType


class BiomaterialControlPanel(QWidget):
    """Control panel for biomaterial visualization settings."""

    # Visualization signals
    layout_changed = Signal(str)
    color_property_changed = Signal(str)
    size_property_changed = Signal(str)
    type_filter_changed = Signal(list)
    search_changed = Signal(str)
    filter_range_changed = Signal(str, float, float)

    # Data management signals
    add_requested = Signal()
    edit_requested = Signal()
    ai_update_requested = Signal()
    remove_requested = Signal()
    export_requested = Signal()
    import_requested = Signal()
    duplicate_requested = Signal()
    reset_requested = Signal()
    material_creation_requested = Signal()
    composition_analysis_requested = Signal()

    # AI generation signals
    ai_generate_requested = Signal()
    ai_settings_requested = Signal()
    # Auto-generation signal
    auto_generate_requested = Signal()

    def __init__(self, table_widget=None, parent=None):
        super().__init__(parent)
        self.table = table_widget
        self._setup_ui()

    def _setup_ui(self):
        """Set up the control panel UI."""
        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {ThemeColors.BG_DARK}; }}
            QScrollBar:vertical {{
                background: rgba(40, 40, 60, 100);
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(102, 187, 106, 150);
                border-radius: 5px;
            }}
        """)

        content = QWidget()
        content.setStyleSheet(f"background: {ThemeColors.BG_DARK};")
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Title
        title = QLabel("Biomaterial Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ThemeColors.ACCENT};")
        main_layout.addWidget(title)

        # Search widget
        self.search_widget = BiologicalSearchWidget(
            placeholder="Search biomaterials...",
            accent_color=ThemeColors.ACCENT
        )
        self.search_widget.search_changed.connect(self._on_search_changed)
        main_layout.addWidget(self.search_widget)

        # Layout mode selection
        main_layout.addWidget(self._create_layout_mode_group())

        # Visual property encodings (collapsible)
        main_layout.addWidget(self._create_visual_properties_group())

        # Filter options (collapsible)
        main_layout.addWidget(self._create_filter_options_group())

        # Generation
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout as GenVLayout
        gen_group = QGroupBox("Generation")
        gen_layout = GenVLayout(gen_group)
        self.auto_generate_btn = QPushButton("Auto-Generate Biomaterials")
        self.auto_generate_btn.setToolTip("Generate biomaterial data from\nECM composition and porosity models")
        self.auto_generate_btn.clicked.connect(self.auto_generate_requested.emit)
        gen_layout.addWidget(self.auto_generate_btn)
        self.ai_widget = AIGenerationWidget("biomaterial", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        gen_layout.addWidget(self.ai_widget)
        main_layout.addWidget(gen_group)

        # Data management
        self.data_management = BiologicalDataManagement(
            title="Data Management",
            accent_color=ThemeColors.ACCENT,
        )
        self._connect_data_management_signals()
        main_layout.addWidget(self.data_management)

        main_layout.addStretch()

        scroll.setWidget(content)

        # Set up main layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _create_layout_mode_group(self):
        """Create layout mode selection group."""
        group = QGroupBox("Layout Mode")
        group.setStyleSheet(self._get_group_style(ThemeColors.ACCENT))
        layout = QVBoxLayout(group)

        self.grid_radio = QRadioButton("Grid (Alphabetical)")
        self.type_radio = QRadioButton("By Type")
        self.stiffness_radio = QRadioButton("By Stiffness")
        self.density_radio = QRadioButton("By Density")
        self.organ_radio = QRadioButton("By Organ System")

        self.grid_radio.setChecked(True)

        radio_style = self._get_radio_style()
        for radio in [self.grid_radio, self.type_radio, self.stiffness_radio,
                      self.density_radio, self.organ_radio]:
            radio.setStyleSheet(radio_style)
            layout.addWidget(radio)

        self.grid_radio.toggled.connect(lambda: self._on_layout_changed("grid") if self.grid_radio.isChecked() else None)
        self.type_radio.toggled.connect(lambda: self._on_layout_changed("type") if self.type_radio.isChecked() else None)
        self.stiffness_radio.toggled.connect(lambda: self._on_layout_changed("stiffness") if self.stiffness_radio.isChecked() else None)
        self.density_radio.toggled.connect(lambda: self._on_layout_changed("density") if self.density_radio.isChecked() else None)
        self.organ_radio.toggled.connect(lambda: self._on_layout_changed("organ_system") if self.organ_radio.isChecked() else None)

        return group

    def _create_visual_properties_group(self):
        """Create visual property encodings with expandable controls."""
        collapsible = CollapsibleBox("Visual Property Encodings", ThemeColors.ACCENT)

        # Property metadata for sliders
        property_metadata = {
            "None": {"min": 0, "max": 100, "unit": ""},
            "Type": {"min": 0, "max": 10, "unit": ""},
            "Stiffness": {"min": 0.001, "max": 20000, "unit": "MPa"},
            "Organ System": {"min": 0, "max": 10, "unit": ""},
            "Density": {"min": 0.9, "max": 3.2, "unit": "g/cm3"},
            "Porosity": {"min": 0, "max": 100, "unit": "%"},
            "Water Content": {"min": 0, "max": 100, "unit": "%"},
            "Young's Modulus": {"min": 0.001, "max": 20000, "unit": "MPa"},
        }

        color_properties = ["None", "Type", "Stiffness", "Organ System", "Density", "Porosity"]
        size_properties = ["None", "Stiffness", "Density", "Porosity", "Water Content"]

        # Fill Color control
        self.fill_color_control = BiologicalPropertyControl(
            "Fill Color", "fill_color", color_properties,
            property_metadata=property_metadata,
            control_type="color", default_index=1,
            accent_color=ThemeColors.ACCENT
        )
        self.fill_color_control.property_combo.setCurrentIndex(1)  # Type
        self.fill_color_control.property_changed.connect(self._on_property_control_changed)
        self.fill_color_control.filter_changed.connect(self._on_filter_range_changed)
        collapsible.content_layout.addWidget(self.fill_color_control)

        # Border Color control
        self.border_color_control = BiologicalPropertyControl(
            "Border Color", "border_color", color_properties,
            property_metadata=property_metadata,
            control_type="color", default_index=2,
            accent_color=ThemeColors.ACCENT
        )
        self.border_color_control.property_combo.setCurrentIndex(2)  # Stiffness
        self.border_color_control.property_changed.connect(self._on_property_control_changed)
        collapsible.content_layout.addWidget(self.border_color_control)

        # Card Size control
        self.card_size_control = BiologicalPropertyControl(
            "Card Size", "card_size", size_properties,
            property_metadata=property_metadata,
            control_type="size", default_index=1,
            accent_color=ThemeColors.ACCENT
        )
        self.card_size_control.property_combo.setCurrentIndex(1)  # Stiffness
        self.card_size_control.property_changed.connect(self._on_property_control_changed)
        collapsible.content_layout.addWidget(self.card_size_control)

        # Reset button
        reset_btn = QPushButton("Reset Property Mappings")
        reset_btn.setStyleSheet(self._get_accent_button_style())
        reset_btn.clicked.connect(self._reset_property_mappings)
        collapsible.content_layout.addWidget(reset_btn)

        # Expand by default
        collapsible.set_expanded(True)

        return collapsible

    def _create_filter_options_group(self):
        """Create filter options with tissue type checkboxes."""
        collapsible = CollapsibleBox("Filter Options", "#607D8B")

        # Tissue Type Filter
        type_label = QLabel("Tissue Type:")
        type_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 5px;")
        collapsible.content_layout.addWidget(type_label)

        type_grid = QWidget()
        type_layout = QGridLayout(type_grid)
        type_layout.setContentsMargins(10, 5, 5, 10)
        type_layout.setSpacing(5)

        self.type_checkboxes = {}
        types = [
            ("Bone", "bone", "#FFF8E1"),
            ("Cartilage", "cartilage", "#E3F2FD"),
            ("Muscle", "muscle", "#FFEBEE"),
            ("Tendon", "tendon", "#F3E5F5"),
            ("Ligament", "ligament", "#E8F5E9"),
            ("Nervous", "brain,nerve", "#FFF3E0"),
            ("Organ", "liver,lung,kidney", "#EFEBE9"),
            ("Skin", "skin", "#FFCCBC"),
            ("Adipose", "adipose", "#FCE4EC"),
            ("Blood", "blood", "#FCE4EC"),
        ]

        for i, (label, keys, color) in enumerate(types):
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(self._get_checkbox_style(color))
            cb.stateChanged.connect(self._on_type_filter_changed)
            self.type_checkboxes[keys] = cb
            type_layout.addWidget(cb, i // 2, i % 2)

        collapsible.content_layout.addWidget(type_grid)

        # Select All / Clear All buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(10, 0, 5, 10)
        btn_layout.setSpacing(5)

        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet(self._get_small_button_style())
        select_all_btn.clicked.connect(lambda: self._set_all_type_checkboxes(True))
        btn_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setStyleSheet(self._get_small_button_style())
        clear_all_btn.clicked.connect(lambda: self._set_all_type_checkboxes(False))
        btn_layout.addWidget(clear_all_btn)

        btn_layout.addStretch()
        collapsible.content_layout.addWidget(btn_row)

        # Stiffness Category Filter
        stiff_label = QLabel("Stiffness Category:")
        stiff_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 5px;")
        collapsible.content_layout.addWidget(stiff_label)

        stiff_grid = QWidget()
        stiff_layout = QHBoxLayout(stiff_grid)
        stiff_layout.setContentsMargins(10, 5, 5, 10)
        stiff_layout.setSpacing(10)

        self.stiffness_checkboxes = {}
        categories = [
            ("Ultra-soft", "#4CAF50"),
            ("Soft", "#8BC34A"),
            ("Intermediate", "#FF9800"),
            ("Stiff", "#F44336"),
            ("Hard", "#9C27B0"),
        ]

        for cat, color in categories:
            cb = QCheckBox(cat)
            cb.setChecked(True)
            cb.setStyleSheet(self._get_checkbox_style(color))
            cb.stateChanged.connect(self._on_stiffness_filter_changed)
            self.stiffness_checkboxes[cat] = cb
            stiff_layout.addWidget(cb)

        collapsible.content_layout.addWidget(stiff_grid)

        # Clear filters button
        clear_btn = QPushButton("Clear All Filters")
        clear_btn.setStyleSheet(self._get_warning_button_style())
        clear_btn.clicked.connect(self._on_clear_filters)
        collapsible.content_layout.addWidget(clear_btn)

        return collapsible

    def _connect_data_management_signals(self):
        """Connect data management widget signals."""
        self.data_management.add_requested.connect(self.add_requested.emit)
        self.data_management.edit_requested.connect(self.edit_requested.emit)
        self.data_management.ai_update_requested.connect(self.ai_update_requested.emit)
        self.data_management.remove_requested.connect(self.remove_requested.emit)
        self.data_management.export_requested.connect(self.export_requested.emit)
        self.data_management.import_requested.connect(self.import_requested.emit)
        self.data_management.duplicate_requested.connect(self.duplicate_requested.emit)
        self.data_management.reset_requested.connect(self.reset_requested.emit)
        self.data_management.create_from_components_requested.connect(
            self.material_creation_requested.emit)

    # Event handlers
    def _on_layout_changed(self, mode):
        """Handle layout mode change."""
        self.layout_changed.emit(mode)
        if self.table:
            self.table.set_layout_mode(mode)

    def _on_search_changed(self, text):
        """Handle search text change."""
        self.search_changed.emit(text)
        if self.table and hasattr(self.table, 'set_search_filter'):
            self.table.set_search_filter(text)

    def _on_property_control_changed(self, property_key, index):
        """Handle property control change."""
        control = getattr(self, f"{property_key}_control", None)
        if control:
            prop_name = control.get_current_property().lower().replace(' ', '_')
            if property_key == "fill_color":
                self.color_property_changed.emit(prop_name)
                if self.table:
                    self.table.set_color_property(prop_name)
            elif property_key == "card_size":
                self.size_property_changed.emit(prop_name)
                if self.table:
                    self.table.set_size_property(prop_name)

    def _on_filter_range_changed(self, property_key, min_val, max_val):
        """Handle filter range change."""
        self.filter_range_changed.emit(property_key, min_val, max_val)
        if self.table and hasattr(self.table, 'set_property_filter'):
            self.table.set_property_filter(property_key, min_val, max_val)

    def _on_type_filter_changed(self):
        """Handle type filter checkbox change."""
        active_types = []
        for keys, cb in self.type_checkboxes.items():
            if cb.isChecked():
                active_types.extend(keys.split(','))
        self.type_filter_changed.emit(active_types)
        if self.table:
            self.table.set_type_filters(active_types)

    def _on_stiffness_filter_changed(self):
        """Handle stiffness filter checkbox change."""
        active = [cat for cat, cb in self.stiffness_checkboxes.items() if cb.isChecked()]
        if self.table and hasattr(self.table, 'set_stiffness_filters'):
            self.table.set_stiffness_filters(active)

    def _set_all_type_checkboxes(self, checked):
        """Set all type checkboxes to checked/unchecked."""
        for cb in self.type_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._on_type_filter_changed()

    def _on_clear_filters(self):
        """Clear all filters."""
        for cb in self.type_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
        for cb in self.stiffness_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
        self._on_type_filter_changed()
        self._on_stiffness_filter_changed()

    def _reset_property_mappings(self):
        """Reset all property controls to defaults."""
        self.fill_color_control.set_current_index(1)  # Type
        self.border_color_control.set_current_index(2)  # Stiffness
        self.card_size_control.set_current_index(1)  # Stiffness

    # Style methods
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
        return f"""
            QRadioButton {{
                color: white;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {ThemeColors.ACCENT};
                border-radius: 8px;
                background: rgba(40, 40, 60, 200);
            }}
            QRadioButton::indicator:checked {{
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5, stop:0 {ThemeColors.ACCENT}, stop:1 rgba(102, 187, 106, 100));
            }}
        """

    def _get_checkbox_style(self, color):
        return f"""
            QCheckBox {{
                color: white;
                spacing: 5px;
                font-size: 10px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid {color};
                border-radius: 3px;
                background: rgba(40, 40, 60, 200);
            }}
            QCheckBox::indicator:checked {{
                background: {color};
            }}
        """

    def _get_small_button_style(self):
        return """
            QPushButton {
                background: rgba(100, 100, 120, 150);
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: rgba(120, 120, 140, 180);
            }
        """

    def _get_accent_button_style(self):
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {ThemeColors.ACCENT}, stop:1 #4CAF50);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4CAF50, stop:1 {ThemeColors.ACCENT});
            }}
        """

    def _get_warning_button_style(self):
        return """
            QPushButton {
                background: rgba(255, 87, 34, 180);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 87, 34, 220);
            }
        """

    # Public API
    def set_material_count(self, count):
        """Update material count display."""
        self.data_management.update_item_count(count, count)

    def set_item_selected(self, selected: bool):
        """Enable/disable edit and remove buttons based on selection."""
        self.data_management.set_item_selected(selected)

    def get_active_type_filters(self):
        """Get list of active type filters."""
        active = []
        for keys, cb in self.type_checkboxes.items():
            if cb.isChecked():
                active.extend(keys.split(','))
        return active

    def update_search_results(self, showing: int, total: int):
        """Update search results count."""
        self.search_widget.set_results_count(showing, total)

    def refresh_ai_status(self):
        """Refresh the AI API configuration status."""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()
