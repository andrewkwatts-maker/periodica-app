"""
Quark Composition Tree Layout Renderer for Subatomic Particles
Displays particles in a hierarchical tree structure based on quark composition
Root: fundamental quarks
Level 2: simple hadrons (u,d combinations)
Level 3: strange hadrons
Level 4: heavy hadrons (charm, bottom)

Uses data-driven configuration from layout_config.json
"""

import math

from periodica.data.layout_config_loader import get_subatomic_config, get_layout_config


class SubatomicQuarkTreeLayout:
    """Layout renderer showing hierarchical quark composition tree"""

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

        # Slightly smaller cards for tree view
        self.card_width = int(card_size.get('width', 140) * 0.93)
        self.card_height = int(card_size.get('height', 180) * 0.89)
        self.card_spacing = spacing.get('card', 20)
        self.header_height = spacing.get('header', 40)
        self.margin_left = margins.get('left', 50)
        self.margin_right = margins.get('right', 50)

        # Tree-specific spacing from config
        tree_config = get_subatomic_config('tree', default={})
        self.level_spacing = tree_config.get('level_spacing', 220)

        # Colors from config
        color_scheme = config.get_color_scheme('subatomic')
        self.baryon_color = self._hex_to_rgb(color_scheme.get('baryon', '#667EEA'))
        self.meson_color = self._hex_to_rgb(color_scheme.get('meson', '#F093FB'))

        # Tree level colors (can be configured)
        self.level_colors = get_subatomic_config('tree_level_colors', default={
            'light': (255, 100, 100),
            'strange': (100, 255, 100),
            'charm': (255, 200, 100),
            'bottom': (200, 100, 255)
        })

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        if isinstance(hex_color, tuple):
            return hex_color
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def calculate_layout(self, particles):
        """
        Calculate positions for particles in hierarchical tree.

        Tree levels:
        - Level 0: Root (quarks header)
        - Level 1: Simple hadrons (ud combinations only)
        - Level 2: Strange hadrons (contain s quark)
        - Level 3: Heavy hadrons (contain c or b quarks)

        Args:
            particles: List of particle dictionaries

        Returns:
            Dictionary mapping particle names to position data
        """
        layout_data = {}

        y_start = 30
        x_center = self.widget_width / 2

        # Header
        layout_data['_quark_tree_header'] = {
            'type': 'header',
            'x': self.margin_left,
            'y': y_start,
            'text': 'QUARK COMPOSITION TREE',
            'subtitle': 'Hierarchical view from light to heavy quark content',
            'color': (156, 39, 176)  # Purple
        }

        # Categorize particles by quark content complexity
        light_hadrons = []      # Only u, d quarks
        strange_hadrons = []    # Contains s quark
        charm_hadrons = []      # Contains c quark
        bottom_hadrons = []     # Contains b quark

        for p in particles:
            quark_content = p.get('QuarkContent', '').lower()
            composition = p.get('Composition', [])

            # Check for heavy quarks
            has_bottom = 'b' in quark_content or any(
                'bottom' in c.get('Constituent', '').lower() for c in composition)
            has_charm = 'c' in quark_content or any(
                'charm' in c.get('Constituent', '').lower() for c in composition)
            has_strange = 's' in quark_content or any(
                'strange' in c.get('Constituent', '').lower() for c in composition)

            if has_bottom:
                bottom_hadrons.append(p)
            elif has_charm:
                charm_hadrons.append(p)
            elif has_strange:
                strange_hadrons.append(p)
            else:
                light_hadrons.append(p)

        # Track tree connections for rendering
        tree_connections = []

        # Get level color from config
        def get_level_color(level_name):
            if isinstance(self.level_colors, dict):
                color = self.level_colors.get(level_name, (150, 150, 150))
                if isinstance(color, str):
                    return self._hex_to_rgb(color)
                return color
            return (150, 150, 150)

        # Level 1: Light hadrons (u, d only) - at the top after header
        y_level1 = y_start + self.header_height + 60

        layout_data['_light_level_header'] = {
            'type': 'level_header',
            'x': self.margin_left,
            'y': y_level1,
            'text': 'LIGHT HADRONS (u, d quarks)',
            'color': get_level_color('light'),
            'level': 1
        }
        y_level1 += 40

        light_positions = self._layout_level(light_hadrons, y_level1, layout_data, 'light')

        # Level 2: Strange hadrons
        y_level2 = y_level1 + self._get_level_height(light_hadrons) + self.level_spacing

        layout_data['_strange_level_header'] = {
            'type': 'level_header',
            'x': self.margin_left,
            'y': y_level2,
            'text': 'STRANGE HADRONS (contains s quark)',
            'color': get_level_color('strange'),
            'level': 2
        }
        y_level2 += 40

        strange_positions = self._layout_level(strange_hadrons, y_level2, layout_data, 'strange')

        # Add connections from light to strange level
        if light_positions and strange_positions:
            # Connect center of light level to center of strange level
            light_center_x = sum(pos[0] for pos in light_positions) / len(light_positions) if light_positions else x_center
            strange_center_x = sum(pos[0] for pos in strange_positions) / len(strange_positions) if strange_positions else x_center

            tree_connections.append({
                'from_level': 1,
                'to_level': 2,
                'from_y': y_level1 + self.card_height,
                'to_y': y_level2 - 40,
                'label': '+s quark'
            })

        # Level 3: Charm hadrons
        y_level3 = y_level2 + self._get_level_height(strange_hadrons) + self.level_spacing

        layout_data['_charm_level_header'] = {
            'type': 'level_header',
            'x': self.margin_left,
            'y': y_level3,
            'text': 'CHARM HADRONS (contains c quark)',
            'color': get_level_color('charm'),
            'level': 3
        }
        y_level3 += 40

        charm_positions = self._layout_level(charm_hadrons, y_level3, layout_data, 'charm')

        # Add connections from strange to charm level
        if strange_positions or light_positions:
            tree_connections.append({
                'from_level': 2,
                'to_level': 3,
                'from_y': y_level2 + self.card_height if strange_hadrons else y_level1 + self.card_height,
                'to_y': y_level3 - 40,
                'label': '+c quark'
            })

        # Level 4: Bottom hadrons
        y_level4 = y_level3 + self._get_level_height(charm_hadrons) + self.level_spacing

        layout_data['_bottom_level_header'] = {
            'type': 'level_header',
            'x': self.margin_left,
            'y': y_level4,
            'text': 'BOTTOM HADRONS (contains b quark)',
            'color': get_level_color('bottom'),
            'level': 4
        }
        y_level4 += 40

        bottom_positions = self._layout_level(bottom_hadrons, y_level4, layout_data, 'bottom')

        # Add connections to bottom level
        if charm_positions or strange_positions or light_positions:
            tree_connections.append({
                'from_level': 3,
                'to_level': 4,
                'from_y': y_level3 + self.card_height if charm_hadrons else y_level2 + self.card_height,
                'to_y': y_level4 - 40,
                'label': '+b quark'
            })

        # Store tree connections for rendering
        layout_data['_tree_connections'] = {
            'type': 'connections',
            'connections': tree_connections
        }

        return layout_data

    def _layout_level(self, particles, y_offset, layout_data, level_name):
        """
        Layout particles at a specific tree level.

        Args:
            particles: List of particles for this level
            y_offset: Y position for this level
            layout_data: Dictionary to add positions to
            level_name: Name of this level (for categorization)

        Returns:
            List of (x, y) positions for particles at this level
        """
        if not particles:
            return []

        positions = []

        # Separate baryons and mesons within level
        baryons = [p for p in particles if p.get('_is_baryon', False)]
        mesons = [p for p in particles if p.get('_is_meson', False)]

        # Sort each group by mass
        baryons.sort(key=lambda p: p.get('Mass_MeVc2', 0))
        mesons.sort(key=lambda p: p.get('Mass_MeVc2', 0))

        # Layout baryons on left, mesons on right
        x_start = self.margin_left
        total_particles = len(particles)
        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))

        # Position baryons
        current_idx = 0
        for i, p in enumerate(baryons):
            row = current_idx // cols
            col = current_idx % cols
            x = x_start + col * (self.card_width + self.card_spacing)
            y = y_offset + row * (self.card_height + self.card_spacing)

            layout_data[p['Name']] = {
                'type': 'particle',
                'x': x,
                'y': y,
                'width': self.card_width,
                'height': self.card_height,
                'particle': p,
                'tree_level': level_name,
                'particle_type': 'baryon'
            }
            positions.append((x + self.card_width / 2, y))
            current_idx += 1

        # Position mesons (continue from where baryons left off)
        for i, p in enumerate(mesons):
            row = current_idx // cols
            col = current_idx % cols
            x = x_start + col * (self.card_width + self.card_spacing)
            y = y_offset + row * (self.card_height + self.card_spacing)

            layout_data[p['Name']] = {
                'type': 'particle',
                'x': x,
                'y': y,
                'width': self.card_width,
                'height': self.card_height,
                'particle': p,
                'tree_level': level_name,
                'particle_type': 'meson'
            }
            positions.append((x + self.card_width / 2, y))
            current_idx += 1

        return positions

    def _get_level_height(self, particles):
        """Calculate height needed for a level"""
        if not particles:
            return 0

        available_width = self.widget_width - self.margin_left - self.margin_right
        cols = max(1, available_width // (self.card_width + self.card_spacing))
        rows = (len(particles) + cols - 1) // cols

        return rows * (self.card_height + self.card_spacing)

    def get_content_height(self, particles):
        """Calculate total content height for scrolling"""
        # Categorize particles
        light_hadrons = []
        strange_hadrons = []
        charm_hadrons = []
        bottom_hadrons = []

        for p in particles:
            quark_content = p.get('QuarkContent', '').lower()
            composition = p.get('Composition', [])

            has_bottom = 'b' in quark_content or any(
                'bottom' in c.get('Constituent', '').lower() for c in composition)
            has_charm = 'c' in quark_content or any(
                'charm' in c.get('Constituent', '').lower() for c in composition)
            has_strange = 's' in quark_content or any(
                'strange' in c.get('Constituent', '').lower() for c in composition)

            if has_bottom:
                bottom_hadrons.append(p)
            elif has_charm:
                charm_hadrons.append(p)
            elif has_strange:
                strange_hadrons.append(p)
            else:
                light_hadrons.append(p)

        height = self.header_height + 100  # Header

        # Each level
        height += self._get_level_height(light_hadrons) + self.level_spacing + 40
        height += self._get_level_height(strange_hadrons) + self.level_spacing + 40
        height += self._get_level_height(charm_hadrons) + self.level_spacing + 40
        height += self._get_level_height(bottom_hadrons) + self.margin_left

        return max(height, 800)

    def update_dimensions(self, width, height):
        """Update layout dimensions"""
        self.widget_width = width
        self.widget_height = height
