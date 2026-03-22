"""
Baryon/Meson Layout Renderer for Subatomic Particles
Displays baryons and mesons in separate visual groups

Uses data-driven configuration from layout_config.json
"""

from periodica.data.layout_config_loader import get_subatomic_config, get_layout_config


class SubatomicBaryonMesonLayout:
    """Layout renderer that separates baryons and mesons into distinct groups"""

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

        # Particle type order from config
        self.particle_type_order = config.get_ordering('subatomic', 'particle_type') or ['Baryon', 'Meson']

        # Colors from config color scheme
        color_scheme = config.get_color_scheme('subatomic')
        self.baryon_color = self._hex_to_rgb(color_scheme.get('baryon', '#667EEA'))
        self.meson_color = self._hex_to_rgb(color_scheme.get('meson', '#F093FB'))

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        if isinstance(hex_color, tuple):
            return hex_color
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def calculate_layout(self, particles):
        """
        Calculate positions for all particles.

        Args:
            particles: List of particle dictionaries

        Returns:
            Dictionary mapping particle names to position data
        """
        layout_data = {}

        # Separate particles
        baryons = [p for p in particles if p.get('_is_baryon', False)]
        mesons = [p for p in particles if p.get('_is_meson', False)]

        y_offset = self.header_height + 20
        x_start = self.margin_left

        # Calculate columns
        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))

        # Baryon section
        if baryons:
            layout_data['_baryon_header'] = {
                'type': 'header',
                'x': x_start,
                'y': y_offset,
                'text': 'BARYONS',
                'subtitle': '3 quarks bound by strong force',
                'color': self.baryon_color
            }
            y_offset += self.header_height

            # Sort baryons by mass
            baryons_sorted = sorted(baryons, key=lambda p: p.get('Mass_MeVc2', 0))

            for i, particle in enumerate(baryons_sorted):
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
                    'particle': particle
                }

            # Calculate total baryon rows
            baryon_rows = (len(baryons) + cols - 1) // cols
            y_offset += baryon_rows * (self.card_height + self.card_spacing) + self.section_spacing

        # Meson section
        if mesons:
            layout_data['_meson_header'] = {
                'type': 'header',
                'x': x_start,
                'y': y_offset,
                'text': 'MESONS',
                'subtitle': 'quark + antiquark pairs',
                'color': self.meson_color
            }
            y_offset += self.header_height

            # Sort mesons by mass
            mesons_sorted = sorted(mesons, key=lambda p: p.get('Mass_MeVc2', 0))

            for i, particle in enumerate(mesons_sorted):
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
                    'particle': particle
                }

        return layout_data

    def get_content_height(self, particles):
        """Calculate total content height for scrolling"""
        baryons = [p for p in particles if p.get('_is_baryon', False)]
        mesons = [p for p in particles if p.get('_is_meson', False)]

        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))

        height = self.header_height + 20

        if baryons:
            baryon_rows = (len(baryons) + cols - 1) // cols
            height += self.header_height + baryon_rows * (self.card_height + self.card_spacing) + self.section_spacing

        if mesons:
            meson_rows = (len(mesons) + cols - 1) // cols
            height += self.header_height + meson_rows * (self.card_height + self.card_spacing)

        return height + self.margin_left  # Add padding

    def update_dimensions(self, width, height):
        """Update layout dimensions"""
        self.widget_width = width
        self.widget_height = height
