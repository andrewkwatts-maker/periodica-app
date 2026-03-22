"""
Cell Component Table Widget
Displays cell components (organelles) in a grid layout with visual property encoding.
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                                QScrollArea, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import (QFont, QPainter, QColor, QBrush, QPen)

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.cell_component_enums import OrganelleType, ComponentFunction


class CellComponentCard(QFrame):
    """Individual cell component card widget."""

    clicked = Signal(dict)

    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
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
            comp_type = self.component.get('type', 'ribosome')
            return OrganelleType.get_color(comp_type)
        elif self._color_property == "function":
            func = self.component.get('function', 'structural')
            return ComponentFunction.get_color(func)
        else:
            return ThemeColors.ACCENT

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Draw name
        name = self.component.get('name', '?')
        if len(name) > 14:
            name = name[:12] + ".."

        color = QColor(self._get_property_color())
        painter.setPen(QPen(color, 2))
        font_size = max(8, int(self._current_size * 0.10))
        painter.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, name)

        # Draw type at top
        comp_type = self.component.get('type', 'unknown').replace('_', ' ').title()
        if len(comp_type) > 15:
            comp_type = comp_type[:13] + ".."
        painter.setPen(QPen(QColor(180, 180, 180)))
        painter.setFont(QFont("Arial", max(7, int(self._current_size * 0.07))))
        painter.drawText(5, 12, comp_type)

        # Draw copy number at bottom
        copy_num = self.component.get('copy_number_per_cell', 0)
        if copy_num >= 1000000:
            copy_str = f"{copy_num/1000000:.0f}M"
        elif copy_num >= 1000:
            copy_str = f"{copy_num/1000:.0f}k"
        else:
            copy_str = str(copy_num)
        painter.drawText(5, h - 5, f"×{copy_str}")

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.component)


class CellComponentTableWidget(QWidget):
    """Widget displaying cell components in a grid layout."""

    component_selected = Signal(dict)
    component_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._components = []
        self._cards = []
        self._selected_card = None
        self._layout_mode = "grid"
        self._color_property = "type"
        self._size_property = "none"
        self._type_filters = []
        self._search_filter = ""

        self.setup_ui()
        self.load_components()

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

    def load_components(self):
        comp_dir = Path(__file__).parent.parent / "data" / "active" / "cell_components"
        self._components = []

        if comp_dir.exists():
            for json_file in sorted(comp_dir.glob("*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._components.append(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        self._rebuild_grid()

    def _rebuild_grid(self):
        for card in self._cards:
            card.deleteLater()
        self._cards = []

        filtered = self._get_filtered_components()
        sorted_comps = self._sort_components(filtered)
        cols = 4

        for i, comp in enumerate(sorted_comps):
            card = CellComponentCard(comp)
            card.set_color_property(self._color_property)
            size = self._calculate_card_size(comp)
            card.set_size(size)
            card.clicked.connect(self._on_card_clicked)

            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)
            self._cards.append(card)

    def _get_filtered_components(self):
        filtered = self._components

        # Apply search filter
        if self._search_filter:
            filtered = [
                comp for comp in filtered
                if self._search_filter in comp.get('name', '').lower()
            ]

        # Apply type filter
        if self._type_filters:
            filtered = [
                comp for comp in filtered
                if any(f in comp.get('type', '').lower() for f in self._type_filters)
            ]

        return filtered if filtered else self._components

    def _sort_components(self, components):
        if self._layout_mode == "grid":
            return sorted(components, key=lambda x: x.get('name', 'Z'))
        elif self._layout_mode == "type":
            return sorted(components, key=lambda x: x.get('type', ''))
        elif self._layout_mode == "function":
            return sorted(components, key=lambda x: x.get('function', ''))
        elif self._layout_mode == "size":
            return sorted(components, key=lambda x: x.get('diameter_um', 0) or x.get('diameter_nm', 0)/1000, reverse=True)
        elif self._layout_mode == "copy_number":
            return sorted(components, key=lambda x: x.get('copy_number_per_cell', 0), reverse=True)
        return components

    def _calculate_card_size(self, comp):
        base = 130
        if self._size_property == "none":
            return base
        elif self._size_property == "copy_number":
            import math
            copy = comp.get('copy_number_per_cell', 1)
            return int(100 + min(math.log10(max(1, copy)) * 15, 80))
        return base

    def _on_card_clicked(self, comp):
        if self._selected_card:
            self._selected_card.set_selected(False)
        for card in self._cards:
            if card.component == comp:
                card.set_selected(True)
                self._selected_card = card
                break
        self.component_selected.emit(comp)

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

    def get_selected_component(self):
        if self._selected_card:
            return self._selected_card.component
        return None

    def get_component_count(self):
        return len(self._components)

    def set_search_filter(self, text: str):
        """Set search filter by name."""
        self._search_filter = text.lower().strip()
        self._rebuild_grid()

    def get_filtered_count(self):
        """Get count of currently filtered components."""
        return len(self._get_filtered_components())

    def refresh(self):
        self.load_components()
