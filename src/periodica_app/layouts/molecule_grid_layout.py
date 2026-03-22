"""
Molecule Grid Layout
Arranges molecules in a simple grid pattern.
"""

import math
from typing import List, Dict

from periodica.data.layout_config_loader import get_molecule_config, get_layout_config


class MoleculeGridLayout:
    """Grid layout for molecules"""

    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height

        # Load configuration from JSON
        config = get_layout_config()
        card_size = config.get_card_size('molecules')
        spacing = config.get_spacing('molecules')
        margins = config.get_margins('molecules')

        self.card_width = card_size.get('width', 150)
        self.card_height = card_size.get('height', 170)
        self.padding = margins.get('top', 80)
        self.spacing = spacing.get('card', 15)

    def calculate_layout(self, molecules: List[Dict]) -> List[Dict]:
        """
        Calculate grid positions for all molecules.

        Args:
            molecules: List of molecule dictionaries

        Returns:
            List of molecules with position data added
        """
        if not molecules:
            return []

        # Calculate grid dimensions
        available_width = self.widget_width - 2 * self.padding
        cols = max(1, int(available_width / (self.card_width + self.spacing)))
        rows = math.ceil(len(molecules) / cols)

        # Center the grid
        total_grid_width = cols * self.card_width + (cols - 1) * self.spacing
        start_x = (self.widget_width - total_grid_width) / 2

        positioned_molecules = []
        for idx, mol in enumerate(molecules):
            row = idx // cols
            col = idx % cols

            x = start_x + col * (self.card_width + self.spacing)
            y = self.padding + row * (self.card_height + self.spacing)

            mol_copy = mol.copy()
            mol_copy['x'] = x
            mol_copy['y'] = y
            mol_copy['width'] = self.card_width
            mol_copy['height'] = self.card_height
            mol_copy['row'] = row
            mol_copy['col'] = col
            positioned_molecules.append(mol_copy)

        return positioned_molecules

    def get_molecule_at_position(self, x: float, y: float, molecules: List[Dict]) -> Dict:
        """
        Find molecule at given position.

        Args:
            x: X coordinate
            y: Y coordinate
            molecules: List of positioned molecules

        Returns:
            Molecule dictionary or None
        """
        for mol in molecules:
            mx = mol.get('x', 0)
            my = mol.get('y', 0)
            mw = mol.get('width', self.card_width)
            mh = mol.get('height', self.card_height)

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

        available_width = self.widget_width - 2 * self.padding
        cols = max(1, int(available_width / (self.card_width + self.spacing)))
        rows = math.ceil(len(molecules) / cols)

        return int(2 * self.padding + rows * (self.card_height + self.spacing))
