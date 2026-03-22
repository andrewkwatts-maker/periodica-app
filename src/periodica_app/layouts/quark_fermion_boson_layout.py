#!/usr/bin/env python3
"""
Fermion/Boson Split Layout Renderer
Arranges particles in two hemispheres based on their spin statistics.
Fermions (spin 1/2, 3/2) on left, Bosons (spin 0, 1) on right.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QLinearGradient
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica_app.layouts.quark_base_layout import QuarkBaseLayoutRenderer
from periodica.core.quark_enums import ParticleType
from periodica.data.layout_config_loader import get_quark_config, get_layout_config


class QuarkFermionBosonLayoutRenderer(QuarkBaseLayoutRenderer):
    """
    Fermion/Boson Split layout renderer.
    - Two hemispheres: Fermions (spin 1/2, 3/2) left, Bosons (spin 0, 1) right
    - Within each hemisphere, arrange by mass
    - Color by particle type
    """

    def __init__(self, widget_width, widget_height):
        super().__init__(widget_width, widget_height)
        # Load configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')

        self.cell_size = card_size.get('default', 70) - 15

        # Store size constraints from config
        self.min_size = card_size.get('min', 45) - 5
        self.max_size = card_size.get('max', 120) - 10

    def _is_fermion(self, particle):
        """Determine if particle is a fermion based on spin"""
        spin = particle.get('Spin_hbar', 0)
        if spin is None:
            spin = 0
        # Fermions have half-integer spin (1/2, 3/2, 5/2, etc.)
        return (spin * 2) % 2 == 1

    def _is_boson(self, particle):
        """Determine if particle is a boson based on spin"""
        spin = particle.get('Spin_hbar', 0)
        if spin is None:
            spin = 0
        # Bosons have integer spin (0, 1, 2, etc.)
        return (spin * 2) % 2 == 0

    def create_layout(self, particles, **kwargs):
        """
        Create fermion/boson split layout.

        Args:
            particles: List of particle dictionaries
            **kwargs: Additional parameters

        Returns:
            List of particles with layout positions
        """
        # Get configuration values
        config = get_layout_config()
        margins = config.get_margins('quarks')
        spacing = config.get_spacing('quarks')

        # Separate fermions and bosons
        fermions = []
        bosons = []

        for p in particles:
            if self._is_fermion(p):
                fermions.append(p)
                p['spin_type'] = 'fermion'
            else:
                bosons.append(p)
                p['spin_type'] = 'boson'

        # Sort each group by mass (descending for visual hierarchy)
        fermions.sort(key=lambda p: p.get('Mass_MeVc2', 0) or 0, reverse=True)
        bosons.sort(key=lambda p: p.get('Mass_MeVc2', 0) or 0, reverse=True)

        # Calculate layout dimensions
        available_width = self.widget_width - margins.get('left', 50) - margins.get('right', 50)
        available_height = self.widget_height - margins.get('top', 100) - margins.get('bottom', 50) - 80
        hemisphere_width = (available_width - spacing.get('section', 30) * 2) / 2

        # Calculate cell size based on max group size
        max_count = max(len(fermions), len(bosons), 1)
        cols_per_hemisphere = max(2, min(5, int(math.sqrt(max_count) + 0.5)))

        self.cell_size = min(
            self.max_size,
            (hemisphere_width - 40) / cols_per_hemisphere,
            (available_height - 60) / (math.ceil(max_count / cols_per_hemisphere) + 1)
        )
        self.cell_size = max(self.min_size, self.cell_size)

        # Position fermions (left hemisphere)
        fermion_center_x = self.widget_width * 0.25
        self._position_hemisphere(fermions, fermion_center_x, hemisphere_width,
                                   available_height, 'fermion')

        # Position bosons (right hemisphere)
        boson_center_x = self.widget_width * 0.75
        self._position_hemisphere(bosons, boson_center_x, hemisphere_width,
                                   available_height, 'boson')

        return particles

    def _position_hemisphere(self, particles, center_x, width, height, hemisphere_type):
        """Position particles within a hemisphere arranged by mass"""
        if not particles:
            return

        # Get margins from config
        margins = get_layout_config().get_margins('quarks')

        n = len(particles)
        cols = max(2, min(5, int(math.sqrt(n) + 0.5)))
        rows = math.ceil(n / cols)

        # Start position (centered in hemisphere)
        start_x = center_x - (cols * self.cell_size + (cols - 1) * 8) / 2 + self.cell_size / 2
        start_y = margins.get('top', 100) + 30 + self.cell_size / 2

        # Color scheme by particle type
        type_colors = {
            ParticleType.QUARK: QColor(230, 100, 100),
            ParticleType.LEPTON: QColor(100, 180, 230),
            ParticleType.GAUGE_BOSON: QColor(230, 180, 100),
            ParticleType.SCALAR_BOSON: QColor(180, 100, 230),
            ParticleType.ANTIPARTICLE: QColor(180, 180, 180),
            ParticleType.COMPOSITE: QColor(100, 200, 150),
            ParticleType.UNKNOWN: QColor(150, 150, 150)
        }

        for i, particle in enumerate(particles):
            col = i % cols
            row = i // cols

            particle['x'] = start_x + col * (self.cell_size + 8)
            particle['y'] = start_y + row * (self.cell_size + 8)
            particle['display_size'] = self.cell_size

            # Store hemisphere info
            particle['hemisphere'] = hemisphere_type
            particle['hemisphere_center_x'] = center_x

            # Get color by particle type
            ptype = particle.get('particle_type', ParticleType.UNKNOWN)
            particle['type_color'] = type_colors.get(ptype, QColor(150, 150, 150))

    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the fermion/boson split layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Visualization state
            **kwargs: Additional parameters
        """
        passes_filter_func = kwargs.get('passes_filter_func', lambda p: True)

        # Draw hemisphere backgrounds
        self._draw_hemisphere_backgrounds(painter)

        # Draw dividing line
        self._draw_divider(painter)

        # Draw particles
        for particle in particles:
            if particle.get('x') is not None and particle.get('y') is not None:
                passes = passes_filter_func(particle)
                self.draw_particle_cell(painter, particle, table_state, passes)

        # Draw legend
        self._draw_legend(painter)

    def _draw_hemisphere_backgrounds(self, painter):
        """Draw background regions for each hemisphere"""
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')
        top_margin = margins.get('top', 100) - 20
        bottom_margin = margins.get('bottom', 50)

        # Fermion hemisphere (left) - bluish
        fermion_rect = QRectF(30, top_margin, self.widget_width / 2 - 50,
                              self.widget_height - top_margin - bottom_margin - 80)
        fermion_gradient = QLinearGradient(fermion_rect.left(), fermion_rect.top(),
                                            fermion_rect.right(), fermion_rect.top())
        fermion_gradient.setColorAt(0, QColor(100, 150, 200, 30))
        fermion_gradient.setColorAt(1, QColor(100, 150, 200, 10))
        painter.setBrush(QBrush(fermion_gradient))
        painter.setPen(QPen(QColor(100, 150, 200, 100), 2))
        painter.drawRoundedRect(fermion_rect, 15, 15)

        # Fermion label
        font = QFont('Arial', 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(100, 180, 230), 1))
        painter.drawText(QRectF(30, top_margin + 5, self.widget_width / 2 - 50, 30),
                        Qt.AlignmentFlag.AlignCenter, "FERMIONS")

        # Fermion description
        font_small = QFont('Arial', 10)
        painter.setFont(font_small)
        painter.setPen(QPen(QColor(150, 180, 200), 1))
        painter.drawText(QRectF(30, top_margin + 25, self.widget_width / 2 - 50, 20),
                        Qt.AlignmentFlag.AlignCenter, "Half-integer spin (1/2, 3/2, ...)")

        # Boson hemisphere (right) - orangish
        boson_rect = QRectF(self.widget_width / 2 + 20, top_margin,
                           self.widget_width / 2 - 50,
                           self.widget_height - top_margin - bottom_margin - 80)
        boson_gradient = QLinearGradient(boson_rect.left(), boson_rect.top(),
                                          boson_rect.right(), boson_rect.top())
        boson_gradient.setColorAt(0, QColor(200, 150, 100, 10))
        boson_gradient.setColorAt(1, QColor(200, 150, 100, 30))
        painter.setBrush(QBrush(boson_gradient))
        painter.setPen(QPen(QColor(200, 150, 100, 100), 2))
        painter.drawRoundedRect(boson_rect, 15, 15)

        # Boson label
        font = QFont('Arial', 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(230, 180, 100), 1))
        painter.drawText(QRectF(self.widget_width / 2 + 20, top_margin + 5,
                               self.widget_width / 2 - 50, 30),
                        Qt.AlignmentFlag.AlignCenter, "BOSONS")

        # Boson description
        font_small = QFont('Arial', 10)
        painter.setFont(font_small)
        painter.setPen(QPen(QColor(200, 180, 150), 1))
        painter.drawText(QRectF(self.widget_width / 2 + 20, top_margin + 25,
                               self.widget_width / 2 - 50, 20),
                        Qt.AlignmentFlag.AlignCenter, "Integer spin (0, 1, 2, ...)")

    def _draw_divider(self, painter):
        """Draw dividing line between hemispheres"""
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')

        center_x = self.widget_width / 2
        top_y = margins.get('top', 100) - 10
        bottom_y = self.widget_height - margins.get('bottom', 50) - 90

        painter.setPen(QPen(QColor(80, 80, 100), 2, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(center_x, top_y), QPointF(center_x, bottom_y))

        # Spin statistics label at divider
        font = QFont('Arial', 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(150, 150, 180), 1))

        # Fermi-Dirac on left
        painter.save()
        painter.translate(center_x - 15, self.widget_height / 2 + 50)
        painter.rotate(-90)
        painter.drawText(QRectF(-60, 0, 120, 20),
                        Qt.AlignmentFlag.AlignCenter, "Fermi-Dirac")
        painter.restore()

        # Bose-Einstein on right
        painter.save()
        painter.translate(center_x + 15, self.widget_height / 2 - 50)
        painter.rotate(90)
        painter.drawText(QRectF(-60, 0, 120, 20),
                        Qt.AlignmentFlag.AlignCenter, "Bose-Einstein")
        painter.restore()

    def _draw_legend(self, painter):
        """Draw legend explaining particle types"""
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')

        legend_x = margins.get('left', 50) - 30
        legend_y = self.widget_height - margins.get('bottom', 50) - 40

        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawText(QPointF(legend_x, legend_y), "Particle Types:")

        type_colors = [
            ("Quarks", QColor(230, 100, 100)),
            ("Leptons", QColor(100, 180, 230)),
            ("Gauge Bosons", QColor(230, 180, 100)),
            ("Scalar Boson", QColor(180, 100, 230))
        ]

        font_small = QFont('Arial', 9)
        painter.setFont(font_small)

        for i, (name, color) in enumerate(type_colors):
            x = legend_x + (i % 2) * 140
            y = legend_y + 18 + (i // 2) * 16

            # Color box
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRect(QRectF(x, y - 10, 12, 12))

            # Label
            painter.setPen(QPen(QColor(180, 180, 180), 1))
            painter.drawText(QPointF(x + 18, y), name)

        # Note about arrangement
        painter.setPen(QPen(QColor(120, 120, 140), 1))
        font_tiny = QFont('Arial', 8)
        painter.setFont(font_tiny)
        painter.drawText(QPointF(legend_x + 300, legend_y + 10),
                        "Arranged by mass (heaviest first)")
