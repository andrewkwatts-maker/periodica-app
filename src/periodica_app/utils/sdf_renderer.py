#====== Playtow/PeriodicTable2/utils/sdf_renderer.py ======#
#!copyright (c) 2025 Andrew Keith Watts. All rights reserved.
#!
#!This is the intellectual property of Andrew Keith Watts. Unauthorized
#!reproduction, distribution, or modification of this code, in whole or in part,
#!without the express written permission of Andrew Keith Watts is strictly prohibited.
#!
#!For inquiries, please contact AndrewKWatts@Gmail.com

"""
SDF (Signed Distance Field) renderer for smooth particle visualization.
Supports both numpy (high-performance) and pure Python (zero dependencies) backends.

Uses SDF-based techniques for:
- Smooth particle falloff and anti-aliasing
- Nucleus rendering with protons and neutrons
- Electron orbital probability clouds
"""
import math
from PySide6.QtGui import QImage, QColor, QPainter, QBrush, QRadialGradient
from PySide6.QtCore import Qt, QPointF

# Backend selection
USE_NUMPY = True

try:
    if USE_NUMPY:
        import numpy as np
        _NUMPY_AVAILABLE = True
    else:
        _NUMPY_AVAILABLE = False
except ImportError:
    _NUMPY_AVAILABLE = False

if not _NUMPY_AVAILABLE:
    from periodica.utils.pure_array import (
        Vec3, pi, sqrt, cos, sin,
        random_seed, random_uniform,
        generate_nucleon_positions
    )


def set_backend(use_numpy: bool):
    """
    Switch between numpy and pure Python backends.

    Args:
        use_numpy: True to use numpy backend, False for pure Python.

    Note:
        This function reloads the module to apply the backend change.
        The change affects subsequent operations, not cached data.
    """
    global USE_NUMPY, _NUMPY_AVAILABLE
    USE_NUMPY = use_numpy

    if use_numpy:
        try:
            import numpy as np
            _NUMPY_AVAILABLE = True
        except ImportError:
            _NUMPY_AVAILABLE = False
    else:
        _NUMPY_AVAILABLE = False


def get_backend() -> str:
    """
    Return current backend name.

    Returns:
        "numpy" if using numpy backend, "pure_python" otherwise.
    """
    return "numpy" if _NUMPY_AVAILABLE and USE_NUMPY else "pure_python"


class SDFRenderer:
    """Renders particles using SDF for smooth falloff and blending"""

    # Cache for orbital probability computations
    _orbital_cache = {}
    _cache_max_size = 1000

    @staticmethod
    def sdf_sphere(x, y, cx, cy, radius):
        """
        Signed distance to sphere - negative inside, positive outside.

        Args:
            x, y: Query point coordinates
            cx, cy: Sphere center coordinates
            radius: Sphere radius

        Returns:
            Signed distance (negative if inside sphere)
        """
        return math.sqrt((x - cx)**2 + (y - cy)**2) - radius

    @staticmethod
    def sdf_to_alpha(distance, softness=2.0):
        """
        Convert SDF distance to alpha with smooth falloff.
        Uses smoothstep (hermite interpolation) for anti-aliasing.

        Args:
            distance: Signed distance value
            softness: Controls the falloff width

        Returns:
            Alpha value in [0, 1]
        """
        # Smooth hermite interpolation for anti-aliasing
        t = max(0.0, min(1.0, 0.5 - distance / softness))
        return t * t * (3.0 - 2.0 * t)  # smoothstep

    @staticmethod
    def sdf_union(d1, d2):
        """Union of two SDF shapes (minimum distance)"""
        return min(d1, d2)

    @staticmethod
    def sdf_smooth_union(d1, d2, k=0.5):
        """
        Smooth union of two SDF shapes for blending.

        Args:
            d1, d2: Signed distances to two shapes
            k: Blending factor (higher = sharper transition)
        """
        h = max(k - abs(d1 - d2), 0.0) / k
        return min(d1, d2) - h * h * k * 0.25

    @classmethod
    def draw_sdf_particle(cls, painter, cx, cy, radius, color, softness=3.0, intensity=1.0):
        """
        Draw a particle with SDF-based smooth falloff.
        Uses radial gradient to approximate SDF rendering for performance.

        Args:
            painter: QPainter instance
            cx, cy: Center coordinates
            radius: Particle radius
            color: Base color (QColor or compatible)
            softness: Falloff softness factor
            intensity: Overall intensity multiplier
        """
        # Use radial gradient to approximate SDF rendering (performance-friendly)
        gradient = QRadialGradient(cx, cy, radius + softness)

        inner_color = QColor(color)
        inner_color.setAlpha(int(255 * intensity))
        gradient.setColorAt(0.0, inner_color)

        mid_color = QColor(color)
        mid_color.setAlpha(int(180 * intensity))
        gradient.setColorAt(0.6, mid_color)

        edge_color = QColor(color)
        edge_color.setAlpha(int(80 * intensity))
        gradient.setColorAt(0.85, edge_color)

        edge_color.setAlpha(0)
        gradient.setColorAt(1.0, edge_color)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(cx, cy), radius + softness, radius + softness)

    @classmethod
    def draw_nucleus(cls, painter, cx, cy, protons, neutrons, base_radius,
                     rotation_x=0, rotation_y=0, show_legend=True):
        """
        Draw nucleus with protons and neutrons using SDF blending.
        Uses liquid drop model for nuclear radius scaling.

        Args:
            painter: QPainter instance
            cx, cy: Center coordinates
            protons: Number of protons
            neutrons: Number of neutrons
            base_radius: Base visual radius for scaling
            rotation_x, rotation_y: 3D rotation angles
            show_legend: Whether to draw particle legend
        """
        A = protons + neutrons

        if A == 0:
            return

        # Nuclear radius scales with A^(1/3) - liquid drop model
        # R = r0 * A^(1/3) where r0 ≈ 1.25 fm
        nuclear_radius = base_radius * (A ** (1/3)) / 6.0

        # Place nucleons in a roughly spherical arrangement
        nucleon_radius = max(2, nuclear_radius / max(1, (A ** (1/3))) * 0.8)

        # Select backend-specific implementation
        if _NUMPY_AVAILABLE and USE_NUMPY:
            nucleon_data = cls._generate_nucleons_numpy(
                protons, neutrons, nuclear_radius, rotation_x, rotation_y
            )
        else:
            nucleon_data = cls._generate_nucleons_pure(
                protons, neutrons, nuclear_radius, rotation_x, rotation_y
            )

        # Draw nucleus boundary (subtle)
        from PySide6.QtGui import QPen
        painter.setPen(QPen(QColor(100, 100, 150, 80), 1))
        painter.setBrush(QBrush(QColor(40, 40, 60, 30)))
        painter.drawEllipse(QPointF(cx, cy), nuclear_radius * 1.2, nuclear_radius * 1.2)

        # Sort by depth (back to front)
        nucleon_data.sort(key=lambda n: n[2])

        # Draw nucleons from back to front
        for dx2, dy2, dz3, is_proton in nucleon_data:
            # Project to 2D with depth-based scaling
            depth_scale = 1.0 / (1.0 + dz3 / (nuclear_radius * 3 + 1))
            px = cx + dx2 * depth_scale
            py = cy + dy2 * depth_scale

            # Depth-based alpha for 3D effect
            depth_alpha = 0.4 + 0.6 * (1 + dz3 / (nuclear_radius + 1)) / 2
            depth_alpha = max(0.3, min(1.0, depth_alpha))

            # Draw nucleon with SDF-style gradient
            color = QColor(255, 100, 100) if is_proton else QColor(150, 170, 220)
            cls.draw_sdf_particle(painter, px, py, nucleon_radius * depth_scale,
                                 color, softness=nucleon_radius * 0.5, intensity=depth_alpha)

        # Draw legend if requested
        if show_legend:
            cls._draw_nucleus_legend(painter, cx, cy, protons, neutrons,
                                    nuclear_radius, nucleon_radius)

    @classmethod
    def _generate_nucleons_numpy(cls, protons, neutrons, nuclear_radius, rotation_x, rotation_y):
        """
        Generate nucleon positions using numpy backend.

        Args:
            protons: Number of protons
            neutrons: Number of neutrons
            nuclear_radius: Radius of the nucleus
            rotation_x, rotation_y: 3D rotation angles

        Returns:
            List of tuples (dx2, dy2, dz3, is_proton) for each nucleon
        """
        import numpy as np

        A = protons + neutrons

        # Random but deterministic positions for nucleons
        np.random.seed(protons * 1000 + neutrons)  # Consistent for same isotope

        # Pre-calculate rotation
        cos_rx, sin_rx = np.cos(rotation_x), np.sin(rotation_x)
        cos_ry, sin_ry = np.cos(rotation_y), np.sin(rotation_y)

        nucleon_data = []

        for i in range(protons + neutrons):
            is_proton = i < protons

            # Spherical placement with some randomness
            if A == 1:
                dx, dy, dz = 0, 0, 0
            else:
                phi = np.random.uniform(0, 2 * np.pi)
                cos_theta = np.random.uniform(-1, 1)
                sin_theta = np.sqrt(1 - cos_theta**2)
                r = nuclear_radius * 0.7 * np.random.uniform(0.3, 1.0)

                dx = r * sin_theta * np.cos(phi)
                dy = r * sin_theta * np.sin(phi)
                dz = r * cos_theta

            # Apply 3D rotation - rotate around X axis
            dy2 = dy * cos_rx - dz * sin_rx
            dz2 = dy * sin_rx + dz * cos_rx

            # Rotate around Y axis
            dx2 = dx * cos_ry + dz2 * sin_ry
            dz3 = -dx * sin_ry + dz2 * cos_ry

            nucleon_data.append((dx2, dy2, dz3, is_proton))

        return nucleon_data

    @classmethod
    def _generate_nucleons_pure(cls, protons, neutrons, nuclear_radius, rotation_x, rotation_y):
        """
        Generate nucleon positions using pure Python backend.

        Args:
            protons: Number of protons
            neutrons: Number of neutrons
            nuclear_radius: Radius of the nucleus
            rotation_x, rotation_y: 3D rotation angles

        Returns:
            List of tuples (dx2, dy2, dz3, is_proton) for each nucleon
        """
        from periodica.utils.pure_array import (
            pi, sqrt, cos, sin,
            random_seed, random_uniform
        )

        A = protons + neutrons

        # Random but deterministic positions for nucleons
        random_seed(protons * 1000 + neutrons)  # Consistent for same isotope

        # Pre-calculate rotation
        cos_rx, sin_rx = cos(rotation_x), sin(rotation_x)
        cos_ry, sin_ry = cos(rotation_y), sin(rotation_y)

        nucleon_data = []

        for i in range(protons + neutrons):
            is_proton = i < protons

            # Spherical placement with some randomness
            if A == 1:
                dx, dy, dz = 0, 0, 0
            else:
                phi = random_uniform(0, 2 * pi)
                cos_theta = random_uniform(-1, 1)
                sin_theta = sqrt(1 - cos_theta**2)
                r = nuclear_radius * 0.7 * random_uniform(0.3, 1.0)

                dx = r * sin_theta * cos(phi)
                dy = r * sin_theta * sin(phi)
                dz = r * cos_theta

            # Apply 3D rotation - rotate around X axis
            dy2 = dy * cos_rx - dz * sin_rx
            dz2 = dy * sin_rx + dz * cos_rx

            # Rotate around Y axis
            dx2 = dx * cos_ry + dz2 * sin_ry
            dz3 = -dx * sin_ry + dz2 * cos_ry

            nucleon_data.append((dx2, dy2, dz3, is_proton))

        return nucleon_data

    @classmethod
    def _draw_nucleus_legend(cls, painter, cx, cy, protons, neutrons,
                            nuclear_radius, nucleon_radius):
        """Draw legend for nucleus particles"""
        from PySide6.QtGui import QFont, QPen

        A = protons + neutrons
        # Calculate real nuclear radius in femtometers
        r0_fm = 1.25
        nucleus_radius_fm = r0_fm * (A ** (1/3))

        legend_x = cx - nuclear_radius * 2.0
        legend_y = cy + nuclear_radius * 1.2
        legend_size = max(nucleon_radius * 0.8, 4)

        painter.setFont(QFont('Arial', 9))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))

        # Nucleus info
        painter.drawText(int(legend_x), int(legend_y - 5),
                        f"Nucleus: {nucleus_radius_fm:.2f} fm")

        # Proton legend
        painter.setBrush(QBrush(QColor(255, 80, 80, 180)))
        painter.drawEllipse(QPointF(legend_x, legend_y + 15), legend_size, legend_size)
        painter.drawText(int(legend_x + legend_size + 8), int(legend_y + 19),
                        f"{protons} protons")

        # Neutron legend
        painter.setBrush(QBrush(QColor(150, 170, 220, 180)))
        painter.drawEllipse(QPointF(legend_x, legend_y + 35), legend_size, legend_size)
        painter.drawText(int(legend_x + legend_size + 8), int(legend_y + 39),
                        f"{neutrons} neutrons")

        # Total nucleons
        painter.drawText(int(legend_x), int(legend_y + 58), f"A = {A}")

    @classmethod
    def draw_orbital_cloud(cls, painter, cx, cy, n, l, m, shell_radius,
                          rotation_x=0, rotation_y=0, opacity=0.5, Z=1,
                          animation_phase=0):
        """
        Draw electron orbital probability cloud using SDF-based rendering.

        Args:
            painter: QPainter instance
            cx, cy: Center coordinates
            n: Principal quantum number
            l: Angular momentum quantum number (0=s, 1=p, 2=d, 3=f)
            m: Magnetic quantum number (-l to +l)
            shell_radius: Radius of the electron shell in pixels
            rotation_x, rotation_y: 3D rotation angles
            opacity: Overall cloud opacity
            Z: Atomic number for effective nuclear charge
            animation_phase: Animation phase for pulsing effect
        """
        from periodica.utils.orbital_clouds import get_orbital_probability

        # Pre-calculate rotation
        cos_rx, sin_rx = math.cos(rotation_x), math.sin(rotation_x)
        cos_ry, sin_ry = math.cos(rotation_y), math.sin(rotation_y)

        # Animation offset for fuzzy effect
        animation_offset = math.sin(animation_phase) * 0.05

        # Draw based on orbital type
        if l == 0:
            # s-orbital: spherically symmetric
            cls._draw_s_orbital(painter, cx, cy, n, shell_radius,
                               cos_rx, cos_ry, opacity, Z, animation_offset)
        elif l == 1:
            # p-orbital: dumbbell shape
            cls._draw_p_orbital(painter, cx, cy, n, m, shell_radius,
                               rotation_x, rotation_y, opacity, Z, animation_offset)
        else:
            # d, f orbitals: complex angular shapes
            cls._draw_angular_orbital(painter, cx, cy, n, l, m, shell_radius,
                                     cos_rx, sin_rx, cos_ry, sin_ry, opacity, Z)

    @classmethod
    def _draw_s_orbital(cls, painter, cx, cy, n, shell_radius,
                       cos_rx, cos_ry, opacity, Z, animation_offset):
        """Draw s-orbital (spherically symmetric) with SDF-like gradient"""
        from periodica.utils.orbital_clouds import get_orbital_probability

        # Sample resolution - fewer samples for performance
        resolution = 35
        max_extent = shell_radius * 2.0

        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(resolution - 1, -1, -1):  # Draw from outer to inner
            t = (i + 1) / resolution
            r = t * max_extent

            # Sample probability at this radius
            r_bohr = r / (shell_radius / n) if shell_radius > 0 else r
            prob = get_orbital_probability(n, 0, 0, r_bohr, 0, 0, Z)
            prob = min(1.0, prob * 8.0)  # Amplify for visibility

            # Apply animation
            prob_animated = prob * (1.0 + animation_offset * math.sin(t * math.pi * 2))
            prob_animated = max(0.0, min(1.0, prob_animated))

            if prob_animated < 0.01:
                continue

            # Apply rotation for 3D effect (elliptical projection)
            scale_x = max(0.4, abs(cos_ry))
            scale_y = max(0.4, abs(cos_rx))

            # Draw with SDF-like gradient
            gradient = QRadialGradient(cx, cy, max(r * scale_x, r * scale_y))

            cloud_color = QColor(100, 180, 255)
            cloud_color.setAlpha(int(70 * prob_animated * opacity))
            gradient.setColorAt(0.0, cloud_color)

            cloud_color.setAlpha(int(35 * prob_animated * opacity))
            gradient.setColorAt(0.7, cloud_color)

            cloud_color.setAlpha(0)
            gradient.setColorAt(1.0, cloud_color)

            painter.setBrush(QBrush(gradient))
            painter.drawEllipse(QPointF(cx, cy), r * scale_x, r * scale_y)

    @classmethod
    def _draw_p_orbital(cls, painter, cx, cy, n, m, shell_radius,
                       rotation_x, rotation_y, opacity, Z, animation_offset):
        """Draw p-orbital (dumbbell shape) with SDF-based lobes"""
        from periodica.utils.orbital_clouds import get_orbital_probability

        # p orbitals have two lobes along an axis
        # m = -1: px, m = 0: pz, m = 1: py
        max_extent = shell_radius * 2.2

        # Rotation matrices
        cos_rx, sin_rx = math.cos(rotation_x), math.sin(rotation_x)
        cos_ry, sin_ry = math.cos(rotation_y), math.sin(rotation_y)

        painter.setPen(Qt.PenStyle.NoPen)

        # Determine lobe axis based on m
        if m == 0:  # pz - along z axis
            lobe_axis = (0, 1, 0)  # Will appear vertical
        elif m == -1:  # px
            lobe_axis = (1, 0, 0)  # Along x
        else:  # m == 1, py
            lobe_axis = (0, 0, 1)  # Along y (into screen)

        # Draw two lobes with opposite phases
        for lobe_sign in [1, -1]:
            # Lobe center offset
            lobe_offset = max_extent * 0.4

            # 3D position of lobe center
            lobe_x = lobe_axis[0] * lobe_offset * lobe_sign
            lobe_y = lobe_axis[1] * lobe_offset * lobe_sign
            lobe_z = lobe_axis[2] * lobe_offset * lobe_sign

            # Apply rotation
            # Rotate around X
            ly2 = lobe_y * cos_rx - lobe_z * sin_rx
            lz2 = lobe_y * sin_rx + lobe_z * cos_rx

            # Rotate around Y
            lx2 = lobe_x * cos_ry + lz2 * sin_ry
            lz3 = -lobe_x * sin_ry + lz2 * cos_ry

            # Project to 2D
            lobe_cx = cx + lx2
            lobe_cy = cy + ly2

            # Depth-based scaling
            depth_factor = 1.0 / (1.0 + lz3 / (max_extent * 2))
            depth_factor = max(0.5, min(1.5, depth_factor))

            # Lobe size based on depth
            lobe_radius = max_extent * 0.5 * depth_factor

            # Alpha based on depth (closer = brighter)
            depth_alpha = 0.4 + 0.6 * (1 + lz3 / max_extent) / 2
            depth_alpha = max(0.3, min(1.0, depth_alpha))

            # Draw lobe with gradient
            gradient = QRadialGradient(lobe_cx, lobe_cy, lobe_radius)

            # Different color for positive/negative phase
            if lobe_sign > 0:
                cloud_color = QColor(100, 180, 255)  # Blue
            else:
                cloud_color = QColor(255, 150, 100)  # Orange for opposite phase

            cloud_color.setAlpha(int(90 * opacity * depth_alpha))
            gradient.setColorAt(0.0, cloud_color)

            cloud_color.setAlpha(int(50 * opacity * depth_alpha))
            gradient.setColorAt(0.5, cloud_color)

            cloud_color.setAlpha(int(20 * opacity * depth_alpha))
            gradient.setColorAt(0.8, cloud_color)

            cloud_color.setAlpha(0)
            gradient.setColorAt(1.0, cloud_color)

            painter.setBrush(QBrush(gradient))
            painter.drawEllipse(QPointF(lobe_cx, lobe_cy), lobe_radius, lobe_radius * 0.7)

    @classmethod
    def _draw_angular_orbital(cls, painter, cx, cy, n, l, m, shell_radius,
                             cos_rx, sin_rx, cos_ry, sin_ry, opacity, Z):
        """Draw orbitals with angular dependence (d, f) using sampled SDF blobs"""
        from periodica.utils.orbital_clouds import get_orbital_probability

        # Sample grid for angular orbitals
        grid_size = 25  # Balance between quality and performance
        max_extent = shell_radius * 2.0

        painter.setPen(Qt.PenStyle.NoPen)

        # Pre-compute blob size
        blob_size = max_extent / grid_size * 1.5

        for i in range(grid_size):
            for j in range(grid_size):
                # Normalized coordinates in [-1, 1]
                nx = (i - grid_size / 2) / (grid_size / 2)
                ny = (j - grid_size / 2) / (grid_size / 2)

                # Skip corners for efficiency
                r_norm = math.sqrt(nx * nx + ny * ny)
                if r_norm > 1.0 or r_norm < 0.05:
                    continue

                r = r_norm * max_extent

                # Convert to spherical coordinates
                theta = math.acos(ny / r_norm) if r_norm > 0 else 0
                phi = math.atan2(nx, 0.1)  # Simplified for 2D projection

                # Sample probability
                r_bohr = r / (shell_radius / n) if shell_radius > 0 else r
                prob = get_orbital_probability(n, l, m, r_bohr, theta, phi, Z)
                prob = min(1.0, prob * 20)  # Amplify for visibility

                # Early termination for low probability
                if prob < 0.03:
                    continue

                # 3D position
                x_3d = nx * max_extent
                y_3d = ny * max_extent
                z_3d = 0  # Flat slice

                # Apply rotation
                y_rot = y_3d * cos_rx - z_3d * sin_rx
                z_rot = y_3d * sin_rx + z_3d * cos_rx

                x_rot = x_3d * cos_ry + z_rot * sin_ry

                # Position on screen
                px = cx + x_rot
                py = cy + y_rot

                # Draw small SDF blob at this position
                gradient = QRadialGradient(px, py, blob_size)

                cloud_color = QColor(100, 180, 255)
                cloud_color.setAlpha(int(100 * prob * opacity))
                gradient.setColorAt(0.0, cloud_color)

                cloud_color.setAlpha(int(30 * prob * opacity))
                gradient.setColorAt(0.7, cloud_color)

                cloud_color.setAlpha(0)
                gradient.setColorAt(1.0, cloud_color)

                painter.setBrush(QBrush(gradient))
                painter.drawEllipse(QPointF(px, py), blob_size, blob_size)

    @classmethod
    def draw_electron_sdf(cls, painter, x, y, radius, is_selected=False, glow_factor=1.0):
        """
        Draw an electron with SDF-based smooth rendering.

        Args:
            painter: QPainter instance
            x, y: Center coordinates
            radius: Electron visual radius
            is_selected: Whether electron is selected (highlighted)
            glow_factor: Glow intensity multiplier
        """
        if is_selected:
            base_color = QColor(255, 255, 100)  # Bright yellow
            glow_color = QColor(255, 255, 100, 150)
        else:
            base_color = QColor(200, 220, 255)  # Light blue
            glow_color = QColor(200, 220, 255, 100)

        # Draw glow first
        glow_radius = radius * 2.5 * glow_factor
        cls.draw_sdf_particle(painter, x, y, glow_radius, glow_color,
                             softness=glow_radius * 0.5, intensity=0.4)

        # Draw core particle
        cls.draw_sdf_particle(painter, x, y, radius, base_color,
                             softness=radius * 0.3, intensity=1.0)

    @classmethod
    def clear_cache(cls):
        """Clear the orbital probability cache"""
        cls._orbital_cache.clear()
