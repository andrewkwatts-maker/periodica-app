"""
Molecule Phase Diagram Layout
Scatter plot visualization clustering molecules by physical state.
X-axis: MeltingPoint_K
Y-axis: BoilingPoint_K
Size by molecular mass
Color by State_STP (Gas/Liquid/Solid)
"""

import math
from typing import List, Dict
from periodica.core.molecule_enums import MoleculeState

from periodica.data.layout_config_loader import get_molecule_config, get_layout_config


class MoleculePhaseDiagramLayout:
    """Phase diagram scatter plot layout for molecules"""

    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height

        # Load configuration from JSON
        config = get_layout_config()
        card_size = config.get_card_size('molecules')
        margins = config.get_margins('molecules')

        # Scatter plot card sizes based on config
        self.base_card_size = card_size.get('width', 150) // 2  # Smaller for scatter
        self.min_card_size = card_size.get('min_width', 120) // 2
        self.max_card_size = card_size.get('max_width', 200) // 2 + 40
        self.padding = margins.get('top', 80)  # Extra padding for axis labels
        self.axis_margin = 60

        # Load state ordering from config
        self.state_order = config.get_ordering('molecules', 'state')

    def calculate_layout(self, molecules: List[Dict]) -> List[Dict]:
        """
        Calculate positions for molecules based on melting/boiling points.

        Args:
            molecules: List of molecule dictionaries

        Returns:
            List of molecules with position data added
        """
        if not molecules:
            return []

        # Filter molecules with valid temperature data
        valid_molecules = [m for m in molecules
                         if m.get('melting_point', 0) > 0 and m.get('boiling_point', 0) > 0]

        if not valid_molecules:
            # Fall back to all molecules with default positioning
            valid_molecules = molecules

        # Find ranges for scaling
        melting_points = [m.get('melting_point', 273) for m in valid_molecules]
        boiling_points = [m.get('boiling_point', 373) for m in valid_molecules]
        masses = [m.get('mass', 1) for m in valid_molecules]

        min_mp = min(melting_points) if melting_points else 0
        max_mp = max(melting_points) if melting_points else 1000
        min_bp = min(boiling_points) if boiling_points else 0
        max_bp = max(boiling_points) if boiling_points else 1000
        min_mass = min(masses) if masses else 1
        max_mass = max(masses) if masses else 100

        # Add some margin to ranges
        mp_range = max_mp - min_mp if max_mp > min_mp else 100
        bp_range = max_bp - min_bp if max_bp > min_bp else 100
        mass_range = max_mass - min_mass if max_mass > min_mass else 1

        # Calculate plot area
        plot_left = self.padding + self.axis_margin
        plot_right = self.widget_width - self.padding
        plot_top = self.padding
        plot_bottom = self.widget_height - self.padding - self.axis_margin
        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top

        positioned_molecules = []

        for mol in valid_molecules:
            mp = mol.get('melting_point', min_mp)
            bp = mol.get('boiling_point', min_bp)
            mass = mol.get('mass', min_mass)
            state = mol.get('state', 'Gas')

            # Calculate position based on melting and boiling points
            # X-axis: melting point (left = low, right = high)
            x_ratio = (mp - min_mp) / mp_range if mp_range > 0 else 0.5
            # Y-axis: boiling point (bottom = low, top = high, inverted for screen coords)
            y_ratio = (bp - min_bp) / bp_range if bp_range > 0 else 0.5

            x = plot_left + x_ratio * plot_width
            y = plot_bottom - y_ratio * plot_height  # Invert Y

            # Size based on molecular mass
            mass_ratio = (mass - min_mass) / mass_range if mass_range > 0 else 0.5
            card_size = self.min_card_size + mass_ratio * (self.max_card_size - self.min_card_size)

            # Get state color
            state_color = MoleculeState.get_color(state)

            mol_copy = mol.copy()
            mol_copy['x'] = x - card_size / 2  # Center on point
            mol_copy['y'] = y - card_size / 2
            mol_copy['width'] = card_size
            mol_copy['height'] = card_size
            mol_copy['scatter_x'] = x
            mol_copy['scatter_y'] = y
            mol_copy['state_color'] = state_color
            mol_copy['group'] = state
            mol_copy['group_color'] = state_color
            positioned_molecules.append(mol_copy)

        return positioned_molecules

    def get_axis_info(self, molecules: List[Dict]) -> Dict:
        """Get axis information for rendering"""
        if not molecules:
            return {}

        melting_points = [m.get('melting_point', 0) for m in molecules if m.get('melting_point', 0) > 0]
        boiling_points = [m.get('boiling_point', 0) for m in molecules if m.get('boiling_point', 0) > 0]

        return {
            'x_label': 'Melting Point (K)',
            'y_label': 'Boiling Point (K)',
            'x_min': min(melting_points) if melting_points else 0,
            'x_max': max(melting_points) if melting_points else 1000,
            'y_min': min(boiling_points) if boiling_points else 0,
            'y_max': max(boiling_points) if boiling_points else 1000,
            'plot_left': self.padding + self.axis_margin,
            'plot_right': self.widget_width - self.padding,
            'plot_top': self.padding,
            'plot_bottom': self.widget_height - self.padding - self.axis_margin
        }

    def get_legend_info(self) -> List[Dict]:
        """Get legend information for state colors"""
        # Use configured state order if available
        states = self.state_order if self.state_order else ['Solid', 'Liquid', 'Gas']
        return [
            {'name': state, 'color': MoleculeState.get_color(state)}
            for state in states
        ]

    def get_group_headers(self, molecules: List[Dict]) -> List[Dict]:
        """Get group header information for rendering (legend style)"""
        if not molecules:
            return []

        # Return legend-style headers for the state clusters
        headers = []
        seen_states = set()
        for mol in molecules:
            state = mol.get('group', 'Unknown')
            if state not in seen_states:
                seen_states.add(state)
                headers.append({
                    'name': f'{state} Phase',
                    'y': self.padding,
                    'color': mol.get('state_color', '#FFFFFF')
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
        # Phase diagram fits in viewport, minimal scrolling needed
        return max(self.widget_height, 600)
