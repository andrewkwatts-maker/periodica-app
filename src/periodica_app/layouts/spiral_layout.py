#====== Playtow/PeriodicTable2/layouts/spiral_layout.py ======#
#!copyright (c) 2025 Andrew Keith Watts. All rights reserved.
#!
#!This is the intellectual property of Andrew Keith Watts. Unauthorized
#!reproduction, distribution, or modification of this code, in whole or in part,
#!without the express written permission of Andrew Keith Watts is strictly prohibited.
#!
#!For inquiries, please contact AndrewKWatts@Gmail.com

"""
Spiral Layout Renderer
Renders elements in spiral layout with isotope lines and period circles.
All positions and radii calculated dynamically from element data.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtCore import Qt, QPointF, QRectF
from periodica_app.layouts.base_layout import BaseLayoutRenderer
from periodica.data.element_data import ISOTOPES
from periodica_app.utils.calculations import (get_ie_color, get_electroneg_color, get_melting_color,
                                 get_radius_color, get_density_color, get_electron_affinity_color,
                                 get_boiling_color, wavelength_to_rgb)


class SpiralLayoutRenderer(BaseLayoutRenderer):
    """
    Spiral layout renderer with dynamic period circle calculations.
    Elements arranged in spiral pattern with isotope visualization.
    """

    def __init__(self, widget_width, widget_height):
        """
        Initialize spiral layout renderer.

        Args:
            widget_width: Width of widget in pixels
            widget_height: Height of widget in pixels
        """
        super().__init__(widget_width, widget_height)
        self.isotope_spiral_lines = []
        self.period_radii = {}
        self.spiral_center = (0, 0)

    def create_layout(self, base_elements, position_calculator=None):
        """
        Create spiral layout with main element positions and isotope data.
        Main spiral line goes through element positions (not isotopes).
        Isotopes are rendered as radial offsets from period circles.

        Args:
            base_elements: List of base element dictionaries
            position_calculator: Not used (for compatibility)

        Returns:
            List of element dictionaries with spiral layout data
        """
        margin = 50
        width = self.widget_width - 2 * margin
        height = self.widget_height - 2 * margin

        # Calculate dynamic period radii
        num_periods = max(elem['period'] for elem in base_elements)
        available_radius = min(width, height) / 2 - 50
        base_radius = available_radius * 0.18  # Start at ~18% of available radius
        ring_spacing = (available_radius - base_radius) / (num_periods - 1) if num_periods > 1 else 0

        period_radii = {}
        for period in range(1, num_periods + 1):
            period_radii[period] = base_radius + (period - 1) * ring_spacing

        # Spiral center
        spiral_center_x = width / 2 + margin
        spiral_center_y = height / 2 + margin

        # Find global min/max neutron offset for consistent isotope positioning
        global_min_offset = 0
        global_max_offset = 0
        for elem in base_elements:
            isotopes = ISOTOPES.get(elem['symbol'], [])
            if not isotopes:
                continue
            for mass, abundance in isotopes:
                neutron_count = mass - elem['z']
                neutron_delta = neutron_count - elem['z']
                global_min_offset = min(global_min_offset, neutron_delta)
                global_max_offset = max(global_max_offset, neutron_delta)

        # Calculate offset range for isotope radius mapping
        offset_range = max(abs(global_min_offset), abs(global_max_offset))
        if offset_range == 0:
            offset_range = 1  # Prevent division by zero

        # Angular spacing - 4 full rotations over all ELEMENTS (not isotopes)
        total_elements = len(base_elements)
        angular_spacing_per_element = (8 * math.pi) / max(total_elements, 1)

        element_positions = []
        current_angle = 0

        for elem_idx, elem in enumerate(base_elements):
            period = elem['period']
            base_radius_elem = period_radii[period]

            # Main element position is on the period circle
            spiral_angle = current_angle
            current_angle += angular_spacing_per_element

            # Get isotopes for this element
            isotopes = ISOTOPES.get(elem['symbol'], [])
            if not isotopes:
                # If no isotope data, create default based on mass number
                isotopes = [(elem['z'] * 2, 100)]

            # Calculate isotope positions with radial offsets using GLOBAL offset range
            elem_isotope_data = []
            for iso_idx, (mass, abundance) in enumerate(isotopes):
                neutron_count = mass - elem['z']
                neutron_delta = neutron_count - elem['z']  # Difference from equal protons/neutrons

                # Calculate radius offset based on GLOBAL neutron delta range
                # Positive delta (more neutrons) = outer, negative (fewer neutrons) = inner
                # Map to range [base_radius - ring_spacing/2, base_radius + ring_spacing/2]
                radius_offset = (neutron_delta / offset_range) * (ring_spacing / 2)

                isotope_radius = base_radius_elem + radius_offset

                elem_isotope_data.append({
                    'angle': spiral_angle,
                    'radius': isotope_radius,
                    'base_radius': base_radius_elem,
                    'mass': mass,
                    'abundance': abundance,
                    'neutron_count': neutron_count,
                    'neutron_delta': neutron_delta,
                    'isotope_index': iso_idx
                })

            element_positions.append({
                'angle': spiral_angle,
                'radius': base_radius_elem,
                'base_radius': base_radius_elem,
                'elem': elem,
                'isotopes': elem_isotope_data,
                'element_index': elem_idx,
                'period': period,
                'ring_spacing': ring_spacing
            })

        # Store for rendering
        self.element_spiral_positions = element_positions
        self.period_radii = period_radii
        self.spiral_center = (spiral_center_x, spiral_center_y)
        self.ring_spacing = ring_spacing

        # Create element entries - calculate x,y from angle/radius
        elements = []
        for pos_data in element_positions:
            elem = pos_data['elem']
            angle = pos_data['angle']
            radius = pos_data['radius']
            x = spiral_center_x + radius * math.cos(angle)
            y = spiral_center_y + radius * math.sin(angle)

            elements.append({
                **elem,
                'layout': 'spiral',
                'x': x,
                'y': y,
                'angle': angle,
                'radius': radius,
                'base_radius': pos_data['base_radius'],
                'isotopes': pos_data['isotopes'],
                'has_element': True,
                'element_index': pos_data['element_index'],
                'period': pos_data['period'],
                'ring_spacing': pos_data['ring_spacing']
            })

        return elements

    def paint(self, painter, elements, table_state, **kwargs):
        """
        Paint spiral layout with:
        - Period circles
        - Main spiral line with rainbow gradient (fill property)
        - Isotope lines at radial offsets (if show_isotopes enabled)
        - Element dots with glow (ring property and glow property)
        - Element labels

        Args:
            painter: QPainter instance
            elements: List of element dictionaries with spiral layout data
            table_state: Dictionary with visualization state
            **kwargs: Additional parameters (zoom_level, pan_x, pan_y)
        """
        # Apply zoom and pan transformations
        zoom_level = kwargs.get('zoom_level', 1.0)
        pan_x = kwargs.get('pan_x', 0)
        pan_y = kwargs.get('pan_y', 0)

        painter.save()
        painter.translate(pan_x, pan_y)
        painter.scale(zoom_level, zoom_level)

        # Draw period circles
        self._draw_period_circles(painter)

        # Draw isotope lines (if enabled) - must be drawn before main line
        if table_state.get('show_isotopes', False):
            self._draw_isotope_lines(painter, elements, table_state)

        # Draw main spiral line with gradient
        self._draw_main_spiral(painter, elements, table_state)

        # Draw spectrum lines (if enabled)
        if table_state.get('show_spectrum_lines', False):
            self._draw_spectrum_lines_on_spiral(painter, elements, table_state)

        # Draw element dots with glow
        self._draw_element_dots(painter, elements, table_state)

        # Draw element labels
        self._draw_element_labels(painter, elements, table_state)

        # Draw legend
        self._draw_spiral_legend(painter, table_state)

        painter.restore()

    def _draw_period_circles(self, painter):
        """Draw concentric circles representing periods with dynamic radii."""
        if not self.period_radii or not self.spiral_center:
            return

        center_x, center_y = self.spiral_center

        # Period colors based on block
        period_colors = {
            1: QColor(255, 100, 120, 120),  # s-block (red)
            2: QColor(255, 100, 120, 120),
            3: QColor(100, 160, 255, 120),  # p-block (blue)
            4: QColor(255, 210, 100, 120),  # d-block (gold)
            5: QColor(255, 210, 100, 120),
            6: QColor(140, 255, 170, 120),  # f-block (green)
            7: QColor(140, 255, 170, 120)
        }

        for period, radius in self.period_radii.items():
            color = period_colors.get(period, QColor(150, 150, 150, 120))

            painter.setPen(QPen(color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

            # Draw period label
            label_angle = math.pi / 4  # 45 degrees
            label_x = center_x + radius * math.cos(label_angle)
            label_y = center_y + radius * math.sin(label_angle)

            painter.setPen(QPen(QColor(200, 200, 220, 200), 1))
            font = QFont('Arial', 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QPointF(label_x + 5, label_y - 5), f"P{period}")

    def _draw_main_spiral(self, painter, elements, table_state):
        """Draw the main spiral line connecting all elements with rainbow gradient."""
        if not hasattr(self, 'element_spiral_positions') or not self.element_spiral_positions:
            return

        center_x, center_y = self.spiral_center

        # Draw line segments between consecutive elements
        for i in range(len(self.element_spiral_positions) - 1):
            pos1 = self.element_spiral_positions[i]
            pos2 = self.element_spiral_positions[i + 1]

            elem1 = pos1['elem']
            elem2 = pos2['elem']

            # Calculate positions from angle and radius
            x1 = center_x + pos1['radius'] * math.cos(pos1['angle'])
            y1 = center_y + pos1['radius'] * math.sin(pos1['angle'])
            x2 = center_x + pos2['radius'] * math.cos(pos2['angle'])
            y2 = center_y + pos2['radius'] * math.sin(pos2['angle'])

            # Get fill color for this segment (use midpoint element)
            fill_color = self.get_property_color(
                elem1, table_state['fill_property'],
                get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
                get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
            )

            # Get border properties
            border_color = self.get_property_color(
                elem1, table_state.get('border_color_property', 'electron_affinity'),
                get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
                get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
            )
            border_width = self.get_border_width(elem1, table_state['border_property'])

            # Draw border (outer line)
            if border_width > 1:
                painter.setPen(QPen(border_color, border_width + 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Draw main line
            painter.setPen(QPen(fill_color, max(border_width, 3), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_isotope_lines(self, painter, elements, table_state):
        """Draw isotope lines by connecting matching isotopes between consecutive elements."""
        if not hasattr(self, 'element_spiral_positions') or not self.element_spiral_positions:
            return

        center_x, center_y = self.spiral_center

        # Draw isotope lines for each element segment
        for i in range(len(self.element_spiral_positions) - 1):
            pos_data = self.element_spiral_positions[i]
            next_pos = self.element_spiral_positions[i + 1]

            elem = pos_data['elem']
            isotopes_curr = pos_data['isotopes']
            isotopes_next = next_pos['isotopes']

            # Draw lines for each isotope in current element
            for isotope in isotopes_curr:
                # Skip if this is the base isotope (no offset)
                radial_offset = isotope['radius'] - pos_data['radius']
                if abs(radial_offset) < 0.1:
                    continue

                # Calculate Cartesian coordinates for this isotope at current element position
                angle1 = pos_data['angle']
                radius1 = isotope['radius']
                x1 = center_x + radius1 * math.cos(angle1)
                y1 = center_y + radius1 * math.sin(angle1)

                # Find matching isotope in next element (by neutron_delta)
                neutron_delta = isotope['neutron_delta']
                matching_isotope = None
                for next_iso in isotopes_next:
                    if next_iso['neutron_delta'] == neutron_delta:
                        matching_isotope = next_iso
                        break

                # If no matching isotope found, skip this line
                if matching_isotope is None:
                    continue

                # Calculate Cartesian coordinates for matching isotope at next element position
                angle2 = next_pos['angle']
                radius2 = matching_isotope['radius']
                x2 = center_x + radius2 * math.cos(angle2)
                y2 = center_y + radius2 * math.sin(angle2)

                # Get fill color for this isotope segment
                fill_color = self.get_property_color(
                    elem, table_state['fill_property'],
                    get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
                    get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
                )

                # Get border properties
                border_color = self.get_property_color(
                    elem, table_state.get('border_color_property', 'electron_affinity'),
                    get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
                    get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
                )
                border_width = self.get_border_width(elem, table_state['border_property'])

                # Scale line thickness by abundance
                abundance_scale = isotope['abundance'] / 100.0
                scaled_border = max(1, border_width * abundance_scale)

                # Draw border (outer line) - only if border width > 1
                if border_width > 1:
                    painter.setPen(QPen(border_color, scaled_border + 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

                # Draw main isotope line
                painter.setPen(QPen(fill_color, max(scaled_border, 2), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_element_dots(self, painter, elements, table_state):
        """Draw dots at element positions with ring color and glow."""
        if not hasattr(self, 'element_spiral_positions'):
            return

        center_x, center_y = self.spiral_center

        for pos_data in self.element_spiral_positions:
            elem = pos_data['elem']

            # Calculate position from angle and radius
            angle = pos_data['angle']
            radius = pos_data['radius']
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)

            # Get ring color (ring property)
            ring_color = self.get_property_color(
                elem, table_state.get('ring_property', 'block'),
                get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
                get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
            )

            # Get ring size
            # Using get_inner_ring_size pattern - map to dot size (2-8 pixels)
            ring_size_val = self.get_inner_ring_size(elem, table_state.get('ring_size_property', 'none'))
            dot_size = 3 + ring_size_val * 5

            # Draw glow
            glow_size, glow_intensity = self.get_glow_params(elem, table_state['glow_property'])
            if glow_size > 0:
                glow_color = self.get_property_color(
                    elem, table_state['glow_property'],
                    get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
                    get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
                )
                self.draw_glow_effect(painter, x, y, glow_size, glow_intensity, glow_color, 1.0)

            # Draw dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(ring_color))
            painter.drawEllipse(QPointF(x, y), dot_size, dot_size)

    def get_inner_ring_size(self, elem, ring_size_property):
        """Calculate inner ring size based on property (0.0-1.0)."""
        if ring_size_property == "none":
            return 0.3  # Default size
        elif ring_size_property == "radius":
            return (elem['atomic_radius'] - 30) / 320
        elif ring_size_property == "ionization":
            return (elem['ie'] - 3.5) / (25.0 - 3.5)
        elif ring_size_property == "electronegativity":
            if elem['electronegativity'] == 0:
                return 0.1
            return elem['electronegativity'] / 4.0
        return 0.3

    def _draw_element_labels(self, painter, elements, table_state):
        """Draw element symbols and atomic numbers at their positions."""
        center_x, center_y = self.spiral_center
        hovered_element = table_state.get('hovered_element')
        selected_element = table_state.get('selected_element')

        for elem in elements:
            if not elem.get('has_element'):
                continue

            symbol = elem.get('symbol', '')
            if not symbol:
                continue

            angle = elem['angle']
            radius = elem['base_radius']

            # Place label outside the circle
            label_radius = radius + 25
            text_x = center_x + label_radius * math.cos(angle)
            text_y = center_y + label_radius * math.sin(angle)

            # Draw symbol
            painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
            font = QFont('Arial', 10, QFont.Weight.Bold)
            painter.setFont(font)

            # Highlight if selected/hovered
            if elem == hovered_element or elem == selected_element:
                painter.setPen(QPen(QColor(255, 255, 100, 255), 2))
                font.setPointSize(12)
                painter.setFont(font)

            text_rect = QRectF(text_x - 20, text_y - 10, 40, 20)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, symbol)

            # Draw atomic number (smaller, below symbol)
            if elem != hovered_element and elem != selected_element:
                painter.setPen(QPen(QColor(200, 200, 200, 180), 1))
                font.setPointSize(7)
                painter.setFont(font)
                num_rect = QRectF(text_x - 20, text_y + 5, 40, 15)
                painter.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, str(elem['z']))

    def _draw_spiral_legend(self, painter, table_state):
        """Draw legend showing property encodings (dynamically positioned)."""
        if not self.spiral_center:
            return

        # Position legend in bottom left corner
        legend_width = 250
        legend_height = 130
        legend_x = 20
        legend_y = self.widget_height - legend_height - 20

        # Background box
        painter.setPen(QPen(QColor(100, 100, 120, 200), 2))
        painter.setBrush(QBrush(QColor(20, 20, 40, 200)))
        painter.drawRect(legend_x, legend_y, legend_width, legend_height)

        # Title
        painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(legend_x + 10, legend_y + 20, "Property Encoding")

        # Property mappings
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)

        y_offset = legend_y + 40
        line_height = 22

        painter.drawText(legend_x + 10, y_offset, "Line Color:")
        painter.drawText(legend_x + 110, y_offset, table_state['fill_property'].title())
        y_offset += line_height

        painter.drawText(legend_x + 10, y_offset, "Line Thickness:")
        painter.drawText(legend_x + 110, y_offset, "Isotope Abundance")
        y_offset += line_height

        if table_state.get('show_isotopes', False):
            painter.drawText(legend_x + 10, y_offset, "Wedge Fill:")
            painter.drawText(legend_x + 110, y_offset, table_state['border_property'].title())
            y_offset += line_height

            painter.drawText(legend_x + 10, y_offset, "Wedge Border:")
            painter.drawText(legend_x + 110, y_offset, table_state['glow_property'].title())
            y_offset += line_height

        painter.drawText(legend_x + 10, y_offset, "Period Circles:")
        painter.drawText(legend_x + 110, y_offset, "Orbital Blocks")

    def _draw_spectrum_lines_on_spiral(self, painter, elements, table_state):
        """Draw spectrum lines perpendicular to the spiral/isotope lines."""
        if not hasattr(self, 'element_spiral_positions') or not self.element_spiral_positions:
            return

        # Determine which lines to draw on based on show_isotopes
        if table_state.get('show_isotopes', False):
            # Draw on all isotope lines
            center_x, center_y = self.spiral_center
            for i, pos_data in enumerate(self.element_spiral_positions):
                elem = pos_data['elem']
                isotopes = pos_data['isotopes']

                if i >= len(self.element_spiral_positions) - 1:
                    continue

                next_pos = self.element_spiral_positions[i + 1]

                # Draw spectrum pixels for each isotope line
                for iso_idx, isotope in enumerate(isotopes):
                    # Calculate angle and radius span for this isotope
                    start_angle = pos_data['angle']
                    end_angle = next_pos['angle']
                    start_radius = pos_data['radius']
                    end_radius = next_pos['radius']
                    radial_offset = isotope['radius'] - start_radius

                    # Calculate start and end points
                    x1 = center_x + (start_radius + radial_offset) * math.cos(start_angle)
                    y1 = center_y + (start_radius + radial_offset) * math.sin(start_angle)
                    x2 = center_x + (end_radius + radial_offset) * math.cos(end_angle)
                    y2 = center_y + (end_radius + radial_offset) * math.sin(end_angle)

                    # Draw spectrum pixels on this line segment
                    self.draw_spectrum_pixels_on_line(painter, elem, x1, y1, x2, y2, wavelength_to_rgb)
        else:
            # Draw only on main spiral line
            center_x, center_y = self.spiral_center
            for i in range(len(self.element_spiral_positions) - 1):
                pos1 = self.element_spiral_positions[i]
                pos2 = self.element_spiral_positions[i + 1]
                elem = pos1['elem']

                # Calculate positions from angle and radius
                x1 = center_x + pos1['radius'] * math.cos(pos1['angle'])
                y1 = center_y + pos1['radius'] * math.sin(pos1['angle'])
                x2 = center_x + pos2['radius'] * math.cos(pos2['angle'])
                y2 = center_y + pos2['radius'] * math.sin(pos2['angle'])

                # Draw spectrum pixels on main spiral line
                self.draw_spectrum_pixels_on_line(painter, elem, x1, y1, x2, y2, wavelength_to_rgb)
