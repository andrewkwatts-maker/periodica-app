"""
AI Generation Widget for control panels.
Provides a reusable widget with AI generation button and API settings access.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from periodica_app.config import is_gemini_configured, reload_secrets


class AIGenerationWidget(QWidget):
    """
    Widget for AI-powered asset generation.
    Includes a generate button (grayed out if no API key) and settings button.
    """

    # Emitted when user clicks generate (only if API key configured)
    generate_requested = Signal()

    # Emitted when user clicks settings
    settings_requested = Signal()

    def __init__(self, asset_type: str, parent=None):
        super().__init__(parent)
        self.asset_type = asset_type
        self._api_configured = False
        self.setup_ui()
        self.refresh_api_status()

    def setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # AI Generation Group
        group = QGroupBox("AI Generation")
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid #9C27B0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        group_layout = QVBoxLayout()

        # Status indicator
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 10px;")
        group_layout.addWidget(self.status_label)

        # AI Generate button
        self.generate_btn = QPushButton("Generate with AI")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #9C27B0, stop:1 #7B1FA2);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #AB47BC, stop:1 #8E24AA);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.generate_btn.setToolTip("Generate a new configuration using Gemini AI")
        group_layout.addWidget(self.generate_btn)

        # Settings button
        self.settings_btn = QPushButton("AI Settings")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100, 100, 120, 150);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: rgba(120, 120, 140, 180);
            }
        """)
        self.settings_btn.clicked.connect(self._on_settings_clicked)
        self.settings_btn.setToolTip("Configure Gemini API key")
        group_layout.addWidget(self.settings_btn)

        # Help text
        help_label = QLabel("Use AI to generate configurations\nbased on your description")
        help_label.setStyleSheet("color: rgba(255, 255, 255, 120); font-size: 9px;")
        help_label.setWordWrap(True)
        group_layout.addWidget(help_label)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def refresh_api_status(self):
        """Refresh the API configuration status."""
        reload_secrets()
        self._api_configured = is_gemini_configured()

        if self._api_configured:
            self.status_label.setText("Gemini API: Ready")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 10px; font-weight: bold;")
            self.generate_btn.setEnabled(True)
            self.generate_btn.setToolTip("Generate a new configuration using Gemini AI")
        else:
            self.status_label.setText("Gemini API: Not Configured")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 10px; font-weight: bold;")
            self.generate_btn.setEnabled(False)
            self.generate_btn.setToolTip("Configure your Gemini API key in AI Settings first")

    def _on_generate_clicked(self):
        """Handle generate button click."""
        if self._api_configured:
            self.generate_requested.emit()

    def _on_settings_clicked(self):
        """Handle settings button click."""
        self.settings_requested.emit()

    def is_api_configured(self) -> bool:
        """Check if API is configured."""
        return self._api_configured
