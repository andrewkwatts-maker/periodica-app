"""
Molecule Bond Complexity Layout
Tree structure visualization by total bond count.
Branch by bond type diversity.
Size represents total atom count from Composition.
"""

import math
from typing import List, Dict, Set
from periodica.core.molecule_enums import BondType

from periodica.data.layout_config_loader import get_molecule_config, get_layout_config


class MoleculeBondComplexityLayout:
    """Bond complexity hierarchy tree layout for molecules"""

    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height

        # Load configuration from JSON
        config = get_layout_config()
        card_size = config.get_card_size('molecules')
        spacing = config.get_spacing('molecules')
        margins = config.get_margins('molecules')
        mass_scaling = get_molecule_config('mass_scaling', default={})

        self.base_card_width = mass_scaling.get('base_width', 120)
        self.base_card_height = mass_scaling.get('base_height', 140)
        self.min_card_size = card_size.get('min_width', 120) - 30
        self.max_card_size = card_size.get('max_width', 200) - 40
        self.padding = margins.get('top', 80) - 40
        self.spacing = spacing.get('card', 15) + 5
        self.level_spacing = spacing.get('group', 40) * 2  # Vertical spacing between complexity levels
        self.header_height = spacing.get('header', 40) + 5

    def _count_total_bonds(self, mol: Dict) -> int:
        """Count total number of bonds in a molecule"""
        bonds = mol.get('Bonds', [])
        return len(bonds)

    def _count_atom_total(self, mol: Dict) -> int:
        """Count total number of atoms from composition"""
        composition = mol.get('Composition', [])
        return sum(c.get('Count', 1) for c in composition)

    def _get_bond_type_diversity(self, mol: Dict) -> Set[str]:
        """Get set of unique bond types in molecule"""
        bonds = mol.get('Bonds', [])
        return set(bond.get('Type', 'Single') for bond in bonds)

    def _calculate_complexity_score(self, mol: Dict) -> float:
        """Calculate complexity score based on bonds and diversity"""
        bond_count = self._count_total_bonds(mol)
        diversity = len(self._get_bond_type_diversity(mol))
        atom_count = self._count_atom_total(mol)

        # Complexity score combines bond count, diversity, and atom count
        return bond_count * 2 + diversity * 3 + atom_count

    def calculate_layout(self, molecules: List[Dict]) -> List[Dict]:
        """
        Calculate positions for molecules in a hierarchical tree structure
        based on bond complexity.

        Args:
            molecules: List of molecule dictionaries

        Returns:
            List of molecules with position data added
        """
        if not molecules:
            return []

        # Calculate complexity metrics for each molecule
        molecules_with_metrics = []
        for mol in molecules:
            mol_copy = mol.copy()
            mol_copy['bond_count'] = self._count_total_bonds(mol)
            mol_copy['atom_count'] = self._count_atom_total(mol)
            mol_copy['bond_diversity'] = len(self._get_bond_type_diversity(mol))
            mol_copy['complexity_score'] = self._calculate_complexity_score(mol)
            molecules_with_metrics.append(mol_copy)

        # Group by bond count (primary hierarchy)
        bond_groups = {}
        for mol in molecules_with_metrics:
            bond_count = mol['bond_count']
            # Group into ranges: 0-1, 2-3, 4-5, 6+
            if bond_count <= 1:
                level = 'Simple (0-1 bonds)'
                level_order = 0
            elif bond_count <= 3:
                level = 'Basic (2-3 bonds)'
                level_order = 1
            elif bond_count <= 5:
                level = 'Moderate (4-5 bonds)'
                level_order = 2
            else:
                level = 'Complex (6+ bonds)'
                level_order = 3

            if level not in bond_groups:
                bond_groups[level] = {'mols': [], 'order': level_order}
            bond_groups[level]['mols'].append(mol)

        # Sort groups by level order
        sorted_levels = sorted(bond_groups.items(), key=lambda x: x[1]['order'])

        # Calculate atom count range for sizing
        all_atom_counts = [m['atom_count'] for m in molecules_with_metrics]
        min_atoms = min(all_atom_counts) if all_atom_counts else 1
        max_atoms = max(all_atom_counts) if all_atom_counts else 10
        atom_range = max_atoms - min_atoms if max_atoms > min_atoms else 1

        positioned_molecules = []
        current_y = self.padding

        for level_name, group_data in sorted_levels:
            group_mols = group_data['mols']
            if not group_mols:
                continue

            # Sort within level by bond diversity (secondary branching)
            group_mols.sort(key=lambda m: (-m['bond_diversity'], -m['complexity_score']))

            # Group header
            group_header_y = current_y
            current_y += self.header_height

            # Sub-group by bond diversity for tree branching effect
            diversity_groups = {}
            for mol in group_mols:
                diversity = mol['bond_diversity']
                if diversity not in diversity_groups:
                    diversity_groups[diversity] = []
                diversity_groups[diversity].append(mol)

            # Calculate available width
            available_width = self.widget_width - 2 * self.padding

            # Position molecules with tree-like indentation based on diversity
            max_row_height = 0
            total_rows = 0

            for diversity in sorted(diversity_groups.keys(), reverse=True):
                div_mols = diversity_groups[diversity]

                # Indent based on diversity (more diverse = closer to center/right)
                indent = (diversity - 1) * 40

                # Calculate cards per row for this diversity level
                indented_width = available_width - indent
                cols = max(1, int(indented_width / (self.base_card_width + self.spacing)))

                for idx, mol in enumerate(div_mols):
                    row = idx // cols
                    col = idx % cols

                    # Size based on atom count
                    atom_count = mol['atom_count']
                    size_ratio = (atom_count - min_atoms) / atom_range if atom_range > 0 else 0.5
                    card_width = self.min_card_size + size_ratio * (self.max_card_size - self.min_card_size)
                    card_height = card_width * 1.1  # Slightly taller than wide

                    # Position with indent
                    x = self.padding + indent + col * (self.base_card_width + self.spacing)
                    y = current_y + total_rows * (self.base_card_height + self.spacing)

                    # Get color based on bond diversity
                    diversity_color = self._get_diversity_color(diversity)

                    mol['x'] = x
                    mol['y'] = y + row * (self.base_card_height + self.spacing)
                    mol['width'] = card_width
                    mol['height'] = card_height
                    mol['group'] = level_name
                    mol['group_color'] = diversity_color
                    mol['group_header_y'] = group_header_y
                    mol['diversity_level'] = diversity
                    positioned_molecules.append(mol)

                    max_row_height = max(max_row_height, card_height)

                # Update row count for this diversity sub-group
                rows_in_diversity = (len(div_mols) + cols - 1) // cols
                total_rows += rows_in_diversity

            # Update current_y for next level
            current_y += total_rows * (self.base_card_height + self.spacing) + self.level_spacing

        return positioned_molecules

    def _get_diversity_color(self, diversity: int) -> str:
        """Get color based on bond type diversity"""
        colors = {
            0: '#9E9E9E',   # Grey - no bonds
            1: '#4CAF50',   # Green - single type
            2: '#2196F3',   # Blue - two types
            3: '#9C27B0',   # Purple - three types
            4: '#E91E63',   # Pink - four types
        }
        return colors.get(diversity, '#FF5722')  # Orange for 5+

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

    def get_legend_info(self) -> List[Dict]:
        """Get legend information for bond diversity colors"""
        return [
            {'name': '1 Bond Type', 'color': self._get_diversity_color(1)},
            {'name': '2 Bond Types', 'color': self._get_diversity_color(2)},
            {'name': '3 Bond Types', 'color': self._get_diversity_color(3)},
            {'name': '4+ Bond Types', 'color': self._get_diversity_color(4)}
        ]

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

        positioned = self.calculate_layout(molecules)
        if not positioned:
            return 0

        max_y = max(m.get('y', 0) + m.get('height', self.base_card_height) for m in positioned)
        return int(max_y + self.padding)
