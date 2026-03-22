#!/usr/bin/env python3
"""
Circular Layout Renderer for Particles
Arranges particles in concentric rings based on categories.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QRadialGradient
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica_app.layouts.quark_base_layout import QuarkBaseLayoutRenderer
from periodica.core.quark_enums import ParticleType, QuarkProperty
from periodica.data.layout_config_loader import get_quark_config, get_layout_config


class QuarkCircularLayoutRenderer(QuarkBaseLayoutRenderer):
    """
    Circular layout renderer.
    Arranges particles in concentric rings:
    - Center: Higgs boson
    - Inner ring: Gauge bosons
    - Middle ring: Quarks
    - Outer ring: Leptons
    """

    def __init__(self, widget_width, widget_height):
        super().__init__(widget_width, widget_height)
        # Load configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')

        self.cell_size = card_size.get('default', 70) - 10  # Slightly smaller for circular

        # Store size constraints from config
        self.min_size = card_size.get('min', 45)
        self.max_size = card_size.get('max', 120)

        # Load ring radius ratios from config
        circular_config = get_quark_config('circular', default={})
        self.ring_ratios = circular_config.get('ring_radius_ratios', [0.25, 0.55, 0.85])

    def create_layout(self, particles, **kwargs):
        """
        Create circular layout with particles in rings.

        Args:
            particles: List of particle dictionaries
            **kwargs: Additional parameters

        Returns:
            List of particles with layout positions
        """
        center_x = self.widget_width / 2
        center_y = self.widget_height / 2

        # Get margins from config
        margins = get_layout_config().get_margins('quarks')

        # Categorize particles
        higgs = [p for p in particles if 'higgs' in p.get('Name', '').lower()]
        gauge_bosons = [p for p in particles
                       if p.get('particle_type') == ParticleType.GAUGE_BOSON]
        quarks = [p for p in particles if p.get('particle_type') == ParticleType.QUARK]
        leptons = [p for p in particles if p.get('particle_type') == ParticleType.LEPTON]
        others = [p for p in particles
                 if p not in higgs and p not in gauge_bosons
                 and p not in quarks and p not in leptons]

        # Calculate radii based on widget size
        max_radius = min(self.widget_width, self.widget_height) / 2 - margins.get('bottom', 50) - 10
        self.cell_size = min(self.max_size - 10, max_radius / 5)
        self.cell_size = max(self.min_size, self.cell_size)

        # Ring radii from config ratios
        inner_radius = max_radius * self.ring_ratios[0]
        middle_radius = max_radius * self.ring_ratios[1]
        outer_radius = max_radius * self.ring_ratios[2]

        # Place Higgs at center
        for particle in higgs:
            particle['x'] = center_x
            particle['y'] = center_y
            particle['display_size'] = self.cell_size * 1.2
            particle['ring'] = 'center'

        # Place gauge bosons in inner ring
        self._place_in_ring(gauge_bosons, center_x, center_y, inner_radius, 'inner')

        # Place quarks in middle ring
        self._place_in_ring(quarks, center_x, center_y, middle_radius, 'middle')

        # Place leptons in outer ring
        self._place_in_ring(leptons, center_x, center_y, outer_radius, 'outer')

        # Place others in extra ring
        if others:
            extra_radius = max_radius * 1.05
            self._place_in_ring(others, center_x, center_y, extra_radius, 'extra')

        return particles

    def _place_in_ring(self, particles, center_x, center_y, radius, ring_name):
        """Place particles evenly spaced in a ring"""
        n = len(particles)
        if n == 0:
            return

        angle_step = 2 * math.pi / n
        start_angle = -math.pi / 2  # Start at top

        for i, particle in enumerate(particles):
            angle = start_angle + i * angle_step
            particle['x'] = center_x + radius * math.cos(angle)
            particle['y'] = center_y + radius * math.sin(angle)
            particle['angle'] = angle
            particle['radius'] = radius
            particle['display_size'] = self.cell_size
            particle['ring'] = ring_name

    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the circular layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Visualization state
            **kwargs: Additional parameters
        """
        passes_filter_func = kwargs.get('passes_filter_func', lambda p: True)

        center_x = self.widget_width / 2
        center_y = self.widget_height / 2

        # Draw ring guides and labels
        self._draw_ring_guides(painter, center_x, center_y, particles)

        # Draw connection lines (optional)
        if table_state.get('show_connections', False):
            self._draw_connections(painter, particles)

        # Draw particles
        for particle in particles:
            if particle.get('x') is not None and particle.get('y') is not None:
                passes = passes_filter_func(particle)
                self.draw_particle_cell(painter, particle, table_state, passes)

    def _draw_ring_guides(self, painter, center_x, center_y, particles):
        """Draw guide rings and labels"""
        # Get unique radii
        radii = set()
        for p in particles:
            if p.get('radius'):
                radii.add(p['radius'])

        # Draw ring circles
        painter.setPen(QPen(QColor(60, 60, 80, 100), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for radius in sorted(radii):
            painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # Draw ring labels
        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)

        ring_labels = {
            'inner': ('Gauge Bosons', QColor(230, 180, 100)),
            'middle': ('Quarks', QColor(230, 100, 100)),
            'outer': ('Leptons', QColor(100, 180, 230)),
            'extra': ('Other', QColor(150, 150, 150))
        }

        for ring_name, (label, color) in ring_labels.items():
            ring_particles = [p for p in particles if p.get('ring') == ring_name]
            if ring_particles:
                radius = ring_particles[0].get('radius', 0)
                # Draw label at top of ring
                label_x = center_x
                label_y = center_y - radius - 25

                painter.setPen(QPen(color, 1))
                painter.drawText(QRectF(label_x - 60, label_y, 120, 20),
                               Qt.AlignmentFlag.AlignCenter, label)

        # Center label
        painter.setPen(QPen(QColor(180, 100, 230), 1))
        painter.drawText(QRectF(center_x - 40, center_y + 50, 80, 20),
                       Qt.AlignmentFlag.AlignCenter, "Higgs")

    def _draw_connections(self, painter, particles):
        """Draw connection lines between related particles"""
        # Example: Connect particles that interact via same force
        painter.setPen(QPen(QColor(100, 100, 150, 50), 1))

        quarks = [p for p in particles if p.get('particle_type') == ParticleType.QUARK]
        gluons = [p for p in particles if 'gluon' in p.get('Name', '').lower()]

        # Connect quarks to gluon (strong force)
        for quark in quarks:
            for gluon in gluons:
                if quark.get('x') and gluon.get('x'):
                    painter.drawLine(
                        QPointF(quark['x'], quark['y']),
                        QPointF(gluon['x'], gluon['y'])
                    )
