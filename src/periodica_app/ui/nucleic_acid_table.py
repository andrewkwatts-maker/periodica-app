"""
Nucleic Acid Table Widget
Displays nucleic acids in a grid/table layout with visual property encoding.
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                                QScrollArea, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import (QFont, QPainter, QColor, QBrush, QPen)

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.nucleic_acid_enums import NucleicAcidType, NucleicAcidFunction


class NucleicAcidCard(QFrame):
    """Individual nucleic acid card widget."""

    clicked = Signal(dict)

    def __init__(self, nucleic_acid, parent=None):
        super().__init__(parent)
        self.nucleic_acid = nucleic_acid
        self._selected = False
        self._base_size = 130
        self._current_size = 130
        self._color_property = "type"

        self.setMinimumSize(QSize(80, 80))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def set_selected(self, selected):
        """Set selection state."""
        self._selected = selected
        self.update_style()

    def set_size(self, size):
        """Set card size."""
        self._current_size = size
        self.setFixedSize(QSize(int(size), int(size)))
        self.update()

    def set_color_property(self, prop):
        """Set which property determines card color."""
        self._color_property = prop
        self.update_style()

    def update_style(self):
        """Update card styling based on properties."""
        color = self._get_property_color()
        border_color = ThemeColors.ACCENT if self._selected else color
        border_width = 3 if self._selected else 2

        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(30, 30, 50, 220),
                    stop:1 rgba(40, 40, 70, 220));
                border: {border_width}px solid {border_color};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {ThemeColors.ACCENT};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(40, 40, 70, 220),
                    stop:1 rgba(50, 50, 90, 220));
            }}
        """)
        self.update()

    def _get_property_color(self):
        """Get color based on current color property."""
        if self._color_property == "type":
            na_type = self.nucleic_acid.get('type', 'dna')
            return NucleicAcidType.get_color(na_type)
        elif self._color_property == "function":
            func = self.nucleic_acid.get('function', 'genetic_storage')
            return NucleicAcidFunction.get_color(func)
        elif self._color_property == "gc_content":
            gc = self.nucleic_acid.get('gc_content', 50)
            # Color from red (low GC) to blue (high GC)
            if gc < 40:
                return "#F44336"  # Red for low GC
            elif gc > 60:
                return "#2196F3"  # Blue for high GC
            return "#FFC107"  # Amber for medium GC
        elif self._color_property == "length":
            length = self.nucleic_acid.get('length', 0)
            # Color scale based on length
            if length < 30:
                return "#4CAF50"  # Green for short
            elif length > 100:
                return "#9C27B0"  # Purple for long
            return "#FF9800"  # Orange for medium
        elif self._color_property == "organism":
            organism = self.nucleic_acid.get('organism', '').lower()
            if 'homo' in organism or 'human' in organism:
                return "#2196F3"
            elif 'coli' in organism or 'bacteria' in organism:
                return "#4CAF50"
            elif 'yeast' in organism or 'cerevisiae' in organism:
                return "#FF9800"
            return "#9E9E9E"
        else:
            return ThemeColors.ACCENT

    def paintEvent(self, event):
        """Custom paint for nucleic acid card."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Draw name (abbreviated)
        name = self.nucleic_acid.get('name', '?')
        # Abbreviate long names
        if len(name) > 12:
            name = name[:10] + ".."

        color = QColor(self._get_property_color())
        painter.setPen(QPen(color, 2))
        font_size = max(8, int(self._current_size * 0.11))
        painter.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, name)

        # Draw type indicator at top
        na_type = self.nucleic_acid.get('type', 'dna').upper()
        painter.setPen(QPen(QColor(180, 180, 180)))
        painter.setFont(QFont("Arial", max(7, int(self._current_size * 0.08))))
        painter.drawText(5, 15, na_type)

        # Draw length at top right
        length = self.nucleic_acid.get('length', 0)
        painter.drawText(w - 40, 15, f"{length}nt")

        # Draw GC content bar at bottom
        gc = self.nucleic_acid.get('gc_content', 50)
        bar_width = int((w - 20) * gc / 100)
        bar_y = h - 12

        # Background bar
        painter.fillRect(10, bar_y, w - 20, 5, QColor(60, 60, 80))
        # GC bar
        if gc > 60:
            gc_color = QColor("#2196F3")
        elif gc < 40:
            gc_color = QColor("#F44336")
        else:
            gc_color = QColor("#FFC107")
        painter.fillRect(10, bar_y, bar_width, 5, gc_color)

        # GC percentage text
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Arial", 7))
        painter.drawText(w - 35, h - 3, f"{gc:.0f}%")

        painter.end()

    def mousePressEvent(self, event):
        """Handle click events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.nucleic_acid)


class NucleicAcidTableWidget(QWidget):
    """Widget displaying nucleic acids in a configurable grid layout."""

    nucleic_acid_selected = Signal(dict)
    nucleic_acid_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nucleic_acids = []
        self._cards = []
        self._selected_card = None
        self._layout_mode = "grid"
        self._color_property = "type"
        self._size_property = "none"
        self._type_filters = []
        self._search_filter = ""

        self.setup_ui()
        self.load_nucleic_acids()

    def setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for the grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: rgba(40, 40, 60, 100);
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(102, 187, 106, 150);
                border-radius: 5px;
            }}
        """)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

    def load_nucleic_acids(self):
        """Load nucleic acid data from JSON files."""
        na_dir = Path(__file__).parent.parent / "data" / "active" / "nucleic_acids"
        self._nucleic_acids = []

        if na_dir.exists():
            for json_file in sorted(na_dir.glob("*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._nucleic_acids.append(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        self._rebuild_grid()

    def _rebuild_grid(self):
        """Rebuild the grid with current layout mode."""
        # Clear existing cards
        for card in self._cards:
            card.deleteLater()
        self._cards = []

        # Filter nucleic acids
        filtered = self._get_filtered_nucleic_acids()

        # Sort based on layout mode
        sorted_nas = self._sort_nucleic_acids(filtered)

        # Calculate grid dimensions
        cols = self._get_column_count()

        # Create cards
        for i, na in enumerate(sorted_nas):
            card = NucleicAcidCard(na)
            card.set_color_property(self._color_property)

            # Set size based on size property
            size = self._calculate_card_size(na)
            card.set_size(size)

            card.clicked.connect(self._on_card_clicked)

            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)
            self._cards.append(card)

    def _get_filtered_nucleic_acids(self):
        """Apply filters to nucleic acids."""
        filtered = self._nucleic_acids

        # Apply search filter
        if self._search_filter:
            filtered = [
                na for na in filtered
                if self._search_filter in na.get('name', '').lower()
                or self._search_filter in na.get('abbreviation', '').lower()
            ]

        # Apply type filter
        if self._type_filters:
            filtered = [
                na for na in filtered
                if any(f in na.get('type', 'dna').lower().replace(' ', '')
                       for f in self._type_filters)
            ]

        return filtered if filtered else self._nucleic_acids

    def _sort_nucleic_acids(self, nucleic_acids):
        """Sort nucleic acids based on layout mode."""
        if self._layout_mode == "grid":
            return sorted(nucleic_acids, key=lambda x: x.get('name', 'Z'))
        elif self._layout_mode == "type":
            return sorted(nucleic_acids, key=lambda x: x.get('type', ''))
        elif self._layout_mode == "function":
            return sorted(nucleic_acids, key=lambda x: x.get('function', ''))
        elif self._layout_mode == "length":
            return sorted(nucleic_acids, key=lambda x: x.get('length', 0))
        elif self._layout_mode == "gc_content":
            return sorted(nucleic_acids, key=lambda x: x.get('gc_content', 0), reverse=True)
        elif self._layout_mode == "organism":
            return sorted(nucleic_acids, key=lambda x: x.get('organism', ''))
        else:
            return nucleic_acids

    def _get_column_count(self):
        """Get number of columns based on layout mode."""
        return 4  # Default columns

    def _calculate_card_size(self, na):
        """Calculate card size based on size property."""
        base = 130

        if self._size_property == "none":
            return base
        elif self._size_property == "length":
            length = na.get('length', 50)
            # Scale from short to long -> 100-180px
            return int(100 + min(length / 10, 80))
        elif self._size_property == "gc_content":
            gc = na.get('gc_content', 50)
            return int(100 + gc * 0.6)
        elif self._size_property == "molecular_mass":
            mass = na.get('molecular_mass', 10000)
            return int(100 + (mass / 1000) * 3)
        else:
            return base

    def _on_card_clicked(self, na):
        """Handle card click."""
        # Deselect previous
        if self._selected_card:
            self._selected_card.set_selected(False)

        # Find and select new card
        for card in self._cards:
            if card.nucleic_acid == na:
                card.set_selected(True)
                self._selected_card = card
                break

        self.nucleic_acid_selected.emit(na)

    # === Public API ===

    def set_layout_mode(self, mode):
        """Set layout mode."""
        self._layout_mode = mode
        self._rebuild_grid()

    def set_color_property(self, prop):
        """Set color property."""
        self._color_property = prop
        for card in self._cards:
            card.set_color_property(prop)

    def set_size_property(self, prop):
        """Set size property."""
        self._size_property = prop
        self._rebuild_grid()

    def set_type_filters(self, types):
        """Set type filters."""
        self._type_filters = types
        self._rebuild_grid()

    def get_selected_nucleic_acid(self):
        """Get currently selected nucleic acid."""
        if self._selected_card:
            return self._selected_card.nucleic_acid
        return None

    def get_nucleic_acid_count(self):
        """Get total nucleic acid count."""
        return len(self._nucleic_acids)

    def set_search_filter(self, text: str):
        """Set search filter by name."""
        self._search_filter = text.lower().strip()
        self._rebuild_grid()

    def get_filtered_count(self):
        """Get count of currently filtered nucleic acids."""
        return len(self._get_filtered_nucleic_acids())

    def add_nucleic_acid(self, na_data):
        """Add a new nucleic acid to the table."""
        self._nucleic_acids.append(na_data)
        self._rebuild_grid()

    def refresh(self):
        """Refresh data from files."""
        self.load_nucleic_acids()
