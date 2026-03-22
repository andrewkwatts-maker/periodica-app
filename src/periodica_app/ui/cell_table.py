"""
Cell Table Widget
Displays cells in a grid layout with visual property encoding.
"""

import json
import math
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                                QScrollArea, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import (QFont, QPainter, QColor, QBrush, QPen)

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.cell_enums import CellType, TissueType, MetabolicState


class CellCard(QFrame):
    """Individual cell card widget."""

    clicked = Signal(dict)

    def __init__(self, cell, parent=None):
        super().__init__(parent)
        self.cell = cell
        self._selected = False
        self._base_size = 130
        self._current_size = 130
        self._color_property = "type"

        self.setMinimumSize(QSize(80, 80))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def set_selected(self, selected):
        self._selected = selected
        self.update_style()

    def set_size(self, size):
        self._current_size = size
        self.setFixedSize(QSize(int(size), int(size)))
        self.update()

    def set_color_property(self, prop):
        self._color_property = prop
        self.update_style()

    def update_style(self):
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
        if self._color_property == "type":
            cell_type = self.cell.get('type', 'other')
            return CellType.get_color(cell_type)
        elif self._color_property == "tissue":
            tissue = self.cell.get('tissue', 'connective')
            return TissueType.get_color(tissue)
        elif self._color_property == "metabolic":
            # Color by metabolic rate
            rate = self.cell.get('metabolic_rate_fW', 50)
            if rate < 10:
                return "#4CAF50"  # Green - low
            elif rate < 100:
                return "#FF9800"  # Orange - medium
            else:
                return "#F44336"  # Red - high
        else:
            return ThemeColors.ACCENT

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Draw cell type indicator at top
        cell_type = self.cell.get('type', 'unknown').replace('_', ' ').title()
        if len(cell_type) > 15:
            cell_type = cell_type[:13] + ".."
        color = QColor(self._get_property_color())
        painter.setPen(QPen(QColor(180, 180, 180)))
        painter.setFont(QFont("Arial", max(7, int(self._current_size * 0.07))))
        painter.drawText(8, 14, cell_type)

        # Draw name in center
        name = self.cell.get('name', '?')
        # Shorten name
        if "(" in name:
            name = name.split("(")[0].strip()
        if len(name) > 14:
            name = name[:12] + ".."

        painter.setPen(QPen(color, 2))
        font_size = max(9, int(self._current_size * 0.10))
        painter.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, name)

        # Draw size info at bottom left
        diameter = self.cell.get('diameter_um', 0)
        painter.setPen(QPen(QColor(150, 150, 150)))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(8, h - 5, f"⌀{diameter}μm")

        # Draw metabolic rate at bottom right
        rate = self.cell.get('metabolic_rate_fW', 0)
        if rate >= 1000:
            rate_str = f"{rate/1000:.1f}pW"
        else:
            rate_str = f"{rate:.0f}fW"
        painter.drawText(w - 45, h - 5, rate_str)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.cell)


class CellTableWidget(QWidget):
    """Widget displaying cells in a grid layout."""

    cell_selected = Signal(dict)
    cell_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cells = []
        self._cards = []
        self._selected_card = None
        self._layout_mode = "grid"
        self._color_property = "type"
        self._size_property = "none"
        self._type_filters = []
        self._tissue_filters = []
        self._search_filter = ""

        self.setup_ui()
        self.load_cells()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

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

    def load_cells(self):
        cell_dir = Path(__file__).parent.parent / "data" / "active" / "cells"
        self._cells = []

        if cell_dir.exists():
            for json_file in sorted(cell_dir.glob("*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._cells.append(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        self._rebuild_grid()

    def _rebuild_grid(self):
        for card in self._cards:
            card.deleteLater()
        self._cards = []

        filtered = self._get_filtered_cells()
        sorted_cells = self._sort_cells(filtered)
        cols = 4

        for i, cell in enumerate(sorted_cells):
            card = CellCard(cell)
            card.set_color_property(self._color_property)
            size = self._calculate_card_size(cell)
            card.set_size(size)
            card.clicked.connect(self._on_card_clicked)

            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)
            self._cards.append(card)

    def _get_filtered_cells(self):
        filtered = self._cells

        # Apply search filter
        if self._search_filter:
            filtered = [
                cell for cell in filtered
                if self._search_filter in cell.get('name', '').lower()
            ]

        # Apply type filter
        if self._type_filters:
            filtered = [c for c in filtered
                        if any(f in c.get('type', '').lower() for f in self._type_filters)]

        # Apply tissue filter
        if self._tissue_filters:
            filtered = [c for c in filtered
                        if any(f in c.get('tissue', '').lower() for f in self._tissue_filters)]

        return filtered if filtered else self._cells

    def _sort_cells(self, cells):
        if self._layout_mode == "grid":
            return sorted(cells, key=lambda x: x.get('name', 'Z'))
        elif self._layout_mode == "type":
            return sorted(cells, key=lambda x: x.get('type', ''))
        elif self._layout_mode == "tissue":
            return sorted(cells, key=lambda x: x.get('tissue', ''))
        elif self._layout_mode == "size":
            return sorted(cells, key=lambda x: x.get('diameter_um', 0), reverse=True)
        elif self._layout_mode == "metabolic_rate":
            return sorted(cells, key=lambda x: x.get('metabolic_rate_fW', 0), reverse=True)
        elif self._layout_mode == "organism":
            return sorted(cells, key=lambda x: x.get('organism', ''))
        return cells

    def _calculate_card_size(self, cell):
        base = 130
        if self._size_property == "none":
            return base
        elif self._size_property == "diameter":
            diameter = cell.get('diameter_um', 10)
            return int(100 + min(math.log10(max(1, diameter)) * 35, 80))
        elif self._size_property == "metabolic_rate":
            rate = cell.get('metabolic_rate_fW', 10)
            return int(100 + min(math.log10(max(1, rate)) * 25, 80))
        elif self._size_property == "mitochondria":
            mito = cell.get('mitochondria_count', 100)
            return int(100 + min(math.log10(max(1, mito)) * 20, 80))
        return base

    def _on_card_clicked(self, cell):
        if self._selected_card:
            self._selected_card.set_selected(False)
        for card in self._cards:
            if card.cell == cell:
                card.set_selected(True)
                self._selected_card = card
                break
        self.cell_selected.emit(cell)

    def set_layout_mode(self, mode):
        self._layout_mode = mode
        self._rebuild_grid()

    def set_color_property(self, prop):
        self._color_property = prop
        for card in self._cards:
            card.set_color_property(prop)

    def set_size_property(self, prop):
        self._size_property = prop
        self._rebuild_grid()

    def set_type_filters(self, types):
        self._type_filters = types
        self._rebuild_grid()

    def set_tissue_filters(self, tissues):
        self._tissue_filters = tissues
        self._rebuild_grid()

    def get_selected_cell(self):
        if self._selected_card:
            return self._selected_card.cell
        return None

    def get_cell_count(self):
        return len(self._cells)

    def set_search_filter(self, text: str):
        """Set search filter by name."""
        self._search_filter = text.lower().strip()
        self._rebuild_grid()

    def get_filtered_count(self):
        """Get count of currently filtered cells."""
        return len(self._get_filtered_cells())

    def refresh(self):
        self.load_cells()
