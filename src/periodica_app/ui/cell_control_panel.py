"""
Cell Control Panel
Control panel for cell visualization settings including type filtering,
color encoding, size mapping, and metabolic analysis tools.
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
from periodica.core.cell_enums import CellType, TissueType


class CellControlPanel(QWidget):
    """Control panel for cell visualization settings."""

    # Visualization signals
    layout_changed = Signal(str)
    color_property_changed = Signal(str)
    size_property_changed = Signal(str)
    type_filter_changed = Signal(list)
    tissue_filter_changed = Signal(list)
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
    cell_creation_requested = Signal()
    analysis_requested = Signal()

    # AI generation signals
    ai_generate_requested = Signal()
    ai_settings_requested = Signal()
    auto_generate_requested = Signal()

    def __init__(self, table_widget=None, parent=None):
        super().__init__(parent)
        self.table = table_widget
        self._setup_ui()

    def _setup_ui(self):
        """Set up the control panel UI."""
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
                background: rgba(233, 30, 99, 150);
                border-radius: 5px;
            }}
        """)

        content = QWidget()
        content.setStyleSheet(f"background: {ThemeColors.BG_DARK};")
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Title
        title = QLabel("Cell Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #E91E63;")
        main_layout.addWidget(title)

        # Search widget
        self.search_widget = BiologicalSearchWidget(
            placeholder="Search cells...",
            accent_color="#E91E63"
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
        self.auto_generate_btn = QPushButton("Auto-Generate Cells")
        self.auto_generate_btn.setToolTip("Generate cell types with\nmetabolic and geometric properties")
        self.auto_generate_btn.clicked.connect(self.auto_generate_requested.emit)
        gen_layout.addWidget(self.auto_generate_btn)
        self.ai_widget = AIGenerationWidget("cell", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        gen_layout.addWidget(self.ai_widget)
        main_layout.addWidget(gen_group)

        # Data management
        self.data_management = BiologicalDataManagement(
            title="Data Management",
            accent_color="#E91E63",
        )
        self._connect_data_management_signals()
        main_layout.addWidget(self.data_management)

        main_layout.addStretch()

        scroll.setWidget(content)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _create_layout_mode_group(self):
        """Create layout mode selection group."""
        group = QGroupBox("Layout Mode")
        group.setStyleSheet(self._get_group_style("#E91E63"))
        layout = QVBoxLayout(group)

        self.grid_radio = QRadioButton("Grid (Alphabetical)")
        self.type_radio = QRadioButton("By Cell Type")
        self.tissue_radio = QRadioButton("By Tissue")
        self.size_radio = QRadioButton("By Size")
        self.metabolic_radio = QRadioButton("By Metabolic Rate")

        self.grid_radio.setChecked(True)

        radio_style = self._get_radio_style()
        for radio in [self.grid_radio, self.type_radio, self.tissue_radio,
                      self.size_radio, self.metabolic_radio]:
            radio.setStyleSheet(radio_style)
            layout.addWidget(radio)

        self.grid_radio.toggled.connect(lambda: self._on_layout_changed("grid") if self.grid_radio.isChecked() else None)
        self.type_radio.toggled.connect(lambda: self._on_layout_changed("type") if self.type_radio.isChecked() else None)
        self.tissue_radio.toggled.connect(lambda: self._on_layout_changed("tissue") if self.tissue_radio.isChecked() else None)
        self.size_radio.toggled.connect(lambda: self._on_layout_changed("size") if self.size_radio.isChecked() else None)
        self.metabolic_radio.toggled.connect(lambda: self._on_layout_changed("metabolic_rate") if self.metabolic_radio.isChecked() else None)

        return group

    def _create_visual_properties_group(self):
        """Create visual property encodings with expandable controls."""
        collapsible = CollapsibleBox("Visual Property Encodings", "#E91E63")

        property_metadata = {
            "None": {"min": 0, "max": 100, "unit": ""},
            "Type": {"min": 0, "max": 10, "unit": ""},
            "Tissue": {"min": 0, "max": 10, "unit": ""},
            "Metabolic Rate": {"min": 0, "max": 1000, "unit": "fW"},
            "Diameter": {"min": 1, "max": 100, "unit": "um"},
            "Volume": {"min": 1, "max": 10000, "unit": "fL"},
            "Mass": {"min": 1, "max": 1000, "unit": "pg"},
            "Lifespan": {"min": 1, "max": 1000, "unit": "days"},
            "Mitochondria": {"min": 0, "max": 5000, "unit": ""},
        }

        color_properties = ["None", "Type", "Tissue", "Metabolic Rate", "Lifespan"]
        size_properties = ["None", "Diameter", "Volume", "Metabolic Rate", "Mitochondria"]

        self.fill_color_control = BiologicalPropertyControl(
            "Fill Color", "fill_color", color_properties,
            property_metadata=property_metadata,
            control_type="color", default_index=1,
            accent_color="#E91E63"
        )
        self.fill_color_control.property_combo.setCurrentIndex(1)
        self.fill_color_control.property_changed.connect(self._on_property_control_changed)
        collapsible.content_layout.addWidget(self.fill_color_control)

        self.card_size_control = BiologicalPropertyControl(
            "Card Size", "card_size", size_properties,
            property_metadata=property_metadata,
            control_type="size", default_index=1,
            accent_color="#E91E63"
        )
        self.card_size_control.property_combo.setCurrentIndex(1)
        self.card_size_control.property_changed.connect(self._on_property_control_changed)
        collapsible.content_layout.addWidget(self.card_size_control)

        reset_btn = QPushButton("Reset Property Mappings")
        reset_btn.setStyleSheet(self._get_accent_button_style())
        reset_btn.clicked.connect(self._reset_property_mappings)
        collapsible.content_layout.addWidget(reset_btn)

        collapsible.set_expanded(True)
        return collapsible

    def _create_filter_options_group(self):
        """Create filter options with type and tissue checkboxes."""
        collapsible = CollapsibleBox("Filter Options", "#607D8B")

        # Cell Type Filter
        type_label = QLabel("Cell Type:")
        type_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 5px;")
        collapsible.content_layout.addWidget(type_label)

        type_grid = QWidget()
        type_layout = QGridLayout(type_grid)
        type_layout.setContentsMargins(10, 5, 5, 10)
        type_layout.setSpacing(5)

        self.type_checkboxes = {}
        types = [
            ("Blood Cells", "erythrocyte,leukocyte,platelet,neutrophil,lymphocyte", "#F44336"),
            ("Neurons", "neuron,astrocyte,oligodendrocyte", "#9C27B0"),
            ("Muscle", "myocyte,cardiomyocyte,smooth_muscle", "#E91E63"),
            ("Epithelial", "epithelial,keratinocyte,enterocyte", "#2196F3"),
            ("Connective", "fibroblast,adipocyte,chondrocyte,osteocyte", "#4CAF50"),
            ("Glandular", "hepatocyte,pancreatic_beta,thyroid", "#FF9800"),
            ("Stem Cells", "stem_cell,hematopoietic,mesenchymal", "#00BCD4"),
        ]

        for i, (label, keys, color) in enumerate(types):
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(self._get_checkbox_style(color))
            cb.stateChanged.connect(self._on_type_filter_changed)
            self.type_checkboxes[keys] = cb
            type_layout.addWidget(cb, i // 2, i % 2)

        collapsible.content_layout.addWidget(type_grid)

        # Tissue Filter
        tissue_label = QLabel("Tissue:")
        tissue_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px; margin-top: 5px;")
        collapsible.content_layout.addWidget(tissue_label)

        tissue_grid = QWidget()
        tissue_layout = QGridLayout(tissue_grid)
        tissue_layout.setContentsMargins(10, 5, 5, 10)
        tissue_layout.setSpacing(5)

        self.tissue_checkboxes = {}
        tissues = [
            ("Blood", "blood", "#F44336"),
            ("Nervous", "nervous", "#9C27B0"),
            ("Muscle", "muscle", "#E91E63"),
            ("Connective", "connective", "#4CAF50"),
            ("Epithelial", "epithelial,skin", "#2196F3"),
            ("Organs", "liver,kidney,lung,pancreas", "#FF9800"),
            ("Bone", "bone,bone_marrow", "#FFF8E1"),
        ]

        for i, (label, keys, color) in enumerate(tissues):
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(self._get_checkbox_style(color))
            cb.stateChanged.connect(self._on_tissue_filter_changed)
            self.tissue_checkboxes[keys] = cb
            tissue_layout.addWidget(cb, i // 2, i % 2)

        collapsible.content_layout.addWidget(tissue_grid)

        # Select All / Clear All
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(10, 0, 5, 10)
        btn_layout.setSpacing(5)

        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet(self._get_small_button_style())
        select_all_btn.clicked.connect(lambda: self._set_all_checkboxes(True))
        btn_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setStyleSheet(self._get_small_button_style())
        clear_all_btn.clicked.connect(lambda: self._set_all_checkboxes(False))
        btn_layout.addWidget(clear_all_btn)

        btn_layout.addStretch()
        collapsible.content_layout.addWidget(btn_row)

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
            self.cell_creation_requested.emit)

    # Event handlers
    def _on_layout_changed(self, mode):
        self.layout_changed.emit(mode)
        if self.table:
            self.table.set_layout_mode(mode)

    def _on_search_changed(self, text):
        self.search_changed.emit(text)
        if self.table and hasattr(self.table, 'set_search_filter'):
            self.table.set_search_filter(text)

    def _on_property_control_changed(self, property_key, index):
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

    def _on_type_filter_changed(self):
        active = []
        for keys, cb in self.type_checkboxes.items():
            if cb.isChecked():
                active.extend(keys.split(','))
        self.type_filter_changed.emit(active)
        if self.table:
            self.table.set_type_filters(active)

    def _on_tissue_filter_changed(self):
        active = []
        for keys, cb in self.tissue_checkboxes.items():
            if cb.isChecked():
                active.extend(keys.split(','))
        self.tissue_filter_changed.emit(active)
        if self.table and hasattr(self.table, 'set_tissue_filters'):
            self.table.set_tissue_filters(active)

    def _set_all_checkboxes(self, checked):
        for cb in self.type_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        for cb in self.tissue_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._on_type_filter_changed()
        self._on_tissue_filter_changed()

    def _reset_property_mappings(self):
        self.fill_color_control.set_current_index(1)
        self.card_size_control.set_current_index(1)

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
        return """
            QRadioButton {
                color: white;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #E91E63;
                border-radius: 8px;
                background: rgba(40, 40, 60, 200);
            }
            QRadioButton::indicator:checked {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5, stop:0 #E91E63, stop:1 rgba(233, 30, 99, 100));
            }
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
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E91E63, stop:1 #9C27B0);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #9C27B0, stop:1 #E91E63);
            }
        """

    # Public API
    def set_cell_count(self, count):
        self.data_management.update_item_count(count, count)

    def set_item_selected(self, selected: bool):
        self.data_management.set_item_selected(selected)

    def get_active_type_filters(self):
        active = []
        for keys, cb in self.type_checkboxes.items():
            if cb.isChecked():
                active.extend(keys.split(','))
        return active

    def get_active_tissue_filters(self):
        active = []
        for keys, cb in self.tissue_checkboxes.items():
            if cb.isChecked():
                active.extend(keys.split(','))
        return active

    def refresh_ai_status(self):
        """Refresh the AI API configuration status."""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()
