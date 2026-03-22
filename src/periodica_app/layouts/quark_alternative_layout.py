#!/usr/bin/env python3
"""
Alternative Layout Renderer for Particles
Groups particles by interaction forces.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica_app.layouts.quark_base_layout import QuarkBaseLayoutRenderer
from periodica.core.quark_enums import ParticleType, QuarkProperty, InteractionForce
from periodica.data.layout_config_loader import get_quark_config, get_layout_config


class QuarkAlternativeLayoutRenderer(QuarkBaseLayoutRenderer):
    """
    Alternative layout renderer.
    Groups particles by their interaction forces:
    - Strong force group (quarks, gluons)
    - Electromagnetic group (charged particles, photon)
    - Weak force group (all fermions, W/Z bosons)
    - Gravity only (essentially all particles)
    """

    def __init__(self, widget_width, widget_height):
        super().__init__(widget_width, widget_height)
        # Load configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')
        spacing = config.get_spacing('quarks')

        self.cell_size = card_size.get('default', 70) - 10
        self.group_spacing = spacing.get('group', 40)

        # Store size constraints from config
        self.min_size = card_size.get('min', 45)
        self.max_size = card_size.get('max', 120)

    def create_layout(self, particles, **kwargs):
        """
        Create alternative layout grouping by interactions.

        Args:
            particles: List of particle dictionaries
            **kwargs: Additional parameters

        Returns:
            List of particles with layout positions
        """
        # Get configuration values
        config = get_layout_config()
        margins = config.get_margins('quarks')

        # Group particles by interaction
        strong_particles = []
        em_particles = []
        weak_only = []
        other = []

        for p in particles:
            forces = p.get('InteractionForces', [])
            if 'Strong' in forces:
                strong_particles.append(p)
            elif 'Electromagnetic' in forces:
                em_particles.append(p)
            elif 'Weak' in forces:
                weak_only.append(p)
            else:
                other.append(p)

        # Calculate layout dimensions
        groups = [
            ('Strong', strong_particles, QColor(255, 100, 100)),
            ('Electromagnetic', em_particles, QColor(100, 150, 255)),
            ('Weak Only', weak_only, QColor(255, 200, 100)),
            ('Other', other, QColor(150, 150, 150))
        ]

        # Filter out empty groups
        groups = [(name, parts, color) for name, parts, color in groups if parts]

        if not groups:
            return particles

        # Calculate cell size based on largest group
        max_group_size = max(len(parts) for _, parts, _ in groups)
        available_width = self.widget_width - margins.get('left', 50) - margins.get('right', 50)
        available_height = self.widget_height - margins.get('top', 100) - margins.get('bottom', 50)

        # Arrange groups in a grid (2x2 or 1xN depending on number of groups)
        if len(groups) <= 2:
            cols = len(groups)
            rows = 1
        else:
            cols = 2
            rows = math.ceil(len(groups) / 2)

        group_width = (available_width - (cols - 1) * self.group_spacing) / cols
        group_height = (available_height - (rows - 1) * self.group_spacing) / rows

        # Calculate cell size to fit particles in each group
        max_per_row = max(3, min(6, int(math.sqrt(max_group_size) + 1)))
        self.cell_size = min(
            self.max_size - 10,
            (group_width - 40) / max_per_row,
            (group_height - 60) / max_per_row
        )
        self.cell_size = max(self.min_size, self.cell_size)

        # Position particles in each group
        start_x = margins.get('left', 50)
        start_y = margins.get('top', 100)

        for g_idx, (name, parts, color) in enumerate(groups):
            g_col = g_idx % cols
            g_row = g_idx // cols

            group_x = start_x + g_col * (group_width + self.group_spacing)
            group_y = start_y + g_row * (group_height + self.group_spacing)

            # Store group info for painting
            for p in parts:
                p['group_name'] = name
                p['group_color'] = color
                p['group_rect'] = QRectF(group_x, group_y, group_width, group_height)

            # Arrange particles in grid within group
            inner_cols = max(2, min(5, int(math.sqrt(len(parts)) + 0.5)))
            inner_start_x = group_x + (group_width - inner_cols * self.cell_size) / 2 + self.cell_size / 2
            inner_start_y = group_y + 50 + self.cell_size / 2

            for i, particle in enumerate(parts):
                col = i % inner_cols
                row = i // inner_cols
                particle['x'] = inner_start_x + col * (self.cell_size + 5)
                particle['y'] = inner_start_y + row * (self.cell_size + 5)
                particle['display_size'] = self.cell_size

        return particles

    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the alternative layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Visualization state
            **kwargs: Additional parameters
        """
        passes_filter_func = kwargs.get('passes_filter_func', lambda p: True)

        # Draw group backgrounds and labels
        self._draw_group_backgrounds(painter, particles)

        # Draw particles
        for particle in particles:
            if particle.get('x') is not None and particle.get('y') is not None:
                passes = passes_filter_func(particle)
                self.draw_particle_cell(painter, particle, table_state, passes)

        # Draw interaction force legend
        self._draw_legend(painter)

    def _draw_group_backgrounds(self, painter, particles):
        """Draw backgrounds and labels for each group"""
        # Get unique groups
        drawn_groups = set()

        for p in particles:
            group_name = p.get('group_name')
            if group_name and group_name not in drawn_groups:
                drawn_groups.add(group_name)

                rect = p.get('group_rect')
                color = p.get('group_color', QColor(100, 100, 100))

                if rect:
                    # Background
                    bg_color = QColor(color)
                    bg_color.setAlpha(30)
                    painter.setBrush(QBrush(bg_color))
                    painter.setPen(QPen(color, 2))
                    painter.drawRoundedRect(rect, 15, 15)

                    # Group label
                    font = QFont('Arial', 12, QFont.Weight.Bold)
                    painter.setFont(font)
                    painter.setPen(QPen(color.lighter(130), 1))
                    label_rect = QRectF(rect.x(), rect.y() + 10, rect.width(), 25)
                    painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, group_name)

                    # Force description
                    descriptions = {
                        'Strong': 'Quarks & Gluons',
                        'Electromagnetic': 'Charged particles & Photon',
                        'Weak Only': 'Neutrinos & W/Z bosons',
                        'Other': 'Gravity only'
                    }
                    desc = descriptions.get(group_name, '')
                    if desc:
                        font_small = QFont('Arial', 9)
                        painter.setFont(font_small)
                        painter.setPen(QPen(QColor(180, 180, 180), 1))
                        desc_rect = QRectF(rect.x(), rect.y() + 28, rect.width(), 20)
                        painter.drawText(desc_rect, Qt.AlignmentFlag.AlignCenter, desc)

    def _draw_legend(self, painter):
        """Draw interaction force legend"""
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')

        legend_x = margins.get('left', 50) - 30
        legend_y = self.widget_height - margins.get('bottom', 50) - 50

        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawText(QPointF(legend_x, legend_y), "Fundamental Forces:")

        forces = [
            ('Strong', QColor(255, 100, 100)),
            ('Electromagnetic', QColor(100, 150, 255)),
            ('Weak', QColor(255, 200, 100)),
            ('Gravitational', QColor(150, 255, 150))
        ]

        font_small = QFont('Arial', 9)
        painter.setFont(font_small)

        for i, (force, color) in enumerate(forces):
            x = legend_x + (i % 2) * 150
            y = legend_y + 20 + (i // 2) * 18

            # Color box
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRect(QRectF(x, y - 10, 12, 12))

            # Label
            painter.setPen(QPen(QColor(180, 180, 180), 1))
            painter.drawText(QPointF(x + 18, y), force)
