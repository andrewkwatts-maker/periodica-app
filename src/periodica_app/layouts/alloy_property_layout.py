"""
Alloy Property Layout
Arranges alloys in a scatter plot based on two properties (e.g., strength vs density).

Uses data-driven configuration from layout_config.json.
"""

import math
from typing import List, Dict, Tuple
from periodica.core.alloy_enums import AlloyProperty, AlloyCategory
from periodica.data.layout_config_loader import get_alloy_config, get_layout_config


class AlloyPropertyLayout:
    """Property scatter plot layout for alloys"""

    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height
        self._load_config()

        # Default properties for axes
        self.x_property = 'density'
        self.y_property = 'tensile_strength'

    def _load_config(self):
        """Load layout configuration from JSON."""
        config = get_layout_config()
        margins = config.get_margins('alloys')

        # Get scatter plot specific config
        scatter_config = get_alloy_config('scatter_plot', default={})

        self.card_size = scatter_config.get('card_size', 60)  # Smaller cards for scatter plot
        self.padding = scatter_config.get('plot_padding', 80)
        self.axis_padding = scatter_config.get('axis_padding', 60)

        # Fall back to global margins if not specified
        if not scatter_config:
            self.padding = margins.get('top', 80)

    def set_x_property(self, prop: str):
        """Set the property for X axis"""
        self.x_property = prop

    def set_y_property(self, prop: str):
        """Set the property for Y axis"""
        self.y_property = prop

    def calculate_layout(self, alloys: List[Dict]) -> List[Dict]:
        """
        Calculate positions for alloys based on property values.

        Args:
            alloys: List of alloy dictionaries

        Returns:
            List of alloys with position data added
        """
        if not alloys:
            return []

        # Reload config in case it changed
        self._load_config()

        # Get property ranges
        x_values = [a.get(self.x_property, 0) for a in alloys]
        y_values = [a.get(self.y_property, 0) for a in alloys]

        x_min, x_max = min(x_values) if x_values else 0, max(x_values) if x_values else 1
        y_min, y_max = min(y_values) if y_values else 0, max(y_values) if y_values else 1

        # Add some padding to ranges
        x_range = x_max - x_min if x_max > x_min else 1
        y_range = y_max - y_min if y_max > y_min else 1
        x_min -= x_range * 0.05
        x_max += x_range * 0.05
        y_min -= y_range * 0.05
        y_max += y_range * 0.05

        # Calculate plot area
        plot_left = self.padding + self.axis_padding
        plot_right = self.widget_width - self.padding
        plot_top = self.padding
        plot_bottom = self.widget_height - self.padding - self.axis_padding

        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top

        positioned_alloys = []

        for alloy in alloys:
            x_val = alloy.get(self.x_property, 0)
            y_val = alloy.get(self.y_property, 0)

            # Normalize to plot coordinates
            if x_max > x_min:
                norm_x = (x_val - x_min) / (x_max - x_min)
            else:
                norm_x = 0.5

            if y_max > y_min:
                norm_y = (y_val - y_min) / (y_max - y_min)
            else:
                norm_y = 0.5

            # Convert to pixel coordinates (Y is inverted)
            x = plot_left + norm_x * plot_width - self.card_size / 2
            y = plot_bottom - norm_y * plot_height - self.card_size / 2

            category_color = AlloyCategory.get_color(alloy.get('category', 'Other'))

            alloy_copy = alloy.copy()
            alloy_copy['x'] = x
            alloy_copy['y'] = y
            alloy_copy['width'] = self.card_size
            alloy_copy['height'] = self.card_size
            alloy_copy['x_value'] = x_val
            alloy_copy['y_value'] = y_val
            alloy_copy['category_color'] = category_color
            positioned_alloys.append(alloy_copy)

        # Store axis info for rendering
        self._axis_info = {
            'x_min': x_min,
            'x_max': x_max,
            'y_min': y_min,
            'y_max': y_max,
            'plot_left': plot_left,
            'plot_right': plot_right,
            'plot_top': plot_top,
            'plot_bottom': plot_bottom,
            'x_property': self.x_property,
            'y_property': self.y_property
        }

        return positioned_alloys

    def get_axis_info(self) -> Dict:
        """Get axis information for rendering"""
        return getattr(self, '_axis_info', {})

    def get_axis_ticks(self, num_ticks: int = 5) -> Dict:
        """Generate tick marks for both axes"""
        info = self.get_axis_info()
        if not info:
            return {'x_ticks': [], 'y_ticks': []}

        x_ticks = []
        y_ticks = []

        x_range = info['x_max'] - info['x_min']
        y_range = info['y_max'] - info['y_min']

        for i in range(num_ticks):
            t = i / (num_ticks - 1)

            # X axis ticks
            x_val = info['x_min'] + t * x_range
            x_pos = info['plot_left'] + t * (info['plot_right'] - info['plot_left'])
            x_ticks.append({'value': x_val, 'position': x_pos})

            # Y axis ticks
            y_val = info['y_min'] + t * y_range
            y_pos = info['plot_bottom'] - t * (info['plot_bottom'] - info['plot_top'])
            y_ticks.append({'value': y_val, 'position': y_pos})

        return {'x_ticks': x_ticks, 'y_ticks': y_ticks}

    def get_alloy_at_position(self, x: float, y: float, alloys: List[Dict]) -> Dict:
        """Find alloy at given position."""
        for alloy in alloys:
            ax = alloy.get('x', 0)
            ay = alloy.get('y', 0)
            size = self.card_size

            # Use circular hit detection for scatter plot points
            cx = ax + size / 2
            cy = ay + size / 2
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)

            if dist <= size / 2 + 5:  # 5px tolerance
                return alloy

        return None

    def update_dimensions(self, width: int, height: int):
        """Update widget dimensions"""
        self.widget_width = width
        self.widget_height = height

    def get_content_height(self, alloys: List[Dict]) -> int:
        """Calculate total content height (fixed for scatter plot)"""
        return self.widget_height
