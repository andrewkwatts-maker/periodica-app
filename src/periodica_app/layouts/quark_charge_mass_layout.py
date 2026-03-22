#!/usr/bin/env python3
"""
Charge-Mass Grid Layout Renderer
Scatter plot style layout with charge on X-axis and log mass on Y-axis.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica_app.layouts.quark_base_layout import QuarkBaseLayoutRenderer
from periodica.core.quark_enums import ParticleType
from periodica.data.layout_config_loader import get_quark_config, get_layout_config


class QuarkChargeMassLayoutRenderer(QuarkBaseLayoutRenderer):
    """
    Charge-Mass Grid layout renderer.
    - X-axis: Charge (-1 to +2/3, with extension for +1)
    - Y-axis: Log mass
    - Scatter plot style with particle cards
    """

    def __init__(self, widget_width, widget_height):
        super().__init__(widget_width, widget_height)
        # Load configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')
        margins = config.get_margins('quarks')

        self.cell_size = card_size.get('default', 70) - 15  # Smaller for scatter plot

        # Store size constraints from config
        self.min_size = card_size.get('min', 45) - 10
        self.max_size = card_size.get('max', 120) - 10

        # Grid bounds from config
        self.margin_left = margins.get('left', 50) + 30  # Extra for axis labels
        self.margin_right = margins.get('right', 50) - 10
        self.margin_top = margins.get('top', 100) - 20
        self.margin_bottom = margins.get('bottom', 50) + 50  # Extra for axis labels

        # Charge range (typically -1 to +1, but quarks have fractional charges)
        self.charge_min = -1.2
        self.charge_max = 1.2

    def create_layout(self, particles, **kwargs):
        """
        Create charge-mass grid layout.

        Args:
            particles: List of particle dictionaries
            **kwargs: Additional parameters

        Returns:
            List of particles with layout positions
        """
        # Calculate plot area
        plot_width = self.widget_width - self.margin_left - self.margin_right
        plot_height = self.widget_height - self.margin_top - self.margin_bottom

        # Find mass range for Y-axis (logarithmic)
        masses = [p.get('Mass_MeVc2', 0) or 0.0001 for p in particles]
        min_mass = max(0.0001, min(masses))
        max_mass = max(masses) if masses else 1

        log_min = math.log10(min_mass)
        log_max = math.log10(max_mass) if max_mass > min_mass else log_min + 1

        # Add padding to log range
        log_range = log_max - log_min
        log_min -= log_range * 0.1
        log_max += log_range * 0.1

        # Store axis info for painting
        self.log_min = log_min
        self.log_max = log_max
        self.plot_width = plot_width
        self.plot_height = plot_height

        # Calculate cell size based on number of particles
        n = len(particles)
        if n > 0:
            self.cell_size = min(self.max_size, max(self.min_size, plot_width / (n ** 0.5) * 0.8))

        # Position each particle
        for particle in particles:
            charge = particle.get('Charge_e', 0) or 0
            mass = particle.get('Mass_MeVc2', 0) or 0.0001

            # X position from charge
            charge_norm = (charge - self.charge_min) / (self.charge_max - self.charge_min)
            x = self.margin_left + charge_norm * plot_width

            # Y position from log mass (inverted so heavier is higher)
            log_mass = math.log10(max(0.0001, mass))
            mass_norm = (log_mass - log_min) / (log_max - log_min)
            y = self.margin_top + (1 - mass_norm) * plot_height

            particle['x'] = x
            particle['y'] = y
            particle['display_size'] = self.cell_size

            # Store grid position info
            particle['grid_charge'] = charge
            particle['grid_mass'] = mass
            particle['grid_log_mass'] = log_mass

        # Handle overlapping particles by applying jitter
        self._apply_jitter(particles)

        return particles

    def _apply_jitter(self, particles):
        """Apply small jitter to separate overlapping particles"""
        # Group particles by approximate position
        grid_size = self.cell_size * 0.8
        position_groups = {}

        for p in particles:
            grid_x = int(p['x'] / grid_size)
            grid_y = int(p['y'] / grid_size)
            key = (grid_x, grid_y)
            if key not in position_groups:
                position_groups[key] = []
            position_groups[key].append(p)

        # Apply jitter to groups with multiple particles
        for key, group in position_groups.items():
            if len(group) > 1:
                n = len(group)
                for i, p in enumerate(group):
                    angle = 2 * math.pi * i / n
                    jitter_dist = self.cell_size * 0.4
                    p['x'] += jitter_dist * math.cos(angle)
                    p['y'] += jitter_dist * math.sin(angle)

    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the charge-mass grid layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Visualization state
            **kwargs: Additional parameters
        """
        passes_filter_func = kwargs.get('passes_filter_func', lambda p: True)

        # Draw grid and axes
        self._draw_grid(painter)
        self._draw_axes(painter)

        # Draw particles
        for particle in particles:
            if particle.get('x') is not None and particle.get('y') is not None:
                passes = passes_filter_func(particle)
                self.draw_particle_cell(painter, particle, table_state, passes)

        # Draw legend
        self._draw_legend(painter)

    def _draw_grid(self, painter):
        """Draw background grid"""
        # Grid lines
        painter.setPen(QPen(QColor(50, 50, 70, 80), 1, Qt.PenStyle.DotLine))

        # Vertical lines for charge values
        charge_values = [-1, -2/3, -1/3, 0, 1/3, 2/3, 1]
        for charge in charge_values:
            x = self.margin_left + ((charge - self.charge_min) /
                                    (self.charge_max - self.charge_min)) * self.plot_width
            painter.drawLine(QPointF(x, self.margin_top),
                           QPointF(x, self.margin_top + self.plot_height))

        # Horizontal lines for mass decades
        if hasattr(self, 'log_min') and hasattr(self, 'log_max'):
            for log_mass in range(int(self.log_min) - 1, int(self.log_max) + 2):
                if self.log_min <= log_mass <= self.log_max:
                    mass_norm = (log_mass - self.log_min) / (self.log_max - self.log_min)
                    y = self.margin_top + (1 - mass_norm) * self.plot_height
                    painter.drawLine(QPointF(self.margin_left, y),
                                   QPointF(self.margin_left + self.plot_width, y))

        # Highlight zero charge line
        zero_x = self.margin_left + ((0 - self.charge_min) /
                                     (self.charge_max - self.charge_min)) * self.plot_width
        painter.setPen(QPen(QColor(100, 100, 120, 100), 2))
        painter.drawLine(QPointF(zero_x, self.margin_top),
                        QPointF(zero_x, self.margin_top + self.plot_height))

    def _draw_axes(self, painter):
        """Draw X and Y axes with labels"""
        # Axis lines
        painter.setPen(QPen(QColor(150, 150, 180), 2))

        # X-axis
        painter.drawLine(QPointF(self.margin_left, self.margin_top + self.plot_height),
                        QPointF(self.margin_left + self.plot_width,
                               self.margin_top + self.plot_height))

        # Y-axis
        painter.drawLine(QPointF(self.margin_left, self.margin_top),
                        QPointF(self.margin_left, self.margin_top + self.plot_height))

        # Axis labels
        font = QFont('Arial', 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(180, 180, 200), 1))

        # X-axis label
        painter.drawText(QRectF(self.margin_left, self.margin_top + self.plot_height + 60,
                               self.plot_width, 25),
                        Qt.AlignmentFlag.AlignCenter, "Electric Charge (e)")

        # Y-axis label (rotated)
        painter.save()
        painter.translate(25, self.margin_top + self.plot_height / 2)
        painter.rotate(-90)
        painter.drawText(QRectF(-self.plot_height / 2, 0, self.plot_height, 25),
                        Qt.AlignmentFlag.AlignCenter, "Mass (MeV/c^2) - Log Scale")
        painter.restore()

        # X-axis tick labels
        font_small = QFont('Arial', 9)
        painter.setFont(font_small)
        painter.setPen(QPen(QColor(150, 150, 170), 1))

        charge_labels = [
            (-1, "-1"),
            (-2/3, "-2/3"),
            (-1/3, "-1/3"),
            (0, "0"),
            (1/3, "+1/3"),
            (2/3, "+2/3"),
            (1, "+1")
        ]

        for charge, label in charge_labels:
            x = self.margin_left + ((charge - self.charge_min) /
                                    (self.charge_max - self.charge_min)) * self.plot_width
            y = self.margin_top + self.plot_height + 15
            painter.drawText(QRectF(x - 25, y, 50, 20),
                           Qt.AlignmentFlag.AlignCenter, label)

            # Tick mark
            painter.drawLine(QPointF(x, self.margin_top + self.plot_height),
                           QPointF(x, self.margin_top + self.plot_height + 5))

        # Y-axis tick labels (mass decades)
        if hasattr(self, 'log_min') and hasattr(self, 'log_max'):
            for log_mass in range(int(self.log_min), int(self.log_max) + 1):
                if self.log_min <= log_mass <= self.log_max:
                    mass_norm = (log_mass - self.log_min) / (self.log_max - self.log_min)
                    y = self.margin_top + (1 - mass_norm) * self.plot_height
                    mass_value = 10 ** log_mass

                    # Format mass label
                    if mass_value >= 1000:
                        label = f"{mass_value/1000:.0f} GeV"
                    elif mass_value >= 1:
                        label = f"{mass_value:.0f} MeV"
                    else:
                        label = f"{mass_value*1000:.0f} keV"

                    painter.drawText(QRectF(5, y - 10, self.margin_left - 15, 20),
                                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                                   label)

                    # Tick mark
                    painter.drawLine(QPointF(self.margin_left - 5, y),
                                   QPointF(self.margin_left, y))

    def _draw_legend(self, painter):
        """Draw legend for particle types"""
        legend_x = self.widget_width - 180
        legend_y = 20

        # Legend box background
        legend_rect = QRectF(legend_x - 10, legend_y - 5, 170, 95)
        painter.setBrush(QBrush(QColor(30, 30, 50, 200)))
        painter.setPen(QPen(QColor(80, 80, 100), 1))
        painter.drawRoundedRect(legend_rect, 8, 8)

        font = QFont('Arial', 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawText(QPointF(legend_x, legend_y + 10), "Particle Types:")

        type_colors = [
            ("Quarks", QColor(230, 100, 100)),
            ("Leptons", QColor(100, 180, 230)),
            ("Gauge Bosons", QColor(230, 180, 100)),
            ("Scalar Boson", QColor(180, 100, 230))
        ]

        font_small = QFont('Arial', 8)
        painter.setFont(font_small)

        for i, (name, color) in enumerate(type_colors):
            y = legend_y + 28 + i * 15

            # Color box
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRect(QRectF(legend_x, y - 8, 10, 10))

            # Label
            painter.setPen(QPen(QColor(180, 180, 180), 1))
            painter.drawText(QPointF(legend_x + 15, y), name)

        # Add note about charge regions
        painter.setPen(QPen(QColor(120, 120, 140), 1))
        font_tiny = QFont('Arial', 8)
        painter.setFont(font_tiny)

        notes_y = self.margin_top + self.plot_height + 40
        painter.drawText(QPointF(self.margin_left, notes_y),
                        "Quarks: +2/3 or -1/3  |  Leptons: 0 or -1  |  W boson: +/-1")
