"""
Discovery Timeline Layout Renderer for Subatomic Particles
Displays particles arranged chronologically by discovery year
X-axis: Discovery year
Y-axis: Mass (showing progression of accessible energies)

Uses data-driven configuration from layout_config.json
"""

import math

from periodica.data.layout_config_loader import get_subatomic_config, get_layout_config


class SubatomicDiscoveryLayout:
    """Layout renderer showing particle discovery timeline"""

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

        # Smaller cards for timeline plot
        self.card_width = int(card_size.get('width', 140) * 0.85)
        self.card_height = int(card_size.get('height', 180) * 0.83)
        self.card_spacing = spacing.get('card', 15)
        self.header_height = spacing.get('header', 40)
        self.timeline_height = 60
        self.margin_left = margins.get('left', 50)
        self.margin_right = margins.get('right', 50)

        # Discovery timeline configuration from config
        discovery_config = get_subatomic_config('discovery', default={})
        self.year_min = discovery_config.get('year_min', 1895)
        self.year_max = discovery_config.get('year_max', 2020)
        self.timeline_margin = margins.get('left', 50) * 2

        # Era boundaries from config
        self.era_boundaries = get_subatomic_config('era_boundaries', default={
            'classical': 1932,
            'nuclear': 1947,
            'strange': 1964,
            'quark_model': 1995
        })

    def calculate_layout(self, particles):
        """
        Calculate positions for particles on discovery timeline.

        Args:
            particles: List of particle dictionaries

        Returns:
            Dictionary mapping particle names to position data
        """
        layout_data = {}

        y_start = 30
        x_start = self.margin_left

        # Header
        layout_data['_discovery_header'] = {
            'type': 'header',
            'x': x_start,
            'y': y_start,
            'text': 'DISCOVERY TIMELINE',
            'subtitle': 'Chronological particle discoveries with mass distribution',
            'color': (255, 152, 0)  # Orange
        }

        # Separate particles with and without discovery dates
        particles_with_date = []
        particles_without_date = []

        for p in particles:
            discovery = p.get('Discovery', {})
            year = discovery.get('Year') if isinstance(discovery, dict) else None

            if year:
                particles_with_date.append((p, year))
            else:
                particles_without_date.append(p)

        # Sort by year
        particles_with_date.sort(key=lambda x: x[1])

        # Calculate timeline area
        timeline_left = self.timeline_margin
        timeline_right = self.widget_width - self.timeline_margin
        timeline_width = timeline_right - timeline_left

        timeline_y = y_start + self.header_height + 40

        # Get actual year range from data
        if particles_with_date:
            actual_min_year = min(p[1] for p in particles_with_date)
            actual_max_year = max(p[1] for p in particles_with_date)
            # Add some padding
            year_min = max(1890, actual_min_year - 5)
            year_max = min(2025, actual_max_year + 5)
        else:
            year_min = self.year_min
            year_max = self.year_max

        # Store timeline info for axis rendering
        layout_data['_discovery_timeline'] = {
            'type': 'timeline_axis',
            'left': timeline_left,
            'right': timeline_right,
            'y': timeline_y,
            'year_min': year_min,
            'year_max': year_max,
            'markers': self._get_era_markers()
        }

        # Position particles on timeline
        plot_top = timeline_y + self.timeline_height + 20
        plot_height = 400  # Space for mass distribution

        def year_to_x(year):
            """Convert year to x position"""
            if year < year_min:
                year = year_min
            if year > year_max:
                year = year_max

            normalized = (year - year_min) / (year_max - year_min)
            return timeline_left + normalized * timeline_width

        # Get mass range for Y positioning
        masses = [p.get('Mass_MeVc2', 0) for p, _ in particles_with_date]
        if masses:
            mass_min = min(m for m in masses if m > 0) if any(m > 0 for m in masses) else 1
            mass_max = max(masses)
            # Use log scale for mass
            log_mass_min = math.log10(mass_min) if mass_min > 0 else 0
            log_mass_max = math.log10(mass_max) if mass_max > 0 else 4
        else:
            log_mass_min, log_mass_max = 0, 4

        def mass_to_y(mass):
            """Convert mass to y position (log scale)"""
            if mass <= 0:
                return plot_top + plot_height - 50

            log_mass = math.log10(mass)
            if log_mass_max == log_mass_min:
                normalized = 0.5
            else:
                normalized = (log_mass - log_mass_min) / (log_mass_max - log_mass_min)

            # Invert: higher mass at top
            return plot_top + plot_height - (normalized * (plot_height - 100))

        # Track positions to handle overlap
        position_grid = {}

        # Place particles with discovery dates
        for p, year in particles_with_date:
            mass = p.get('Mass_MeVc2', 100)

            x = year_to_x(year) - self.card_width / 2
            y = mass_to_y(mass) - self.card_height / 2

            # Handle overlapping particles
            grid_key = (round(x / 80), round(y / 100))
            if grid_key in position_grid:
                offset = position_grid[grid_key] * 30
                x += offset % 60
                y += (offset // 2) * 20
                position_grid[grid_key] += 1
            else:
                position_grid[grid_key] = 1

            # Get discovery info
            discovery = p.get('Discovery', {})
            location = discovery.get('Location', 'Unknown') if isinstance(discovery, dict) else 'Unknown'

            layout_data[p['Name']] = {
                'type': 'particle',
                'x': x,
                'y': y,
                'width': self.card_width,
                'height': self.card_height,
                'particle': p,
                'discovery_year': year,
                'discovery_location': location,
                'era': self._get_era(year)
            }

        # Add era bands for visual reference
        layout_data['_eras'] = {
            'type': 'era_bands',
            'eras': self._get_era_bands(plot_top, plot_height),
            'timeline_left': timeline_left,
            'timeline_right': timeline_right,
            'year_min': year_min,
            'year_max': year_max
        }

        # Place particles without discovery dates in a separate section
        if particles_without_date:
            unknown_y = plot_top + plot_height + 80

            layout_data['_unknown_date_header'] = {
                'type': 'subheader',
                'x': x_start,
                'y': unknown_y,
                'text': 'Discovery Date Unknown',
                'color': (150, 150, 150)
            }
            unknown_y += 35

            available_width = self.widget_width - self.margin_left - self.margin_right
            cols = max(1, available_width // (self.card_width + self.card_spacing))

            for i, p in enumerate(particles_without_date):
                row = i // cols
                col = i % cols
                x = x_start + col * (self.card_width + self.card_spacing)
                y = unknown_y + row * (self.card_height + self.card_spacing)

                layout_data[p['Name']] = {
                    'type': 'particle',
                    'x': x,
                    'y': y,
                    'width': self.card_width,
                    'height': self.card_height,
                    'particle': p,
                    'discovery_year': None,
                    'era': 'unknown'
                }

        return layout_data

    def _get_era_markers(self):
        """Get historical era markers for the timeline"""
        return [
            {'year': 1897, 'label': '1897\nElectron', 'major': True},
            {'year': 1911, 'label': '1911\nNucleus'},
            {'year': 1919, 'label': '1919\nProton', 'major': True},
            {'year': 1932, 'label': '1932\nNeutron', 'major': True},
            {'year': 1947, 'label': '1947\nPion', 'major': True},
            {'year': 1950, 'label': '1950\nStrange'},
            {'year': 1964, 'label': '1964\nQuark Model', 'major': True},
            {'year': 1974, 'label': '1974\nJ/psi', 'major': True},
            {'year': 1977, 'label': '1977\nUpsilon'},
            {'year': 1995, 'label': '1995\nTop Quark', 'major': True},
            {'year': 2012, 'label': '2012\nHiggs', 'major': True},
        ]

    def _get_era_bands(self, plot_top, plot_height):
        """Get era bands for visual reference"""
        # Use era boundaries from config
        classical_end = self.era_boundaries.get('classical', 1932)
        nuclear_end = self.era_boundaries.get('nuclear', 1947)
        strange_end = self.era_boundaries.get('strange', 1964)
        quark_model_end = self.era_boundaries.get('quark_model', 1995)

        return [
            {
                'name': 'Classical Era',
                'start': 1895,
                'end': classical_end,
                'color': (100, 100, 150, 50),
                'y_start': plot_top,
                'y_end': plot_top + plot_height
            },
            {
                'name': 'Nuclear Era',
                'start': classical_end,
                'end': nuclear_end,
                'color': (100, 150, 100, 50),
                'y_start': plot_top,
                'y_end': plot_top + plot_height
            },
            {
                'name': 'Strange Particles',
                'start': nuclear_end,
                'end': strange_end,
                'color': (150, 100, 100, 50),
                'y_start': plot_top,
                'y_end': plot_top + plot_height
            },
            {
                'name': 'Quark Model Era',
                'start': strange_end,
                'end': quark_model_end,
                'color': (150, 150, 100, 50),
                'y_start': plot_top,
                'y_end': plot_top + plot_height
            },
            {
                'name': 'Modern Era',
                'start': quark_model_end,
                'end': 2020,
                'color': (100, 150, 150, 50),
                'y_start': plot_top,
                'y_end': plot_top + plot_height
            }
        ]

    def _get_era(self, year):
        """Determine which era a discovery belongs to"""
        classical_end = self.era_boundaries.get('classical', 1932)
        nuclear_end = self.era_boundaries.get('nuclear', 1947)
        strange_end = self.era_boundaries.get('strange', 1964)
        quark_model_end = self.era_boundaries.get('quark_model', 1995)

        if year < classical_end:
            return 'classical'
        elif year < nuclear_end:
            return 'nuclear'
        elif year < strange_end:
            return 'strange'
        elif year < quark_model_end:
            return 'quark_model'
        else:
            return 'modern'

    def get_content_height(self, particles):
        """Calculate total content height"""
        # Count particles without dates
        without_date = 0
        for p in particles:
            discovery = p.get('Discovery', {})
            if isinstance(discovery, dict):
                if not discovery.get('Year'):
                    without_date += 1
            else:
                without_date += 1

        height = self.header_height + self.timeline_height + 500  # Main plot area

        if without_date > 0:
            available_width = self.widget_width - self.margin_left - self.margin_right
            cols = max(1, available_width // (self.card_width + self.card_spacing))
            rows = (without_date + cols - 1) // cols
            height += 100 + rows * (self.card_height + self.card_spacing)

        return max(height, 700)

    def update_dimensions(self, width, height):
        """Update layout dimensions"""
        self.widget_width = width
        self.widget_height = height
