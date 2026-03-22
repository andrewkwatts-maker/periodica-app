"""
Biomaterial Table Widget
Displays biological materials in a grid layout with visual property encoding.
"""

import json
import math
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                                QScrollArea, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import (QFont, QPainter, QColor, QBrush, QPen)

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.biomaterial_enums import BiomaterialType, ECMComponent


class BiomaterialCard(QFrame):
    """Individual biomaterial card widget."""

    clicked = Signal(dict)

    def __init__(self, material, parent=None):
        super().__init__(parent)
        self.material = material
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
            mat_type = self.material.get('type', 'other')
            return BiomaterialType.get_color(mat_type)
        elif self._color_property == "stiffness":
            mech = self.material.get('mechanical_properties', {})
            E = mech.get('youngs_modulus_MPa', 1)
            if E < 1:
                return "#4CAF50"    # Green - very soft
            elif E < 100:
                return "#2196F3"    # Blue - soft
            elif E < 1000:
                return "#FF9800"    # Orange - intermediate
            elif E < 10000:
                return "#F44336"    # Red - stiff
            else:
                return "#9C27B0"    # Purple - hard (bone)
        elif self._color_property == "organ_system":
            system = self.material.get('organ_system', 'other')
            systems = {
                'skeletal': '#FFF8E1',
                'musculoskeletal': '#E8F5E9',
                'muscular': '#FFEBEE',
                'cardiovascular': '#FCE4EC',
                'nervous': '#FFF3E0',
                'digestive': '#EFEBE9',
                'respiratory': '#E3F2FD',
                'integumentary': '#FFCCBC',
                'endocrine': '#F3E5F5',
            }
            return systems.get(system, '#9E9E9E')
        return ThemeColors.ACCENT

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Draw type indicator at top
        mat_type = self.material.get('type', 'unknown').replace('_', ' ').title()
        if len(mat_type) > 15:
            mat_type = mat_type[:13] + ".."
        painter.setPen(QPen(QColor(180, 180, 180)))
        painter.setFont(QFont("Arial", max(7, int(self._current_size * 0.07))))
        painter.drawText(8, 14, mat_type)

        # Draw name in center
        name = self.material.get('name', '?')
        if len(name) > 16:
            name = name[:14] + ".."

        color = QColor(self._get_property_color())
        painter.setPen(QPen(color, 2))
        font_size = max(9, int(self._current_size * 0.09))
        painter.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, name)

        # Draw modulus at bottom
        mech = self.material.get('mechanical_properties', {})
        E = mech.get('youngs_modulus_MPa', 0)
        if E >= 1000:
            E_str = f"E={E/1000:.1f} GPa"
        elif E >= 1:
            E_str = f"E={E:.1f} MPa"
        else:
            E_str = f"E={E*1000:.1f} kPa"

        painter.setPen(QPen(QColor(150, 150, 150)))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(8, h - 5, E_str)

        # Draw stiffness bar
        derived = self.material.get('derived_properties', {})
        category = derived.get('stiffness_category', 'Soft')
        painter.drawText(w - 60, h - 5, category)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.material)


class BiomaterialTableWidget(QWidget):
    """Widget displaying biological materials in a grid layout."""

    biomaterial_selected = Signal(dict)
    biomaterial_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._materials = []
        self._cards = []
        self._selected_card = None
        self._layout_mode = "grid"
        self._color_property = "type"
        self._size_property = "none"
        self._type_filters = []
        self._stiffness_filters = []
        self._search_filter = ""
        self._property_filters = {}  # {property_key: (min, max)}

        self.setup_ui()
        self.load_materials()

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

    def load_materials(self):
        mat_dir = Path(__file__).parent.parent / "data" / "active" / "biological_materials"
        self._materials = []

        if mat_dir.exists():
            for json_file in sorted(mat_dir.glob("*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._materials.append(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        self._rebuild_grid()

    def _rebuild_grid(self):
        for card in self._cards:
            card.deleteLater()
        self._cards = []

        filtered = self._get_filtered_materials()
        sorted_mats = self._sort_materials(filtered)
        cols = 4

        for i, mat in enumerate(sorted_mats):
            card = BiomaterialCard(mat)
            card.set_color_property(self._color_property)
            size = self._calculate_card_size(mat)
            card.set_size(size)
            card.clicked.connect(self._on_card_clicked)

            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)
            self._cards.append(card)

    def _get_filtered_materials(self):
        filtered = self._materials

        # Apply search filter
        if self._search_filter:
            search_lower = self._search_filter.lower()
            filtered = [m for m in filtered
                        if search_lower in m.get('name', '').lower()
                        or search_lower in m.get('type', '').lower()
                        or search_lower in m.get('organ_system', '').lower()]

        # Apply type filters
        if self._type_filters:
            filtered = [m for m in filtered
                        if any(f in m.get('type', '').lower() for f in self._type_filters)]

        # Apply stiffness category filters
        if self._stiffness_filters:
            filtered = [m for m in filtered
                        if m.get('derived_properties', {}).get('stiffness_category', '') in self._stiffness_filters]

        # Apply property range filters
        for prop_key, (min_val, max_val) in self._property_filters.items():
            if prop_key == "fill_color":
                # Filter by the currently selected color property
                filtered = self._apply_property_range_filter(filtered, self._color_property, min_val, max_val)

        return filtered if filtered else self._materials

    def _apply_property_range_filter(self, materials, prop, min_val, max_val):
        """Apply a property range filter."""
        result = []
        for m in materials:
            value = self._get_property_value(m, prop)
            if value is not None and min_val <= value <= max_val:
                result.append(m)
        return result if result else materials

    def _get_property_value(self, material, prop):
        """Get a property value from a material for filtering."""
        if prop == "stiffness":
            return material.get('mechanical_properties', {}).get('youngs_modulus_MPa', 0)
        elif prop == "density":
            return material.get('physical_properties', {}).get('density_g_cm3', 0)
        elif prop == "porosity":
            return material.get('porosity', 0)
        elif prop == "water_content":
            return material.get('physical_properties', {}).get('water_content_percent', 0)
        return None

    def _sort_materials(self, materials):
        if self._layout_mode == "grid":
            return sorted(materials, key=lambda x: x.get('name', 'Z'))
        elif self._layout_mode == "type":
            return sorted(materials, key=lambda x: x.get('type', ''))
        elif self._layout_mode == "stiffness":
            return sorted(materials,
                          key=lambda x: x.get('mechanical_properties', {}).get('youngs_modulus_MPa', 0),
                          reverse=True)
        elif self._layout_mode == "density":
            return sorted(materials,
                          key=lambda x: x.get('physical_properties', {}).get('density_g_cm3', 0),
                          reverse=True)
        elif self._layout_mode == "organ_system":
            return sorted(materials, key=lambda x: x.get('organ_system', ''))
        return materials

    def _calculate_card_size(self, mat):
        base = 130
        if self._size_property == "none":
            return base
        elif self._size_property == "stiffness":
            mech = mat.get('mechanical_properties', {})
            E = mech.get('youngs_modulus_MPa', 1)
            return int(100 + min(math.log10(max(0.001, E)) * 15, 80))
        elif self._size_property == "density":
            phys = mat.get('physical_properties', {})
            rho = phys.get('density_g_cm3', 1)
            return int(90 + rho * 30)
        return base

    def _on_card_clicked(self, mat):
        if self._selected_card:
            self._selected_card.set_selected(False)
        for card in self._cards:
            if card.material == mat:
                card.set_selected(True)
                self._selected_card = card
                break
        self.biomaterial_selected.emit(mat)

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

    def set_stiffness_filters(self, categories):
        """Set stiffness category filters."""
        self._stiffness_filters = categories
        self._rebuild_grid()

    def set_search_filter(self, text):
        """Set search filter text."""
        self._search_filter = text.strip()
        self._rebuild_grid()

    def set_property_filter(self, property_key, min_val, max_val):
        """Set a property range filter."""
        self._property_filters[property_key] = (min_val, max_val)
        self._rebuild_grid()

    def get_filtered_count(self):
        """Get the count of currently filtered materials."""
        return len(self._get_filtered_materials())

    def get_selected_material(self):
        if self._selected_card:
            return self._selected_card.material
        return None

    def get_material_count(self):
        return len(self._materials)

    def refresh(self):
        self.load_materials()
