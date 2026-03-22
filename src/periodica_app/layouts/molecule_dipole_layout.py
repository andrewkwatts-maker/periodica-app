"""
Molecule Dipole Layout
Polarity-Dipole Moment Chart visualization.
X-axis: DipoleMoment_D (0 to max)
Grouped vertically by Polarity type (Polar/Nonpolar/Ionic)
Shows relationship between dipole moment and polarity classification.
"""

from typing import List, Dict
from periodica.core.molecule_enums import MoleculePolarity

from periodica.data.layout_config_loader import get_molecule_config, get_layout_config


class MoleculeDipoleLayout:
    """Dipole moment grouped by polarity layout for molecules"""

    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height

        # Load configuration from JSON
        config = get_layout_config()
        card_size = config.get_card_size('molecules')
        spacing = config.get_spacing('molecules')
        margins = config.get_margins('molecules')

        # Slightly smaller cards for dipole chart
        self.card_width = card_size.get('width', 150) - 20
        self.card_height = card_size.get('height', 170) - 20
        self.padding = margins.get('top', 80) - 40
        self.spacing = spacing.get('card', 15)
        self.group_spacing = spacing.get('group', 40) + 10
        self.header_height = spacing.get('header', 40) + 5
        self.axis_height = 50  # Space for dipole moment axis

        # Load polarity ordering from config
        self.polarity_order = config.get_ordering('molecules', 'polarity')

    def calculate_layout(self, molecules: List[Dict]) -> List[Dict]:
        """
        Calculate positions for molecules based on dipole moment and polarity.

        Args:
            molecules: List of molecule dictionaries

        Returns:
            List of molecules with position data added
        """
        if not molecules:
            return []

        # Group molecules by polarity
        groups = {
            'Polar': [],
            'Nonpolar': [],
            'Ionic': []
        }

        for mol in molecules:
            polarity = mol.get('polarity', 'Unknown')
            if polarity in groups:
                groups[polarity].append(mol)
            else:
                groups['Nonpolar'].append(mol)  # Default to nonpolar

        # Sort each group by dipole moment
        for group_name in groups:
            groups[group_name].sort(key=lambda m: m.get('dipole_moment', 0))

        # Find dipole moment range for X-axis positioning
        all_dipoles = [m.get('dipole_moment', 0) for m in molecules]
        max_dipole = max(all_dipoles) if all_dipoles else 5.0
        min_dipole = 0  # Dipole moments start at 0

        # Calculate plot area for X-axis (dipole moment)
        plot_left = self.padding + 20  # Extra space for labels
        plot_right = self.widget_width - self.padding
        plot_width = plot_right - plot_left

        positioned_molecules = []
        current_y = self.padding + self.axis_height

        # Build group order: start with Nonpolar, then use config order
        group_order = ['Nonpolar']
        for pol in self.polarity_order:
            if pol not in group_order:
                group_order.append(pol)
        if 'Ionic' not in group_order:
            group_order.append('Ionic')

        for group_name in group_order:
            group_mols = groups.get(group_name, [])
            if not group_mols:
                continue

            # Get group color
            group_color = MoleculePolarity.get_color(group_name)

            # Add space for header
            group_header_y = current_y
            current_y += self.header_height

            # Position molecules along the X-axis by dipole moment
            # Stack vertically if multiple molecules have similar dipole values
            dipole_bins = {}  # Group molecules by similar dipole moments

            for mol in group_mols:
                dipole = mol.get('dipole_moment', 0)
                # Create bins for similar dipole values (within 0.5 D)
                bin_key = round(dipole * 2) / 2  # Round to nearest 0.5
                if bin_key not in dipole_bins:
                    dipole_bins[bin_key] = []
                dipole_bins[bin_key].append(mol)

            row_count = 0
            for bin_dipole in sorted(dipole_bins.keys()):
                bin_mols = dipole_bins[bin_dipole]

                for row_idx, mol in enumerate(bin_mols):
                    dipole = mol.get('dipole_moment', 0)

                    # Calculate X position based on dipole moment
                    if max_dipole > min_dipole:
                        x_ratio = (dipole - min_dipole) / (max_dipole - min_dipole)
                    else:
                        x_ratio = 0.5

                    x = plot_left + x_ratio * (plot_width - self.card_width)
                    y = current_y + row_idx * (self.card_height + self.spacing)

                    mol_copy = mol.copy()
                    mol_copy['x'] = x
                    mol_copy['y'] = y
                    mol_copy['width'] = self.card_width
                    mol_copy['height'] = self.card_height
                    mol_copy['group'] = group_name
                    mol_copy['group_color'] = group_color
                    mol_copy['group_header_y'] = group_header_y
                    mol_copy['dipole_value'] = dipole
                    positioned_molecules.append(mol_copy)

                    row_count = max(row_count, row_idx + 1)

            # Update current_y for next group
            current_y += row_count * (self.card_height + self.spacing) + self.group_spacing

        return positioned_molecules

    def get_axis_info(self, molecules: List[Dict]) -> Dict:
        """Get axis information for rendering dipole moment scale"""
        all_dipoles = [m.get('dipole_moment', 0) for m in molecules]
        max_dipole = max(all_dipoles) if all_dipoles else 5.0

        return {
            'x_label': 'Dipole Moment (Debye)',
            'x_min': 0,
            'x_max': max_dipole,
            'plot_left': self.padding + 20,
            'plot_right': self.widget_width - self.padding,
            'axis_y': self.padding + self.axis_height - 20
        }

    def get_group_headers(self, molecules: List[Dict]) -> List[Dict]:
        """Get group header information for rendering"""
        if not molecules:
            return []

        headers = {}
        for mol in molecules:
            group = mol.get('group')
            if group and group not in headers:
                headers[group] = {
                    'name': f'{group} Molecules',
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
