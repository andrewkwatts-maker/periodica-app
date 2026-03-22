"""
Alloy Composition Layout
Arranges alloys grouped by their primary (base) element.

Uses data-driven configuration from layout_config.json.
"""

from typing import List, Dict
from periodica.core.alloy_enums import get_element_color
from periodica.data.layout_config_loader import get_alloy_config, get_layout_config


class AlloyCompositionLayout:
    """Primary element grouped layout for alloys"""

    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height
        self._load_config()

    def _load_config(self):
        """Load layout configuration from JSON."""
        config = get_layout_config()
        card_size = config.get_card_size('alloys')
        spacing = config.get_spacing('alloys')
        margins = config.get_margins('alloys')

        self.card_width = card_size.get('width', 160)
        self.card_height = card_size.get('height', 180)
        self.padding = margins.get('left', 30)
        self.spacing = spacing.get('card', 15)
        self.group_spacing = spacing.get('group', 40)
        self.header_height = spacing.get('header', 45)

    def calculate_layout(self, alloys: List[Dict]) -> List[Dict]:
        """
        Calculate positions for alloys grouped by primary element.

        Args:
            alloys: List of alloy dictionaries

        Returns:
            List of alloys with position data added
        """
        if not alloys:
            return []

        # Reload config in case it changed
        self._load_config()

        # Group alloys by primary element
        groups = {}
        for alloy in alloys:
            primary = alloy.get('primary_element', 'Unknown')
            if primary not in groups:
                groups[primary] = []
            groups[primary].append(alloy)

        positioned_alloys = []
        current_y = self.padding

        # Sort elements by number of alloys (most common first)
        sorted_elements = sorted(groups.keys(), key=lambda e: -len(groups[e]))

        # Get element display names from config
        element_names = get_alloy_config('element_display_names', default={})
        if not element_names:
            element_names = {
                'Fe': 'Iron-based',
                'Al': 'Aluminum-based',
                'Cu': 'Copper-based',
                'Ti': 'Titanium-based',
                'Ni': 'Nickel-based',
                'Zn': 'Zinc-based',
                'Sn': 'Tin-based',
                'Ag': 'Silver-based',
                'Au': 'Gold-based',
                'Pb': 'Lead-based'
            }

        for element in sorted_elements:
            group_alloys = groups.get(element, [])
            if not group_alloys:
                continue

            group_color = get_element_color(element)
            display_name = element_names.get(element, f'{element}-based')

            # Calculate cards per row
            available_width = self.widget_width - 2 * self.padding
            cols = max(1, int(available_width / (self.card_width + self.spacing)))

            # Add space for header
            current_y += self.header_height

            # Position alloys in this group
            for idx, alloy in enumerate(group_alloys):
                row = idx // cols
                col = idx % cols

                # Center the row
                items_in_row = min(cols, len(group_alloys) - row * cols)
                row_width = items_in_row * self.card_width + (items_in_row - 1) * self.spacing
                start_x = (self.widget_width - row_width) / 2

                x = start_x + col * (self.card_width + self.spacing)
                y = current_y + row * (self.card_height + self.spacing)

                alloy_copy = alloy.copy()
                alloy_copy['x'] = x
                alloy_copy['y'] = y
                alloy_copy['width'] = self.card_width
                alloy_copy['height'] = self.card_height
                alloy_copy['group'] = display_name
                alloy_copy['group_element'] = element
                alloy_copy['group_color'] = group_color
                alloy_copy['group_header_y'] = current_y - self.header_height
                positioned_alloys.append(alloy_copy)

            # Update current_y for next group
            rows = (len(group_alloys) + cols - 1) // cols
            current_y += rows * (self.card_height + self.spacing) + self.group_spacing

        return positioned_alloys

    def get_group_headers(self, alloys: List[Dict]) -> List[Dict]:
        """Get group header information for rendering"""
        if not alloys:
            return []

        headers = {}
        for alloy in alloys:
            group = alloy.get('group')
            element = alloy.get('group_element', '')
            if group and group not in headers:
                headers[group] = {
                    'name': group,
                    'element': element,
                    'y': alloy.get('group_header_y', 0),
                    'color': alloy.get('group_color', '#FFFFFF'),
                    'count': sum(1 for a in alloys if a.get('group') == group)
                }

        return list(headers.values())

    def get_alloy_at_position(self, x: float, y: float, alloys: List[Dict]) -> Dict:
        """Find alloy at given position."""
        for alloy in alloys:
            ax = alloy.get('x', 0)
            ay = alloy.get('y', 0)
            aw = alloy.get('width', self.card_width)
            ah = alloy.get('height', self.card_height)

            if ax <= x <= ax + aw and ay <= y <= ay + ah:
                return alloy

        return None

    def update_dimensions(self, width: int, height: int):
        """Update widget dimensions"""
        self.widget_width = width
        self.widget_height = height

    def get_content_height(self, alloys: List[Dict]) -> int:
        """Calculate total content height for scrolling"""
        if not alloys:
            return 0

        positioned = self.calculate_layout(alloys)
        if not positioned:
            return 0

        max_y = max(a.get('y', 0) + a.get('height', self.card_height) for a in positioned)
        return int(max_y + self.padding)
