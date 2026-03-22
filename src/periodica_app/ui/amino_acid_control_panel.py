"""
Amino Acid Control Panel
Provides UI controls for amino acid visualization settings.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                                QScrollArea, QRadioButton, QComboBox, QCheckBox,
                                QPushButton, QSlider, QDoubleSpinBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from periodica.core.amino_acid_enums import (AminoAcidLayoutMode, AminoAcidCategory,
                                    AminoAcidPolarity, AminoAcidProperty,
                                    AMINO_ACID_PROPERTY_METADATA)
from periodica_app.ui.biological_search_widget import BiologicalSearchWidget
from periodica_app.ui.biological_data_management import BiologicalDataManagement
from periodica_app.ui.biological_property_control import BiologicalPropertyControl, CollapsibleBox
from periodica_app.ui.ai_generation_widget import AIGenerationWidget


class AminoAcidControlPanel(QWidget):
    """Control panel for amino acid visualization settings"""

    # Layout and filter signals
    layout_changed = Signal(str)
    category_filter_changed = Signal(list)
    polarity_filter_changed = Signal(list)
    charge_filter_changed = Signal(float, float)
    hydropathy_filter_changed = Signal(float, float)

    # pH control signal
    pH_changed = Signal(float)

    # Property mapping signals
    color_property_changed = Signal(str, str)
    size_property_changed = Signal(str, str)

    # Search signal
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

    # AI generation signals
    ai_generate_requested = Signal()
    ai_settings_requested = Signal()
    auto_generate_requested = Signal()

    def __init__(self, table_widget=None):
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

        title = QLabel("Amino Acid Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #66bb6a;")
        layout.addWidget(title)

        # Search widget
        self.search_widget = BiologicalSearchWidget(
            placeholder="Search amino acids...",
            accent_color="#66bb6a"
        )
        self.search_widget.search_changed.connect(self._on_search_changed)
        layout.addWidget(self.search_widget)

        # Layout Mode Selection
        layout.addWidget(self._create_layout_mode_group())

        # pH Control
        layout.addWidget(self._create_pH_control_group())

        # Visual Property Encodings
        layout.addWidget(self._create_visual_properties_group())

        # Filter Options
        layout.addWidget(self._create_filter_options_group())

        # Generation
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout as GenVLayout
        gen_group = QGroupBox("Generation")
        gen_layout = GenVLayout(gen_group)
        self.auto_generate_btn = QPushButton("Auto-Generate Amino Acids")
        self.auto_generate_btn.setToolTip("Generate the 20 standard amino acids\nwith properties derived from atomic composition")
        self.auto_generate_btn.clicked.connect(self.auto_generate_requested.emit)
        gen_layout.addWidget(self.auto_generate_btn)
        self.ai_widget = AIGenerationWidget("amino_acid", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        gen_layout.addWidget(self.ai_widget)
        layout.addWidget(gen_group)

        # Data Management
        layout.addWidget(self._create_data_management_group())

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_layout_mode_group(self):
        """Create layout mode selection group"""
        group = QGroupBox("Layout Mode")
        group.setStyleSheet(self._get_group_style("#66bb6a"))
        layout = QVBoxLayout()

        self.grid_radio = QRadioButton("Grid View")
        self.hydropathy_radio = QRadioButton("By Hydropathy")
        self.charge_radio = QRadioButton("By Charge")
        self.polarity_radio = QRadioButton("By Polarity")
        self.category_radio = QRadioButton("By Category")
        self.mass_radio = QRadioButton("By Mass")
        self.pi_radio = QRadioButton("By Isoelectric Point")
        self.structure_radio = QRadioButton("By Structure Propensity")

        self.grid_radio.setChecked(True)

        radio_style = self._get_radio_style("#66bb6a")
        all_radios = [
            self.grid_radio, self.hydropathy_radio, self.charge_radio,
            self.polarity_radio, self.category_radio, self.mass_radio,
            self.pi_radio, self.structure_radio
        ]

        for radio in all_radios:
            radio.setStyleSheet(radio_style)
            layout.addWidget(radio)

        # Connect signals
        self.grid_radio.toggled.connect(lambda: self._on_layout_changed("grid") if self.grid_radio.isChecked() else None)
        self.hydropathy_radio.toggled.connect(lambda: self._on_layout_changed("hydropathy") if self.hydropathy_radio.isChecked() else None)
        self.charge_radio.toggled.connect(lambda: self._on_layout_changed("charge") if self.charge_radio.isChecked() else None)
        self.polarity_radio.toggled.connect(lambda: self._on_layout_changed("polarity") if self.polarity_radio.isChecked() else None)
        self.category_radio.toggled.connect(lambda: self._on_layout_changed("category") if self.category_radio.isChecked() else None)
        self.mass_radio.toggled.connect(lambda: self._on_layout_changed("mass") if self.mass_radio.isChecked() else None)
        self.pi_radio.toggled.connect(lambda: self._on_layout_changed("pi_order") if self.pi_radio.isChecked() else None)
        self.structure_radio.toggled.connect(lambda: self._on_layout_changed("structure") if self.structure_radio.isChecked() else None)

        group.setLayout(layout)
        return group

    def _create_pH_control_group(self):
        """Create pH control for charge calculations"""
        group = QGroupBox("pH Control")
        group.setStyleSheet(self._get_group_style("#42a5f5"))
        layout = QVBoxLayout()

        # pH explanation
        info_label = QLabel("Adjust pH to see amino acid charges\n(Henderson-Hasselbalch calculation)")
        info_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # pH slider with value display
        ph_layout = QHBoxLayout()
        ph_label = QLabel("pH:")
        ph_label.setStyleSheet("color: white; font-weight: bold;")
        ph_layout.addWidget(ph_label)

        self.pH_spinbox = QDoubleSpinBox()
        self.pH_spinbox.setRange(0.0, 14.0)
        self.pH_spinbox.setValue(7.0)
        self.pH_spinbox.setSingleStep(0.1)
        self.pH_spinbox.setDecimals(1)
        self.pH_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid #42a5f5;
                padding: 5px;
                border-radius: 4px;
            }
        """)
        self.pH_spinbox.valueChanged.connect(self._on_pH_changed)
        ph_layout.addWidget(self.pH_spinbox)

        layout.addLayout(ph_layout)

        # pH slider
        self.pH_slider = QSlider(Qt.Orientation.Horizontal)
        self.pH_slider.setMinimum(0)
        self.pH_slider.setMaximum(140)
        self.pH_slider.setValue(70)
        self.pH_slider.setStyleSheet(self._get_slider_style("#42a5f5"))
        self.pH_slider.valueChanged.connect(lambda v: self.pH_spinbox.setValue(v / 10.0))
        layout.addWidget(self.pH_slider)

        # Preset pH values
        preset_layout = QHBoxLayout()
        for label, value in [("Acidic (2)", 2.0), ("Neutral (7)", 7.0), ("Basic (10)", 10.0)]:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(66, 165, 245, 100);
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 9px;
                }
                QPushButton:hover {
                    background: rgba(66, 165, 245, 180);
                }
            """)
            btn.clicked.connect(lambda checked, v=value: self.pH_spinbox.setValue(v))
            preset_layout.addWidget(btn)
        layout.addLayout(preset_layout)

        group.setLayout(layout)
        return group

    def _create_visual_properties_group(self):
        """Create visual property encodings using CollapsibleBox and BiologicalPropertyControl"""
        collapsible = CollapsibleBox("Visual Property Encodings", "#ab47bc")

        # Define property options for amino acids
        color_properties = ["None", "Category", "Hydropathy", "Charge", "pI", "MW"]
        size_properties = ["None", "MW", "Hydropathy", "Charge", "pI"]

        # Store property controls for later access
        self.property_controls = {}

        # Fill Colour control (default: Category)
        self.fill_color_control = BiologicalPropertyControl(
            "Fill Colour", "fill_color", color_properties,
            control_type="color", default_index=1,  # Category
            accent_color="#ab47bc"
        )
        self.fill_color_control.set_current_index(1)
        self.fill_color_control.property_changed.connect(self._on_property_control_changed)
        self.fill_color_control.filter_changed.connect(self._on_property_filter_changed)
        self.fill_color_control.color_changed.connect(self._on_gradient_color_changed)
        collapsible.add_widget(self.fill_color_control)
        self.property_controls["fill_color"] = self.fill_color_control

        # Border Colour control (default: Hydropathy)
        self.border_color_control = BiologicalPropertyControl(
            "Border Colour", "border_color", color_properties,
            control_type="color", default_index=2,  # Hydropathy
            accent_color="#ab47bc"
        )
        self.border_color_control.set_current_index(2)
        self.border_color_control.property_changed.connect(self._on_property_control_changed)
        self.border_color_control.filter_changed.connect(self._on_property_filter_changed)
        self.border_color_control.color_changed.connect(self._on_gradient_color_changed)
        collapsible.add_widget(self.border_color_control)
        self.property_controls["border_color"] = self.border_color_control

        # Glow Colour control (default: Charge)
        self.glow_color_control = BiologicalPropertyControl(
            "Glow Colour", "glow_color", color_properties,
            control_type="color", default_index=3,  # Charge
            accent_color="#ab47bc"
        )
        self.glow_color_control.set_current_index(3)
        self.glow_color_control.property_changed.connect(self._on_property_control_changed)
        self.glow_color_control.filter_changed.connect(self._on_property_filter_changed)
        self.glow_color_control.color_changed.connect(self._on_gradient_color_changed)
        collapsible.add_widget(self.glow_color_control)
        self.property_controls["glow_color"] = self.glow_color_control

        # Glow Intensity control (default: pI)
        self.glow_intensity_control = BiologicalPropertyControl(
            "Glow Intensity", "glow_intensity", size_properties,
            control_type="size", default_index=4,  # pI
            accent_color="#ab47bc"
        )
        self.glow_intensity_control.set_current_index(4)
        self.glow_intensity_control.property_changed.connect(self._on_property_control_changed)
        self.glow_intensity_control.filter_changed.connect(self._on_property_filter_changed)
        collapsible.add_widget(self.glow_intensity_control)
        self.property_controls["glow_intensity"] = self.glow_intensity_control

        # Symbol Text Colour control (default: pI)
        self.symbol_text_color_control = BiologicalPropertyControl(
            "Symbol Text Colour", "symbol_text_color", color_properties,
            control_type="color", default_index=4,  # pI
            accent_color="#ab47bc"
        )
        self.symbol_text_color_control.set_current_index(4)
        self.symbol_text_color_control.property_changed.connect(self._on_property_control_changed)
        self.symbol_text_color_control.filter_changed.connect(self._on_property_filter_changed)
        self.symbol_text_color_control.color_changed.connect(self._on_gradient_color_changed)
        collapsible.add_widget(self.symbol_text_color_control)
        self.property_controls["symbol_text_color"] = self.symbol_text_color_control

        # Border Size control (default: MW)
        self.border_size_control = BiologicalPropertyControl(
            "Border Size", "border_size", size_properties,
            control_type="size", default_index=1,  # MW
            accent_color="#ab47bc"
        )
        self.border_size_control.set_current_index(1)
        self.border_size_control.property_changed.connect(self._on_property_control_changed)
        self.border_size_control.filter_changed.connect(self._on_property_filter_changed)
        collapsible.add_widget(self.border_size_control)
        self.property_controls["border_size"] = self.border_size_control

        # Card Size control (default: Hydropathy)
        self.card_size_control = BiologicalPropertyControl(
            "Card Size", "card_size", size_properties,
            control_type="size", default_index=2,  # Hydropathy
            accent_color="#ab47bc"
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
                                           stop:0 #ab47bc, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #c158dc, stop:1 #ab47bc);
            }
        """)
        reset_button.clicked.connect(self._reset_property_mappings)
        collapsible.add_widget(reset_button)

        return collapsible

    def _create_filter_options_group(self):
        """Create filter options using CollapsibleBox"""
        collapsible = CollapsibleBox("Filter Options", "#ff7043")

        # Category filter label
        category_label = QLabel("Category:")
        category_label.setStyleSheet("color: white; font-weight: bold;")
        collapsible.add_widget(category_label)

        # Category checkboxes container
        category_container = QWidget()
        cat_layout = QVBoxLayout(category_container)
        cat_layout.setContentsMargins(10, 0, 0, 0)

        self.nonpolar_check = QCheckBox("Nonpolar (Aliphatic)")
        self.aromatic_check = QCheckBox("Nonpolar (Aromatic)")
        self.polar_check = QCheckBox("Polar Uncharged")
        self.basic_check = QCheckBox("Basic (Positive)")
        self.acidic_check = QCheckBox("Acidic (Negative)")
        self.special_check = QCheckBox("Special (G, P, C)")

        category_checks = [self.nonpolar_check, self.aromatic_check, self.polar_check,
                           self.basic_check, self.acidic_check, self.special_check]

        for check in category_checks:
            check.setChecked(True)
            check.setStyleSheet(self._get_checkbox_style("#ff7043"))
            check.stateChanged.connect(self._on_category_filter_changed)
            cat_layout.addWidget(check)

        collapsible.add_widget(category_container)

        # Select All / Clear All buttons row
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(10, 5, 5, 5)
        btn_layout.setSpacing(5)

        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet(self._get_small_button_style())
        select_all_btn.clicked.connect(lambda: self._set_all_category_checkboxes(True))
        btn_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setStyleSheet(self._get_small_button_style())
        clear_all_btn.clicked.connect(lambda: self._set_all_category_checkboxes(False))
        btn_layout.addWidget(clear_all_btn)

        btn_layout.addStretch()
        collapsible.add_widget(btn_row)

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
        clear_btn.clicked.connect(self._on_clear_filters)
        collapsible.add_widget(clear_btn)

        return collapsible

    def _create_data_management_group(self):
        """Create data management controls using shared widget"""
        self.data_management = BiologicalDataManagement(
            title="Data Management",
            accent_color="#66bb6a"
        )

        # Connect signals
        self.data_management.add_requested.connect(self.add_requested.emit)
        self.data_management.edit_requested.connect(self.edit_requested.emit)
        self.data_management.ai_update_requested.connect(self.ai_update_requested.emit)
        self.data_management.remove_requested.connect(self.remove_requested.emit)
        self.data_management.export_requested.connect(self.export_requested.emit)
        self.data_management.import_requested.connect(self.import_requested.emit)
        self.data_management.duplicate_requested.connect(self.duplicate_requested.emit)
        self.data_management.reset_requested.connect(self.reset_requested.emit)

        return self.data_management

    # === Event Handlers ===

    def _on_search_changed(self, text):
        """Handle search text change"""
        self.search_changed.emit(text)
        if self.table and hasattr(self.table, 'set_search_filter'):
            self.table.set_search_filter(text)

    def _on_layout_changed(self, mode):
        """Handle layout mode change"""
        self.layout_changed.emit(mode)
        if hasattr(self.table, 'set_layout_mode'):
            self.table.set_layout_mode(mode)

    def _on_pH_changed(self, value):
        """Handle pH change"""
        self.pH_slider.setValue(int(value * 10))
        self.pH_changed.emit(value)
        if hasattr(self.table, 'set_pH'):
            self.table.set_pH(value)

    def _on_property_control_changed(self, property_key: str, index: int):
        """Handle property selection change from BiologicalPropertyControl"""
        control = self.property_controls.get(property_key)
        if control:
            prop_name = control.get_current_property()
            # Emit appropriate signal based on control type
            if control.control_type == "color":
                self.color_property_changed.emit(property_key, prop_name)
            else:
                self.size_property_changed.emit(property_key, prop_name)

            # Update table if it supports visual property changes
            if self.table and hasattr(self.table, 'set_visual_property'):
                self.table.set_visual_property(property_key, prop_name)
                self.table.update()

    def _on_property_filter_changed(self, property_key: str, min_val: float, max_val: float):
        """Handle filter range change from BiologicalPropertyControl"""
        if self.table and hasattr(self.table, 'set_property_filter'):
            self.table.set_property_filter(property_key, min_val, max_val)
            self.table.update()

    def _on_gradient_color_changed(self, property_key: str, start_color, end_color):
        """Handle gradient color change from BiologicalPropertyControl"""
        if self.table and hasattr(self.table, 'set_gradient_colors'):
            self.table.set_gradient_colors(property_key, start_color, end_color)
            self.table.update()

    def _reset_property_mappings(self):
        """Reset all property controls to their default values"""
        for control in self.property_controls.values():
            control.reset_to_default()
        if self.table:
            self.table.update()

    def _set_all_category_checkboxes(self, checked: bool):
        """Set all category checkboxes to the specified state"""
        for check in [self.nonpolar_check, self.aromatic_check, self.polar_check,
                      self.basic_check, self.acidic_check, self.special_check]:
            check.blockSignals(True)
            check.setChecked(checked)
            check.blockSignals(False)
        self._on_category_filter_changed()

    def _on_category_filter_changed(self):
        """Handle category filter change"""
        categories = []
        if self.nonpolar_check.isChecked():
            categories.append("nonpolar_aliphatic")
        if self.aromatic_check.isChecked():
            categories.append("nonpolar_aromatic")
        if self.polar_check.isChecked():
            categories.append("polar_uncharged")
        if self.basic_check.isChecked():
            categories.append("polar_positive")
        if self.acidic_check.isChecked():
            categories.append("polar_negative")
        if self.special_check.isChecked():
            categories.append("special")

        self.category_filter_changed.emit(categories)
        if hasattr(self.table, 'set_category_filters'):
            self.table.set_category_filters(categories)

    def _on_clear_filters(self):
        """Clear all filters"""
        for check in [self.nonpolar_check, self.aromatic_check, self.polar_check,
                      self.basic_check, self.acidic_check, self.special_check]:
            check.setChecked(True)

    # === Public API ===

    def set_item_selected(self, selected: bool):
        """Enable/disable edit and remove buttons"""
        self.data_management.set_item_selected(selected)

    def update_item_count(self, current: int, total: int = None):
        """Update the item count label

        Args:
            current: Number of currently visible/filtered items
            total: Total number of items (defaults to current if not provided)
        """
        if total is None:
            total = current
        self.data_management.update_item_count(current, total)

    def refresh_ai_status(self):
        """Refresh the AI API configuration status"""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()

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

    def _get_radio_style(self, color="#66bb6a"):
        return f"""
            QRadioButton {{
                color: white;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {color};
                border-radius: 8px;
                background: rgba(40, 40, 60, 200);
            }}
            QRadioButton::indicator:checked {{
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5, stop:0 {color}, stop:1 rgba(102, 187, 106, 100));
            }}
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
                border: 1px solid #ab47bc;
                padding: 5px 10px;
                border-radius: 5px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: rgba(30, 30, 50, 250);
                color: white;
                selection-background-color: #ab47bc;
            }
        """

    def _get_slider_style(self, color):
        return f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: rgba(60, 60, 80, 200);
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {color};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
        """

    def _get_small_button_style(self):
        """Get stylesheet for small utility buttons"""
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
