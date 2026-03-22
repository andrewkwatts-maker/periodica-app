#====== Playtow/PeriodicTable2/layouts/base_layout.py ======#
#!copyright (c) 2025 Andrew Keith Watts. All rights reserved.
#!
#!This is the intellectual property of Andrew Keith Watts. Unauthorized
#!reproduction, distribution, or modification of this code, in whole or in part,
#!without the express written permission of Andrew Keith Watts is strictly prohibited.
#!
#!For inquiries, please contact AndrewKWatts@Gmail.com

"""
Base Layout Renderer
Abstract base class defining the interface for all layout renderers.
Provides common utility methods for filtering and property calculations.
"""

from abc import ABC, abstractmethod
import math
from PySide6.QtGui import QColor, QRadialGradient, QBrush, QPen, QLinearGradient
from PySide6.QtCore import Qt, QPointF, QRectF
from periodica.core.pt_enums import PTPropertyName
from periodica_app.constants import VisualizationConstants


class BaseLayoutRenderer(ABC):
    """
    Abstract base class for layout renderers.
    All layout renderers must implement create_layout() and paint() methods.
    """

    def __init__(self, widget_width, widget_height):
        """
        Initialize layout renderer with widget dimensions.

        Args:
            widget_width: Width of the widget in pixels
            widget_height: Height of the widget in pixels
        """
        self.widget_width = widget_width
        self.widget_height = widget_height

    @abstractmethod
    def create_layout(self, base_elements, **kwargs):
        """
        Create layout data for elements.

        Args:
            base_elements: List of base element dictionaries
            **kwargs: Additional layout-specific parameters

        Returns:
            List of element dictionaries with layout-specific position data
        """
        pass

    @abstractmethod
    def paint(self, painter, elements, table_state, **kwargs):
        """
        Paint the layout.

        Args:
            painter: QPainter instance
            elements: List of element dictionaries with layout data
            table_state: Dictionary containing visualization state:
                - fill_property: Property for fill color
                - border_property: Property for border thickness
                - glow_property: Property for glow effect
                - ring_property: Property for inner ring (circular mode)
                - show_isotopes: Boolean for isotope visualization
                - hovered_element: Currently hovered element or None
                - selected_element: Currently selected element or None
            **kwargs: Additional rendering parameters
        """
        pass

    def apply_filter_alpha(self, color, passes_filter):
        """
        Apply filter transparency to a color.

        Args:
            color: QColor instance
            passes_filter: Boolean indicating if element passes filters

        Returns:
            Modified QColor with adjusted alpha
        """
        alpha = 255 if passes_filter else 80
        color.setAlpha(alpha)
        return color

    def get_element_at_position(self, x, y, elements):
        """
        Find element at given position (for mouse interaction).

        Args:
            x: X coordinate
            y: Y coordinate
            elements: List of element dictionaries with position data

        Returns:
            Element dictionary or None
        """
        # Default implementation - should be overridden by specific layouts
        return None

    def calculate_dynamic_spacing(self, total_items, available_space, min_spacing=5, max_spacing=100):
        """
        Calculate optimal spacing for items given available space.

        Args:
            total_items: Number of items to space
            available_space: Available space in pixels
            min_spacing: Minimum spacing between items
            max_spacing: Maximum spacing between items

        Returns:
            Calculated spacing value
        """
        if total_items <= 1:
            return 0

        spacing = available_space / (total_items - 1)
        return max(min_spacing, min(max_spacing, spacing))

    def calculate_period_radii(self, num_periods, base_radius=45, ring_spacing=55):
        """
        Calculate radii for period rings dynamically.

        Args:
            num_periods: Number of periods in the data
            base_radius: Starting radius for first period
            ring_spacing: Spacing between period rings

        Returns:
            List of (r_inner, r_outer) tuples for each period
        """
        period_radii = []
        for period_idx in range(num_periods):
            r_inner = base_radius + period_idx * ring_spacing
            r_outer = r_inner + ring_spacing - 5  # 5px gap between rings
            period_radii.append((r_inner, r_outer))
        return period_radii

    def get_property_color(self, elem, property_name, get_ie_color_func, get_electroneg_color_func,
                          get_melting_color_func, get_radius_color_func, get_density_color_func,
                          get_electron_affinity_color_func, get_boiling_color_func,
                          wavelength_to_rgb_func):
        """
        Get color based on property name using provided color functions.

        Args:
            elem: Element dictionary
            property_name: Name of the property
            get_ie_color_func: Function for ionization energy color
            get_electroneg_color_func: Function for electronegativity color
            get_melting_color_func: Function for melting point color
            get_radius_color_func: Function for atomic radius color
            get_density_color_func: Function for density color
            get_electron_affinity_color_func: Function for electron affinity color
            get_boiling_color_func: Function for boiling point color
            wavelength_to_rgb_func: Function for wavelength to RGB conversion

        Returns:
            QColor instance
        """
        prop_enum = PTPropertyName.from_string(property_name)

        if property_name == "ionization":
            return get_ie_color_func(elem['ie'])
        elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
            return get_electroneg_color_func(elem['electronegativity'])
        elif prop_enum == PTPropertyName.BLOCK:
            return elem['block_color']
        elif prop_enum == PTPropertyName.WAVELENGTH:
            return wavelength_to_rgb_func(elem['wavelength_nm'])
        elif prop_enum == PTPropertyName.SPECTRUM:
            # Blend colors from all emission lines weighted by intensity
            if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
                # Fallback to primary emission wavelength if no spectrum data
                return wavelength_to_rgb_func(elem['wavelength_nm'])

            # Blend colors from all spectrum lines weighted by intensity
            total_r, total_g, total_b = 0.0, 0.0, 0.0
            total_weight = 0.0

            # Default color range for visible spectrum
            color_range_min = VisualizationConstants.VISIBLE_SPECTRUM_MIN  # nm (violet)
            color_range_max = VisualizationConstants.VISIBLE_SPECTRUM_MAX  # nm (red)

            for wavelength, intensity in elem['spectrum_lines']:
                # Only include lines within visible range
                if wavelength < color_range_min or wavelength > color_range_max:
                    continue

                # Get color for this wavelength
                color = wavelength_to_rgb_func(wavelength)
                weight = intensity

                total_r += color.red() * weight
                total_g += color.green() * weight
                total_b += color.blue() * weight
                total_weight += weight

            if total_weight > 0:
                # Return weighted average color
                return QColor(
                    int(total_r / total_weight),
                    int(total_g / total_weight),
                    int(total_b / total_weight)
                )
            else:
                # No lines in visible range, return neutral color
                return QColor(128, 128, 128)
        elif prop_enum == PTPropertyName.MELTING:
            return get_melting_color_func(elem['melting_point'])
        elif prop_enum == PTPropertyName.RADIUS:
            return get_radius_color_func(elem['atomic_radius'])
        elif prop_enum == PTPropertyName.DENSITY:
            return get_density_color_func(elem.get('density', 1.0))
        elif prop_enum == PTPropertyName.BOILING:
            return get_boiling_color_func(elem.get('boiling_point', 300))
        elif property_name == "electron_affinity":
            return get_electron_affinity_color_func(elem.get('electron_affinity', 0))
        elif property_name == "valence":
            valence = elem.get('valence_electrons', 1)
            hue = (valence * 25) % 360
            return QColor.fromHsv(hue, 200, 255)
        return QColor(150, 150, 150)

    def get_border_width(self, elem, border_property):
        """
        Calculate border width based on property.

        Args:
            elem: Element dictionary
            border_property: Property name for border encoding

        Returns:
            Border width in pixels (1-6)
        """
        if border_property == "none":
            return 1
        elif border_property == "radius":
            return 1 + 5 * ((elem['atomic_radius'] - 30) / 320)
        elif border_property == "ionization":
            return 1 + 5 * ((elem['ie'] - 3.5) / (25.0 - 3.5))
        elif border_property == "electronegativity":
            if elem['electronegativity'] == 0:
                return 1
            return 1 + 5 * (elem['electronegativity'] / 4.0)
        elif border_property == "melting":
            return 1 + 5 * min(elem['melting_point'] / 4000.0, 1.0)
        elif border_property == "boiling":
            return 1 + 5 * min(elem.get('boiling_point', 300) / 4000.0, 1.0)
        elif border_property == "density":
            log_density = math.log10(max(elem.get('density', 1.0), 0.0001))
            normalized = (log_density + 4) / 5.3
            return 1 + 5 * max(0, min(1, normalized))
        elif border_property == "electron_affinity":
            affinity = elem.get('electron_affinity', 0)
            normalized = (affinity + 10) / 360
            return 1 + 5 * max(0, min(1, normalized))
        elif border_property == "valence":
            valence = elem.get('valence_electrons', 1)
            return 1 + 5 * (valence / 8.0)
        return 1

    def get_glow_params(self, elem, glow_property):
        """
        Calculate glow parameters based on property.

        Args:
            elem: Element dictionary
            glow_property: Property name for glow encoding

        Returns:
            Tuple of (glow_size, glow_intensity)
        """
        if glow_property == "none":
            return 0, 0
        elif glow_property == "melting":
            intensity = min(elem['melting_point'] / 4000.0, 1.0)
            size = 20 + 30 * intensity
            return size, intensity
        elif glow_property == "ionization":
            intensity = (elem['ie'] - 3.5) / (25.0 - 3.5)
            size = 20 + 30 * intensity
            return size, intensity
        elif glow_property == "radius":
            intensity = (elem['atomic_radius'] - 30) / 320
            size = 20 + 30 * intensity
            return size, intensity
        elif glow_property == "boiling":
            intensity = min(elem.get('boiling_point', 300) / 4000.0, 1.0)
            size = 20 + 30 * intensity
            return size, intensity
        elif glow_property == "density":
            log_density = math.log10(max(elem.get('density', 1.0), 0.0001))
            intensity = max(0, min(1, (log_density + 4) / 5.3))
            size = 20 + 30 * intensity
            return size, intensity
        elif glow_property == "electron_affinity":
            affinity = elem.get('electron_affinity', 0)
            intensity = max(0, min(1, (affinity + 10) / 360))
            size = 20 + 30 * intensity
            return size, intensity
        elif glow_property == "electronegativity":
            if elem['electronegativity'] == 0:
                return 0, 0
            intensity = elem['electronegativity'] / 4.0
            size = 20 + 30 * intensity
            return size, intensity
        elif glow_property == "valence":
            valence = elem.get('valence_electrons', 1)
            intensity = valence / 8.0
            size = 20 + 30 * intensity
            return size, intensity
        return 0, 0

    def draw_glow_effect(self, painter, x, y, glow_size, glow_intensity, fill_color, alpha_scale=1.0):
        """
        Draw glow effect at specified position.

        Args:
            painter: QPainter instance
            x: X coordinate
            y: Y coordinate
            glow_size: Size of glow effect
            glow_intensity: Intensity of glow (0-1)
            fill_color: Base color for glow
            alpha_scale: Additional alpha scaling factor
        """
        if glow_size <= 0:
            return

        glow_grad = QRadialGradient(x, y, glow_size)
        glow_c = QColor(fill_color)
        glow_c.setAlpha(int(100 * glow_intensity * alpha_scale))
        glow_grad.setColorAt(0, glow_c)
        glow_c.setAlpha(0)
        glow_grad.setColorAt(1, glow_c)
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(x, y), glow_size, glow_size)

    def update_dimensions(self, widget_width, widget_height):
        """
        Update widget dimensions (called on resize).

        Args:
            widget_width: New width in pixels
            widget_height: New height in pixels
        """
        self.widget_width = widget_width
        self.widget_height = widget_height

    def create_spectrum_gradient(self, elem, x1, y1, x2, y2, wavelength_to_rgb_func, alpha=255):
        """
        Create a linear gradient showing spectrum lines for an element.

        Args:
            elem: Element dictionary with spectrum_lines data
            x1, y1: Start point of gradient
            x2, y2: End point of gradient
            wavelength_to_rgb_func: Function to convert wavelength to RGB
            alpha: Base alpha value (default 255)

        Returns:
            QLinearGradient with spectrum colors or None if no spectrum data
        """
        if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
            return None

        spectrum_lines = elem['spectrum_lines']

        # Filter to visible spectrum
        visible_lines = [(wl, intensity) for wl, intensity in spectrum_lines
                        if VisualizationConstants.VISIBLE_SPECTRUM_MIN <= wl <= VisualizationConstants.VISIBLE_SPECTRUM_MAX]

        if not visible_lines:
            return None

        # Sort by wavelength
        visible_lines.sort(key=lambda x: x[0])

        # Find wavelength range
        min_wl = min(wl for wl, _ in visible_lines)
        max_wl = max(wl for wl, _ in visible_lines)
        wl_range = max_wl - min_wl
        if wl_range == 0:
            wl_range = 1

        # Create gradient
        gradient = QLinearGradient(x1, y1, x2, y2)

        # Always add color stops at both ends for proper interpolation
        first_wl = visible_lines[0][0]
        last_wl = visible_lines[-1][0]

        # Add first color stop at 0
        first_color = wavelength_to_rgb_func(first_wl)
        first_color.setAlpha(alpha)
        gradient.setColorAt(0.0, first_color)

        # Add color stops for each spectral line
        for wavelength, intensity in visible_lines:
            # Position along gradient (0 to 1)
            t = (wavelength - min_wl) / wl_range

            # Get color for this wavelength
            color = wavelength_to_rgb_func(wavelength)
            color.setAlpha(alpha)

            # Add color stop
            gradient.setColorAt(t, color)

        # Add last color stop at 1
        last_color = wavelength_to_rgb_func(last_wl)
        last_color.setAlpha(alpha)
        gradient.setColorAt(1.0, last_color)

        return gradient

    def should_draw_spectrum_gradient(self, property_name):
        """
        Check if spectrum gradient should be drawn for this property.

        Args:
            property_name: Name of the property

        Returns:
            Boolean indicating if spectrum gradient should be drawn
        """
        from periodica.core.pt_enums import PTPropertyName
        prop_enum = PTPropertyName.from_string(property_name)
        return prop_enum == PTPropertyName.SPECTRUM

    def get_spectrum_color_at_position(self, elem, position_fraction, wavelength_to_rgb_func, alpha=255):
        """
        Get spectrum color at a specific position along the element's spectrum.

        Args:
            elem: Element dictionary with spectrum_lines data
            position_fraction: Position along spectrum (0.0 to 1.0)
            wavelength_to_rgb_func: Function to convert wavelength to RGB
            alpha: Base alpha value (default 255)

        Returns:
            QColor at the specified position or neutral color if no spectrum data
        """
        if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
            # Fallback to primary emission wavelength
            return wavelength_to_rgb_func(elem.get('wavelength_nm', 550))

        spectrum_lines = elem['spectrum_lines']

        # Filter to visible spectrum and sort by wavelength
        visible_lines = [(wl, intensity) for wl, intensity in spectrum_lines
                        if VisualizationConstants.VISIBLE_SPECTRUM_MIN <= wl <= VisualizationConstants.VISIBLE_SPECTRUM_MAX]

        if not visible_lines:
            return QColor(128, 128, 128, alpha)

        visible_lines.sort(key=lambda x: x[0])

        # Find wavelength at this position
        min_wl = min(wl for wl, _ in visible_lines)
        max_wl = max(wl for wl, _ in visible_lines)
        target_wl = min_wl + position_fraction * (max_wl - min_wl)

        # Find the two closest spectrum lines and interpolate
        for i in range(len(visible_lines) - 1):
            wl1, intensity1 = visible_lines[i]
            wl2, intensity2 = visible_lines[i + 1]

            if wl1 <= target_wl <= wl2:
                # Interpolate between the two lines
                if wl2 - wl1 > 0:
                    t = (target_wl - wl1) / (wl2 - wl1)
                    interp_wl = wl1 + t * (wl2 - wl1)
                else:
                    interp_wl = wl1

                color = wavelength_to_rgb_func(interp_wl)
                color.setAlpha(alpha)
                return color

        # If we didn't find a match, use closest line
        closest_line = min(visible_lines, key=lambda x: abs(x[0] - target_wl))
        color = wavelength_to_rgb_func(closest_line[0])
        color.setAlpha(alpha)
        return color

    def draw_spectrum_pixels_on_line(self, painter, elem, x1, y1, x2, y2, wavelength_to_rgb_func):
        """
        Draw spectrum emission lines as colored pixels perpendicular to a line segment.
        This method can be used by all layout renderers to visualize spectral lines.

        Args:
            painter: QPainter instance
            elem: Element dictionary containing 'spectrum_lines' data
            x1, y1: Start point of line segment
            x2, y2: End point of line segment
            wavelength_to_rgb_func: Function to convert wavelength to RGB color
        """
        if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
            return

        spectrum_lines = elem['spectrum_lines']

        # Filter to visible spectrum
        visible_lines = [(wl, intensity) for wl, intensity in spectrum_lines
                        if VisualizationConstants.VISIBLE_SPECTRUM_MIN <= wl <= VisualizationConstants.VISIBLE_SPECTRUM_MAX]

        if not visible_lines:
            return

        # Calculate line length and direction
        dx = x2 - x1
        dy = y2 - y1
        line_length = math.sqrt(dx * dx + dy * dy)

        if line_length < 1:
            return

        # Normalize direction
        dx_norm = dx / line_length
        dy_norm = dy / line_length

        # Draw each spectral line as a small perpendicular mark
        for wavelength, intensity in visible_lines:
            # Skip faint lines
            if intensity < VisualizationConstants.SPECTRUM_INTENSITY_THRESHOLD:
                continue

            # Position along line (map wavelength to position)
            # Use normalized wavelength position (0-1 across visible spectrum)
            spectrum_range = VisualizationConstants.VISIBLE_SPECTRUM_MAX - VisualizationConstants.VISIBLE_SPECTRUM_MIN
            t = (wavelength - VisualizationConstants.VISIBLE_SPECTRUM_MIN) / spectrum_range
            t = max(0, min(1, t))

            # Calculate position on line
            px = x1 + dx * t
            py = y1 + dy * t

            # Perpendicular direction
            perp_x = -dy_norm
            perp_y = dx_norm

            # Line length based on intensity
            mark_range = VisualizationConstants.SPECTRUM_MARK_MAX_LENGTH - VisualizationConstants.SPECTRUM_MARK_MIN_LENGTH
            mark_length = VisualizationConstants.SPECTRUM_MARK_MIN_LENGTH + intensity * mark_range

            # Draw short perpendicular line
            color = wavelength_to_rgb_func(wavelength)
            color.setAlpha(int(255 * intensity))

            painter.setPen(QPen(color, VisualizationConstants.SPECTRUM_LINE_WIDTH, Qt.PenStyle.SolidLine))
            painter.drawLine(
                QPointF(px - perp_x * mark_length / 2, py - perp_y * mark_length / 2),
                QPointF(px + perp_x * mark_length / 2, py + perp_y * mark_length / 2)
            )
