"""
Molecule Bond Type Layout
Arranges molecules grouped by bond type (Covalent, Ionic, etc.).
"""

from typing import List, Dict
from periodica.core.molecule_enums import BondType

from periodica.data.layout_config_loader import get_molecule_config, get_layout_config


class MoleculeBondLayout:
    """Bond type-grouped layout for molecules"""

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
        self.group_spacing = spacing.get('group', 40)
        self.header_height = spacing.get('header', 40)

        # Load bond type ordering from config
        self.bond_type_order = config.get_ordering('molecules', 'bond_type')

    def calculate_layout(self, molecules: List[Dict]) -> List[Dict]:
        """
        Calculate positions for molecules grouped by bond type.

        Args:
            molecules: List of molecule dictionaries

        Returns:
            List of molecules with position data added
        """
        if not molecules:
            return []

        # Group molecules by bond type
        groups = {}
        for mol in molecules:
            bond_type = mol.get('bond_type', 'Unknown')
            if bond_type not in groups:
                groups[bond_type] = []
            groups[bond_type].append(mol)

        positioned_molecules = []
        current_y = self.padding

        # Use configured bond type order, then add remaining alphabetically
        group_order = []
        for bond in self.bond_type_order:
            if bond in groups:
                group_order.append(bond)

        for key in sorted(groups.keys()):
            if key not in group_order:
                group_order.append(key)

        for group_name in group_order:
            group_mols = groups.get(group_name, [])
            if not group_mols:
                continue

            # Get group color
            group_color = BondType.get_color(group_name)

            # Calculate cards per row
            available_width = self.widget_width - 2 * self.padding
            cols = max(1, int(available_width / (self.card_width + self.spacing)))

            # Add space for header
            current_y += self.header_height

            # Position molecules in this group
            for idx, mol in enumerate(group_mols):
                row = idx // cols
                col = idx % cols

                # Center the row
                items_in_row = min(cols, len(group_mols) - row * cols)
                row_width = items_in_row * self.card_width + (items_in_row - 1) * self.spacing
                start_x = (self.widget_width - row_width) / 2

                x = start_x + col * (self.card_width + self.spacing)
                y = current_y + row * (self.card_height + self.spacing)

                mol_copy = mol.copy()
                mol_copy['x'] = x
                mol_copy['y'] = y
                mol_copy['width'] = self.card_width
                mol_copy['height'] = self.card_height
                mol_copy['group'] = group_name
                mol_copy['group_color'] = group_color
                mol_copy['group_header_y'] = current_y - self.header_height
                positioned_molecules.append(mol_copy)

            # Update current_y for next group
            rows = (len(group_mols) + cols - 1) // cols
            current_y += rows * (self.card_height + self.spacing) + self.group_spacing

        return positioned_molecules

    def get_group_headers(self, molecules: List[Dict]) -> List[Dict]:
        """Get group header information for rendering"""
        if not molecules:
            return []

        headers = {}
        for mol in molecules:
            group = mol.get('group')
            if group and group not in headers:
                headers[group] = {
                    'name': group,
                    'y': mol.get('group_header_y', 0),
                    'color': mol.get('group_color', '#FFFFFF')
                }

        return list(headers.values())

    def get_molecule_at_position(self, x: float, y: float, molecules: List[Dict]) -> Dict:
        """Find molecule at given position."""
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

        positioned = self.calculate_layout(molecules)
        if not positioned:
            return 0

        max_y = max(m.get('y', 0) + m.get('height', self.card_height) for m in positioned)
        return int(max_y + self.padding)
