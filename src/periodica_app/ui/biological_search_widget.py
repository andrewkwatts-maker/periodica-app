"""
Biological Search Widget
Reusable search/filter widget for all biological tabs.
Provides a search input with clear button, search icon, and debounced filtering.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QPainter, QColor, QPen


class SearchIcon(QWidget):
    """Custom search icon widget (magnifying glass)."""

    def __init__(self, color="#ffffff", size=16, parent=None):
        super().__init__(parent)
        self.color = color
        self.icon_size = size
        self.setFixedSize(size + 4, size + 4)

    def set_color(self, color):
        """Update the icon color."""
        self.color = color
        self.update()

    def paintEvent(self, event):
        """Draw a magnifying glass icon."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        margin = 2
        size = self.icon_size
        circle_radius = size * 0.35
        center_x = margin + size * 0.35
        center_y = margin + size * 0.35

        # Draw the circle (lens)
        pen = QPen(QColor(self.color))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            int(center_x - circle_radius),
            int(center_y - circle_radius),
            int(circle_radius * 2),
            int(circle_radius * 2)
        )

        # Draw the handle
        handle_start_x = center_x + circle_radius * 0.7
        handle_start_y = center_y + circle_radius * 0.7
        handle_end_x = margin + size * 0.85
        handle_end_y = margin + size * 0.85
        painter.drawLine(
            int(handle_start_x), int(handle_start_y),
            int(handle_end_x), int(handle_end_y)
        )


class ClearButton(QPushButton):
    """Custom clear button (X) that shows/hides based on input text."""

    def __init__(self, accent_color="#66BB6A", parent=None):
        super().__init__(parent)
        self.accent_color = accent_color
        self.setText("\u00d7")  # Unicode multiplication sign (x)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Clear search (Esc)")
        self._apply_style()

    def _apply_style(self):
        """Apply button styling."""
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: rgba(255, 255, 255, 150);
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 30);
                color: {self.accent_color};
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 50);
            }}
        """)

    def set_accent_color(self, color):
        """Update the accent color."""
        self.accent_color = color
        self._apply_style()


class BiologicalSearchWidget(QWidget):
    """
    Search widget with text input, clear button, search icon, and debounced search.

    Features:
    - Search icon on the left
    - Text input with placeholder
    - Clear button (X) that appears when text is entered
    - Real-time filtering with configurable debounce delay
    - Results count display
    - Escape key to clear

    Signals:
        search_changed(str): Emitted when search text changes (after debounce)

    Example usage:
        search_widget = BiologicalSearchWidget(
            placeholder="Search amino acids...",
            accent_color="#66bb6a"
        )
        search_widget.search_changed.connect(self.on_search)
    """

    search_changed = Signal(str)  # Emitted when search text changes (debounced)

    def __init__(
        self,
        placeholder="Search...",
        accent_color="#66BB6A",
        debounce_ms=150,
        parent=None
    ):
        """
        Initialize the search widget.

        Args:
            placeholder: Placeholder text for the search input
            accent_color: Accent color for styling (borders, highlights)
            debounce_ms: Debounce delay in milliseconds (default 150ms)
            parent: Parent widget
        """
        super().__init__(parent)
        self.accent_color = accent_color
        self.debounce_ms = debounce_ms

        # Debounce timer
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_search)

        self._setup_ui(placeholder)

    def _setup_ui(self, placeholder):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 10)
        layout.setSpacing(0)

        # Container widget for the search input with icon and clear button
        self.search_container = QWidget()
        self.search_container.setStyleSheet(self._get_container_style())
        container_layout = QHBoxLayout(self.search_container)
        container_layout.setContentsMargins(8, 0, 4, 0)
        container_layout.setSpacing(6)

        # Search icon
        self.search_icon = SearchIcon(color="rgba(255, 255, 255, 150)", size=14)
        container_layout.addWidget(self.search_icon)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.setStyleSheet(self._get_input_style())
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.setMinimumHeight(28)
        container_layout.addWidget(self.search_input, 1)

        # Clear button (hidden by default)
        self.clear_btn = ClearButton(accent_color=self.accent_color)
        self.clear_btn.clicked.connect(self.clear)
        self.clear_btn.setVisible(False)
        container_layout.addWidget(self.clear_btn)

        layout.addWidget(self.search_container, 1)

        # Results count label
        self.results_label = QLabel("")
        self.results_label.setStyleSheet(
            "color: rgba(255, 255, 255, 150); "
            "font-size: 9px; "
            "min-width: 50px; "
            "margin-left: 8px;"
        )
        self.results_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.results_label)

    def _get_container_style(self):
        """Get style for the search container."""
        return f"""
            QWidget {{
                background: rgba(40, 40, 60, 200);
                border: 1px solid {self.accent_color};
                border-radius: 6px;
            }}
            QWidget:focus-within {{
                border: 2px solid {self.accent_color};
            }}
        """

    def _get_input_style(self):
        """Get style for the search input."""
        return f"""
            QLineEdit {{
                background: transparent;
                color: white;
                border: none;
                padding: 4px 0;
                font-size: 11px;
                selection-background-color: {self.accent_color};
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 100);
            }}
        """

    def _on_text_changed(self, text):
        """Handle text change with debouncing."""
        # Show/hide clear button based on text content
        self.clear_btn.setVisible(bool(text))

        # Update search icon color when typing
        if text:
            self.search_icon.set_color(self.accent_color)
        else:
            self.search_icon.set_color("rgba(255, 255, 255, 150)")

        # Restart debounce timer
        self._debounce_timer.stop()
        self._debounce_timer.start(self.debounce_ms)

    def _emit_search(self):
        """Emit the search signal after debounce."""
        self.search_changed.emit(self.search_input.text())

    def clear(self):
        """Clear the search input and emit empty search."""
        self.search_input.clear()
        self.search_input.setFocus()
        # Emit immediately without debounce for clear action
        self._debounce_timer.stop()
        self.search_changed.emit("")

    def set_results_count(self, showing: int, total: int):
        """
        Update the results count label.

        Args:
            showing: Number of items currently showing
            total: Total number of items
        """
        if self.search_input.text():
            self.results_label.setText(f"{showing}/{total}")
        else:
            self.results_label.setText("")

    def get_search_text(self) -> str:
        """Get the current search text."""
        return self.search_input.text()

    def set_search_text(self, text: str):
        """
        Set the search text programmatically.

        Args:
            text: The text to set in the search input
        """
        self.search_input.setText(text)

    def set_placeholder(self, placeholder: str):
        """
        Update the placeholder text.

        Args:
            placeholder: New placeholder text
        """
        self.search_input.setPlaceholderText(placeholder)

    def set_accent_color(self, color: str):
        """
        Update the accent color.

        Args:
            color: New accent color (CSS color string)
        """
        self.accent_color = color
        self.search_container.setStyleSheet(self._get_container_style())
        self.search_input.setStyleSheet(self._get_input_style())
        self.clear_btn.set_accent_color(color)

    def set_debounce_delay(self, ms: int):
        """
        Update the debounce delay.

        Args:
            ms: Debounce delay in milliseconds
        """
        self.debounce_ms = ms

    def setFocus(self):
        """Set focus to the search input."""
        self.search_input.setFocus()

    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.clear()
        else:
            super().keyPressEvent(event)

    # Backward compatibility aliases
    def clear_search(self):
        """Alias for clear() - backward compatibility."""
        self.clear()
