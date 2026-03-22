"""
Unified Grain Visualization Widget
Shared visualization component for grain structure across AlloyAnalysis and Create dialogs.
Features:
- Voronoi tessellation with IPF coloring
- Zoom/pan controls
- 3D domain with X,Y,Z size controls
- Perspective switching (XY, XZ, YZ views)
- Depth slicing for editing at different Z levels
"""

import math
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                                QSlider, QComboBox, QSpinBox, QDoubleSpinBox,
                                QWidget, QGroupBox, QPushButton, QCheckBox,
                                QFileDialog)
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QRadialGradient,
                           QPainterPath, QWheelEvent, QMouseEvent, QFont,
                           QImage)

# Try to import crystalline math for proper Voronoi
try:
    from periodica.utils.crystalline_math import VoronoiTessellation, Vec3, GrainCenter
    HAS_CRYSTALLINE = True
except ImportError:
    HAS_CRYSTALLINE = False


@dataclass
class GrainData:
    """Data structure for a single grain"""
    id: int
    x: float  # Normalized 0-1
    y: float
    z: float
    orientation: Tuple[float, float, float]  # Euler angles (phi1, phi, phi2)
    phase_id: int = 0

    def get_ipf_color(self) -> QColor:
        """Get IPF color based on orientation with enhanced saturation"""
        phi1, phi, phi2 = self.orientation
        # Enhanced IPF coloring with better saturation and contrast
        # Use full range for more vibrant colors
        r = int((phi1 / 360) * 180 + 75)
        g = int((phi / 90) * 180 + 75)
        b = int((phi2 / 90) * 180 + 75)
        return QColor(r, g, b, 220)


class GrainVisualizationCore(QFrame):
    """
    Core visualization widget for grain structure.
    Handles rendering, zoom, pan, and interaction.
    """

    grain_selected = Signal(int)  # Emitted when a grain is selected
    grain_moved = Signal(int, float, float, float)  # grain_id, x, y, z
    grain_added = Signal(float, float, float)  # x, y, z (normalized)
    grains_changed = Signal()  # Emitted when any grain data changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.setStyleSheet("""
            QFrame {
                background: rgba(20, 20, 35, 255);
                border: 2px solid #667eea;
                border-radius: 8px;
            }
        """)

        # Grain data
        self.grains: List[GrainData] = []
        self.voronoi: Optional[VoronoiTessellation] = None

        # Domain size (in micrometers)
        self.domain_x = 100.0
        self.domain_y = 100.0
        self.domain_z = 50.0

        # View settings
        self.view_plane = 'XY'  # 'XY', 'XZ', 'YZ'
        self.depth_slice = 0.5  # Normalized 0-1, position along the third axis
        self.depth_tolerance = 0.2  # How thick the slice is

        # Zoom and pan
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        # Interaction
        self.selected_grain: Optional[int] = None
        self.hovered_grain: Optional[int] = None
        self.dragging = False
        self.drag_start = None
        self.panning = False
        self.pan_start = None

        # Visual feedback for newly added grains
        self.newly_added_grain: Optional[int] = None
        self.add_animation_frame = 0

        # Display options
        self.show_grain_centers = True
        self.show_grain_ids = False
        self.show_boundaries = True
        self.boundary_width = 2.5  # Enhanced boundary visibility
        self.render_resolution = 2  # Higher resolution for smoother rendering

        # Editable mode
        self.editable = True

    def set_grains(self, grains: List[GrainData]):
        """Set grain data"""
        self.grains = grains
        self._rebuild_voronoi()
        self.update()

    def set_grains_from_dict(self, grain_dicts: List[Dict]):
        """Set grains from list of dictionaries"""
        self.grains = []
        for i, g in enumerate(grain_dicts):
            self.grains.append(GrainData(
                id=g.get('id', i),
                x=g.get('x', random.random()),
                y=g.get('y', random.random()),
                z=g.get('z', random.random()),
                orientation=tuple(g.get('orientation', [random.uniform(0, 360),
                                                         random.uniform(0, 90),
                                                         random.uniform(0, 90)])),
                phase_id=g.get('phase_id', 0)
            ))
        self._rebuild_voronoi()
        self.update()

    def generate_random_grains(self, num_grains: int, seed: int = 42,
                                distribution: str = 'poisson'):
        """Generate random grain structure"""
        random.seed(seed)
        self.grains = []

        if distribution == 'poisson' and HAS_CRYSTALLINE:
            # Use Voronoi tessellation for proper Poisson distribution
            voronoi = VoronoiTessellation(seed)
            centers = voronoi.generate_grain_centers_2d(
                1.0, 1.0, num_grains, 'poisson'
            )
            for i, center in enumerate(centers):
                self.grains.append(GrainData(
                    id=i,
                    x=center.position.x,
                    y=center.position.y,
                    z=random.random(),
                    orientation=center.orientation,
                    phase_id=0
                ))
        elif distribution == 'regular':
            # Grid with perturbation
            side = int(math.sqrt(num_grains)) + 1
            idx = 0
            for row in range(side):
                for col in range(side):
                    if idx >= num_grains:
                        break
                    x = (col + 0.5 + random.gauss(0, 0.15)) / side
                    y = (row + 0.5 + random.gauss(0, 0.15)) / side
                    x = max(0.05, min(0.95, x))
                    y = max(0.05, min(0.95, y))
                    self.grains.append(GrainData(
                        id=idx,
                        x=x, y=y, z=random.random(),
                        orientation=(random.uniform(0, 360),
                                   random.uniform(0, 90),
                                   random.uniform(0, 90)),
                        phase_id=0
                    ))
                    idx += 1
        else:
            # Random distribution
            for i in range(num_grains):
                self.grains.append(GrainData(
                    id=i,
                    x=random.random(),
                    y=random.random(),
                    z=random.random(),
                    orientation=(random.uniform(0, 360),
                               random.uniform(0, 90),
                               random.uniform(0, 90)),
                    phase_id=0
                ))

        self._rebuild_voronoi()
        self.update()
        self.grains_changed.emit()

    def _rebuild_voronoi(self):
        """Rebuild Voronoi tessellation from grain data"""
        if not HAS_CRYSTALLINE or not self.grains:
            self.voronoi = None
            return

        self.voronoi = VoronoiTessellation(42)
        self.voronoi.grain_centers = []

        for grain in self.grains:
            # Get coordinates based on view plane
            if self.view_plane == 'XY':
                px, py = grain.x, grain.y
                pz = grain.z
            elif self.view_plane == 'XZ':
                px, py = grain.x, grain.z
                pz = grain.y
            else:  # YZ
                px, py = grain.y, grain.z
                pz = grain.x

            # Filter by depth slice
            if abs(pz - self.depth_slice) <= self.depth_tolerance:
                pos = Vec3(px, py, 0)
                self.voronoi.grain_centers.append(GrainCenter(
                    position=pos,
                    grain_id=grain.id,
                    orientation=grain.orientation,
                    phase_id=grain.phase_id
                ))

    def _get_visible_grains(self) -> List[GrainData]:
        """Get grains visible in current slice"""
        visible = []
        for grain in self.grains:
            if self.view_plane == 'XY':
                depth = grain.z
            elif self.view_plane == 'XZ':
                depth = grain.y
            else:  # YZ
                depth = grain.x

            if abs(depth - self.depth_slice) <= self.depth_tolerance:
                visible.append(grain)
        return visible

    def _grain_to_screen(self, grain: GrainData) -> Tuple[float, float]:
        """Convert grain position to screen coordinates"""
        # Get coordinates based on view plane
        if self.view_plane == 'XY':
            x, y = grain.x, grain.y
        elif self.view_plane == 'XZ':
            x, y = grain.x, grain.z
        else:  # YZ
            x, y = grain.y, grain.z

        # Apply zoom and pan
        w, h = self.width(), self.height()
        margin = 20

        screen_x = margin + (x * self.zoom + self.pan_x) * (w - 2 * margin)
        screen_y = margin + (y * self.zoom + self.pan_y) * (h - 2 * margin)

        return screen_x, screen_y

    def _screen_to_grain(self, sx: float, sy: float) -> Tuple[float, float]:
        """Convert screen coordinates to grain position"""
        w, h = self.width(), self.height()
        margin = 20

        x = ((sx - margin) / (w - 2 * margin) - self.pan_x) / self.zoom
        y = ((sy - margin) / (h - 2 * margin) - self.pan_y) / self.zoom

        return max(0, min(1, x)), max(0, min(1, y))

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 20

        # Draw background grid
        self._draw_grid(painter, margin, w, h)

        # Draw grains
        if HAS_CRYSTALLINE and self.voronoi and self.voronoi.grain_centers:
            self._draw_voronoi_grains(painter, margin, w, h)
        else:
            self._draw_simple_grains(painter, margin, w, h)

        # Draw grain centers
        if self.show_grain_centers:
            self._draw_grain_centers(painter)

        # Draw info overlay
        self._draw_info_overlay(painter, w, h)

        painter.end()

    def _draw_grid(self, painter: QPainter, margin: int, w: int, h: int):
        """Draw enhanced background grid with depth indicator"""
        # Draw subtle grid lines
        painter.setPen(QPen(QColor(45, 45, 70), 1))

        # Draw grid lines
        for i in range(11):
            t = i / 10.0
            x = margin + t * self.zoom * (w - 2 * margin) + self.pan_x * (w - 2 * margin)
            y = margin + t * self.zoom * (h - 2 * margin) + self.pan_y * (h - 2 * margin)

            if margin <= x <= w - margin:
                painter.drawLine(int(x), margin, int(x), h - margin)
            if margin <= y <= h - margin:
                painter.drawLine(margin, int(y), w - margin, int(y))

        # Draw depth slice indicator bar
        slice_bar_height = 8
        slice_bar_y = h - margin - slice_bar_height - 5
        slice_bar_width = w - 2 * margin - 160  # Leave space for domain info
        slice_bar_x = margin

        # Background bar
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(40, 40, 60, 180)))
        painter.drawRoundedRect(slice_bar_x, slice_bar_y, slice_bar_width, slice_bar_height, 3, 3)

        # Active slice position
        slice_pos = slice_bar_x + int(self.depth_slice * slice_bar_width)
        slice_width = int(self.depth_tolerance * 2 * slice_bar_width)

        # Slice range
        painter.setBrush(QBrush(QColor(100, 150, 255, 120)))
        slice_range_x = max(slice_bar_x, slice_pos - slice_width // 2)
        slice_range_width = min(slice_width, slice_bar_x + slice_bar_width - slice_range_x)
        painter.drawRoundedRect(slice_range_x, slice_bar_y, slice_range_width, slice_bar_height, 3, 3)

        # Slice center marker
        painter.setBrush(QBrush(QColor(150, 200, 255, 255)))
        painter.drawEllipse(slice_pos - 3, slice_bar_y + slice_bar_height // 2 - 3, 6, 6)

    def _draw_voronoi_grains(self, painter: QPainter, margin: int, w: int, h: int):
        """Draw grains using Voronoi tessellation with enhanced visual quality"""
        draw_w = w - 2 * margin
        draw_h = h - 2 * margin

        # Build color map
        color_map = {}
        for grain in self.grains:
            color_map[grain.id] = grain.get_ipf_color()

        # Render Voronoi cells with antialiasing
        res = self.render_resolution
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        for py in range(margin, h - margin, res):
            for px in range(margin, w - margin, res):
                # Convert to normalized coordinates
                nx = ((px - margin) / draw_w - self.pan_x) / self.zoom
                ny = ((py - margin) / draw_h - self.pan_y) / self.zoom

                if not (0 <= nx <= 1 and 0 <= ny <= 1):
                    continue

                point = Vec3(nx, ny, 0)
                nearest, dist = self.voronoi.find_nearest_grain(point)

                if nearest:
                    # Check if on boundary with improved detection
                    is_boundary = self.show_boundaries and self.voronoi.is_on_boundary(
                        point, self.boundary_width / 600.0
                    )

                    if is_boundary:
                        # Enhanced boundary appearance with slight gradient
                        color = QColor(25, 25, 40, 240)
                    else:
                        color = color_map.get(nearest.grain_id, QColor(128, 128, 128))
                        # Enhanced visual feedback for selection/hover
                        if nearest.grain_id == self.selected_grain:
                            color = color.lighter(140)
                            # Add subtle glow effect
                            painter.setOpacity(0.95)
                        elif nearest.grain_id == self.hovered_grain:
                            color = color.lighter(120)
                            painter.setOpacity(0.9)
                        else:
                            painter.setOpacity(1.0)

                    painter.fillRect(px, py, res, res, color)
                    painter.setOpacity(1.0)

    def _draw_simple_grains(self, painter: QPainter, margin: int, w: int, h: int):
        """Fallback simple grain rendering"""
        visible = self._get_visible_grains()

        for grain in visible:
            sx, sy = self._grain_to_screen(grain)

            if not (margin <= sx <= w - margin and margin <= sy <= h - margin):
                continue

            color = grain.get_ipf_color()
            if grain.id == self.selected_grain:
                color = color.lighter(130)
            elif grain.id == self.hovered_grain:
                color = color.lighter(115)

            # Draw grain as ellipse
            size = 30 * self.zoom
            gradient = QRadialGradient(sx, sy, size)
            gradient.setColorAt(0, color.lighter(120))
            gradient.setColorAt(0.7, color)
            gradient.setColorAt(1, color.darker(120))

            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(QColor(20, 20, 30), 2))
            painter.drawEllipse(QPointF(sx, sy), size, size)

    def _draw_grain_centers(self, painter: QPainter):
        """Draw grain center markers with enhanced visual feedback"""
        visible = self._get_visible_grains()

        for grain in visible:
            sx, sy = self._grain_to_screen(grain)

            # Special animation for newly added grains
            if grain.id == self.newly_added_grain and self.add_animation_frame < 20:
                # Pulsing ring animation
                alpha = int(255 * (1 - self.add_animation_frame / 20))
                radius = 15 + self.add_animation_frame * 2
                painter.setPen(QPen(QColor(100, 255, 100, alpha), 3))
                painter.setBrush(QBrush(QColor(100, 255, 100, alpha // 3)))
                painter.drawEllipse(QPointF(sx, sy), radius, radius)

            # Enhanced highlight for hover with pulsing effect
            if grain.id == self.hovered_grain:
                # Outer glow ring
                painter.setPen(QPen(QColor(255, 255, 100, 180), 2))
                painter.setBrush(QBrush(QColor(255, 255, 100, 40)))
                painter.drawEllipse(QPointF(sx, sy), 14, 14)
                # Inner highlight ring
                painter.setPen(QPen(QColor(255, 255, 150, 220), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(sx, sy), 10, 10)

            # Enhanced highlight for selection with double ring
            if grain.id == self.selected_grain:
                # Outer selection ring
                painter.setPen(QPen(QColor(100, 255, 255, 200), 3))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(sx, sy), 18, 18)
                # Inner selection ring
                painter.setPen(QPen(QColor(150, 255, 255, 255), 2))
                painter.drawEllipse(QPointF(sx, sy), 14, 14)

            # Enhanced center point with gradient
            gradient = QRadialGradient(sx, sy, 5)
            gradient.setColorAt(0, QColor(255, 255, 255, 255))
            gradient.setColorAt(0.7, QColor(220, 220, 220, 255))
            gradient.setColorAt(1, QColor(180, 180, 180, 200))
            painter.setPen(QPen(QColor(80, 80, 100), 1))
            painter.setBrush(QBrush(gradient))
            painter.drawEllipse(QPointF(sx, sy), 5, 5)

            # Draw ID if enabled with better visibility
            if self.show_grain_ids:
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                # Draw text with shadow for better readability
                painter.setPen(QPen(QColor(0, 0, 0, 180)))
                painter.drawText(int(sx + 9), int(sy - 7), str(grain.id))
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(int(sx + 8), int(sy - 8), str(grain.id))

    def _draw_info_overlay(self, painter: QPainter, w: int, h: int):
        """Draw information overlay with improved readability"""
        # Semi-transparent background for info panel
        info_bg = QRectF(5, 5, 240, 70)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(20, 20, 35, 180)))
        painter.drawRoundedRect(info_bg, 5, 5)

        painter.setPen(QPen(QColor(220, 220, 240)))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))

        # View info with color coding
        info_lines = [
            (f"View: {self.view_plane}", QColor(100, 200, 255)),
            (f"Grains: {len(self.grains)} ({len(self._get_visible_grains())} visible)", QColor(150, 255, 150)),
            (f"Slice: {self.depth_slice:.2f} ± {self.depth_tolerance:.2f}", QColor(255, 200, 100)),
            (f"Zoom: {self.zoom:.1f}x", QColor(255, 150, 200)),
        ]

        y = 18
        for line, color in info_lines:
            painter.setPen(QPen(color))
            painter.drawText(12, y, line)
            y += 14

        # Domain size with background
        domain_text = f"Domain: {self.domain_x:.0f}×{self.domain_y:.0f}×{self.domain_z:.0f} µm"
        domain_width = 150
        domain_bg = QRectF(w - domain_width - 10, 5, domain_width, 25)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(20, 20, 35, 180)))
        painter.drawRoundedRect(domain_bg, 5, 5)
        painter.setPen(QPen(QColor(200, 220, 255)))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(int(w - domain_width - 5), 20, domain_text)

        # Enhanced controls hint with background
        hint_text = "Scroll: Zoom | Drag: Pan | Double-click: Add | Right-click: Select"
        hint_width = 470
        hint_bg = QRectF(5, h - 30, hint_width, 25)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(20, 20, 35, 180)))
        painter.drawRoundedRect(hint_bg, 5, 5)
        painter.setPen(QPen(QColor(180, 180, 200)))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(12, h - 12, hint_text)

    def wheelEvent(self, event: QWheelEvent):
        """Handle zoom with mouse wheel"""
        delta = event.angleDelta().y()

        if delta > 0:
            self.zoom = min(5.0, self.zoom * 1.1)
        else:
            self.zoom = max(0.2, self.zoom / 1.1)

        self._rebuild_voronoi()
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on a grain center
            clicked_grain = self._find_grain_at(event.pos().x(), event.pos().y())

            if clicked_grain is not None and self.editable:
                self.dragging = True
                self.drag_start = (event.pos().x(), event.pos().y())
                self.selected_grain = clicked_grain
                self.grain_selected.emit(clicked_grain)
            else:
                # Start panning
                self.panning = True
                self.pan_start = (event.pos().x(), event.pos().y())

        elif event.button() == Qt.MouseButton.RightButton:
            # Select grain
            clicked_grain = self._find_grain_at(event.pos().x(), event.pos().y())
            self.selected_grain = clicked_grain
            if clicked_grain is not None:
                self.grain_selected.emit(clicked_grain)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging and self.selected_grain is not None:
            # Smooth grain dragging with real-time feedback
            gx, gy = self._screen_to_grain(event.pos().x(), event.pos().y())

            for grain in self.grains:
                if grain.id == self.selected_grain:
                    if self.view_plane == 'XY':
                        grain.x, grain.y = gx, gy
                    elif self.view_plane == 'XZ':
                        grain.x, grain.z = gx, gy
                    else:  # YZ
                        grain.y, grain.z = gx, gy
                    break

            # Rebuild Voronoi for smooth real-time updates
            self._rebuild_voronoi()
            self.update()
            # Set cursor to indicate dragging
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        elif self.panning:
            # Smoother panning with improved responsiveness
            dx = (event.pos().x() - self.pan_start[0]) / (self.width() - 40)
            dy = (event.pos().y() - self.pan_start[1]) / (self.height() - 40)
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start = (event.pos().x(), event.pos().y())
            self.update()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        else:
            # Update hover with cursor feedback
            hovered = self._find_grain_at(event.pos().x(), event.pos().y())
            if hovered != self.hovered_grain:
                self.hovered_grain = hovered
                # Change cursor on hover
                if hovered is not None:
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.dragging and self.selected_grain is not None:
            # Emit grain moved signal
            for grain in self.grains:
                if grain.id == self.selected_grain:
                    self.grain_moved.emit(grain.id, grain.x, grain.y, grain.z)
                    break
            self.grains_changed.emit()

        self.dragging = False
        self.panning = False
        self.drag_start = None
        self.pan_start = None

        # Reset cursor
        hovered = self._find_grain_at(event.pos().x(), event.pos().y())
        if hovered is not None:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if not self.editable:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Add new grain
            gx, gy = self._screen_to_grain(event.pos().x(), event.pos().y())

            # Determine z based on view plane and slice
            if self.view_plane == 'XY':
                new_grain = GrainData(
                    id=max((g.id for g in self.grains), default=-1) + 1,
                    x=gx, y=gy, z=self.depth_slice,
                    orientation=(random.uniform(0, 360), random.uniform(0, 90), random.uniform(0, 90))
                )
            elif self.view_plane == 'XZ':
                new_grain = GrainData(
                    id=max((g.id for g in self.grains), default=-1) + 1,
                    x=gx, y=self.depth_slice, z=gy,
                    orientation=(random.uniform(0, 360), random.uniform(0, 90), random.uniform(0, 90))
                )
            else:  # YZ
                new_grain = GrainData(
                    id=max((g.id for g in self.grains), default=-1) + 1,
                    x=self.depth_slice, y=gx, z=gy,
                    orientation=(random.uniform(0, 360), random.uniform(0, 90), random.uniform(0, 90))
                )

            self.grains.append(new_grain)
            self._rebuild_voronoi()

            # Trigger add animation
            self.newly_added_grain = new_grain.id
            self.add_animation_frame = 0
            self._animate_grain_add()

            self.grain_added.emit(new_grain.x, new_grain.y, new_grain.z)
            self.grains_changed.emit()

    def _animate_grain_add(self):
        """Animate newly added grain"""
        if self.add_animation_frame < 20:
            self.add_animation_frame += 1
            self.update()
            # Schedule next frame using QTimer
            from PySide6.QtCore import QTimer
            QTimer.singleShot(30, self._animate_grain_add)
        else:
            self.newly_added_grain = None

    def _find_grain_at(self, sx: float, sy: float) -> Optional[int]:
        """Find grain at screen coordinates with improved hit detection"""
        visible = self._get_visible_grains()

        for grain in visible:
            gsx, gsy = self._grain_to_screen(grain)
            dist = math.sqrt((sx - gsx) ** 2 + (sy - gsy) ** 2)
            # Larger hit area for easier selection
            if dist < 18:
                return grain.id

        return None

    def get_grain_data_for_json(self) -> Dict:
        """Get grain structure data for JSON export"""
        return {
            'domain_size': {
                'x_um': self.domain_x,
                'y_um': self.domain_y,
                'z_um': self.domain_z
            },
            'num_grains': len(self.grains),
            'grains': [
                {
                    'id': g.id,
                    'x': g.x, 'y': g.y, 'z': g.z,
                    'orientation': list(g.orientation),
                    'phase_id': g.phase_id
                }
                for g in self.grains
            ]
        }



    def export_to_png(self, filepath: str, width: int = 800, height: int = 600):
        from PySide6.QtCore import QSize
        image = QImage(QSize(width, height), QImage.Format.Format_ARGB32)
        image.fill(QColor(20, 20, 35, 255))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._render_to_painter(painter, width, height)
        painter.end()
        image.save(filepath, 'PNG')

    def export_to_svg(self, filepath: str, width: int = 800, height: int = 600):
        from PySide6.QtSvg import QSvgGenerator
        from PySide6.QtCore import QSize
        generator = QSvgGenerator()
        generator.setFileName(filepath)
        generator.setSize(QSize(width, height))
        generator.setViewBox(QRectF(0, 0, width, height))
        generator.setTitle('Grain Visualization')
        generator.setDescription('Grain structure visualization from Periodics')
        painter = QPainter(generator)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._render_to_painter(painter, width, height)
        painter.end()

    def _render_to_painter(self, painter: QPainter, width: int, height: int):
        margin = 20
        w, h = width, height
        painter.fillRect(0, 0, w, h, QColor(20, 20, 35, 255))
        self._draw_grid_to_painter(painter, margin, w, h)
        if HAS_CRYSTALLINE and self.voronoi and self.voronoi.grain_centers:
            self._draw_voronoi_grains_to_painter(painter, margin, w, h)
        else:
            self._draw_simple_grains_to_painter(painter, margin, w, h)
        if self.show_grain_centers:
            self._draw_grain_centers_to_painter(painter, margin, w, h)
        self._draw_info_overlay_to_painter(painter, margin, w, h)


class GrainVisualizationWidget(QWidget):
    """
    Complete grain visualization widget with controls.
    Combines GrainVisualizationCore with control panels.
    """

    grains_changed = Signal()

    def __init__(self, parent=None, editable: bool = True):
        super().__init__(parent)
        self.editable = editable
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Main visualization
        self.viz = GrainVisualizationCore()
        self.viz.editable = self.editable
        self.viz.grains_changed.connect(self.grains_changed.emit)
        layout.addWidget(self.viz, 1)

        # Controls panel
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(10)

        # View plane selector
        view_group = QWidget()
        view_layout = QHBoxLayout(view_group)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.addWidget(QLabel("View:"))
        self.view_combo = QComboBox()
        self.view_combo.addItems(['XY (Top)', 'XZ (Front)', 'YZ (Side)'])
        self.view_combo.currentIndexChanged.connect(self._on_view_changed)
        self.view_combo.setStyleSheet("QComboBox { min-width: 80px; }")
        view_layout.addWidget(self.view_combo)
        controls_layout.addWidget(view_group)

        # Depth slice slider
        slice_group = QWidget()
        slice_layout = QHBoxLayout(slice_group)
        slice_layout.setContentsMargins(0, 0, 0, 0)
        slice_layout.addWidget(QLabel("Depth:"))
        self.slice_slider = QSlider(Qt.Orientation.Horizontal)
        self.slice_slider.setRange(0, 100)
        self.slice_slider.setValue(50)
        self.slice_slider.setMaximumWidth(100)
        self.slice_slider.valueChanged.connect(self._on_slice_changed)
        slice_layout.addWidget(self.slice_slider)
        self.slice_label = QLabel("0.50")
        self.slice_label.setMinimumWidth(30)
        slice_layout.addWidget(self.slice_label)
        controls_layout.addWidget(slice_group)

        # Domain size controls (only if editable)
        if self.editable:
            domain_group = QWidget()
            domain_layout = QHBoxLayout(domain_group)
            domain_layout.setContentsMargins(0, 0, 0, 0)
            domain_layout.addWidget(QLabel("Size (µm):"))

            self.domain_x_spin = QSpinBox()
            self.domain_x_spin.setRange(10, 1000)
            self.domain_x_spin.setValue(100)
            self.domain_x_spin.setMaximumWidth(60)
            self.domain_x_spin.valueChanged.connect(self._on_domain_changed)
            domain_layout.addWidget(self.domain_x_spin)

            domain_layout.addWidget(QLabel("×"))

            self.domain_y_spin = QSpinBox()
            self.domain_y_spin.setRange(10, 1000)
            self.domain_y_spin.setValue(100)
            self.domain_y_spin.setMaximumWidth(60)
            self.domain_y_spin.valueChanged.connect(self._on_domain_changed)
            domain_layout.addWidget(self.domain_y_spin)

            domain_layout.addWidget(QLabel("×"))

            self.domain_z_spin = QSpinBox()
            self.domain_z_spin.setRange(10, 1000)
            self.domain_z_spin.setValue(50)
            self.domain_z_spin.setMaximumWidth(60)
            self.domain_z_spin.valueChanged.connect(self._on_domain_changed)
            domain_layout.addWidget(self.domain_z_spin)

            controls_layout.addWidget(domain_group)

        controls_layout.addStretch()

        # Display options
        self.show_centers_cb = QCheckBox("Centers")
        self.show_centers_cb.setChecked(True)
        self.show_centers_cb.toggled.connect(self._on_display_changed)
        controls_layout.addWidget(self.show_centers_cb)

        self.show_ids_cb = QCheckBox("IDs")
        self.show_ids_cb.setChecked(False)
        self.show_ids_cb.toggled.connect(self._on_display_changed)
        controls_layout.addWidget(self.show_ids_cb)

        layout.addWidget(controls)

        # Grain controls (only if editable)
        if self.editable:
            grain_controls = QWidget()
            grain_layout = QHBoxLayout(grain_controls)
            grain_layout.setContentsMargins(5, 0, 5, 5)

            grain_layout.addWidget(QLabel("Grains:"))
            self.grain_count_spin = QSpinBox()
            self.grain_count_spin.setRange(2, 100)
            self.grain_count_spin.setValue(12)
            self.grain_count_spin.setMaximumWidth(60)
            grain_layout.addWidget(self.grain_count_spin)

            grain_layout.addWidget(QLabel("Dist:"))
            self.dist_combo = QComboBox()
            self.dist_combo.addItems(['poisson', 'random', 'regular'])
            grain_layout.addWidget(self.dist_combo)

            grain_layout.addWidget(QLabel("Seed:"))
            self.seed_spin = QSpinBox()
            self.seed_spin.setRange(0, 9999)
            self.seed_spin.setValue(42)
            self.seed_spin.setMaximumWidth(60)
            grain_layout.addWidget(self.seed_spin)

            regen_btn = QPushButton("Generate")
            regen_btn.clicked.connect(self._on_regenerate)
            regen_btn.setStyleSheet("""
                QPushButton {
                    background: #667eea;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 3px;
                }
                QPushButton:hover { background: #764ba2; }
            """)
            grain_layout.addWidget(regen_btn)

            grain_layout.addStretch()
            layout.addWidget(grain_controls)

    def _on_view_changed(self, index):
        views = ['XY', 'XZ', 'YZ']
        self.viz.view_plane = views[index]
        self.viz._rebuild_voronoi()
        self.viz.update()

    def _on_slice_changed(self, value):
        self.viz.depth_slice = value / 100.0
        self.slice_label.setText(f"{self.viz.depth_slice:.2f}")
        self.viz._rebuild_voronoi()
        self.viz.update()

    def _on_domain_changed(self):
        if hasattr(self, 'domain_x_spin'):
            self.viz.domain_x = self.domain_x_spin.value()
            self.viz.domain_y = self.domain_y_spin.value()
            self.viz.domain_z = self.domain_z_spin.value()
            self.viz.update()

    def _on_display_changed(self):
        self.viz.show_grain_centers = self.show_centers_cb.isChecked()
        self.viz.show_grain_ids = self.show_ids_cb.isChecked()
        self.viz.update()

    def _on_regenerate(self):
        self.viz.generate_random_grains(
            self.grain_count_spin.value(),
            self.seed_spin.value(),
            self.dist_combo.currentText()
        )

    def set_from_alloy_data(self, alloy: Dict):
        """Set visualization from alloy JSON data"""
        microstructure = alloy.get('Microstructure', {})
        grain_structure = microstructure.get('GrainStructure', {})

        # Get domain size
        domain = grain_structure.get('domain_size', {})
        self.viz.domain_x = domain.get('x_um', 100)
        self.viz.domain_y = domain.get('y_um', 100)
        self.viz.domain_z = domain.get('z_um', 50)

        if hasattr(self, 'domain_x_spin'):
            self.domain_x_spin.setValue(int(self.viz.domain_x))
            self.domain_y_spin.setValue(int(self.viz.domain_y))
            self.domain_z_spin.setValue(int(self.viz.domain_z))

        # Get grain data
        grains = grain_structure.get('grains', [])
        if grains:
            self.viz.set_grains_from_dict(grains)
        else:
            # Generate from parameters
            num_grains = grain_structure.get('NumGrains', 12)
            seed = grain_structure.get('VoronoiSeed', 42)
            dist = grain_structure.get('Distribution', 'poisson')
            self.viz.generate_random_grains(num_grains, seed, dist)

            if hasattr(self, 'grain_count_spin'):
                self.grain_count_spin.setValue(num_grains)
                self.seed_spin.setValue(seed)
                idx = self.dist_combo.findText(dist)
                if idx >= 0:
                    self.dist_combo.setCurrentIndex(idx)

    def get_grain_data(self) -> Dict:
        """Get grain data for JSON export"""
        return self.viz.get_grain_data_for_json()
