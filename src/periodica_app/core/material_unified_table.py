"""
Material Unified Table Widget
Main visualization widget for displaying engineering materials with various layouts.
"""

import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QRadialGradient,
                           QLinearGradient, QPainterPath)

from periodica.data.material_data import MaterialDataLoader
from periodica.core.material_enums import MaterialLayoutMode, MaterialCategory, MaterialProperty


class MaterialUnifiedTable(QWidget):
    """Main widget for visualizing engineering materials"""

    # Signals
    material_selected = Signal(dict)
    material_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

        # Data
        self.loader = MaterialDataLoader()
        self.base_materials = list(self.loader.get_all_materials().values())
        self.positioned_materials = []

        # State
        self.layout_mode = MaterialLayoutMode.CATEGORY
        self.hovered_material = None
        self.selected_material = None

        # Filters
        self.category_filters = list(MaterialCategory)
        self.search_filter = ""

        # Visual settings
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0

        # Visual property encoding settings
        self.fill_property = MaterialProperty.DENSITY
        self.border_color_property = MaterialProperty.YIELD_STRENGTH
        self.glow_property = MaterialProperty.FRACTURE_TOUGHNESS
        self.card_size_property = MaterialProperty.YOUNGS_MODULUS

        # Scatter plot settings
        self.scatter_x_property = MaterialProperty.YOUNGS_MODULUS
        self.scatter_y_property = MaterialProperty.YIELD_STRENGTH

        # Card dimensions
        self.base_card_width = 120
        self.base_card_height = 80

        # Initialize layout
        self._update_layout()

    def set_layout_mode(self, mode):
        """Set the layout mode"""
        if isinstance(mode, str):
            mode = MaterialLayoutMode.from_string(mode)
        self.layout_mode = mode
        self._update_layout()
        self.update()

    def set_category_filters(self, categories):
        """Set category filter (multi-select list)"""
        self.category_filters = categories if categories else []
        self._update_layout()
        self.update()

    def set_search_filter(self, search_text):
        """Set search filter"""
        self.search_filter = search_text.lower() if search_text else ""
        self._update_layout()
        self.update()

    def set_fill_property(self, prop):
        """Set fill color property"""
        if isinstance(prop, str):
            prop = MaterialProperty.from_string(prop)
        self.fill_property = prop
        self.update()

    def set_scatter_properties(self, x_prop, y_prop):
        """Set scatter plot axes"""
        if isinstance(x_prop, str):
            x_prop = MaterialProperty.from_string(x_prop)
        if isinstance(y_prop, str):
            y_prop = MaterialProperty.from_string(y_prop)
        self.scatter_x_property = x_prop
        self.scatter_y_property = y_prop
        self._update_layout()
        self.update()

    def _filter_materials(self):
        """Filter materials based on current filter settings"""
        filtered = []
        for material in self.base_materials:
            # Category filter
            category = MaterialCategory.from_string(material.get('Category', ''))
            if category not in self.category_filters:
                continue

            # Search filter
            if self.search_filter:
                name = material.get('Name', '').lower()
                desc = material.get('Description', '').lower()
                cat = material.get('Category', '').lower()
                if not (self.search_filter in name or
                        self.search_filter in desc or
                        self.search_filter in cat):
                    continue

            filtered.append(material)
        return filtered

    def _update_layout(self):
        """Update material positions based on current layout mode"""
        filtered = self._filter_materials()
        self.positioned_materials = []

        if not filtered:
            return

        if self.layout_mode == MaterialLayoutMode.CATEGORY:
            self._layout_by_category(filtered)
        elif self.layout_mode == MaterialLayoutMode.PROPERTY_SCATTER:
            self._layout_scatter(filtered)
        elif self.layout_mode == MaterialLayoutMode.STRENGTH_STIFFNESS:
            self._layout_strength_stiffness(filtered)
        elif self.layout_mode == MaterialLayoutMode.THERMAL_MAP:
            self._layout_thermal_map(filtered)

    def _layout_by_category(self, materials):
        """Layout materials grouped by category"""
        width = max(self.width(), 800)
        margin = 40
        card_spacing = 20

        # Group by category
        categories = {}
        for mat in materials:
            cat = MaterialCategory.from_string(mat.get('Category', ''))
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(mat)

        # Layout each category
        y = margin
        for cat in MaterialCategory:
            if cat not in categories:
                continue

            cat_materials = categories[cat]
            x = margin

            # Category header space
            y += 30

            for mat in cat_materials:
                if x + self.base_card_width + card_spacing > width - margin:
                    x = margin
                    y += self.base_card_height + card_spacing

                self.positioned_materials.append({
                    'material': mat,
                    'x': x,
                    'y': y,
                    'width': self.base_card_width,
                    'height': self.base_card_height,
                    'category': cat
                })
                x += self.base_card_width + card_spacing

            y += self.base_card_height + card_spacing + 20

        self.setMinimumHeight(int(y + margin))

    def _layout_scatter(self, materials):
        """Layout materials as scatter plot based on X/Y properties"""
        width = max(self.width() - 100, 600)
        height = max(self.height() - 100, 400)
        margin = 80

        # Get property values
        x_values = [MaterialProperty.get_value_from_material(self.scatter_x_property, m) for m in materials]
        y_values = [MaterialProperty.get_value_from_material(self.scatter_y_property, m) for m in materials]

        x_min, x_max = min(x_values) if x_values else 0, max(x_values) if x_values else 1
        y_min, y_max = min(y_values) if y_values else 0, max(y_values) if y_values else 1

        # Avoid division by zero
        x_range = x_max - x_min if x_max != x_min else 1
        y_range = y_max - y_min if y_max != y_min else 1

        for i, mat in enumerate(materials):
            x_norm = (x_values[i] - x_min) / x_range
            y_norm = (y_values[i] - y_min) / y_range

            self.positioned_materials.append({
                'material': mat,
                'x': margin + x_norm * (width - 2 * margin),
                'y': margin + (1 - y_norm) * (height - 2 * margin),  # Flip Y
                'width': 60,
                'height': 40,
                'category': MaterialCategory.from_string(mat.get('Category', ''))
            })

    def _layout_strength_stiffness(self, materials):
        """Ashby-style plot of specific strength vs specific stiffness"""
        self.scatter_x_property = MaterialProperty.SPECIFIC_STIFFNESS
        self.scatter_y_property = MaterialProperty.SPECIFIC_STRENGTH
        self._layout_scatter(materials)

    def _layout_thermal_map(self, materials):
        """Layout based on thermal properties"""
        self.scatter_x_property = MaterialProperty.THERMAL_CONDUCTIVITY
        self.scatter_y_property = MaterialProperty.MELTING_POINT
        self._layout_scatter(materials)

    def paintEvent(self, event):
        """Paint the material visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(20, 20, 35))

        # Draw title
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(20, 30, "Engineering Materials")

        # Draw category headers if in category mode
        if self.layout_mode == MaterialLayoutMode.CATEGORY:
            self._draw_category_headers(painter)

        # Draw scatter axes if in scatter mode
        if self.layout_mode in [MaterialLayoutMode.PROPERTY_SCATTER,
                                 MaterialLayoutMode.STRENGTH_STIFFNESS,
                                 MaterialLayoutMode.THERMAL_MAP]:
            self._draw_scatter_axes(painter)

        # Draw materials
        for pos in self.positioned_materials:
            self._draw_material_card(painter, pos)

        painter.end()

    def _draw_category_headers(self, painter):
        """Draw category section headers"""
        header_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(header_font)

        # Group positions by category
        categories_drawn = set()
        for pos in self.positioned_materials:
            cat = pos['category']
            if cat not in categories_drawn:
                color = QColor(MaterialCategory.get_color(cat))
                painter.setPen(color)
                painter.drawText(int(pos['x']), int(pos['y'] - 10), cat.value)
                categories_drawn.add(cat)

    def _draw_scatter_axes(self, painter):
        """Draw axes for scatter plot"""
        margin = 80
        width = self.width() - margin
        height = self.height() - margin

        painter.setPen(QPen(QColor(100, 100, 120), 2))

        # X axis
        painter.drawLine(margin, height, width, height)
        # Y axis
        painter.drawLine(margin, margin, margin, height)

        # Labels
        label_font = QFont("Segoe UI", 9)
        painter.setFont(label_font)
        painter.setPen(QColor(180, 180, 200))

        x_label = MaterialProperty.get_display_name(self.scatter_x_property)
        y_label = MaterialProperty.get_display_name(self.scatter_y_property)

        painter.drawText(int(width / 2), int(height + 40), x_label)
        painter.save()
        painter.translate(30, int(height / 2))
        painter.rotate(-90)
        painter.drawText(0, 0, y_label)
        painter.restore()

    def _draw_material_card(self, painter, pos):
        """Draw a single material card"""
        material = pos['material']
        x, y = pos['x'], pos['y']
        w, h = pos['width'], pos['height']
        category = pos['category']

        is_hovered = self.hovered_material == material
        is_selected = self.selected_material == material

        # Card background
        base_color = QColor(MaterialCategory.get_color(category))
        if is_hovered:
            base_color = base_color.lighter(130)
        if is_selected:
            base_color = base_color.lighter(150)

        # Create gradient
        gradient = QLinearGradient(x, y, x, y + h)
        gradient.setColorAt(0, base_color.lighter(120))
        gradient.setColorAt(1, base_color.darker(110))

        # Draw card
        card_rect = QRectF(x, y, w, h)
        painter.setBrush(QBrush(gradient))

        border_color = QColor(255, 255, 255, 100) if is_hovered else QColor(0, 0, 0, 50)
        border_width = 3 if is_selected else (2 if is_hovered else 1)
        painter.setPen(QPen(border_color, border_width))

        painter.drawRoundedRect(card_rect, 8, 8)

        # Draw name
        name = material.get('Name', 'Unknown')
        if len(name) > 15:
            name = name[:14] + '...'

        name_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(name_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(card_rect.adjusted(5, 5, -5, -h/2), Qt.AlignmentFlag.AlignLeft, name)

        # Draw key property
        yield_str = material.get('StrengthProperties', {}).get('YieldStrength_MPa', 0)
        prop_font = QFont("Segoe UI", 7)
        painter.setFont(prop_font)
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(card_rect.adjusted(5, h/2, -5, -5),
                        Qt.AlignmentFlag.AlignLeft,
                        f"σy: {yield_str:.0f} MPa")

    def mouseMoveEvent(self, event):
        """Handle mouse move for hover detection"""
        pos = event.position()
        old_hovered = self.hovered_material

        self.hovered_material = None
        for item in self.positioned_materials:
            rect = QRectF(item['x'], item['y'], item['width'], item['height'])
            if rect.contains(pos):
                self.hovered_material = item['material']
                break

        if old_hovered != self.hovered_material:
            if self.hovered_material:
                self.material_hovered.emit(self.hovered_material)
            self.update()

    def mousePressEvent(self, event):
        """Handle mouse press for selection"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.hovered_material:
                self.selected_material = self.hovered_material
                self.material_selected.emit(self.selected_material)
                self.update()

    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        self._update_layout()

    def get_selected_material(self):
        """Get currently selected material"""
        return self.selected_material

    def select_material_by_name(self, name):
        """Select a material by name"""
        for mat in self.base_materials:
            if mat.get('Name') == name:
                self.selected_material = mat
                self.material_selected.emit(mat)
                self.update()
                return True
        return False

    def get_all_materials(self):
        """Get all loaded materials"""
        return self.base_materials
