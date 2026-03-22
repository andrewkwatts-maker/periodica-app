#====== Playtow/PeriodicTable2/layouts/table_layout.py ======#
#!copyright (c) 2025 Andrew Keith Watts. All rights reserved.
#!
#!This is the intellectual property of Andrew Keith Watts. Unauthorized
#!reproduction, distribution, or modification of this code, in whole or in part,
#!without the express written permission of Andrew Keith Watts is strictly prohibited.
#!
#!For inquiries, please contact AndrewKWatts@Gmail.com

"""
Table Layout Renderer
Renders elements in traditional periodic table grid layout.
All cell sizes and positions calculated dynamically from widget dimensions.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QRadialGradient
from PySide6.QtCore import Qt, QPointF, QRectF
from periodica_app.layouts.base_layout import BaseLayoutRenderer
from periodica_app.utils.calculations import (get_ie_color, get_electroneg_color, get_melting_color,
                                 get_radius_color, get_density_color, get_electron_affinity_color,
                                 get_boiling_color, wavelength_to_rgb)


class TableLayoutRenderer(BaseLayoutRenderer):
    """
    Table layout renderer with dynamic cell sizing.
    Elements arranged in traditional periodic table grid (18 columns × 9 rows).
    """

    def __init__(self, widget_width, widget_height):
        """
        Initialize table layout renderer.

        Args:
            widget_width: Width of widget in pixels
            widget_height: Height of widget in pixels
        """
        super().__init__(widget_width, widget_height)

    def create_layout(self, base_elements, position_calculator):
        """
        Create table layout with dynamically calculated cell sizes.

        Args:
            base_elements: List of base element dictionaries
            position_calculator: PositionCalculator instance for grid positions

        Returns:
            List of element dictionaries with table layout data
        """
        # Calculate dynamic cell size based on widget dimensions
        # Standard periodic table: 18 columns, 9 rows (including lanthanides/actinides separated)
        num_cols = 18
        num_rows = 9

        # Dynamic margins (5-10% of dimensions)
        margin_left = max(30, self.widget_width * 0.05)
        margin_top = max(30, self.widget_height * 0.05)
        margin_right = max(30, self.widget_width * 0.05)
        margin_bottom = max(30, self.widget_height * 0.05)

        available_width = self.widget_width - margin_left - margin_right
        available_height = self.widget_height - margin_top - margin_bottom

        # Calculate cell size to fit grid
        cell_size_by_width = available_width / num_cols
        cell_size_by_height = available_height / num_rows
        cell_size = min(cell_size_by_width, cell_size_by_height)

        # Ensure minimum cell size
        cell_size = max(35, min(cell_size, 80))  # Between 35 and 80 pixels

        elements = []
        for elem in base_elements:
            symbol = elem['symbol']
            z = elem['z']

            # Calculate grid position dynamically from atomic properties
            row, col = position_calculator.get_table_position(z, symbol)

            # Calculate pixel coordinates from grid position
            x = margin_left + (col - 1) * cell_size
            y = margin_top + (row - 1) * cell_size

            elements.append({
                **elem,
                'layout': 'table',
                'x': x,
                'y': y,
                'cell_size': cell_size,
                'grid_row': row,
                'grid_col': col
            })

        return elements

    def paint(self, painter, elements, table_state, passes_filters_func):
        """
        Paint traditional periodic table layout.

        Args:
            painter: QPainter instance
            elements: List of element dictionaries with table layout data
            table_state: Dictionary with visualization state
            passes_filters_func: Function to check if element passes filters
        """
        for elem in elements:
            passes_filter = passes_filters_func(elem)
            self._draw_table_element(painter, elem, table_state, passes_filter)

            # Draw spectrum lines if enabled
            if table_state.get('show_spectrum_lines', False):
                self._draw_spectrum_lines_for_element(painter, elem)

    def _draw_table_element(self, painter, elem, table_state, passes_filter):
        """Draw a single element cell in table layout."""
        x = elem['x']
        y = elem['y']
        cell_size = elem['cell_size']

        alpha = 255 if passes_filter else 80

        # Get fill color
        fill_color = self.get_property_color(
            elem, table_state['fill_property'],
            get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
            get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
        )
        fill_color.setAlpha(alpha)

        hovered_element = table_state.get('hovered_element')
        selected_element = table_state.get('selected_element')

        if elem == hovered_element:
            fill_color = fill_color.lighter(130)
        if elem == selected_element:
            fill_color = fill_color.lighter(150)

        # Glow effect
        glow_size, glow_intensity = self.get_glow_params(elem, table_state['glow_property'])
        if glow_size > 0 and passes_filter:
            if elem == hovered_element or elem == selected_element:
                glow_size *= 1.5
            self.draw_glow_effect(painter, x + cell_size/2, y + cell_size/2,
                                glow_size, glow_intensity, fill_color, alpha / 255)

        # Main cell fill - use spectrum gradient if spectrum property selected
        if self.should_draw_spectrum_gradient(table_state['fill_property']):
            spectrum_gradient = self.create_spectrum_gradient(
                elem, x, y, x + cell_size, y, wavelength_to_rgb, alpha
            )
            if spectrum_gradient:
                painter.setBrush(QBrush(spectrum_gradient))
            else:
                painter.setBrush(QBrush(fill_color))
        else:
            painter.setBrush(QBrush(fill_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(x, y, cell_size, cell_size), 5, 5)

        # Border
        border_width = self.get_border_width(elem, table_state['border_property'])
        border_color = self.get_property_color(
            elem, table_state['border_property'],
            get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
            get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
        )
        border_color.setAlpha(alpha)
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(x, y, cell_size, cell_size), 5, 5)

        # Draw element info
        if passes_filter or elem == hovered_element or elem == selected_element:
            self._draw_element_text(painter, elem, x, y, cell_size, alpha,
                                  hovered_element, selected_element, table_state)

    def _draw_element_text(self, painter, elem, x, y, cell_size, alpha,
                          hovered_element, selected_element, table_state):
        """Draw element text (atomic number, symbol, property value)."""
        text_alpha = alpha
        painter.setPen(QPen(QColor(255, 255, 255, text_alpha), 1))

        # Atomic number (top left)
        font = QFont('Arial', max(7, int(cell_size * 0.13)))
        painter.setFont(font)
        painter.drawText(QRectF(x + 3, y + 2, cell_size - 6, cell_size * 0.2),
                        Qt.AlignmentFlag.AlignLeft, str(elem['z']))

        # Symbol (center, large)
        font_size = max(12, int(cell_size * 0.3)) if alpha > 200 else max(10, int(cell_size * 0.23))
        font = QFont('Arial', font_size, QFont.Weight.Bold)
        painter.setFont(font)

        if elem == hovered_element or elem == selected_element:
            painter.setPen(QPen(QColor(255, 255, 100, 255), 2))

        painter.drawText(QRectF(x, y + cell_size/2 - cell_size * 0.2,
                               cell_size, cell_size * 0.4),
                        Qt.AlignmentFlag.AlignCenter, elem.get('symbol', ''))

        # Property value (bottom, small)
        painter.setPen(QPen(QColor(200, 200, 200, text_alpha), 1))
        font = QFont('Arial', max(6, int(cell_size * 0.12)))
        painter.setFont(font)

        value_text = self._get_property_value_text(elem, table_state['fill_property'])
        painter.drawText(QRectF(x + 2, y + cell_size - cell_size * 0.2,
                               cell_size - 4, cell_size * 0.15),
                        Qt.AlignmentFlag.AlignCenter, value_text)

    def _get_property_value_text(self, elem, fill_property):
        """Get formatted property value text for display."""
        if fill_property == "ionization":
            return f"{elem['ie']:.1f}eV"
        elif fill_property == "electronegativity":
            return f"{elem['electronegativity']:.2f}"
        elif fill_property == "melting":
            return f"{elem['melting_point']:.0f}K"
        elif fill_property == "boiling":
            return f"{elem.get('boiling_point', 0):.0f}K"
        elif fill_property == "radius":
            return f"{elem['atomic_radius']:.0f}pm"
        elif fill_property == "density":
            return f"{elem.get('density', 0):.2f}"
        elif fill_property == "electron_affinity":
            return f"{elem.get('electron_affinity', 0):.0f}"
        elif fill_property == "valence":
            return f"v={elem.get('valence_electrons', 0)}"
        return ""

    def _draw_spectrum_lines_for_element(self, painter, elem):
        """Draw vertical spectrum lines within the table cell for this element."""
        if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
            return

        x = elem['x']
        y = elem['y']
        cell_size = elem['cell_size']

        # Draw spectrum lines as vertical lines within the cell
        # Use the bottom portion of the cell for spectrum display
        spectrum_height = cell_size * 0.2  # Bottom 20% of cell
        y_start = y + cell_size - spectrum_height
        y_end = y + cell_size

        # Draw vertical line for each spectral line
        self.draw_spectrum_pixels_on_line(painter, elem, x, y_start, x + cell_size, y_start, wavelength_to_rgb)
