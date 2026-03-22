"""
Molecule Density Layout
Density-Mass Correlation scatter plot visualization.
X-axis: MolecularMass_amu
Y-axis: Density_g_cm3
Color by Category (Organic/Inorganic/Ionic)
Reveals packing efficiency patterns.
"""

import math
from typing import List, Dict
from periodica.core.molecule_enums import MoleculeCategory

from periodica.data.layout_config_loader import get_molecule_config, get_layout_config


class MoleculeDensityLayout:
    """Density-mass correlation scatter plot layout for molecules"""

    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height

        # Load configuration from JSON
        config = get_layout_config()
        card_size = config.get_card_size('molecules')
        margins = config.get_margins('molecules')

        # Scatter plot card sizes based on config
        self.base_card_size = card_size.get('width', 150) - 50
        self.min_card_size = card_size.get('min_width', 120) - 50
        self.max_card_size = card_size.get('max_width', 200) - 70
        self.padding = margins.get('top', 80)  # Extra padding for axis labels
        self.axis_margin = 60

        # Load category ordering from config
        self.category_order = config.get_ordering('molecules', 'category')

    def calculate_layout(self, molecules: List[Dict]) -> List[Dict]:
        """
        Calculate positions for molecules based on mass and density.

        Args:
            molecules: List of molecule dictionaries

        Returns:
            List of molecules with position data added
        """
        if not molecules:
            return []

        # Filter molecules with valid density and mass data
        valid_molecules = [m for m in molecules
                         if m.get('density', 0) > 0 and m.get('mass', 0) > 0]

        if not valid_molecules:
            # Fall back to all molecules
            valid_molecules = molecules

        # Find ranges for scaling
        masses = [m.get('mass', 1) for m in valid_molecules]
        densities = [m.get('density', 1) for m in valid_molecules]

        min_mass = min(masses) if masses else 1
        max_mass = max(masses) if masses else 100
        min_density = min(densities) if densities else 0.5
        max_density = max(densities) if densities else 3.0

        # Add margin to ranges
        mass_range = max_mass - min_mass if max_mass > min_mass else 1
        density_range = max_density - min_density if max_density > min_density else 0.1

        # Calculate plot area
        plot_left = self.padding + self.axis_margin
        plot_right = self.widget_width - self.padding
        plot_top = self.padding
        plot_bottom = self.widget_height - self.padding - self.axis_margin
        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top

        positioned_molecules = []

        for mol in valid_molecules:
            mass = mol.get('mass', min_mass)
            density = mol.get('density', min_density)
            category = mol.get('category', 'Inorganic')

            # Calculate position based on mass and density
            # X-axis: molecular mass (left = low, right = high)
            x_ratio = (mass - min_mass) / mass_range if mass_range > 0 else 0.5
            # Y-axis: density (bottom = low, top = high, inverted for screen coords)
            y_ratio = (density - min_density) / density_range if density_range > 0 else 0.5

            x = plot_left + x_ratio * plot_width
            y = plot_bottom - y_ratio * plot_height  # Invert Y

            # Get category color
            category_color = MoleculeCategory.get_color(category)

            # Calculate packing efficiency indicator (density / mass ratio scaled)
            packing_ratio = density / max(mass, 1)
            card_size = self.min_card_size + (packing_ratio * 50) * (self.max_card_size - self.min_card_size)
            card_size = min(max(card_size, self.min_card_size), self.max_card_size)

            mol_copy = mol.copy()
            mol_copy['x'] = x - card_size / 2  # Center on point
            mol_copy['y'] = y - card_size / 2
            mol_copy['width'] = card_size
            mol_copy['height'] = card_size
            mol_copy['scatter_x'] = x
            mol_copy['scatter_y'] = y
            mol_copy['category_color'] = category_color
            mol_copy['group'] = category
            mol_copy['group_color'] = category_color
            mol_copy['packing_efficiency'] = packing_ratio
            positioned_molecules.append(mol_copy)

        return positioned_molecules

    def get_axis_info(self, molecules: List[Dict]) -> Dict:
        """Get axis information for rendering"""
        if not molecules:
            return {}

        masses = [m.get('mass', 0) for m in molecules if m.get('mass', 0) > 0]
        densities = [m.get('density', 0) for m in molecules if m.get('density', 0) > 0]

        return {
            'x_label': 'Molecular Mass (amu)',
            'y_label': 'Density (g/cm3)',
            'x_min': min(masses) if masses else 0,
            'x_max': max(masses) if masses else 100,
            'y_min': min(densities) if densities else 0,
            'y_max': max(densities) if densities else 3,
            'plot_left': self.padding + self.axis_margin,
            'plot_right': self.widget_width - self.padding,
            'plot_top': self.padding,
            'plot_bottom': self.widget_height - self.padding - self.axis_margin
        }

    def get_legend_info(self) -> List[Dict]:
        """Get legend information for category colors"""
        # Use configured category order if available
        categories = self.category_order if self.category_order else ['Organic', 'Inorganic']
        return [
            {'name': cat, 'color': MoleculeCategory.get_color(cat)}
            for cat in categories
        ]

    def get_group_headers(self, molecules: List[Dict]) -> List[Dict]:
        """Get group header information for rendering (legend style)"""
        if not molecules:
            return []

        # Return legend-style headers for the category clusters
        headers = []
        seen_categories = set()
        for mol in molecules:
            category = mol.get('group', 'Unknown')
            if category not in seen_categories:
                seen_categories.add(category)
                headers.append({
                    'name': f'{category}',
                    'y': self.padding,
                    'color': mol.get('category_color', '#FFFFFF')
                })

        return headers

    def get_molecule_at_position(self, x: float, y: float, molecules: List[Dict]) -> Dict:
        """Find molecule at given position."""
        for mol in molecules:
            mx = mol.get('x', 0)
            my = mol.get('y', 0)
            mw = mol.get('width', self.base_card_size)
            mh = mol.get('height', self.base_card_size)

            if mx <= x <= mx + mw and my <= y <= my + mh:
                return mol

        return None

    def update_dimensions(self, width: int, height: int):
        """Update widget dimensions"""
        self.widget_width = width
        self.widget_height = height

    def get_content_height(self, molecules: List[Dict]) -> int:
        """Calculate total content height for scrolling"""
        # Scatter plot fits in viewport, minimal scrolling needed
        return max(self.widget_height, 600)
