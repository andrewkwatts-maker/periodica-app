#!/usr/bin/env python3
"""
Linear Layout Renderer for Particles
Arranges particles in a linear sequence sorted by a property.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QLinearGradient
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica_app.layouts.quark_base_layout import QuarkBaseLayoutRenderer
from periodica.core.quark_enums import ParticleType, QuarkProperty
from periodica.data.layout_config_loader import get_quark_config, get_layout_config


class QuarkLinearLayoutRenderer(QuarkBaseLayoutRenderer):
    """
    Linear layout renderer.
    Arranges particles in a horizontal or vertical line sorted by a property.
    """

    def __init__(self, widget_width, widget_height):
        super().__init__(widget_width, widget_height)
        # Load configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')
        spacing = config.get_spacing('quarks')

        self.cell_size = card_size.get('default', 70)
        self.cell_spacing = spacing.get('cell', 10) + 5  # Slightly more for linear layout
        self.orientation = "horizontal"  # or "vertical"

        # Store size constraints from config
        self.min_size = card_size.get('min', 45)
        self.max_size = card_size.get('max', 120)

    def create_layout(self, particles, **kwargs):
        """
        Create linear layout sorted by a property.

        Args:
            particles: List of particle dictionaries
            **kwargs:
                - sort_property: Property to sort by (default: "mass")
                - orientation: "horizontal" or "vertical"

        Returns:
            List of particles with layout positions
        """
        sort_property = kwargs.get('sort_property', 'mass')
        self.orientation = kwargs.get('orientation', 'horizontal')

        # Get configuration values
        config = get_layout_config()
        margins = config.get_margins('quarks')

        # Sort particles by property
        sorted_particles = self._sort_particles(particles, sort_property)

        # Calculate layout
        n = len(sorted_particles)
        if n == 0:
            return particles

        if self.orientation == "horizontal":
            # Calculate cell size to fit all particles
            available_width = self.widget_width - margins.get('left', 50) - margins.get('right', 50)
            self.cell_size = min(self.max_size, (available_width - (n - 1) * self.cell_spacing) / n)
            self.cell_size = max(self.min_size, self.cell_size)

            total_width = n * self.cell_size + (n - 1) * self.cell_spacing
            start_x = (self.widget_width - total_width) / 2 + self.cell_size / 2
            center_y = self.widget_height / 2

            for i, particle in enumerate(sorted_particles):
                particle['x'] = start_x + i * (self.cell_size + self.cell_spacing)
                particle['y'] = center_y
                particle['display_size'] = self.cell_size
                particle['sort_index'] = i
        else:
            # Vertical layout
            available_height = self.widget_height - margins.get('top', 100) - margins.get('bottom', 50)
            self.cell_size = min(self.max_size, (available_height - (n - 1) * self.cell_spacing) / n)
            self.cell_size = max(self.min_size - 10, self.cell_size)  # Allow slightly smaller for vertical

            total_height = n * self.cell_size + (n - 1) * self.cell_spacing
            start_y = (self.widget_height - total_height) / 2 + self.cell_size / 2
            center_x = self.widget_width / 2

            for i, particle in enumerate(sorted_particles):
                particle['x'] = center_x
                particle['y'] = start_y + i * (self.cell_size + self.cell_spacing)
                particle['display_size'] = self.cell_size
                particle['sort_index'] = i

        return particles

    def _sort_particles(self, particles, sort_property):
        """Sort particles by the specified property"""
        prop = QuarkProperty.from_string(sort_property)

        if prop == QuarkProperty.MASS:
            return sorted(particles, key=lambda p: p.get('Mass_MeVc2', 0) or 0)
        elif prop == QuarkProperty.CHARGE:
            return sorted(particles, key=lambda p: p.get('Charge_e', 0) or 0)
        elif prop == QuarkProperty.SPIN:
            return sorted(particles, key=lambda p: p.get('Spin_hbar', 0) or 0)
        elif prop == QuarkProperty.GENERATION:
            return sorted(particles, key=lambda p: p.get('generation_num', -1))
        else:
            # Default: sort by name
            return sorted(particles, key=lambda p: p.get('Name', ''))

    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the linear layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Visualization state
            **kwargs: Additional parameters
        """
        passes_filter_func = kwargs.get('passes_filter_func', lambda p: True)
        sort_property = table_state.get('order_property', 'mass')

        # Draw axis/scale
        self._draw_axis(painter, particles, sort_property)

        # Draw particles
        for particle in particles:
            if particle.get('x') is not None and particle.get('y') is not None:
                passes = passes_filter_func(particle)
                self.draw_particle_cell(painter, particle, table_state, passes)

    def _draw_axis(self, painter, particles, sort_property):
        """Draw the sorting axis with labels"""
        if not particles:
            return

        sorted_particles = [p for p in particles if p.get('x') is not None]
        if not sorted_particles:
            return

        # Get spacing from config for consistent padding
        spacing = get_layout_config().get_spacing('quarks')
        axis_padding = spacing.get('section', 30)

        # Draw axis line
        painter.setPen(QPen(QColor(100, 100, 120), 2))

        if self.orientation == "horizontal":
            min_x = min(p['x'] for p in sorted_particles) - self.cell_size / 2 - 20
            max_x = max(p['x'] for p in sorted_particles) + self.cell_size / 2 + 20
            y = sorted_particles[0]['y'] + self.cell_size / 2 + axis_padding

            # Draw gradient line
            gradient = QLinearGradient(min_x, y, max_x, y)
            gradient.setColorAt(0, QColor(100, 150, 255))
            gradient.setColorAt(1, QColor(255, 150, 100))
            painter.setPen(QPen(QBrush(gradient), 3))
            painter.drawLine(QPointF(min_x, y), QPointF(max_x, y))

            # Arrow at end
            painter.setPen(QPen(QColor(255, 150, 100), 2))
            painter.drawLine(QPointF(max_x - 10, y - 5), QPointF(max_x, y))
            painter.drawLine(QPointF(max_x - 10, y + 5), QPointF(max_x, y))

            # Property label
            prop_name = QuarkProperty.get_display_name(sort_property)
            font = QFont('Arial', 11, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawText(QRectF(min_x, y + 10, max_x - min_x, 25),
                           Qt.AlignmentFlag.AlignCenter, f"Sorted by: {prop_name}")

            # Min/max value labels
            font_small = QFont('Arial', 9)
            painter.setFont(font_small)
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawText(QRectF(min_x - 10, y - 20, 50, 15),
                           Qt.AlignmentFlag.AlignLeft, "Low")
            painter.drawText(QRectF(max_x - 40, y - 20, 50, 15),
                           Qt.AlignmentFlag.AlignRight, "High")

        else:
            # Vertical axis
            min_y = min(p['y'] for p in sorted_particles) - self.cell_size / 2 - 20
            max_y = max(p['y'] for p in sorted_particles) + self.cell_size / 2 + 20
            x = sorted_particles[0]['x'] - self.cell_size / 2 - axis_padding

            gradient = QLinearGradient(x, min_y, x, max_y)
            gradient.setColorAt(0, QColor(100, 150, 255))
            gradient.setColorAt(1, QColor(255, 150, 100))
            painter.setPen(QPen(QBrush(gradient), 3))
            painter.drawLine(QPointF(x, min_y), QPointF(x, max_y))

            # Property label (rotated)
            prop_name = QuarkProperty.get_display_name(sort_property)
            font = QFont('Arial', 11, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor(200, 200, 200), 1))

            painter.save()
            painter.translate(x - 25, (min_y + max_y) / 2)
            painter.rotate(-90)
            painter.drawText(QRectF(-75, -10, 150, 20),
                           Qt.AlignmentFlag.AlignCenter, f"Sorted by: {prop_name}")
            painter.restore()
