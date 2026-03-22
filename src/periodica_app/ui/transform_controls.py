"""
3D Transform Controls Widget
Unified component for 3D rotation, zoom, and translation controls.
Used across all visualization tabs (Atoms, Quarks, Subatomic, Molecules, Alloys).
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional, Callable

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QLabel, QSlider, QDoubleSpinBox, QPushButton,
                                QGroupBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


@dataclass
class Transform3D:
    """3D transformation state"""
    # Rotation (degrees)
    pitch: float = 0.0  # X-axis rotation (tilt up/down)
    yaw: float = 0.0    # Y-axis rotation (turn left/right)
    roll: float = 0.0   # Z-axis rotation (spin)

    # Translation (normalized, for slicing through 3D data)
    translate_x: float = 0.0
    translate_y: float = 0.0
    translate_z: float = 0.0

    # Zoom
    zoom: float = 1.0

    def reset(self):
        """Reset to defaults"""
        self.pitch = 0.0
        self.yaw = 0.0
        self.roll = 0.0
        self.translate_x = 0.0
        self.translate_y = 0.0
        self.translate_z = 0.0
        self.zoom = 1.0

    def copy(self) -> 'Transform3D':
        """Create a copy"""
        return Transform3D(
            pitch=self.pitch, yaw=self.yaw, roll=self.roll,
            translate_x=self.translate_x, translate_y=self.translate_y,
            translate_z=self.translate_z, zoom=self.zoom
        )


def rotate_point_3d(x: float, y: float, z: float,
                    pitch: float, yaw: float, roll: float) -> Tuple[float, float, float]:
    """
    Apply 3D rotation and return transformed coordinates.

    Args:
        x, y, z: Original 3D coordinates (relative to center)
        pitch: Rotation around X-axis (tilt up/down) in degrees
        yaw: Rotation around Y-axis (turn left/right) in degrees
        roll: Rotation around Z-axis (spin) in degrees

    Returns:
        Tuple of (x_rotated, y_rotated, z_rotated)
    """
    pitch_rad = math.radians(pitch)
    yaw_rad = math.radians(yaw)
    roll_rad = math.radians(roll)

    # Rotation around X-axis (pitch)
    y1 = y * math.cos(pitch_rad) - z * math.sin(pitch_rad)
    z1 = y * math.sin(pitch_rad) + z * math.cos(pitch_rad)
    x1 = x

    # Rotation around Y-axis (yaw)
    x2 = x1 * math.cos(yaw_rad) + z1 * math.sin(yaw_rad)
    z2 = -x1 * math.sin(yaw_rad) + z1 * math.cos(yaw_rad)
    y2 = y1

    # Rotation around Z-axis (roll)
    x3 = x2 * math.cos(roll_rad) - y2 * math.sin(roll_rad)
    y3 = x2 * math.sin(roll_rad) + y2 * math.cos(roll_rad)
    z3 = z2

    return x3, y3, z3


def apply_transform_3d(x: float, y: float, z: float,
                       transform: Transform3D,
                       center_x: float = 0, center_y: float = 0,
                       center_z: float = 0) -> Tuple[float, float, float]:
    """
    Apply full 3D transform (rotation + translation + zoom).

    Args:
        x, y, z: Original coordinates
        transform: Transform3D object with all transform parameters
        center_x, center_y, center_z: Center point for rotation

    Returns:
        Tuple of (x_transformed, y_transformed, z_depth)
    """
    # Translate to center
    x_rel = x - center_x
    y_rel = y - center_y
    z_rel = z - center_z

    # Apply rotation
    x_rot, y_rot, z_rot = rotate_point_3d(
        x_rel, y_rel, z_rel,
        transform.pitch, transform.yaw, transform.roll
    )

    # Apply zoom
    x_zoomed = x_rot * transform.zoom
    y_zoomed = y_rot * transform.zoom
    z_zoomed = z_rot * transform.zoom

    # Apply translation (for slicing)
    x_final = x_zoomed + transform.translate_x
    y_final = y_zoomed + transform.translate_y
    z_final = z_zoomed + transform.translate_z

    # Translate back from center
    return x_final + center_x, y_final + center_y, z_final


def project_3d_to_2d(x: float, y: float, z: float,
                     perspective: float = 500) -> Tuple[float, float, float]:
    """
    Project 3D point to 2D with perspective.

    Args:
        x, y, z: 3D coordinates
        perspective: Perspective distance (larger = less perspective)

    Returns:
        Tuple of (x_2d, y_2d, depth) for rendering
    """
    if perspective > 0:
        scale = perspective / (perspective + z)
        return x * scale, y * scale, z
    return x, y, z


class TransformControlsWidget(QGroupBox):
    """
    3D Transform Controls Panel
    Provides sliders and inputs for rotation, translation, and zoom.
    """

    transform_changed = Signal(Transform3D)

    def __init__(self, title: str = "3D Transform Controls",
                 show_rotation: bool = True,
                 show_translation: bool = True,
                 show_zoom: bool = True,
                 accent_color: str = "#4fc3f7",
                 parent=None):
        super().__init__(title, parent)

        self.accent_color = accent_color
        self.show_rotation = show_rotation
        self.show_translation = show_translation
        self.show_zoom = show_zoom

        self.transform = Transform3D()
        self._updating = False  # Prevent signal loops

        self.setup_ui()
        self.setStyleSheet(self._get_group_style())

    def _get_group_style(self) -> str:
        return f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {self.accent_color};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                color: white;
                background: rgba(30, 30, 50, 150);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {self.accent_color};
            }}
            QLabel {{
                color: white;
                font-size: 10px;
            }}
            QSlider::groove:horizontal {{
                background: rgba(60, 60, 80, 200);
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {self.accent_color};
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
            QDoubleSpinBox {{
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px;
                max-width: 60px;
            }}
            QPushButton {{
                background: rgba(60, 60, 80, 200);
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background: {self.accent_color};
            }}
        """

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)

        # Rotation controls
        if self.show_rotation:
            rotation_widget = QWidget()
            rotation_layout = QGridLayout(rotation_widget)
            rotation_layout.setSpacing(4)
            rotation_layout.setContentsMargins(0, 0, 0, 0)

            # Pitch (X rotation)
            rotation_layout.addWidget(QLabel("Pitch (X):"), 0, 0)
            self.pitch_slider = self._create_angle_slider()
            self.pitch_slider.valueChanged.connect(lambda v: self._on_rotation_changed('pitch', v))
            rotation_layout.addWidget(self.pitch_slider, 0, 1)
            self.pitch_spin = self._create_angle_spin()
            self.pitch_spin.valueChanged.connect(lambda v: self._on_rotation_spin_changed('pitch', v))
            rotation_layout.addWidget(self.pitch_spin, 0, 2)

            # Yaw (Y rotation)
            rotation_layout.addWidget(QLabel("Yaw (Y):"), 1, 0)
            self.yaw_slider = self._create_angle_slider()
            self.yaw_slider.valueChanged.connect(lambda v: self._on_rotation_changed('yaw', v))
            rotation_layout.addWidget(self.yaw_slider, 1, 1)
            self.yaw_spin = self._create_angle_spin()
            self.yaw_spin.valueChanged.connect(lambda v: self._on_rotation_spin_changed('yaw', v))
            rotation_layout.addWidget(self.yaw_spin, 1, 2)

            # Roll (Z rotation)
            rotation_layout.addWidget(QLabel("Roll (Z):"), 2, 0)
            self.roll_slider = self._create_angle_slider()
            self.roll_slider.valueChanged.connect(lambda v: self._on_rotation_changed('roll', v))
            rotation_layout.addWidget(self.roll_slider, 2, 1)
            self.roll_spin = self._create_angle_spin()
            self.roll_spin.valueChanged.connect(lambda v: self._on_rotation_spin_changed('roll', v))
            rotation_layout.addWidget(self.roll_spin, 2, 2)

            layout.addWidget(rotation_widget)

        # Zoom control
        if self.show_zoom:
            zoom_widget = QWidget()
            zoom_layout = QHBoxLayout(zoom_widget)
            zoom_layout.setSpacing(4)
            zoom_layout.setContentsMargins(0, 0, 0, 0)

            zoom_layout.addWidget(QLabel("Zoom:"))
            self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
            self.zoom_slider.setRange(10, 300)  # 0.1x to 3.0x
            self.zoom_slider.setValue(100)
            self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
            zoom_layout.addWidget(self.zoom_slider)

            self.zoom_spin = QDoubleSpinBox()
            self.zoom_spin.setRange(0.1, 3.0)
            self.zoom_spin.setSingleStep(0.1)
            self.zoom_spin.setValue(1.0)
            self.zoom_spin.setDecimals(2)
            self.zoom_spin.valueChanged.connect(self._on_zoom_spin_changed)
            zoom_layout.addWidget(self.zoom_spin)

            layout.addWidget(zoom_widget)

        # Translation controls
        if self.show_translation:
            trans_widget = QWidget()
            trans_layout = QGridLayout(trans_widget)
            trans_layout.setSpacing(4)
            trans_layout.setContentsMargins(0, 0, 0, 0)

            # X translation
            trans_layout.addWidget(QLabel("Slice X:"), 0, 0)
            self.trans_x_slider = self._create_translation_slider()
            self.trans_x_slider.valueChanged.connect(lambda v: self._on_translation_changed('x', v))
            trans_layout.addWidget(self.trans_x_slider, 0, 1)
            self.trans_x_spin = self._create_translation_spin()
            self.trans_x_spin.valueChanged.connect(lambda v: self._on_translation_spin_changed('x', v))
            trans_layout.addWidget(self.trans_x_spin, 0, 2)

            # Y translation
            trans_layout.addWidget(QLabel("Slice Y:"), 1, 0)
            self.trans_y_slider = self._create_translation_slider()
            self.trans_y_slider.valueChanged.connect(lambda v: self._on_translation_changed('y', v))
            trans_layout.addWidget(self.trans_y_slider, 1, 1)
            self.trans_y_spin = self._create_translation_spin()
            self.trans_y_spin.valueChanged.connect(lambda v: self._on_translation_spin_changed('y', v))
            trans_layout.addWidget(self.trans_y_spin, 1, 2)

            # Z translation
            trans_layout.addWidget(QLabel("Slice Z:"), 2, 0)
            self.trans_z_slider = self._create_translation_slider()
            self.trans_z_slider.valueChanged.connect(lambda v: self._on_translation_changed('z', v))
            trans_layout.addWidget(self.trans_z_slider, 2, 1)
            self.trans_z_spin = self._create_translation_spin()
            self.trans_z_spin.valueChanged.connect(lambda v: self._on_translation_spin_changed('z', v))
            trans_layout.addWidget(self.trans_z_spin, 2, 2)

            layout.addWidget(trans_widget)

        # Reset button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.reset_btn = QPushButton("Reset Transform")
        self.reset_btn.clicked.connect(self.reset_transform)
        btn_layout.addWidget(self.reset_btn)

        layout.addLayout(btn_layout)

    def _create_angle_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(-180, 180)
        slider.setValue(0)
        return slider

    def _create_angle_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-180, 180)
        spin.setSingleStep(5)
        spin.setValue(0)
        spin.setDecimals(1)
        spin.setSuffix("°")
        return spin

    def _create_translation_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(-100, 100)  # -1.0 to 1.0
        slider.setValue(0)
        return slider

    def _create_translation_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-1.0, 1.0)
        spin.setSingleStep(0.05)
        spin.setValue(0)
        spin.setDecimals(2)
        return spin

    def _on_rotation_changed(self, axis: str, value: int):
        if self._updating:
            return
        self._updating = True

        setattr(self.transform, axis, float(value))
        getattr(self, f'{axis}_spin').setValue(float(value))

        self._updating = False
        self.transform_changed.emit(self.transform)

    def _on_rotation_spin_changed(self, axis: str, value: float):
        if self._updating:
            return
        self._updating = True

        setattr(self.transform, axis, value)
        getattr(self, f'{axis}_slider').setValue(int(value))

        self._updating = False
        self.transform_changed.emit(self.transform)

    def _on_zoom_slider_changed(self, value: int):
        if self._updating:
            return
        self._updating = True

        self.transform.zoom = value / 100.0
        self.zoom_spin.setValue(self.transform.zoom)

        self._updating = False
        self.transform_changed.emit(self.transform)

    def _on_zoom_spin_changed(self, value: float):
        if self._updating:
            return
        self._updating = True

        self.transform.zoom = value
        self.zoom_slider.setValue(int(value * 100))

        self._updating = False
        self.transform_changed.emit(self.transform)

    def _on_translation_changed(self, axis: str, value: int):
        if self._updating:
            return
        self._updating = True

        trans_value = value / 100.0
        setattr(self.transform, f'translate_{axis}', trans_value)
        getattr(self, f'trans_{axis}_spin').setValue(trans_value)

        self._updating = False
        self.transform_changed.emit(self.transform)

    def _on_translation_spin_changed(self, axis: str, value: float):
        if self._updating:
            return
        self._updating = True

        setattr(self.transform, f'translate_{axis}', value)
        getattr(self, f'trans_{axis}_slider').setValue(int(value * 100))

        self._updating = False
        self.transform_changed.emit(self.transform)

    def reset_transform(self):
        """Reset all transforms to defaults"""
        self._updating = True

        self.transform.reset()

        if self.show_rotation:
            self.pitch_slider.setValue(0)
            self.pitch_spin.setValue(0)
            self.yaw_slider.setValue(0)
            self.yaw_spin.setValue(0)
            self.roll_slider.setValue(0)
            self.roll_spin.setValue(0)

        if self.show_zoom:
            self.zoom_slider.setValue(100)
            self.zoom_spin.setValue(1.0)

        if self.show_translation:
            self.trans_x_slider.setValue(0)
            self.trans_x_spin.setValue(0)
            self.trans_y_slider.setValue(0)
            self.trans_y_spin.setValue(0)
            self.trans_z_slider.setValue(0)
            self.trans_z_spin.setValue(0)

        self._updating = False
        self.transform_changed.emit(self.transform)

    def get_transform(self) -> Transform3D:
        """Get current transform"""
        return self.transform.copy()

    def set_transform(self, transform: Transform3D):
        """Set transform values"""
        self._updating = True

        self.transform = transform.copy()

        if self.show_rotation:
            self.pitch_slider.setValue(int(transform.pitch))
            self.pitch_spin.setValue(transform.pitch)
            self.yaw_slider.setValue(int(transform.yaw))
            self.yaw_spin.setValue(transform.yaw)
            self.roll_slider.setValue(int(transform.roll))
            self.roll_spin.setValue(transform.roll)

        if self.show_zoom:
            self.zoom_slider.setValue(int(transform.zoom * 100))
            self.zoom_spin.setValue(transform.zoom)

        if self.show_translation:
            self.trans_x_slider.setValue(int(transform.translate_x * 100))
            self.trans_x_spin.setValue(transform.translate_x)
            self.trans_y_slider.setValue(int(transform.translate_y * 100))
            self.trans_y_spin.setValue(transform.translate_y)
            self.trans_z_slider.setValue(int(transform.translate_z * 100))
            self.trans_z_spin.setValue(transform.translate_z)

        self._updating = False


class CompactTransformControls(QWidget):
    """
    Compact version of transform controls for embedding in smaller spaces.
    Shows only rotation sliders in a horizontal layout.
    """

    transform_changed = Signal(Transform3D)

    def __init__(self, accent_color: str = "#4fc3f7", parent=None):
        super().__init__(parent)
        self.accent_color = accent_color
        self.transform = Transform3D()
        self._updating = False
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        # Pitch
        layout.addWidget(QLabel("P:"))
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-180, 180)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setMaximumWidth(80)
        self.pitch_slider.valueChanged.connect(lambda v: self._on_changed('pitch', v))
        layout.addWidget(self.pitch_slider)

        # Yaw
        layout.addWidget(QLabel("Y:"))
        self.yaw_slider = QSlider(Qt.Orientation.Horizontal)
        self.yaw_slider.setRange(-180, 180)
        self.yaw_slider.setValue(0)
        self.yaw_slider.setMaximumWidth(80)
        self.yaw_slider.valueChanged.connect(lambda v: self._on_changed('yaw', v))
        layout.addWidget(self.yaw_slider)

        # Roll
        layout.addWidget(QLabel("R:"))
        self.roll_slider = QSlider(Qt.Orientation.Horizontal)
        self.roll_slider.setRange(-180, 180)
        self.roll_slider.setValue(0)
        self.roll_slider.setMaximumWidth(80)
        self.roll_slider.valueChanged.connect(lambda v: self._on_changed('roll', v))
        layout.addWidget(self.roll_slider)

        # Zoom
        layout.addWidget(QLabel("Z:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(60)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        layout.addWidget(self.zoom_slider)

        # Reset
        reset_btn = QPushButton("↺")
        reset_btn.setMaximumWidth(30)
        reset_btn.setToolTip("Reset Transform")
        reset_btn.clicked.connect(self.reset_transform)
        layout.addWidget(reset_btn)

        self.setStyleSheet(f"""
            QLabel {{ color: white; font-size: 10px; }}
            QSlider::groove:horizontal {{
                background: rgba(60, 60, 80, 200);
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {self.accent_color};
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }}
            QPushButton {{
                background: rgba(60, 60, 80, 200);
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {self.accent_color};
            }}
        """)

    def _on_changed(self, axis: str, value: int):
        if self._updating:
            return
        setattr(self.transform, axis, float(value))
        self.transform_changed.emit(self.transform)

    def _on_zoom_changed(self, value: int):
        if self._updating:
            return
        self.transform.zoom = value / 100.0
        self.transform_changed.emit(self.transform)

    def reset_transform(self):
        self._updating = True
        self.transform.reset()
        self.pitch_slider.setValue(0)
        self.yaw_slider.setValue(0)
        self.roll_slider.setValue(0)
        self.zoom_slider.setValue(100)
        self._updating = False
        self.transform_changed.emit(self.transform)

    def get_transform(self) -> Transform3D:
        return self.transform.copy()
