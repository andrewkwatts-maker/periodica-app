"""
Cell Component Control Panel
Control panel for cell component visualization settings including type filtering,
color encoding, size mapping, and component analysis tools.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QComboBox, QSlider, QGroupBox, QPushButton,
                                QCheckBox, QSpinBox, QDoubleSpinBox, QFrame,
                                QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from periodica_app.ui.theme_constants import ThemeColors
from periodica_app.ui.biological_search_widget import BiologicalSearchWidget
from periodica_app.ui.biological_data_management import BiologicalDataManagement
from periodica_app.ui.biological_property_control import BiologicalPropertyControl, CollapsibleBox
from periodica_app.ui.ai_generation_widget import AIGenerationWidget
from periodica.core.cell_component_enums import (OrganelleType, ComponentFunction,
                                        CellularCompartment, CellComponentLayoutMode)


class CellComponentControlPanel(QWidget):
    """Control panel for cell component visualization settings."""

    # Signals
    layout_changed = Signal(str)
    color_property_changed = Signal(str)
    size_property_changed = Signal(str)
    type_filter_changed = Signal(list)
    compartment_filter_changed = Signal(list)
    component_creation_requested = Signal()
    assembly_requested = Signal()
    search_changed = Signal(str)
    # Data management signals
    add_requested = Signal()
    edit_requested = Signal()
    ai_update_requested = Signal()
    remove_requested = Signal()
    export_requested = Signal()
    import_requested = Signal()
    duplicate_requested = Signal()
    reset_requested = Signal()
    create_from_components_requested = Signal()

    # AI generation signals
    ai_generate_requested = Signal()
    ai_settings_requested = Signal()
    auto_generate_requested = Signal()

    # Property encoding signals
    property_changed = Signal(str, str)  # property_key, property_name
    filter_range_changed = Signal(str, float, float)  # property_key, min, max
    gradient_color_changed = Signal(str, object, object)  # property_key, start_color, end_color

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
                background: rgba(38, 166, 154, 150);
                border-radius: 5px;
            }}
        """)

        content = QWidget()
        content.setStyleSheet(f"background: {ThemeColors.BG_DARK};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Title
        title = QLabel("Cell Component Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #26A69A;")
        layout.addWidget(title)

        # === Search Widget ===
        self.search_widget = BiologicalSearchWidget(
            placeholder="Search components by name...",
            accent_color="#26A69A"  # Teal for cell components
        )
        self.search_widget.search_changed.connect(self._on_search_changed)
        layout.addWidget(self.search_widget)

        # === Layout Controls ===
        layout_group = self._create_layout_group()
        layout.addWidget(layout_group)

        # === Visual Property Encodings (CollapsibleBox) ===
        layout.addWidget(self._create_visual_properties_group())

        # === Filter Options (CollapsibleBox) ===
        layout.addWidget(self._create_filter_options_group())

        # === Generation ===
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout as GenVLayout
        gen_group = QGroupBox("Generation")
        gen_layout = GenVLayout(gen_group)
        self.auto_generate_btn = QPushButton("Auto-Generate Components")
        self.auto_generate_btn.setToolTip("Generate cell components from\nprotein and nucleic acid data")
        self.auto_generate_btn.clicked.connect(self.auto_generate_requested.emit)
        gen_layout.addWidget(self.auto_generate_btn)
        self.ai_widget = AIGenerationWidget("cell_component", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        gen_layout.addWidget(self.ai_widget)
        layout.addWidget(gen_group)

        # === Data Management ===
        self.data_mgmt = BiologicalDataManagement(
            title="Component Management",
            accent_color="#26A69A"
        )
        self._connect_data_management_signals()
        layout.addWidget(self.data_mgmt)

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _connect_data_management_signals(self):
        """Connect data management widget signals."""
        self.data_mgmt.add_requested.connect(self.add_requested.emit)
        self.data_mgmt.edit_requested.connect(self.edit_requested.emit)
        self.data_mgmt.ai_update_requested.connect(self.ai_update_requested.emit)
        self.data_mgmt.remove_requested.connect(self.remove_requested.emit)
        self.data_mgmt.export_requested.connect(self.export_requested.emit)
        self.data_mgmt.import_requested.connect(self.import_requested.emit)
        self.data_mgmt.duplicate_requested.connect(self.duplicate_requested.emit)
        self.data_mgmt.reset_requested.connect(self.reset_requested.emit)
        # Note: create_from_components_requested can be connected via the
        # control panel's own signal if an "Assemble from Proteins" action is needed

    def _on_search_changed(self, text):
        """Handle search text change."""
        self.search_changed.emit(text)

    def _create_layout_group(self):
        """Create layout controls group."""
        group = QGroupBox("Layout Mode")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        self.layout_combo = QComboBox()
        self.layout_combo.addItems([
            "Grid",
            "Type",
            "Function",
            "Size",
            "Copy Number"
        ])
        self.layout_combo.setStyleSheet(self._combo_style())
        self.layout_combo.currentTextChanged.connect(
            lambda t: self.layout_changed.emit(t.lower().replace(' ', '_'))
        )
        layout.addWidget(self.layout_combo)

        return group

    def _create_visual_properties_group(self):
        """Create visual property encodings using CollapsibleBox and BiologicalPropertyControl."""
        collapsible = CollapsibleBox("Visual Property Encodings", "#26A69A")

        # Define property options for cell components
        # Color properties: Type, Compartment (as requested)
        color_properties = ["None", "Type", "Compartment", "Function"]
        # Size properties: Mass, Diameter (as requested)
        size_properties = ["None", "Mass", "Diameter", "Copy Number", "Protein Count"]

        # Store property controls for later access
        self.property_controls = {}

        # Fill Colour control (default: Type)
        self.fill_color_control = BiologicalPropertyControl(
            "Fill Colour", "fill_color", color_properties,
            control_type="color", default_index=1,  # Type
            accent_color="#26A69A"
        )
        self.fill_color_control.set_current_index(1)
        self.fill_color_control.property_changed.connect(self._on_property_control_changed)
        self.fill_color_control.filter_changed.connect(self._on_property_filter_changed)
        self.fill_color_control.color_changed.connect(self._on_gradient_color_changed)
        collapsible.add_widget(self.fill_color_control)
        self.property_controls["fill_color"] = self.fill_color_control

        # Border Colour control (default: Compartment)
        self.border_color_control = BiologicalPropertyControl(
            "Border Colour", "border_color", color_properties,
            control_type="color", default_index=2,  # Compartment
            accent_color="#26A69A"
        )
        self.border_color_control.set_current_index(2)
        self.border_color_control.property_changed.connect(self._on_property_control_changed)
        self.border_color_control.filter_changed.connect(self._on_property_filter_changed)
        self.border_color_control.color_changed.connect(self._on_gradient_color_changed)
        collapsible.add_widget(self.border_color_control)
        self.property_controls["border_color"] = self.border_color_control

        # Glow Colour control (default: Function)
        self.glow_color_control = BiologicalPropertyControl(
            "Glow Colour", "glow_color", color_properties,
            control_type="color", default_index=3,  # Function
            accent_color="#26A69A"
        )
        self.glow_color_control.set_current_index(3)
        self.glow_color_control.property_changed.connect(self._on_property_control_changed)
        self.glow_color_control.filter_changed.connect(self._on_property_filter_changed)
        self.glow_color_control.color_changed.connect(self._on_gradient_color_changed)
        collapsible.add_widget(self.glow_color_control)
        self.property_controls["glow_color"] = self.glow_color_control

        # Glow Intensity control (default: Mass)
        self.glow_intensity_control = BiologicalPropertyControl(
            "Glow Intensity", "glow_intensity", size_properties,
            control_type="size", default_index=1,  # Mass
            accent_color="#26A69A"
        )
        self.glow_intensity_control.set_current_index(1)
        self.glow_intensity_control.property_changed.connect(self._on_property_control_changed)
        self.glow_intensity_control.filter_changed.connect(self._on_property_filter_changed)
        collapsible.add_widget(self.glow_intensity_control)
        self.property_controls["glow_intensity"] = self.glow_intensity_control

        # Symbol Text Colour control (default: Type)
        self.symbol_text_color_control = BiologicalPropertyControl(
            "Symbol Text Colour", "symbol_text_color", color_properties,
            control_type="color", default_index=1,  # Type
            accent_color="#26A69A"
        )
        self.symbol_text_color_control.set_current_index(1)
        self.symbol_text_color_control.property_changed.connect(self._on_property_control_changed)
        self.symbol_text_color_control.filter_changed.connect(self._on_property_filter_changed)
        self.symbol_text_color_control.color_changed.connect(self._on_gradient_color_changed)
        collapsible.add_widget(self.symbol_text_color_control)
        self.property_controls["symbol_text_color"] = self.symbol_text_color_control

        # Border Size control (default: Mass)
        self.border_size_control = BiologicalPropertyControl(
            "Border Size", "border_size", size_properties,
            control_type="size", default_index=1,  # Mass
            accent_color="#26A69A"
        )
        self.border_size_control.set_current_index(1)
        self.border_size_control.property_changed.connect(self._on_property_control_changed)
        self.border_size_control.filter_changed.connect(self._on_property_filter_changed)
        collapsible.add_widget(self.border_size_control)
        self.property_controls["border_size"] = self.border_size_control

        # Card Size control (default: Diameter)
        self.card_size_control = BiologicalPropertyControl(
            "Card Size", "card_size", size_properties,
            control_type="size", default_index=2,  # Diameter
            accent_color="#26A69A"
        )
        self.card_size_control.set_current_index(2)
        self.card_size_control.property_changed.connect(self._on_property_control_changed)
        self.card_size_control.filter_changed.connect(self._on_property_filter_changed)
        collapsible.add_widget(self.card_size_control)
        self.property_controls["card_size"] = self.card_size_control

        # Reset button for property mappings
        reset_button = QPushButton("Reset Property Mappings")
        reset_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #26A69A, stop:1 #00897B);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #4DB6AC, stop:1 #26A69A);
            }
        """)
        reset_button.clicked.connect(self._reset_property_mappings)
        collapsible.add_widget(reset_button)

        return collapsible

    def _create_filter_options_group(self):
        """Create filter options using CollapsibleBox."""
        collapsible = CollapsibleBox("Filter Options", "#FF7043")

        # Type filter label
        type_label = QLabel("Component Type:")
        type_label.setStyleSheet("color: white; font-weight: bold;")
        collapsible.add_widget(type_label)

        # Type filter checkboxes container
        type_container = QWidget()
        type_layout = QVBoxLayout(type_container)
        type_layout.setContentsMargins(10, 0, 0, 0)

        self.type_checks = {}
        types = [
            ("Ribosome", "ribosome"),
            ("Mitochondrion", "mitochondrion"),
            ("Nucleus", "nucleus"),
            ("ER", "endoplasmic_reticulum"),
            ("Golgi", "golgi_apparatus"),
            ("Lysosome", "lysosome"),
            ("Proteasome", "proteasome"),
            ("Other", "other")
        ]

        for label, key in types:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(self._get_checkbox_style("#FF7043"))
            cb.stateChanged.connect(self._on_type_filter_changed)
            self.type_checks[key] = cb
            type_layout.addWidget(cb)

        collapsible.add_widget(type_container)

        # Type filter buttons row
        type_btn_row = QWidget()
        type_btn_layout = QHBoxLayout(type_btn_row)
        type_btn_layout.setContentsMargins(10, 5, 5, 10)
        type_btn_layout.setSpacing(5)

        select_all_types_btn = QPushButton("Select All")
        select_all_types_btn.setStyleSheet(self._get_small_button_style())
        select_all_types_btn.clicked.connect(lambda: self._set_all_type_checkboxes(True))
        type_btn_layout.addWidget(select_all_types_btn)

        clear_all_types_btn = QPushButton("Clear All")
        clear_all_types_btn.setStyleSheet(self._get_small_button_style())
        clear_all_types_btn.clicked.connect(lambda: self._set_all_type_checkboxes(False))
        type_btn_layout.addWidget(clear_all_types_btn)

        type_btn_layout.addStretch()
        collapsible.add_widget(type_btn_row)

        # Compartment filter label
        compartment_label = QLabel("Compartment:")
        compartment_label.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")
        collapsible.add_widget(compartment_label)

        # Compartment filter checkboxes container
        compartment_container = QWidget()
        compartment_layout = QVBoxLayout(compartment_container)
        compartment_layout.setContentsMargins(10, 0, 0, 0)

        self.compartment_checks = {}
        compartments = [
            ("Cytoplasm", "cytoplasm"),
            ("Nucleus", "nucleus"),
            ("Mitochondria", "mitochondria"),
            ("ER Lumen", "er_lumen"),
            ("Membrane", "plasma_membrane"),
        ]

        for label, key in compartments:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(self._get_checkbox_style("#FF7043"))
            cb.stateChanged.connect(self._on_compartment_filter_changed)
            self.compartment_checks[key] = cb
            compartment_layout.addWidget(cb)

        collapsible.add_widget(compartment_container)

        # Compartment filter buttons row
        compartment_btn_row = QWidget()
        compartment_btn_layout = QHBoxLayout(compartment_btn_row)
        compartment_btn_layout.setContentsMargins(10, 5, 5, 5)
        compartment_btn_layout.setSpacing(5)

        select_all_compartments_btn = QPushButton("Select All")
        select_all_compartments_btn.setStyleSheet(self._get_small_button_style())
        select_all_compartments_btn.clicked.connect(lambda: self._set_all_compartment_checkboxes(True))
        compartment_btn_layout.addWidget(select_all_compartments_btn)

        clear_all_compartments_btn = QPushButton("Clear All")
        clear_all_compartments_btn.setStyleSheet(self._get_small_button_style())
        clear_all_compartments_btn.clicked.connect(lambda: self._set_all_compartment_checkboxes(False))
        compartment_btn_layout.addWidget(clear_all_compartments_btn)

        compartment_btn_layout.addStretch()
        collapsible.add_widget(compartment_btn_row)

        # Clear all filters button
        clear_btn = QPushButton("Clear All Filters")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 112, 67, 150);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 112, 67, 200);
            }
        """)
        clear_btn.clicked.connect(self._on_clear_all_filters)
        collapsible.add_widget(clear_btn)

        return collapsible


    def _on_property_control_changed(self, property_key: str, index: int):
        """Handle property selection change from BiologicalPropertyControl."""
        control = self.property_controls.get(property_key)
        if control:
            prop_name = control.get_current_property()
            # Emit the property changed signal
            self.property_changed.emit(property_key, prop_name)

            # Update table if it supports visual property changes
            if self.table and hasattr(self.table, 'set_visual_property'):
                self.table.set_visual_property(property_key, prop_name)
                self.table.update()

            # Also emit the legacy color/size signals for backward compatibility
            if control.control_type == "color":
                prop_map = {"Type": "type", "Function": "function", "Compartment": "compartment", "None": "none"}
                self.color_property_changed.emit(prop_map.get(prop_name, prop_name.lower()))
            else:
                prop_map = {"None": "none", "Mass": "mass", "Diameter": "diameter",
                           "Copy Number": "copy_number", "Protein Count": "protein_count"}
                self.size_property_changed.emit(prop_map.get(prop_name, prop_name.lower()))

    def _on_property_filter_changed(self, property_key: str, min_val: float, max_val: float):
        """Handle filter range change from BiologicalPropertyControl."""
        self.filter_range_changed.emit(property_key, min_val, max_val)
        if self.table and hasattr(self.table, 'set_property_filter'):
            self.table.set_property_filter(property_key, min_val, max_val)
            self.table.update()

    def _on_gradient_color_changed(self, property_key: str, start_color, end_color):
        """Handle gradient color change from BiologicalPropertyControl."""
        self.gradient_color_changed.emit(property_key, start_color, end_color)
        if self.table and hasattr(self.table, 'set_gradient_colors'):
            self.table.set_gradient_colors(property_key, start_color, end_color)
            self.table.update()

    def _reset_property_mappings(self):
        """Reset all property controls to their default values."""
        for control in self.property_controls.values():
            control.reset_to_default()
        if self.table:
            self.table.update()

    def _on_type_filter_changed(self):
        """Handle type filter checkbox changes."""
        active = [k for k, cb in self.type_checks.items() if cb.isChecked()]
        self.type_filter_changed.emit(active)
        if self.table and hasattr(self.table, 'set_type_filters'):
            self.table.set_type_filters(active)

    def _on_compartment_filter_changed(self):
        """Handle compartment filter checkbox changes."""
        active = [k for k, cb in self.compartment_checks.items() if cb.isChecked()]
        self.compartment_filter_changed.emit(active)
        if self.table and hasattr(self.table, 'set_compartment_filters'):
            self.table.set_compartment_filters(active)

    def _set_all_type_checkboxes(self, checked: bool):
        """Set all type filter checkboxes to the specified state."""
        for cb in self.type_checks.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._on_type_filter_changed()

    def _set_all_compartment_checkboxes(self, checked: bool):
        """Set all compartment filter checkboxes to the specified state."""
        for cb in self.compartment_checks.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._on_compartment_filter_changed()

    def _on_clear_all_filters(self):
        """Clear all filters (select all types and compartments)."""
        self._set_all_type_checkboxes(True)
        self._set_all_compartment_checkboxes(True)

    # === Style Methods ===

    def _group_style(self):
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

    def _combo_style(self):
        return f"""
            QComboBox {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 5px 10px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {ThemeColors.ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background: {ThemeColors.BG_DARK};
                color: {ThemeColors.TEXT_PRIMARY};
                selection-background-color: {ThemeColors.ACCENT};
            }}
        """

    def _button_style(self):
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
            QPushButton:pressed {{
                background: {ThemeColors.ACCENT_DARK};
            }}
        """

    def _get_checkbox_style(self, color):
        """Get stylesheet for filter checkboxes."""
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

    def _get_small_button_style(self):
        """Get stylesheet for small utility buttons."""
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

    # === Public API ===

    def set_component_count(self, current: int, total: int = None):
        """Update component count display.

        Args:
            current: Number of currently visible/filtered items
            total: Total number of items (defaults to current if not provided)
        """
        if total is None:
            total = current
        self.data_mgmt.update_item_count(current, total)

    def set_item_selected(self, selected: bool):
        """Enable/disable edit, remove, export, duplicate buttons."""
        self.data_mgmt.set_item_selected(selected)

    def set_search_results(self, showing: int, total: int):
        """Update search results count."""
        self.search_widget.set_results_count(showing, total)

    def get_active_type_filters(self):
        """Get list of active type filters."""
        return [k for k, cb in self.type_checks.items() if cb.isChecked()]

    def get_active_compartment_filters(self):
        """Get list of active compartment filters."""
        return [k for k, cb in self.compartment_checks.items() if cb.isChecked()]

    def refresh_ai_status(self):
        """Refresh the AI API configuration status."""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()
