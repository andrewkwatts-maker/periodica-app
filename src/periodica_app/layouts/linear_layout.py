#====== Playtow/PeriodicTable2/layouts/linear_layout.py ======#
#!copyright (c) 2025 Andrew Keith Watts. All rights reserved.
#!
#!This is the intellectual property of Andrew Keith Watts. Unauthorized
#!reproduction, distribution, or modification of this code, in whole or in part,
#!without the express written permission of Andrew Keith Watts is strictly prohibited.
#!
#!For inquiries, please contact AndrewKWatts@Gmail.com

"""
Linear Layout Renderer
Renders elements in linear graph layout with property trend lines.
All positions and margins calculated dynamically.
"""

import math
from enum import Enum
from dataclasses import dataclass
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainterPath, QRadialGradient
from PySide6.QtCore import Qt, QPointF, QRectF
from periodica_app.layouts.base_layout import BaseLayoutRenderer
from periodica.data.element_data import ISOTOPES
from periodica_app.utils.calculations import (get_ie_color, get_electroneg_color, get_melting_color,
                                 get_radius_color, get_density_color, get_electron_affinity_color,
                                 get_boiling_color, wavelength_to_rgb)
from periodica_app.constants import UIConstants


class PTTPropertyKey(Enum):
    """Property keys for linear graph visualization"""
    IONIZATION = "ionization"
    ELECTRONEGATIVITY = "electronegativity"
    RADIUS = "radius"
    MELTING = "melting"
    BOILING = "boiling"
    DENSITY = "density"
    ELECTRON_AFFINITY = "electron_affinity"
    VALENCE = "valence"


@dataclass
class PTTPropertyConfig:
    """Configuration for a property visualization line"""
    key: PTTPropertyKey
    label: str
    color: QColor
    element_key: str  # Key used to access element data
    display_name: str  # Full display name with units


# Property configurations - single source of truth
PTT_PROPERTY_CONFIGS = {
    PTTPropertyKey.IONIZATION: PTTPropertyConfig(
        key=PTTPropertyKey.IONIZATION,
        label='Ionization Energy',
        color=QColor(255, 100, 100, 200),
        element_key='ie',
        display_name='Ionization Energy (eV)'
    ),
    PTTPropertyKey.ELECTRONEGATIVITY: PTTPropertyConfig(
        key=PTTPropertyKey.ELECTRONEGATIVITY,
        label='Electronegativity',
        color=QColor(100, 180, 255, 200),
        element_key='electronegativity',
        display_name='Electronegativity'
    ),
    PTTPropertyKey.RADIUS: PTTPropertyConfig(
        key=PTTPropertyKey.RADIUS,
        label='Atomic Radius',
        color=QColor(100, 255, 180, 200),
        element_key='atomic_radius',
        display_name='Atomic Radius (pm)'
    ),
    PTTPropertyKey.MELTING: PTTPropertyConfig(
        key=PTTPropertyKey.MELTING,
        label='Melting Point',
        color=QColor(255, 180, 100, 200),
        element_key='melting_point',
        display_name='Melting Point (K)'
    ),
    PTTPropertyKey.BOILING: PTTPropertyConfig(
        key=PTTPropertyKey.BOILING,
        label='Boiling Point',
        color=QColor(255, 100, 255, 200),
        element_key='boiling_point',
        display_name='Boiling Point (K)'
    ),
    PTTPropertyKey.DENSITY: PTTPropertyConfig(
        key=PTTPropertyKey.DENSITY,
        label='Density',
        color=QColor(180, 100, 255, 200),
        element_key='density',
        display_name='Density (g/cm³)'
    ),
    PTTPropertyKey.ELECTRON_AFFINITY: PTTPropertyConfig(
        key=PTTPropertyKey.ELECTRON_AFFINITY,
        label='Electron Affinity',
        color=QColor(255, 255, 100, 200),
        element_key='electron_affinity',
        display_name='Electron Affinity (kJ/mol)'
    ),
    PTTPropertyKey.VALENCE: PTTPropertyConfig(
        key=PTTPropertyKey.VALENCE,
        label='Valence Electrons',
        color=QColor(100, 255, 255, 200),
        element_key='valence_electrons',
        display_name='Valence Electrons'
    ),
}


class LinearLayoutRenderer(BaseLayoutRenderer):
    """
    Linear layout renderer with dynamic spacing and property trend lines.
    Elements arranged horizontally with configurable ordering.
    """

    def __init__(self, widget_width, widget_height):
        """
        Initialize linear layout renderer.

        Args:
            widget_width: Width of widget in pixels
            widget_height: Height of widget in pixels
        """
        super().__init__(widget_width, widget_height)
        self.period_boundaries = []

    def create_layout(self, base_elements, position_calculator=None, order_property="atomic_number"):
        """
        Create linear layout with non-overlapping boxes arranged horizontally.

        Args:
            base_elements: List of base element dictionaries
            position_calculator: Not used (for compatibility)
            order_property: Property to order elements by

        Returns:
            List of element dictionaries with linear layout data
        """
        # Sort elements by ordering property
        sorted_elements = sorted(base_elements, key=lambda e: self._get_order_value(e, order_property))

        # Calculate dynamic margins based on widget size
        margin_left = max(150, self.widget_width * 0.12)  # Increased for label visibility and title text
        margin_right = max(20, self.widget_width * 0.02)
        margin_top = max(40, self.widget_height * 0.05)  # 5% of height or 40px minimum
        margin_bottom = max(40, self.widget_height * 0.05)

        total_width = self.widget_width - margin_left - margin_right
        total_height = self.widget_height - margin_top - margin_bottom

        # Calculate box dimensions - SQUARES like traditional table
        num_elements = len(sorted_elements)

        # Fixed box size like traditional table (readable and consistent)
        # Use 60-80px boxes similar to table layout
        desired_box_size = 70  # Target size for readability
        max_box_height = total_height * 0.6  # Use 60% of height for the row

        # Use fixed size (boxes will extend beyond view, use scrolling via zoom/pan)
        box_size = min(desired_box_size, max_box_height)

        box_width = box_size
        box_height = box_size

        # Center line y position
        center_y = margin_top + total_height / 2

        # Calculate total layout width (may exceed widget width - that's OK, we have pan)
        total_layout_width = num_elements * box_size

        # Track period boundaries
        period_boundaries = []
        last_period = None

        elements = []
        for elem_idx, elem in enumerate(sorted_elements):
            # Box center position
            box_x = margin_left + elem_idx * box_width + box_width / 2

            # Detect period changes
            if last_period is not None and elem['period'] != last_period:
                period_boundaries.append(box_x - box_width / 2)
            last_period = elem['period']

            elements.append({
                **elem,
                'layout': 'linear',
                'x': box_x,
                'y': center_y,
                'box_width': box_width,
                'box_height': box_height,
                'element_index': elem_idx,
                'has_element': True
            })

        self.period_boundaries = period_boundaries
        return elements

    def _get_order_value(self, elem, order_property):
        """Get value to order elements by."""
        property_map = {
            'atomic_number': 'z',
            'ionization': 'ie',
            'electronegativity': 'electronegativity',
            'melting': 'melting_point',
            'boiling': 'boiling_point',
            'radius': 'atomic_radius',
            'density': 'density',
            'electron_affinity': 'electron_affinity',
            'valence': 'valence_electrons'
        }
        key = property_map.get(order_property, 'z')
        return elem.get(key, 0)

    def paint(self, painter, elements, table_state, passes_filters_func, **kwargs):
        """
        Paint linear graph layout with property trend lines.

        Args:
            painter: QPainter instance
            elements: List of element dictionaries with linear layout data
            table_state: Dictionary with visualization state
            passes_filters_func: Function to check if element passes filters
            **kwargs: Additional parameters (zoom_level, pan_x, pan_y)
        """
        # Apply zoom and pan
        zoom_level = kwargs.get('zoom_level', 1.0)
        pan_x = kwargs.get('pan_x', 0)
        pan_y = kwargs.get('pan_y', 0)

        painter.save()
        painter.translate(pan_x, pan_y)
        painter.scale(zoom_level, zoom_level)

        # Calculate margins dynamically
        margin_top = max(80, self.widget_height * 0.1)
        margin_bottom = max(80, self.widget_height * 0.1)
        height = self.widget_height - margin_top - margin_bottom
        center_y = margin_top + height / 2

        # Draw period dividers
        self._draw_period_dividers(painter)

        # Draw center line
        painter.setPen(QPen(QColor(100, 100, 150, 80), 1, Qt.PenStyle.DotLine))
        painter.drawLine(QPointF(50, center_y), QPointF(self.widget_width - 50, center_y))

        # Draw property trend lines (unless in subatomic mode)
        if not table_state.get('show_subatomic_particles', False):
            self._draw_property_lines(painter, elements, table_state, center_y, height)

        # Draw elements - if showing subatomic particles, only draw selected element
        show_subatomic = table_state.get('show_subatomic_particles', False)
        selected_elem = table_state.get('selected_element')

        if show_subatomic and selected_elem:
            # Only draw selected element
            passes_filter = passes_filters_func(selected_elem)
            self._draw_linear_element(painter, selected_elem, table_state, passes_filter)
        else:
            # Draw all elements
            for elem in elements:
                passes_filter = passes_filters_func(elem)
                self._draw_linear_element(painter, elem, table_state, passes_filter)

        # Draw spectrum lines perpendicular to horizontal axis (if enabled)
        if table_state.get('show_spectrum_lines', False):
            self._draw_spectrum_lines(painter, elements, table_state)

        painter.restore()

    def _draw_period_dividers(self, painter):
        """Draw vertical lines at period boundaries."""
        if not self.period_boundaries:
            return

        painter.setPen(QPen(QColor(150, 150, 200, 150), 3, Qt.PenStyle.DashLine))
        for x in self.period_boundaries:
            painter.drawLine(QPointF(x, 50), QPointF(x, self.widget_height - 50))

    def _draw_property_lines(self, painter, elements, table_state, center_y, height):
        """Draw N property trend lines - N/2 above center, N/2 below center."""
        if not elements:
            return

        # Get box size to calculate element boundaries
        box_height = elements[0]['box_height'] if elements else 70

        # All available properties for visualization - use enum-based configs
        all_property_keys = [
            PTTPropertyKey.IONIZATION,
            PTTPropertyKey.ELECTRONEGATIVITY,
            PTTPropertyKey.RADIUS,
            PTTPropertyKey.MELTING,
            PTTPropertyKey.BOILING,
            PTTPropertyKey.DENSITY,
            PTTPropertyKey.ELECTRON_AFFINITY,
            PTTPropertyKey.VALENCE,
        ]

        N = len(all_property_keys)
        N_above = N // 2
        N_below = N - N_above

        # Available space above and below elements
        space_above = center_y - box_height/2 - max(80, self.widget_height * 0.1)
        space_below = (self.widget_height - max(80, self.widget_height * 0.1)) - (center_y + box_height/2)

        # Height for each property line
        line_height_above = space_above / N_above if N_above > 0 else 0
        line_height_below = space_below / N_below if N_below > 0 else 0

        margin_left = max(150, self.widget_width * 0.12)  # Increased for label visibility and title text

        # Draw properties above center (min of one = max of previous)
        for i in range(N_above):
            prop_key = all_property_keys[i]
            prop_config = PTT_PROPERTY_CONFIGS[prop_key]

            # Calculate y range for this property line (from bottom to top)
            # Line i=0 is closest to elements, i=N_above-1 is furthest
            # Leave gap between properties for clarity
            if i == 0:
                # First line above center: min is closer to center (bottom), max is farther from center (top)
                min_y = center_y - box_height/2 - line_height_above * 0.05
                max_y = min_y - line_height_above * 0.85
            else:
                # Subsequent lines: add gap above previous property's max
                # Next property's min should be above (smaller Y than) previous property's max
                gap = line_height_above * 0.10
                max_y = max_y - line_height_above * 0.85 - gap  # Continue upward with gap and property height
                min_y = max_y + line_height_above * 0.85  # Min is below max (larger Y)

            self._draw_single_property_line(painter, elements, prop_config, min_y, max_y, margin_left, center_y)

        # Draw properties below center (min of one = max of previous)
        for i in range(N_below):
            prop_key = all_property_keys[N_above + i]
            prop_config = PTT_PROPERTY_CONFIGS[prop_key]

            # Calculate y range for this property line (from top to bottom)
            # Line i=0 is closest to elements, i=N_below-1 is furthest
            # Leave gap between properties for clarity
            if i == 0:
                # First line below center: min is just below element boxes
                min_y = center_y + box_height/2 + line_height_below * 0.05
                max_y = min_y + line_height_below * 0.85
            else:
                # Subsequent lines: add gap below previous property
                gap = line_height_below * 0.10
                min_y = max_y + gap  # Start above max of previous with gap
                max_y = min_y + line_height_below * 0.85

            self._draw_single_property_line(painter, elements, prop_config, min_y, max_y, margin_left, center_y)

    def _draw_single_property_line(self, painter, elements, prop_config: PTTPropertyConfig, min_y, max_y, margin_left, center_y):
        """Draw a single property trend line with reference lines and labels.

        Args:
            painter: QPainter instance
            elements: List of element dictionaries
            prop_config: PTTPropertyConfig dataclass instance
            min_y, max_y: Y coordinate range for this property line
            margin_left: Left margin for labels
            center_y: Y coordinate of the center line
        """
        property_key = prop_config.key
        color = prop_config.color
        label = prop_config.label

        # Calculate min/max values for this property using property key
        min_val, max_val = self._get_property_range(elements, property_key)

        # Determine if this is above or below center (for label positioning)
        # Above center: both min_y and max_y are less than center_y
        is_above = max_y < center_y

        # Draw dashed reference lines for min and max
        painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine))

        # Get element x range
        first_x = elements[0]['x']
        last_x = elements[-1]['x']

        # Draw min reference line (always at min_y - the Y coordinate for minimum values)
        painter.drawLine(QPointF(first_x, min_y), QPointF(last_x, min_y))

        # Draw max reference line (always at max_y - the Y coordinate for maximum values)
        painter.drawLine(QPointF(first_x, max_y), QPointF(last_x, max_y))

        # Build the property value path
        path = QPainterPath()
        first = True

        for elem in elements:
            x = elem['x']
            normalized_value = self._get_normalized_property_value(elem, property_key)

            # Map normalized value (-1 to 1) to y range (min_y to max_y)
            y = min_y + (normalized_value + 1) / 2 * (max_y - min_y)

            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)

        # Draw the property line (solid, thicker)
        painter.setPen(QPen(color, 2.5, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Draw labels
        self._draw_property_labels(painter, label, color, min_val, max_val, min_y, max_y,
                                   first_x, last_x, margin_left, is_above)

    def _get_normalized_property_value(self, elem, property_key: PTTPropertyKey):
        """Get normalized property value in range -1 to 1.

        Args:
            elem: Element dictionary
            property_key: PTTPropertyKey enum value

        Returns:
            Normalized value in range -1 to 1
        """
        value_map = {
            PTTPropertyKey.IONIZATION: lambda e: (e.get('ie', 0) - 14) / 11,
            PTTPropertyKey.ELECTRONEGATIVITY: lambda e: (e.get('electronegativity', 0) - 2) / 2,
            PTTPropertyKey.MELTING: lambda e: (e.get('melting_point', 0) - 1500) / 1500,
            PTTPropertyKey.BOILING: lambda e: (e.get('boiling_point', 0) - 2000) / 2000,
            PTTPropertyKey.RADIUS: lambda e: (e.get('atomic_radius', 0) - 150) / 150,
            PTTPropertyKey.DENSITY: lambda e: math.log10(max(e.get('density', 1), 0.001)) / 1.5,
            PTTPropertyKey.ELECTRON_AFFINITY: lambda e: (e.get('electron_affinity', 0) - 100) / 150,
            PTTPropertyKey.VALENCE: lambda e: (e.get('valence_electrons', 1) - 4) / 4
        }

        calc_func = value_map.get(property_key)
        return calc_func(elem) if calc_func else 0

    def _get_property_range(self, elements, property_key: PTTPropertyKey):
        """Get min and max values for a property across all elements.

        Args:
            elements: List of element dictionaries
            property_key: PTTPropertyKey enum value

        Returns:
            Tuple of (min_value, max_value)
        """
        # Get element key from config
        if property_key not in PTT_PROPERTY_CONFIGS:
            return 0, 0

        element_key = PTT_PROPERTY_CONFIGS[property_key].element_key

        values = [elem.get(element_key, 0) for elem in elements if elem.get(element_key) is not None]
        if not values:
            return 0, 0

        return min(values), max(values)

    def _draw_property_legend(self, painter, config, min_val, max_val, margin_left):
        """Draw label and min/max legend for a property line."""
        color = config['color']
        property_name = config['property']
        label = config['label']
        min_y = config['min_y']
        max_y = config['max_y']

        # Property name mapping for display
        display_names = {
            'ionization': 'Ionization Energy (eV)',
            'electronegativity': 'Electronegativity',
            'melting': 'Melting Point (K)',
            'boiling': 'Boiling Point (K)',
            'radius': 'Atomic Radius (pm)',
            'density': 'Density (g/cm³)',
            'electron_affinity': 'Electron Affinity (kJ/mol)',
            'valence': 'Valence Electrons'
        }

        display_name = display_names.get(property_name, property_name.title())

        # Draw label on the LEFT (outside graph, right-aligned)
        # Position at middle of the line range
        midpoint_y = (min_y + max_y) / 2

        painter.setPen(QPen(color, 1))
        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)

        # Label position - LEFT of graph, right-aligned
        label_text = f"{label}: {display_name}"
        label_rect = QRectF(10, midpoint_y - 12, margin_left - 20, 24)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label_text)

        # Draw min/max values on the RIGHT (outside graph, left-aligned)
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)

        # Format values
        if isinstance(min_val, float):
            min_str = f"{min_val:.2f}"
            max_str = f"{max_val:.2f}"
        else:
            min_str = str(int(min_val))
            max_str = str(int(max_val))

        # Right side position - after all elements
        right_x = self.widget_width - max(20, self.widget_width * 0.02)

        # Min value at min_y position - RIGHT side, left-aligned
        min_rect = QRectF(right_x - 150, min_y - 10, 145, 20)
        painter.drawText(min_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Min: {min_str}")

        # Max value at max_y position - RIGHT side, left-aligned
        max_rect = QRectF(right_x - 150, max_y - 10, 145, 20)
        painter.drawText(max_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Max: {max_str}")

    def _draw_property_labels(self, painter, label, color, min_val, max_val, min_y, max_y,
                              first_x, last_x, margin_left, is_above):
        """Draw property title and min/max labels.

        Args:
            label: Property label (e.g., "Ionization Energy")
            color: Line color
            min_val, max_val: Min and max property values
            min_y, max_y: Y coordinates for min and max
            first_x, last_x: X coordinates of first and last elements
            margin_left: Left margin
            is_above: True if line is above center
        """
        # Format values
        if isinstance(min_val, float):
            min_str = f"{min_val:.2f}"
            max_str = f"{max_val:.2f}"
        else:
            min_str = str(int(min_val))
            max_str = str(int(max_val))

        # Create gradient colors for min/max labels
        # Min should use a darker version of the color, max should use the full color
        min_color = color.darker(150)
        max_color = color.lighter(110)

        # Title font (middle, bold)
        title_font = QFont(UIConstants.FONT_FAMILY, UIConstants.LABEL_FONT_SIZE, QFont.Weight.Bold)
        # Min/max font (smaller, not bold)
        value_font = QFont(UIConstants.FONT_FAMILY, UIConstants.VALUE_FONT_SIZE, QFont.Weight.Normal)

        # Calculate vertical positions with spacing to avoid overlap
        title_y = (min_y + max_y) / 2
        label_spacing = UIConstants.LABEL_VERTICAL_SPACING
        half_label_height = UIConstants.LABEL_HEIGHT / 2

        # Position min/max labels near their reference lines, but inset toward title to avoid overlap
        # In screen coordinates, Y increases downward

        # Min label is always at min_y (the line where value=min), offset inward toward title
        # Max label is always at max_y (the line where value=max), offset inward toward title
        if is_above:
            # Above center: min_y is visually LOWER (larger Y, near center), max_y is visually HIGHER (smaller Y, far from center)
            # Offset inward means: move min label UP toward title (subtract spacing), move max label DOWN toward title (add spacing)
            min_label_y = min_y - label_spacing
            max_label_y = max_y + label_spacing
        else:
            # Below center: min_y is visually HIGHER (smaller Y, near center), max_y is visually LOWER (larger Y, far from center)
            # Offset inward means: move min label DOWN toward title (add spacing), move max label UP toward title (subtract spacing)
            min_label_y = min_y + label_spacing
            max_label_y = max_y - label_spacing

        # Draw LEFT side labels (aligned right)
        left_x = 0
        left_width = margin_left - UIConstants.LABEL_HORIZONTAL_MARGIN

        # Max label
        painter.setFont(value_font)
        painter.setPen(QPen(max_color, 1))
        max_rect_left = QRectF(left_x, max_label_y - half_label_height, left_width, UIConstants.LABEL_HEIGHT)
        painter.drawText(max_rect_left, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, max_str)

        # Title label
        painter.setFont(title_font)
        painter.setPen(QPen(color, 1))
        title_rect_left = QRectF(left_x, title_y - half_label_height, left_width, UIConstants.LABEL_HEIGHT)
        painter.drawText(title_rect_left, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

        # Min label
        painter.setFont(value_font)
        painter.setPen(QPen(min_color, 1))
        min_rect_left = QRectF(left_x, min_label_y - half_label_height, left_width, UIConstants.LABEL_HEIGHT)
        painter.drawText(min_rect_left, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, min_str)

        # Draw RIGHT side labels (aligned left)
        right_x = last_x + 10
        right_width = self.widget_width - right_x - UIConstants.LABEL_HORIZONTAL_MARGIN

        # Max label
        painter.setFont(value_font)
        painter.setPen(QPen(max_color, 1))
        max_rect_right = QRectF(right_x, max_label_y - half_label_height, right_width, UIConstants.LABEL_HEIGHT)
        painter.drawText(max_rect_right, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, max_str)

        # Title label
        painter.setFont(title_font)
        painter.setPen(QPen(color, 1))
        title_rect_right = QRectF(right_x, title_y - half_label_height, right_width, UIConstants.LABEL_HEIGHT)
        painter.drawText(title_rect_right, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

        # Min label
        painter.setFont(value_font)
        painter.setPen(QPen(min_color, 1))
        min_rect_right = QRectF(right_x, min_label_y - half_label_height, right_width, UIConstants.LABEL_HEIGHT)
        painter.drawText(min_rect_right, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, min_str)

    def _draw_spectrum_lines(self, painter, elements, table_state):
        """Draw spectrum emission lines as colored pixels perpendicular to the horizontal axis."""
        if not elements:
            return

        # For linear layout, elements are arranged horizontally at their x positions
        # Draw spectrum lines vertically (perpendicular to horizontal arrangement)
        for i in range(len(elements) - 1):
            elem = elements[i]
            next_elem = elements[i + 1]

            # Get horizontal positions
            x1 = elem['x'] + elem['box_width'] / 2
            y1 = elem['y']
            x2 = next_elem['x'] + next_elem['box_width'] / 2
            y2 = next_elem['y']

            # Draw spectrum pixels on the line segment between elements
            self.draw_spectrum_pixels_on_line(painter, elem, x1, y1, x2, y2, wavelength_to_rgb)

    def _draw_linear_element(self, painter, elem, table_state, passes_filter):
        """Draw element as box in linear layout with multi-property visual encoding."""
        x = elem['x']
        y = elem['y']
        box_width = elem['box_width']
        box_height = elem['box_height']

        alpha = 255 if passes_filter else 60

        # Get fill color (property-based)
        fill_color = self.get_property_color(
            elem, table_state['fill_property'],
            get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
            get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
        )
        fill_color.setAlpha(alpha)

        hovered_element = table_state.get('hovered_element')
        selected_element = table_state.get('selected_element')

        # Highlight effects
        is_hovered = (elem == hovered_element)
        is_selected = (elem == selected_element)

        if is_hovered:
            fill_color = fill_color.lighter(120)
        if is_selected:
            fill_color = fill_color.lighter(140)

        # Draw box background
        half_width = box_width / 2
        half_height = box_height / 2
        box_rect = QRectF(x - half_width, y - half_height, box_width, box_height)

        painter.setPen(Qt.PenStyle.NoPen)

        # Use spectrum gradient if spectrum property selected
        if self.should_draw_spectrum_gradient(table_state['fill_property']):
            spectrum_gradient = self.create_spectrum_gradient(
                elem, x - half_width, y, x + half_width, y, wavelength_to_rgb, alpha
            )
            if spectrum_gradient:
                painter.setBrush(QBrush(spectrum_gradient))
            else:
                painter.setBrush(QBrush(fill_color))
        else:
            painter.setBrush(QBrush(fill_color))

        painter.drawRect(box_rect)

        # Draw border (thickness based on border_property)
        border_width = self.get_border_width(elem, table_state['border_property'])
        border_color = self.get_property_color(
            elem, table_state['border_property'],
            get_ie_color, get_electroneg_color, get_melting_color, get_radius_color,
            get_density_color, get_electron_affinity_color, get_boiling_color, wavelength_to_rgb
        )
        border_color.setAlpha(alpha)

        if is_hovered or is_selected:
            border_width = max(border_width, 3)
            border_color = QColor(255, 255, 100, alpha)

        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(box_rect)

        # Vertical position within box based on normalized property value
        # This creates a visual indicator showing property variation
        glow_property = table_state['glow_property']
        if glow_property != 'none':
            normalized_value = self._get_normalized_property_value(elem, glow_property)
            # Map -1 to 1 range to vertical position within box
            indicator_y = y + normalized_value * half_height * 0.7  # 70% of half height

            # Draw horizontal indicator line
            indicator_color = QColor(255, 255, 255, int(alpha * 0.8))
            painter.setPen(QPen(indicator_color, 2))
            painter.drawLine(QPointF(x - half_width * 0.8, indicator_y),
                           QPointF(x + half_width * 0.8, indicator_y))

        # Draw element symbol and atomic number
        if passes_filter or is_hovered or is_selected:
            text_alpha = alpha
            text_color = QColor(255, 255, 255, text_alpha)

            if is_hovered or is_selected:
                text_color = QColor(255, 255, 100, 255)

            # Draw symbol
            painter.setPen(QPen(text_color, 1))
            symbol_font = QFont('Arial', max(8, int(box_width * 0.2)), QFont.Weight.Bold)
            painter.setFont(symbol_font)

            symbol_rect = QRectF(x - half_width, y - half_height * 0.5, box_width, half_height * 0.6)
            painter.drawText(symbol_rect, Qt.AlignmentFlag.AlignCenter, elem.get('symbol', ''))

            # Draw atomic number (smaller, at top)
            number_font = QFont('Arial', max(6, int(box_width * 0.12)))
            painter.setFont(number_font)
            number_rect = QRectF(x - half_width, y - half_height * 0.95, box_width, half_height * 0.3)
            painter.drawText(number_rect, Qt.AlignmentFlag.AlignCenter, str(elem.get('z', '')))

        # Isotopes (small markers at bottom of box)
        if table_state.get('show_isotopes', False) and passes_filter:
            self._draw_isotopes_in_box(painter, elem, x, y, half_width, half_height, alpha)

    def _draw_isotopes_in_box(self, painter, elem, x, y, half_width, half_height, alpha):
        """Draw isotope markers at bottom of box."""
        isotopes = ISOTOPES.get(elem['symbol'], [])
        if not isotopes:
            return

        # Draw isotopes as small circles near bottom of box
        iso_y_base = y + half_height * 0.6
        num_isotopes = min(len(isotopes), 3)  # Limit to 3
        iso_spacing = (half_width * 1.6) / (num_isotopes + 1) if num_isotopes > 0 else 0

        for iso_idx, (mass, abundance) in enumerate(isotopes[:num_isotopes]):
            iso_x = x - half_width * 0.8 + (iso_idx + 1) * iso_spacing
            iso_size = 1.5 + (abundance / 100) * 2.5
            neutron_count = mass - elem['z']
            iso_color = QColor(150 + neutron_count * 5, 150 + neutron_count * 3, 255, alpha)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(iso_color))
            painter.drawEllipse(QPointF(iso_x, iso_y_base), iso_size, iso_size)

    def _draw_isotopes(self, painter, elem, x, y, alpha):
        """Draw isotope markers below element (legacy method for compatibility)."""
        isotopes = ISOTOPES.get(elem['symbol'], [])
        if not isotopes:
            return

        iso_y_offset = 15
        for iso_idx, (mass, abundance) in enumerate(isotopes[:3]):  # Limit to 3
            iso_y = y + iso_y_offset + iso_idx * 5
            iso_size = 1 + (abundance / 100) * 3
            neutron_count = mass - elem['z']
            iso_color = QColor(150 + neutron_count * 5, 150 + neutron_count * 3, 255, alpha)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(iso_color))
            painter.drawEllipse(QPointF(x, iso_y), iso_size, iso_size)
