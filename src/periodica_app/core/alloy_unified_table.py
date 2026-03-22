"""
Alloy Unified Table Widget
Main visualization widget for displaying alloys with various layouts.
Features microstructure visualization using crystalline_math module.
"""

import json
import math
from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QRadialGradient,
                           QLinearGradient, QPainterPath, QImage, QPixmap, QGuiApplication)

from periodica.data.alloy_loader import AlloyDataLoader
from periodica.core.alloy_enums import (AlloyLayoutMode, AlloyCategory, CrystalStructure,
                               AlloyProperty, get_element_color)
from periodica_app.layouts.alloy_category_layout import AlloyCategoryLayout
from periodica_app.layouts.alloy_property_layout import AlloyPropertyLayout
from periodica_app.layouts.alloy_composition_layout import AlloyCompositionLayout
from periodica_app.layouts.alloy_lattice_layout import AlloyLatticeLayout

# Import crystalline math for microstructure visualization
try:
    from periodica.utils.crystalline_math import (
        VoronoiTessellation, PerlinNoise, SimplexNoise,
        MicrostructureRenderer, generate_noise_phase_map
    )
    HAS_CRYSTALLINE_MATH = True
except ImportError:
    HAS_CRYSTALLINE_MATH = False


class AlloyUnifiedTable(QWidget):
    """Main widget for visualizing alloys"""

    # Signals
    alloy_selected = Signal(dict)
    alloy_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

        # Data
        self.loader = AlloyDataLoader()
        self.base_alloys = self.loader.load_all_alloys()
        self.positioned_alloys = []

        # State
        self.layout_mode = AlloyLayoutMode.CATEGORY
        self.hovered_alloy = None
        self.selected_alloy = None

        # Filters (single-value, legacy)
        self.category_filter = None
        self.structure_filter = None
        self.element_filter = None

        # Filters (multi-select)
        self.category_filters = ['Steel', 'Aluminum', 'Copper', 'Titanium', 'Nickel', 'Precious']  # All by default
        self.structure_filters = ['FCC', 'BCC', 'HCP']  # All by default
        self.corrosion_filters = ['Excellent', 'Good', 'Moderate', 'Poor']  # All by default

        # Visual settings
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.scroll_offset_y = 0

        # Visual property encoding settings
        self.fill_property = "Density"
        self.border_color_property = "Melting Point"
        self.glow_property = "Tensile Strength"
        self.glow_intensity_property = "Corrosion Resistance"
        self.symbol_text_color_property = "Young's Modulus"
        self.border_size_property = "Hardness (Brinell)"
        self.card_size_property = "Yield Strength"

        # Scatter plot settings
        self.scatter_x_property = 'density'
        self.scatter_y_property = 'tensile_strength'

        # Layout renderers
        self.layouts = {
            AlloyLayoutMode.CATEGORY: AlloyCategoryLayout(self.width(), self.height()),
            AlloyLayoutMode.PROPERTY_SCATTER: AlloyPropertyLayout(self.width(), self.height()),
            AlloyLayoutMode.COMPOSITION: AlloyCompositionLayout(self.width(), self.height()),
            AlloyLayoutMode.LATTICE: AlloyLatticeLayout(self.width(), self.height()),
        }

        # Initialize layout
        self._update_layout()

    def set_layout_mode(self, mode):
        """Set the layout mode"""
        if isinstance(mode, str):
            mode = AlloyLayoutMode.from_string(mode)
        self.layout_mode = mode
        self._update_layout()
        self.update()

    def set_category_filter(self, category):
        """Set category filter"""
        self.category_filter = category
        self._update_layout()
        self.update()

    def set_structure_filter(self, structure):
        """Set crystal structure filter"""
        self.structure_filter = structure
        self._update_layout()
        self.update()

    def set_element_filter(self, element):
        """Set primary element filter"""
        self.element_filter = element
        self._update_layout()
        self.update()

    def set_category_filters(self, categories):
        """Set category filter (multi-select list)

        Args:
            categories: List of category names to show, e.g. ['Steel', 'Aluminum', 'Copper']
        """
        self.category_filters = categories if categories else []
        self._update_layout()
        self.update()

    def set_structure_filters(self, structures):
        """Set crystal structure filter (multi-select list)

        Args:
            structures: List of crystal structures to show, e.g. ['FCC', 'BCC', 'HCP']
        """
        self.structure_filters = structures if structures else []
        self._update_layout()
        self.update()

    def set_corrosion_filters(self, ratings):
        """Set corrosion resistance filter (multi-select list)

        Args:
            ratings: List of corrosion resistance ratings to show, e.g. ['Excellent', 'Good']
        """
        self.corrosion_filters = ratings if ratings else []
        self._update_layout()
        self.update()

    def set_scatter_properties(self, x_prop, y_prop):
        """Set properties for scatter plot axes"""
        self.scatter_x_property = x_prop
        self.scatter_y_property = y_prop
        layout = self.layouts.get(AlloyLayoutMode.PROPERTY_SCATTER)
        if layout:
            layout.set_x_property(x_prop)
            layout.set_y_property(y_prop)
        if self.layout_mode == AlloyLayoutMode.PROPERTY_SCATTER:
            self._update_layout()
            self.update()

    def _get_filtered_alloys(self):
        """Get alloys after applying filters"""
        alloys = self.base_alloys.copy()

        # Apply multi-select category filter
        if self.category_filters:
            alloys = [a for a in alloys if self._matches_category(a)]
        elif self.category_filter:  # Legacy single-value filter
            alloys = [a for a in alloys if a.get('category', '').lower() == self.category_filter.lower()]

        # Apply multi-select structure filter
        if self.structure_filters:
            alloys = [a for a in alloys if self._matches_structure(a)]
        elif self.structure_filter:  # Legacy single-value filter
            alloys = [a for a in alloys if a.get('crystal_structure', '').upper() == self.structure_filter.upper()]

        # Apply multi-select corrosion filter
        if self.corrosion_filters:
            alloys = [a for a in alloys if self._matches_corrosion(a)]

        # Apply element filter (single value only)
        if self.element_filter:
            alloys = [a for a in alloys if a.get('primary_element') == self.element_filter]

        return alloys

    def _matches_category(self, alloy):
        """Check if alloy matches category filter"""
        if not self.category_filters:
            return True  # No filter, show all
        alloy_category = alloy.get('category', '')
        # Check both exact match and case-insensitive match
        return (alloy_category in self.category_filters or
                alloy_category.title() in self.category_filters or
                alloy_category.lower() in [c.lower() for c in self.category_filters])

    def _matches_structure(self, alloy):
        """Check if alloy matches crystal structure filter"""
        if not self.structure_filters:
            return True  # No filter, show all
        alloy_structure = alloy.get('crystal_structure', '').upper()
        return alloy_structure in [s.upper() for s in self.structure_filters]

    def _matches_corrosion(self, alloy):
        """Check if alloy matches corrosion resistance filter"""
        if not self.corrosion_filters:
            return True  # No filter, show all

        # Check corrosion_resistance field
        corrosion = alloy.get('corrosion_resistance', '')
        if not corrosion:
            # Try to infer from other properties
            corrosion = alloy.get('corrosion_rating', '')

        # Normalize the rating
        if isinstance(corrosion, str):
            corrosion_normalized = corrosion.title()
            return (corrosion_normalized in self.corrosion_filters or
                    corrosion in self.corrosion_filters)

        # If no corrosion data and all filters selected, show by default
        return len(self.corrosion_filters) == 4

    def _update_layout(self):
        """Recalculate positions for all alloys"""
        alloys = self._get_filtered_alloys()
        layout = self.layouts.get(self.layout_mode)

        if layout:
            layout.update_dimensions(self.width(), self.height())
            self.positioned_alloys = layout.calculate_layout(alloys)

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        for layout in self.layouts.values():
            layout.update_dimensions(self.width(), self.height())
        self._update_layout()

    def paintEvent(self, event):
        """Paint the alloy visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        self._draw_background(painter)

        # Apply transformations
        painter.translate(self.pan_x, self.pan_y - self.scroll_offset_y)
        painter.scale(self.zoom_level, self.zoom_level)

        # Draw based on layout mode
        if self.layout_mode == AlloyLayoutMode.PROPERTY_SCATTER:
            self._draw_scatter_plot(painter)
        else:
            # Draw group headers if applicable
            self._draw_group_headers(painter)
            # Draw alloy cards
            for alloy in self.positioned_alloys:
                self._draw_alloy_card(painter, alloy)

        painter.end()

    def _draw_background(self, painter):
        """Draw the dark gradient background"""
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(15, 15, 30))
        gradient.setColorAt(1, QColor(30, 30, 50))
        painter.fillRect(self.rect(), QBrush(gradient))

    def _draw_group_headers(self, painter):
        """Draw group section headers"""
        layout = self.layouts.get(self.layout_mode)
        if not hasattr(layout, 'get_group_headers'):
            return

        headers = layout.get_group_headers(self.positioned_alloys)

        for header in headers:
            y = header.get('y', 0)
            name = header.get('name', '')
            color = header.get('color', '#FFFFFF')
            count = header.get('count', 0)
            description = header.get('description', '')

            # Draw header background
            header_rect = QRectF(20, y, self.width() - 40, 40)
            painter.setPen(Qt.PenStyle.NoPen)

            header_color = QColor(color)
            header_color.setAlpha(50)
            painter.setBrush(QBrush(header_color))
            painter.drawRoundedRect(header_rect, 8, 8)

            # Draw header text
            painter.setPen(QPen(QColor(color)))
            painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            text = f"{name} ({count})"
            painter.drawText(header_rect.adjusted(15, 0, 0, -5 if description else 0),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                           text)

            # Draw description if present
            if description:
                painter.setFont(QFont("Arial", 9))
                painter.setPen(QPen(QColor(200, 200, 200, 180)))
                desc_rect = QRectF(header_rect.left() + 15, header_rect.bottom() - 18,
                                   header_rect.width() - 30, 15)
                # Truncate description
                short_desc = description[:80] + '...' if len(description) > 80 else description
                painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft, short_desc)

            # Draw accent line
            painter.setPen(QPen(QColor(color), 3))
            painter.drawLine(int(header_rect.left() + 5), int(header_rect.bottom() + 2),
                           int(header_rect.left() + 100), int(header_rect.bottom() + 2))

    def _draw_scatter_plot(self, painter):
        """Draw scatter plot visualization"""
        layout = self.layouts.get(AlloyLayoutMode.PROPERTY_SCATTER)
        axis_info = layout.get_axis_info()
        ticks = layout.get_axis_ticks()

        if not axis_info:
            return

        # Draw axes
        painter.setPen(QPen(QColor(100, 100, 120), 2))

        # X axis
        painter.drawLine(int(axis_info['plot_left']), int(axis_info['plot_bottom']),
                        int(axis_info['plot_right']), int(axis_info['plot_bottom']))

        # Y axis
        painter.drawLine(int(axis_info['plot_left']), int(axis_info['plot_bottom']),
                        int(axis_info['plot_left']), int(axis_info['plot_top']))

        # Draw tick marks and labels
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QPen(QColor(150, 150, 170)))

        for tick in ticks['x_ticks']:
            x = tick['position']
            y = axis_info['plot_bottom']
            painter.drawLine(int(x), int(y), int(x), int(y + 5))
            label = f"{tick['value']:.1f}" if tick['value'] < 100 else f"{int(tick['value'])}"
            painter.drawText(int(x - 20), int(y + 20), label)

        for tick in ticks['y_ticks']:
            x = axis_info['plot_left']
            y = tick['position']
            painter.drawLine(int(x - 5), int(y), int(x), int(y))
            label = f"{tick['value']:.0f}" if tick['value'] >= 10 else f"{tick['value']:.1f}"
            painter.drawText(int(x - 50), int(y + 5), label)

        # Draw axis labels
        painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(180, 180, 200)))

        x_label = AlloyProperty.get_display_name(axis_info['x_property'])
        x_unit = AlloyProperty.get_unit(axis_info['x_property'])
        painter.drawText(int((axis_info['plot_left'] + axis_info['plot_right']) / 2 - 50),
                        int(axis_info['plot_bottom'] + 45),
                        f"{x_label} ({x_unit})")

        # Y axis label (rotated)
        painter.save()
        painter.translate(20, (axis_info['plot_top'] + axis_info['plot_bottom']) / 2)
        painter.rotate(-90)
        y_label = AlloyProperty.get_display_name(axis_info['y_property'])
        y_unit = AlloyProperty.get_unit(axis_info['y_property'])
        painter.drawText(-50, 0, f"{y_label} ({y_unit})")
        painter.restore()

        # Draw data points
        for alloy in self.positioned_alloys:
            self._draw_scatter_point(painter, alloy)

    def _draw_scatter_point(self, painter, alloy):
        """Draw a single point in the scatter plot"""
        x = alloy.get('x', 0)
        y = alloy.get('y', 0)
        size = alloy.get('width', 60)

        is_hovered = alloy == self.hovered_alloy
        is_selected = alloy == self.selected_alloy

        category_color = QColor(alloy.get('category_color', '#C0C0C0'))

        # Draw glow for hover/selection
        if is_hovered or is_selected:
            glow_color = QColor(category_color)
            glow_color.setAlpha(100)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x + size/2, y + size/2), size * 0.8, size * 0.8)

        # Draw point
        gradient = QRadialGradient(x + size/2, y + size/2, size/2)
        gradient.setColorAt(0, category_color.lighter(130))
        gradient.setColorAt(0.7, category_color)
        gradient.setColorAt(1, category_color.darker(120))

        painter.setBrush(QBrush(gradient))
        if is_selected:
            painter.setPen(QPen(QColor(255, 255, 255), 3))
        elif is_hovered:
            painter.setPen(QPen(category_color.lighter(150), 2))
        else:
            painter.setPen(QPen(category_color.darker(120), 1))

        painter.drawEllipse(QPointF(x + size/2, y + size/2), size/2 - 2, size/2 - 2)

        # Draw label on hover
        if is_hovered or is_selected:
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            name = alloy.get('name', '')[:15]
            painter.drawText(int(x + size + 5), int(y + size/2 + 5), name)

    def _draw_alloy_card(self, painter, alloy):
        """Draw a single alloy card with visual property encoding"""
        x = alloy.get('x', 0)
        y = alloy.get('y', 0)
        width = alloy.get('width', 160)
        height = alloy.get('height', 180)

        is_hovered = alloy == self.hovered_alloy
        is_selected = alloy == self.selected_alloy

        # Get visual encoding colors
        fill_value = self.get_normalized_property_value(alloy, self.fill_property)
        border_value = self.get_normalized_property_value(alloy, self.border_color_property)
        glow_value = self.get_normalized_property_value(alloy, self.glow_property)
        glow_intensity = self.get_normalized_property_value(alloy, self.glow_intensity_property)

        # Get custom gradient colors if set
        fill_start, fill_end = (QColor(64, 128, 255), QColor(255, 128, 64))
        border_start, border_end = (QColor(100, 100, 150), QColor(255, 200, 100))
        glow_start, glow_end = (QColor(80, 80, 200), QColor(255, 100, 100))

        if hasattr(self, 'gradient_colors'):
            if 'fill_color' in self.gradient_colors:
                fill_start, fill_end = self.gradient_colors['fill_color']
            if 'border_color' in self.gradient_colors:
                border_start, border_end = self.gradient_colors['border_color']
            if 'glow_color' in self.gradient_colors:
                glow_start, glow_end = self.gradient_colors['glow_color']

        # Compute encoded colors
        fill_color = self.get_color_from_gradient(fill_value, fill_start, fill_end)
        border_color = self.get_color_from_gradient(border_value, border_start, border_end)
        glow_color = self.get_color_from_gradient(glow_value, glow_start, glow_end)

        # Get border size from encoding
        border_size_value = self.get_normalized_property_value(alloy, self.border_size_property)
        border_width = 1 + border_size_value * 4  # 1-5 pixels

        # Card background
        card_rect = QRectF(x, y, width, height)

        # Get category color (fallback)
        category_color = QColor(AlloyCategory.get_color(alloy.get('category', 'Other')))

        # Draw glow effect based on glow intensity
        if glow_intensity > 0.1 or is_hovered or is_selected:
            glow_alpha = int(80 + glow_intensity * 120) if not (is_hovered or is_selected) else 150
            glow_radius = 8 + glow_intensity * 12
            glow_color_with_alpha = QColor(glow_color)
            glow_color_with_alpha.setAlpha(glow_alpha)

            glow_gradient = QRadialGradient(x + width/2, y + height/2, glow_radius + width/2)
            glow_gradient.setColorAt(0, glow_color_with_alpha)
            glow_gradient.setColorAt(0.5, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), glow_alpha // 2))
            glow_gradient.setColorAt(1, QColor(0, 0, 0, 0))

            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x - glow_radius, y - glow_radius,
                                           width + 2*glow_radius, height + 2*glow_radius), 15, 15)

        # Gradient background with fill color encoding
        gradient = QLinearGradient(x, y, x, y + height)
        if is_selected:
            gradient.setColorAt(0, QColor(fill_color.red()//2 + 40, fill_color.green()//2 + 40,
                                          fill_color.blue()//2 + 50, 230))
            gradient.setColorAt(1, QColor(fill_color.red()//3 + 30, fill_color.green()//3 + 30,
                                          fill_color.blue()//3 + 40, 230))
        elif is_hovered:
            gradient.setColorAt(0, QColor(fill_color.red()//2 + 35, fill_color.green()//2 + 35,
                                          fill_color.blue()//2 + 45, 210))
            gradient.setColorAt(1, QColor(fill_color.red()//3 + 25, fill_color.green()//3 + 25,
                                          fill_color.blue()//3 + 35, 210))
        else:
            gradient.setColorAt(0, QColor(fill_color.red()//3 + 28, fill_color.green()//3 + 28,
                                          fill_color.blue()//3 + 37, 190))
            gradient.setColorAt(1, QColor(fill_color.red()//4 + 20, fill_color.green()//4 + 20,
                                          fill_color.blue()//4 + 27, 190))

        painter.setBrush(QBrush(gradient))

        # Border with encoded color and size
        if is_selected:
            painter.setPen(QPen(border_color.lighter(130), border_width + 2))
        elif is_hovered:
            painter.setPen(QPen(border_color.lighter(120), border_width + 1))
        else:
            painter.setPen(QPen(border_color, border_width))

        painter.drawRoundedRect(card_rect, 10, 10)

        # Draw microstructure preview
        self._draw_microstructure_preview(painter, alloy, x + 10, y + 10, width - 20, 70)

        # Draw alloy info with encoded text colors
        self._draw_alloy_info(painter, alloy, x, y, width, height)

    def _draw_microstructure_preview(self, painter, alloy, x, y, width, height):
        """Draw a simplified microstructure preview"""
        # Draw background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 40)))
        painter.drawRoundedRect(QRectF(x, y, width, height), 5, 5)

        # Draw simplified Voronoi-like grain structure
        structure = alloy.get('crystal_structure', 'FCC')
        structure_color = QColor(CrystalStructure.get_color(structure))

        # Generate some pseudo-random grain centers based on alloy name
        seed = sum(ord(c) for c in alloy.get('name', 'alloy'))
        num_grains = 8 + (seed % 5)

        grain_centers = []
        for i in range(num_grains):
            gx = x + 10 + ((seed * (i + 1) * 17) % int(width - 20))
            gy = y + 10 + ((seed * (i + 1) * 23) % int(height - 20))
            grain_centers.append((gx, gy))

        # Draw grains as colored regions
        for i, (gx, gy) in enumerate(grain_centers):
            # Color variation based on IPF-like coloring
            hue = (seed + i * 30) % 360
            grain_color = QColor.fromHsv(hue, 120, 180, 150)

            # Draw gradient grain
            grain_gradient = QRadialGradient(gx, gy, 25)
            grain_gradient.setColorAt(0, grain_color)
            grain_gradient.setColorAt(1, grain_color.darker(150))

            painter.setBrush(QBrush(grain_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(gx, gy), 15, 12)

        # Draw grain boundaries
        painter.setPen(QPen(QColor(20, 20, 30), 1))
        for i, (gx, gy) in enumerate(grain_centers):
            painter.drawEllipse(QPointF(gx, gy), 15, 12)

        # Draw structure label
        painter.setPen(QPen(structure_color))
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(int(x + 3), int(y + height - 3), structure)

    def _draw_alloy_info(self, painter, alloy, x, y, width, height):
        """Draw alloy text information"""
        # Name
        name = alloy.get('name', '')
        painter.setPen(QPen(QColor(220, 220, 240)))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_rect = QRectF(x + 5, y + 85, width - 10, 20)
        # Truncate long names
        display_name = name[:18] + '...' if len(name) > 18 else name
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, display_name)

        # Formula
        formula = alloy.get('formula', '')
        category_color = QColor(AlloyCategory.get_color(alloy.get('category', 'Other')))
        painter.setPen(QPen(category_color))
        painter.setFont(QFont("Arial", 9))
        formula_rect = QRectF(x + 5, y + 103, width - 10, 16)
        painter.drawText(formula_rect, Qt.AlignmentFlag.AlignCenter, formula)

        # Properties
        painter.setPen(QPen(QColor(180, 180, 200, 200)))
        painter.setFont(QFont("Arial", 8))

        # Density
        density = alloy.get('density', 0)
        density_rect = QRectF(x + 5, y + 122, width - 10, 14)
        painter.drawText(density_rect, Qt.AlignmentFlag.AlignCenter, f"{density:.2f} g/cm³")

        # Tensile strength
        tensile = alloy.get('tensile_strength', 0)
        tensile_rect = QRectF(x + 5, y + 136, width - 10, 14)
        painter.drawText(tensile_rect, Qt.AlignmentFlag.AlignCenter, f"{tensile:.0f} MPa")

        # Category badge
        category = alloy.get('category', 'Other')
        badge_rect = QRectF(x + width - 50, y + height - 22, 45, 16)
        painter.setBrush(QBrush(category_color.darker(120)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 3, 3)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 7))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, category[:8])

    def mouseMoveEvent(self, event):
        """Handle mouse movement for hover effects"""
        # Transform mouse position
        x = (event.position().x() - self.pan_x) / self.zoom_level
        y = (event.position().y() - self.pan_y + self.scroll_offset_y) / self.zoom_level

        layout = self.layouts.get(self.layout_mode)
        if layout:
            alloy = layout.get_alloy_at_position(x, y, self.positioned_alloys)

            if alloy != self.hovered_alloy:
                self.hovered_alloy = alloy
                if alloy:
                    self.alloy_hovered.emit(alloy)
                self.update()

    def mousePressEvent(self, event):
        """Handle mouse click for selection"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.hovered_alloy:
                self.selected_alloy = self.hovered_alloy
                self.alloy_selected.emit(self.selected_alloy)
                # Copy alloy data to clipboard
                clipboard_text = json.dumps(self.selected_alloy, indent=2, default=str)
                QGuiApplication.clipboard().setText(clipboard_text)
                self.update()

    def wheelEvent(self, event):
        """Handle scroll wheel for zooming/scrolling"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            self.zoom_level = max(0.5, min(2.0, self.zoom_level * factor))
        else:
            # Scroll
            delta = event.angleDelta().y()
            self.scroll_offset_y = max(0, self.scroll_offset_y - delta / 2)

        self.update()

    def reset_view(self):
        """Reset zoom and scroll to default"""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.scroll_offset_y = 0
        self.update()

    def get_content_height(self):
        """Get the total content height for scrolling"""
        layout = self.layouts.get(self.layout_mode)
        if layout and hasattr(layout, 'get_content_height'):
            return layout.get_content_height(self.positioned_alloys)
        return self.height()

    def reload_data(self):
        """Reload alloy data from files"""
        self.base_alloys = self.loader.load_all_alloys()
        self._update_layout()
        self.update()

    def set_property_filter(self, property_key, min_val, max_val):
        """Set filter range for a property. Items outside the range will be grayed out.

        Args:
            property_key: Visual element key to filter by (fill_color, border_color, etc.)
            min_val: Minimum value for the filter range
            max_val: Maximum value for the filter range
        """
        if not hasattr(self, 'property_filter_ranges'):
            self.property_filter_ranges = {}
        self.property_filter_ranges[property_key] = (min_val, max_val)
        self.update()

    def set_gradient_colors(self, property_key, start_color, end_color):
        """Set custom gradient colors for visual property encoding.

        Args:
            property_key: Visual element key to set gradient for
            start_color: Start color of the gradient (QColor)
            end_color: End color of the gradient (QColor)
        """
        if not hasattr(self, 'gradient_colors'):
            self.gradient_colors = {}
        self.gradient_colors[property_key] = (start_color, end_color)
        self.update()

    def set_property_fade(self, property_key, fade_value):
        """Set fade value for items outside the filter range.

        Args:
            property_key: Visual element key to set fade for
            fade_value: Fade value from 0.0 (no fade) to 1.0 (fully faded)
        """
        if not hasattr(self, 'fade_values'):
            self.fade_values = {}
        self.fade_values[property_key] = fade_value
        self.update()

    def set_visual_property(self, property_key, property_name):
        """Set visual property mapping.

        Args:
            property_key: Visual element key (fill_color, border_color, etc.)
            property_name: Property name to map to this visual element
        """
        attr_map = {
            "fill_color": "fill_property",
            "border_color": "border_color_property",
            "glow_color": "glow_property",
            "glow_intensity": "glow_intensity_property",
            "symbol_text_color": "symbol_text_color_property",
            "border_size": "border_size_property",
            "card_size": "card_size_property"
        }
        attr_name = attr_map.get(property_key)
        if attr_name:
            setattr(self, attr_name, property_name)
            self.update()

    def get_normalized_property_value(self, alloy, property_name):
        """Get normalized property value (0-1) for visual encoding.

        Args:
            alloy: Alloy data dictionary
            property_name: Display name of the property

        Returns:
            Float value between 0 and 1
        """
        # Map display names to internal keys
        property_key_map = {
            "None": None,
            "Density": "density",
            "Melting Point": "melting_point",
            "Thermal Conductivity": "thermal_conductivity",
            "Thermal Expansion": "thermal_expansion",
            "Electrical Resistivity": "electrical_resistivity",
            "Specific Heat": "specific_heat",
            "Tensile Strength": "tensile_strength",
            "Yield Strength": "yield_strength",
            "Fatigue Strength": "fatigue_strength",
            "Hardness (Brinell)": "hardness_brinell",
            "Hardness (Vickers)": "hardness_vickers",
            "Hardness (Rockwell)": "hardness_rockwell",
            "Elongation": "elongation",
            "Reduction of Area": "reduction_of_area",
            "Impact Strength": "impact_strength",
            "Fracture Toughness": "fracture_toughness",
            "Young's Modulus": "youngs_modulus",
            "Shear Modulus": "shear_modulus",
            "Poisson's Ratio": "poissons_ratio",
            "Corrosion Resistance": "corrosion_resistance",
            "PREN": "pren",
            "Pitting Potential": "pitting_potential",
            "Cost per kg": "cost_per_kg"
        }

        # Property ranges for normalization
        property_ranges = {
            "density": (1.0, 25.0),
            "melting_point": (300, 4000),
            "thermal_conductivity": (5, 500),
            "thermal_expansion": (1e-6, 30e-6),
            "electrical_resistivity": (1e-8, 1e-5),
            "specific_heat": (100, 1500),
            "tensile_strength": (50, 3000),
            "yield_strength": (20, 2500),
            "fatigue_strength": (50, 1500),
            "hardness_brinell": (10, 800),
            "hardness_vickers": (50, 2000),
            "hardness_rockwell": (10, 70),
            "elongation": (0, 80),
            "reduction_of_area": (0, 90),
            "impact_strength": (5, 300),
            "fracture_toughness": (10, 200),
            "youngs_modulus": (10, 500),
            "shear_modulus": (10, 200),
            "poissons_ratio": (0.2, 0.5),
            "corrosion_resistance": (0, 100),
            "pren": (0, 50),
            "pitting_potential": (-500, 1000),
            "cost_per_kg": (0.5, 1000)
        }

        key = property_key_map.get(property_name)
        if key is None:
            return 0.5  # Default middle value for "None"

        value = alloy.get(key, 0)
        min_val, max_val = property_ranges.get(key, (0, 100))

        if max_val == min_val:
            return 0.5

        normalized = (value - min_val) / (max_val - min_val)
        return max(0, min(1, normalized))

    def get_color_from_gradient(self, normalized_value, start_color=None, end_color=None):
        """Get interpolated color from gradient based on normalized value.

        Args:
            normalized_value: Value between 0 and 1
            start_color: Start color (QColor), defaults to blue
            end_color: End color (QColor), defaults to orange

        Returns:
            QColor interpolated between start and end
        """
        if start_color is None:
            start_color = QColor(64, 128, 255)  # Blue
        if end_color is None:
            end_color = QColor(255, 128, 64)    # Orange

        r = int(start_color.red() + (end_color.red() - start_color.red()) * normalized_value)
        g = int(start_color.green() + (end_color.green() - start_color.green()) * normalized_value)
        b = int(start_color.blue() + (end_color.blue() - start_color.blue()) * normalized_value)

        return QColor(r, g, b)
