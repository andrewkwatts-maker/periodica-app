"""
Alloy Lattice Layout
Arranges alloys grouped by their crystal structure (FCC, BCC, HCP, etc.).

Uses data-driven configuration from layout_config.json.
"""

from typing import List, Dict
from periodica.core.alloy_enums import CrystalStructure
from periodica.data.layout_config_loader import get_alloy_config, get_layout_config


class AlloyLatticeLayout:
    """Crystal structure grouped layout for alloys"""

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
        self.group_spacing = spacing.get('group', 40) + 10  # Extra spacing for structure descriptions
        self.header_height = spacing.get('header', 45) + 10  # Extra height for structure description

    def calculate_layout(self, alloys: List[Dict]) -> List[Dict]:
        """
        Calculate positions for alloys grouped by crystal structure.

        Args:
            alloys: List of alloy dictionaries

        Returns:
            List of alloys with position data added
        """
        if not alloys:
            return []

        # Reload config in case it changed
        self._load_config()

        # Group alloys by crystal structure
        groups = {}
        for alloy in alloys:
            structure = alloy.get('crystal_structure', 'Unknown')
            if structure not in groups:
                groups[structure] = []
            groups[structure].append(alloy)

        positioned_alloys = []
        current_y = self.padding

        # Get structure order from config
        structure_order = get_layout_config().get_ordering('alloys', 'crystal_structure')
        if not structure_order:
            structure_order = ['FCC', 'BCC', 'HCP', 'BCT', 'Mixed', 'Unknown']

        # Add any structures not in the predefined order
        for struct in sorted(groups.keys()):
            if struct not in structure_order:
                # Insert before 'Unknown' or 'Other' if present
                if 'Unknown' in structure_order:
                    idx = structure_order.index('Unknown')
                    structure_order.insert(idx, struct)
                elif 'Other' in structure_order:
                    idx = structure_order.index('Other')
                    structure_order.insert(idx, struct)
                else:
                    structure_order.append(struct)

        # Get structure descriptions from config
        structure_descriptions = get_alloy_config('structure_descriptions', default={})

        for structure in structure_order:
            group_alloys = groups.get(structure, [])
            if not group_alloys:
                continue

            group_color = CrystalStructure.get_color(structure)
            # Try config description first, then fall back to enum
            description = structure_descriptions.get(structure)
            if not description:
                description = CrystalStructure.get_description(structure)

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
                alloy_copy['group'] = structure
                alloy_copy['group_description'] = description
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
            if group and group not in headers:
                headers[group] = {
                    'name': group,
                    'description': alloy.get('group_description', ''),
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
