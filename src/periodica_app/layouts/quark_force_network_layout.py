#!/usr/bin/env python3
"""
Force Interaction Network Layout Renderer
Clusters particles by which forces they interact with and draws connection lines.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica_app.layouts.quark_base_layout import QuarkBaseLayoutRenderer
from periodica.core.quark_enums import ParticleType, InteractionForce
from periodica.data.layout_config_loader import get_quark_config, get_layout_config


class QuarkForceNetworkLayoutRenderer(QuarkBaseLayoutRenderer):
    """
    Force Interaction Network layout renderer.
    Clusters particles by which forces they interact with (InteractionForces property).
    Draws connection lines between particles sharing forces.
    Colors nodes by primary force:
    - Red: Strong
    - Blue: Electromagnetic
    - Orange: Weak
    - Green: Gravity
    """

    def __init__(self, widget_width, widget_height):
        super().__init__(widget_width, widget_height)
        # Load configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')
        spacing = config.get_spacing('quarks')

        self.cell_size = card_size.get('default', 70) - 15
        self.cluster_spacing = spacing.get('section', 30) * 2

        # Store size constraints from config
        self.min_size = card_size.get('min', 45) - 5
        self.max_size = card_size.get('max', 120) - 10

        # Load cluster positions from config
        force_network_config = get_quark_config('force_network', default={})
        self.cluster_positions = force_network_config.get('cluster_positions', {
            'strong': [0.25, 0.3],
            'electromagnetic': [0.75, 0.3],
            'weak': [0.5, 0.7],
            'gravitational': [0.5, 0.5]
        })

    def create_layout(self, particles, **kwargs):
        """
        Create force network layout clustering by interaction forces.

        Args:
            particles: List of particle dictionaries
            **kwargs: Additional parameters

        Returns:
            List of particles with layout positions
        """
        # Get configuration values
        config = get_layout_config()
        margins = config.get_margins('quarks')

        # Define force clusters and their colors, using config positions
        force_clusters = {
            'Strong': {
                'particles': [],
                'color': QColor(255, 100, 100),
                'position': tuple(self.cluster_positions.get('strong', [0.25, 0.3]))
            },
            'Electromagnetic': {
                'particles': [],
                'color': QColor(100, 150, 255),
                'position': tuple(self.cluster_positions.get('electromagnetic', [0.75, 0.3]))
            },
            'Weak': {
                'particles': [],
                'color': QColor(255, 180, 100),
                'position': tuple(self.cluster_positions.get('weak', [0.5, 0.7]))
            },
            'Gravitational': {
                'particles': [],
                'color': QColor(100, 255, 150),
                'position': tuple(self.cluster_positions.get('gravitational', [0.5, 0.5]))
            }
        }

        # Categorize particles by their primary interaction force
        for p in particles:
            forces = p.get('InteractionForces', [])
            # Determine primary force (Strong > EM > Weak > Gravity)
            if 'Strong' in forces:
                force_clusters['Strong']['particles'].append(p)
                p['primary_force'] = 'Strong'
            elif 'Electromagnetic' in forces:
                force_clusters['Electromagnetic']['particles'].append(p)
                p['primary_force'] = 'Electromagnetic'
            elif 'Weak' in forces:
                force_clusters['Weak']['particles'].append(p)
                p['primary_force'] = 'Weak'
            else:
                force_clusters['Gravitational']['particles'].append(p)
                p['primary_force'] = 'Gravitational'

            # Store all forces for connection drawing
            p['all_forces'] = forces if forces else ['Gravitational']

        # Calculate layout dimensions
        available_width = self.widget_width - margins.get('left', 50) - margins.get('right', 50)
        available_height = self.widget_height - margins.get('top', 100) - margins.get('bottom', 50)

        # Calculate cell size based on max cluster size
        max_cluster = max((len(c['particles']) for c in force_clusters.values()), default=1)
        cluster_radius = min(available_width, available_height) * 0.2

        # Adjust cell size to fit in cluster
        if max_cluster > 0:
            self.cell_size = min(self.max_size, cluster_radius * 1.5 / math.sqrt(max_cluster))
            self.cell_size = max(self.min_size, self.cell_size)

        # Position particles in each cluster
        center_x = self.widget_width / 2
        center_y = self.widget_height / 2

        for force_name, cluster in force_clusters.items():
            cluster_particles = cluster['particles']
            if not cluster_particles:
                continue

            # Cluster center position
            pos_x, pos_y = cluster['position']
            cx = center_x + (pos_x - 0.5) * available_width * 0.8
            cy = margins.get('top', 100) - 20 + pos_y * (available_height - 40)

            # Store cluster info for each particle
            for p in cluster_particles:
                p['cluster_center'] = (cx, cy)
                p['cluster_color'] = cluster['color']
                p['cluster_name'] = force_name

            # Arrange particles in a circular pattern within cluster
            n = len(cluster_particles)
            if n == 1:
                cluster_particles[0]['x'] = cx
                cluster_particles[0]['y'] = cy
                cluster_particles[0]['display_size'] = self.cell_size
            else:
                # Multiple particles: arrange in circle
                radius = min(cluster_radius, self.cell_size * n / (2 * math.pi) + self.cell_size)
                for i, particle in enumerate(cluster_particles):
                    angle = 2 * math.pi * i / n - math.pi / 2
                    particle['x'] = cx + radius * math.cos(angle)
                    particle['y'] = cy + radius * math.sin(angle)
                    particle['display_size'] = self.cell_size

        return particles

    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the force network layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Visualization state
            **kwargs: Additional parameters
        """
        passes_filter_func = kwargs.get('passes_filter_func', lambda p: True)

        # Draw cluster backgrounds
        self._draw_cluster_backgrounds(painter, particles)

        # Draw connection lines between particles sharing forces
        self._draw_force_connections(painter, particles)

        # Draw particles
        for particle in particles:
            if particle.get('x') is not None and particle.get('y') is not None:
                passes = passes_filter_func(particle)
                self.draw_particle_cell(painter, particle, table_state, passes)

        # Draw legend
        self._draw_legend(painter)

    def _draw_cluster_backgrounds(self, painter, particles):
        """Draw background circles for each force cluster"""
        # Get unique clusters
        drawn_clusters = {}

        for p in particles:
            cluster_name = p.get('cluster_name')
            if cluster_name and cluster_name not in drawn_clusters:
                center = p.get('cluster_center')
                color = p.get('cluster_color', QColor(100, 100, 100))
                if center:
                    drawn_clusters[cluster_name] = {
                        'center': center,
                        'color': color,
                        'particles': []
                    }
            if cluster_name in drawn_clusters:
                drawn_clusters[cluster_name]['particles'].append(p)

        # Draw each cluster background
        for cluster_name, cluster_data in drawn_clusters.items():
            cx, cy = cluster_data['center']
            color = cluster_data['color']
            cluster_particles = cluster_data['particles']

            # Calculate cluster radius
            if len(cluster_particles) > 0:
                max_dist = 0
                for p in cluster_particles:
                    dist = math.sqrt((p.get('x', cx) - cx)**2 + (p.get('y', cy) - cy)**2)
                    max_dist = max(max_dist, dist)
                radius = max_dist + self.cell_size * 0.8
            else:
                radius = self.cell_size

            # Background circle
            bg_color = QColor(color)
            bg_color.setAlpha(25)
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            painter.drawEllipse(QPointF(cx, cy), radius, radius)

            # Cluster label
            font = QFont('Arial', 11, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(color.lighter(140), 1))
            label_rect = QRectF(cx - 80, cy - radius - 30, 160, 25)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, cluster_name)

    def _draw_force_connections(self, painter, particles):
        """Draw connection lines between particles that share forces"""
        # Create force-particle mapping
        force_particles = {
            'Strong': [],
            'Electromagnetic': [],
            'Weak': [],
            'Gravitational': []
        }

        for p in particles:
            forces = p.get('all_forces', [])
            for force in forces:
                if force in force_particles:
                    force_particles[force].append(p)

        # Draw connections for each force
        force_colors = {
            'Strong': QColor(255, 100, 100, 40),
            'Electromagnetic': QColor(100, 150, 255, 40),
            'Weak': QColor(255, 180, 100, 40),
            'Gravitational': QColor(100, 255, 150, 20)
        }

        for force, particles_with_force in force_particles.items():
            if len(particles_with_force) < 2:
                continue

            color = force_colors.get(force, QColor(150, 150, 150, 30))
            painter.setPen(QPen(color, 1))

            # Connect particles in the same force group (limit connections for clarity)
            for i, p1 in enumerate(particles_with_force):
                # Only connect to nearby particles to avoid visual clutter
                for p2 in particles_with_force[i+1:min(i+4, len(particles_with_force))]:
                    if p1.get('x') and p2.get('x'):
                        # Only draw if particles are in different clusters
                        if p1.get('cluster_name') != p2.get('cluster_name'):
                            painter.drawLine(
                                QPointF(p1['x'], p1['y']),
                                QPointF(p2['x'], p2['y'])
                            )

    def _draw_legend(self, painter):
        """Draw force color legend"""
        # Get margins from config
        margins = get_layout_config().get_margins('quarks')

        legend_x = margins.get('left', 50) - 30
        legend_y = self.widget_height - margins.get('bottom', 50) - 50

        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawText(QPointF(legend_x, legend_y), "Force Network Legend:")

        forces = [
            ('Strong', QColor(255, 100, 100)),
            ('Electromagnetic', QColor(100, 150, 255)),
            ('Weak', QColor(255, 180, 100)),
            ('Gravitational', QColor(100, 255, 150))
        ]

        font_small = QFont('Arial', 9)
        painter.setFont(font_small)

        for i, (force, color) in enumerate(forces):
            x = legend_x + (i % 2) * 150
            y = legend_y + 20 + (i // 2) * 18

            # Color circle
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawEllipse(QPointF(x + 6, y - 4), 6, 6)

            # Label
            painter.setPen(QPen(QColor(180, 180, 180), 1))
            painter.drawText(QPointF(x + 18, y), force)
