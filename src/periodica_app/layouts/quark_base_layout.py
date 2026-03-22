#!/usr/bin/env python3
"""
Base Layout Renderer for Quark/Particle Visualization
Abstract base class defining the interface for all particle layout renderers.
"""

from abc import ABC, abstractmethod
import math
from PySide6.QtGui import QColor, QRadialGradient, QBrush, QPen, QLinearGradient, QFont
from PySide6.QtCore import Qt, QPointF, QRectF

from periodica.core.quark_enums import ParticleType, QuarkProperty, InteractionForce


class QuarkBaseLayoutRenderer(ABC):
    """
    Abstract base class for particle layout renderers.
    All layout renderers must implement create_layout() and paint() methods.
    """

    def __init__(self, widget_width, widget_height):
        """
        Initialize layout renderer with widget dimensions.

        Args:
            widget_width: Width of the widget in pixels
            widget_height: Height of the widget in pixels
        """
        self.widget_width = widget_width
        self.widget_height = widget_height

    @abstractmethod
    def create_layout(self, particles, **kwargs):
        """
        Create layout data for particles.

        Args:
            particles: List of particle dictionaries
            **kwargs: Additional layout-specific parameters

        Returns:
            List of particle dictionaries with layout-specific position data
        """
        pass

    @abstractmethod
    def paint(self, painter, particles, table_state, **kwargs):
        """
        Paint the layout.

        Args:
            painter: QPainter instance
            particles: List of particle dictionaries with layout data
            table_state: Dictionary containing visualization state
            **kwargs: Additional rendering parameters
        """
        pass

    def update_dimensions(self, widget_width, widget_height):
        """Update widget dimensions on resize"""
        self.widget_width = widget_width
        self.widget_height = widget_height

    def get_particle_at_position(self, x, y, particles):
        """
        Find particle at given position.

        Args:
            x: X coordinate
            y: Y coordinate
            particles: List of particle dictionaries with position data

        Returns:
            Particle dictionary or None
        """
        for particle in particles:
            if self._is_point_in_particle(x, y, particle):
                return particle
        return None

    def _is_point_in_particle(self, x, y, particle):
        """Check if point is within particle bounds"""
        px = particle.get('x', 0)
        py = particle.get('y', 0)
        size = particle.get('display_size', 60)
        half_size = size / 2

        return (px - half_size <= x <= px + half_size and
                py - half_size <= y <= py + half_size)

    def get_property_color(self, particle, property_name, table_state):
        """
        Get color based on property name.

        Args:
            particle: Particle dictionary
            property_name: Property to encode as color
            table_state: Table state for additional settings

        Returns:
            QColor instance
        """
        prop = QuarkProperty.from_string(property_name)

        if prop == QuarkProperty.PARTICLE_TYPE:
            ptype = particle.get('particle_type', ParticleType.UNKNOWN)
            r, g, b = ParticleType.get_color(ptype)
            return QColor(r, g, b)

        elif prop == QuarkProperty.MASS:
            mass = particle.get('Mass_MeVc2', 0) or 0
            # Log scale for mass (ranges from 0 to ~173000 MeV for top quark)
            if mass > 0:
                log_mass = math.log10(mass + 1)
                normalized = min(log_mass / 6, 1.0)  # log10(1000000) = 6
            else:
                normalized = 0
            # Blue (low) to Red (high)
            return QColor.fromHsvF(0.66 * (1 - normalized), 0.8, 0.9)

        elif prop == QuarkProperty.CHARGE:
            charge = particle.get('Charge_e', 0) or 0
            # Map charge to hue: negative=blue, zero=white, positive=red
            if charge < 0:
                intensity = min(abs(charge), 1.0)
                return QColor(int(100 + 155 * (1-intensity)), int(100 + 155 * (1-intensity)), 255)
            elif charge > 0:
                intensity = min(charge, 1.0)
                return QColor(255, int(100 + 155 * (1-intensity)), int(100 + 155 * (1-intensity)))
            else:
                return QColor(200, 200, 200)

        elif prop == QuarkProperty.SPIN:
            spin = particle.get('Spin_hbar', 0) or 0
            if spin == 0:
                return QColor(180, 100, 230)  # Purple for scalars
            elif spin == 0.5:
                return QColor(100, 180, 230)  # Blue for spin-1/2
            elif spin == 1:
                return QColor(230, 180, 100)  # Orange for spin-1
            else:
                return QColor(150, 150, 150)

        elif prop == QuarkProperty.GENERATION:
            gen = particle.get('generation_num', -1)
            colors = {
                1: QColor(100, 200, 100),  # Green - first gen
                2: QColor(200, 200, 100),  # Yellow - second gen
                3: QColor(200, 100, 100),  # Red - third gen
                0: QColor(100, 100, 200),  # Blue - bosons
                -1: QColor(150, 150, 150)  # Gray - unknown
            }
            return colors.get(gen, QColor(150, 150, 150))

        elif prop == QuarkProperty.STABILITY:
            stability = particle.get('Stability', 'Unknown')
            if stability == 'Stable':
                return QColor(100, 200, 100)  # Green
            elif stability == 'Unstable':
                return QColor(200, 100, 100)  # Red
            else:
                return QColor(200, 200, 100)  # Yellow

        elif prop == QuarkProperty.INTERACTION:
            forces = particle.get('InteractionForces', [])
            if 'Strong' in forces:
                return QColor(255, 100, 100)  # Red
            elif 'Electromagnetic' in forces and 'Weak' in forces:
                return QColor(200, 150, 255)  # Purple
            elif 'Electromagnetic' in forces:
                return QColor(100, 150, 255)  # Blue
            elif 'Weak' in forces:
                return QColor(255, 200, 100)  # Orange
            else:
                return QColor(150, 255, 150)  # Green (gravity only)

        return QColor(150, 150, 150)

    def draw_particle_cell(self, painter, particle, table_state, passes_filter=True):
        """
        Draw a single particle cell.

        Args:
            painter: QPainter instance
            particle: Particle dictionary with position data
            table_state: Visualization state
            passes_filter: Whether particle passes current filters
        """
        x = particle.get('x', 0)
        y = particle.get('y', 0)
        size = particle.get('display_size', 60)

        # Alpha for filtered particles
        alpha = 255 if passes_filter else 80

        # Get fill color
        fill_property = table_state.get('fill_property', 'particle_type')
        fill_color = self.get_property_color(particle, fill_property, table_state)
        fill_color.setAlpha(alpha)

        # Check if hovered or selected
        hovered = table_state.get('hovered_particle') == particle
        selected = table_state.get('selected_particle') == particle

        if hovered:
            fill_color = fill_color.lighter(130)
        if selected:
            fill_color = fill_color.lighter(150)

        # Draw glow if enabled
        glow_property = table_state.get('glow_property', 'none')
        if glow_property != 'none' and passes_filter:
            glow_size = self._get_glow_size(particle, glow_property)
            if glow_size > 0:
                self._draw_glow(painter, x, y, glow_size, fill_color, alpha / 255)

        # Draw main cell
        rect = QRectF(x - size/2, y - size/2, size, size)

        # Background gradient
        gradient = QRadialGradient(x, y, size/2)
        gradient.setColorAt(0, fill_color.lighter(115))
        gradient.setColorAt(1, fill_color)
        painter.setBrush(QBrush(gradient))

        # Border
        border_property = table_state.get('border_property', 'charge')
        border_color = self.get_property_color(particle, border_property, table_state)
        border_color.setAlpha(alpha)
        border_width = 2 if not selected else 4
        painter.setPen(QPen(border_color, border_width))

        # Draw rounded rectangle
        painter.drawRoundedRect(rect, 8, 8)

        # Draw symbol
        self._draw_particle_text(painter, particle, x, y, size, alpha)

    def _draw_particle_text(self, painter, particle, x, y, size, alpha):
        """Draw particle symbol and name"""
        # Symbol (large)
        symbol = particle.get('Symbol', '?')
        painter.setPen(QPen(QColor(255, 255, 255, alpha), 1))
        font = QFont('Arial', int(size * 0.35), QFont.Weight.Bold)
        painter.setFont(font)
        symbol_rect = QRectF(x - size/2, y - size/4, size, size/2)
        painter.drawText(symbol_rect, Qt.AlignmentFlag.AlignCenter, symbol)

        # Name (smaller, below symbol)
        name = particle.get('Name', 'Unknown')
        # Shorten long names
        if len(name) > 10:
            name = name[:9] + '...'
        font_small = QFont('Arial', int(size * 0.12))
        painter.setFont(font_small)
        painter.setPen(QPen(QColor(200, 200, 200, alpha), 1))
        name_rect = QRectF(x - size/2, y + size/6, size, size/4)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, name)

        # Mass (tiny, at bottom)
        mass_display = particle.get('mass_display', '')
        if mass_display and size > 50:
            font_tiny = QFont('Arial', int(size * 0.1))
            painter.setFont(font_tiny)
            painter.setPen(QPen(QColor(180, 180, 180, alpha), 1))
            mass_rect = QRectF(x - size/2, y + size/3, size, size/6)
            painter.drawText(mass_rect, Qt.AlignmentFlag.AlignCenter, mass_display)

    def _get_glow_size(self, particle, glow_property):
        """Calculate glow size based on property"""
        prop = QuarkProperty.from_string(glow_property)

        if prop == QuarkProperty.MASS:
            mass = particle.get('Mass_MeVc2', 0) or 0
            if mass > 0:
                log_mass = math.log10(mass + 1)
                return 20 + 30 * min(log_mass / 6, 1.0)
            return 0

        elif prop == QuarkProperty.SPIN:
            spin = particle.get('Spin_hbar', 0) or 0
            return 20 + 30 * min(spin, 1.0)

        elif prop == QuarkProperty.STABILITY:
            stability = particle.get('Stability', 'Unknown')
            if stability == 'Stable':
                return 40
            elif stability == 'Unstable':
                return 20
            return 0

        return 0

    def _draw_glow(self, painter, x, y, glow_size, color, alpha_scale=1.0):
        """Draw glow effect"""
        if glow_size <= 0:
            return

        glow_grad = QRadialGradient(x, y, glow_size)
        glow_color = QColor(color)
        glow_color.setAlpha(int(100 * alpha_scale))
        glow_grad.setColorAt(0, glow_color)
        glow_color.setAlpha(0)
        glow_grad.setColorAt(1, glow_color)
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(x, y), glow_size, glow_size)

    def draw_category_label(self, painter, text, x, y, color=None):
        """Draw a category label"""
        if color is None:
            color = QColor(100, 150, 200, 200)

        painter.setPen(QPen(color, 1))
        font = QFont('Arial', 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QPointF(x, y), text)

    def draw_section_background(self, painter, rect, color, alpha=30):
        """Draw a section background"""
        bg_color = QColor(color)
        bg_color.setAlpha(alpha)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
