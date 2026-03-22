#!/usr/bin/env python3
"""
Standard Model Layout Renderer
Arranges particles in the classic Standard Model grid layout.
"""

import math
from PySide6.QtGui import QColor, QPen, QBrush, QFont
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica_app.layouts.quark_base_layout import QuarkBaseLayoutRenderer
from periodica.core.quark_enums import ParticleType
from periodica.data.layout_config_loader import get_quark_config, get_layout_config


class QuarkStandardLayoutRenderer(QuarkBaseLayoutRenderer):
    """
    Standard Model grid layout renderer.
    Arranges particles in the familiar Standard Model table format:
    - 3 generations of quarks (up-type and down-type)
    - 3 generations of leptons (charged and neutrinos)
    - Gauge bosons (gluon, photon, Z, W)
    - Higgs boson
    """

    def __init__(self, widget_width, widget_height):
        super().__init__(widget_width, widget_height)
        # Load configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')
        spacing = config.get_spacing('quarks')

        self.cell_size = card_size.get('default', 70)
        self.cell_spacing = spacing.get('cell', 10)
        self.section_spacing = spacing.get('section', 30)

        # Standard model grid configuration
        sm_config = get_quark_config('standard_model', default={})
        self.sm_rows = sm_config.get('row_count', 4)
        self.sm_cols = sm_config.get('col_count', 6)

    def create_layout(self, particles, **kwargs):
        """
        Create Standard Model grid layout.

        Args:
            particles: List of particle dictionaries
            **kwargs: Additional parameters

        Returns:
            List of particles with layout positions
        """
        # Get configuration values
        config = get_layout_config()
        card_size = config.get_card_size('quarks')
        margins = config.get_margins('quarks')

        min_size = card_size.get('min', 45)
        max_size = card_size.get('max', 120)

        # Calculate cell size based on widget dimensions
        available_width = self.widget_width - margins.get('left', 50) - margins.get('right', 50)
        available_height = self.widget_height - margins.get('top', 100) - margins.get('bottom', 50)

        # We need space for 5 columns (3 generations + bosons + Higgs) and 4 rows
        cols = 5
        rows = 4

        self.cell_size = min(
            (available_width - (cols + 1) * self.cell_spacing) / cols,
            (available_height - (rows + 1) * self.cell_spacing) / rows
        )
        self.cell_size = max(min_size, min(max_size, self.cell_size))

        # Starting position
        start_x = (self.widget_width - (cols * self.cell_size + (cols - 1) * self.cell_spacing)) / 2 + self.cell_size / 2
        start_y = margins.get('top', 100) + self.cell_size / 2

        # Position particles based on their Standard Model position
        for particle in particles:
            sm_row = particle.get('sm_row', -1)
            sm_col = particle.get('sm_col', -1)

            if sm_row >= 0 and sm_col >= 0:
                particle['x'] = start_x + sm_col * (self.cell_size + self.cell_spacing)
                particle['y'] = start_y + sm_row * (self.cell_size + self.cell_spacing)
                particle['display_size'] = self.cell_size
                particle['in_layout'] = True
            else:
                # Particles not in Standard Model layout
                particle['in_layout'] = False
                particle['display_size'] = self.cell_size * 0.8

        # Position antiparticles and composites below main layout
        non_sm_particles = [p for p in particles if not p.get('in_layout', False)]
        if non_sm_particles:
            extra_start_y = start_y + rows * (self.cell_size + self.cell_spacing) + self.section_spacing * 2
            for i, particle in enumerate(non_sm_particles):
                col = i % 6
                row = i // 6
                particle['x'] = start_x + col * (self.cell_size * 0.8 + self.cell_spacing)
                particle['y'] = extra_start_y + row * (self.cell_size * 0.8 + self.cell_spacing)

        return particles

    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the Standard Model layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Visualization state
            **kwargs: Additional parameters
        """
        passes_filter_func = kwargs.get('passes_filter_func', lambda p: True)

        # Draw section backgrounds and labels
        self._draw_section_backgrounds(painter, particles)

        # Draw particles
        for particle in particles:
            if particle.get('x') is not None and particle.get('y') is not None:
                passes = passes_filter_func(particle)
                self.draw_particle_cell(painter, particle, table_state, passes)

        # Draw generation labels
        self._draw_generation_labels(painter, particles)

    def _draw_section_backgrounds(self, painter, particles):
        """Draw background sections for different particle types"""
        # Find bounds for each section
        sm_particles = [p for p in particles if p.get('in_layout', False)]
        if not sm_particles:
            return

        # Get positions
        quarks = [p for p in sm_particles if p.get('sm_row', -1) in [0, 1] and p.get('sm_col', -1) < 3]
        leptons = [p for p in sm_particles if p.get('sm_row', -1) in [2, 3] and p.get('sm_col', -1) < 3]
        bosons = [p for p in sm_particles if p.get('sm_col', -1) >= 3]

        # Get spacing from config
        spacing = get_layout_config().get_spacing('quarks')
        padding = spacing.get('cell', 10) + 5

        # Quarks section (red-ish)
        if quarks:
            min_x = min(p['x'] for p in quarks) - self.cell_size/2 - padding
            max_x = max(p['x'] for p in quarks) + self.cell_size/2 + padding
            min_y = min(p['y'] for p in quarks) - self.cell_size/2 - padding
            max_y = max(p['y'] for p in quarks) + self.cell_size/2 + padding
            rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
            self.draw_section_background(painter, rect, QColor(230, 100, 100), 25)

        # Leptons section (blue)
        if leptons:
            min_x = min(p['x'] for p in leptons) - self.cell_size/2 - padding
            max_x = max(p['x'] for p in leptons) + self.cell_size/2 + padding
            min_y = min(p['y'] for p in leptons) - self.cell_size/2 - padding
            max_y = max(p['y'] for p in leptons) + self.cell_size/2 + padding
            rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
            self.draw_section_background(painter, rect, QColor(100, 180, 230), 25)

        # Bosons section (gold)
        if bosons:
            min_x = min(p['x'] for p in bosons) - self.cell_size/2 - padding
            max_x = max(p['x'] for p in bosons) + self.cell_size/2 + padding
            min_y = min(p['y'] for p in bosons) - self.cell_size/2 - padding
            max_y = max(p['y'] for p in bosons) + self.cell_size/2 + padding
            rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
            self.draw_section_background(painter, rect, QColor(230, 180, 100), 25)

    def _draw_generation_labels(self, painter, particles):
        """Draw generation and category labels"""
        sm_particles = [p for p in particles if p.get('in_layout', False)]
        if not sm_particles:
            return

        # Get first particle positions for labels
        first_gen = [p for p in sm_particles if p.get('sm_col', -1) == 0]
        second_gen = [p for p in sm_particles if p.get('sm_col', -1) == 1]
        third_gen = [p for p in sm_particles if p.get('sm_col', -1) == 2]

        painter.setPen(QPen(QColor(200, 200, 200), 1))
        font = QFont('Arial', 10)
        painter.setFont(font)

        # Get margins from config
        margins = get_layout_config().get_margins('quarks')
        label_y = margins.get('top', 100) - 30

        if first_gen:
            x = first_gen[0]['x']
            painter.drawText(QRectF(x - 40, label_y, 80, 20), Qt.AlignmentFlag.AlignCenter, "I")
        if second_gen:
            x = second_gen[0]['x']
            painter.drawText(QRectF(x - 40, label_y, 80, 20), Qt.AlignmentFlag.AlignCenter, "II")
        if third_gen:
            x = third_gen[0]['x']
            painter.drawText(QRectF(x - 40, label_y, 80, 20), Qt.AlignmentFlag.AlignCenter, "III")

        # Category labels (left side)
        quarks_row0 = [p for p in sm_particles if p.get('sm_row', -1) == 0 and p.get('sm_col', -1) == 0]
        quarks_row1 = [p for p in sm_particles if p.get('sm_row', -1) == 1 and p.get('sm_col', -1) == 0]
        leptons_row2 = [p for p in sm_particles if p.get('sm_row', -1) == 2 and p.get('sm_col', -1) == 0]
        leptons_row3 = [p for p in sm_particles if p.get('sm_row', -1) == 3 and p.get('sm_col', -1) == 0]

        label_x = margins.get('left', 50) - 30
        font_small = QFont('Arial', 9)
        painter.setFont(font_small)

        if quarks_row0:
            y = quarks_row0[0]['y']
            painter.setPen(QPen(QColor(230, 150, 150), 1))
            painter.drawText(QRectF(label_x, y - 10, 60, 20), Qt.AlignmentFlag.AlignLeft, "up-type")
        if quarks_row1:
            y = quarks_row1[0]['y']
            painter.setPen(QPen(QColor(230, 150, 150), 1))
            painter.drawText(QRectF(label_x, y - 10, 60, 20), Qt.AlignmentFlag.AlignLeft, "down-type")
        if leptons_row2:
            y = leptons_row2[0]['y']
            painter.setPen(QPen(QColor(150, 200, 230), 1))
            painter.drawText(QRectF(label_x, y - 10, 60, 20), Qt.AlignmentFlag.AlignLeft, "charged")
        if leptons_row3:
            y = leptons_row3[0]['y']
            painter.setPen(QPen(QColor(150, 200, 230), 1))
            painter.drawText(QRectF(label_x, y - 10, 60, 20), Qt.AlignmentFlag.AlignLeft, "neutrinos")

        # Section titles
        font_title = QFont('Arial', 12, QFont.Weight.Bold)
        painter.setFont(font_title)

        quarks = [p for p in sm_particles if p.get('sm_row', -1) in [0, 1] and p.get('sm_col', -1) < 3]
        if quarks:
            x = (min(p['x'] for p in quarks) + max(p['x'] for p in quarks)) / 2
            y = min(p['y'] for p in quarks) - self.cell_size/2 - 30
            painter.setPen(QPen(QColor(230, 150, 150), 1))
            painter.drawText(QRectF(x - 50, y, 100, 20), Qt.AlignmentFlag.AlignCenter, "QUARKS")

        leptons = [p for p in sm_particles if p.get('sm_row', -1) in [2, 3] and p.get('sm_col', -1) < 3]
        if leptons:
            x = (min(p['x'] for p in leptons) + max(p['x'] for p in leptons)) / 2
            y = max(p['y'] for p in leptons) + self.cell_size/2 + 10
            painter.setPen(QPen(QColor(150, 200, 230), 1))
            painter.drawText(QRectF(x - 50, y, 100, 20), Qt.AlignmentFlag.AlignCenter, "LEPTONS")

        bosons = [p for p in sm_particles if p.get('sm_col', -1) >= 3]
        if bosons:
            x = (min(p['x'] for p in bosons) + max(p['x'] for p in bosons)) / 2
            y = max(p['y'] for p in bosons) + self.cell_size/2 + 10
            painter.setPen(QPen(QColor(230, 200, 150), 1))
            painter.drawText(QRectF(x - 50, y, 100, 20), Qt.AlignmentFlag.AlignCenter, "BOSONS")
