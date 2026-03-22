"""
Biological Data Management Widget

A reusable widget providing CRUD operations for biological data with:
- Add, Edit, Remove, Export, Import, Duplicate, Reset buttons
- Keyboard shortcuts for all operations
- Item count display (current/total)
- Consistent theming from theme_constants
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence

from periodica_app.ui.theme_constants import (
    ACCENT_PRIMARY,
    ACCENT_DANGER,
    BG_CONTROL,
    TEXT_SECONDARY,
    TEXT_DISABLED,
    PADDING_NORMAL,
    BORDER_RADIUS_NORMAL,
)


class BiologicalDataManagement(QWidget):
    """
    Reusable widget for CRUD operations on biological data.

    Provides buttons for Add, Edit, Remove, Export, Import, Duplicate, and Reset
    operations with corresponding signals and keyboard shortcuts.

    Signals:
        add_requested: Emitted when Add button is clicked (Ctrl+N)
        edit_requested: Emitted when Edit button is clicked (Ctrl+E)
        ai_update_requested: Emitted when Update with AI button is clicked (Ctrl+U)
        remove_requested: Emitted when Remove button is clicked (Del)
        export_requested: Emitted when Export button is clicked (Ctrl+Shift+E)
        import_requested: Emitted when Import button is clicked (Ctrl+Shift+I)
        duplicate_requested: Emitted when Duplicate button is clicked (Ctrl+D)
        reset_requested: Emitted when Reset to Defaults button is clicked
    """

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

    def __init__(self, title: str = "Data Management", accent_color: str = None, parent: QWidget = None):
        """
        Initialize the BiologicalDataManagement widget.

        Args:
            title: Title for the group box (default: "Data Management")
            accent_color: Optional accent color for styling (default: uses ACCENT_PRIMARY from theme_constants)
            parent: Parent widget
        """
        super().__init__(parent)
        self._title = title
        self._accent_color = accent_color if accent_color else ACCENT_PRIMARY
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the group box
        self._group = QGroupBox(self._title)
        self._group.setStyleSheet(self._get_group_style())
        group_layout = QVBoxLayout(self._group)
        group_layout.setSpacing(PADDING_NORMAL)

        # First row: Add, Edit, Remove
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(PADDING_NORMAL)

        self.add_btn = self._create_button(
            "Add",
            "Add a new item (Ctrl+N)",
            "Ctrl+N"
        )
        self.add_btn.clicked.connect(self.add_requested.emit)
        row1_layout.addWidget(self.add_btn)

        self.edit_btn = self._create_button(
            "Edit",
            "Edit the selected item (Ctrl+E)",
            "Ctrl+E"
        )
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.edit_requested.emit)
        row1_layout.addWidget(self.edit_btn)

        self.ai_update_btn = self._create_button(
            "Update with AI",
            "Update selected item with AI (Ctrl+U)",
            "Ctrl+U"
        )
        self.ai_update_btn.setEnabled(False)
        self.ai_update_btn.clicked.connect(self.ai_update_requested.emit)
        row1_layout.addWidget(self.ai_update_btn)

        self.remove_btn = self._create_button(
            "Remove",
            "Remove the selected item (Del)",
            "Del"
        )
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_requested.emit)
        row1_layout.addWidget(self.remove_btn)

        group_layout.addLayout(row1_layout)

        # Second row: Export, Import, Duplicate
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(PADDING_NORMAL)

        self.export_btn = self._create_button(
            "Export",
            "Export selected item to file (Ctrl+Shift+E)",
            "Ctrl+Shift+E"
        )
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_requested.emit)
        row2_layout.addWidget(self.export_btn)

        self.import_btn = self._create_button(
            "Import",
            "Import item from file (Ctrl+Shift+I)",
            "Ctrl+Shift+I"
        )
        self.import_btn.clicked.connect(self.import_requested.emit)
        row2_layout.addWidget(self.import_btn)

        self.duplicate_btn = self._create_button(
            "Duplicate",
            "Create a copy of selected item (Ctrl+D)",
            "Ctrl+D"
        )
        self.duplicate_btn.setEnabled(False)
        self.duplicate_btn.clicked.connect(self.duplicate_requested.emit)
        row2_layout.addWidget(self.duplicate_btn)

        group_layout.addLayout(row2_layout)

        # Reset to Defaults button
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setStyleSheet(self._get_reset_button_style())
        self.reset_btn.setToolTip("Reset all data to defaults (cannot be undone)")
        self.reset_btn.clicked.connect(self.reset_requested.emit)
        group_layout.addWidget(self.reset_btn)

        # Item count label showing current/total items
        self.item_count_label = QLabel("Items: 0 / 0")
        self.item_count_label.setStyleSheet(f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 10px;
                margin-top: 5px;
            }}
        """)
        group_layout.addWidget(self.item_count_label)

        main_layout.addWidget(self._group)

    def _create_button(self, text: str, tooltip: str, shortcut: str) -> QPushButton:
        """
        Create a styled button with tooltip and shortcut.

        Args:
            text: Button text
            tooltip: Tooltip text
            shortcut: Keyboard shortcut string

        Returns:
            Configured QPushButton instance
        """
        btn = QPushButton(text)
        btn.setStyleSheet(self._get_button_style())
        btn.setToolTip(tooltip)
        btn.setShortcut(QKeySequence(shortcut))
        return btn

    def _get_group_style(self) -> str:
        """Get stylesheet for the group box."""
        return f"""
            QGroupBox {{
                color: white;
                border: 2px solid {self._accent_color};
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

    def _get_button_style(self) -> str:
        """Get stylesheet for action buttons."""
        return f"""
            QPushButton {{
                background: rgba(102, 126, 234, 150);
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: {BORDER_RADIUS_NORMAL}px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(102, 126, 234, 200);
            }}
            QPushButton:pressed {{
                background: rgba(102, 126, 234, 255);
            }}
            QPushButton:disabled {{
                background: {BG_CONTROL};
                color: {TEXT_DISABLED};
            }}
        """

    def _get_reset_button_style(self) -> str:
        """Get stylesheet for the reset button."""
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 {ACCENT_DANGER}, stop:1 #e53935);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #f44336, stop:1 #d32f2f);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #d32f2f, stop:1 #c62828);
            }}
        """

    # =========================================================================
    # Public Interface Methods
    # =========================================================================

    def set_item_selected(self, selected: bool) -> None:
        """
        Enable or disable buttons that require an item selection.

        When an item is selected, Edit, Update with AI, Remove, Export, and Duplicate
        buttons are enabled. When no item is selected, they are disabled.

        Args:
            selected: True if an item is selected, False otherwise
        """
        self.edit_btn.setEnabled(selected)
        self.ai_update_btn.setEnabled(selected)
        self.remove_btn.setEnabled(selected)
        self.export_btn.setEnabled(selected)
        self.duplicate_btn.setEnabled(selected)

    def update_item_count(self, current: int, total: int) -> None:
        """
        Update the item count display showing current/total items.

        Args:
            current: Number of currently visible/filtered items
            total: Total number of items in the collection
        """
        self.item_count_label.setText(f"Items: {current} / {total}")

    def set_title(self, title: str) -> None:
        """
        Update the group box title.

        Args:
            title: New title string
        """
        self._title = title
        self._group.setTitle(title)

    def set_accent_color(self, color: str) -> None:
        """
        Update the accent color used for styling.

        Args:
            color: New accent color (CSS color string)
        """
        self._accent_color = color
        self._group.setStyleSheet(self._get_group_style())
