"""
Charge Order Layout Renderer for Subatomic Particles
Groups particles by their electric charge

Uses data-driven configuration from layout_config.json
"""

from periodica.data.layout_config_loader import get_subatomic_config, get_layout_config


class SubatomicChargeLayout:
    """Layout renderer that groups particles by charge"""

    def __init__(self, widget_width, widget_height):
        self.widget_width = widget_width
        self.widget_height = widget_height
        self._load_config()

    def _load_config(self):
        """Load configuration from JSON config file"""
        config = get_layout_config()
        card_size = config.get_card_size('subatomic')
        spacing = config.get_spacing('subatomic')
        margins = config.get_margins('subatomic')

        self.card_width = card_size.get('width', 140)
        self.card_height = card_size.get('height', 180)
        self.card_spacing = spacing.get('card', 20)
        self.section_spacing = spacing.get('section', 60)
        self.header_height = spacing.get('header', 40)
        self.margin_left = margins.get('left', 50)
        self.margin_right = margins.get('right', 50)

        # Charge ordering from config
        self.charge_order = config.get_ordering('subatomic', 'charge') or [2, 1, 0, -1, -2]

        # Charge colors from config color scheme
        color_scheme = config.get_color_scheme('subatomic')
        self.charge_colors = get_subatomic_config('charge_colors', default={
            2: (255, 100, 100),    # +2 red
            1: (255, 183, 77),     # +1 orange
            0: (200, 200, 200),    # 0 gray
            -1: (100, 181, 246),   # -1 blue
            -2: (156, 39, 176),    # -2 purple
        })

    def calculate_layout(self, particles):
        """
        Calculate positions for particles grouped by charge.

        Args:
            particles: List of particle dictionaries

        Returns:
            Dictionary mapping particle names to position data
        """
        layout_data = {}

        # Group by charge
        charge_groups = {}
        for p in particles:
            charge = p.get('Charge_e', 0)
            if charge not in charge_groups:
                charge_groups[charge] = []
            charge_groups[charge].append(p)

        y_offset = self.header_height + 20
        x_start = self.margin_left

        # Calculate columns
        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))

        # Process charges in configured order, or by sorted keys if not found
        ordered_charges = [c for c in self.charge_order if c in charge_groups]
        remaining_charges = sorted([c for c in charge_groups.keys() if c not in ordered_charges], reverse=True)
        all_charges = ordered_charges + remaining_charges

        for charge in all_charges:
            group = charge_groups[charge]
            charge_str = f"+{charge}" if charge > 0 else str(charge)

            # Get color from config or default
            if isinstance(self.charge_colors, dict):
                color = self.charge_colors.get(charge, (150, 150, 150))
                if isinstance(color, str):
                    # Convert hex to RGB tuple if needed
                    color = (150, 150, 150)
            else:
                color = (150, 150, 150)

            # Section header
            layout_data[f'_charge_{charge}_header'] = {
                'type': 'header',
                'x': x_start,
                'y': y_offset,
                'text': f'CHARGE: {charge_str} e',
                'subtitle': f'{len(group)} particle{"s" if len(group) != 1 else ""}',
                'color': color
            }
            y_offset += self.header_height

            # Sort group by mass
            group_sorted = sorted(group, key=lambda p: p.get('Mass_MeVc2', 0))

            for i, particle in enumerate(group_sorted):
                row = i // cols
                col = i % cols
                x = x_start + col * (self.card_width + self.card_spacing)
                y = y_offset + row * (self.card_height + self.card_spacing)

                layout_data[particle['Name']] = {
                    'type': 'particle',
                    'x': x,
                    'y': y,
                    'width': self.card_width,
                    'height': self.card_height,
                    'particle': particle,
                    'charge_group': charge
                }

            # Calculate rows for this group
            group_rows = (len(group) + cols - 1) // cols
            y_offset += group_rows * (self.card_height + self.card_spacing) + self.section_spacing

        return layout_data

    def get_content_height(self, particles):
        """Calculate total content height"""
        # Group by charge
        charge_groups = {}
        for p in particles:
            charge = p.get('Charge_e', 0)
            if charge not in charge_groups:
                charge_groups[charge] = []
            charge_groups[charge].append(p)

        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))

        height = self.header_height + 20

        for charge, group in charge_groups.items():
            height += self.header_height
            rows = (len(group) + cols - 1) // cols
            height += rows * (self.card_height + self.card_spacing) + self.section_spacing

        return height + self.margin_left

    def update_dimensions(self, width, height):
        """Update layout dimensions"""
        self.widget_width = width
        self.widget_height = height
