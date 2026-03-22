"""
Molecule Info Panel
Displays detailed information about selected molecules.
Supports inline editing mode for Add/Edit operations.
"""

import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame,
                                QStackedWidget)
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen, QRadialGradient, QPainterPath

from periodica.core.molecule_enums import (MolecularGeometry, BondType, MoleculePolarity,
                                  MoleculeCategory, MoleculeState, get_element_color)
from periodica.data.data_manager import DataCategory, get_data_manager
import json
from pathlib import Path


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


class MoleculeStructureWidget(QFrame):
    """Widget to display molecular structure diagram with 3D rotation support"""

    # Default geometry configurations (fallbacks when JSON data not available)
    DEFAULT_GEOMETRY_CONFIG = {
        'Bent': {'default_angle': 104.5},
        'Tetrahedral': {'default_angle': 109.47},
        'Trigonal Pyramidal': {'default_angle': 107.0},
        'Trigonal Planar': {'default_angle': 120.0},
        'Linear': {'default_angle': 180.0},
        'Octahedral': {'default_angle': 90.0},
        'Square Planar': {'default_angle': 90.0},
    }

    # Default element radii for display (in pixels) - fallback values
    DEFAULT_ELEMENT_RADII = {
        'H': 15, 'C': 22, 'N': 20, 'O': 18, 'S': 24, 'P': 23,
        'Cl': 22, 'Br': 25, 'F': 16, 'I': 28, 'Na': 26, 'K': 28
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.molecule = None
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 45, 200);
                border: 2px solid #4fc3f7;
                border-radius: 12px;
            }
        """)
        # 3D rotation angles (in degrees)
        self.pitch = 0.0
        self.yaw = 0.0
        self.roll = 0.0

        # Cache for layout config and element data
        self._layout_config = None
        self._element_radii_cache = {}

    def set_molecule(self, mol):
        """Set molecule to display"""
        self.molecule = mol
        self.update()

    def set_rotation(self, pitch, yaw, roll):
        """Set 3D rotation angles (in degrees)"""
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll
        self.update()

    def _get_layout_config(self):
        """Load and cache the layout configuration from layout_config.json"""
        if self._layout_config is None:
            try:
                config_path = Path(__file__).parent.parent / "data" / "layout_config" / "layout_config.json"
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self._layout_config = json.load(f)
                else:
                    self._layout_config = {}
            except Exception as e:
                print(f"Error loading layout config: {e}")
                self._layout_config = {}
        return self._layout_config

    def _get_geometry_defaults(self, geometry):
        """Get default configuration for a specific geometry type"""
        # First check layout_config
        config = self._get_layout_config()
        molecules_config = config.get('molecules', {})

        # Check if there are geometry-specific defaults in config
        geometry_defaults = molecules_config.get('geometry_defaults', {}).get(geometry, {})

        # Merge with class defaults
        defaults = self.DEFAULT_GEOMETRY_CONFIG.get(geometry, {'default_angle': 109.5})
        defaults.update(geometry_defaults)

        return defaults

    def _get_element_radius_from_data(self, element):
        """
        Get the atomic radius for an element from element JSON data.
        Uses covalent_radius scaled to display pixels.
        """
        if element in self._element_radii_cache:
            return self._element_radii_cache[element]

        try:
            data_manager = get_data_manager()
            element_data = data_manager.get_item(DataCategory.ELEMENTS, element)

            if element_data:
                # Use covalent_radius (in pm) scaled for display
                # Typical covalent radii: H=31, C=76, O=66, N=71
                # Scale factor to convert pm to reasonable pixel size
                covalent_radius = element_data.get('covalent_radius', 0)
                atomic_radius = element_data.get('atomic_radius', 0)

                if covalent_radius > 0:
                    # Scale covalent radius (typically 30-150 pm) to pixel range (15-30)
                    display_radius = max(12, min(30, covalent_radius * 0.25))
                    self._element_radii_cache[element] = display_radius
                    return display_radius
                elif atomic_radius > 0:
                    display_radius = max(12, min(30, atomic_radius * 0.3))
                    self._element_radii_cache[element] = display_radius
                    return display_radius
        except Exception as e:
            pass  # Fall back to defaults

        # Fall back to default
        default_radius = self.DEFAULT_ELEMENT_RADII.get(element, 20)
        self._element_radii_cache[element] = default_radius
        return default_radius

    def _get_bond_length_scale(self, molecule, radius):
        """
        Calculate a scale factor for bond lengths based on molecule's bond data.
        Returns a multiplier to convert bond lengths to display coordinates.
        """
        bonds = molecule.get('Bonds', [])
        if not bonds:
            return radius * 0.7 / 100  # Default scale

        # Get average bond length in pm
        total_length = 0
        count = 0
        for bond in bonds:
            length = bond.get('Length_pm', 0)
            if length > 0:
                total_length += length
                count += 1

        if count > 0:
            avg_length_pm = total_length / count
            # Scale so average bond appears at about 0.7 * radius
            return (radius * 0.7) / avg_length_pm

        return radius * 0.7 / 100  # Default scale

    def paintEvent(self, event):
        """Paint the molecular structure"""
        super().paintEvent(event)

        if not self.molecule:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        radius = min(self.width(), self.height()) * 0.35

        composition = self.molecule.get('Composition', [])
        bonds = self.molecule.get('Bonds', [])
        geometry = self.molecule.get('geometry', 'Linear')

        if not composition:
            painter.setPen(QPen(QColor(150, 150, 150)))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No structure data")
            painter.end()
            return

        # Calculate atom positions
        atom_positions = self._calculate_atom_positions(composition, geometry, cx, cy, radius)

        # Draw bonds
        self._draw_bonds(painter, atom_positions, bonds, cx, cy)

        # Draw atoms
        for atom in atom_positions:
            self._draw_atom(painter, atom)

        # Draw geometry label
        painter.setPen(QPen(QColor(100, 150, 200)))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(10, self.height() - 10, f"Geometry: {geometry}")

        painter.end()

    def _calculate_atom_positions(self, composition, geometry, cx, cy, radius):
        """
        Calculate atom positions based on geometry with 3D rotation support.

        Priority for position data:
        1. Use Atoms3D from molecule JSON if available (most accurate)
        2. Calculate using BondAngle_deg from molecule JSON
        3. Fall back to default geometry angles
        """
        positions_3d = []
        total_atoms = sum(c.get('Count', 1) for c in composition)

        if total_atoms == 0:
            return []

        # Try to use Atoms3D data from molecule JSON (most accurate)
        if self.molecule and 'Atoms3D' in self.molecule:
            positions_3d = self._positions_from_atoms3d(radius)
            if positions_3d:
                return self._apply_rotation_and_project(positions_3d, cx, cy, radius)

        # Get bond angle from molecule data or use defaults
        bond_angle_deg = self._get_bond_angle(geometry)
        bond_length_scale = self._get_bond_length_scale(self.molecule, radius) if self.molecule else radius * 0.7 / 100

        # Generate initial 3D positions based on geometry using JSON data
        if geometry == 'Linear':
            positions_3d = self._generate_linear_positions(composition, radius)

        elif geometry == 'Bent':
            positions_3d = self._generate_bent_positions(composition, radius, bond_angle_deg)

        elif geometry == 'Tetrahedral':
            positions_3d = self._generate_tetrahedral_positions(composition, radius, bond_angle_deg)

        elif geometry == 'Trigonal Pyramidal':
            positions_3d = self._generate_trigonal_pyramidal_positions(composition, radius, bond_angle_deg)

        elif geometry == 'Trigonal Planar':
            positions_3d = self._generate_trigonal_planar_positions(composition, radius, bond_angle_deg)

        elif geometry == 'Planar Hexagonal':
            positions_3d = self._generate_planar_hexagonal_positions(composition, radius)

        else:
            positions_3d = self._generate_default_positions(composition, radius, total_atoms)

        return self._apply_rotation_and_project(positions_3d, cx, cy, radius)

    def _get_bond_angle(self, geometry):
        """
        Get bond angle from molecule JSON data or fall back to defaults.
        Returns angle in degrees.
        """
        # First try to get from molecule's BondAngle_deg field
        if self.molecule:
            bond_angle = self.molecule.get('BondAngle_deg')
            if bond_angle is not None and bond_angle > 0:
                return bond_angle

        # Fall back to geometry defaults
        defaults = self._get_geometry_defaults(geometry)
        return defaults.get('default_angle', 109.5)

    def _positions_from_atoms3d(self, radius):
        """
        Generate position data from molecule's Atoms3D field.
        This provides the most accurate molecular geometry from pre-calculated coordinates.
        """
        atoms_3d = self.molecule.get('Atoms3D', [])
        if not atoms_3d:
            return []

        positions = []

        # Find the bounding box to scale coordinates appropriately
        xs = [a.get('x', 0) for a in atoms_3d]
        ys = [a.get('y', 0) for a in atoms_3d]
        zs = [a.get('z', 0) for a in atoms_3d]

        max_extent = max(
            max(xs) - min(xs) if xs else 1,
            max(ys) - min(ys) if ys else 1,
            max(zs) - min(zs) if zs else 1,
            0.001  # Avoid division by zero
        )

        # Scale factor to fit in display radius
        scale = (radius * 0.7) / max(max_extent, 0.5)

        # Center offset
        center_x = (max(xs) + min(xs)) / 2 if xs else 0
        center_y = (max(ys) + min(ys)) / 2 if ys else 0
        center_z = (max(zs) + min(zs)) / 2 if zs else 0

        for atom in atoms_3d:
            element = atom.get('element', '?')
            positions.append({
                'element': element,
                'x': (atom.get('x', 0) - center_x) * scale,
                'y': (atom.get('y', 0) - center_y) * scale,
                'z': (atom.get('z', 0) - center_z) * scale,
                'radius': self._get_atom_radius(element)
            })

        return positions

    def _generate_linear_positions(self, composition, radius):
        """Generate positions for Linear geometry"""
        positions = []
        total_atoms = sum(c.get('Count', 1) for c in composition)
        step = radius * 1.5 / max(total_atoms - 1, 1) if total_atoms > 1 else 0
        start_x = -(total_atoms - 1) * step / 2
        atom_idx = 0

        for comp in composition:
            element = comp.get('Element', '?')
            count = comp.get('Count', 1)
            for i in range(count):
                positions.append({
                    'element': element,
                    'x': start_x + atom_idx * step,
                    'y': 0,
                    'z': 0,
                    'radius': self._get_atom_radius(element)
                })
                atom_idx += 1

        return positions

    def _generate_bent_positions(self, composition, radius, bond_angle_deg):
        """Generate positions for Bent geometry using bond angle from JSON data"""
        positions = []
        # Use the actual bond angle from data
        angle = math.radians(bond_angle_deg)

        central_atom = composition[0] if composition else {'Element': '?'}
        positions.append({
            'element': central_atom.get('Element', '?'),
            'x': 0, 'y': 0, 'z': 0,
            'radius': self._get_atom_radius(central_atom.get('Element', '?'))
        })

        if len(composition) > 1:
            peripheral = composition[1]
            count = peripheral.get('Count', 1)

            # Get bond length from molecule data if available
            bond_radius = self._get_display_bond_length(radius)

            for i in range(count):
                # Position atoms at the actual bond angle
                a = -math.pi/2 + (i - (count-1)/2) * angle / max(count-1, 1)
                positions.append({
                    'element': peripheral.get('Element', '?'),
                    'x': bond_radius * math.cos(a),
                    'y': bond_radius * math.sin(a),
                    'z': radius * 0.1 * (i - (count-1)/2),  # Slight Z offset for depth
                    'radius': self._get_atom_radius(peripheral.get('Element', '?'))
                })

        return positions

    def _generate_tetrahedral_positions(self, composition, radius, bond_angle_deg):
        """Generate positions for Tetrahedral geometry using bond angle from JSON data"""
        positions = []

        central = composition[0] if composition else {'Element': '?'}
        positions.append({
            'element': central.get('Element', '?'),
            'x': 0, 'y': 0, 'z': 0,
            'radius': self._get_atom_radius(central.get('Element', '?'))
        })

        # Use bond angle from data to calculate tetrahedral angle
        # For ideal tetrahedral, this is 109.47 degrees
        tet_angle_rad = math.radians(bond_angle_deg)
        # Calculate the angle from vertical based on bond angle
        # For tetrahedral: cos(theta) = -1/3, theta = 109.47 degrees between bonds
        # The angle from the z-axis is: arccos(1/sqrt(3)) for ideal tetrahedral
        tet_angle = math.acos(math.cos(tet_angle_rad / 2))

        bond_radius = self._get_display_bond_length(radius)
        atom_idx = 0

        for comp in composition[1:] if len(composition) > 1 else []:
            element = comp.get('Element', '?')
            count = comp.get('Count', 1)
            for i in range(count):
                if atom_idx == 0:
                    x, y, z = 0, 0, bond_radius
                elif atom_idx == 1:
                    x = bond_radius * math.sin(tet_angle)
                    y = 0
                    z = -bond_radius * math.cos(tet_angle)
                elif atom_idx == 2:
                    x = -bond_radius * math.sin(tet_angle) * math.cos(math.pi/3)
                    y = bond_radius * math.sin(tet_angle) * math.sin(math.pi/3)
                    z = -bond_radius * math.cos(tet_angle)
                else:
                    x = -bond_radius * math.sin(tet_angle) * math.cos(math.pi/3)
                    y = -bond_radius * math.sin(tet_angle) * math.sin(math.pi/3)
                    z = -bond_radius * math.cos(tet_angle)

                positions.append({
                    'element': element,
                    'x': x, 'y': y, 'z': z,
                    'radius': self._get_atom_radius(element)
                })
                atom_idx += 1

        return positions

    def _generate_trigonal_pyramidal_positions(self, composition, radius, bond_angle_deg):
        """Generate positions for Trigonal Pyramidal geometry using bond angle from JSON data"""
        positions = []

        # The bond angle determines how "flat" the pyramid is
        # Smaller angle = more pyramidal, larger angle = flatter
        angle_rad = math.radians(bond_angle_deg)

        # Calculate z-offset based on bond angle (how far up the central atom is)
        # For 107 degrees (ammonia), the central atom is above the base plane
        z_offset = radius * 0.2 * (1 - (bond_angle_deg - 90) / 30)

        central = composition[0] if composition else {'Element': '?'}
        positions.append({
            'element': central.get('Element', '?'),
            'x': 0, 'y': 0, 'z': max(0, z_offset),
            'radius': self._get_atom_radius(central.get('Element', '?'))
        })

        bond_radius = self._get_display_bond_length(radius, scale=0.55)
        atom_idx = 0

        for comp in composition[1:] if len(composition) > 1 else []:
            element = comp.get('Element', '?')
            count = comp.get('Count', 1)
            for i in range(count):
                a = atom_idx * 2 * math.pi / 3 - math.pi/2
                positions.append({
                    'element': element,
                    'x': bond_radius * math.cos(a),
                    'y': bond_radius * math.sin(a),
                    'z': -radius * 0.3,
                    'radius': self._get_atom_radius(element)
                })
                atom_idx += 1

        return positions

    def _generate_trigonal_planar_positions(self, composition, radius, bond_angle_deg):
        """Generate positions for Trigonal Planar geometry using bond angle from JSON data"""
        positions = []

        # For trigonal planar, bond angle should be 120 degrees
        # Use the actual angle from data for any variations

        central = composition[0] if composition else {'Element': '?'}
        positions.append({
            'element': central.get('Element', '?'),
            'x': 0, 'y': 0, 'z': 0,
            'radius': self._get_atom_radius(central.get('Element', '?'))
        })

        bond_radius = self._get_display_bond_length(radius, scale=0.6)
        # Convert bond angle to angular spacing
        angular_spacing = math.radians(bond_angle_deg)
        atom_idx = 0

        for comp in composition[1:] if len(composition) > 1 else []:
            count = comp.get('Count', 1)
            for j in range(count):
                a = atom_idx * angular_spacing - math.pi/2
                positions.append({
                    'element': comp.get('Element', '?'),
                    'x': bond_radius * math.cos(a),
                    'y': bond_radius * math.sin(a),
                    'z': 0,
                    'radius': self._get_atom_radius(comp.get('Element', '?'))
                })
                atom_idx += 1

        return positions

    def _generate_planar_hexagonal_positions(self, composition, radius):
        """Generate positions for Planar Hexagonal geometry (like benzene)"""
        positions = []
        atom_idx = 0

        for comp in composition:
            element = comp.get('Element', '?')
            count = comp.get('Count', 1)
            for i in range(count):
                a = atom_idx * math.pi / 3 - math.pi/2
                r = radius * 0.6 if element == 'C' else radius * 0.85
                positions.append({
                    'element': element,
                    'x': r * math.cos(a),
                    'y': r * math.sin(a),
                    'z': 0,
                    'radius': self._get_atom_radius(element)
                })
                atom_idx += 1

        return positions

    def _generate_default_positions(self, composition, radius, total_atoms):
        """Generate default circular arrangement for unknown geometries"""
        positions = []
        atom_idx = 0

        for comp in composition:
            element = comp.get('Element', '?')
            count = comp.get('Count', 1)
            for i in range(count):
                if total_atoms == 1:
                    positions.append({
                        'element': element,
                        'x': 0, 'y': 0, 'z': 0,
                        'radius': self._get_atom_radius(element)
                    })
                else:
                    a = atom_idx * 2 * math.pi / total_atoms - math.pi/2
                    positions.append({
                        'element': element,
                        'x': radius * 0.6 * math.cos(a),
                        'y': radius * 0.6 * math.sin(a),
                        'z': radius * 0.15 * math.sin(atom_idx * math.pi / 2),
                        'radius': self._get_atom_radius(element)
                    })
                atom_idx += 1

        return positions

    def _get_display_bond_length(self, radius, scale=0.7):
        """
        Get display bond length based on molecule's bond data.
        Uses BondLength_pm from Bonds array if available.
        """
        if self.molecule:
            bonds = self.molecule.get('Bonds', [])
            if bonds:
                # Get average bond length
                total_length = 0
                count = 0
                for bond in bonds:
                    length = bond.get('Length_pm', 0)
                    if length > 0:
                        total_length += length
                        count += 1

                if count > 0:
                    avg_length = total_length / count
                    # Scale from pm (typically 90-150) to display coordinates
                    # Map to radius * scale range
                    return radius * scale * (avg_length / 100)

        return radius * scale

    def _apply_rotation_and_project(self, positions_3d, cx, cy, radius):
        """Apply 3D rotation and project to 2D screen coordinates"""
        positions = []

        for atom in positions_3d:
            x_rot, y_rot, z_rot = rotate_point_3d(
                atom['x'], atom['y'], atom['z'],
                self.pitch, self.yaw, self.roll
            )
            # Simple orthographic projection (just use x, y)
            # Add depth-based scaling for perspective effect
            depth_scale = 1.0 + z_rot / (radius * 4)  # Subtle perspective
            positions.append({
                'element': atom['element'],
                'x': cx + x_rot,
                'y': cy + y_rot,
                'z': z_rot,  # Keep Z for depth sorting
                'radius': atom['radius'] * max(0.6, min(1.4, depth_scale)),
                'depth_scale': depth_scale
            })

        # Sort by Z depth (draw far atoms first)
        positions.sort(key=lambda p: p.get('z', 0))

        return positions

    def _get_atom_radius(self, element):
        """
        Get display radius for an element.

        Priority:
        1. Cached value (from previous lookup)
        2. Element data from JSON (covalent_radius or atomic_radius)
        3. Default hardcoded values
        """
        return self._get_element_radius_from_data(element)

    def _draw_bonds(self, painter, positions, bonds, cx, cy):
        """Draw bonds between atoms"""
        if len(positions) < 2:
            return

        # Draw lines from center to all peripheral atoms (simplified)
        if len(positions) > 1:
            center = positions[0]
            for atom in positions[1:]:
                # Determine bond type (simplified)
                painter.setPen(QPen(QColor(180, 180, 180), 3))
                painter.drawLine(
                    QPointF(center['x'], center['y']),
                    QPointF(atom['x'], atom['y'])
                )

    def _draw_atom(self, painter, atom):
        """Draw a single atom"""
        x, y = atom['x'], atom['y']
        r = atom['radius']
        element = atom['element']

        color = QColor(get_element_color(element))

        # Glow effect
        glow = QRadialGradient(x, y, r * 1.8)
        glow_color = QColor(color)
        glow_color.setAlpha(60)
        glow.setColorAt(0, glow_color)
        glow_color.setAlpha(0)
        glow.setColorAt(1, glow_color)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(x, y), r * 1.8, r * 1.8)

        # Atom sphere
        gradient = QRadialGradient(x - r * 0.3, y - r * 0.3, r * 1.5)
        gradient.setColorAt(0, color.lighter(140))
        gradient.setColorAt(0.5, color)
        gradient.setColorAt(1, color.darker(130))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(color.darker(150), 1))
        painter.drawEllipse(QPointF(x, y), r, r)

        # Element symbol
        text_color = QColor(0, 0, 0) if color.lightness() > 128 else QColor(255, 255, 255)
        painter.setPen(QPen(text_color))
        painter.setFont(QFont("Arial", int(r * 0.7), QFont.Weight.Bold))
        painter.drawText(QPointF(x - r * 0.4, y + r * 0.3), element)


class MoleculeInfoPanel(QWidget):
    """Panel displaying detailed molecule information with inline editing support"""

    # Signals for data management
    data_saved = Signal(dict)
    edit_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.molecule = None
        self._editor = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for switching between display and edit modes
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Display mode widget
        self.display_widget = QWidget()
        display_layout = QVBoxLayout(self.display_widget)
        display_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Molecule Analysis")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        display_layout.addWidget(title)

        # Structure widget
        self.structure_widget = MoleculeStructureWidget()
        display_layout.addWidget(self.structure_widget)

        # Info text
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background: rgba(25, 25, 45, 200);
                color: white;
                border: 2px solid #4fc3f7;
                border-radius: 12px;
                padding: 15px;
                font-size: 13px;
            }
        """)
        display_layout.addWidget(self.info_text)

        self.stack.addWidget(self.display_widget)
        self.show_default()

    def start_add(self, template_data=None):
        """Start add mode with inline editor"""
        from periodica_app.ui.inline_editor import InlineDataEditor

        if self._editor is None:
            self._editor = InlineDataEditor()
            self._editor.data_saved.connect(self._on_editor_saved)
            self._editor.edit_cancelled.connect(self._on_editor_cancelled)
            self.stack.addWidget(self._editor)

        self._editor.start_add(DataCategory.MOLECULES, template_data)
        self.stack.setCurrentWidget(self._editor)

    def start_edit(self, data):
        """Start edit mode with inline editor"""
        from periodica_app.ui.inline_editor import InlineDataEditor

        if self._editor is None:
            self._editor = InlineDataEditor()
            self._editor.data_saved.connect(self._on_editor_saved)
            self._editor.edit_cancelled.connect(self._on_editor_cancelled)
            self.stack.addWidget(self._editor)

        self._editor.start_edit(DataCategory.MOLECULES, data)
        self.stack.setCurrentWidget(self._editor)

    def _on_editor_saved(self, data):
        """Handle save from editor"""
        self.stack.setCurrentWidget(self.display_widget)
        self.data_saved.emit(data)

    def _on_editor_cancelled(self):
        """Handle cancel from editor"""
        self.stack.setCurrentWidget(self.display_widget)
        self.edit_cancelled.emit()

    def show_default(self):
        """Show default message"""
        self.structure_widget.set_molecule(None)
        self.info_text.setHtml("""
            <h3 style='color: #4fc3f7;'>Click any molecule to view:</h3>
            <ul>
                <li><b>Molecular Structure</b></li>
                <li><b>Bond Information</b></li>
                <li><b>Physical Properties</b></li>
                <li><b>Chemical Properties</b></li>
                <li><b>Applications</b></li>
            </ul>
            <p style='background: rgba(100,200,255,0.15); padding: 10px; border-radius: 5px;'>
            <b>Tip:</b> Use the control panel to filter molecules by category,
            polarity, or physical state.
            </p>
        """)

    def update_molecule(self, mol):
        """Update panel with molecule data"""
        if not mol:
            self.show_default()
            return

        self.molecule = mol
        self.structure_widget.set_molecule(mol)

        # Build HTML content
        name = mol.get('Name', 'Unknown')
        formula = mol.get('Formula', '')
        mass = mol.get('mass', 0)
        geometry = mol.get('geometry', 'Unknown')
        bond_type = mol.get('bond_type', 'Unknown')
        polarity = mol.get('polarity', 'Unknown')
        state = mol.get('state', 'Unknown')
        melting = mol.get('melting_point', 0)
        boiling = mol.get('boiling_point', 0)
        density = mol.get('density', 0)
        dipole = mol.get('dipole_moment', 0)
        bond_angle = mol.get('bond_angle', 0)
        applications = mol.get('Applications', [])
        iupac = mol.get('IUPAC_Name', '')
        category = mol.get('category', 'Unknown')

        # Get colors
        geometry_color = MolecularGeometry.get_color(geometry)
        polarity_color = MoleculePolarity.get_color(polarity)
        category_color = MoleculeCategory.get_color(category)
        state_color = MoleculeState.get_color(state)

        # Build composition text
        composition = mol.get('Composition', [])
        comp_text = ", ".join([f"{c['Element']}: {c['Count']}" for c in composition])

        # Build bonds text
        bonds = mol.get('Bonds', [])
        unique_bonds = set()
        for b in bonds:
            unique_bonds.add(f"{b['From']}-{b['To']} ({b['Type']})")
        bonds_text = ", ".join(list(unique_bonds)[:3])
        if len(unique_bonds) > 3:
            bonds_text += f" +{len(unique_bonds)-3} more"

        apps_html = ""
        if applications:
            apps_html = "<h3 style='color: #4fc3f7; margin-top: 15px;'>Applications:</h3><ul>"
            for app in applications[:5]:
                apps_html += f"<li>{app}</li>"
            apps_html += "</ul>"

        html = f"""
            <h2 style='color: #4fc3f7;'>{name}</h2>
            <div style='font-size: 18px; font-weight: bold; color: white;'>{formula}</div>
            <div style='color: #aaa; font-size: 10px;'>IUPAC: {iupac}</div>
            <hr style='border-color: #4fc3f7;'>

            <h3 style='color: #4fc3f7;'>Molecular Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Molecular Mass:</b></td>
                    <td><b style='color: #00ff88;'>{mass:.2f}</b> g/mol</td>
                </tr>
                <tr>
                    <td><b>Geometry:</b></td>
                    <td><span style='background: {geometry_color}; padding: 2px 8px;
                        border-radius: 4px; color: black;'>{geometry}</span></td>
                </tr>
                <tr>
                    <td><b>Bond Type:</b></td>
                    <td><b style='color: #ff8800;'>{bond_type}</b></td>
                </tr>
                <tr>
                    <td><b>Bond Angle:</b></td>
                    <td>{bond_angle:.1f}°</td>
                </tr>
                <tr>
                    <td><b>Polarity:</b></td>
                    <td><span style='background: {polarity_color}; padding: 2px 8px;
                        border-radius: 4px;'>{polarity}</span></td>
                </tr>
                <tr>
                    <td><b>Dipole Moment:</b></td>
                    <td>{dipole:.2f} D</td>
                </tr>
            </table>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Physical Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>State at STP:</b></td>
                    <td><span style='background: {state_color}; padding: 2px 8px;
                        border-radius: 4px;'>{state}</span></td>
                </tr>
                <tr>
                    <td><b>Melting Point:</b></td>
                    <td><b style='color: #00ff88;'>{melting:.1f} K</b> ({melting - 273.15:.1f}°C)</td>
                </tr>
                <tr>
                    <td><b>Boiling Point:</b></td>
                    <td><b style='color: #00ff88;'>{boiling:.1f} K</b> ({boiling - 273.15:.1f}°C)</td>
                </tr>
                <tr>
                    <td><b>Density:</b></td>
                    <td>{density:.4f} g/cm³</td>
                </tr>
            </table>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Composition:</h3>
            <div style='color: white;'>{comp_text}</div>

            <h3 style='color: #4fc3f7; margin-top: 10px;'>Bonds:</h3>
            <div style='color: white; font-size: 11px;'>{bonds_text}</div>

            {apps_html}

            <div style='background: rgba(100,200,255,0.15); padding: 12px; border-radius: 8px;
                border-left: 4px solid {category_color}; margin-top: 15px;'>
                <p style='margin: 0;'><b>Category:</b> {category}</p>
            </div>
        """
        self.info_text.setHtml(html)
