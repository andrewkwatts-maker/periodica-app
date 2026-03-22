"""
SubatomicUnifiedTable - Main visualization widget for subatomic particles
Handles all layout modes and user interactions for the Subatomic tab
"""

import json
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QFont, QPainterPath,
                           QLinearGradient, QRadialGradient, QPolygonF, QGuiApplication)

from periodica.data.subatomic_loader import get_subatomic_loader, SubatomicDataLoader
from periodica.data.layout_config_loader import get_subatomic_config
from periodica.core.subatomic_enums import (SubatomicLayoutMode, ParticleCategory, SubatomicProperty,
                                   QuarkType, PARTICLE_COLORS, get_particle_family_color)


class SubatomicUnifiedTable(QWidget):
    """Unified widget for displaying subatomic particles in various layouts"""

    particle_selected = Signal(dict)  # Emitted when a particle is selected
    particle_hovered = Signal(dict)   # Emitted when a particle is hovered

    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)

        # Load particle data
        self.loader = get_subatomic_loader()
        self.particles = self.loader.get_all_particles()

        # Interaction state
        self.hovered_particle = None
        self.selected_particle = None
        self.setMouseTracking(True)

        # Layout mode
        self.layout_mode = SubatomicLayoutMode.BARYON_MESON

        # Visual property encodings
        self.fill_property = SubatomicProperty.MASS
        self.border_property = SubatomicProperty.CHARGE
        self.size_property = SubatomicProperty.MASS
        self.glow_property = SubatomicProperty.STABILITY
        self.ring_property = SubatomicProperty.BARYON_NUMBER
        self.symbol_text_property = SubatomicProperty.ISOSPIN

        # Filters
        self.show_baryons = True
        self.show_mesons = True
        self.show_stable = True
        self.show_unstable = True
        self.charge_filter = None  # None = show all, or specific charge

        # Zoom and pan
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # Card size
        self.card_width = 140
        self.card_height = 180
        self.card_spacing = 20

        # Layout cache
        self._layout_cache = {}
        self._needs_layout_update = True

    def set_layout_mode(self, mode):
        """Set the layout mode"""
        if isinstance(mode, str):
            mode = SubatomicLayoutMode.from_string(mode)
        self.layout_mode = mode
        self._needs_layout_update = True
        self.update()

    def set_filter(self, show_baryons=True, show_mesons=True, show_stable=True, show_unstable=True, charge=None):
        """Set particle filters"""
        self.show_baryons = show_baryons
        self.show_mesons = show_mesons
        self.show_stable = show_stable
        self.show_unstable = show_unstable
        self.charge_filter = charge
        self._needs_layout_update = True
        self.update()

    def get_filtered_particles(self):
        """Get particles after applying filters"""
        filtered = []
        for p in self.particles:
            # Category filter
            if p.get('_is_baryon') and not self.show_baryons:
                continue
            if p.get('_is_meson') and not self.show_mesons:
                continue

            # Stability filter
            stability = p.get('Stability', 'Unstable')
            is_stable = stability == 'Stable'
            if is_stable and not self.show_stable:
                continue
            if not is_stable and not self.show_unstable:
                continue

            # Charge filter
            if self.charge_filter is not None:
                if p.get('Charge_e', 0) != self.charge_filter:
                    continue

            filtered.append(p)

        return filtered

    def _calculate_layout(self):
        """Calculate positions for all particles based on layout mode"""
        particles = self.get_filtered_particles()
        self._layout_cache = {}

        if self.layout_mode == SubatomicLayoutMode.BARYON_MESON:
            self._calculate_baryon_meson_layout(particles)
        elif self.layout_mode == SubatomicLayoutMode.MASS_ORDER:
            self._calculate_mass_layout(particles)
        elif self.layout_mode == SubatomicLayoutMode.CHARGE_ORDER:
            self._calculate_charge_layout(particles)
        elif self.layout_mode == SubatomicLayoutMode.DECAY_CHAIN:
            self._calculate_decay_layout(particles)
        elif self.layout_mode == SubatomicLayoutMode.QUARK_CONTENT:
            self._calculate_quark_content_layout(particles)
        elif self.layout_mode == SubatomicLayoutMode.EIGHTFOLD_WAY:
            self._calculate_eightfold_layout(particles)
        elif self.layout_mode == SubatomicLayoutMode.LIFETIME_SPECTRUM:
            self._calculate_lifetime_layout(particles)
        elif self.layout_mode == SubatomicLayoutMode.QUARK_TREE:
            self._calculate_quark_tree_layout(particles)
        elif self.layout_mode == SubatomicLayoutMode.DISCOVERY_TIMELINE:
            self._calculate_discovery_layout(particles)

        self._needs_layout_update = False

    def _calculate_baryon_meson_layout(self, particles):
        """Layout with baryons and mesons in separate groups"""
        baryons = [p for p in particles if p.get('_is_baryon')]
        mesons = [p for p in particles if p.get('_is_meson')]

        y_offset = 80
        x_start = 50

        # Baryon section
        if baryons:
            self._layout_cache['baryon_header'] = {'x': x_start, 'y': y_offset - 40, 'text': 'BARYONS (3 quarks)'}
            cols = max(1, (self.width() - 100) // (self.card_width + self.card_spacing))
            for i, p in enumerate(baryons):
                row = i // cols
                col = i % cols
                x = x_start + col * (self.card_width + self.card_spacing)
                y = y_offset + row * (self.card_height + self.card_spacing)
                self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}

            # Calculate end of baryon section
            baryon_rows = (len(baryons) + cols - 1) // cols
            y_offset += baryon_rows * (self.card_height + self.card_spacing) + 60

        # Meson section
        if mesons:
            self._layout_cache['meson_header'] = {'x': x_start, 'y': y_offset - 40, 'text': 'MESONS (quark + antiquark)'}
            cols = max(1, (self.width() - 100) // (self.card_width + self.card_spacing))
            for i, p in enumerate(mesons):
                row = i // cols
                col = i % cols
                x = x_start + col * (self.card_width + self.card_spacing)
                y = y_offset + row * (self.card_height + self.card_spacing)
                self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}

    def _calculate_mass_layout(self, particles):
        """Layout ordered by mass"""
        sorted_particles = sorted(particles, key=lambda p: p.get('Mass_MeVc2', 0))

        y_offset = 80
        x_start = 50
        cols = max(1, (self.width() - 100) // (self.card_width + self.card_spacing))

        self._layout_cache['header'] = {'x': x_start, 'y': y_offset - 40, 'text': 'Particles by Mass (MeV/c^2)'}

        for i, p in enumerate(sorted_particles):
            row = i // cols
            col = i % cols
            x = x_start + col * (self.card_width + self.card_spacing)
            y = y_offset + row * (self.card_height + self.card_spacing)
            self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}

    def _calculate_charge_layout(self, particles):
        """Layout grouped by charge"""
        charge_groups = {}
        for p in particles:
            charge = p.get('Charge_e', 0)
            if charge not in charge_groups:
                charge_groups[charge] = []
            charge_groups[charge].append(p)

        y_offset = 80
        x_start = 50

        for charge in sorted(charge_groups.keys(), reverse=True):
            group = charge_groups[charge]
            charge_str = f"+{charge}" if charge > 0 else str(charge)
            self._layout_cache[f'charge_header_{charge}'] = {
                'x': x_start, 'y': y_offset - 40,
                'text': f'Charge: {charge_str} e'
            }

            cols = max(1, (self.width() - 100) // (self.card_width + self.card_spacing))
            for i, p in enumerate(group):
                row = i // cols
                col = i % cols
                x = x_start + col * (self.card_width + self.card_spacing)
                y = y_offset + row * (self.card_height + self.card_spacing)
                self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}

            rows = (len(group) + cols - 1) // cols
            y_offset += rows * (self.card_height + self.card_spacing) + 60

    def _calculate_decay_layout(self, particles):
        """Layout showing decay relationships"""
        # Sort by stability (most stable first)
        sorted_particles = sorted(particles, key=lambda p: -p.get('_stability_factor', 0))

        y_offset = 80
        x_start = 50

        self._layout_cache['header'] = {'x': x_start, 'y': y_offset - 40, 'text': 'Particles by Stability (Decay Chains)'}

        cols = max(1, (self.width() - 100) // (self.card_width + self.card_spacing))
        for i, p in enumerate(sorted_particles):
            row = i // cols
            col = i % cols
            x = x_start + col * (self.card_width + self.card_spacing)
            y = y_offset + row * (self.card_height + self.card_spacing)
            self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}

    def _calculate_quark_content_layout(self, particles):
        """Layout grouped by quark content"""
        quark_groups = {
            'uuu/uud/udd/ddd': [],  # Delta baryons
            'uds': [],               # Lambda, Sigma0
            'uus/dds': [],          # Sigma+/-
            'uss/dss': [],          # Xi
            'sss': [],               # Omega
            'light_mesons': [],      # Pions, Kaons
            'heavy_mesons': [],      # J/psi, Upsilon
        }

        for p in particles:
            quark_content = p.get('QuarkContent', '').lower()
            if 'uuu' in quark_content or 'ddd' in quark_content:
                quark_groups['uuu/uud/udd/ddd'].append(p)
            elif ('uud' in quark_content or 'udd' in quark_content) and p.get('_is_baryon'):
                quark_groups['uuu/uud/udd/ddd'].append(p)
            elif 'sss' in quark_content:
                quark_groups['sss'].append(p)
            elif 'uss' in quark_content or 'dss' in quark_content:
                quark_groups['uss/dss'].append(p)
            elif 'uus' in quark_content or 'dds' in quark_content:
                quark_groups['uus/dds'].append(p)
            elif 'uds' in quark_content and p.get('_is_baryon'):
                quark_groups['uds'].append(p)
            elif p.get('_is_meson'):
                mass = p.get('Mass_MeVc2', 0)
                if mass > 1000:
                    quark_groups['heavy_mesons'].append(p)
                else:
                    quark_groups['light_mesons'].append(p)

        y_offset = 80
        x_start = 50

        group_names = {
            'uuu/uud/udd/ddd': 'Light Baryons (u, d quarks)',
            'uds': 'Lambda/Sigma (uds)',
            'uus/dds': 'Sigma (uus/dds)',
            'uss/dss': 'Xi Cascade (uss/dss)',
            'sss': 'Omega (sss)',
            'light_mesons': 'Light Mesons',
            'heavy_mesons': 'Heavy Mesons (c, b quarks)',
        }

        for group_key, particles_list in quark_groups.items():
            if not particles_list:
                continue

            self._layout_cache[f'quark_header_{group_key}'] = {
                'x': x_start, 'y': y_offset - 40,
                'text': group_names.get(group_key, group_key)
            }

            cols = max(1, (self.width() - 100) // (self.card_width + self.card_spacing))
            for i, p in enumerate(particles_list):
                row = i // cols
                col = i % cols
                x = x_start + col * (self.card_width + self.card_spacing)
                y = y_offset + row * (self.card_height + self.card_spacing)
                self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}

            rows = (len(particles_list) + cols - 1) // cols
            y_offset += rows * (self.card_height + self.card_spacing) + 60

    def _calculate_eightfold_layout(self, particles):
        """Layout in Eightfold Way diagram (I3 vs Hypercharge Y)"""
        y_offset = 80
        x_start = 50

        self._layout_cache['header'] = {'x': x_start, 'y': y_offset - 40, 'text': 'Eightfold Way (I3 vs Hypercharge)'}

        if not particles:
            return

        # Calculate I3 and Y for positioning
        plot_left = 100
        plot_right = self.width() - 100
        plot_top = y_offset + 20
        plot_bottom = plot_top + 500
        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top

        # Get ranges
        i3_values = [p.get('Isospin_I3', 0) for p in particles]
        y_values = [p.get('Strangeness', 0) + p.get('BaryonNumber_B', 0) for p in particles]

        i3_min, i3_max = min(i3_values) - 0.5, max(i3_values) + 0.5
        y_min, y_max = min(y_values) - 0.5, max(y_values) + 0.5
        i3_range = i3_max - i3_min if i3_max != i3_min else 3
        y_range = y_max - y_min if y_max != y_min else 4

        position_map = {}
        for p in particles:
            i3 = p.get('Isospin_I3', 0)
            hypercharge = p.get('Strangeness', 0) + p.get('BaryonNumber_B', 0)

            # Map to pixel coordinates
            x_norm = (i3 - i3_min) / i3_range
            y_norm = (hypercharge - y_min) / y_range

            px = plot_left + x_norm * plot_width - self.card_width / 2
            py = plot_bottom - y_norm * plot_height - self.card_height / 2

            # Handle overlap
            key = (round(i3 * 2), round(hypercharge * 2))
            if key in position_map:
                px += position_map[key] * 25
                position_map[key] += 1
            else:
                position_map[key] = 1

            self._layout_cache[p['Name']] = {'x': px, 'y': py, 'particle': p}

    def _calculate_lifetime_layout(self, particles):
        """Layout on logarithmic lifetime spectrum"""
        y_offset = 80
        x_start = 50

        self._layout_cache['header'] = {'x': x_start, 'y': y_offset - 40, 'text': 'Lifetime Spectrum (Log Scale)'}

        # Separate by stability
        stable = [p for p in particles if p.get('Stability') == 'Stable']
        unstable_baryons = [p for p in particles if p.get('_is_baryon') and p.get('Stability') != 'Stable']
        unstable_mesons = [p for p in particles if p.get('_is_meson') and p.get('Stability') != 'Stable']

        timeline_left = 100
        timeline_right = self.width() - 200
        timeline_width = timeline_right - timeline_left
        log_min, log_max = -24, 4

        def half_life_to_x(hl):
            if not hl or hl <= 0:
                return timeline_left
            log_hl = max(log_min, min(log_max, math.log10(hl)))
            return timeline_left + ((log_hl - log_min) / (log_max - log_min)) * timeline_width

        # Stable particles on far right
        if stable:
            self._layout_cache['stable_header'] = {'x': x_start, 'y': y_offset, 'text': 'Stable'}
            for i, p in enumerate(stable):
                self._layout_cache[p['Name']] = {
                    'x': timeline_right + 50,
                    'y': y_offset + 40 + i * (self.card_height + 10),
                    'particle': p
                }
            y_offset += 40 + len(stable) * (self.card_height + 10) + 60

        # Unstable baryons
        if unstable_baryons:
            self._layout_cache['baryon_lifetime_header'] = {'x': x_start, 'y': y_offset, 'text': 'Baryons (by half-life)'}
            y_offset += 40
            x_positions = {}
            for p in sorted(unstable_baryons, key=lambda p: p.get('HalfLife_s') or 0):
                x = half_life_to_x(p.get('HalfLife_s')) - self.card_width / 2
                x_key = round(x / 50) * 50
                if x_key in x_positions:
                    y = y_offset + x_positions[x_key] * (self.card_height + 10)
                    x_positions[x_key] += 1
                else:
                    y = y_offset
                    x_positions[x_key] = 1
                self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}
            max_rows = max(x_positions.values()) if x_positions else 1
            y_offset += max_rows * (self.card_height + 10) + 60

        # Unstable mesons
        if unstable_mesons:
            self._layout_cache['meson_lifetime_header'] = {'x': x_start, 'y': y_offset, 'text': 'Mesons (by half-life)'}
            y_offset += 40
            x_positions = {}
            for p in sorted(unstable_mesons, key=lambda p: p.get('HalfLife_s') or 0):
                x = half_life_to_x(p.get('HalfLife_s')) - self.card_width / 2
                x_key = round(x / 50) * 50
                if x_key in x_positions:
                    y = y_offset + x_positions[x_key] * (self.card_height + 10)
                    x_positions[x_key] += 1
                else:
                    y = y_offset
                    x_positions[x_key] = 1
                self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}

    def _calculate_quark_tree_layout(self, particles):
        """Layout as hierarchical quark composition tree"""
        y_offset = 80
        x_start = 50

        self._layout_cache['header'] = {'x': x_start, 'y': y_offset - 40, 'text': 'Quark Composition Tree'}

        # Categorize by quark content
        light_hadrons = []
        strange_hadrons = []
        charm_hadrons = []
        bottom_hadrons = []

        for p in particles:
            quark_content = p.get('QuarkContent', '').lower()
            composition = p.get('Composition', [])
            has_bottom = 'b' in quark_content or any('bottom' in c.get('Constituent', '').lower() for c in composition)
            has_charm = 'c' in quark_content or any('charm' in c.get('Constituent', '').lower() for c in composition)
            has_strange = 's' in quark_content or any('strange' in c.get('Constituent', '').lower() for c in composition)

            if has_bottom:
                bottom_hadrons.append(p)
            elif has_charm:
                charm_hadrons.append(p)
            elif has_strange:
                strange_hadrons.append(p)
            else:
                light_hadrons.append(p)

        cols = max(1, (self.width() - 100) // (self.card_width + self.card_spacing))
        level_spacing = 220

        # Level 1: Light hadrons
        if light_hadrons:
            self._layout_cache['light_header'] = {'x': x_start, 'y': y_offset, 'text': 'Light Hadrons (u, d)'}
            y_offset += 40
            for i, p in enumerate(light_hadrons):
                row, col = i // cols, i % cols
                self._layout_cache[p['Name']] = {
                    'x': x_start + col * (self.card_width + self.card_spacing),
                    'y': y_offset + row * (self.card_height + self.card_spacing),
                    'particle': p
                }
            rows = (len(light_hadrons) + cols - 1) // cols
            y_offset += rows * (self.card_height + self.card_spacing) + level_spacing - 160

        # Level 2: Strange hadrons
        if strange_hadrons:
            self._layout_cache['strange_header'] = {'x': x_start, 'y': y_offset, 'text': 'Strange Hadrons (+s)'}
            y_offset += 40
            for i, p in enumerate(strange_hadrons):
                row, col = i // cols, i % cols
                self._layout_cache[p['Name']] = {
                    'x': x_start + col * (self.card_width + self.card_spacing),
                    'y': y_offset + row * (self.card_height + self.card_spacing),
                    'particle': p
                }
            rows = (len(strange_hadrons) + cols - 1) // cols
            y_offset += rows * (self.card_height + self.card_spacing) + level_spacing - 160

        # Level 3: Charm hadrons
        if charm_hadrons:
            self._layout_cache['charm_header'] = {'x': x_start, 'y': y_offset, 'text': 'Charm Hadrons (+c)'}
            y_offset += 40
            for i, p in enumerate(charm_hadrons):
                row, col = i // cols, i % cols
                self._layout_cache[p['Name']] = {
                    'x': x_start + col * (self.card_width + self.card_spacing),
                    'y': y_offset + row * (self.card_height + self.card_spacing),
                    'particle': p
                }
            rows = (len(charm_hadrons) + cols - 1) // cols
            y_offset += rows * (self.card_height + self.card_spacing) + level_spacing - 160

        # Level 4: Bottom hadrons
        if bottom_hadrons:
            self._layout_cache['bottom_header'] = {'x': x_start, 'y': y_offset, 'text': 'Bottom Hadrons (+b)'}
            y_offset += 40
            for i, p in enumerate(bottom_hadrons):
                row, col = i // cols, i % cols
                self._layout_cache[p['Name']] = {
                    'x': x_start + col * (self.card_width + self.card_spacing),
                    'y': y_offset + row * (self.card_height + self.card_spacing),
                    'particle': p
                }

    def _calculate_discovery_layout(self, particles):
        """Layout on discovery timeline with mass distribution"""
        y_offset = 80
        x_start = 50

        self._layout_cache['header'] = {'x': x_start, 'y': y_offset - 40, 'text': 'Discovery Timeline'}

        # Separate particles with and without discovery dates
        with_date = []
        without_date = []
        for p in particles:
            discovery = p.get('Discovery', {})
            year = discovery.get('Year') if isinstance(discovery, dict) else None
            if year:
                with_date.append((p, year))
            else:
                without_date.append(p)

        with_date.sort(key=lambda x: x[1])

        # Timeline area
        timeline_left = 100
        timeline_right = self.width() - 100
        timeline_width = timeline_right - timeline_left

        year_min = min(p[1] for p in with_date) - 5 if with_date else 1895
        year_max = max(p[1] for p in with_date) + 5 if with_date else 2020
        year_range = year_max - year_min

        # Mass range for Y positioning
        masses = [p.get('Mass_MeVc2', 100) for p, _ in with_date]
        if masses:
            mass_values = [m for m in masses if m > 0]
            log_mass_min = math.log10(min(mass_values)) if mass_values else 0
            log_mass_max = math.log10(max(mass_values)) if mass_values else 4
        else:
            log_mass_min, log_mass_max = 0, 4
        log_mass_range = log_mass_max - log_mass_min if log_mass_max != log_mass_min else 4

        plot_top = y_offset + 60
        plot_height = 400

        position_grid = {}
        for p, year in with_date:
            mass = p.get('Mass_MeVc2', 100)

            x_norm = (year - year_min) / year_range if year_range else 0.5
            log_mass = math.log10(mass) if mass > 0 else log_mass_min
            y_norm = (log_mass - log_mass_min) / log_mass_range

            x = timeline_left + x_norm * timeline_width - self.card_width / 2
            y = plot_top + plot_height - y_norm * (plot_height - 100) - self.card_height / 2

            # Handle overlap
            grid_key = (round(x / 80), round(y / 100))
            if grid_key in position_grid:
                x += (position_grid[grid_key] % 3) * 30
                y += (position_grid[grid_key] // 3) * 20
                position_grid[grid_key] += 1
            else:
                position_grid[grid_key] = 1

            self._layout_cache[p['Name']] = {'x': x, 'y': y, 'particle': p}

        # Particles without dates
        if without_date:
            unknown_y = plot_top + plot_height + 80
            self._layout_cache['unknown_header'] = {'x': x_start, 'y': unknown_y, 'text': 'Discovery Date Unknown'}
            unknown_y += 40
            cols = max(1, (self.width() - 100) // (self.card_width + self.card_spacing))
            for i, p in enumerate(without_date):
                row, col = i // cols, i % cols
                self._layout_cache[p['Name']] = {
                    'x': x_start + col * (self.card_width + self.card_spacing),
                    'y': unknown_y + row * (self.card_height + self.card_spacing),
                    'particle': p
                }

    def paintEvent(self, event):
        """Paint the widget"""
        if self._needs_layout_update:
            self._calculate_layout()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Apply zoom and pan transform
        painter.translate(self.pan_x, self.pan_y)
        painter.scale(self.zoom_level, self.zoom_level)

        # Draw background
        painter.fillRect(self.rect(), QColor(20, 20, 35))

        # Draw section headers
        for key, data in self._layout_cache.items():
            if 'text' in data:
                self._draw_section_header(painter, data['x'], data['y'], data['text'])

        # Draw particle cards
        for key, data in self._layout_cache.items():
            if 'particle' in data:
                is_hovered = self.hovered_particle == data['particle']
                is_selected = self.selected_particle == data['particle']
                self._draw_particle_card(painter, data['x'], data['y'],
                                        data['particle'], is_hovered, is_selected)

        # Draw decay arrows if in decay mode
        if self.layout_mode == SubatomicLayoutMode.DECAY_CHAIN:
            self._draw_decay_arrows(painter)

        painter.end()

    def _draw_section_header(self, painter, x, y, text):
        """Draw a section header"""
        painter.setPen(QPen(QColor(79, 195, 247), 1))
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(int(x), int(y), text)

        # Draw underline
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        painter.drawLine(int(x), int(y + 5), int(x + text_width), int(y + 5))

    def _draw_particle_card(self, painter, x, y, particle, is_hovered, is_selected):
        """Draw a single particle card"""
        # Get category color
        category = particle.get('_category', 'baryon')
        base_color = PARTICLE_COLORS.get(category, (102, 126, 234))

        # Card background
        if is_selected:
            bg_color = QColor(base_color[0], base_color[1], base_color[2], 200)
            border_color = QColor(255, 255, 255)
            border_width = 3
        elif is_hovered:
            bg_color = QColor(base_color[0], base_color[1], base_color[2], 150)
            border_color = QColor(base_color[0], base_color[1], base_color[2])
            border_width = 2
        else:
            bg_color = QColor(40, 40, 60, 200)
            border_color = QColor(base_color[0], base_color[1], base_color[2], 150)
            border_width = 2

        # Draw glow for selected/hovered
        if is_selected or is_hovered:
            glow_color = QColor(base_color[0], base_color[1], base_color[2], 100)
            glow_rect = QRectF(x - 5, y - 5, self.card_width + 10, self.card_height + 10)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(glow_rect, 15, 15)

        # Draw card
        card_rect = QRectF(x, y, self.card_width, self.card_height)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(card_rect, 10, 10)

        # Draw particle name
        painter.setPen(QPen(QColor(79, 195, 247)))
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        name = particle.get('Name', 'Unknown')
        painter.drawText(QRectF(x + 5, y + 5, self.card_width - 10, 20),
                        Qt.AlignmentFlag.AlignCenter, name)

        # Draw symbol
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont("Arial", 20, QFont.Weight.Bold)
        painter.setFont(font)
        symbol = particle.get('Symbol', name)
        painter.drawText(QRectF(x + 5, y + 25, self.card_width - 10, 35),
                        Qt.AlignmentFlag.AlignCenter, symbol)

        # Draw quark composition visualization
        self._draw_quark_composition(painter, x + 10, y + 65, particle)

        # Draw properties
        painter.setPen(QPen(QColor(200, 200, 200)))
        font = QFont("Arial", 8)
        painter.setFont(font)

        # Charge
        charge = particle.get('Charge_e', 0)
        charge_str = f"+{charge}" if charge > 0 else str(charge)
        painter.drawText(int(x + 5), int(y + 115), f"Charge: {charge_str} e")

        # Mass
        mass = particle.get('Mass_MeVc2', 0)
        if mass >= 1000:
            mass_str = f"{mass/1000:.2f} GeV"
        else:
            mass_str = f"{mass:.1f} MeV"
        painter.drawText(int(x + 5), int(y + 130), f"Mass: {mass_str}")

        # Spin
        spin = particle.get('Spin_hbar', 0)
        painter.drawText(int(x + 5), int(y + 145), f"Spin: {spin}")

        # Stability indicator
        stability = particle.get('Stability', 'Unstable')
        if stability == 'Stable':
            stability_color = QColor(100, 255, 100)
        else:
            half_life = particle.get('HalfLife_s')
            if half_life and half_life > 1e-10:
                stability_color = QColor(255, 200, 100)
            else:
                stability_color = QColor(255, 100, 100)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(stability_color))
        painter.drawEllipse(int(x + self.card_width - 15), int(y + self.card_height - 15), 10, 10)

        # Draw category tag
        painter.setPen(QPen(QColor(base_color[0], base_color[1], base_color[2])))
        font = QFont("Arial", 7)
        painter.setFont(font)
        category_text = 'Baryon' if particle.get('_is_baryon') else 'Meson' if particle.get('_is_meson') else 'Other'
        painter.drawText(int(x + 5), int(y + self.card_height - 8), category_text)

    def _draw_quark_composition(self, painter, x, y, particle):
        """Draw visual representation of quark composition using configuration"""
        quarks = particle.get('_parsed_quarks', [])
        if not quarks:
            # Fallback: try to parse from Composition field in particle JSON
            composition = particle.get('Composition', [])
            if composition:
                quarks = self._parse_quarks_from_composition(composition)
            if not quarks:
                return

        # Get configuration values from layout_config.json
        quark_size = get_subatomic_config('card_quark_mini', 'quark_size', default=18)
        spacing = get_subatomic_config('card_quark_mini', 'quark_spacing', default=22)
        border_width = get_subatomic_config('card_quark_mini', 'border_width', default=1)
        label_font_size = get_subatomic_config('card_quark_mini', 'label_font_size', default=9)

        # Scale quark size for many quarks to fit in card
        num_quarks = len(quarks)
        if num_quarks > 3:
            scale_factor = max(0.6, 3 / num_quarks)
            quark_size = int(quark_size * scale_factor)
            spacing = int(spacing * scale_factor)

        total_width = num_quarks * spacing

        # Center the quarks within the card
        start_x = x + (self.card_width - 20 - total_width) / 2

        for i, quark in enumerate(quarks):
            qx = start_x + i * spacing
            qy = y

            # Get quark color from type
            quark_type = quark.get('type', 'u')
            is_anti = quark.get('is_anti', False)

            if is_anti:
                quark_type_full = f"{quark_type}-bar"
            else:
                quark_type_full = quark_type

            color_tuple = QuarkType.get_color(QuarkType.from_string(quark_type_full))
            color = QColor(color_tuple[0], color_tuple[1], color_tuple[2])

            # Draw quark circle with configurable border
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(255, 255, 255), border_width))
            painter.drawEllipse(int(qx), int(qy), quark_size, quark_size)

            # Draw quark label with configurable font size
            painter.setPen(QPen(QColor(0, 0, 0)))
            font = QFont("Arial", label_font_size, QFont.Weight.Bold)
            painter.setFont(font)
            label = quark_type.upper()
            if is_anti:
                label = label + '\u0305'  # Combining overline
            painter.drawText(QRectF(qx, qy, quark_size, quark_size),
                           Qt.AlignmentFlag.AlignCenter, label)

    def _parse_quarks_from_composition(self, composition):
        """Parse quark list from particle's Composition field in JSON data"""
        quarks = []
        for comp in composition:
            constituent = comp.get('Constituent', '')
            count = comp.get('Count', 1)
            symbol = comp.get('Symbol', '')
            is_anti = comp.get('IsAnti', False) or 'Anti' in constituent

            # Determine quark type from symbol or constituent name
            quark_type = symbol.replace('-bar', '').lower() if symbol else ''
            if not quark_type:
                if 'up' in constituent.lower():
                    quark_type = 'u'
                elif 'down' in constituent.lower():
                    quark_type = 'd'
                elif 'strange' in constituent.lower():
                    quark_type = 's'
                elif 'charm' in constituent.lower():
                    quark_type = 'c'
                elif 'bottom' in constituent.lower():
                    quark_type = 'b'
                elif 'top' in constituent.lower():
                    quark_type = 't'

            for _ in range(count):
                quarks.append({
                    'type': quark_type,
                    'is_anti': is_anti
                })
        return quarks

    def _draw_decay_arrows(self, painter):
        """Draw arrows showing decay relationships"""
        painter.setPen(QPen(QColor(150, 150, 150, 100), 1, Qt.PenStyle.DashLine))

        for key, data in self._layout_cache.items():
            if 'particle' not in data:
                continue

            particle = data['particle']
            decay_products = particle.get('DecayProducts', [])

            for product in decay_products:
                if product in self._layout_cache:
                    target_data = self._layout_cache[product]
                    if 'particle' in target_data:
                        # Draw arrow from this particle to decay product
                        x1 = data['x'] + self.card_width / 2
                        y1 = data['y'] + self.card_height
                        x2 = target_data['x'] + self.card_width / 2
                        y2 = target_data['y']

                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = True
            self.pan_start_x = event.position().x()
            self.pan_start_y = event.position().y()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            # Check for Ctrl+left click for panning
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.is_panning = True
                self.pan_start_x = event.position().x()
                self.pan_start_y = event.position().y()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                particle = self._get_particle_at_position(event.position().x(), event.position().y())
                if particle:
                    self.selected_particle = particle
                    self.particle_selected.emit(particle)
                    # Copy particle data to clipboard
                    clipboard_text = json.dumps(self.selected_particle, indent=2, default=str)
                    QGuiApplication.clipboard().setText(clipboard_text)
                    self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.LeftButton:
            if self.is_panning:
                self.is_panning = False
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event):
        """Handle mouse move"""
        if self.is_panning:
            dx = event.position().x() - self.pan_start_x
            dy = event.position().y() - self.pan_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start_x = event.position().x()
            self.pan_start_y = event.position().y()
            self.update()
        else:
            particle = self._get_particle_at_position(event.position().x(), event.position().y())
            if particle != self.hovered_particle:
                self.hovered_particle = particle
                if particle:
                    self.particle_hovered.emit(particle)
                self.update()

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_level = min(3.0, self.zoom_level * 1.1)
        else:
            self.zoom_level = max(0.3, self.zoom_level / 1.1)
        self.update()

    def _get_particle_at_position(self, screen_x, screen_y):
        """Get particle at screen position"""
        # Convert screen coordinates to widget coordinates
        x = (screen_x - self.pan_x) / self.zoom_level
        y = (screen_y - self.pan_y) / self.zoom_level

        for key, data in self._layout_cache.items():
            if 'particle' not in data:
                continue

            card_x = data['x']
            card_y = data['y']

            if (card_x <= x <= card_x + self.card_width and
                card_y <= y <= card_y + self.card_height):
                return data['particle']

        return None

    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        self._needs_layout_update = True
        self.update()

    def reset_view(self):
        """Reset zoom and pan to default"""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update()

    def set_zoom(self, zoom_level):
        """Set zoom level from external control (e.g., slider)

        Args:
            zoom_level: Zoom factor (0.2 to 5.0, where 1.0 is default)
        """
        self.zoom_level = max(0.2, min(5.0, zoom_level))
        self.update()

    def set_gradient_colors(self, property_key, start_color, end_color):
        """Set custom gradient colors for a visual property encoding.

        Args:
            property_key: Visual encoding key (e.g., 'fill_color', 'border_color')
            start_color: Starting color (QColor or hex string)
            end_color: Ending color (QColor or hex string)
        """
        # Store custom gradient colors for use in rendering
        if not hasattr(self, 'custom_gradients'):
            self.custom_gradients = {}
        self.custom_gradients[property_key] = {
            'start': start_color if isinstance(start_color, str) else start_color.name(),
            'end': end_color if isinstance(end_color, str) else end_color.name()
        }
        self.update()

    def set_fade_value(self, property_key, fade_value):
        """Set the fade amount for a visual property encoding.

        Args:
            property_key: Visual encoding key (e.g., 'fill_color', 'border_color')
            fade_value: Fade amount from 0.0 (no fade) to 1.0 (fully transparent)
        """
        # Store fade values for use in rendering
        if not hasattr(self, 'fade_values'):
            self.fade_values = {}
        self.fade_values[property_key] = max(0.0, min(1.0, fade_value))
        self.update()

    def reload_data(self):
        """Reload particle data from files and refresh the display"""
        self.particles = self.loader.get_all_particles()
        self._needs_layout_update = True
        self.update()
