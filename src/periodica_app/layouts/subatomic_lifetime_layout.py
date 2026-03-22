"""
Lifetime Spectrum Layout Renderer for Subatomic Particles
Displays particles on a horizontal logarithmic timeline based on half-life
Groups particles vertically by family (baryons/mesons)

Uses data-driven configuration from layout_config.json
"""

import math

from periodica.data.layout_config_loader import get_subatomic_config, get_layout_config


class SubatomicLifetimeLayout:
    """Layout renderer showing particle lifetime spectrum"""

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

        # Slightly smaller cards for timeline view
        self.card_width = int(card_size.get('width', 140) * 0.85)
        self.card_height = int(card_size.get('height', 180) * 0.78)
        self.card_spacing = spacing.get('card', 15)
        self.header_height = spacing.get('header', 40)
        self.section_spacing = spacing.get('section', 60) + 20

        # Timeline configuration from config
        timeline_config = get_subatomic_config('timeline', default={})
        self.log_min = timeline_config.get('log_min', -24)
        self.log_max = timeline_config.get('log_max', 4)
        self.timeline_margin = margins.get('left', 50) * 2

        # Colors from config
        color_scheme = config.get_color_scheme('subatomic')
        self.stable_color = self._hex_to_rgb(color_scheme.get('stable', '#00B894'))
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
        Calculate positions for particles on lifetime spectrum.

        Args:
            particles: List of particle dictionaries

        Returns:
            Dictionary mapping particle names to position data
        """
        layout_data = {}

        y_offset = 30
        x_start = 50

        # Header
        layout_data['_lifetime_header'] = {
            'type': 'header',
            'x': x_start,
            'y': y_offset,
            'text': 'LIFETIME SPECTRUM',
            'subtitle': 'Logarithmic timeline from shortest to longest lived',
            'color': (76, 175, 80)  # Green
        }
        y_offset += self.header_height + 20

        # Separate particles by type and stability
        stable_particles = [p for p in particles if p.get('Stability') == 'Stable']
        unstable_baryons = [p for p in particles
                          if p.get('_is_baryon', False) and p.get('Stability') != 'Stable']
        unstable_mesons = [p for p in particles
                         if p.get('_is_meson', False) and p.get('Stability') != 'Stable']

        # Calculate timeline area
        timeline_left = self.timeline_margin
        timeline_right = self.widget_width - self.timeline_margin
        timeline_width = timeline_right - timeline_left

        # Store timeline info for axis rendering
        layout_data['_timeline_axis'] = {
            'type': 'timeline_axis',
            'left': timeline_left,
            'right': timeline_right,
            'y': y_offset + 30,
            'log_min': self.log_min,
            'log_max': self.log_max,
            'markers': self._get_time_markers()
        }
        y_offset += 80

        def log_half_life_to_x(half_life_s):
            """Convert half-life to x position on timeline"""
            if half_life_s is None or half_life_s <= 0:
                return timeline_left  # Default to leftmost (shortest)

            log_hl = math.log10(half_life_s)
            # Clamp to range
            log_hl = max(self.log_min, min(self.log_max, log_hl))

            # Map to timeline position (left = short, right = long)
            normalized = (log_hl - self.log_min) / (self.log_max - self.log_min)
            return timeline_left + normalized * timeline_width

        # Stable particles section (rightmost, off the scale)
        if stable_particles:
            layout_data['_stable_header'] = {
                'type': 'subheader',
                'x': x_start,
                'y': y_offset,
                'text': 'STABLE PARTICLES',
                'color': self.stable_color
            }
            y_offset += 35

            # Place stable particles at the far right
            for i, p in enumerate(stable_particles):
                x = timeline_right + 50
                y = y_offset + (i % 2) * (self.card_height + 10)

                layout_data[p['Name']] = {
                    'type': 'particle',
                    'x': x,
                    'y': y,
                    'width': self.card_width,
                    'height': self.card_height,
                    'particle': p,
                    'lifetime_category': 'stable',
                    'is_stable': True
                }

            stable_rows = (len(stable_particles) + 1) // 2
            y_offset += stable_rows * (self.card_height + 10) + self.section_spacing

        # Unstable baryons section
        if unstable_baryons:
            layout_data['_baryon_lifetime_header'] = {
                'type': 'subheader',
                'x': x_start,
                'y': y_offset,
                'text': 'BARYONS (by half-life)',
                'color': self.baryon_color
            }
            y_offset += 35

            # Sort by half-life (shortest first)
            sorted_baryons = sorted(unstable_baryons,
                                   key=lambda p: p.get('HalfLife_s') or 0)

            # Track vertical positions to avoid overlap
            x_positions = {}

            for p in sorted_baryons:
                half_life = p.get('HalfLife_s')
                x = log_half_life_to_x(half_life) - self.card_width / 2

                # Find a y position that doesn't overlap
                x_key = round(x / 50) * 50
                if x_key in x_positions:
                    y = y_offset + x_positions[x_key] * (self.card_height + 10)
                    x_positions[x_key] += 1
                else:
                    y = y_offset
                    x_positions[x_key] = 1

                layout_data[p['Name']] = {
                    'type': 'particle',
                    'x': x,
                    'y': y,
                    'width': self.card_width,
                    'height': self.card_height,
                    'particle': p,
                    'lifetime_category': self._categorize_lifetime(half_life),
                    'log_half_life': math.log10(half_life) if half_life and half_life > 0 else None
                }

            max_rows = max(x_positions.values()) if x_positions else 1
            y_offset += max_rows * (self.card_height + 10) + self.section_spacing

        # Unstable mesons section
        if unstable_mesons:
            layout_data['_meson_lifetime_header'] = {
                'type': 'subheader',
                'x': x_start,
                'y': y_offset,
                'text': 'MESONS (by half-life)',
                'color': self.meson_color
            }
            y_offset += 35

            # Sort by half-life (shortest first)
            sorted_mesons = sorted(unstable_mesons,
                                  key=lambda p: p.get('HalfLife_s') or 0)

            # Track vertical positions to avoid overlap
            x_positions = {}

            for p in sorted_mesons:
                half_life = p.get('HalfLife_s')
                x = log_half_life_to_x(half_life) - self.card_width / 2

                # Find a y position that doesn't overlap
                x_key = round(x / 50) * 50
                if x_key in x_positions:
                    y = y_offset + x_positions[x_key] * (self.card_height + 10)
                    x_positions[x_key] += 1
                else:
                    y = y_offset
                    x_positions[x_key] = 1

                layout_data[p['Name']] = {
                    'type': 'particle',
                    'x': x,
                    'y': y,
                    'width': self.card_width,
                    'height': self.card_height,
                    'particle': p,
                    'lifetime_category': self._categorize_lifetime(half_life),
                    'log_half_life': math.log10(half_life) if half_life and half_life > 0 else None
                }

            max_rows = max(x_positions.values()) if x_positions else 1
            y_offset += max_rows * (self.card_height + 10)

        return layout_data

    def _get_time_markers(self):
        """Get markers for the timeline axis"""
        markers = []
        # Create markers at key orders of magnitude
        for exp in range(self.log_min, self.log_max + 1, 3):
            if exp == 0:
                label = "1 s"
            elif exp == -3:
                label = "1 ms"
            elif exp == -6:
                label = "1 us"
            elif exp == -9:
                label = "1 ns"
            elif exp == -12:
                label = "1 ps"
            elif exp == -15:
                label = "1 fs"
            elif exp == -18:
                label = "1 as"
            elif exp == -21:
                label = "1 zs"
            elif exp == -24:
                label = "1 ys"
            elif exp == 3:
                label = "1000 s"
            else:
                label = f"10^{exp} s"

            markers.append({
                'log_value': exp,
                'label': label
            })

        return markers

    def _categorize_lifetime(self, half_life_s):
        """Categorize particle by lifetime range"""
        if half_life_s is None:
            return 'unknown'

        log_hl = math.log10(half_life_s) if half_life_s > 0 else -30

        if log_hl > 0:
            return 'long_lived'  # > 1 second
        elif log_hl > -9:
            return 'medium'  # nanoseconds to seconds
        elif log_hl > -18:
            return 'short'  # attoseconds to nanoseconds
        else:
            return 'ultra_short'  # < attoseconds

    def get_content_height(self, particles):
        """Calculate total content height"""
        # Estimate based on number of particles
        stable = len([p for p in particles if p.get('Stability') == 'Stable'])
        unstable = len(particles) - stable

        height = self.header_height + 100  # Header and timeline
        height += ((stable + 1) // 2) * (self.card_height + 10) + self.section_spacing
        height += (unstable // 2 + 1) * (self.card_height + 10) * 2  # Baryons and mesons

        return max(height, 600)

    def update_dimensions(self, width, height):
        """Update layout dimensions"""
        self.widget_width = width
        self.widget_height = height
