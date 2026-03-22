"""
API Settings Dialog for configuring AI service API keys.
Provides a secure interface for users to enter and manage their API keys.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from periodica_app.config import get_gemini_api_key, set_gemini_api_key, is_gemini_configured


class APISettingsDialog(QDialog):
    """Dialog for managing AI service API keys."""

    # Emitted when API key configuration changes
    api_key_changed = Signal(bool)  # True if key is now configured

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Settings")
        self.setMinimumSize(500, 300)
        self.setModal(True)
        self.setup_ui()
        self.load_current_values()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(20, 20, 35);
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: rgb(45, 45, 65);
                color: white;
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 4px;
                padding: 8px;
                font-family: Consolas, Monaco, monospace;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
            QGroupBox {
                color: white;
                border: 2px solid #667eea;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("AI Service Configuration")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Configure your API keys to enable AI-powered asset generation.\n"
            "Keys are stored locally in config/secrets.json and are never shared."
        )
        desc.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 11px;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # Gemini API Key Group
        gemini_group = QGroupBox("Google Gemini API")
        gemini_layout = QVBoxLayout()

        # Status indicator
        self.gemini_status = QLabel()
        self.gemini_status.setStyleSheet("font-size: 11px;")
        gemini_layout.addWidget(self.gemini_status)

        # API key input row
        key_row = QHBoxLayout()

        key_label = QLabel("API Key:")
        key_label.setMinimumWidth(60)
        key_row.addWidget(key_label)

        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setPlaceholderText("Enter your Gemini API key...")
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_row.addWidget(self.gemini_key_input)

        # Show/hide toggle
        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setFixedWidth(60)
        self.show_key_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100, 100, 120, 150);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background: rgba(120, 120, 140, 180);
            }
        """)
        self.show_key_btn.clicked.connect(self.toggle_key_visibility)
        key_row.addWidget(self.show_key_btn)

        gemini_layout.addLayout(key_row)

        # Help text
        help_label = QLabel(
            "Get your API key from: https://aistudio.google.com/apikey"
        )
        help_label.setStyleSheet("color: rgba(255, 255, 255, 120); font-size: 10px;")
        help_label.setOpenExternalLinks(True)
        gemini_layout.addWidget(help_label)

        gemini_group.setLayout(gemini_layout)
        layout.addWidget(gemini_group)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(100, 100, 120, 100);")
        layout.addWidget(separator)

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background: rgba(76, 175, 80, 180);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(76, 175, 80, 220);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """)
        self.test_btn.clicked.connect(self.test_connection)
        button_row.addWidget(self.test_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #7b8fed, stop:1 #8b5cb5);
            }
        """)
        self.save_btn.clicked.connect(self.save_settings)
        button_row.addWidget(self.save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100, 100, 120, 150);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(120, 120, 140, 180);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        layout.addLayout(button_row)
        layout.addStretch()

    def load_current_values(self):
        """Load current API key values."""
        key = get_gemini_api_key()
        if key:
            # Show masked version
            self.gemini_key_input.setText(key)
            self.update_status(True)
        else:
            self.update_status(False)

    def update_status(self, configured: bool):
        """Update the status indicator."""
        if configured:
            self.gemini_status.setText("Status: Configured")
            self.gemini_status.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;")
        else:
            self.gemini_status.setText("Status: Not Configured")
            self.gemini_status.setStyleSheet("color: #FF9800; font-size: 11px; font-weight: bold;")

    def toggle_key_visibility(self):
        """Toggle between showing and hiding the API key."""
        if self.gemini_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("Hide")
        else:
            self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("Show")

    def test_connection(self):
        """Test the Gemini API connection."""
        key = self.gemini_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "No API Key", "Please enter an API key first.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content("Say 'API connection successful' in exactly 3 words.")

            if response and response.text:
                QMessageBox.information(
                    self, "Connection Successful",
                    f"Successfully connected to Gemini API!\n\nResponse: {response.text[:100]}"
                )
            else:
                QMessageBox.warning(
                    self, "Connection Issue",
                    "Connected but received empty response."
                )

        except ImportError:
            QMessageBox.critical(
                self, "Missing Package",
                "The google-generativeai package is not installed.\n\n"
                "Install it with: pip install google-generativeai"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Connection Failed",
                f"Failed to connect to Gemini API:\n\n{str(e)}"
            )

    def save_settings(self):
        """Save the API key settings."""
        key = self.gemini_key_input.text().strip()

        if not key:
            # Allow clearing the key
            result = QMessageBox.question(
                self, "Clear API Key?",
                "No API key entered. Do you want to clear the saved key?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        if set_gemini_api_key(key if key else None):
            self.update_status(bool(key))
            self.api_key_changed.emit(bool(key))
            QMessageBox.information(
                self, "Settings Saved",
                "API key has been saved successfully."
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, "Save Failed",
                "Failed to save the API key. Check file permissions."
            )
