"""
Molecule Mass Order Layout
Arranges molecules in order of molecular mass, with visual sizing based on mass.
"""

import math
from typing import List, Dict

from periodica.data.layout_config_loader import get_molecule_config, get_layout_config


class MoleculeMassLayout:
    """Mass-ordered layout for molecules"""

    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height

        # Load configuration from JSON
        config = get_layout_config()
        spacing = config.get_spacing('molecules')
        margins = config.get_margins('molecules')
        mass_scaling = get_molecule_config('mass_scaling', default={})

        self.base_card_width = mass_scaling.get('base_width', 120)
        self.base_card_height = mass_scaling.get('base_height', 140)
        self.min_scale = mass_scaling.get('min_scale', 1.0)
        self.max_scale = mass_scaling.get('max_scale', 1.5)
        self.padding = margins.get('top', 80)
        self.spacing = spacing.get('card', 15) + 5  # Slightly more spacing for variable sizes

    def calculate_layout(self, molecules: List[Dict]) -> List[Dict]:
        """
        Calculate positions for molecules ordered by mass.

        Args:
            molecules: List of molecule dictionaries

        Returns:
            List of molecules with position data added
        """
        if not molecules:
            return []

        # Sort by molecular mass
        sorted_mols = sorted(molecules, key=lambda m: m.get('mass', 0))

        # Find mass range for scaling
        masses = [m.get('mass', 0) for m in sorted_mols]
        min_mass = min(masses) if masses else 1
        max_mass = max(masses) if masses else 1
        mass_range = max_mass - min_mass if max_mass > min_mass else 1

        positioned_molecules = []
        current_x = self.padding
        current_y = self.padding
        row_height = 0
        row_start_idx = 0

        for idx, mol in enumerate(sorted_mols):
            # Scale card size based on mass using config values
            mass = mol.get('mass', min_mass)
            scale = self.min_scale + (self.max_scale - self.min_scale) * ((mass - min_mass) / mass_range)

            card_width = int(self.base_card_width * scale)
            card_height = int(self.base_card_height * scale)

            # Check if we need to wrap to next row
            if current_x + card_width > self.widget_width - self.padding:
                # Center the completed row
                row_width = current_x - self.spacing - self.padding
                offset = (self.widget_width - row_width - 2 * self.padding) / 2
                for i in range(row_start_idx, len(positioned_molecules)):
                    positioned_molecules[i]['x'] += offset

                current_x = self.padding
                current_y += row_height + self.spacing
                row_height = 0
                row_start_idx = len(positioned_molecules)

            mol_copy = mol.copy()
            mol_copy['x'] = current_x
            mol_copy['y'] = current_y
            mol_copy['width'] = card_width
            mol_copy['height'] = card_height
            mol_copy['scale'] = scale
            mol_copy['mass_rank'] = idx + 1
            positioned_molecules.append(mol_copy)

            current_x += card_width + self.spacing
            row_height = max(row_height, card_height)

        # Center the last row
        if positioned_molecules:
            row_width = current_x - self.spacing - self.padding
            offset = (self.widget_width - row_width - 2 * self.padding) / 2
            for i in range(row_start_idx, len(positioned_molecules)):
                positioned_molecules[i]['x'] += offset

        return positioned_molecules

    def get_molecule_at_position(self, x: float, y: float, molecules: List[Dict]) -> Dict:
        """Find molecule at given position."""
        for mol in molecules:
            mx = mol.get('x', 0)
            my = mol.get('y', 0)
            mw = mol.get('width', self.base_card_width)
            mh = mol.get('height', self.base_card_height)

            if mx <= x <= mx + mw and my <= y <= my + mh:
                return mol

        return None

    def update_dimensions(self, width: int, height: int):
        """Update widget dimensions"""
        self.widget_width = width
        self.widget_height = height

    def get_content_height(self, molecules: List[Dict]) -> int:
        """Calculate total content height for scrolling"""
        if not molecules:
            return 0

        # Recalculate to find actual height
        positioned = self.calculate_layout(molecules)
        if not positioned:
            return 0

        max_y = max(m.get('y', 0) + m.get('height', self.base_card_height) for m in positioned)
        return int(max_y + self.padding)
