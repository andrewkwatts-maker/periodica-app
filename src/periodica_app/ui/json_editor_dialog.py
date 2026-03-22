"""
JSON Editor Dialog
A simple dialog for editing JSON data as text with syntax highlighting.
"""

import json

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat
import re


class JsonSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON text"""

    def __init__(self, document):
        super().__init__(document)
        # Define formats
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("#e06c75"))  # Red for keys

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#98c379"))  # Green for strings

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#d19a66"))  # Orange for numbers

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#56b6c2"))  # Cyan for keywords

        self.bracket_format = QTextCharFormat()
        self.bracket_format.setForeground(QColor("#c678dd"))  # Purple for brackets

    def highlightBlock(self, text):
        """Highlight a block of text"""
        # Highlight keys (text before colon, in quotes)
        key_pattern = r'"([^"\\]|\\.)*"\s*(?=:)'
        for match in re.finditer(key_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.key_format)

        # Highlight string values
        # Find strings that are values (after : or in arrays)
        string_pattern = r':\s*"([^"\\]|\\.)*"|\[\s*"([^"\\]|\\.)*"'
        for match in re.finditer(string_pattern, text):
            # Find the actual string part
            start = text.find('"', match.start())
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

        # Highlight brackets
        for char in '{}[]':
            index = text.find(char)
            while index >= 0:
                self.setFormat(index, 1, self.bracket_format)
                index = text.find(char, index + 1)


class JSONEditorDialog(QDialog):
    """Dialog for editing JSON data as text"""

    def __init__(self, data: dict, title: str = "Edit JSON", parent=None):
        """
        Initialize the JSON editor dialog.

        Args:
            data: The dictionary data to edit
            title: Dialog title
            parent: Parent widget
        """
        super().__init__(parent)
        self.original_data = data
        self._edited_data = None

        self.setWindowTitle(title)
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                color: white;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QPlainTextEdit {
                background: rgba(30, 30, 45, 250);
                color: #abb2bf;
                border: 1px solid #667eea;
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
                padding: 10px;
            }
            QPlainTextEdit:focus {
                border: 2px solid #764ba2;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c8ff5, stop:1 #8957b5);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5668d4, stop:1 #6a4199);
            }
            QPushButton#cancelBtn {
                background: rgba(100, 100, 120, 200);
            }
            QPushButton#cancelBtn:hover {
                background: rgba(120, 120, 140, 220);
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title/instruction
        title_label = QLabel("Edit the JSON data below:")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #4fc3f7;")
        layout.addWidget(title_label)

        # JSON text editor
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont("Consolas", 11))
        self.highlighter = JsonSyntaxHighlighter(self.text_edit.document())

        # Format JSON with indentation
        json_text = json.dumps(self.original_data, indent=2, ensure_ascii=False)
        self.text_edit.setPlainText(json_text)
        layout.addWidget(self.text_edit)

        # Validation message
        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self._validate)
        button_layout.addWidget(validate_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #27ae60, stop:1 #1e8449);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2ecc71, stop:1 #27ae60);
            }
        """)
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _validate(self) -> bool:
        """Validate the JSON text and show any errors"""
        text = self.text_edit.toPlainText()
        try:
            self._edited_data = json.loads(text)
            self.validation_label.setText("")
            self.validation_label.setStyleSheet("color: #27ae60; font-size: 11px;")
            self.validation_label.setText("Valid JSON")
            return True
        except json.JSONDecodeError as e:
            self.validation_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
            self.validation_label.setText(f"JSON Error: {e}")
            return False

    def _on_save(self):
        """Handle save button click"""
        if self._validate():
            self.accept()
        else:
            QMessageBox.warning(
                self, "Invalid JSON",
                "Please fix the JSON errors before saving."
            )

    def get_data(self) -> dict:
        """Get the edited data dictionary"""
        if self._edited_data is None:
            # Try to parse if not already validated
            try:
                self._edited_data = json.loads(self.text_edit.toPlainText())
            except json.JSONDecodeError:
                return self.original_data
        return self._edited_data
