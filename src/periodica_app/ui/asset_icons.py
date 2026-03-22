"""
Asset Icon Renderer for generating visual icons for different asset types.

This module provides a reusable class that generates icons programmatically using
QPainter for displaying in table card widgets across all asset types in the
Periodics application.
"""

from typing import Any, Dict, Optional
import math

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap,
    QRadialGradient, QLinearGradient, QPainterPath, QPolygonF
)

from periodica_app.ui.theme_constants import (
    ACCENT_ATOMS, ACCENT_QUARKS, ACCENT_SUBATOMIC, ACCENT_MOLECULES, ACCENT_ALLOYS,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_INFO,
    BG_DARK, BG_PANEL
)


class AssetIconRenderer:
    """
    Generates visual icons for different asset types using QPainter.

    All icons are generated programmatically without external image files.
    Each asset type has a distinct visual representation that reflects its
    physical or chemical nature.
    """

    # Asset type constants
    ASSET_ELEMENTS = "elements"
    ASSET_QUARKS = "quarks"
    ASSET_SUBATOMIC = "subatomic"
    ASSET_MOLECULES = "molecules"
    ASSET_MATERIALS = "materials"
    ASSET_ALLOYS = "alloys"
    ASSET_AMINO_ACIDS = "amino_acids"
    ASSET_PROTEINS = "proteins"
    ASSET_NUCLEIC_ACIDS = "nucleic_acids"
    ASSET_CELL_COMPONENTS = "cell_components"
    ASSET_CELLS = "cells"
    ASSET_BIOMATERIALS = "biomaterials"

    # Asset type accent colors
    ASSET_COLORS = {
        ASSET_ELEMENTS: ACCENT_ATOMS,
        ASSET_QUARKS: ACCENT_QUARKS,
        ASSET_SUBATOMIC: ACCENT_SUBATOMIC,
        ASSET_MOLECULES: ACCENT_MOLECULES,
        ASSET_MATERIALS: "#8d6e63",       # Brown for materials
        ASSET_ALLOYS: ACCENT_ALLOYS,
        ASSET_AMINO_ACIDS: "#26c6da",     # Cyan for amino acids
        ASSET_PROTEINS: "#7e57c2",        # Deep purple for proteins
        ASSET_NUCLEIC_ACIDS: "#ec407a",   # Pink for nucleic acids
        ASSET_CELL_COMPONENTS: "#9ccc65", # Light green for cell components
        ASSET_CELLS: "#5c6bc0",           # Indigo for cells
        ASSET_BIOMATERIALS: "#ff8a65",    # Deep orange for biomaterials
    }

    # Quark colors (from subatomic_enums.py QuarkType)
    QUARK_COLORS = {
        'u': (255, 100, 100),        # Up - Red
        'd': (100, 100, 255),        # Down - Blue
        's': (100, 255, 100),        # Strange - Green
        'c': (255, 200, 100),        # Charm - Orange
        'b': (200, 100, 255),        # Bottom - Purple
        't': (255, 255, 100),        # Top - Yellow
    }

    # Element block colors
    BLOCK_COLORS = {
        's': QColor(255, 100, 100),   # Red
        'p': QColor(100, 200, 100),   # Green
        'd': QColor(100, 150, 255),   # Blue
        'f': QColor(255, 200, 100),   # Orange/Gold
    }

    # Cell component organelle colors
    ORGANELLE_COLORS = {
        'nucleus': QColor(120, 80, 160),
        'mitochondria': QColor(200, 100, 80),
        'endoplasmic_reticulum': QColor(100, 150, 200),
        'golgi': QColor(200, 180, 100),
        'ribosome': QColor(80, 80, 80),
        'lysosome': QColor(180, 80, 180),
        'chloroplast': QColor(80, 180, 80),
        'vacuole': QColor(100, 180, 220),
    }

    def __init__(self):
        """Initialize the icon renderer."""
        pass

    def render_icon(self, asset_type: str, data: Dict, size: int = 64) -> QPixmap:
        """
        Generate a visual icon for the specified asset type.

        Args:
            asset_type: One of the 12 asset type constants
            data: Dictionary containing asset-specific data for rendering
            size: Icon size in pixels (default 64)

        Returns:
            QPixmap containing the rendered icon
        """
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dispatch to appropriate renderer
        renderer_map = {
            self.ASSET_ELEMENTS: self._render_element_icon,
            self.ASSET_QUARKS: self._render_quark_icon,
            self.ASSET_SUBATOMIC: self._render_subatomic_icon,
            self.ASSET_MOLECULES: self._render_molecule_icon,
            self.ASSET_MATERIALS: self._render_material_icon,
            self.ASSET_ALLOYS: self._render_alloy_icon,
            self.ASSET_AMINO_ACIDS: self._render_amino_acid_icon,
            self.ASSET_PROTEINS: self._render_protein_icon,
            self.ASSET_NUCLEIC_ACIDS: self._render_nucleic_acid_icon,
            self.ASSET_CELL_COMPONENTS: self._render_cell_component_icon,
            self.ASSET_CELLS: self._render_cell_icon,
            self.ASSET_BIOMATERIALS: self._render_biomaterial_icon,
        }

        renderer = renderer_map.get(asset_type.lower())
        if renderer:
            renderer(painter, data, size)
        else:
            self._render_default_icon(painter, data, size)

        painter.end()
        return pixmap

    def get_color_for_property(self, asset_type: str, property_name: str, value: Any) -> QColor:
        """
        Get a color appropriate for visualizing a property value.

        Args:
            asset_type: The asset type context
            property_name: Name of the property
            value: The property value

        Returns:
            QColor for the property visualization
        """
        # Element properties
        if asset_type == self.ASSET_ELEMENTS:
            if property_name == "block":
                return self.BLOCK_COLORS.get(str(value).lower(), QColor(150, 150, 150))
            elif property_name == "atomic_number":
                # Rainbow gradient based on atomic number
                hue = int((float(value) / 118.0) * 360) % 360
                return QColor.fromHsv(hue, 200, 230)
            elif property_name in ("electronegativity", "ionization"):
                # Gradient from blue (low) to red (high)
                t = min(1.0, max(0.0, float(value) / 4.0))  # Normalize to 0-1
                return QColor(int(255 * t), int(100 * (1 - t)), int(255 * (1 - t)))

        # Quark properties
        elif asset_type == self.ASSET_QUARKS:
            if property_name == "type" or property_name == "quark_type":
                quark_key = str(value).lower()[0] if value else 'u'
                rgb = self.QUARK_COLORS.get(quark_key, (150, 150, 150))
                return QColor(rgb[0], rgb[1], rgb[2])
            elif property_name == "charge":
                # Positive: red, Negative: blue
                charge = float(value) if value else 0
                if charge > 0:
                    return QColor(255, 100, 100)
                elif charge < 0:
                    return QColor(100, 100, 255)
                return QColor(150, 150, 150)

        # Subatomic properties
        elif asset_type == self.ASSET_SUBATOMIC:
            if property_name == "particle_type":
                type_colors = {
                    'baryon': QColor(102, 126, 234),
                    'meson': QColor(240, 147, 251),
                    'lepton': QColor(100, 200, 150),
                    'boson': QColor(255, 200, 100),
                }
                return type_colors.get(str(value).lower(), QColor(150, 150, 150))

        # Molecule properties
        elif asset_type == self.ASSET_MOLECULES:
            if property_name == "polarity":
                polarity_colors = {
                    'polar': QColor(100, 150, 255),
                    'nonpolar': QColor(255, 200, 100),
                    'ionic': QColor(255, 100, 100),
                }
                return polarity_colors.get(str(value).lower(), QColor(150, 150, 150))

        # Material properties
        elif asset_type == self.ASSET_MATERIALS:
            if property_name == "crystal_system":
                system_colors = {
                    'cubic': QColor(100, 100, 255),
                    'hexagonal': QColor(100, 200, 100),
                    'tetragonal': QColor(200, 100, 200),
                    'orthorhombic': QColor(255, 200, 100),
                    'monoclinic': QColor(200, 150, 100),
                    'triclinic': QColor(150, 150, 200),
                }
                return system_colors.get(str(value).lower(), QColor(150, 150, 150))

        # Protein properties
        elif asset_type == self.ASSET_PROTEINS:
            if property_name == "structure":
                struct_colors = {
                    'alpha_helix': QColor(255, 100, 150),
                    'beta_sheet': QColor(100, 200, 255),
                    'coil': QColor(200, 200, 100),
                }
                return struct_colors.get(str(value).lower(), QColor(150, 150, 150))

        # Nucleic acid properties
        elif asset_type == self.ASSET_NUCLEIC_ACIDS:
            if property_name == "base":
                base_colors = {
                    'a': QColor(255, 100, 100),   # Adenine - Red
                    't': QColor(100, 255, 100),   # Thymine - Green
                    'g': QColor(100, 100, 255),   # Guanine - Blue
                    'c': QColor(255, 255, 100),   # Cytosine - Yellow
                    'u': QColor(255, 150, 50),    # Uracil - Orange
                }
                return base_colors.get(str(value).lower()[0] if value else '', QColor(150, 150, 150))

        # Cell component properties
        elif asset_type == self.ASSET_CELL_COMPONENTS:
            if property_name == "organelle_type":
                return self.ORGANELLE_COLORS.get(str(value).lower(), QColor(150, 150, 150))

        # Default: use asset type accent color
        accent = self.ASSET_COLORS.get(asset_type, ACCENT_PRIMARY)
        return QColor(accent)

    # =========================================================================
    # Individual Asset Type Renderers
    # =========================================================================

    def _render_element_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render an element icon with circular shape, atomic number, and electron shells.
        """
        center = size / 2

        # Get element data
        atomic_number = data.get('atomic_number', data.get('z', 1))
        symbol = data.get('symbol', '?')
        block = data.get('block', 's')

        # Background circle with block color
        block_color = self.BLOCK_COLORS.get(block.lower() if block else 's', QColor(100, 150, 200))

        # Draw glow effect
        glow_radius = size * 0.45
        glow = QRadialGradient(center, center, glow_radius)
        glow_color = QColor(block_color)
        glow_color.setAlpha(80)
        glow.setColorAt(0, glow_color)
        glow_color.setAlpha(0)
        glow.setColorAt(1, glow_color)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center, center), glow_radius, glow_radius)

        # Draw electron shell rings
        shells = self._get_shell_count(atomic_number)
        for i in range(shells):
            shell_radius = size * 0.2 + (i * size * 0.08)
            painter.setPen(QPen(QColor(255, 255, 255, 60 + i * 20), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(center, center), shell_radius, shell_radius)

        # Draw main circle
        main_radius = size * 0.35
        painter.setBrush(QBrush(block_color))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
        painter.drawEllipse(QPointF(center, center), main_radius, main_radius)

        # Draw atomic number at top
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", int(size * 0.12), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, size * 0.1, size, size * 0.2),
                        Qt.AlignmentFlag.AlignCenter, str(atomic_number))

        # Draw symbol in center
        font = QFont("Arial", int(size * 0.25), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, size * 0.25, size, size * 0.4),
                        Qt.AlignmentFlag.AlignCenter, symbol[:2])

    def _render_quark_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a quark icon with colored circle and charge indicator.
        """
        center = size / 2

        # Get quark data
        quark_type = data.get('type', data.get('quark_type', 'up'))
        charge = data.get('charge', 2/3)
        symbol = data.get('symbol', quark_type[0].lower() if quark_type else 'u')

        # Get quark color
        quark_key = symbol.lower() if symbol else 'u'
        rgb = self.QUARK_COLORS.get(quark_key, (150, 150, 150))
        quark_color = QColor(rgb[0], rgb[1], rgb[2])

        # Draw glow
        glow_radius = size * 0.4
        glow = QRadialGradient(center, center, glow_radius)
        glow_color = QColor(quark_color)
        glow_color.setAlpha(100)
        glow.setColorAt(0, glow_color)
        glow_color.setAlpha(0)
        glow.setColorAt(1, glow_color)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center, center), glow_radius, glow_radius)

        # Draw main quark circle
        main_radius = size * 0.3
        painter.setBrush(QBrush(quark_color))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(QPointF(center, center), main_radius, main_radius)

        # Draw symbol
        painter.setPen(QColor(0, 0, 0))
        font = QFont("Arial", int(size * 0.25), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, size * 0.25, size, size * 0.4),
                        Qt.AlignmentFlag.AlignCenter, quark_key)

        # Draw charge indicator
        charge_val = float(charge) if charge else 0
        charge_symbol = "+" if charge_val > 0 else "-" if charge_val < 0 else ""
        if charge_symbol:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", int(size * 0.18), QFont.Weight.Bold)
            painter.setFont(font)
            charge_x = size * 0.7
            charge_y = size * 0.25
            painter.drawText(QRectF(charge_x - 10, charge_y - 5, 20, 20),
                            Qt.AlignmentFlag.AlignCenter, charge_symbol)

    def _render_subatomic_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a subatomic particle icon with proton/neutron clusters and gluon bonds.
        """
        center = size / 2

        # Get particle data
        particle_type = data.get('type', data.get('particle_type', 'baryon'))
        quarks = data.get('quarks', data.get('quark_content', ['u', 'u', 'd']))
        name = data.get('name', 'proton')

        # Determine number of quarks to draw
        if isinstance(quarks, str):
            quark_list = list(quarks.replace('-', '').replace('bar', ''))[:3]
        elif isinstance(quarks, list):
            quark_list = [q[0].lower() if q else 'u' for q in quarks[:3]]
        else:
            quark_list = ['u', 'u', 'd']

        num_quarks = len(quark_list)

        # Draw gluon bonds (wavy lines between quarks)
        quark_radius = size * 0.35
        angles = [i * 2 * math.pi / num_quarks - math.pi / 2 for i in range(num_quarks)]
        quark_positions = [(center + quark_radius * 0.5 * math.cos(a),
                           center + quark_radius * 0.5 * math.sin(a)) for a in angles]

        # Draw gluon bonds as curved lines
        painter.setPen(QPen(QColor(100, 255, 100, 150), 2, Qt.PenStyle.DashLine))
        for i in range(num_quarks):
            p1 = quark_positions[i]
            p2 = quark_positions[(i + 1) % num_quarks]
            path = QPainterPath()
            path.moveTo(p1[0], p1[1])
            # Create a curved line
            ctrl_x = center + (p1[0] + p2[0] - 2 * center) * 0.2
            ctrl_y = center + (p1[1] + p2[1] - 2 * center) * 0.2
            path.quadTo(ctrl_x, ctrl_y, p2[0], p2[1])
            painter.drawPath(path)

        # Draw each quark
        quark_size = size * 0.2
        for i, (qx, qy) in enumerate(quark_positions):
            quark_key = quark_list[i] if i < len(quark_list) else 'u'
            rgb = self.QUARK_COLORS.get(quark_key, (150, 150, 150))
            quark_color = QColor(rgb[0], rgb[1], rgb[2])

            painter.setBrush(QBrush(quark_color))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawEllipse(QPointF(qx, qy), quark_size / 2, quark_size / 2)

            # Draw quark label
            painter.setPen(QColor(0, 0, 0))
            font = QFont("Arial", int(size * 0.1), QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(qx - 10, qy - 6, 20, 12),
                            Qt.AlignmentFlag.AlignCenter, quark_key)

        # Draw particle outline
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(200, 200, 200, 100), 1, Qt.PenStyle.DotLine))
        painter.drawEllipse(QPointF(center, center), quark_radius, quark_radius)

    def _render_molecule_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a molecule icon with ball-and-stick molecular structure.
        """
        center = size / 2

        # Get molecule data
        atoms = data.get('atoms', data.get('composition', ['C', 'H', 'H', 'H', 'H']))
        formula = data.get('formula', data.get('molecular_formula', 'CH4'))

        # Simplify to just show a few atoms connected
        if isinstance(atoms, str):
            # Parse formula like "CH4" -> ['C', 'H', 'H', 'H', 'H']
            atom_list = []
            for char in atoms:
                if char.isalpha():
                    atom_list.append(char.upper())
            atoms = atom_list[:5] if atom_list else ['C', 'H']
        elif isinstance(atoms, dict):
            atom_list = []
            for elem, count in atoms.items():
                atom_list.extend([elem] * min(int(count), 3))
            atoms = atom_list[:5]

        num_atoms = min(len(atoms) if isinstance(atoms, list) else 3, 5)

        # Position atoms in a simple layout
        if num_atoms == 1:
            positions = [(center, center)]
        elif num_atoms == 2:
            positions = [(center - size * 0.15, center), (center + size * 0.15, center)]
        else:
            # Central atom with surrounding atoms
            positions = [(center, center)]
            for i in range(num_atoms - 1):
                angle = i * 2 * math.pi / (num_atoms - 1) - math.pi / 2
                positions.append((center + size * 0.25 * math.cos(angle),
                                 center + size * 0.25 * math.sin(angle)))

        # Draw bonds (sticks)
        painter.setPen(QPen(QColor(180, 180, 180), 2))
        if len(positions) > 1:
            for i in range(1, len(positions)):
                painter.drawLine(QPointF(positions[0][0], positions[0][1]),
                               QPointF(positions[i][0], positions[i][1]))

        # Draw atoms (balls)
        atom_colors = {
            'C': QColor(80, 80, 80),      # Carbon - dark gray
            'H': QColor(255, 255, 255),   # Hydrogen - white
            'O': QColor(255, 100, 100),   # Oxygen - red
            'N': QColor(100, 100, 255),   # Nitrogen - blue
            'S': QColor(255, 255, 100),   # Sulfur - yellow
            'P': QColor(255, 150, 50),    # Phosphorus - orange
            'F': QColor(100, 255, 100),   # Fluorine - green
            'CL': QColor(100, 255, 100),  # Chlorine - green
            'BR': QColor(150, 50, 50),    # Bromine - dark red
        }

        atom_list = atoms if isinstance(atoms, list) else ['C', 'H', 'H', 'H']
        for i, (ax, ay) in enumerate(positions):
            atom_symbol = atom_list[i].upper() if i < len(atom_list) else 'C'
            atom_color = atom_colors.get(atom_symbol[:2], atom_colors.get(atom_symbol[0], QColor(150, 150, 150)))

            atom_radius = size * 0.12 if atom_symbol != 'H' else size * 0.08
            painter.setBrush(QBrush(atom_color))
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.drawEllipse(QPointF(ax, ay), atom_radius, atom_radius)

    def _render_material_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a material icon with crystal lattice or grain pattern.
        """
        center = size / 2

        # Get material data
        crystal_system = data.get('crystal_system', 'cubic')
        material_type = data.get('type', data.get('material_type', 'crystal'))

        # Draw lattice pattern
        lattice_color = QColor(141, 110, 99)  # Brown-ish for materials
        grid_size = size * 0.15

        # Draw grid of atoms in lattice pattern
        for row in range(4):
            for col in range(4):
                x = size * 0.2 + col * grid_size
                y = size * 0.2 + row * grid_size

                # Alternate coloring for crystal structure
                if (row + col) % 2 == 0:
                    painter.setBrush(QBrush(lattice_color))
                else:
                    painter.setBrush(QBrush(lattice_color.lighter(130)))

                painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
                atom_r = size * 0.06
                painter.drawEllipse(QPointF(x, y), atom_r, atom_r)

        # Draw connecting lines (bonds)
        painter.setPen(QPen(QColor(200, 200, 200, 80), 1))
        for row in range(4):
            for col in range(3):
                x1 = size * 0.2 + col * grid_size
                y1 = size * 0.2 + row * grid_size
                x2 = size * 0.2 + (col + 1) * grid_size
                y2 = y1
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        for row in range(3):
            for col in range(4):
                x1 = size * 0.2 + col * grid_size
                y1 = size * 0.2 + row * grid_size
                x2 = x1
                y2 = size * 0.2 + (row + 1) * grid_size
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _render_alloy_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render an alloy icon with multi-colored grain boundaries.
        """
        center = size / 2

        # Get alloy data
        components = data.get('components', data.get('composition', {'Fe': 0.7, 'C': 0.3}))

        # Define colors for different metals
        metal_colors = [
            QColor(180, 180, 200),  # Silver/Steel
            QColor(255, 200, 100),  # Gold/Brass
            QColor(200, 120, 80),   # Copper
            QColor(100, 100, 100),  # Iron
        ]

        # Draw irregular grain polygons
        grain_centers = [
            (size * 0.25, size * 0.3),
            (size * 0.7, size * 0.25),
            (size * 0.5, size * 0.55),
            (size * 0.3, size * 0.75),
            (size * 0.75, size * 0.7),
        ]

        for i, (gx, gy) in enumerate(grain_centers):
            color = metal_colors[i % len(metal_colors)]

            # Draw irregular polygon for grain
            num_sides = 5 + (i % 3)
            points = []
            grain_radius = size * 0.15 + (i % 2) * size * 0.05
            for j in range(num_sides):
                angle = j * 2 * math.pi / num_sides + i * 0.5
                r = grain_radius * (0.8 + 0.2 * ((j + i) % 3) / 2)
                points.append(QPointF(gx + r * math.cos(angle), gy + r * math.sin(angle)))

            polygon = QPolygonF(points)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawPolygon(polygon)

        # Draw grain boundary lines
        painter.setPen(QPen(QColor(40, 40, 40), 2))
        for i in range(len(grain_centers)):
            for j in range(i + 1, len(grain_centers)):
                if abs(grain_centers[i][0] - grain_centers[j][0]) < size * 0.4:
                    if abs(grain_centers[i][1] - grain_centers[j][1]) < size * 0.4:
                        mid_x = (grain_centers[i][0] + grain_centers[j][0]) / 2
                        mid_y = (grain_centers[i][1] + grain_centers[j][1]) / 2
                        painter.drawPoint(QPointF(mid_x, mid_y))

    def _render_amino_acid_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render an amino acid icon with side chain chemical structure outline.
        """
        center = size / 2

        # Get amino acid data
        name = data.get('name', data.get('abbreviation', 'Ala'))
        polarity = data.get('polarity', 'nonpolar')

        # Draw backbone (N-C-C pattern)
        backbone_color = QColor(38, 198, 218)  # Cyan

        # Central alpha carbon
        painter.setBrush(QBrush(QColor(80, 80, 80)))
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawEllipse(QPointF(center, center), size * 0.1, size * 0.1)

        # Amino group (N)
        n_pos = (center - size * 0.25, center)
        painter.setBrush(QBrush(QColor(100, 100, 255)))
        painter.drawEllipse(QPointF(n_pos[0], n_pos[1]), size * 0.08, size * 0.08)

        # Carboxyl group (C=O)
        c_pos = (center + size * 0.25, center)
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        painter.drawEllipse(QPointF(c_pos[0], c_pos[1]), size * 0.08, size * 0.08)

        # O atom of carboxyl
        o_pos = (center + size * 0.35, center - size * 0.15)
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        painter.drawEllipse(QPointF(o_pos[0], o_pos[1]), size * 0.06, size * 0.06)

        # Draw bonds
        painter.setPen(QPen(QColor(180, 180, 180), 2))
        painter.drawLine(QPointF(n_pos[0] + size * 0.08, n_pos[1]),
                        QPointF(center - size * 0.1, center))
        painter.drawLine(QPointF(center + size * 0.1, center),
                        QPointF(c_pos[0] - size * 0.08, c_pos[1]))
        painter.drawLine(QPointF(c_pos[0], c_pos[1] - size * 0.08),
                        QPointF(o_pos[0] - size * 0.06, o_pos[1] + size * 0.06))

        # Draw side chain (R group) - simplified
        r_pos = (center, center + size * 0.3)
        painter.setPen(QPen(QColor(180, 180, 180), 2))
        painter.drawLine(QPointF(center, center + size * 0.1), QPointF(r_pos[0], r_pos[1] - size * 0.05))

        # R group circle with color based on polarity
        if polarity == 'polar':
            r_color = QColor(100, 200, 255)
        elif polarity == 'charged':
            r_color = QColor(255, 150, 150)
        else:
            r_color = QColor(200, 200, 150)

        painter.setBrush(QBrush(r_color))
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawEllipse(QPointF(r_pos[0], r_pos[1]), size * 0.1, size * 0.1)

        # Label
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", int(size * 0.08))
        painter.setFont(font)
        painter.drawText(QRectF(r_pos[0] - 10, r_pos[1] - 5, 20, 10),
                        Qt.AlignmentFlag.AlignCenter, "R")

    def _render_protein_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a protein icon with alpha helix or beta sheet ribbons.
        """
        center = size / 2

        # Get protein data
        structure = data.get('secondary_structure', data.get('structure', 'alpha_helix'))

        if 'beta' in str(structure).lower() or 'sheet' in str(structure).lower():
            # Draw beta sheet (zigzag arrows)
            self._draw_beta_sheet(painter, size)
        else:
            # Draw alpha helix (spiral ribbon)
            self._draw_alpha_helix(painter, size)

    def _draw_alpha_helix(self, painter: QPainter, size: int):
        """Draw an alpha helix spiral."""
        center = size / 2
        helix_color = QColor(255, 100, 150)

        # Draw spiral ribbon
        num_turns = 3
        points_per_turn = 20
        total_points = num_turns * points_per_turn

        path = QPainterPath()
        ribbon_width = size * 0.1

        for i in range(total_points):
            t = i / total_points
            angle = t * num_turns * 2 * math.pi

            # Helix parameters
            x = center + size * 0.25 * math.cos(angle)
            y = size * 0.15 + t * size * 0.7

            if i == 0:
                path.moveTo(x - ribbon_width / 2, y)
            else:
                path.lineTo(x - ribbon_width / 2, y)

        # Draw back of ribbon
        for i in range(total_points - 1, -1, -1):
            t = i / total_points
            angle = t * num_turns * 2 * math.pi
            x = center + size * 0.25 * math.cos(angle)
            y = size * 0.15 + t * size * 0.7
            path.lineTo(x + ribbon_width / 2, y)

        path.closeSubpath()

        # Create gradient
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, helix_color)
        gradient.setColorAt(1, helix_color.darker(130))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(helix_color.darker(150), 1))
        painter.drawPath(path)

    def _draw_beta_sheet(self, painter: QPainter, size: int):
        """Draw beta sheet arrows."""
        sheet_color = QColor(100, 200, 255)

        # Draw multiple arrow strands
        num_strands = 3
        strand_width = size * 0.15
        strand_spacing = size * 0.2

        for s in range(num_strands):
            x = size * 0.25 + s * strand_spacing

            # Draw arrow body
            painter.setBrush(QBrush(sheet_color if s % 2 == 0 else sheet_color.darker(120)))
            painter.setPen(QPen(sheet_color.darker(150), 1))

            # Arrow pointing down or up alternating
            if s % 2 == 0:
                # Down arrow
                points = [
                    QPointF(x, size * 0.15),
                    QPointF(x + strand_width, size * 0.15),
                    QPointF(x + strand_width, size * 0.6),
                    QPointF(x + strand_width * 1.3, size * 0.6),
                    QPointF(x + strand_width / 2, size * 0.85),
                    QPointF(x - strand_width * 0.3, size * 0.6),
                    QPointF(x, size * 0.6),
                ]
            else:
                # Up arrow
                points = [
                    QPointF(x + strand_width / 2, size * 0.15),
                    QPointF(x + strand_width * 1.3, size * 0.4),
                    QPointF(x + strand_width, size * 0.4),
                    QPointF(x + strand_width, size * 0.85),
                    QPointF(x, size * 0.85),
                    QPointF(x, size * 0.4),
                    QPointF(x - strand_width * 0.3, size * 0.4),
                ]

            polygon = QPolygonF(points)
            painter.drawPolygon(polygon)

    def _render_nucleic_acid_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a nucleic acid icon with double helix or RNA hairpin.
        """
        center = size / 2

        # Get nucleic acid data
        acid_type = data.get('type', data.get('nucleic_acid_type', 'dna'))

        if 'rna' in str(acid_type).lower():
            self._draw_rna_hairpin(painter, size)
        else:
            self._draw_double_helix(painter, size)

    def _draw_double_helix(self, painter: QPainter, size: int):
        """Draw DNA double helix."""
        center = size / 2

        # Helix parameters
        num_turns = 2
        points_per_turn = 15
        total_points = num_turns * points_per_turn
        helix_width = size * 0.25

        # Base pair colors
        base_colors = [
            (QColor(255, 100, 100), QColor(100, 255, 100)),  # A-T
            (QColor(100, 100, 255), QColor(255, 255, 100)),  # G-C
        ]

        # Draw base pairs and backbone
        for i in range(total_points):
            t = i / total_points
            angle = t * num_turns * 2 * math.pi
            y = size * 0.1 + t * size * 0.8

            # Two strands
            x1 = center + helix_width * math.sin(angle)
            x2 = center - helix_width * math.sin(angle)

            # Draw base pair line
            if i % 3 == 0:
                colors = base_colors[i % 2]
                painter.setPen(QPen(QColor(180, 180, 180), 2))
                painter.drawLine(QPointF(x1, y), QPointF(x2, y))

                # Draw bases
                painter.setBrush(QBrush(colors[0]))
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawEllipse(QPointF(x1, y), size * 0.04, size * 0.04)

                painter.setBrush(QBrush(colors[1]))
                painter.drawEllipse(QPointF(x2, y), size * 0.04, size * 0.04)

        # Draw backbone strands
        path1 = QPainterPath()
        path2 = QPainterPath()

        for i in range(total_points):
            t = i / total_points
            angle = t * num_turns * 2 * math.pi
            y = size * 0.1 + t * size * 0.8
            x1 = center + helix_width * math.sin(angle)
            x2 = center - helix_width * math.sin(angle)

            if i == 0:
                path1.moveTo(x1, y)
                path2.moveTo(x2, y)
            else:
                path1.lineTo(x1, y)
                path2.lineTo(x2, y)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(236, 64, 122), 2))  # Pink strand
        painter.drawPath(path1)
        painter.setPen(QPen(QColor(100, 180, 255), 2))  # Blue strand
        painter.drawPath(path2)

    def _draw_rna_hairpin(self, painter: QPainter, size: int):
        """Draw RNA hairpin structure."""
        center = size / 2

        # Draw stem
        stem_width = size * 0.15
        stem_height = size * 0.5

        painter.setPen(QPen(QColor(255, 150, 50), 2))
        painter.drawLine(QPointF(center - stem_width, size * 0.8),
                        QPointF(center - stem_width, size * 0.3))
        painter.drawLine(QPointF(center + stem_width, size * 0.8),
                        QPointF(center + stem_width, size * 0.3))

        # Draw loop at top
        path = QPainterPath()
        path.moveTo(center - stem_width, size * 0.3)
        path.cubicTo(center - stem_width * 2, size * 0.1,
                    center + stem_width * 2, size * 0.1,
                    center + stem_width, size * 0.3)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 150, 50), 2))
        painter.drawPath(path)

        # Draw base pairs in stem
        for i in range(4):
            y = size * 0.4 + i * size * 0.1
            painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(center - stem_width + 5, y),
                            QPointF(center + stem_width - 5, y))

    def _render_cell_component_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a cell component icon with organelle shapes.
        """
        center = size / 2

        # Get component data
        organelle_type = data.get('type', data.get('organelle_type', 'nucleus'))

        organelle_renderers = {
            'nucleus': self._draw_nucleus,
            'mitochondria': self._draw_mitochondria,
            'endoplasmic_reticulum': self._draw_er,
            'golgi': self._draw_golgi,
            'ribosome': self._draw_ribosome,
            'chloroplast': self._draw_chloroplast,
        }

        renderer = organelle_renderers.get(organelle_type.lower(), self._draw_nucleus)
        renderer(painter, size)

    def _draw_nucleus(self, painter: QPainter, size: int):
        """Draw nucleus organelle."""
        center = size / 2

        # Outer membrane
        painter.setBrush(QBrush(QColor(120, 80, 160, 150)))
        painter.setPen(QPen(QColor(100, 60, 140), 2))
        painter.drawEllipse(QPointF(center, center), size * 0.35, size * 0.3)

        # Nucleolus
        painter.setBrush(QBrush(QColor(80, 50, 120)))
        painter.drawEllipse(QPointF(center + size * 0.05, center), size * 0.12, size * 0.1)

        # Nuclear pores (dots on membrane)
        painter.setBrush(QBrush(QColor(60, 40, 100)))
        painter.setPen(Qt.PenStyle.NoPen)
        for angle in [0, 60, 120, 180, 240, 300]:
            rad = math.radians(angle)
            px = center + size * 0.35 * math.cos(rad)
            py = center + size * 0.3 * math.sin(rad)
            painter.drawEllipse(QPointF(px, py), size * 0.03, size * 0.03)

    def _draw_mitochondria(self, painter: QPainter, size: int):
        """Draw mitochondria organelle."""
        center = size / 2

        # Outer membrane (oval)
        painter.setBrush(QBrush(QColor(200, 100, 80, 180)))
        painter.setPen(QPen(QColor(150, 70, 50), 2))
        painter.drawEllipse(QPointF(center, center), size * 0.4, size * 0.25)

        # Inner membrane folds (cristae)
        painter.setPen(QPen(QColor(150, 70, 50), 2))
        for i in range(3):
            x = center - size * 0.2 + i * size * 0.15
            path = QPainterPath()
            path.moveTo(x, center - size * 0.15)
            path.cubicTo(x + size * 0.1, center - size * 0.05,
                        x - size * 0.1, center + size * 0.05,
                        x, center + size * 0.15)
            painter.drawPath(path)

    def _draw_er(self, painter: QPainter, size: int):
        """Draw endoplasmic reticulum."""
        center = size / 2

        painter.setPen(QPen(QColor(100, 150, 200), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw wavy lines
        for i in range(4):
            y = size * 0.2 + i * size * 0.18
            path = QPainterPath()
            path.moveTo(size * 0.1, y)

            for j in range(4):
                x = size * 0.2 + j * size * 0.2
                ctrl_y = y + (size * 0.08 if j % 2 == 0 else -size * 0.08)
                path.quadTo(x, ctrl_y, x + size * 0.1, y)

            painter.drawPath(path)

    def _draw_golgi(self, painter: QPainter, size: int):
        """Draw Golgi apparatus."""
        center = size / 2

        # Draw stacked curved membranes
        for i in range(4):
            y_offset = (i - 1.5) * size * 0.12

            path = QPainterPath()
            path.moveTo(size * 0.15, center + y_offset)
            path.quadTo(center, center + y_offset - size * 0.1,
                       size * 0.85, center + y_offset)

            # Create closed shape
            path.quadTo(center, center + y_offset + size * 0.05,
                       size * 0.15, center + y_offset)

            color = QColor(200, 180, 100, 180 - i * 30)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(180, 160, 80), 1))
            painter.drawPath(path)

        # Draw vesicles
        painter.setBrush(QBrush(QColor(200, 180, 100)))
        painter.drawEllipse(QPointF(size * 0.8, center - size * 0.15), size * 0.05, size * 0.05)
        painter.drawEllipse(QPointF(size * 0.85, center + size * 0.1), size * 0.04, size * 0.04)

    def _draw_ribosome(self, painter: QPainter, size: int):
        """Draw ribosome."""
        center = size / 2

        # Large subunit
        painter.setBrush(QBrush(QColor(80, 80, 80)))
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.drawEllipse(QPointF(center, center + size * 0.05), size * 0.25, size * 0.2)

        # Small subunit
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.drawEllipse(QPointF(center, center - size * 0.15), size * 0.18, size * 0.12)

    def _draw_chloroplast(self, painter: QPainter, size: int):
        """Draw chloroplast."""
        center = size / 2

        # Outer membrane
        painter.setBrush(QBrush(QColor(80, 180, 80, 180)))
        painter.setPen(QPen(QColor(60, 140, 60), 2))
        painter.drawEllipse(QPointF(center, center), size * 0.4, size * 0.25)

        # Thylakoid stacks (grana)
        painter.setBrush(QBrush(QColor(50, 140, 50)))
        for i in range(3):
            x = center - size * 0.2 + i * size * 0.15
            for j in range(3):
                y = center - size * 0.08 + j * size * 0.06
                painter.drawEllipse(QPointF(x, y), size * 0.08, size * 0.03)

    def _render_cell_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a cell icon with membrane and organelles inside.
        """
        center = size / 2

        # Get cell data
        cell_type = data.get('type', data.get('cell_type', 'eukaryotic'))

        # Draw cell membrane
        membrane_color = QColor(92, 107, 192, 150)  # Indigo, semi-transparent

        # Outer glow
        glow = QRadialGradient(center, center, size * 0.48)
        glow_color = QColor(membrane_color)
        glow_color.setAlpha(50)
        glow.setColorAt(0.7, glow_color)
        glow_color.setAlpha(0)
        glow.setColorAt(1, glow_color)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center, center), size * 0.48, size * 0.48)

        # Cell membrane
        painter.setBrush(QBrush(membrane_color))
        painter.setPen(QPen(QColor(72, 87, 172), 2))
        painter.drawEllipse(QPointF(center, center), size * 0.42, size * 0.38)

        # Cytoplasm
        painter.setBrush(QBrush(QColor(200, 220, 240, 100)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center, center), size * 0.38, size * 0.34)

        # Draw mini organelles inside
        # Nucleus
        painter.setBrush(QBrush(QColor(120, 80, 160)))
        painter.setPen(QPen(QColor(100, 60, 140), 1))
        painter.drawEllipse(QPointF(center - size * 0.05, center), size * 0.12, size * 0.1)

        # Mitochondria (small)
        painter.setBrush(QBrush(QColor(200, 100, 80)))
        painter.setPen(QPen(QColor(150, 70, 50), 1))
        painter.drawEllipse(QPointF(center + size * 0.2, center - size * 0.1), size * 0.08, size * 0.05)
        painter.drawEllipse(QPointF(center - size * 0.2, center + size * 0.15), size * 0.07, size * 0.04)

        # Small dots for ribosomes
        painter.setBrush(QBrush(QColor(80, 80, 80)))
        painter.setPen(Qt.PenStyle.NoPen)
        for _ in range(8):
            rx = center + (size * 0.25 * (0.5 - math.cos(_ * 0.8)))
            ry = center + (size * 0.2 * (0.5 - math.sin(_ * 1.1)))
            painter.drawEllipse(QPointF(rx, ry), size * 0.02, size * 0.02)

    def _render_biomaterial_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a biomaterial icon with tissue-like fiber pattern.
        """
        center = size / 2

        # Get biomaterial data
        material_type = data.get('type', data.get('biomaterial_type', 'collagen'))

        # Background
        painter.setBrush(QBrush(QColor(255, 200, 180, 50)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center, center), size * 0.45, size * 0.45)

        # Draw fiber bundles
        fiber_color = QColor(255, 138, 101)  # Deep orange

        # Multiple wavy fiber strands
        for strand in range(5):
            path = QPainterPath()
            start_y = size * 0.15 + strand * size * 0.15
            path.moveTo(size * 0.1, start_y)

            amplitude = size * 0.03 + (strand % 2) * size * 0.02
            wavelength = size * 0.15

            for x in range(int(size * 0.1), int(size * 0.9), 5):
                y = start_y + amplitude * math.sin((x - size * 0.1) / wavelength * 2 * math.pi)
                if x == int(size * 0.1):
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            painter.setPen(QPen(fiber_color.darker(100 + strand * 10), 2))
            painter.drawPath(path)

        # Draw cross-links
        painter.setPen(QPen(QColor(200, 150, 100, 150), 1))
        for i in range(4):
            x = size * 0.2 + i * size * 0.2
            painter.drawLine(QPointF(x, size * 0.2), QPointF(x + size * 0.05, size * 0.8))

        # Draw cells embedded in matrix
        painter.setBrush(QBrush(QColor(100, 150, 200, 150)))
        painter.setPen(QPen(QColor(80, 120, 180), 1))
        painter.drawEllipse(QPointF(size * 0.3, size * 0.4), size * 0.06, size * 0.05)
        painter.drawEllipse(QPointF(size * 0.7, size * 0.6), size * 0.05, size * 0.04)

    def _render_default_icon(self, painter: QPainter, data: Dict, size: int):
        """
        Render a default icon for unknown asset types.
        """
        center = size / 2

        # Simple circle with question mark
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        painter.drawEllipse(QPointF(center, center), size * 0.35, size * 0.35)

        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", int(size * 0.3), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "?")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_shell_count(self, atomic_number: int) -> int:
        """Get the number of electron shells for an element."""
        if atomic_number <= 2:
            return 1
        elif atomic_number <= 10:
            return 2
        elif atomic_number <= 18:
            return 3
        elif atomic_number <= 36:
            return 4
        elif atomic_number <= 54:
            return 5
        elif atomic_number <= 86:
            return 6
        else:
            return 7
