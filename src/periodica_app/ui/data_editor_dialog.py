#!/usr/bin/env python3
"""
Data Editor Dialog
Reusable dialog widgets for editing JSON data across all tabs.
Supports add, edit, remove operations with dynamic form generation.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QWidget, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox,
    QComboBox, QListWidget, QListWidgetItem, QGroupBox, QScrollArea,
    QPushButton, QToolButton, QTextEdit, QPlainTextEdit, QSplitter,
    QMessageBox, QFileDialog, QFrame, QSizePolicy, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat

from periodica.data.data_manager import DataManager, DataCategory, get_data_manager


# ==================== Field Type Enum ====================

class FieldType(Enum):
    """Supported field types for schema definitions"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"
    COLOR = "color"
    CHOICE = "choice"


# ==================== Schema Field Definition ====================

@dataclass
class SchemaField:
    """
    Defines a single field in a data schema.

    Attributes:
        name: Internal field name (key in JSON)
        field_type: Type of the field (string, number, boolean, list, object)
        label: Display label for the field
        required: Whether the field is required
        default: Default value for the field
        validators: List of validation functions
        help_text: Help text shown as tooltip
        choices: List of choices for choice type
        min_value: Minimum value for numbers
        max_value: Maximum value for numbers
        decimals: Decimal places for numbers
        item_schema: Schema for list items (for list type)
        object_schema: Schema for nested object (for object type)
        readonly: Whether the field is read-only
        placeholder: Placeholder text for input
    """
    name: str
    field_type: Union[str, FieldType] = "string"
    label: Optional[str] = None
    required: bool = False
    default: Any = None
    validators: List[Callable] = field(default_factory=list)
    help_text: str = ""
    choices: List[str] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    decimals: int = 6
    item_schema: Optional[List['SchemaField']] = None
    object_schema: Optional[List['SchemaField']] = None
    readonly: bool = False
    placeholder: str = ""

    def __post_init__(self):
        if self.label is None:
            # Convert snake_case or camelCase to Title Case
            self.label = self._format_label(self.name)
        if isinstance(self.field_type, str):
            self.field_type = FieldType(self.field_type)

    def _format_label(self, name: str) -> str:
        """Convert field name to readable label"""
        # Handle snake_case
        name = name.replace('_', ' ')
        # Handle camelCase
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        return name.title()


# ==================== JSON Syntax Highlighter ====================

class JsonSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON preview"""

    def __init__(self, document):
        super().__init__(document)
        self._init_formats()

    def _init_formats(self):
        """Initialize text formats for different JSON elements"""
        # String format (green)
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#98c379"))

        # Number format (orange)
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#d19a66"))

        # Boolean/Null format (purple)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#c678dd"))

        # Key format (cyan)
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("#56b6c2"))

        # Brackets format (white)
        self.bracket_format = QTextCharFormat()
        self.bracket_format.setForeground(QColor("#abb2bf"))

    def highlightBlock(self, text):
        """Apply highlighting to a block of text"""
        # Highlight keys
        key_pattern = r'"([^"]+)"(?=\s*:)'
        for match in re.finditer(key_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.key_format)

        # Highlight string values
        string_pattern = r':\s*"([^"]*)"'
        for match in re.finditer(string_pattern, text):
            start = match.start() + text[match.start():].index('"')
            end = match.end()
            self.setFormat(start, end - start, self.string_format)

        # Highlight numbers
        number_pattern = r':\s*(-?\d+\.?\d*(?:[eE][+-]?\d+)?)'
        for match in re.finditer(number_pattern, text):
            start = match.start(1)
            length = len(match.group(1))
            self.setFormat(start, length, self.number_format)

        # Highlight booleans and null
        for keyword in ['true', 'false', 'null']:
            pattern = rf'\b{keyword}\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)


# ==================== Validators ====================

def required_validator(value: Any, field_name: str) -> Optional[str]:
    """Validate that a value is not empty"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return f"{field_name} is required"
    return None


def positive_number_validator(value: Any, field_name: str) -> Optional[str]:
    """Validate that a number is positive"""
    if value is not None and isinstance(value, (int, float)) and value < 0:
        return f"{field_name} must be positive"
    return None


def range_validator(min_val: float, max_val: float):
    """Create a range validator"""
    def validator(value: Any, field_name: str) -> Optional[str]:
        if value is not None and isinstance(value, (int, float)):
            if value < min_val or value > max_val:
                return f"{field_name} must be between {min_val} and {max_val}"
        return None
    return validator


def symbol_validator(value: Any, field_name: str) -> Optional[str]:
    """Validate that a symbol is 1-3 characters"""
    if value and isinstance(value, str):
        if len(value) > 3:
            return f"{field_name} must be 1-3 characters"
    return None


# ==================== Style Constants ====================

DIALOG_STYLE = """
    QDialog {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1a1a2e, stop:1 #16213e);
        color: white;
    }
    QLabel {
        color: white;
        font-size: 11px;
    }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {
        background: rgba(40, 40, 60, 200);
        color: white;
        border: 1px solid #667eea;
        border-radius: 4px;
        padding: 5px;
        font-size: 11px;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 2px solid #764ba2;
    }
    QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
        background: rgba(30, 30, 45, 150);
        color: rgba(255, 255, 255, 100);
    }
    QCheckBox {
        color: white;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #667eea;
        border-radius: 4px;
        background: rgba(40, 40, 60, 200);
    }
    QCheckBox::indicator:checked {
        background: #667eea;
    }
    QGroupBox {
        color: white;
        border: 1px solid #667eea;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 10px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
    QListWidget {
        background: rgba(40, 40, 60, 200);
        color: white;
        border: 1px solid #667eea;
        border-radius: 4px;
    }
    QListWidget::item {
        padding: 5px;
        border-bottom: 1px solid rgba(102, 126, 234, 50);
    }
    QListWidget::item:selected {
        background: rgba(102, 126, 234, 150);
    }
    QListWidget::item:hover {
        background: rgba(102, 126, 234, 80);
    }
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #667eea, stop:1 #764ba2);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
        font-weight: bold;
        font-size: 11px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #7688f0, stop:1 #8658b8);
    }
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #5567d0, stop:1 #653a92);
    }
    QPushButton:disabled {
        background: rgba(80, 80, 100, 150);
        color: rgba(255, 255, 255, 100);
    }
    QScrollArea {
        border: none;
        background: transparent;
    }
    QScrollBar:vertical {
        background: rgba(40, 40, 60, 100);
        width: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: rgba(102, 126, 234, 150);
        border-radius: 5px;
        min-height: 20px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
"""

BUTTON_SECONDARY_STYLE = """
    QPushButton {
        background: rgba(60, 60, 80, 200);
        border: 1px solid #667eea;
    }
    QPushButton:hover {
        background: rgba(80, 80, 100, 200);
    }
"""

BUTTON_DANGER_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #e74c3c, stop:1 #c0392b);
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #ec7063, stop:1 #d35400);
    }
"""

BUTTON_SUCCESS_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #27ae60, stop:1 #1e8449);
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #2ecc71, stop:1 #27ae60);
    }
"""


# ==================== Data Editor Dialog ====================

class DataEditorDialog(QDialog):
    """
    Dialog for editing a single data item.
    Dynamically generates form fields based on schema.
    """

    # Signal emitted when data is saved
    data_saved = Signal(dict)

    def __init__(self, schema: List[SchemaField], data: Optional[Dict] = None,
                 title: str = "Edit Data", parent=None):
        """
        Initialize the data editor dialog.

        Args:
            schema: List of SchemaField defining the form
            data: Existing data to edit (None for new item)
            title: Dialog title
            parent: Parent widget
        """
        super().__init__(parent)
        self.schema = schema
        self.original_data = data or {}
        self.field_widgets: Dict[str, QWidget] = {}
        self.is_new = data is None

        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setStyleSheet(DIALOG_STYLE)

        self._setup_ui()
        self._populate_data()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Create splitter for form and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Form
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title_label = QLabel("Edit Fields")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #4fc3f7; margin-bottom: 10px;")
        form_layout.addWidget(title_label)

        # Scrollable form area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_widget = QWidget()
        self.form_layout = QVBoxLayout(form_widget)
        self.form_layout.setContentsMargins(5, 5, 5, 5)
        self.form_layout.setSpacing(10)

        # Generate form fields
        self._generate_form_fields()

        self.form_layout.addStretch()
        scroll.setWidget(form_widget)
        form_layout.addWidget(scroll)

        # Validation status
        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("color: #e74c3c; font-size: 10px;")
        self.validation_label.setWordWrap(True)
        form_layout.addWidget(self.validation_label)

        splitter.addWidget(form_container)

        # Right side: JSON Preview
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        preview_title = QLabel("JSON Preview")
        preview_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        preview_title.setStyleSheet("color: #4fc3f7; margin-bottom: 10px;")
        preview_layout.addWidget(preview_title)

        self.json_preview = QPlainTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setFont(QFont("Consolas", 10))
        self.json_preview.setStyleSheet("""
            QPlainTextEdit {
                background: rgba(30, 30, 45, 250);
                color: #abb2bf;
                border: 1px solid #667eea;
                border-radius: 4px;
            }
        """)
        self.highlighter = JsonSyntaxHighlighter(self.json_preview.document())
        preview_layout.addWidget(self.json_preview)

        splitter.addWidget(preview_container)
        splitter.setSizes([500, 300])

        layout.addWidget(splitter)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(BUTTON_SECONDARY_STYLE)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(BUTTON_SUCCESS_STYLE)
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _generate_form_fields(self):
        """Generate form fields based on schema"""
        for field in self.schema:
            widget = self._create_field_widget(field)
            if widget:
                self.field_widgets[field.name] = widget

    def _create_field_widget(self, field: SchemaField) -> Optional[QWidget]:
        """Create a widget for a schema field"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setSpacing(3)

        # Label with required indicator
        label_text = field.label
        if field.required:
            label_text += " *"
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold;")
        if field.help_text:
            label.setToolTip(field.help_text)
        layout.addWidget(label)

        # Create appropriate widget based on type
        if field.field_type == FieldType.STRING:
            widget = self._create_string_widget(field)
        elif field.field_type == FieldType.NUMBER:
            widget = self._create_number_widget(field)
        elif field.field_type == FieldType.INTEGER:
            widget = self._create_integer_widget(field)
        elif field.field_type == FieldType.BOOLEAN:
            widget = self._create_boolean_widget(field)
        elif field.field_type == FieldType.LIST:
            widget = self._create_list_widget(field)
        elif field.field_type == FieldType.OBJECT:
            widget = self._create_object_widget(field)
        elif field.field_type == FieldType.COLOR:
            widget = self._create_color_widget(field)
        elif field.field_type == FieldType.CHOICE:
            widget = self._create_choice_widget(field)
        else:
            widget = self._create_string_widget(field)

        if widget:
            layout.addWidget(widget)
            self.form_layout.addWidget(container)

            # Connect change signal for live preview
            self._connect_change_signal(widget, field.field_type)

        return widget

    def _create_string_widget(self, field: SchemaField) -> QLineEdit:
        """Create a string input widget"""
        widget = QLineEdit()
        widget.setPlaceholderText(field.placeholder or f"Enter {field.label.lower()}")
        widget.setReadOnly(field.readonly)
        return widget

    def _create_number_widget(self, field: SchemaField) -> QDoubleSpinBox:
        """Create a number input widget"""
        widget = QDoubleSpinBox()
        widget.setDecimals(field.decimals)
        widget.setMinimum(field.min_value if field.min_value is not None else -1e10)
        widget.setMaximum(field.max_value if field.max_value is not None else 1e10)
        widget.setReadOnly(field.readonly)
        # Allow scientific notation
        widget.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        return widget

    def _create_integer_widget(self, field: SchemaField) -> QSpinBox:
        """Create an integer input widget"""
        widget = QSpinBox()
        widget.setMinimum(int(field.min_value) if field.min_value is not None else -2147483647)
        widget.setMaximum(int(field.max_value) if field.max_value is not None else 2147483647)
        widget.setReadOnly(field.readonly)
        return widget

    def _create_boolean_widget(self, field: SchemaField) -> QCheckBox:
        """Create a boolean input widget"""
        widget = QCheckBox(field.label)
        widget.setEnabled(not field.readonly)
        return widget

    def _create_list_widget(self, field: SchemaField) -> QWidget:
        """Create a list editor widget"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # List widget
        list_widget = QListWidget()
        list_widget.setMaximumHeight(120)
        list_widget.setProperty("field_name", field.name)
        layout.addWidget(list_widget)

        # Buttons for list management
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        add_btn = QPushButton("+")
        add_btn.setFixedWidth(30)
        add_btn.setStyleSheet(BUTTON_SUCCESS_STYLE)
        add_btn.clicked.connect(lambda: self._add_list_item(list_widget, field))
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("-")
        remove_btn.setFixedWidth(30)
        remove_btn.setStyleSheet(BUTTON_DANGER_STYLE)
        remove_btn.clicked.connect(lambda: self._remove_list_item(list_widget))
        btn_layout.addWidget(remove_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet(BUTTON_SECONDARY_STYLE)
        edit_btn.clicked.connect(lambda: self._edit_list_item(list_widget, field))
        btn_layout.addWidget(edit_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        container.list_widget = list_widget
        return container

    def _create_object_widget(self, field: SchemaField) -> QGroupBox:
        """Create a nested object editor widget"""
        group = QGroupBox(field.label)
        layout = QFormLayout(group)
        layout.setContentsMargins(10, 15, 10, 10)

        if field.object_schema:
            group.field_widgets = {}
            for sub_field in field.object_schema:
                sub_widget = self._create_field_widget_simple(sub_field)
                if sub_widget:
                    layout.addRow(sub_field.label + ":", sub_widget)
                    group.field_widgets[sub_field.name] = sub_widget
                    self._connect_change_signal(sub_widget, sub_field.field_type)

        return group

    def _create_field_widget_simple(self, field: SchemaField) -> Optional[QWidget]:
        """Create a simple widget without container"""
        if field.field_type == FieldType.STRING:
            return self._create_string_widget(field)
        elif field.field_type == FieldType.NUMBER:
            return self._create_number_widget(field)
        elif field.field_type == FieldType.INTEGER:
            return self._create_integer_widget(field)
        elif field.field_type == FieldType.BOOLEAN:
            widget = QCheckBox()
            widget.setEnabled(not field.readonly)
            return widget
        elif field.field_type == FieldType.CHOICE:
            return self._create_choice_widget(field)
        return None

    def _create_color_widget(self, field: SchemaField) -> QWidget:
        """Create a color picker widget"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText("#RRGGBB")
        layout.addWidget(line_edit)

        color_preview = QFrame()
        color_preview.setFixedSize(30, 30)
        color_preview.setStyleSheet("background: #667eea; border-radius: 4px;")
        layout.addWidget(color_preview)

        def update_preview():
            color = line_edit.text()
            if color.startswith('#') and len(color) in [4, 7]:
                color_preview.setStyleSheet(f"background: {color}; border-radius: 4px;")

        line_edit.textChanged.connect(update_preview)

        container.line_edit = line_edit
        container.color_preview = color_preview
        return container

    def _create_choice_widget(self, field: SchemaField) -> QComboBox:
        """Create a choice/dropdown widget"""
        widget = QComboBox()
        widget.addItems(field.choices)
        widget.setEnabled(not field.readonly)
        return widget

    def _connect_change_signal(self, widget: QWidget, field_type: FieldType):
        """Connect appropriate change signal for live preview"""
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._update_preview)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.valueChanged.connect(self._update_preview)
        elif isinstance(widget, QCheckBox):
            widget.stateChanged.connect(self._update_preview)
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(self._update_preview)
        elif hasattr(widget, 'list_widget'):
            widget.list_widget.model().rowsInserted.connect(self._update_preview)
            widget.list_widget.model().rowsRemoved.connect(self._update_preview)
        elif hasattr(widget, 'line_edit'):
            widget.line_edit.textChanged.connect(self._update_preview)

    def _add_list_item(self, list_widget: QListWidget, field: SchemaField):
        """Add an item to a list widget"""
        if field.item_schema:
            # Complex item - open editor dialog
            dialog = DataEditorDialog(field.item_schema, title="Add Item", parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                item = QListWidgetItem(self._format_list_item(data))
                item.setData(Qt.ItemDataRole.UserRole, data)
                list_widget.addItem(item)
                self._update_preview()
        else:
            # Simple string item
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "Add Item", "Enter value:")
            if ok and text:
                list_widget.addItem(text)
                self._update_preview()

    def _remove_list_item(self, list_widget: QListWidget):
        """Remove selected item from list widget"""
        current = list_widget.currentRow()
        if current >= 0:
            list_widget.takeItem(current)
            self._update_preview()

    def _edit_list_item(self, list_widget: QListWidget, field: SchemaField):
        """Edit selected item in list widget"""
        current_item = list_widget.currentItem()
        if not current_item:
            return

        if field.item_schema:
            data = current_item.data(Qt.ItemDataRole.UserRole) or {}
            dialog = DataEditorDialog(field.item_schema, data=data, title="Edit Item", parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_data = dialog.get_data()
                current_item.setText(self._format_list_item(new_data))
                current_item.setData(Qt.ItemDataRole.UserRole, new_data)
                self._update_preview()
        else:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "Edit Item", "Enter value:", text=current_item.text())
            if ok and text:
                current_item.setText(text)
                self._update_preview()

    def _format_list_item(self, data: dict) -> str:
        """Format a complex list item for display"""
        if isinstance(data, dict):
            # Show first 2-3 key values
            parts = []
            for key in list(data.keys())[:3]:
                parts.append(f"{key}: {data[key]}")
            return ", ".join(parts)
        return str(data)

    def _populate_data(self):
        """Populate form fields with existing data"""
        for field in self.schema:
            if field.name in self.original_data:
                value = self.original_data[field.name]
                self._set_field_value(field, value)
            elif field.default is not None:
                self._set_field_value(field, field.default)

        self._update_preview()

    def _set_field_value(self, field: SchemaField, value: Any):
        """Set a field's widget value"""
        widget = self.field_widgets.get(field.name)
        if not widget:
            return

        if field.field_type == FieldType.STRING:
            widget.setText(str(value) if value is not None else "")
        elif field.field_type == FieldType.NUMBER:
            widget.setValue(float(value) if value is not None else 0.0)
        elif field.field_type == FieldType.INTEGER:
            widget.setValue(int(value) if value is not None else 0)
        elif field.field_type == FieldType.BOOLEAN:
            widget.setChecked(bool(value))
        elif field.field_type == FieldType.LIST:
            list_widget = widget.list_widget
            list_widget.clear()
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        list_item = QListWidgetItem(self._format_list_item(item))
                        list_item.setData(Qt.ItemDataRole.UserRole, item)
                        list_widget.addItem(list_item)
                    else:
                        list_widget.addItem(str(item))
        elif field.field_type == FieldType.OBJECT:
            if isinstance(value, dict) and hasattr(widget, 'field_widgets'):
                for sub_field in field.object_schema:
                    if sub_field.name in value:
                        sub_widget = widget.field_widgets.get(sub_field.name)
                        if sub_widget:
                            self._set_widget_value(sub_widget, sub_field.field_type, value[sub_field.name])
        elif field.field_type == FieldType.COLOR:
            widget.line_edit.setText(str(value) if value else "")
        elif field.field_type == FieldType.CHOICE:
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)

    def _set_widget_value(self, widget: QWidget, field_type: FieldType, value: Any):
        """Set value for a simple widget"""
        if isinstance(widget, QLineEdit):
            widget.setText(str(value) if value is not None else "")
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value) if value is not None else 0.0)
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value) if value is not None else 0)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)

    def get_data(self) -> Dict[str, Any]:
        """Get the current form data as a dictionary"""
        data = {}

        for field in self.schema:
            widget = self.field_widgets.get(field.name)
            if not widget:
                continue

            value = self._get_field_value(field, widget)

            # Only include non-empty values or required fields
            if value is not None or field.required:
                data[field.name] = value

        return data

    def _get_field_value(self, field: SchemaField, widget: QWidget) -> Any:
        """Get value from a field widget"""
        if field.field_type == FieldType.STRING:
            return widget.text().strip() or None
        elif field.field_type == FieldType.NUMBER:
            return widget.value()
        elif field.field_type == FieldType.INTEGER:
            return widget.value()
        elif field.field_type == FieldType.BOOLEAN:
            return widget.isChecked()
        elif field.field_type == FieldType.LIST:
            list_widget = widget.list_widget
            items = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    items.append(data)
                else:
                    items.append(item.text())
            return items
        elif field.field_type == FieldType.OBJECT:
            if hasattr(widget, 'field_widgets'):
                obj = {}
                for sub_field in field.object_schema:
                    sub_widget = widget.field_widgets.get(sub_field.name)
                    if sub_widget:
                        obj[sub_field.name] = self._get_widget_value(sub_widget, sub_field.field_type)
                return obj
            return None
        elif field.field_type == FieldType.COLOR:
            return widget.line_edit.text().strip() or None
        elif field.field_type == FieldType.CHOICE:
            return widget.currentText()

        return None

    def _get_widget_value(self, widget: QWidget, field_type: FieldType) -> Any:
        """Get value from a simple widget"""
        if isinstance(widget, QLineEdit):
            return widget.text().strip() or None
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        return None

    def _update_preview(self):
        """Update the JSON preview"""
        data = self.get_data()
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            self.json_preview.setPlainText(json_str)
        except Exception as e:
            self.json_preview.setPlainText(f"Error generating JSON: {e}")

    def validate(self) -> List[str]:
        """Validate the form data"""
        errors = []

        for field in self.schema:
            widget = self.field_widgets.get(field.name)
            if not widget:
                continue

            value = self._get_field_value(field, widget)

            # Check required
            if field.required:
                error = required_validator(value, field.label)
                if error:
                    errors.append(error)

            # Run custom validators
            for validator in field.validators:
                error = validator(value, field.label)
                if error:
                    errors.append(error)

        return errors

    def _on_save(self):
        """Handle save button click"""
        errors = self.validate()

        if errors:
            self.validation_label.setText("\n".join(errors))
            return

        self.validation_label.setText("")
        data = self.get_data()
        self.data_saved.emit(data)
        self.accept()


# ==================== Data List Dialog ====================

class DataListDialog(QDialog):
    """
    Dialog for managing a list of data items.
    Supports add, edit, remove, import, export, and reset operations.
    """

    # Signal emitted when data changes
    data_changed = Signal()

    def __init__(self, category: DataCategory, schema: List[SchemaField],
                 data_manager: Optional[DataManager] = None,
                 title: str = "Manage Data", display_field: str = "Name",
                 parent=None):
        """
        Initialize the data list dialog.

        Args:
            category: DataCategory for this data type
            schema: Schema for individual items
            data_manager: DataManager instance (uses global if None)
            title: Dialog title
            display_field: Field to show in list
            parent: Parent widget
        """
        super().__init__(parent)
        self.category = category
        self.schema = schema
        self.data_manager = data_manager or get_data_manager()
        self.display_field = display_field

        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)
        self.setStyleSheet(DIALOG_STYLE)

        self._setup_ui()
        self._load_items()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        title_label = QLabel(f"Manage {self.category.value.title()}")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #4fc3f7;")
        layout.addWidget(title_label)

        # Search/filter
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter items...")
        self.search_edit.textChanged.connect(self._filter_items)
        search_layout.addWidget(self.search_edit)

        layout.addLayout(search_layout)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(self._on_edit)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        # Item count label
        self.count_label = QLabel("0 items")
        self.count_label.setStyleSheet("color: rgba(255,255,255,150); font-size: 10px;")
        layout.addWidget(self.count_label)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        add_btn = QPushButton("Add")
        add_btn.setStyleSheet(BUTTON_SUCCESS_STYLE)
        add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._on_edit)
        self.edit_btn.setEnabled(False)
        btn_layout.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setStyleSheet(BUTTON_DANGER_STYLE)
        self.remove_btn.clicked.connect(self._on_remove)
        self.remove_btn.setEnabled(False)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()

        import_btn = QPushButton("Import")
        import_btn.setStyleSheet(BUTTON_SECONDARY_STYLE)
        import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(import_btn)

        export_btn = QPushButton("Export")
        export_btn.setStyleSheet(BUTTON_SECONDARY_STYLE)
        export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(export_btn)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setStyleSheet(BUTTON_DANGER_STYLE)
        reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(reset_btn)

        layout.addLayout(btn_layout)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(BUTTON_SECONDARY_STYLE)
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)

        layout.addLayout(close_layout)

    def _load_items(self):
        """Load items from data manager"""
        self.list_widget.clear()

        items = self.data_manager.get_all_items(self.category)
        for item in items:
            display_text = item.get(self.display_field, item.get('_filename', 'Unknown'))
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(list_item)

        self._update_count()

    def _filter_items(self, text: str):
        """Filter list items by search text"""
        text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            data = item.data(Qt.ItemDataRole.UserRole) or {}

            # Search in multiple fields
            match = False
            for key, value in data.items():
                if isinstance(value, str) and text in value.lower():
                    match = True
                    break

            item.setHidden(not match and text != "")

    def _update_count(self):
        """Update the item count label"""
        visible = sum(1 for i in range(self.list_widget.count())
                     if not self.list_widget.item(i).isHidden())
        total = self.list_widget.count()

        if visible == total:
            self.count_label.setText(f"{total} items")
        else:
            self.count_label.setText(f"{visible} of {total} items")

    def _on_selection_changed(self):
        """Handle selection change"""
        has_selection = self.list_widget.currentItem() is not None
        self.edit_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)

    def _on_add(self):
        """Handle add button"""
        dialog = DataEditorDialog(self.schema, title="Add New Item", parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            # Generate filename from name or first field
            filename = data.get('Name', data.get('name', data.get('symbol', 'new_item')))
            filename = re.sub(r'[^\w\-_]', '', filename)

            if self.data_manager.add_item(self.category, filename, data):
                self._load_items()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Error", "Failed to add item. It may already exist.")

    def _on_edit(self):
        """Handle edit button"""
        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        data = current_item.data(Qt.ItemDataRole.UserRole)
        filename = data.get('_filename', '')

        # Remove internal field before editing
        edit_data = {k: v for k, v in data.items() if not k.startswith('_')}

        dialog = DataEditorDialog(self.schema, data=edit_data, title="Edit Item", parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()

            if self.data_manager.edit_item(self.category, filename, new_data):
                self._load_items()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Error", "Failed to update item.")

    def _on_remove(self):
        """Handle remove button"""
        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        data = current_item.data(Qt.ItemDataRole.UserRole)
        name = data.get(self.display_field, data.get('_filename', 'Unknown'))
        filename = data.get('_filename', '')

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.data_manager.remove_item(self.category, filename):
                self._load_items()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Error", "Failed to remove item.")

    def _on_import(self):
        """Handle import button"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import JSON File",
            "", "JSON Files (*.json);;All Files (*)"
        )

        if filepath:
            if self.data_manager.import_item(self.category, filepath):
                self._load_items()
                self.data_changed.emit()
                QMessageBox.information(self, "Success", "Item imported successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to import item.")

    def _on_export(self):
        """Handle export button"""
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select an item to export.")
            return

        data = current_item.data(Qt.ItemDataRole.UserRole)
        filename = data.get('_filename', 'export')

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export JSON File",
            f"{filename}.json", "JSON Files (*.json);;All Files (*)"
        )

        if filepath:
            if self.data_manager.export_item(self.category, filename, filepath):
                QMessageBox.information(self, "Success", "Item exported successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to export item.")

    def _on_reset(self):
        """Handle reset to defaults"""
        reply = QMessageBox.question(
            self, "Confirm Reset",
            f"Are you sure you want to reset all {self.category.value} to defaults?\n"
            "This will delete any custom items and restore original data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.data_manager.reset_category(self.category):
                self._load_items()
                self.data_changed.emit()
                QMessageBox.information(self, "Success", "Data reset to defaults.")
            else:
                QMessageBox.warning(self, "Error", "Failed to reset data.")


# ==================== Pre-defined Schemas ====================

# Element Schema
ELEMENT_SCHEMA = [
    SchemaField("symbol", FieldType.STRING, "Symbol", required=True,
                validators=[symbol_validator], help_text="1-3 character element symbol"),
    SchemaField("name", FieldType.STRING, "Name", required=True,
                help_text="Full element name"),
    SchemaField("atomic_number", FieldType.INTEGER, "Atomic Number", required=True,
                min_value=1, max_value=200, help_text="Number of protons"),
    SchemaField("atomic_mass", FieldType.NUMBER, "Atomic Mass",
                min_value=0, decimals=6, help_text="Atomic mass in amu"),
    SchemaField("block", FieldType.CHOICE, "Block", choices=["s", "p", "d", "f"],
                help_text="Orbital block"),
    SchemaField("period", FieldType.INTEGER, "Period", min_value=1, max_value=10),
    SchemaField("group", FieldType.INTEGER, "Group", min_value=0, max_value=18),
    SchemaField("ionization_energy", FieldType.NUMBER, "Ionization Energy",
                min_value=0, decimals=3, help_text="First ionization energy in eV"),
    SchemaField("electronegativity", FieldType.NUMBER, "Electronegativity",
                min_value=0, max_value=5, decimals=2, help_text="Pauling electronegativity"),
    SchemaField("atomic_radius", FieldType.NUMBER, "Atomic Radius",
                min_value=0, decimals=1, help_text="Atomic radius in pm"),
    SchemaField("melting_point", FieldType.NUMBER, "Melting Point",
                decimals=2, help_text="Melting point in K"),
    SchemaField("boiling_point", FieldType.NUMBER, "Boiling Point",
                decimals=2, help_text="Boiling point in K"),
    SchemaField("density", FieldType.NUMBER, "Density",
                min_value=0, decimals=6, help_text="Density in g/cm3"),
    SchemaField("electron_affinity", FieldType.NUMBER, "Electron Affinity",
                decimals=2, help_text="Electron affinity in kJ/mol"),
    SchemaField("valence_electrons", FieldType.INTEGER, "Valence Electrons",
                min_value=0, max_value=8),
    SchemaField("electron_configuration", FieldType.STRING, "Electron Configuration",
                help_text="Electron configuration notation"),
    SchemaField("primary_emission_wavelength", FieldType.NUMBER, "Primary Emission Wavelength",
                min_value=0, decimals=1, help_text="Primary emission wavelength in nm"),
    SchemaField("isotopes", FieldType.LIST, "Isotopes",
                item_schema=[
                    SchemaField("mass_number", FieldType.INTEGER, "Mass Number", required=True),
                    SchemaField("neutrons", FieldType.INTEGER, "Neutrons"),
                    SchemaField("abundance", FieldType.NUMBER, "Abundance (%)", decimals=4),
                    SchemaField("is_stable", FieldType.BOOLEAN, "Stable"),
                    SchemaField("half_life", FieldType.STRING, "Half Life"),
                ], help_text="List of isotopes"),
]

# Quark Schema (for quarks and fundamental particles)
QUARK_SCHEMA = [
    SchemaField("Name", FieldType.STRING, "Name", required=True,
                help_text="Particle name"),
    SchemaField("Symbol", FieldType.STRING, "Symbol", required=True,
                help_text="Particle symbol"),
    SchemaField("Type", FieldType.STRING, "Type", default="Subatomic Particle"),
    SchemaField("Classification", FieldType.LIST, "Classification",
                help_text="Particle classifications (Fermion, Quark, etc.)"),
    SchemaField("Charge_e", FieldType.NUMBER, "Charge (e)", decimals=10,
                help_text="Electric charge in units of e"),
    SchemaField("Mass_MeVc2", FieldType.NUMBER, "Mass (MeV/c2)", decimals=10,
                min_value=0, help_text="Mass in MeV/c2"),
    SchemaField("Mass_kg", FieldType.NUMBER, "Mass (kg)", decimals=40,
                min_value=0, help_text="Mass in kg"),
    SchemaField("Mass_amu", FieldType.NUMBER, "Mass (amu)", decimals=12,
                min_value=0, help_text="Mass in atomic mass units"),
    SchemaField("Spin_hbar", FieldType.NUMBER, "Spin (hbar)", decimals=2,
                help_text="Spin in units of hbar"),
    SchemaField("MagneticDipoleMoment_J_T", FieldType.NUMBER, "Magnetic Dipole Moment (J/T)",
                decimals=40, help_text="Magnetic dipole moment"),
    SchemaField("LeptonNumber_L", FieldType.INTEGER, "Lepton Number"),
    SchemaField("BaryonNumber_B", FieldType.NUMBER, "Baryon Number", decimals=10),
    SchemaField("Isospin_I", FieldType.NUMBER, "Isospin (I)", decimals=2),
    SchemaField("Isospin_I3", FieldType.NUMBER, "Isospin (I3)", decimals=2),
    SchemaField("Parity_P", FieldType.INTEGER, "Parity"),
    SchemaField("Composition", FieldType.LIST, "Composition",
                item_schema=[
                    SchemaField("Constituent", FieldType.STRING, "Constituent", required=True),
                    SchemaField("Count", FieldType.INTEGER, "Count", required=True),
                    SchemaField("Charge_e", FieldType.NUMBER, "Charge (e)", decimals=10),
                ], help_text="Quark composition"),
    SchemaField("Stability", FieldType.CHOICE, "Stability",
                choices=["Stable", "Unstable", "Unknown"]),
    SchemaField("HalfLife_s", FieldType.NUMBER, "Half Life (s)", decimals=20),
    SchemaField("DecayProducts", FieldType.LIST, "Decay Products",
                help_text="List of decay product particles"),
    SchemaField("Antiparticle", FieldType.OBJECT, "Antiparticle",
                object_schema=[
                    SchemaField("Name", FieldType.STRING, "Name"),
                    SchemaField("Symbol", FieldType.STRING, "Symbol"),
                ]),
    SchemaField("InteractionForces", FieldType.LIST, "Interaction Forces",
                help_text="Forces the particle interacts with"),
]

# Subatomic Schema (for composite particles like protons, neutrons)
SUBATOMIC_SCHEMA = [
    SchemaField("Name", FieldType.STRING, "Name", required=True,
                help_text="Particle name"),
    SchemaField("Symbol", FieldType.STRING, "Symbol", required=True,
                help_text="Particle symbol"),
    SchemaField("Type", FieldType.STRING, "Type", default="Subatomic Particle"),
    SchemaField("Classification", FieldType.LIST, "Classification",
                help_text="Particle classifications"),
    SchemaField("Charge_e", FieldType.NUMBER, "Charge (e)", decimals=10,
                help_text="Electric charge in units of e"),
    SchemaField("Mass_MeVc2", FieldType.NUMBER, "Mass (MeV/c2)", decimals=10,
                min_value=0, help_text="Mass in MeV/c2"),
    SchemaField("Mass_kg", FieldType.NUMBER, "Mass (kg)", decimals=40,
                min_value=0, help_text="Mass in kg"),
    SchemaField("Mass_amu", FieldType.NUMBER, "Mass (amu)", decimals=12,
                min_value=0, help_text="Mass in atomic mass units"),
    SchemaField("Spin_hbar", FieldType.NUMBER, "Spin (hbar)", decimals=2,
                help_text="Spin in units of hbar"),
    SchemaField("MagneticDipoleMoment_J_T", FieldType.NUMBER, "Magnetic Dipole Moment (J/T)",
                decimals=40),
    SchemaField("LeptonNumber_L", FieldType.INTEGER, "Lepton Number"),
    SchemaField("BaryonNumber_B", FieldType.NUMBER, "Baryon Number", decimals=10),
    SchemaField("Isospin_I", FieldType.NUMBER, "Isospin (I)", decimals=2),
    SchemaField("Isospin_I3", FieldType.NUMBER, "Isospin (I3)", decimals=2),
    SchemaField("Parity_P", FieldType.INTEGER, "Parity"),
    SchemaField("Composition", FieldType.LIST, "Composition",
                item_schema=[
                    SchemaField("Constituent", FieldType.STRING, "Constituent", required=True),
                    SchemaField("Count", FieldType.INTEGER, "Count", required=True),
                    SchemaField("Charge_e", FieldType.NUMBER, "Charge (e)", decimals=10),
                ]),
    SchemaField("Stability", FieldType.CHOICE, "Stability",
                choices=["Stable", "Unstable", "Unknown"]),
    SchemaField("HalfLife_s", FieldType.NUMBER, "Half Life (s)", decimals=20),
    SchemaField("DecayProducts", FieldType.LIST, "Decay Products"),
    SchemaField("Antiparticle", FieldType.OBJECT, "Antiparticle",
                object_schema=[
                    SchemaField("Name", FieldType.STRING, "Name"),
                    SchemaField("Symbol", FieldType.STRING, "Symbol"),
                ]),
    SchemaField("InteractionForces", FieldType.LIST, "Interaction Forces"),
]

# Molecule Schema
MOLECULE_SCHEMA = [
    SchemaField("Name", FieldType.STRING, "Name", required=True,
                help_text="Molecule name"),
    SchemaField("Formula", FieldType.STRING, "Formula", required=True,
                help_text="Chemical formula"),
    SchemaField("IUPAC_Name", FieldType.STRING, "IUPAC Name",
                help_text="Official IUPAC name"),
    SchemaField("MolecularMass_amu", FieldType.NUMBER, "Molecular Mass (amu)",
                min_value=0, decimals=3),
    SchemaField("MolecularMass_g_mol", FieldType.NUMBER, "Molecular Mass (g/mol)",
                min_value=0, decimals=3),
    SchemaField("BondType", FieldType.CHOICE, "Bond Type",
                choices=["Covalent", "Ionic", "Metallic", "Hydrogen", "Van der Waals"]),
    SchemaField("Geometry", FieldType.STRING, "Geometry",
                help_text="Molecular geometry (Linear, Bent, Tetrahedral, etc.)"),
    SchemaField("BondAngle_deg", FieldType.NUMBER, "Bond Angle (deg)",
                min_value=0, max_value=360, decimals=1),
    SchemaField("Polarity", FieldType.CHOICE, "Polarity",
                choices=["Polar", "Nonpolar", "Ionic"]),
    SchemaField("MeltingPoint_K", FieldType.NUMBER, "Melting Point (K)", decimals=2),
    SchemaField("BoilingPoint_K", FieldType.NUMBER, "Boiling Point (K)", decimals=2),
    SchemaField("Density_g_cm3", FieldType.NUMBER, "Density (g/cm3)",
                min_value=0, decimals=4),
    SchemaField("State_STP", FieldType.CHOICE, "State at STP",
                choices=["Solid", "Liquid", "Gas", "Plasma"]),
    SchemaField("Composition", FieldType.LIST, "Composition",
                item_schema=[
                    SchemaField("Element", FieldType.STRING, "Element", required=True),
                    SchemaField("Count", FieldType.INTEGER, "Count", required=True, min_value=1),
                ], help_text="Elemental composition"),
    SchemaField("Bonds", FieldType.LIST, "Bonds",
                item_schema=[
                    SchemaField("From", FieldType.STRING, "From Atom", required=True),
                    SchemaField("To", FieldType.STRING, "To Atom", required=True),
                    SchemaField("Type", FieldType.CHOICE, "Bond Type",
                               choices=["Single", "Double", "Triple", "Aromatic"]),
                    SchemaField("Length_pm", FieldType.NUMBER, "Length (pm)", min_value=0),
                    SchemaField("Index", FieldType.INTEGER, "Index"),
                ], help_text="Bond information"),
    SchemaField("DipoleMoment_D", FieldType.NUMBER, "Dipole Moment (D)",
                min_value=0, decimals=2),
    SchemaField("ElectronConfiguration", FieldType.STRING, "Electron Configuration"),
    SchemaField("Applications", FieldType.LIST, "Applications",
                help_text="Common applications"),
    SchemaField("Category", FieldType.CHOICE, "Category",
                choices=["Organic", "Inorganic", "Polymer", "Biomolecule"]),
    SchemaField("Color", FieldType.COLOR, "Display Color",
                help_text="Color for visualization (#RRGGBB)"),
]


# ==================== Helper Functions ====================

def get_schema_for_category(category: DataCategory) -> List[SchemaField]:
    """Get the appropriate schema for a data category"""
    schema_map = {
        DataCategory.ELEMENTS: ELEMENT_SCHEMA,
        DataCategory.QUARKS: QUARK_SCHEMA,
        DataCategory.ANTIQUARKS: QUARK_SCHEMA,
        DataCategory.SUBATOMIC: SUBATOMIC_SCHEMA,
        DataCategory.MOLECULES: MOLECULE_SCHEMA,
    }
    return schema_map.get(category, [])


def get_display_field_for_category(category: DataCategory) -> str:
    """Get the display field name for a data category"""
    display_map = {
        DataCategory.ELEMENTS: "name",
        DataCategory.QUARKS: "Name",
        DataCategory.ANTIQUARKS: "Name",
        DataCategory.SUBATOMIC: "Name",
        DataCategory.MOLECULES: "Name",
    }
    return display_map.get(category, "Name")


def open_data_editor(category: DataCategory, parent=None) -> Optional[DataListDialog]:
    """
    Open a data editor dialog for the specified category.

    Args:
        category: DataCategory to edit
        parent: Parent widget

    Returns:
        DataListDialog instance or None if cancelled
    """
    schema = get_schema_for_category(category)
    display_field = get_display_field_for_category(category)

    dialog = DataListDialog(
        category=category,
        schema=schema,
        title=f"Edit {category.value.title()}",
        display_field=display_field,
        parent=parent
    )

    dialog.exec()
    return dialog


# ==================== Demo/Testing ====================

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Test with molecule schema
    test_data = {
        "Name": "Water",
        "Formula": "H2O",
        "MolecularMass_amu": 18.015,
        "BondType": "Covalent",
        "Geometry": "Bent",
        "Polarity": "Polar",
        "Composition": [
            {"Element": "H", "Count": 2},
            {"Element": "O", "Count": 1}
        ]
    }

    dialog = DataEditorDialog(MOLECULE_SCHEMA, data=test_data, title="Edit Molecule")
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Saved data:", dialog.get_data())

    sys.exit(0)
