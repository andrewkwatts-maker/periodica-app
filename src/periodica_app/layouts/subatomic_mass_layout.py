"""
Mass Order Layout Renderer for Subatomic Particles
Displays all particles ordered by their mass

Uses data-driven configuration from layout_config.json
"""

from periodica.data.layout_config_loader import get_subatomic_config, get_layout_config


class SubatomicMassLayout:
    """Layout renderer that orders particles by mass"""

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
        self.header_height = spacing.get('header', 40)
        self.margin_left = margins.get('left', 50)
        self.margin_right = margins.get('right', 50)
        self.margin_top = margins.get('top', 100)

        # Mass ranges from config
        self.mass_ranges = get_subatomic_config('mass_ranges', default=[
            {'min': 0, 'max': 200, 'label': 'Light (< 200 MeV)'},
            {'min': 200, 'max': 1000, 'label': 'Medium (200-1000 MeV)'},
            {'min': 1000, 'max': 2000, 'label': 'Heavy (1-2 GeV)'},
            {'min': 2000, 'max': float('inf'), 'label': 'Very Heavy (> 2 GeV)'}
        ])

    def calculate_layout(self, particles):
        """
        Calculate positions for all particles ordered by mass.

        Args:
            particles: List of particle dictionaries

        Returns:
            Dictionary mapping particle names to position data
        """
        layout_data = {}

        y_offset = self.header_height + 20
        x_start = self.margin_left

        # Calculate columns
        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))

        # Header
        layout_data['_mass_header'] = {
            'type': 'header',
            'x': x_start,
            'y': y_offset,
            'text': 'PARTICLES BY MASS',
            'subtitle': 'Lightest to heaviest (MeV/c^2)',
            'color': (255, 183, 77)
        }
        y_offset += self.header_height

        # Sort by mass
        sorted_particles = sorted(particles, key=lambda p: p.get('Mass_MeVc2', 0))

        # Add mass scale markers from config
        mass_ranges = [
            (r.get('min', 0), r.get('max', float('inf')), r.get('label', ''))
            for r in self.mass_ranges
        ] if isinstance(self.mass_ranges, list) else [
            (0, 200, 'Light (< 200 MeV)'),
            (200, 1000, 'Medium (200-1000 MeV)'),
            (1000, 2000, 'Heavy (1-2 GeV)'),
            (2000, float('inf'), 'Very Heavy (> 2 GeV)')
        ]

        current_range_idx = 0
        for i, particle in enumerate(sorted_particles):
            mass = particle.get('Mass_MeVc2', 0)

            # Check if we need a new range header
            while current_range_idx < len(mass_ranges):
                min_m, max_m, label = mass_ranges[current_range_idx]
                if min_m <= mass < max_m:
                    break
                current_range_idx += 1

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
                'mass_rank': i + 1
            }

        return layout_data

    def get_content_height(self, particles):
        """Calculate total content height"""
        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))

        rows = (len(particles) + cols - 1) // cols
        height = self.header_height * 2 + 20
        height += rows * (self.card_height + self.card_spacing)

        return height + self.margin_left

    def update_dimensions(self, width, height):
        """Update layout dimensions"""
        self.widget_width = width
        self.widget_height = height
