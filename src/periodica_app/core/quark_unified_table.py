#!/usr/bin/env python3
"""
QuarkUnifiedTable - Main visualization widget for particles
Handles all layout modes and user interactions for the Quarks tab.
"""

import json
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QFont, QGuiApplication)

from periodica.core.quark_enums import QuarkLayoutMode, QuarkProperty, ParticleType
from periodica.data.quark_loader import QuarkDataLoader
from periodica_app.layouts.quark_standard_layout import QuarkStandardLayoutRenderer
from periodica_app.layouts.quark_linear_layout import QuarkLinearLayoutRenderer
from periodica_app.layouts.quark_circular_layout import QuarkCircularLayoutRenderer
from periodica_app.layouts.quark_alternative_layout import QuarkAlternativeLayoutRenderer
from periodica_app.layouts.quark_force_network_layout import QuarkForceNetworkLayoutRenderer
from periodica_app.layouts.quark_mass_spiral_layout import QuarkMassSpiralLayoutRenderer
from periodica_app.layouts.quark_fermion_boson_layout import QuarkFermionBosonLayoutRenderer
from periodica_app.layouts.quark_charge_mass_layout import QuarkChargeMassLayoutRenderer


class QuarkUnifiedTable(QWidget):
    """Unified widget for displaying particle visualizations in multiple layouts"""

    # Signals
    quark_selected = Signal(dict)  # Emitted when a quark/particle is clicked
    quark_hovered = Signal(dict)   # Emitted when a quark/particle is hovered

    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 500)
        self.setMouseTracking(True)

        # Data
        self.loader = QuarkDataLoader()
        self.particles = []
        self.base_particles = []

        # Layout state
        self.layout_mode = QuarkLayoutMode.STANDARD_MODEL
        self.current_renderer = None

        # Interaction state
        self.hovered_quark = None
        self.selected_quark = None

        # Visual property mappings
        self.fill_property = "particle_type"
        self.border_property = "charge"
        self.glow_property = "mass"

        # Linear layout ordering
        self.order_property = "mass"

        # Filters
        self.filters = {
            'mass': {'min': 0, 'max': float('inf'), 'active': False},
            'charge': {'min': -2, 'max': 2, 'active': False},
            'spin': {'min': 0, 'max': 2, 'active': False}
        }

        # Display options
        self.show_antiparticles = False
        self.show_composites = False
        self.show_connections = False

        # Zoom and pan
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # Create renderers first (needed by _update_layout)
        self._create_renderers()
        # Then load data
        self.load_particle_data()

    def load_particle_data(self):
        """Load particle data from JSON files"""
        self.base_particles = self.loader.load_all_particles(
            include_antiparticles=self.show_antiparticles,
            include_composite=self.show_composites
        )
        self._update_layout()

    def _create_renderers(self):
        """Create layout renderer instances"""
        self.renderers = {
            QuarkLayoutMode.STANDARD_MODEL: QuarkStandardLayoutRenderer(self.width(), self.height()),
            QuarkLayoutMode.LINEAR: QuarkLinearLayoutRenderer(self.width(), self.height()),
            QuarkLayoutMode.CIRCULAR: QuarkCircularLayoutRenderer(self.width(), self.height()),
            QuarkLayoutMode.ALTERNATIVE: QuarkAlternativeLayoutRenderer(self.width(), self.height()),
            QuarkLayoutMode.FORCE_NETWORK: QuarkForceNetworkLayoutRenderer(self.width(), self.height()),
            QuarkLayoutMode.MASS_SPIRAL: QuarkMassSpiralLayoutRenderer(self.width(), self.height()),
            QuarkLayoutMode.FERMION_BOSON: QuarkFermionBosonLayoutRenderer(self.width(), self.height()),
            QuarkLayoutMode.CHARGE_MASS: QuarkChargeMassLayoutRenderer(self.width(), self.height())
        }
        self.current_renderer = self.renderers[self.layout_mode]

    def _update_layout(self):
        """Update particle positions based on current layout mode"""
        if not self.base_particles:
            return

        # Filter particles based on settings
        filtered = self.base_particles.copy()
        if not self.show_antiparticles:
            filtered = [p for p in filtered if not p.get('_is_antiparticle', False)]
        if not self.show_composites:
            filtered = [p for p in filtered if not p.get('is_composite', False)]

        # Apply classification filter (quarks, leptons, bosons)
        if hasattr(self, 'classification_filters'):
            filtered = [p for p in filtered if self._passes_classification_filter(p)]

        # Apply generation filter (1st, 2nd, 3rd generation)
        if hasattr(self, 'generation_filters'):
            filtered = [p for p in filtered if self._passes_generation_filter(p)]

        # Apply charge type filter (positive, negative, neutral)
        if hasattr(self, 'charge_type_filters'):
            filtered = [p for p in filtered if self._passes_charge_type_filter(p)]

        # Create layout
        self.current_renderer = self.renderers.get(self.layout_mode)
        if self.current_renderer:
            self.current_renderer.update_dimensions(self.width(), self.height())
            kwargs = {}
            if self.layout_mode == QuarkLayoutMode.LINEAR:
                kwargs['sort_property'] = self.order_property
            self.particles = self.current_renderer.create_layout(filtered, **kwargs)
        else:
            self.particles = filtered

        self.update()

    def _passes_classification_filter(self, particle):
        """Check if particle passes the classification filter"""
        if not hasattr(self, 'classification_filters'):
            return True

        # Get particle type
        ptype = particle.get('Type', '').lower()
        particle_classification = particle.get('classification', '').lower()

        # Determine classification
        is_quark = 'quark' in ptype or particle_classification == 'quark'
        is_lepton = 'lepton' in ptype or 'electron' in ptype or 'muon' in ptype or 'tau' in ptype or 'neutrino' in ptype or particle_classification == 'lepton'
        is_boson = 'boson' in ptype or ptype in ['photon', 'gluon', 'z', 'w+', 'w-', 'higgs'] or particle_classification == 'boson'

        # Check against filters
        if is_quark and self.classification_filters.get('quark', True):
            return True
        if is_lepton and self.classification_filters.get('lepton', True):
            return True
        if is_boson and self.classification_filters.get('boson', True):
            return True

        # If none of the above matched but all filters are on, show it
        if not is_quark and not is_lepton and not is_boson:
            return all(self.classification_filters.values())

        return False

    def _passes_generation_filter(self, particle):
        """Check if particle passes the generation filter"""
        if not hasattr(self, 'generation_filters'):
            return True

        generation = particle.get('generation', particle.get('Generation', 0))

        # If particle has no generation (like bosons), check if any generation filter is on
        if generation == 0 or generation is None:
            return any(self.generation_filters.values())

        return self.generation_filters.get(generation, True)

    def _passes_charge_type_filter(self, particle):
        """Check if particle passes the charge type filter"""
        if not hasattr(self, 'charge_type_filters'):
            return True

        charge = particle.get('Charge_e', particle.get('charge', 0))
        if charge is None:
            charge = 0

        # Determine charge type
        if charge > 0:
            return self.charge_type_filters.get('positive', True)
        elif charge < 0:
            return self.charge_type_filters.get('negative', True)
        else:
            return self.charge_type_filters.get('neutral', True)

    def set_layout_mode(self, mode):
        """Set the layout mode"""
        if isinstance(mode, str):
            mode = QuarkLayoutMode.from_string(mode)
        self.layout_mode = mode
        self._update_layout()

    def set_fill_property(self, prop):
        """Set the property for fill color encoding"""
        self.fill_property = prop
        self.update()

    def set_border_property(self, prop):
        """Set the property for border color encoding"""
        self.border_property = prop
        self.update()

    def set_glow_property(self, prop):
        """Set the property for glow effect encoding"""
        self.glow_property = prop
        self.update()

    def set_order_property(self, prop):
        """Set the property for ordering in linear layout"""
        self.order_property = prop
        if self.layout_mode == QuarkLayoutMode.LINEAR:
            self._update_layout()

    def set_show_antiparticles(self, show):
        """Toggle antiparticle display"""
        if self.show_antiparticles != show:
            self.show_antiparticles = show
            self.load_particle_data()

    def set_show_composites(self, show):
        """Toggle composite particle display"""
        if self.show_composites != show:
            self.show_composites = show
            self.load_particle_data()

    def passes_filter(self, particle):
        """Check if a particle passes the current filters"""
        for prop, filter_settings in self.filters.items():
            if not filter_settings.get('active', False):
                continue

            value = None
            if prop == 'mass':
                value = particle.get('Mass_MeVc2', 0)
            elif prop == 'charge':
                value = particle.get('Charge_e', 0)
            elif prop == 'spin':
                value = particle.get('Spin_hbar', 0)

            if value is not None:
                if value < filter_settings['min'] or value > filter_settings['max']:
                    return False
        return True

    def get_table_state(self):
        """Get current visualization state for renderers"""
        return {
            'fill_property': self.fill_property,
            'border_property': self.border_property,
            'glow_property': self.glow_property,
            'order_property': self.order_property,
            'hovered_quark': self.hovered_quark,
            'selected_quark': self.selected_quark,
            'show_connections': self.show_connections
        }

    def paintEvent(self, event):
        """Paint the particle visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(15, 15, 30))

        # Apply zoom and pan
        painter.translate(self.pan_x, self.pan_y)
        painter.scale(self.zoom_level, self.zoom_level)

        # Draw title
        self._draw_title(painter)

        # Draw particles using current renderer
        if self.current_renderer and self.particles:
            table_state = self.get_table_state()
            self.current_renderer.paint(
                painter, self.particles, table_state,
                passes_filter_func=self.passes_filter
            )

        painter.end()

    def _draw_title(self, painter):
        """Draw layout mode title"""
        title = QuarkLayoutMode.get_display_name(self.layout_mode)
        font = QFont('Arial', 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(100, 150, 200), 1))
        painter.drawText(QPointF(20, 30), f"Layout: {title}")

        # Particle count
        font_small = QFont('Arial', 10)
        painter.setFont(font_small)
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawText(QPointF(20, 50), f"Showing {len(self.particles)} particles")

    def resizeEvent(self, event):
        """Handle widget resize"""
        super().resizeEvent(event)
        for renderer in self.renderers.values():
            renderer.update_dimensions(self.width(), self.height())
        self._update_layout()

    def mouseMoveEvent(self, event):
        """Handle mouse move for hover detection"""
        # Transform mouse position
        x = (event.position().x() - self.pan_x) / self.zoom_level
        y = (event.position().y() - self.pan_y) / self.zoom_level

        # Handle panning
        if self.is_panning:
            self.pan_x = event.position().x() - self.pan_start_x
            self.pan_y = event.position().y() - self.pan_start_y
            self.update()
            return

        # Find particle under mouse
        old_hovered = self.hovered_quark
        self.hovered_quark = None

        if self.current_renderer:
            self.hovered_quark = self.current_renderer.get_particle_at_position(
                x, y, self.particles
            )

        if old_hovered != self.hovered_quark:
            if self.hovered_quark:
                self.quark_hovered.emit(self.hovered_quark)
            self.update()

    def mousePressEvent(self, event):
        """Handle mouse press for selection and panning"""
        if event.button() == Qt.MouseButton.MiddleButton:
            # Start panning
            self.is_panning = True
            self.pan_start_x = event.position().x() - self.pan_x
            self.pan_start_y = event.position().y() - self.pan_y
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            # Select particle
            if self.hovered_quark:
                self.selected_quark = self.hovered_quark
                self.quark_selected.emit(self.selected_quark)
                # Copy particle data to clipboard
                clipboard_text = json.dumps(self.selected_quark, indent=2, default=str)
                QGuiApplication.clipboard().setText(clipboard_text)
                self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9

        # Zoom toward mouse position
        mouse_x = event.position().x()
        mouse_y = event.position().y()

        # Adjust pan to zoom toward mouse
        self.pan_x = mouse_x - (mouse_x - self.pan_x) * zoom_factor
        self.pan_y = mouse_y - (mouse_y - self.pan_y) * zoom_factor

        self.zoom_level *= zoom_factor
        self.zoom_level = max(0.3, min(3.0, self.zoom_level))
        self.update()

    def reset_view(self):
        """Reset zoom and pan to default"""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update()

    def set_gradient_colors(self, property_key, start_color, end_color):
        """Set custom gradient colors for a visual property encoding.

        Args:
            property_key: Visual encoding key (e.g., 'fill_color', 'border_color')
            start_color: Starting color (QColor or hex string)
            end_color: Ending color (QColor or hex string)
        """
        # Store custom gradient colors for use in rendering
        if not hasattr(self, 'custom_gradients'):
            self.custom_gradients = {}
        self.custom_gradients[property_key] = {
            'start': start_color if isinstance(start_color, str) else start_color.name(),
            'end': end_color if isinstance(end_color, str) else end_color.name()
        }
        self.update()

    def set_fade_value(self, property_key, fade_value):
        """Set the fade amount for a visual property encoding.

        Args:
            property_key: Visual encoding key (e.g., 'fill_color', 'border_color')
            fade_value: Fade amount from 0.0 (no fade) to 1.0 (fully transparent)
        """
        # Store fade values for use in rendering
        if not hasattr(self, 'fade_values'):
            self.fade_values = {}
        self.fade_values[property_key] = max(0.0, min(1.0, fade_value))
        self.update()

    def set_classification_filter(self, filters):
        """Set classification filter (quarks, leptons, bosons)

        Args:
            filters: dict with keys 'quark', 'lepton', 'boson' mapping to booleans
        """
        if not hasattr(self, 'classification_filters'):
            self.classification_filters = {'quark': True, 'lepton': True, 'boson': True}
        self.classification_filters.update(filters)
        self._update_layout()

    def set_generation_filter(self, filters):
        """Set generation filter (1st, 2nd, 3rd generation)

        Args:
            filters: dict with keys 1, 2, 3 mapping to booleans
        """
        if not hasattr(self, 'generation_filters'):
            self.generation_filters = {1: True, 2: True, 3: True}
        self.generation_filters.update(filters)
        self._update_layout()

    def set_charge_filter(self, filters):
        """Set charge type filter (positive, negative, neutral)

        Args:
            filters: dict with keys 'positive', 'negative', 'neutral' mapping to booleans
        """
        if not hasattr(self, 'charge_type_filters'):
            self.charge_type_filters = {'positive': True, 'negative': True, 'neutral': True}
        self.charge_type_filters.update(filters)
        self._update_layout()

    def reload_data(self):
        """Reload particle data from files and refresh the display"""
        self.load_particle_data()
        self.update()
