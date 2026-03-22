"""
Decay Chain Layout Renderer for Subatomic Particles
Displays particles ordered by stability with decay relationship arrows

Uses data-driven configuration from layout_config.json
"""

from periodica.data.layout_config_loader import get_subatomic_config, get_layout_config


class SubatomicDecayLayout:
    """Layout renderer showing decay chains and stability ordering"""

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
        # Use slightly larger spacing for arrows
        base_spacing = spacing.get('card', 20)
        self.card_spacing = base_spacing + 10
        self.section_spacing = spacing.get('section', 60)
        self.header_height = spacing.get('header', 40)
        self.margin_left = margins.get('left', 50)
        self.margin_right = margins.get('right', 50)

        # Stability thresholds from config
        self.stability_thresholds = get_subatomic_config('stability_thresholds', default={
            'stable': None,
            'long_lived': 1e-6,
            'short_lived': 1e-12,
            'very_short': 1e-20
        })

        # Stability order from config
        self.stability_order = config.get_ordering('subatomic', 'stability') or [
            'Stable', 'Long-lived', 'Short-lived', 'Very short-lived'
        ]

        # Colors from config color scheme
        color_scheme = config.get_color_scheme('subatomic')
        self.stable_color = self._hex_to_rgb(color_scheme.get('stable', '#00B894'))
        self.unstable_color = self._hex_to_rgb(color_scheme.get('unstable', '#E17055'))

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        if isinstance(hex_color, tuple):
            return hex_color
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def calculate_layout(self, particles):
        """
        Calculate positions for particles ordered by stability.

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
        layout_data['_decay_header'] = {
            'type': 'header',
            'x': x_start,
            'y': y_offset,
            'text': 'STABILITY & DECAY',
            'subtitle': 'Ordered by half-life (most stable first)',
            'color': (129, 199, 132)
        }
        y_offset += self.header_height

        # Sort by stability factor (most stable first)
        sorted_particles = sorted(particles, key=lambda p: -p.get('_stability_factor', 0))

        # Get thresholds from config
        long_lived_threshold = self.stability_thresholds.get('long_lived', 1e-6)
        short_lived_threshold = self.stability_thresholds.get('short_lived', 1e-12)

        # Group by stability ranges using config thresholds
        stability_groups = [
            ('stable', 'Stable Particles', (100, 255, 100),
             lambda p: p.get('Stability') == 'Stable'),
            ('long', f'Long-lived (> {self._format_time(long_lived_threshold)})', (200, 255, 100),
             lambda p: p.get('Stability') != 'Stable' and p.get('HalfLife_s', 0) and p.get('HalfLife_s', 0) > long_lived_threshold),
            ('medium', f'Medium ({self._format_time(short_lived_threshold)} - {self._format_time(long_lived_threshold)})', (255, 255, 100),
             lambda p: p.get('HalfLife_s', 0) and short_lived_threshold <= p.get('HalfLife_s', 0) <= long_lived_threshold),
            ('short', f'Short-lived (< {self._format_time(short_lived_threshold)})', (255, 150, 100),
             lambda p: p.get('HalfLife_s', 0) and p.get('HalfLife_s', 0) < short_lived_threshold),
        ]

        decay_arrows = []

        for group_id, group_name, color, filter_func in stability_groups:
            group_particles = [p for p in sorted_particles if filter_func(p)]

            if not group_particles:
                continue

            # Group header
            layout_data[f'_stability_{group_id}_header'] = {
                'type': 'subheader',
                'x': x_start,
                'y': y_offset,
                'text': group_name,
                'color': color
            }
            y_offset += 30

            for i, particle in enumerate(group_particles):
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
                    'stability_group': group_id
                }

                # Record decay arrows
                decay_products = particle.get('DecayProducts', [])
                for product in decay_products:
                    decay_arrows.append({
                        'from': particle['Name'],
                        'to': product
                    })

            group_rows = (len(group_particles) + cols - 1) // cols
            y_offset += group_rows * (self.card_height + self.card_spacing) + self.section_spacing

        # Store decay arrows for later rendering
        layout_data['_decay_arrows'] = {
            'type': 'arrows',
            'arrows': decay_arrows
        }

        return layout_data

    def _format_time(self, seconds):
        """Format time in appropriate units"""
        if seconds is None:
            return 'stable'
        if seconds >= 1:
            return f'{seconds:.0f} s'
        if seconds >= 1e-3:
            return f'{seconds * 1e3:.0f} ms'
        if seconds >= 1e-6:
            return f'{seconds * 1e6:.0f} us'
        if seconds >= 1e-9:
            return f'{seconds * 1e9:.0f} ns'
        if seconds >= 1e-12:
            return f'{seconds * 1e12:.0f} ps'
        return f'{seconds * 1e15:.0f} fs'

    def get_decay_arrows(self, layout_data):
        """Get list of decay arrows to draw"""
        arrows_data = layout_data.get('_decay_arrows', {})
        return arrows_data.get('arrows', [])

    def get_content_height(self, particles):
        """Calculate total content height"""
        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))

        # Estimate based on number of particles
        rows = (len(particles) + cols - 1) // cols
        # Add extra for group headers
        height = self.header_height * 6 + 20
        height += rows * (self.card_height + self.card_spacing)
        height += self.section_spacing * 4

        return height + self.margin_left

    def update_dimensions(self, width, height):
        """Update layout dimensions"""
        self.widget_width = width
        self.widget_height = height
