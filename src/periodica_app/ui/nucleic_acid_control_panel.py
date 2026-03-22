"""
Nucleic Acid Control Panel
Control panel for nucleic acid visualization settings including type filtering,
color encoding, and sequence analysis controls.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QComboBox, QSlider, QGroupBox, QPushButton,
                                QCheckBox, QSpinBox, QDoubleSpinBox, QFrame,
                                QTextEdit, QRadioButton, QButtonGroup, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from periodica_app.ui.theme_constants import ThemeColors
from periodica_app.ui.biological_search_widget import BiologicalSearchWidget
from periodica_app.ui.biological_data_management import BiologicalDataManagement
from periodica_app.ui.biological_property_control import BiologicalPropertyControl, CollapsibleBox
from periodica_app.ui.ai_generation_widget import AIGenerationWidget


class NucleicAcidControlPanel(QWidget):
    """Control panel for nucleic acid visualization settings."""

    # Signals
    layout_changed = Signal(str)
    color_property_changed = Signal(str, str)  # property_key, property_name
    size_property_changed = Signal(str, str)   # property_key, property_name
    filter_property_changed = Signal(str, float, float)  # property_key, min, max
    type_filter_changed = Signal(list)
    sequence_submitted = Signal(str, bool)  # sequence, is_rna
    tm_calculation_requested = Signal()
    complement_requested = Signal()
    transcribe_requested = Signal()
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the control panel UI."""
        # Create scroll area for the panel
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
                background: rgba(66, 165, 245, 150);
                border-radius: 5px;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background: rgb(20, 20, 35);")
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Title
        title = QLabel("Nucleic Acid Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #42A5F5;")
        main_layout.addWidget(title)

        # === Search Widget ===
        self.search_widget = BiologicalSearchWidget(
            placeholder="Search nucleic acids by name...",
            accent_color="#42A5F5"  # Blue for nucleic acids
        )
        self.search_widget.search_changed.connect(self._on_search_changed)
        main_layout.addWidget(self.search_widget)

        # === Sequence Input Section ===
        sequence_group = self._create_sequence_group()
        main_layout.addWidget(sequence_group)

        # === Layout Controls ===
        layout_group = self._create_layout_group()
        main_layout.addWidget(layout_group)

        # === Visual Property Encodings (CollapsibleBox) ===
        self._create_visual_property_encodings(main_layout)

        # === Analysis Tools ===
        analysis_group = self._create_analysis_group()
        main_layout.addWidget(analysis_group)

        # === Filter Options (CollapsibleBox) ===
        self._create_filter_options(main_layout)

        # === Generation ===
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout as GenVLayout
        gen_group = QGroupBox("Generation")
        gen_layout = GenVLayout(gen_group)
        self.auto_generate_btn = QPushButton("Auto-Generate Nucleic Acids")
        self.auto_generate_btn.setToolTip("Generate nucleic acid sequences\nwith Tm and structure prediction")
        self.auto_generate_btn.clicked.connect(self.auto_generate_requested.emit)
        gen_layout.addWidget(self.auto_generate_btn)
        self.ai_widget = AIGenerationWidget("nucleic_acid", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        gen_layout.addWidget(self.ai_widget)
        main_layout.addWidget(gen_group)

        # === Data Management ===
        self.data_mgmt = BiologicalDataManagement(
            title="Nucleic Acid Management",
            accent_color="#42A5F5"
        )
        self._connect_data_management_signals()
        main_layout.addWidget(self.data_mgmt)

        main_layout.addStretch()

        scroll.setWidget(content)

        # Set up main layout with scroll area
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

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
        # Note: create_from_components_requested signal is available on the control panel
        # for external consumers but needs separate button handling if needed

    def _create_visual_property_encodings(self, parent_layout):
        """Create Visual Property Encodings collapsible section with BiologicalPropertyControl."""
        # Nucleic acid color properties: Type, GC Content, Tm
        color_properties = ["None", "Type", "GC Content", "Tm"]
        # Nucleic acid size properties: Length, MW
        size_properties = ["None", "Length", "MW"]

        self.visual_collapsible = CollapsibleBox(
            "Visual Property Encodings",
            accent_color="#42A5F5"
        )

        # Store property controls for later access
        self.property_controls = {}

        # Fill Color control
        self.fill_color_control = BiologicalPropertyControl(
            title="Fill Colour",
            property_key="fill_color",
            available_properties=color_properties,
            control_type="color",
            default_index=1,  # Type
            accent_color="#42A5F5"
        )
        self.fill_color_control.set_current_index(1)
        self.fill_color_control.property_changed.connect(self._on_property_control_changed)
        self.fill_color_control.filter_changed.connect(self._on_filter_range_changed)
        self.visual_collapsible.add_widget(self.fill_color_control)
        self.property_controls["fill_color"] = self.fill_color_control

        # Border Color control
        self.border_color_control = BiologicalPropertyControl(
            title="Border Colour",
            property_key="border_color",
            available_properties=color_properties,
            control_type="color",
            default_index=2,  # GC Content
            accent_color="#42A5F5"
        )
        self.border_color_control.set_current_index(2)
        self.border_color_control.property_changed.connect(self._on_property_control_changed)
        self.border_color_control.filter_changed.connect(self._on_filter_range_changed)
        self.visual_collapsible.add_widget(self.border_color_control)
        self.property_controls["border_color"] = self.border_color_control

        # Glow Color control
        self.glow_color_control = BiologicalPropertyControl(
            title="Glow Colour",
            property_key="glow_color",
            available_properties=color_properties,
            control_type="color",
            default_index=3,  # Tm
            accent_color="#42A5F5"
        )
        self.glow_color_control.set_current_index(3)
        self.glow_color_control.property_changed.connect(self._on_property_control_changed)
        self.glow_color_control.filter_changed.connect(self._on_filter_range_changed)
        self.visual_collapsible.add_widget(self.glow_color_control)
        self.property_controls["glow_color"] = self.glow_color_control

        # Card Size control (size-based)
        self.card_size_control = BiologicalPropertyControl(
            title="Card Size",
            property_key="card_size",
            available_properties=size_properties,
            control_type="size",
            default_index=1,  # Length
            accent_color="#42A5F5"
        )
        self.card_size_control.set_current_index(1)
        self.card_size_control.property_changed.connect(self._on_property_control_changed)
        self.card_size_control.filter_changed.connect(self._on_filter_range_changed)
        self.visual_collapsible.add_widget(self.card_size_control)
        self.property_controls["card_size"] = self.card_size_control

        # Border Size control (size-based)
        self.border_size_control = BiologicalPropertyControl(
            title="Border Size",
            property_key="border_size",
            available_properties=size_properties,
            control_type="size",
            default_index=2,  # MW
            accent_color="#42A5F5"
        )
        self.border_size_control.set_current_index(2)
        self.border_size_control.property_changed.connect(self._on_property_control_changed)
        self.border_size_control.filter_changed.connect(self._on_filter_range_changed)
        self.visual_collapsible.add_widget(self.border_size_control)
        self.property_controls["border_size"] = self.border_size_control

        # Reset button
        reset_btn = QPushButton("Reset Property Mappings")
        reset_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #42A5F5, stop:1 #1976D2);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #64B5F6, stop:1 #42A5F5);
            }
        """)
        reset_btn.clicked.connect(self._on_reset_property_mappings)
        self.visual_collapsible.add_widget(reset_btn)

        parent_layout.addWidget(self.visual_collapsible)

    def _create_filter_options(self, parent_layout):
        """Create Filter Options collapsible section."""
        self.filter_collapsible = CollapsibleBox(
            "Filter Options",
            accent_color="#FF7043"
        )

        # Type filters
        type_label = QLabel("Nucleic Acid Types:")
        type_label.setStyleSheet("color: white; font-weight: bold; margin-bottom: 5px;")
        self.filter_collapsible.add_widget(type_label)

        self.type_checks = {}
        types = ["DNA", "mRNA", "tRNA", "rRNA", "miRNA", "siRNA", "snRNA", "Other RNA"]

        for na_type in types:
            cb = QCheckBox(na_type)
            cb.setChecked(True)
            cb.setStyleSheet(self._checkbox_style("#FF7043"))
            cb.stateChanged.connect(self._on_filter_changed)
            self.type_checks[na_type.lower().replace(' ', '')] = cb
            self.filter_collapsible.add_widget(cb)

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
        self.filter_collapsible.add_widget(clear_btn)

        parent_layout.addWidget(self.filter_collapsible)

    def _on_property_control_changed(self, property_key, index):
        """Handle property control selection change."""
        control = self.property_controls.get(property_key)
        if control:
            property_name = control.get_current_property()
            # Emit the appropriate signal based on control type
            if control.control_type == "color":
                self.color_property_changed.emit(property_key, property_name.lower().replace(' ', '_'))
            else:
                self.size_property_changed.emit(property_key, property_name.lower().replace(' ', '_'))

    def _on_filter_range_changed(self, property_key, min_val, max_val):
        """Handle filter range change from property controls."""
        self.filter_property_changed.emit(property_key, min_val, max_val)

    def _on_reset_property_mappings(self):
        """Reset all property mappings to defaults."""
        for control in self.property_controls.values():
            control.reset_to_default()

    def _on_clear_filters(self):
        """Clear all type filters (check all)."""
        for cb in self.type_checks.values():
            cb.setChecked(True)

    def _checkbox_style(self, color):
        """Get checkbox style with given accent color."""
        return f"""
            QCheckBox {{
                color: white;
                spacing: 8px;
                padding: 2px;
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

    def _on_search_changed(self, text):
        """Handle search text change."""
        self.search_changed.emit(text)

    def _create_sequence_group(self):
        """Create sequence input group."""
        group = QGroupBox("Sequence Input")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        # Sequence type selection
        type_layout = QHBoxLayout()
        self.type_group = QButtonGroup()
        self.dna_radio = QRadioButton("DNA")
        self.rna_radio = QRadioButton("RNA")
        self.dna_radio.setChecked(True)
        self.type_group.addButton(self.dna_radio)
        self.type_group.addButton(self.rna_radio)
        self.dna_radio.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        self.rna_radio.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        type_layout.addWidget(self.dna_radio)
        type_layout.addWidget(self.rna_radio)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Sequence text area
        self.sequence_input = QTextEdit()
        self.sequence_input.setMaximumHeight(80)
        self.sequence_input.setPlaceholderText("Enter sequence (e.g., ATGCGATCGA...)")
        self.sequence_input.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 5px;
                font-family: monospace;
            }}
        """)
        layout.addWidget(self.sequence_input)

        # Analyze button
        btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setStyleSheet(self._button_style())
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        btn_layout.addWidget(self.analyze_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(self._button_style())
        self.clear_btn.clicked.connect(self.sequence_input.clear)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)

        return group

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
            "Length",
            "GC Content",
            "Organism"
        ])
        self.layout_combo.setStyleSheet(self._combo_style())
        self.layout_combo.currentTextChanged.connect(
            lambda t: self.layout_changed.emit(t.lower().replace(' ', '_'))
        )
        layout.addWidget(self.layout_combo)

        return group

    def _create_analysis_group(self):
        """Create analysis tools group."""
        group = QGroupBox("Analysis Tools")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        # Tm calculation
        self.tm_btn = QPushButton("Calculate Tm")
        self.tm_btn.setStyleSheet(self._button_style())
        self.tm_btn.clicked.connect(self.tm_calculation_requested.emit)
        layout.addWidget(self.tm_btn)

        # Get complement
        self.complement_btn = QPushButton("Get Complement")
        self.complement_btn.setStyleSheet(self._button_style())
        self.complement_btn.clicked.connect(self.complement_requested.emit)
        layout.addWidget(self.complement_btn)

        # Transcribe/Reverse transcribe
        self.transcribe_btn = QPushButton("Transcribe DNA→RNA")
        self.transcribe_btn.setStyleSheet(self._button_style())
        self.transcribe_btn.clicked.connect(self.transcribe_requested.emit)
        layout.addWidget(self.transcribe_btn)

        # Salt concentration for Tm
        salt_layout = QHBoxLayout()
        salt_layout.addWidget(QLabel("Na+ (mM):"))
        self.salt_spin = QSpinBox()
        self.salt_spin.setRange(1, 1000)
        self.salt_spin.setValue(50)
        self.salt_spin.setStyleSheet(self._spin_style())
        salt_layout.addWidget(self.salt_spin)
        layout.addLayout(salt_layout)

        return group

    def _on_analyze_clicked(self):
        """Handle analyze button click."""
        sequence = self.sequence_input.toPlainText().strip()
        # Remove whitespace and validate
        sequence = ''.join(sequence.split()).upper()
        if sequence:
            is_rna = self.rna_radio.isChecked()
            self.sequence_submitted.emit(sequence, is_rna)

    def _on_filter_changed(self):
        """Handle filter checkbox changes."""
        active = [k for k, cb in self.type_checks.items() if cb.isChecked()]
        self.type_filter_changed.emit(active)

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

    def _spin_style(self):
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 5px;
            }}
        """

    # === Public API ===

    def get_salt_concentration(self):
        """Get salt concentration in M."""
        return self.salt_spin.value() / 1000.0

    def set_sequence(self, sequence, is_rna=False):
        """Set sequence in input field."""
        self.sequence_input.setText(sequence)
        if is_rna:
            self.rna_radio.setChecked(True)
        else:
            self.dna_radio.setChecked(True)

    def set_item_selected(self, selected: bool):
        """Enable/disable edit, remove, export, duplicate buttons."""
        self.data_mgmt.set_item_selected(selected)

    def set_search_results(self, showing: int, total: int):
        """Update search results count."""
        self.search_widget.set_results_count(showing, total)

    def update_item_count(self, current: int, total: int = None):
        """Update the nucleic acid count display.

        Args:
            current: Number of currently visible items
            total: Total number of items (defaults to current if not provided)
        """
        if total is None:
            total = current
        self.data_mgmt.update_item_count(current, total)

    def refresh_ai_status(self):
        """Refresh the AI API configuration status."""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()
