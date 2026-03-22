#!/usr/bin/env python3
"""
Mass Hierarchy Spiral Layout Renderer
Arranges particles in a logarithmic spiral based on mass,
with angular position by generation and size proportional to spin.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QRadialGradient
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica_app.layouts.quark_base_layout import QuarkBaseLayoutRenderer
from periodica.core.quark_enums import ParticleType, QuarkGeneration
from periodica.data.layout_config_loader import get_quark_config, get_layout_config


class QuarkMassSpiralLayoutRenderer(QuarkBaseLayoutRenderer):
    """
    Mass Hierarchy Spiral layout renderer.
    - Logarithmic spiral where radius = log(Mass_MeVc2)
    - Angular position by generation (1st/2nd/3rd)
    - Size proportional to spin value
    """

    def __init__(self, widget_width, widget_height):
        super().__init__(widget_width, widget_height)
        # Load configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')

        self.base_cell_size = card_size.get('default', 70) - 20

        # Store size constraints from config
        self.min_size = card_size.get('min', 45)
        self.max_size = card_size.get('max', 120)

        # Load mass spiral configuration
        spiral_config = get_quark_config('mass_spiral', default={})
        self.min_radius_ratio = spiral_config.get('min_radius_ratio', 0.15)
        self.max_radius_ratio = spiral_config.get('max_radius_ratio', 0.85)
        self.angular_spread_deg = spiral_config.get('angular_spread_deg', 60)
        self.angular_spread = math.radians(self.angular_spread_deg)

    def create_layout(self, particles, **kwargs):
        """
        Create mass spiral layout.

        Args:
            particles: List of particle dictionaries
            **kwargs: Additional parameters

        Returns:
            List of particles with layout positions
        """
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')

        center_x = self.widget_width / 2
        center_y = self.widget_height / 2

        # Calculate max radius available
        max_radius = min(self.widget_width, self.widget_height) / 2 - margins.get('bottom', 50) - 30

        # Find mass range for normalization
        masses = [p.get('Mass_MeVc2', 0) or 0.001 for p in particles]
        min_mass = max(0.001, min(masses))  # Avoid log(0)
        max_mass = max(masses) if masses else 1

        # Log scale normalization
        log_min = math.log10(min_mass)
        log_max = math.log10(max_mass) if max_mass > min_mass else log_min + 1

        # Group particles by generation for angular positioning
        gen_groups = {
            0: [],   # Bosons (no generation)
            1: [],   # First generation
            2: [],   # Second generation
            3: [],   # Third generation
            -1: []   # Unknown
        }

        for p in particles:
            gen = p.get('generation_num', -1)
            if gen in gen_groups:
                gen_groups[gen].append(p)
            else:
                gen_groups[-1].append(p)

        # Angular sectors for each generation
        # Bosons: center/top, Gen 1: right, Gen 2: bottom-right, Gen 3: bottom-left, Unknown: left
        gen_base_angles = {
            0: -math.pi / 2,      # Top (bosons)
            1: 0,                  # Right
            2: 2 * math.pi / 3,   # Lower right
            3: 4 * math.pi / 3,   # Lower left
            -1: math.pi           # Left (unknown)
        }

        gen_colors = {
            0: QColor(180, 100, 230),  # Purple for bosons
            1: QColor(100, 200, 100),  # Green for 1st gen
            2: QColor(200, 200, 100),  # Yellow for 2nd gen
            3: QColor(200, 100, 100),  # Red for 3rd gen
            -1: QColor(150, 150, 150)  # Gray for unknown
        }

        # Position each particle
        for gen, group_particles in gen_groups.items():
            if not group_particles:
                continue

            base_angle = gen_base_angles[gen]
            n = len(group_particles)

            # Sort by mass within generation
            group_particles.sort(key=lambda p: p.get('Mass_MeVc2', 0) or 0)

            for i, particle in enumerate(group_particles):
                # Calculate radius from mass (logarithmic spiral)
                mass = particle.get('Mass_MeVc2', 0) or 0.001
                log_mass = math.log10(max(0.001, mass))

                # Normalize to [min_radius_ratio, max_radius_ratio] range for radius
                if log_max > log_min:
                    norm_mass = (log_mass - log_min) / (log_max - log_min)
                else:
                    norm_mass = 0.5
                radius = max_radius * (self.min_radius_ratio + (self.max_radius_ratio - self.min_radius_ratio) * norm_mass)

                # Calculate angle within generation sector
                if n > 1:
                    angle_offset = (i / (n - 1) - 0.5) * self.angular_spread
                else:
                    angle_offset = 0
                angle = base_angle + angle_offset

                # Position
                particle['x'] = center_x + radius * math.cos(angle)
                particle['y'] = center_y + radius * math.sin(angle)

                # Size proportional to spin
                spin = particle.get('Spin_hbar', 0.5) or 0.5
                size_factor = 0.7 + 0.6 * min(spin, 1.5)  # Scale from 0.7 to 1.6
                particle['display_size'] = self.base_cell_size * size_factor

                # Store spiral data for visualization
                particle['spiral_radius'] = radius
                particle['spiral_angle'] = angle
                particle['generation_color'] = gen_colors[gen]
                particle['generation_num'] = gen

        return particles

    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the mass spiral layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Visualization state
            **kwargs: Additional parameters
        """
        passes_filter_func = kwargs.get('passes_filter_func', lambda p: True)

        center_x = self.widget_width / 2
        center_y = self.widget_height / 2

        # Draw spiral guides
        self._draw_spiral_guides(painter, center_x, center_y, particles)

        # Draw generation sectors
        self._draw_generation_sectors(painter, center_x, center_y)

        # Draw particles
        for particle in particles:
            if particle.get('x') is not None and particle.get('y') is not None:
                passes = passes_filter_func(particle)
                self.draw_particle_cell(painter, particle, table_state, passes)

        # Draw legend
        self._draw_legend(painter, center_x, center_y)

    def _draw_spiral_guides(self, painter, center_x, center_y, particles):
        """Draw logarithmic spiral guide lines"""
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')
        max_radius = min(self.widget_width, self.widget_height) / 2 - margins.get('bottom', 50) - 30

        # Draw concentric circles for mass scale
        painter.setPen(QPen(QColor(60, 60, 80, 80), 1, Qt.PenStyle.DotLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        mass_markers = [0.001, 0.1, 1, 10, 100, 1000, 10000, 100000]
        for mass in mass_markers:
            log_mass = math.log10(mass)
            # Normalize (assuming typical particle mass range)
            norm = (log_mass + 3) / 8  # -3 to 5 range
            if self.min_radius_ratio <= norm <= 1.0:
                radius = max_radius * norm
                painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

                # Mass label
                painter.setPen(QPen(QColor(100, 100, 120), 1))
                font = QFont('Arial', 8)
                painter.setFont(font)
                label = f"{mass} MeV" if mass >= 1 else f"{mass*1000} keV"
                painter.drawText(QPointF(center_x + radius + 5, center_y), label)

    def _draw_generation_sectors(self, painter, center_x, center_y):
        """Draw generation sector labels"""
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')
        max_radius = min(self.widget_width, self.widget_height) / 2 - margins.get('bottom', 50) - 30

        gen_info = [
            (0, -math.pi / 2, "Bosons", QColor(180, 100, 230)),
            (1, 0, "1st Gen", QColor(100, 200, 100)),
            (2, 2 * math.pi / 3, "2nd Gen", QColor(200, 200, 100)),
            (3, 4 * math.pi / 3, "3rd Gen", QColor(200, 100, 100))
        ]

        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)

        for gen, angle, label, color in gen_info:
            # Draw sector line
            painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine))
            end_x = center_x + max_radius * math.cos(angle)
            end_y = center_y + max_radius * math.sin(angle)
            painter.drawLine(QPointF(center_x, center_y), QPointF(end_x, end_y))

            # Draw label at outer edge
            label_radius = max_radius + 25
            label_x = center_x + label_radius * math.cos(angle)
            label_y = center_y + label_radius * math.sin(angle)

            painter.setPen(QPen(color.lighter(130), 1))
            rect = QRectF(label_x - 40, label_y - 10, 80, 20)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_legend(self, painter, center_x, center_y):
        """Draw legend explaining the spiral"""
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')

        legend_x = margins.get('left', 50) - 30
        legend_y = self.widget_height - margins.get('bottom', 50) - 70

        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawText(QPointF(legend_x, legend_y), "Mass Hierarchy Spiral:")

        font_small = QFont('Arial', 9)
        painter.setFont(font_small)
        painter.setPen(QPen(QColor(150, 150, 150), 1))

        info_lines = [
            "Radius = log(Mass)",
            "Angle = Generation",
            "Size = Spin"
        ]

        for i, line in enumerate(info_lines):
            painter.drawText(QPointF(legend_x, legend_y + 18 + i * 15), line)

        # Generation color legend
        gen_legend_y = legend_y + 70
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        font = QFont('Arial', 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QPointF(legend_x, gen_legend_y), "Generations:")

        gen_colors = [
            ("1st", QColor(100, 200, 100)),
            ("2nd", QColor(200, 200, 100)),
            ("3rd", QColor(200, 100, 100)),
            ("Bosons", QColor(180, 100, 230))
        ]

        font_small = QFont('Arial', 8)
        painter.setFont(font_small)

        for i, (name, color) in enumerate(gen_colors):
            x = legend_x + (i % 2) * 80
            y = gen_legend_y + 15 + (i // 2) * 15

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRect(QRectF(x, y - 8, 10, 10))

            painter.setPen(QPen(QColor(180, 180, 180), 1))
            painter.drawText(QPointF(x + 14, y), name)
