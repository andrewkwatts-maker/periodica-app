"""
Material Control Panel
Provides UI controls for material visualization settings.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                                QScrollArea, QComboBox, QCheckBox, QPushButton,
                                QFrame, QLineEdit, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from periodica.core.material_enums import MaterialLayoutMode, MaterialCategory, MaterialProperty
from periodica_app.ui.ai_generation_widget import AIGenerationWidget


class MaterialControlPanel(QWidget):
    """Control panel for material visualization settings"""

    # Signals for actions
    add_material_requested = Signal()
    edit_material_requested = Signal()
    delete_material_requested = Signal()
    export_requested = Signal()
    import_requested = Signal()
    duplicate_requested = Signal()

    # AI generation signals
    ai_generate_requested = Signal()
    ai_settings_requested = Signal()
    auto_generate_requested = Signal()

    def __init__(self, table_widget, parent=None):
        super().__init__(parent)
        self.table = table_widget

        self._setup_ui()

    def _setup_ui(self):
        """Set up the control panel UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Title
        title = QLabel("Material Controls")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        main_layout.addWidget(title)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)

        # Layout Mode Group
        layout_group = self._create_layout_group()
        content_layout.addWidget(layout_group)

        # Filter Group
        filter_group = self._create_filter_group()
        content_layout.addWidget(filter_group)

        # Visual Encoding Group
        visual_group = self._create_visual_group()
        content_layout.addWidget(visual_group)

        # AI Generation Group
        gen_group = QGroupBox("Generation")
        gen_group.setStyleSheet(self._create_group_style())
        gen_layout = QVBoxLayout(gen_group)
        self.auto_generate_btn = QPushButton("Auto-Generate Materials")
        self.auto_generate_btn.setToolTip(
            "Automatically generate materials from alloy compositions\n"
            "with microstructure and mechanical property prediction"
        )
        self.auto_generate_btn.clicked.connect(self.auto_generate_requested.emit)
        gen_layout.addWidget(self.auto_generate_btn)
        self.ai_widget = AIGenerationWidget("material", self)
        self.ai_widget.generate_requested.connect(self.ai_generate_requested.emit)
        self.ai_widget.settings_requested.connect(self.ai_settings_requested.emit)
        gen_layout.addWidget(self.ai_widget)
        content_layout.addWidget(gen_group)

        # Actions Group
        actions_group = self._create_actions_group()
        content_layout.addWidget(actions_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_group_style(self):
        """Get common group box style"""
        return """
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                color: white;
                border: 2px solid #667eea;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background: rgba(30, 30, 50, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """

    def _create_layout_group(self):
        """Create layout mode selection group"""
        group = QGroupBox("Layout Mode")
        group.setStyleSheet(self._create_group_style())
        layout = QVBoxLayout(group)

        self.layout_combo = QComboBox()
        for mode in MaterialLayoutMode:
            self.layout_combo.addItem(MaterialLayoutMode.get_display_name(mode), mode.value)
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)
        self.layout_combo.setStyleSheet(self._get_combo_style())
        layout.addWidget(self.layout_combo)

        return group

    def _create_filter_group(self):
        """Create filter controls group"""
        group = QGroupBox("Filters")
        group.setStyleSheet(self._create_group_style())
        layout = QVBoxLayout(group)

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: white;")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search materials...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background: rgba(40, 40, 60, 200);
                border: 1px solid #667eea;
                border-radius: 4px;
                color: white;
                padding: 5px;
            }
        """)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # Category checkboxes
        cat_label = QLabel("Categories:")
        cat_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(cat_label)

        self.category_checkboxes = {}
        grid = QGridLayout()
        for i, cat in enumerate(MaterialCategory):
            if cat == MaterialCategory.OTHER:
                continue
            cb = QCheckBox(cat.value)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_category_filter_changed)
            cb.setStyleSheet("color: white;")
            self.category_checkboxes[cat] = cb
            grid.addWidget(cb, i // 2, i % 2)
        layout.addLayout(grid)

        return group

    def _create_visual_group(self):
        """Create visual encoding controls"""
        group = QGroupBox("Visual Encoding")
        group.setStyleSheet(self._create_group_style())
        layout = QVBoxLayout(group)

        # Fill property
        fill_layout = QHBoxLayout()
        fill_label = QLabel("Color by:")
        fill_label.setStyleSheet("color: white;")
        self.fill_combo = QComboBox()
        for prop in MaterialProperty:
            self.fill_combo.addItem(MaterialProperty.get_display_name(prop), prop.value)
        self.fill_combo.currentIndexChanged.connect(self._on_fill_changed)
        self.fill_combo.setStyleSheet(self._get_combo_style())
        fill_layout.addWidget(fill_label)
        fill_layout.addWidget(self.fill_combo)
        layout.addLayout(fill_layout)

        # Scatter X axis
        x_layout = QHBoxLayout()
        x_label = QLabel("X Axis:")
        x_label.setStyleSheet("color: white;")
        self.x_combo = QComboBox()
        for prop in MaterialProperty:
            self.x_combo.addItem(MaterialProperty.get_display_name(prop), prop.value)
        self.x_combo.setCurrentIndex(0)  # Young's modulus
        self.x_combo.currentIndexChanged.connect(self._on_scatter_changed)
        self.x_combo.setStyleSheet(self._get_combo_style())
        x_layout.addWidget(x_label)
        x_layout.addWidget(self.x_combo)
        layout.addLayout(x_layout)

        # Scatter Y axis
        y_layout = QHBoxLayout()
        y_label = QLabel("Y Axis:")
        y_label.setStyleSheet("color: white;")
        self.y_combo = QComboBox()
        for prop in MaterialProperty:
            self.y_combo.addItem(MaterialProperty.get_display_name(prop), prop.value)
        self.y_combo.setCurrentIndex(1)  # Yield strength
        self.y_combo.currentIndexChanged.connect(self._on_scatter_changed)
        self.y_combo.setStyleSheet(self._get_combo_style())
        y_layout.addWidget(y_label)
        y_layout.addWidget(self.y_combo)
        layout.addLayout(y_layout)

        return group

    def _create_actions_group(self):
        """Create action buttons group"""
        group = QGroupBox("Actions")
        group.setStyleSheet(self._create_group_style())
        layout = QVBoxLayout(group)

        btn_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #5a6fd6);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7b8ef5, stop:1 #667eea);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6fd6, stop:1 #4e5fc0);
            }
        """

        # Add button
        self.add_btn = QPushButton("+ Add Material")
        self.add_btn.setStyleSheet(btn_style)
        self.add_btn.setToolTip("Add a new material (Ctrl+N)")
        self.add_btn.clicked.connect(self.add_material_requested.emit)
        layout.addWidget(self.add_btn)

        # Edit button
        self.edit_btn = QPushButton("Edit Material")
        self.edit_btn.setStyleSheet(btn_style)
        self.edit_btn.setToolTip("Edit selected material (Ctrl+E)")
        self.edit_btn.clicked.connect(self.edit_material_requested.emit)
        layout.addWidget(self.edit_btn)

        # Delete button
        self.delete_btn = QPushButton("Delete Material")
        self.delete_btn.setStyleSheet(btn_style.replace('#667eea', '#e74c3c').replace('#5a6fd6', '#c0392b'))
        self.delete_btn.setToolTip("Delete selected material (Del)")
        self.delete_btn.clicked.connect(self.delete_material_requested.emit)
        layout.addWidget(self.delete_btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #667eea;")
        layout.addWidget(sep)

        # Export button
        self.export_btn = QPushButton("Export Data")
        self.export_btn.setStyleSheet(btn_style)
        self.export_btn.setToolTip("Export materials to JSON (Ctrl+Shift+E)")
        self.export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.export_btn)

        # Import button
        self.import_btn = QPushButton("Import Data")
        self.import_btn.setStyleSheet(btn_style)
        self.import_btn.setToolTip("Import materials from JSON (Ctrl+Shift+I)")
        self.import_btn.clicked.connect(self.import_requested.emit)
        layout.addWidget(self.import_btn)

        # Duplicate button
        self.duplicate_btn = QPushButton("Duplicate Material")
        self.duplicate_btn.setStyleSheet(btn_style)
        self.duplicate_btn.setToolTip("Duplicate selected material (Ctrl+D)")
        self.duplicate_btn.clicked.connect(self.duplicate_requested.emit)
        layout.addWidget(self.duplicate_btn)

        return group

    def _get_combo_style(self):
        """Get combobox style"""
        return """
            QComboBox {
                background: rgba(40, 40, 60, 200);
                border: 1px solid #667eea;
                border-radius: 4px;
                color: white;
                padding: 5px;
                min-height: 25px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
            }
            QComboBox QAbstractItemView {
                background: rgba(40, 40, 60, 250);
                border: 1px solid #667eea;
                color: white;
                selection-background-color: #667eea;
            }
        """

    def _on_layout_changed(self, index):
        """Handle layout mode change"""
        mode = self.layout_combo.currentData()
        self.table.set_layout_mode(mode)

    def _on_search_changed(self, text):
        """Handle search text change"""
        self.table.set_search_filter(text)

    def _on_category_filter_changed(self):
        """Handle category filter change"""
        selected = [cat for cat, cb in self.category_checkboxes.items() if cb.isChecked()]
        self.table.set_category_filters(selected)

    def _on_fill_changed(self, index):
        """Handle fill property change"""
        prop = self.fill_combo.currentData()
        self.table.set_fill_property(prop)

    def _on_scatter_changed(self):
        """Handle scatter property change"""
        x_prop = self.x_combo.currentData()
        y_prop = self.y_combo.currentData()
        self.table.set_scatter_properties(x_prop, y_prop)

    def refresh_ai_status(self):
        """Refresh the AI API configuration status."""
        if hasattr(self, 'ai_widget'):
            self.ai_widget.refresh_api_status()
