"""
Molecule Unified Table Widget
Main visualization widget for displaying molecules with various layouts.
"""

import json
import math
from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QRadialGradient,
                           QLinearGradient, QPainterPath, QGuiApplication)

from periodica.data.molecule_loader import MoleculeDataLoader
from periodica.core.molecule_enums import (MoleculeLayoutMode, MolecularGeometry, BondType,
                                  MoleculePolarity, MoleculeCategory, MoleculeState,
                                  get_element_color)
from periodica_app.layouts.molecule_grid_layout import MoleculeGridLayout
from periodica_app.layouts.molecule_mass_layout import MoleculeMassLayout
from periodica_app.layouts.molecule_polarity_layout import MoleculePolarityLayout
from periodica_app.layouts.molecule_bond_layout import MoleculeBondLayout
from periodica_app.layouts.molecule_geometry_layout import MoleculeGeometryLayout
from periodica_app.layouts.molecule_phase_diagram_layout import MoleculePhaseDiagramLayout
from periodica_app.layouts.molecule_dipole_layout import MoleculeDipoleLayout
from periodica_app.layouts.molecule_density_layout import MoleculeDensityLayout
from periodica_app.layouts.molecule_bond_complexity_layout import MoleculeBondComplexityLayout


def rotate_point_3d(x, y, z, pitch, yaw, roll):
    """
    Apply 3D rotation and return transformed coordinates.

    Args:
        x, y, z: Original 3D coordinates (relative to center)
        pitch: Rotation around X-axis (tilt up/down) in degrees
        yaw: Rotation around Y-axis (turn left/right) in degrees
        roll: Rotation around Z-axis (spin) in degrees

    Returns:
        Tuple of (x2d, y2d, z_depth) for 2D projection with depth info
    """
    # Convert to radians
    pitch_rad = math.radians(pitch)
    yaw_rad = math.radians(yaw)
    roll_rad = math.radians(roll)

    # Rotation around X-axis (pitch)
    y1 = y * math.cos(pitch_rad) - z * math.sin(pitch_rad)
    z1 = y * math.sin(pitch_rad) + z * math.cos(pitch_rad)
    x1 = x

    # Rotation around Y-axis (yaw)
    x2 = x1 * math.cos(yaw_rad) + z1 * math.sin(yaw_rad)
    z2 = -x1 * math.sin(yaw_rad) + z1 * math.cos(yaw_rad)
    y2 = y1

    # Rotation around Z-axis (roll)
    x3 = x2 * math.cos(roll_rad) - y2 * math.sin(roll_rad)
    y3 = x2 * math.sin(roll_rad) + y2 * math.cos(roll_rad)
    z3 = z2

    return x3, y3, z3


class MoleculeUnifiedTable(QWidget):
    """Main widget for visualizing molecules"""

    # Signals
    molecule_selected = Signal(dict)
    molecule_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

        # Data
        self.loader = MoleculeDataLoader()
        self.base_molecules = self.loader.load_all_molecules()
        self.positioned_molecules = []

        # State
        self.layout_mode = MoleculeLayoutMode.GRID
        self.hovered_molecule = None
        self.selected_molecule = None

        # Filters (single-value, legacy)
        self.category_filter = None  # None means show all
        self.polarity_filter = None
        self.state_filter = None

        # Filters (multi-select)
        self.state_filters = ['Solid', 'Liquid', 'Gas']  # Show all by default
        self.polarity_filters = ['Polar', 'Nonpolar']  # Show all by default
        self.bond_type_filters = ['Ionic', 'Covalent', 'Polar Covalent']  # Show all by default
        self.category_filters = ['Organic', 'Inorganic']  # Show all by default

        # Visual settings
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.scroll_offset_y = 0

        # Pan interaction state
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # 3D rotation angles (in degrees)
        self.pitch = 0.0
        self.yaw = 0.0
        self.roll = 0.0

        # Layout renderers
        self.layouts = {
            MoleculeLayoutMode.GRID: MoleculeGridLayout(self.width(), self.height()),
            MoleculeLayoutMode.MASS_ORDER: MoleculeMassLayout(self.width(), self.height()),
            MoleculeLayoutMode.POLARITY: MoleculePolarityLayout(self.width(), self.height()),
            MoleculeLayoutMode.BOND_TYPE: MoleculeBondLayout(self.width(), self.height()),
            MoleculeLayoutMode.GEOMETRY: MoleculeGeometryLayout(self.width(), self.height()),
            MoleculeLayoutMode.PHASE_DIAGRAM: MoleculePhaseDiagramLayout(self.width(), self.height()),
            MoleculeLayoutMode.DIPOLE: MoleculeDipoleLayout(self.width(), self.height()),
            MoleculeLayoutMode.DENSITY: MoleculeDensityLayout(self.width(), self.height()),
            MoleculeLayoutMode.BOND_COMPLEXITY: MoleculeBondComplexityLayout(self.width(), self.height()),
        }

        # Initialize layout
        self._update_layout()

    def set_layout_mode(self, mode):
        """Set the layout mode"""
        if isinstance(mode, str):
            mode = MoleculeLayoutMode.from_string(mode)
        self.layout_mode = mode
        self._update_layout()
        self.update()

    def set_category_filter(self, category):
        """Set category filter (Organic, Inorganic, Ionic, or None for all)"""
        self.category_filter = category
        self._update_layout()
        self.update()

    def set_polarity_filter(self, polarity):
        """Set polarity filter"""
        self.polarity_filter = polarity
        self._update_layout()
        self.update()

    def set_state_filter(self, state):
        """Set state filter (single value, legacy)"""
        self.state_filter = state
        self._update_layout()
        self.update()

    def set_state_filters(self, states):
        """Set state filter (multi-select list)

        Args:
            states: List of state names to show, e.g. ['Solid', 'Liquid', 'Gas']
        """
        self.state_filters = states if states else []
        self._update_layout()
        self.update()

    def set_polarity_filters(self, polarities):
        """Set polarity filter (multi-select list)

        Args:
            polarities: List of polarity types to show, e.g. ['Polar', 'Nonpolar']
        """
        self.polarity_filters = polarities if polarities else []
        self._update_layout()
        self.update()

    def set_bond_type_filters(self, bond_types):
        """Set bond type filter (multi-select list)

        Args:
            bond_types: List of bond types to show, e.g. ['Ionic', 'Covalent', 'Polar Covalent']
        """
        self.bond_type_filters = bond_types if bond_types else []
        self._update_layout()
        self.update()

    def set_category_filters(self, categories):
        """Set category filter (multi-select list)

        Args:
            categories: List of categories to show, e.g. ['Organic', 'Inorganic']
        """
        self.category_filters = categories if categories else []
        self._update_layout()
        self.update()

    def set_rotation(self, pitch, yaw, roll):
        """Set 3D rotation angles for molecule structure visualization.

        Args:
            pitch: Rotation around X-axis (tilt up/down) in degrees (-180 to 180)
            yaw: Rotation around Y-axis (turn left/right) in degrees (-180 to 180)
            roll: Rotation around Z-axis (spin) in degrees (-180 to 180)
        """
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll
        self.update()

    def _get_filtered_molecules(self):
        """Get molecules after applying filters"""
        molecules = self.base_molecules.copy()

        # Apply multi-select category filter
        if self.category_filters:
            molecules = [m for m in molecules if self._matches_category(m)]
        elif self.category_filter:  # Legacy single-value filter
            molecules = [m for m in molecules if m.get('category') == self.category_filter]

        # Apply multi-select polarity filter
        if self.polarity_filters:
            molecules = [m for m in molecules if self._matches_polarity(m)]
        elif self.polarity_filter:  # Legacy single-value filter
            molecules = [m for m in molecules if m.get('polarity') == self.polarity_filter]

        # Apply multi-select state filter
        if self.state_filters:
            molecules = [m for m in molecules if self._matches_state(m)]
        elif self.state_filter:  # Legacy single-value filter
            molecules = [m for m in molecules if m.get('state') == self.state_filter]

        # Apply multi-select bond type filter
        if self.bond_type_filters:
            molecules = [m for m in molecules if self._matches_bond_type(m)]

        return molecules

    def _matches_category(self, molecule):
        """Check if molecule matches category filter"""
        if not self.category_filters:
            return True  # No filter, show all
        mol_category = molecule.get('category', '').capitalize()
        return mol_category in self.category_filters or molecule.get('category', '') in self.category_filters

    def _matches_polarity(self, molecule):
        """Check if molecule matches polarity filter"""
        if not self.polarity_filters:
            return True  # No filter, show all
        mol_polarity = molecule.get('polarity', '').capitalize()
        return mol_polarity in self.polarity_filters or molecule.get('polarity', '') in self.polarity_filters

    def _matches_state(self, molecule):
        """Check if molecule matches state filter"""
        if not self.state_filters:
            return True  # No filter, show all
        mol_state = molecule.get('state', '').capitalize()
        return mol_state in self.state_filters or molecule.get('state', '') in self.state_filters

    def _matches_bond_type(self, molecule):
        """Check if molecule matches bond type filter"""
        if not self.bond_type_filters:
            return True  # No filter, show all

        # Get primary bond type from molecule
        mol_bond_type = molecule.get('bond_type', '')

        # Normalize the bond type
        normalized_bond_type = mol_bond_type.title() if mol_bond_type else ''

        # Check bonds array if available
        bonds = molecule.get('Bonds', [])
        if bonds:
            for bond in bonds:
                bond_type = bond.get('Type', '').title()
                # Map common variations
                if bond_type in ['Covalent', 'Single', 'Double', 'Triple']:
                    if 'Covalent' in self.bond_type_filters:
                        return True
                elif bond_type == 'Ionic':
                    if 'Ionic' in self.bond_type_filters:
                        return True
                elif 'polar' in bond_type.lower() and 'covalent' in bond_type.lower():
                    if 'Polar Covalent' in self.bond_type_filters:
                        return True

        # Check direct bond_type field
        if normalized_bond_type:
            if normalized_bond_type in self.bond_type_filters:
                return True
            # Handle "Polar Covalent" variations
            if 'polar' in normalized_bond_type.lower() and 'covalent' in normalized_bond_type.lower():
                if 'Polar Covalent' in self.bond_type_filters:
                    return True

        # If no specific bond type but we have covalent filter, treat covalent bonds as matching
        if 'Covalent' in self.bond_type_filters:
            return True

        return len(self.bond_type_filters) == 3  # All selected, show everything

    def _update_layout(self):
        """Recalculate positions for all molecules"""
        molecules = self._get_filtered_molecules()
        layout = self.layouts.get(self.layout_mode)

        if layout:
            layout.update_dimensions(self.width(), self.height())
            self.positioned_molecules = layout.calculate_layout(molecules)

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        for layout in self.layouts.values():
            layout.update_dimensions(self.width(), self.height())
        self._update_layout()

    def paintEvent(self, event):
        """Paint the molecule visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        self._draw_background(painter)

        # Apply transformations
        painter.translate(self.pan_x, self.pan_y - self.scroll_offset_y)
        painter.scale(self.zoom_level, self.zoom_level)

        # Draw group headers if applicable
        if self.layout_mode in [MoleculeLayoutMode.POLARITY, MoleculeLayoutMode.BOND_TYPE,
                                MoleculeLayoutMode.GEOMETRY, MoleculeLayoutMode.PHASE_DIAGRAM,
                                MoleculeLayoutMode.DIPOLE, MoleculeLayoutMode.DENSITY,
                                MoleculeLayoutMode.BOND_COMPLEXITY]:
            self._draw_group_headers(painter)

        # Draw molecules
        for mol in self.positioned_molecules:
            self._draw_molecule_card(painter, mol)

        painter.end()

    def _draw_background(self, painter):
        """Draw the dark gradient background"""
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(10, 10, 26))
        gradient.setColorAt(1, QColor(26, 26, 46))
        painter.fillRect(self.rect(), QBrush(gradient))

    def _draw_group_headers(self, painter):
        """Draw group section headers"""
        layout = self.layouts.get(self.layout_mode)
        if not hasattr(layout, 'get_group_headers'):
            return

        headers = layout.get_group_headers(self.positioned_molecules)

        for header in headers:
            y = header.get('y', 0)
            name = header.get('name', '')
            color = header.get('color', '#FFFFFF')

            # Draw header background
            header_rect = QRectF(20, y, self.width() - 40, 35)
            painter.setPen(Qt.PenStyle.NoPen)

            header_color = QColor(color)
            header_color.setAlpha(40)
            painter.setBrush(QBrush(header_color))
            painter.drawRoundedRect(header_rect, 5, 5)

            # Draw header text
            painter.setPen(QPen(QColor(color)))
            painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            painter.drawText(header_rect.adjusted(15, 0, 0, 0),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                           name)

            # Draw underline
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(int(header_rect.left() + 10), int(header_rect.bottom()),
                           int(header_rect.right() - 10), int(header_rect.bottom()))

    def _draw_molecule_card(self, painter, mol):
        """Draw a single molecule card"""
        x = mol.get('x', 0)
        y = mol.get('y', 0)
        width = mol.get('width', 150)
        height = mol.get('height', 170)

        is_hovered = mol == self.hovered_molecule
        is_selected = mol == self.selected_molecule

        # Card background
        card_rect = QRectF(x, y, width, height)

        # Gradient background
        gradient = QLinearGradient(x, y, x, y + height)
        if is_selected:
            gradient.setColorAt(0, QColor(80, 80, 120, 220))
            gradient.setColorAt(1, QColor(60, 60, 100, 220))
        elif is_hovered:
            gradient.setColorAt(0, QColor(70, 70, 100, 200))
            gradient.setColorAt(1, QColor(50, 50, 80, 200))
        else:
            gradient.setColorAt(0, QColor(60, 60, 80, 180))
            gradient.setColorAt(1, QColor(40, 40, 60, 180))

        painter.setBrush(QBrush(gradient))

        # Border
        border_color = QColor(mol.get('color', '#4FC3F7'))
        if is_selected:
            border_color.setAlpha(255)
            painter.setPen(QPen(border_color, 3))
        elif is_hovered:
            border_color.setAlpha(200)
            painter.setPen(QPen(border_color, 2))
        else:
            border_color.setAlpha(150)
            painter.setPen(QPen(border_color, 1))

        painter.drawRoundedRect(card_rect, 10, 10)

        # Draw molecule structure visualization
        self._draw_molecule_structure(painter, mol, x + width/2, y + 50, min(width, height) * 0.25)

        # Draw text info
        self._draw_molecule_info(painter, mol, x, y, width, height)

    def _draw_molecule_structure(self, painter, mol, cx, cy, radius):
        """Draw a simplified molecular structure visualization"""
        composition = mol.get('Composition', [])
        bonds = mol.get('Bonds', [])

        if not composition:
            return

        # Calculate atom positions based on geometry
        geometry = mol.get('geometry', 'Linear')
        atom_positions = self._calculate_atom_positions(composition, geometry, cx, cy, radius)

        # Draw bonds first
        painter.setPen(QPen(QColor(200, 200, 200, 150), 2))
        for bond in bonds:
            bond_type = bond.get('Type', 'Single')
            # For simplicity, draw lines between center and atoms
            if bond_type == 'Double':
                painter.setPen(QPen(QColor(100, 150, 255, 180), 3))
            elif bond_type == 'Triple':
                painter.setPen(QPen(QColor(150, 100, 255, 180), 4))
            else:
                painter.setPen(QPen(QColor(200, 200, 200, 150), 2))

        # Draw atoms
        for atom_info in atom_positions:
            ax, ay = atom_info['x'], atom_info['y']
            element = atom_info['element']
            atom_radius = atom_info['radius']

            # Get element color
            color = QColor(get_element_color(element))

            # Draw atom glow
            glow_gradient = QRadialGradient(ax, ay, atom_radius * 1.5)
            glow_color = QColor(color)
            glow_color.setAlpha(80)
            glow_gradient.setColorAt(0, glow_color)
            glow_color.setAlpha(0)
            glow_gradient.setColorAt(1, glow_color)
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(ax, ay), atom_radius * 1.5, atom_radius * 1.5)

            # Draw atom
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawEllipse(QPointF(ax, ay), atom_radius, atom_radius)

            # Draw element symbol
            painter.setPen(QPen(QColor(0, 0, 0) if color.lightness() > 128 else QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", int(atom_radius * 0.8), QFont.Weight.Bold))
            text_rect = QRectF(ax - atom_radius, ay - atom_radius, atom_radius * 2, atom_radius * 2)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, element)

    def _calculate_atom_positions(self, composition, geometry, cx, cy, radius):
        """Calculate positions for atoms based on molecular geometry with 3D rotation"""
        positions_3d = []
        total_atoms = sum(c.get('Count', 1) for c in composition)

        if total_atoms == 0:
            return []

        # Generate initial 3D positions based on geometry
        atom_index = 0
        for comp in composition:
            element = comp.get('Element', '?')
            count = comp.get('Count', 1)

            # Size based on element (rough approximation)
            base_radius = 12
            if element in ['C', 'N', 'O', 'S']:
                base_radius = 14
            elif element in ['H']:
                base_radius = 8
            elif element in ['Cl', 'Br', 'I']:
                base_radius = 16

            for i in range(count):
                if total_atoms == 1:
                    # Single atom at center
                    x, y, z = 0, 0, 0
                elif total_atoms == 2:
                    # Linear arrangement along X-axis
                    offset = radius * 0.6 * (1 if atom_index == 0 else -1)
                    x, y, z = offset, 0, 0
                elif geometry == 'Tetrahedral' and total_atoms <= 5:
                    # Tetrahedral arrangement
                    if atom_index == 0:
                        x, y, z = 0, 0, 0  # Central atom
                    else:
                        tet_angle = math.acos(-1/3)
                        idx = atom_index - 1
                        if idx == 0:
                            x, y, z = 0, 0, radius * 0.6
                        elif idx == 1:
                            x = radius * 0.6 * math.sin(tet_angle)
                            y = 0
                            z = -radius * 0.6 * math.cos(tet_angle)
                        elif idx == 2:
                            x = -radius * 0.6 * math.sin(tet_angle) * math.cos(math.pi/3)
                            y = radius * 0.6 * math.sin(tet_angle) * math.sin(math.pi/3)
                            z = -radius * 0.6 * math.cos(tet_angle)
                        else:
                            x = -radius * 0.6 * math.sin(tet_angle) * math.cos(math.pi/3)
                            y = -radius * 0.6 * math.sin(tet_angle) * math.sin(math.pi/3)
                            z = -radius * 0.6 * math.cos(tet_angle)
                elif geometry == 'Trigonal Pyramidal':
                    # Pyramidal arrangement
                    if atom_index == 0:
                        x, y, z = 0, 0, radius * 0.2
                    else:
                        a = (atom_index - 1) * 2 * math.pi / 3 - math.pi/2
                        x = radius * 0.5 * math.cos(a)
                        y = radius * 0.5 * math.sin(a)
                        z = -radius * 0.25
                elif geometry == 'Trigonal Planar':
                    # Triangle in XY plane
                    if atom_index == 0:
                        x, y, z = 0, 0, 0
                    else:
                        a = (atom_index - 1) * 2 * math.pi / 3 - math.pi/2
                        x = radius * 0.55 * math.cos(a)
                        y = radius * 0.55 * math.sin(a)
                        z = 0
                elif geometry == 'Bent':
                    # V-shape with Z variation
                    if atom_index == 0:
                        x, y, z = 0, 0, 0
                    else:
                        angle = math.radians(104.5)
                        a = -math.pi/2 + (atom_index - 1) * angle / max(total_atoms - 2, 1)
                        x = radius * 0.6 * math.cos(a)
                        y = radius * 0.6 * math.sin(a)
                        z = radius * 0.1 * (atom_index - 1.5)
                else:
                    # Default circular arrangement with Z variation
                    angle_step = 2 * math.pi / max(total_atoms, 1)
                    current_angle = atom_index * angle_step - math.pi / 2
                    x = radius * 0.7 * math.cos(current_angle)
                    y = radius * 0.7 * math.sin(current_angle)
                    z = radius * 0.15 * math.sin(atom_index * math.pi / 2)

                positions_3d.append({
                    'element': element,
                    'x': x,
                    'y': y,
                    'z': z,
                    'radius': base_radius
                })
                atom_index += 1

        # Apply 3D rotation and project to 2D
        positions = []
        for atom in positions_3d:
            x_rot, y_rot, z_rot = rotate_point_3d(
                atom['x'], atom['y'], atom['z'],
                self.pitch, self.yaw, self.roll
            )
            # Simple orthographic projection with depth-based scaling
            depth_scale = 1.0 + z_rot / (radius * 4)  # Subtle perspective
            positions.append({
                'element': atom['element'],
                'x': cx + x_rot,
                'y': cy + y_rot,
                'z': z_rot,
                'radius': atom['radius'] * max(0.7, min(1.3, depth_scale))
            })

        # Sort by Z depth (draw far atoms first)
        positions.sort(key=lambda p: p.get('z', 0))

        return positions

    def _draw_molecule_info(self, painter, mol, x, y, width, height):
        """Draw molecule text information"""
        # Formula
        formula = mol.get('formula', '')
        painter.setPen(QPen(QColor(79, 195, 247)))
        painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        formula_rect = QRectF(x, y + 90, width, 20)
        painter.drawText(formula_rect, Qt.AlignmentFlag.AlignCenter, formula)

        # Name
        name = mol.get('name', '')
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 9))
        name_rect = QRectF(x, y + 110, width, 18)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, name)

        # Properties
        painter.setPen(QPen(QColor(200, 200, 200, 180)))
        painter.setFont(QFont("Arial", 8))

        # Mass
        mass = mol.get('mass', 0)
        mass_rect = QRectF(x + 5, y + 130, width - 10, 15)
        painter.drawText(mass_rect, Qt.AlignmentFlag.AlignCenter, f"{mass:.1f} amu")

        # State indicator
        state = mol.get('state', 'Unknown')
        state_color = MoleculeState.get_color(state)
        painter.setPen(QPen(QColor(state_color), 2))
        painter.setBrush(QBrush(QColor(state_color)))
        state_x = x + width - 15
        state_y = y + 150
        painter.drawEllipse(QPointF(state_x, state_y), 5, 5)

        # Polarity indicator
        polarity = mol.get('polarity', 'Unknown')
        polarity_color = MoleculePolarity.get_color(polarity)
        painter.setPen(QPen(QColor(polarity_color), 2))
        painter.setBrush(QBrush(QColor(polarity_color)))
        polarity_x = x + 15
        painter.drawEllipse(QPointF(polarity_x, state_y), 5, 5)

    def mouseMoveEvent(self, event):
        """Handle mouse movement for panning and hover effects"""
        if self.is_panning:
            # Update pan offset
            dx = event.position().x() - self.pan_start_x
            dy = event.position().y() - self.pan_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start_x = event.position().x()
            self.pan_start_y = event.position().y()
            self.update()
        else:
            # Transform mouse position for hover detection
            x = (event.position().x() - self.pan_x) / self.zoom_level
            y = (event.position().y() - self.pan_y + self.scroll_offset_y) / self.zoom_level

            layout = self.layouts.get(self.layout_mode)
            if layout:
                mol = layout.get_molecule_at_position(x, y, self.positioned_molecules)

                if mol != self.hovered_molecule:
                    self.hovered_molecule = mol
                    if mol:
                        self.molecule_hovered.emit(mol)
                    self.update()

    def mousePressEvent(self, event):
        """Handle mouse click for selection and panning"""
        if event.button() == Qt.MouseButton.MiddleButton:
            # Middle button: start panning
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
            elif self.hovered_molecule:
                self.selected_molecule = self.hovered_molecule
                self.molecule_selected.emit(self.selected_molecule)
                # Copy molecule data to clipboard
                clipboard_text = json.dumps(self.selected_molecule, indent=2, default=str)
                QGuiApplication.clipboard().setText(clipboard_text)
                self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.LeftButton:
            if self.is_panning:
                self.is_panning = False
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event):
        """Handle scroll wheel for zooming (default) or scrolling (with Ctrl)"""
        delta = event.angleDelta().y()

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+scroll: vertical scrolling
            self.scroll_offset_y = max(0, self.scroll_offset_y - delta / 2)
        else:
            # Default scroll: zoom in/out
            if delta > 0:
                self.zoom_level = min(5.0, self.zoom_level * 1.1)  # Zoom in
            else:
                self.zoom_level = max(0.2, self.zoom_level / 1.1)  # Zoom out

        self.update()

    def reset_view(self):
        """Reset zoom and scroll to default"""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.scroll_offset_y = 0
        self.update()

    def set_zoom(self, zoom_level):
        """Set zoom level from external control (e.g., slider)

        Args:
            zoom_level: Zoom factor (0.2 to 5.0, where 1.0 is default)
        """
        self.zoom_level = max(0.2, min(5.0, zoom_level))
        self.update()

    def get_content_height(self):
        """Get the total content height for scrolling"""
        layout = self.layouts.get(self.layout_mode)
        if layout and hasattr(layout, 'get_content_height'):
            return layout.get_content_height(self.positioned_molecules)
        return self.height()

    def set_3d_mode(self, enabled):
        """Enable or disable 3D molecular structure visualization.

        Args:
            enabled: Boolean to enable/disable 3D mode
        """
        self.show_3d_structure = getattr(self, 'show_3d_structure', False)
        self.show_3d_structure = enabled
        self.update()

    def set_show_bonds(self, show):
        """Toggle bond line visualization.

        Args:
            show: Boolean to show/hide bond lines
        """
        self.show_bonds = getattr(self, 'show_bonds', True)
        self.show_bonds = show
        self.update()

    def set_show_labels(self, show):
        """Toggle atom label visualization.

        Args:
            show: Boolean to show/hide atom labels
        """
        self.show_labels = getattr(self, 'show_labels', True)
        self.show_labels = show
        self.update()

    def set_property_mapping(self, property_key, property_name):
        """Set visual property mapping for a specific visual element.

        Args:
            property_key: Visual element key (fill_color, border_color, glow_color, symbol_text_color, border_size)
            property_name: Data property name to map to the visual element
        """
        if not hasattr(self, 'property_mappings'):
            self.property_mappings = {}
        self.property_mappings[property_key] = property_name
        self.update()

    def set_property_filter_range(self, property_key, min_val, max_val):
        """Set filter range for a property. Items outside the range will be grayed out.

        Args:
            property_key: Visual element key to filter by
            min_val: Minimum value for the filter range
            max_val: Maximum value for the filter range
        """
        if not hasattr(self, 'property_filter_ranges'):
            self.property_filter_ranges = {}
        self.property_filter_ranges[property_key] = (min_val, max_val)
        self.update()

    def set_gradient_colors(self, property_key, start_color, end_color):
        """Set custom gradient colors for visual property encoding.

        Args:
            property_key: Visual element key to set gradient for
            start_color: Start color of the gradient (hex string or QColor)
            end_color: End color of the gradient (hex string or QColor)
        """
        if not hasattr(self, 'gradient_colors'):
            self.gradient_colors = {}
        self.gradient_colors[property_key] = (start_color, end_color)
        self.update()

    def set_fade_value(self, property_key, fade):
        """Set fade value for items outside the filter range.

        Args:
            property_key: Visual element key to set fade for
            fade: Fade value from 0.0 (no fade) to 1.0 (fully faded)
        """
        if not hasattr(self, 'fade_values'):
            self.fade_values = {}
        self.fade_values[property_key] = fade
        self.update()

    def set_card_size_mapping(self, property_name):
        """Set the property used for card size scaling.

        Args:
            property_name: Name of the property to map to card size
        """
        if not hasattr(self, 'card_size_property'):
            self.card_size_property = None
        self.card_size_property = property_name
        self._update_layout()
        self.update()

    def set_glow_intensity_mapping(self, property_name):
        """Set the property used for glow intensity.

        Args:
            property_name: Name of the property to map to glow intensity
        """
        if not hasattr(self, 'glow_intensity_property'):
            self.glow_intensity_property = None
        self.glow_intensity_property = property_name
        self.update()

    def set_opacity_mapping(self, property_name):
        """Set the property used for card opacity.

        Args:
            property_name: Name of the property to map to opacity
        """
        if not hasattr(self, 'opacity_property'):
            self.opacity_property = None
        self.opacity_property = property_name
        self.update()

    def get_molecule_property_value(self, mol, property_name):
        """Get a property value from a molecule, including derived properties.

        Args:
            mol: Molecule dictionary
            property_name: Name of the property to retrieve

        Returns:
            The property value or None if not found
        """
        # Handle derived properties
        if property_name == 'num_atoms':
            composition = mol.get('Composition', [])
            return sum(c.get('Count', 1) for c in composition)
        elif property_name == 'num_bonds':
            bonds = mol.get('Bonds', [])
            return len(bonds)
        elif property_name == 'bond_length_avg':
            bonds = mol.get('Bonds', [])
            if bonds:
                lengths = [b.get('Length_pm', 0) for b in bonds if b.get('Length_pm')]
                return sum(lengths) / len(lengths) if lengths else 0
            return 0
        elif property_name == 'electronegativity_diff':
            # Calculate based on molecule polarity/bond type
            polarity = mol.get('polarity', '')
            if polarity == 'Ionic':
                return 2.5
            elif polarity == 'Polar':
                return 1.5
            else:
                return 0.5

        # Map property names to JSON keys
        property_mapping = {
            'molecular_mass': ['mass', 'MolecularMass_amu', 'MolecularMass_g_mol'],
            'density': ['density', 'Density_g_cm3'],
            'melting_point': ['melting_point', 'MeltingPoint_K'],
            'boiling_point': ['boiling_point', 'BoilingPoint_K'],
            'bond_angle': ['bond_angle', 'BondAngle_deg'],
            'dipole_moment': ['dipole_moment', 'DipoleMoment_D'],
            'vapor_pressure': ['vapor_pressure', 'VaporPressure_kPa'],
            'solubility': ['solubility', 'Solubility_g_L'],
        }

        # Try mapped keys first
        if property_name in property_mapping:
            for key in property_mapping[property_name]:
                if key in mol:
                    return mol[key]

        # Try direct key lookup
        return mol.get(property_name)

    def reload_data(self):
        """Reload molecule data from files and refresh the display"""
        self.base_molecules = self.loader.load_all_molecules()
        self._update_layout()
        self.update()
