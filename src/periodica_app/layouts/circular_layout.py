#====== Playtow/PeriodicTable2/layouts/circular_layout.py ======#
#!copyright (c) 2025 Andrew Keith Watts. All rights reserved.
#!
#!This is the intellectual property of Andrew Keith Watts. Unauthorized
#!reproduction, distribution, or modification of this code, in whole or in part,
#!without the express written permission of Andrew Keith Watts is strictly prohibited.
#!
#!For inquiries, please contact AndrewKWatts@Gmail.com

"""
Circular Layout Renderer
Renders elements in circular wedge layout with dynamic period ring calculations.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainterPath, QRadialGradient
from PySide6.QtCore import Qt, QPointF, QRectF
from periodica_app.layouts.base_layout import BaseLayoutRenderer
from periodica.data.element_data import ISOTOPES
from periodica_app.utils.calculations import (get_ie_color, get_electroneg_color, get_melting_color,
                                 get_radius_color, get_density_color, get_electron_affinity_color,
                                 get_boiling_color, wavelength_to_rgb)


class CircularLayoutRenderer(BaseLayoutRenderer):
    """
    Circular layout renderer with dynamic period ring calculations.
    Elements are arranged in circular wedges with period-based rings.
    """

    def __init__(self, widget_width, widget_height):
        """
        Initialize circular layout renderer.

        Args:
            widget_width: Width of widget in pixels
            widget_height: Height of widget in pixels
        """
        super().__init__(widget_width, widget_height)

    def create_layout(self, base_elements, **kwargs):
        """
        Create circular wedge layout with dynamically calculated period radii.

        Args:
            base_elements: List of base element dictionaries
            **kwargs: Not used for circular layout

        Returns:
            List of element dictionaries with circular layout data
        """
        # Calculate dynamic radii based on widget size and number of periods
        periods_in_data = max(elem['period'] for elem in base_elements)
        available_radius = min(self.widget_width, self.widget_height) / 2 - 20  # 20px margin

        # Calculate base radius and ring spacing to fit available space
        base_radius = available_radius * 0.12  # Start at ~12% of available radius
        ring_spacing = (available_radius - base_radius) / periods_in_data

        # Generate period radii dynamically
        period_radii = []
        for period_idx in range(periods_in_data):
            r_inner = base_radius + period_idx * ring_spacing
            r_outer = r_inner + ring_spacing * 0.9  # 90% of spacing (10% gap)
            period_radii.append((r_inner, r_outer))

        start_angle = -math.pi / 2  # Start at top

        elements = []
        for elem in base_elements:
            period_idx = elem['period'] - 1
            r_inner, r_outer = period_radii[period_idx]

            # Count elements in this period
            period_elements = [e for e in base_elements if e['period'] == elem['period']]
            num_elements = len(period_elements)
            elem_idx_in_period = period_elements.index(elem)

            # Calculate angular position
            angle_per_elem = (2 * math.pi) / num_elements
            angle_start = start_angle + elem_idx_in_period * angle_per_elem
            angle_end = angle_start + angle_per_elem
            angle_mid = (angle_start + angle_end) / 2

            elements.append({
                **elem,
                'layout': 'circular',
                'r_inner': r_inner,
                'r_outer': r_outer,
                'angle_start': angle_start,
                'angle_end': angle_end,
                'angle_mid': angle_mid
            })

        return elements

    def paint(self, painter, elements, table_state, passes_filters_func):
        """
        Paint circular wedge layout.

        Args:
            painter: QPainter instance
            elements: List of element dictionaries with circular layout data
            table_state: Dictionary with visualization state
            passes_filters_func: Function to check if element passes filters
        """
        center_x = self.widget_width / 2
        center_y = self.widget_height / 2

        # Draw period guide rings
        self._draw_period_guide_rings(painter, center_x, center_y, elements)

        # Draw each element
        for elem in elements:
            passes_filter = passes_filters_func(elem)
            self._draw_circular_element(painter, elem, center_x, center_y, table_state, passes_filter)

        # Draw spectrum lines on outer arcs (if enabled)
        if table_state.get('show_spectrum_lines', False):
            for elem in elements:
                self._draw_spectrum_lines_for_element(painter, elem, center_x, center_y, table_state)

    def _draw_period_guide_rings(self, painter, center_x, center_y, elements):
        """
        Draw guide rings for each period.

        Args:
            painter: QPainter instance
            center_x: Center X coordinate
            center_y: Center Y coordinate
            elements: List of elements to extract period info
        """
        # Extract unique period radii from elements
        period_radii_set = set()
        for elem in elements:
            period_radii_set.add((elem['r_inner'] + elem['r_outer']) / 2)

        # Draw guide rings
        painter.setPen(QPen(QColor(60, 60, 100, 80), 1, Qt.PenStyle.DotLine))
        for radius in sorted(period_radii_set):
            painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

    def _draw_circular_element(self, painter, elem, center_x, center_y, table_state, passes_filter):
        """
        Draw a single element in circular wedge layout.

        Args:
            painter: QPainter instance
            elem: Element dictionary
            center_x: Center X coordinate
            center_y: Center Y coordinate
            table_state: Visualization state dictionary
            passes_filter: Boolean if element passes filters
        """
        # Apply filter alpha
        alpha = 255 if passes_filter else 80

        # Create wedge path
        path = QPainterPath()

        x1 = center_x + elem['r_inner'] * math.cos(elem['angle_start'])
        y1 = center_y + elem['r_inner'] * math.sin(elem['angle_start'])
        path.moveTo(x1, y1)

        rect_inner = QRectF(center_x - elem['r_inner'], center_y - elem['r_inner'],
                           elem['r_inner'] * 2, elem['r_inner'] * 2)
        span_angle = math.degrees(elem['angle_end'] - elem['angle_start'])
        path.arcTo(rect_inner, -math.degrees(elem['angle_start']), -span_angle)

        x2 = center_x + elem['r_outer'] * math.cos(elem['angle_end'])
        y2 = center_y + elem['r_outer'] * math.sin(elem['angle_end'])
        path.lineTo(x2, y2)

        rect_outer = QRectF(center_x - elem['r_outer'], center_y - elem['r_outer'],
                           elem['r_outer'] * 2, elem['r_outer'] * 2)
        path.arcTo(rect_outer, -math.degrees(elem['angle_end']), span_angle)
        path.closeSubpath()

        r_mid = (elem['r_inner'] + elem['r_outer']) / 2
        x_center = center_x + r_mid * math.cos(elem['angle_mid'])
        y_center = center_y + r_mid * math.sin(elem['angle_mid'])

        # Get fill color
        fill_color = self.get_property_color(
            elem, table_state['fill_property'],
            get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
            get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
        )
        fill_color.setAlpha(alpha)

        # Highlight hovered/selected elements
        hovered_element = table_state.get('hovered_element')
        selected_element = table_state.get('selected_element')

        if elem == hovered_element:
            fill_color = fill_color.lighter(130)
        if elem == selected_element:
            fill_color = fill_color.lighter(150)

        # Draw glow effect
        glow_size, glow_intensity = self.get_glow_params(elem, table_state['glow_property'])
        if glow_size > 0 and passes_filter:
            if elem == hovered_element or elem == selected_element:
                glow_size *= 1.5
            self.draw_glow_effect(painter, x_center, y_center, glow_size, glow_intensity,
                                fill_color, alpha / 255)

        # Main wedge fill - use spectrum gradient if spectrum property selected
        if self.should_draw_spectrum_gradient(table_state['fill_property']):
            # For circular wedges, create radial spectrum gradient from inner to outer
            x_inner = center_x + elem['r_inner'] * math.cos(elem['angle_mid'])
            y_inner = center_y + elem['r_inner'] * math.sin(elem['angle_mid'])
            x_outer = center_x + elem['r_outer'] * math.cos(elem['angle_mid'])
            y_outer = center_y + elem['r_outer'] * math.sin(elem['angle_mid'])

            spectrum_gradient = self.create_spectrum_gradient(
                elem, x_inner, y_inner, x_outer, y_outer, wavelength_to_rgb, alpha
            )
            if spectrum_gradient:
                painter.fillPath(path, QBrush(spectrum_gradient))
            else:
                # Fallback to radial gradient
                wedge_gradient = QRadialGradient(x_center, y_center, elem['r_outer'] - elem['r_inner'])
                bright_color = fill_color.lighter(115)
                wedge_gradient.setColorAt(0, bright_color)
                wedge_gradient.setColorAt(1, fill_color)
                painter.fillPath(path, QBrush(wedge_gradient))
        else:
            # Standard radial gradient
            wedge_gradient = QRadialGradient(x_center, y_center, elem['r_outer'] - elem['r_inner'])
            bright_color = fill_color.lighter(115)
            wedge_gradient.setColorAt(0, bright_color)
            wedge_gradient.setColorAt(1, fill_color)
            painter.fillPath(path, QBrush(wedge_gradient))

        # Inner ring (block color)
        self._draw_inner_ring(painter, elem, center_x, center_y, span_angle, table_state)

        # Isotope visualization
        if table_state.get('show_isotopes', False):
            self._draw_isotopes(painter, elem, center_x, center_y, alpha)

        # Border
        border_width = self.get_border_width(elem, table_state['border_property'])
        border_width = max(1, min(6, border_width))
        if elem == selected_element:
            border_width += 2

        # Get border color from property
        border_color = self.get_property_color(
            elem, table_state.get('border_color_property', 'electron_affinity'),
            get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
            get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
        )
        # Increase alpha for selected/hovered elements
        if elem == hovered_element or elem == selected_element:
            border_color.setAlpha(min(255, int(border_color.alpha() * 1.5)))
        else:
            border_color.setAlpha(int(alpha * 0.6))  # 60% of filter alpha

        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Text labels
        self._draw_element_text(painter, elem, x_center, y_center)

    def _draw_inner_ring(self, painter, elem, center_x, center_y, span_angle, table_state):
        """
        Draw inner ring showing block color.

        Args:
            painter: QPainter instance
            elem: Element dictionary
            center_x: Center X coordinate
            center_y: Center Y coordinate
            span_angle: Span angle in degrees
            table_state: Visualization state
        """
        ring_property = table_state.get('ring_property', 'block')
        fill_property = table_state['fill_property']

        if ring_property == "block" and fill_property != "block":
            ring_width = 8
            r_ring = elem['r_inner'] + ring_width / 2
            x_ring_start = center_x + r_ring * math.cos(elem['angle_start'])
            y_ring_start = center_y + r_ring * math.sin(elem['angle_start'])

            inner_ring_path = QPainterPath()
            inner_ring_path.moveTo(x_ring_start, y_ring_start)
            rect_ring = QRectF(center_x - r_ring, center_y - r_ring, r_ring * 2, r_ring * 2)
            inner_ring_path.arcTo(rect_ring, -math.degrees(elem['angle_start']), -span_angle)

            painter.setPen(QPen(elem['block_color'], ring_width, Qt.PenStyle.SolidLine,
                              Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(inner_ring_path)

    def _draw_isotopes(self, painter, elem, center_x, center_y, alpha):
        """
        Draw isotope markers within wedge.

        Args:
            painter: QPainter instance
            elem: Element dictionary
            center_x: Center X coordinate
            center_y: Center Y coordinate
            alpha: Base alpha for filtering
        """
        isotopes = ISOTOPES.get(elem['symbol'], [])
        if not isotopes:
            return

        num_isotopes = len(isotopes)
        for iso_idx, (mass, abundance) in enumerate(isotopes):
            # Position along the wedge radially
            iso_factor = (iso_idx + 1) / (num_isotopes + 1)
            r_iso = elem['r_inner'] + iso_factor * (elem['r_outer'] - elem['r_inner'])

            # Angle position (center of wedge)
            angle_iso = elem['angle_mid']

            x_iso = center_x + r_iso * math.cos(angle_iso)
            y_iso = center_y + r_iso * math.sin(angle_iso)

            # Size based on abundance
            iso_size = 2 + (abundance / 100) * 4

            # Color based on neutron count
            neutron_count = mass - elem['z']
            iso_color = QColor(150 + neutron_count * 5, 150 + neutron_count * 3, 255, 180)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(iso_color))
            painter.drawEllipse(QPointF(x_iso, y_iso), iso_size, iso_size)

            # Draw abundance bar for major isotopes
            if abundance > 20:
                bar_length = (abundance / 100) * 15
                angle_perp = angle_iso + math.pi / 2
                bar_x1 = x_iso - bar_length/2 * math.cos(angle_perp)
                bar_y1 = y_iso - bar_length/2 * math.sin(angle_perp)
                bar_x2 = x_iso + bar_length/2 * math.cos(angle_perp)
                bar_y2 = y_iso + bar_length/2 * math.sin(angle_perp)

                painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
                painter.drawLine(QPointF(bar_x1, bar_y1), QPointF(bar_x2, bar_y2))

    def _draw_element_text(self, painter, elem, x_center, y_center):
        """
        Draw element symbol and atomic number.

        Args:
            painter: QPainter instance
            elem: Element dictionary
            x_center: Center X coordinate of element
            y_center: Center Y coordinate of element
        """
        # Symbol
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        font = QFont('Arial', 9 if elem['period'] < 6 else 8, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = QRectF(x_center - 25, y_center - 15, 50, 18)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, elem['symbol'])

        # Atomic number
        font_tiny = QFont('Arial', 5)
        painter.setFont(font_tiny)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        num_rect = QRectF(x_center - 25, y_center + 5, 50, 12)
        painter.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, str(elem['z']))

    def _draw_spectrum_lines_for_element(self, painter, elem, center_x, center_y, table_state):
        """Draw spectrum emission lines as radial marks on the outer arc of the wedge."""
        if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
            return

        # Draw spectrum lines along the outer arc
        # Use the outer radius for the arc
        r_outer = elem['r_outer']
        angle_start = elem['angle_start']
        angle_end = elem['angle_end']

        # Calculate start and end points of the arc segment
        x_start = center_x + r_outer * math.cos(angle_start)
        y_start = center_y + r_outer * math.sin(angle_start)
        x_end = center_x + r_outer * math.cos(angle_end)
        y_end = center_y + r_outer * math.sin(angle_end)

        # Draw spectrum pixels as radial marks perpendicular to the arc
        self.draw_spectrum_pixels_on_line(painter, elem, x_start, y_start, x_end, y_end, wavelength_to_rgb)
