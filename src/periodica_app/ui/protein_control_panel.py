"""
Protein Control Panel
Control panel for protein visualization settings including structure display,
color encoding, and folding simulation controls.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QComboBox, QSlider, QGroupBox, QPushButton,
                                QCheckBox, QSpinBox, QDoubleSpinBox, QFrame,
                                QTextEdit, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, Signal

from periodica_app.ui.theme_constants import ThemeColors
from periodica_app.ui.biological_search_widget import BiologicalSearchWidget
from periodica_app.ui.biological_data_management import BiologicalDataManagement
from periodica_app.ui.biological_property_control import BiologicalPropertyControl, CollapsibleBox
from periodica_app.ui.ai_generation_widget import AIGenerationWidget


class ProteinControlPanel(QWidget):
    """Control panel for protein visualization settings."""

    # Signals
    layout_changed = Signal(str)
    color_property_changed = Signal(str)
    size_property_changed = Signal(str)
    pH_changed = Signal(float)
    filter_changed = Signal(list)
    sequence_submitted = Signal(str)
    ramachandran_requested = Signal()
    structure_prediction_requested = Signal()
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
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # === Search Widget ===
        self.search_widget = BiologicalSearchWidget(
            placeholder="Search proteins by name...",
            accent_color="#AB47BC"  # Purple for proteins
        )
        self.search_widget.search_changed.connect(self._on_search_changed)
        main_layout.addWidget(self.search_widget)

        # === Sequence Input Section ===
        sequence_group = self._create_sequence_group()
        main_layout.addWidget(sequence_group)

        # === Layout Controls ===
        layout_group = self._create_layout_group()
        main_layout.addWidget(layout_group)

        # === Visual Encoding ===
        visual_group = self._create_visual_encoding_group()
        main_layout.addWidget(visual_group)

        # === pH and Environment ===
        env_group = self._create_environment_group()
        main_layout.addWidget(env_group)

        # === Analysis Tools ===
        analysis_group = self._create_analysis_group()
        main_layout.addWidget(analysis_group)

        # === Filter Controls ===
        filter_group = self._create_filter_group()
        main_layout.addWidget(filter_group)

        # === Generation ===
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout as GenVLayout
        gen_group = QGroupBox("Generation")
        gen_layout = GenVLayout(gen_group)
        self.auto_generate_btn = QPushButton("Auto-Generate Proteins")
        self.auto_generate_btn.setToolTip("Generate proteins from template sequences\nwith structure and property prediction")
        self.auto_generate_btn.clicked.connect(self.auto_generate_requested.emit)
        gen_layout.addWidget(self.auto_generate_btn)
        self.ai_widget = AIGenerationWidget("protein", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        gen_layout.addWidget(self.ai_widget)
        main_layout.addWidget(gen_group)

        # === Data Management ===
        self.data_mgmt = BiologicalDataManagement(
            title="Protein Management",
            accent_color="#AB47BC"
        )
        self._connect_data_management_signals()
        main_layout.addWidget(self.data_mgmt)

        main_layout.addStretch()

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
        # Note: create_from_components_requested is emitted via the Add button
        # which triggers add_requested, and callers can handle protein building there

    def _on_search_changed(self, text):
        """Handle search text change."""
        self.search_changed.emit(text)

    def _create_sequence_group(self):
        """Create sequence input group."""
        group = QGroupBox("Sequence Input")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        # Sequence text area
        self.sequence_input = QTextEdit()
        self.sequence_input.setMaximumHeight(80)
        self.sequence_input.setPlaceholderText("Enter protein sequence (e.g., MVLSPADKTNVK...)")
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
        self.analyze_btn = QPushButton("Analyze Sequence")
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
            "Mass",
            "Function",
            "Structure",
            "Localization",
            "Organism"
        ])
        self.layout_combo.setStyleSheet(self._combo_style())
        self.layout_combo.currentTextChanged.connect(
            lambda t: self.layout_changed.emit(t.lower())
        )
        layout.addWidget(self.layout_combo)

        return group

    def _create_visual_encoding_group(self):
        """Create visual encoding controls with expandable BiologicalPropertyControl widgets."""
        collapsible = CollapsibleBox("Visual Property Encodings", "#AB47BC")

        # Property metadata for proteins
        property_metadata = {
            "None": {"min": 0, "max": 100, "unit": ""},
            "MW": {"min": 1000, "max": 1000000, "unit": "Da"},
            "pI": {"min": 3.0, "max": 12.0, "unit": ""},
            "Structure %": {"min": 0, "max": 100, "unit": "%"},
            "Alpha Helix %": {"min": 0, "max": 100, "unit": "%"},
            "Beta Sheet %": {"min": 0, "max": 100, "unit": "%"},
            "Function": {"min": 0, "max": 10, "unit": "", "type": "categorical"},
            "Length": {"min": 10, "max": 10000, "unit": "aa"},
        }

        # Color properties available for proteins
        color_properties = ["None", "MW", "pI", "Structure %", "Function"]
        # Size properties available for proteins
        size_properties = ["None", "Length", "MW"]

        # Fill Color control
        self.fill_color_control = BiologicalPropertyControl(
            "Fill Color", "fill_color", color_properties,
            property_metadata=property_metadata,
            control_type="color", default_index=4,  # Default to Function
            accent_color="#AB47BC"
        )
        self.fill_color_control.property_combo.setCurrentIndex(4)
        self.fill_color_control.property_changed.connect(self._on_property_control_changed)
        collapsible.content_layout.addWidget(self.fill_color_control)

        # Card Size control
        self.card_size_control = BiologicalPropertyControl(
            "Card Size", "card_size", size_properties,
            property_metadata=property_metadata,
            control_type="size", default_index=1,  # Default to Length
            accent_color="#AB47BC"
        )
        self.card_size_control.property_combo.setCurrentIndex(1)
        self.card_size_control.property_changed.connect(self._on_property_control_changed)
        collapsible.content_layout.addWidget(self.card_size_control)

        # Reset button
        reset_btn = QPushButton("Reset Property Mappings")
        reset_btn.setStyleSheet(self._accent_button_style())
        reset_btn.clicked.connect(self._reset_property_mappings)
        collapsible.content_layout.addWidget(reset_btn)

        collapsible.set_expanded(True)
        return collapsible

    def _create_environment_group(self):
        """Create environment controls."""
        group = QGroupBox("Environment")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        # pH slider
        ph_layout = QHBoxLayout()
        ph_layout.addWidget(QLabel("pH:"))
        self.pH_slider = QSlider(Qt.Orientation.Horizontal)
        self.pH_slider.setRange(0, 140)  # 0.0 to 14.0
        self.pH_slider.setValue(70)  # pH 7.0
        self.pH_slider.setStyleSheet(self._slider_style())
        self.pH_slider.valueChanged.connect(self._on_pH_changed)
        ph_layout.addWidget(self.pH_slider)

        self.pH_label = QLabel("7.0")
        self.pH_label.setMinimumWidth(40)
        ph_layout.addWidget(self.pH_label)
        layout.addLayout(ph_layout)

        # Temperature (for future Tm calculations)
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temp (°C):"))
        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(0, 100)
        self.temp_spin.setValue(25)
        self.temp_spin.setStyleSheet(self._spin_style())
        temp_layout.addWidget(self.temp_spin)
        layout.addLayout(temp_layout)

        return group

    def _create_analysis_group(self):
        """Create analysis tools group."""
        group = QGroupBox("Analysis Tools")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        # Ramachandran plot button
        self.ramachandran_btn = QPushButton("Ramachandran Plot")
        self.ramachandran_btn.setStyleSheet(self._button_style())
        self.ramachandran_btn.clicked.connect(self.ramachandran_requested.emit)
        layout.addWidget(self.ramachandran_btn)

        # Structure prediction button
        self.predict_btn = QPushButton("Predict Structure")
        self.predict_btn.setStyleSheet(self._button_style())
        self.predict_btn.clicked.connect(self.structure_prediction_requested.emit)
        layout.addWidget(self.predict_btn)

        # Show disulfide bonds
        self.disulfide_check = QCheckBox("Show Disulfide Bonds")
        self.disulfide_check.setChecked(True)
        self.disulfide_check.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        layout.addWidget(self.disulfide_check)

        # Show secondary structure
        self.secondary_check = QCheckBox("Show Secondary Structure")
        self.secondary_check.setChecked(True)
        self.secondary_check.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        layout.addWidget(self.secondary_check)

        return group

    def _create_filter_group(self):
        """Create filter controls with CollapsibleBox."""
        collapsible = CollapsibleBox("Filter Options", "#607D8B")

        # Function filter label
        func_label = QLabel("Function:")
        func_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 5px;")
        collapsible.content_layout.addWidget(func_label)

        # Function filters in a grid
        func_grid = QWidget()
        func_layout = QGridLayout(func_grid)
        func_layout.setContentsMargins(10, 5, 5, 10)
        func_layout.setSpacing(5)

        self.function_checks = {}
        functions = [
            ("Enzyme", "enzyme", "#4CAF50"),
            ("Structural", "structural", "#2196F3"),
            ("Transport", "transport", "#FF9800"),
            ("Signaling", "signaling", "#9C27B0"),
            ("Receptor", "receptor", "#E91E63"),
            ("Antibody", "antibody", "#00BCD4"),
            ("Storage", "storage", "#795548"),
            ("Regulatory", "regulatory", "#607D8B"),
        ]

        for i, (label, key, color) in enumerate(functions):
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(self._get_checkbox_style(color))
            cb.stateChanged.connect(self._on_filter_changed)
            self.function_checks[key] = cb
            func_layout.addWidget(cb, i // 2, i % 2)

        collapsible.content_layout.addWidget(func_grid)

        # Select All / Clear All buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(10, 0, 5, 10)
        btn_layout.setSpacing(5)

        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet(self._small_button_style())
        select_all_btn.clicked.connect(lambda: self._set_all_function_filters(True))
        btn_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setStyleSheet(self._small_button_style())
        clear_all_btn.clicked.connect(lambda: self._set_all_function_filters(False))
        btn_layout.addWidget(clear_all_btn)

        btn_layout.addStretch()
        collapsible.content_layout.addWidget(btn_row)

        return collapsible

    def _set_all_function_filters(self, checked: bool):
        """Set all function filter checkboxes to the given state."""
        for cb in self.function_checks.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._on_filter_changed()

    def _on_analyze_clicked(self):
        """Handle analyze button click."""
        sequence = self.sequence_input.toPlainText().strip()
        # Remove whitespace and validate
        sequence = ''.join(sequence.split()).upper()
        if sequence:
            self.sequence_submitted.emit(sequence)

    def _on_color_changed(self, text):
        """Handle color property change."""
        prop_map = {
            "Function": "function",
            "Localization": "localization",
            "Organism": "organism",
            "Secondary Structure": "secondary_structure",
            "Hydropathy": "hydropathy",
            "Charge": "charge",
            "Mass": "mass"
        }
        self.color_property_changed.emit(prop_map.get(text, "function"))

    def _on_size_changed(self, text):
        """Handle size property change."""
        prop_map = {
            "None": "none",
            "Molecular Mass": "molecular_mass",
            "Length": "length",
            "Helix Content": "helix_content",
            "Sheet Content": "sheet_content"
        }
        self.size_property_changed.emit(prop_map.get(text, "none"))

    def _on_pH_changed(self, value):
        """Handle pH slider change."""
        pH = value / 10.0
        self.pH_label.setText(f"{pH:.1f}")
        self.pH_changed.emit(pH)

    def _on_filter_changed(self):
        """Handle filter checkbox changes."""
        active = [k for k, cb in self.function_checks.items() if cb.isChecked()]
        self.filter_changed.emit(active)

    def _on_property_control_changed(self, property_key: str, index: int):
        """Handle property control changes from BiologicalPropertyControl widgets."""
        control = getattr(self, f"{property_key}_control", None)
        if control:
            prop_name = control.get_current_property().lower().replace(' ', '_').replace('%', 'pct')
            if property_key == "fill_color":
                self.color_property_changed.emit(prop_name)
            elif property_key == "card_size":
                self.size_property_changed.emit(prop_name)

    def _reset_property_mappings(self):
        """Reset all property mappings to their defaults."""
        self.fill_color_control.set_current_index(4)  # Function
        self.card_size_control.set_current_index(1)   # Length

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

    def _slider_style(self):
        return f"""
            QSlider::groove:horizontal {{
                background: {ThemeColors.BG_MEDIUM};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {ThemeColors.ACCENT};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {ThemeColors.ACCENT_LIGHT};
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

    def _accent_button_style(self):
        """Style for accent-colored buttons."""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #AB47BC, stop:1 #7B1FA2);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7B1FA2, stop:1 #AB47BC);
            }
        """

    def _small_button_style(self):
        """Style for small utility buttons."""
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

    def _get_checkbox_style(self, color: str):
        """Style for colored checkboxes."""
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

    # === Public API ===

    def get_current_pH(self):
        """Get current pH value."""
        return self.pH_slider.value() / 10.0

    def get_current_temperature(self):
        """Get current temperature."""
        return self.temp_spin.value()

    def set_pH(self, pH):
        """Set pH value."""
        self.pH_slider.setValue(int(pH * 10))

    def set_sequence(self, sequence):
        """Set sequence in input field."""
        self.sequence_input.setText(sequence)

    def set_item_selected(self, selected: bool):
        """Enable/disable edit, remove, export, duplicate buttons."""
        self.data_mgmt.set_item_selected(selected)

    def set_search_results(self, showing: int, total: int):
        """Update search results count."""
        self.search_widget.set_results_count(showing, total)

    def update_item_count(self, current: int, total: int = None):
        """Update the protein count display.

        Args:
            current: Number of currently visible/filtered items
            total: Total number of items (defaults to current if not provided)
        """
        if total is None:
            total = current
        self.data_mgmt.update_item_count(current, total)

    def refresh_ai_status(self):
        """Refresh the AI API configuration status."""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()
