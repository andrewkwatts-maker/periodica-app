#!/usr/bin/env python3
"""
UI Components for the Quantum Orbit visualization
Reusable widget classes for legends and gradient bars
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QCheckBox, QPushButton, QLabel
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient, QPolygonF, QPainterPath

from periodica_app.utils.calculations import (get_block_color, get_ie_color, get_electroneg_color,
                                 get_melting_color, get_radius_color, get_density_color,
                                 get_electron_affinity_color, get_boiling_color,
                                 wavelength_to_rgb)
from periodica.core.pt_enums import PTPropertyName, PTWavelengthMode, PTPropertyType


class ColorGradientBar(QWidget):
    """Widget to display a color gradient bar with labels"""
    def __init__(self, mode="ionization"):
        super().__init__()
        self.mode = mode
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        bar_y = 25
        bar_height = 25
        segments = 100
        seg_width = (width - 20) / segments

        if self.mode == "ionization":
            painter.drawText(5, 15, "Ionization Energy (eV)")
            for i in range(segments):
                ie = 3.5 + (25.0 - 3.5) * (i / segments)
                painter.fillRect(int(10 + i * seg_width), bar_y, int(seg_width + 1), bar_height, get_ie_color(ie))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawRect(10, bar_y, width - 20, bar_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(5, bar_y + bar_height + 15, "3.9")
            painter.drawText(int(width/2 - 10), bar_y + bar_height + 15, "14")
            painter.drawText(width - 25, bar_y + bar_height + 15, "24.6")

        elif self.mode == "electronegativity":
            painter.drawText(5, 15, "Electronegativity (Pauling)")
            for i in range(segments):
                en = 0.7 + (4.0 - 0.7) * (i / segments)
                painter.fillRect(int(10 + i * seg_width), bar_y, int(seg_width + 1), bar_height, get_electroneg_color(en))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawRect(10, bar_y, width - 20, bar_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(5, bar_y + bar_height + 15, "0.7")
            painter.drawText(int(width/2 - 10), bar_y + bar_height + 15, "2.3")
            painter.drawText(width - 25, bar_y + bar_height + 15, "4.0")

        elif self.mode == "melting":
            painter.drawText(5, 15, "Melting Point (K)")
            for i in range(segments):
                mp = 0 + (4000 - 0) * (i / segments)
                painter.fillRect(int(10 + i * seg_width), bar_y, int(seg_width + 1), bar_height, get_melting_color(mp))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawRect(10, bar_y, width - 20, bar_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(5, bar_y + bar_height + 15, "0")
            painter.drawText(int(width/2 - 15), bar_y + bar_height + 15, "2000")
            painter.drawText(width - 30, bar_y + bar_height + 15, "4000")

        elif self.mode == "radius":
            painter.drawText(5, 15, "Atomic Radius (pm)")
            for i in range(segments):
                r = 30 + (350 - 30) * (i / segments)
                painter.fillRect(int(10 + i * seg_width), bar_y, int(seg_width + 1), bar_height, get_radius_color(r))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawRect(10, bar_y, width - 20, bar_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(5, bar_y + bar_height + 15, "30")
            painter.drawText(int(width/2 - 15), bar_y + bar_height + 15, "190")
            painter.drawText(width - 25, bar_y + bar_height + 15, "350")

        elif self.mode == "block":
            painter.drawText(5, 15, "Orbital Blocks")
            block_width = (width - 20) / 4
            blocks = [('s', get_block_color('s')), ('p', get_block_color('p')),
                     ('d', get_block_color('d')), ('f', get_block_color('f'))]
            for i, (block, color) in enumerate(blocks):
                x = 10 + i * block_width
                painter.fillRect(int(x), bar_y, int(block_width), bar_height, color)
                painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
                painter.drawRect(int(x), bar_y, int(block_width), bar_height)
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                painter.drawText(int(x + block_width/2 - 5), bar_y + bar_height + 15, f"{block}")

        elif self.mode == "wavelength":
            painter.drawText(5, 15, "Emission Wavelength (nm)")
            for i in range(segments):
                wl = 50 + (200 - 50) * (i / segments)
                painter.fillRect(int(10 + i * seg_width), bar_y, int(seg_width + 1), bar_height, wavelength_to_rgb(wl))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawRect(10, bar_y, width - 20, bar_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(5, bar_y + bar_height + 15, "50")
            painter.drawText(int(width/2 - 10), bar_y + bar_height + 15, "125")
            painter.drawText(width - 25, bar_y + bar_height + 15, "200")

        elif self.mode == "boiling":
            painter.drawText(5, 15, "Boiling Point (K)")
            for i in range(segments):
                bp = 0 + (4000 - 0) * (i / segments)
                painter.fillRect(int(10 + i * seg_width), bar_y, int(seg_width + 1), bar_height, get_boiling_color(bp))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawRect(10, bar_y, width - 20, bar_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(5, bar_y + bar_height + 15, "0")
            painter.drawText(int(width/2 - 15), bar_y + bar_height + 15, "2000")
            painter.drawText(width - 25, bar_y + bar_height + 15, "4000")

        elif self.mode == "density":
            painter.drawText(5, 15, "Density (g/cm³, log scale)")
            for i in range(segments):
                log_d = -4 + (5.3) * (i / segments)
                density = 10 ** log_d
                painter.fillRect(int(10 + i * seg_width), bar_y, int(seg_width + 1), bar_height, get_density_color(density))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawRect(10, bar_y, width - 20, bar_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(5, bar_y + bar_height + 15, "0.0001")
            painter.drawText(int(width/2 - 20), bar_y + bar_height + 15, "1")
            painter.drawText(width - 25, bar_y + bar_height + 15, "20")

        elif self.mode == "electron_affinity":
            painter.drawText(5, 15, "Electron Affinity (kJ/mol)")
            for i in range(segments):
                ea = -10 + (360) * (i / segments)
                painter.fillRect(int(10 + i * seg_width), bar_y, int(seg_width + 1), bar_height, get_electron_affinity_color(ea))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawRect(10, bar_y, width - 20, bar_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(5, bar_y + bar_height + 15, "-10")
            painter.drawText(int(width/2 - 15), bar_y + bar_height + 15, "175")
            painter.drawText(width - 25, bar_y + bar_height + 15, "350")

        elif self.mode == "valence":
            painter.drawText(5, 15, "Valence Electrons")
            for i in range(8):
                valence = i + 1
                hue = (valence * 25) % 360
                color = QColor.fromHsv(hue, 200, 255)
                val_width = (width - 20) / 8
                x = 10 + i * val_width
                painter.fillRect(int(x), bar_y, int(val_width), bar_height, color)
                painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
                painter.drawRect(int(x), bar_y, int(val_width), bar_height)
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                painter.drawText(int(x + val_width/2 - 5), bar_y + bar_height + 15, f"{valence}")


class DistanceMappingVisualizer(QWidget):
    """Visual trapezoid representation for distance/size property mapping"""
    def __init__(self):
        super().__init__()
        self.min_value = 0.0
        self.max_value = 1.0
        self.min_viz = 0.0
        self.max_viz = 1.0
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)

    def set_values(self, min_value, max_value, min_viz, max_viz):
        """Update the mapping values"""
        self.min_value = min_value
        self.max_value = max_value
        self.min_viz = min_viz
        self.max_viz = max_viz
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw trapezoid representing the mapping
        margin = 10
        trap_y = 15
        trap_height = 30

        # Calculate trapezoid dimensions
        # min_viz controls bottom width, max_viz controls top width
        bottom_width = (width - 2 * margin) * self.min_viz
        top_width = (width - 2 * margin) * self.max_viz

        # Center the trapezoid
        bottom_left_x = margin + ((width - 2 * margin) - bottom_width) / 2
        top_left_x = margin + ((width - 2 * margin) - top_width) / 2

        # Draw trapezoid
        from PySide6.QtGui import QPolygonF
        trap_points = QPolygonF([
            QPointF(bottom_left_x, trap_y + trap_height),
            QPointF(bottom_left_x + bottom_width, trap_y + trap_height),
            QPointF(top_left_x + top_width, trap_y),
            QPointF(top_left_x, trap_y)
        ])

        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.setBrush(QBrush(QColor(100, 150, 255, 150)))
        painter.drawPolygon(trap_points)

        # Draw labels
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 7))
        painter.drawText(int(bottom_left_x), trap_y + trap_height + 12, f"Min: {self.min_value:.1f}")
        painter.drawText(int(top_left_x), trap_y - 3, f"Max: {self.max_value:.1f}")


class SpectrumMappingVisualizer(QWidget):
    """Visual rainbow representation for emission spectrum mapping"""
    def __init__(self):
        super().__init__()
        self.min_wavelength = 380.0  # nm
        self.max_wavelength = 780.0  # nm
        self.min_map = 380.0
        self.max_map = 780.0
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)

    def set_values(self, min_wavelength, max_wavelength, min_map, max_map):
        """Update the mapping wavelength values"""
        self.min_wavelength = min_wavelength
        self.max_wavelength = max_wavelength
        self.min_map = min_map
        self.max_map = max_map
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw spectrum across the full data range (min_wavelength to max_wavelength)
        # The visible spectrum rainbow (380-780nm) is remapped to viz range (min_map to max_map)
        # Below min_map: fade to white
        # Between min_map and max_map: rainbow (380-780nm mapped to this range)
        # Above max_map: fade to black
        margin = 10
        bar_y = 15
        bar_height = 25
        bar_width = width - 2 * margin

        segments = 200
        seg_width = bar_width / segments

        for i in range(segments):
            # Map bar position to actual wavelength in the data range
            t = i / segments
            wl = self.min_wavelength + (self.max_wavelength - self.min_wavelength) * t

            # Now determine color based on where wl falls relative to the viz mapping range
            # min_map to max_map shows the rainbow (380-780nm visible spectrum)
            # Below min_map: fade from white to the rainbow start
            # Above max_map: fade from rainbow end to black

            if wl < self.min_map:
                # Below visualization range - fade from white (at 0nm) to start of rainbow (at min_map)
                if wl <= 0:
                    color = QColor(255, 255, 255)  # Pure white at 0nm
                else:
                    # Fade from white to violet as we approach min_map
                    fade = (self.min_map - wl) / self.min_map if self.min_map > 0 else 0
                    fade = max(0, min(1, fade))
                    # At min_map we want pure violet (bright purple), at 0 we want white
                    # Use manual RGB for violet to avoid wavelength_to_rgb dimming
                    violet_r, violet_g, violet_b = 138, 43, 226  # BlueViolet color
                    color = QColor(
                        int(255 * fade + violet_r * (1 - fade)),
                        int(255 * fade + violet_g * (1 - fade)),
                        int(255 * fade + violet_b * (1 - fade))
                    )
            elif wl > self.max_map:
                # Above visualization range - fade from end of rainbow (at max_map) to black (at max wavelength)
                fade = (wl - self.max_map) / (self.max_wavelength - self.max_map) if (self.max_wavelength - self.max_map) > 0 else 1
                fade = max(0, min(1, fade))
                # At max_map we want pure red, at max we want black
                # Use manual RGB for red to avoid wavelength_to_rgb dimming
                red_r, red_g, red_b = 255, 0, 0  # Pure red
                color = QColor(
                    int(red_r * (1 - fade)),
                    int(red_g * (1 - fade)),
                    int(red_b * (1 - fade))
                )
            else:
                # Within visualization range (min_map to max_map INCLUSIVE) - show ONLY rainbow (380-780nm)
                # Map position within min_map to max_map to full visible spectrum (380-780nm)
                rainbow_t = (wl - self.min_map) / (self.max_map - self.min_map) if (self.max_map - self.min_map) > 0 else 0

                # Create smooth rainbow from violet to red using manual interpolation
                # This avoids wavelength_to_rgb's dimming at edges
                if rainbow_t < 0.17:  # Violet to Blue
                    t = rainbow_t / 0.17
                    r, g, b = int(138 + (0-138)*t), int(43 + (0-43)*t), 226
                elif rainbow_t < 0.33:  # Blue to Cyan
                    t = (rainbow_t - 0.17) / 0.16
                    r, g, b = 0, int(0 + 255*t), 255
                elif rainbow_t < 0.5:  # Cyan to Green
                    t = (rainbow_t - 0.33) / 0.17
                    r, g, b = 0, 255, int(255 - 255*t)
                elif rainbow_t < 0.67:  # Green to Yellow
                    t = (rainbow_t - 0.5) / 0.17
                    r, g, b = int(0 + 255*t), 255, 0
                elif rainbow_t < 0.83:  # Yellow to Orange
                    t = (rainbow_t - 0.67) / 0.16
                    r, g, b = 255, int(255 - 128*t), 0
                else:  # Orange to Red
                    t = (rainbow_t - 0.83) / 0.17
                    r, g, b = 255, int(127 - 127*t), 0

                color = QColor(r, g, b)

            painter.fillRect(int(margin + i * seg_width), bar_y, int(seg_width + 1), bar_height, color)

        # Draw border
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(margin, bar_y, bar_width, bar_height)

        # Draw visualization mapping range markers (where rainbow starts/ends)
        if self.min_wavelength != self.max_wavelength:
            # Calculate positions for min_map and max_map within the full data range bar
            wavelength_range = self.max_wavelength - self.min_wavelength

            # Position of min_map (where rainbow starts - violet)
            min_t = (self.min_map - self.min_wavelength) / wavelength_range if wavelength_range > 0 else 0
            min_pos = margin + bar_width * min_t
            min_pos = max(margin, min(margin + bar_width, min_pos))

            # Position of max_map (where rainbow ends - red)
            max_t = (self.max_map - self.min_wavelength) / wavelength_range if wavelength_range > 0 else 1
            max_pos = margin + bar_width * max_t
            max_pos = max(margin, min(margin + bar_width, max_pos))

            # Draw vertical bars for mapping range
            painter.setPen(QPen(QColor(255, 255, 0, 220), 3))
            painter.drawLine(int(min_pos), bar_y, int(min_pos), bar_y + bar_height)
            painter.drawLine(int(max_pos), bar_y, int(max_pos), bar_y + bar_height)

            # Draw labels for visualization mapping range
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(int(min_pos - 15), bar_y + bar_height + 12, f"{self.min_map:.0f}nm")
            painter.drawText(int(max_pos - 15), bar_y + bar_height + 12, f"{self.max_map:.0f}nm")

            # Draw data range labels at the ends
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Arial", 6))
            painter.drawText(margin, bar_y - 5, f"{self.min_wavelength:.0f}nm")
            painter.drawText(margin + bar_width - 30, bar_y - 5, f"{self.max_wavelength:.0f}nm")


class ColorMappingVisualizer(QWidget):
    """Visual color gradient representation for color property mapping"""
    def __init__(self, property_name="ionization"):
        super().__init__()
        self.property_name = property_name
        self.min_value = 0.0
        self.max_value = 1.0
        self.min_map = 0.0
        self.max_map = 1.0
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)

    def set_property(self, property_name):
        """Update the property type being visualized"""
        self.property_name = property_name
        self.update()

    def set_values(self, min_value, max_value, min_map, max_map):
        """Update the mapping values"""
        self.min_value = min_value
        self.max_value = max_value
        self.min_map = min_map
        self.max_map = max_map
        self.update()

    def _get_color_for_value(self, value):
        """Get color for a property value"""
        if self.property_name == "ionization":
            return get_ie_color(value)
        elif self.property_name == "electronegativity":
            return get_electroneg_color(value)
        elif self.property_name == "melting":
            return get_melting_color(value)
        elif self.property_name == "boiling":
            return get_boiling_color(value)
        elif self.property_name == "radius":
            return get_radius_color(value)
        elif self.property_name == "density":
            return get_density_color(value)
        elif self.property_name == "electron_affinity":
            return get_electron_affinity_color(value)
        elif self.property_name == "valence":
            hue = (int(value) * 25) % 360
            return QColor.fromHsv(hue, 200, 255)
        elif self.property_name == "block":
            blocks = ['s', 'p', 'd', 'f']
            idx = int(value) % len(blocks)
            return get_block_color(blocks[idx])
        else:
            return QColor(128, 128, 128)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw gradient bar
        margin = 10
        bar_y = 15
        bar_height = 25
        bar_width = width - 2 * margin

        segments = 100
        seg_width = bar_width / segments

        # Draw full gradient
        for i in range(segments):
            t = i / segments
            value = self.min_value + (self.max_value - self.min_value) * t
            color = self._get_color_for_value(value)
            painter.fillRect(int(margin + i * seg_width), bar_y, int(seg_width + 1), bar_height, color)

        # Draw border
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(margin, bar_y, bar_width, bar_height)

        # Draw min/max mapping bars
        if self.min_value != self.max_value:
            # Calculate positions for min and max bars
            min_t = (self.min_map - self.min_value) / (self.max_value - self.min_value)
            max_t = (self.max_map - self.min_value) / (self.max_value - self.min_value)

            min_pos = margin + bar_width * min_t
            max_pos = margin + bar_width * max_t

            # Clamp to bar bounds
            min_pos = max(margin, min(margin + bar_width, min_pos))
            max_pos = max(margin, min(margin + bar_width, max_pos))

            # Draw vertical bars for mapping range
            painter.setPen(QPen(QColor(255, 255, 0, 220), 3))
            painter.drawLine(int(min_pos), bar_y, int(min_pos), bar_y + bar_height)
            painter.drawLine(int(max_pos), bar_y, int(max_pos), bar_y + bar_height)

            # Draw labels
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(int(min_pos - 10), bar_y + bar_height + 12, f"{self.min_map:.1f}")
            painter.drawText(int(max_pos - 10), bar_y + bar_height + 12, f"{self.max_map:.1f}")


class BorderThicknessLegend(QWidget):
    """Widget showing border thickness scale"""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMaximumHeight(100)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(5, 15, "Border Thickness Scale")

        y_base = 35
        samples = [("Low", 1), ("Medium", 2.5), ("High", 4), ("Max", 6)]

        x_pos = 15
        for label, thickness in samples:
            painter.setPen(QPen(QColor(255, 255, 255, 150), thickness))
            painter.setBrush(QBrush(QColor(60, 60, 80)))
            painter.drawRect(x_pos, y_base, 35, 35)
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x_pos, y_base + 50, label)
            x_pos += 70


class GlowIntensityLegend(QWidget):
    """Widget showing glow intensity scale"""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMaximumHeight(100)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(5, 15, "Glow Intensity Scale")

        y_base = 55
        samples = [("Low", 0.025), ("Med", 0.25), ("High", 0.625), ("Max", 1.0)]

        x_pos = 40
        for label, intensity in samples:
            glow_size = 20 + 30 * intensity
            glow_grad = QRadialGradient(x_pos, y_base, glow_size)
            glow_c = QColor(100, 150, 255)
            glow_c.setAlpha(int(100 * intensity))
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x_pos, y_base), glow_size, glow_size)
            painter.setBrush(QBrush(QColor(100, 150, 255)))
            painter.drawEllipse(QPointF(x_pos, y_base), 8, 8)
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(int(x_pos - 15), int(y_base + 35), label)
            x_pos += 70


class InnerRingLegend(QWidget):
    """Widget showing inner ring colors"""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(70)
        self.setMaximumHeight(70)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(5, 15, "Inner Ring = Orbital Block")

        y_base = 40
        blocks = [('s', get_block_color('s')), ('p', get_block_color('p')),
                 ('d', get_block_color('d')), ('f', get_block_color('f'))]

        x_pos = 35
        for block, color in blocks:
            rect = QRectF(x_pos - 15, y_base - 15, 30, 30)
            painter.setPen(QPen(color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(rect, 45 * 16, 270 * 16)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(x_pos - 5, y_base + 25, block)
            x_pos += 70


class UnifiedPropertyMappingWidget(QWidget):
    """
    Unified property mapping widget combining color mapping and filter range.

    Features:
    - Color gradient bar for color properties (or empty bar for size properties)
    - Yellow draggable tags below for color mapping range (min/max color map)
    - Grey draggable tags above for property value filter range
    - Filter checkbox and reset button in header
    - Color picker swatches for customizing gradient start/end colors (non-wavelength properties only)
    """

    # Signals for value changes
    filter_changed = Signal(bool)  # Filter enabled/disabled
    color_range_changed = Signal(float, float)  # min_map, max_map
    filter_range_changed = Signal(float, float)  # min_filter, max_filter
    gradient_colors_changed = Signal(object, object)  # start_color, end_color (QColor objects)
    wavelength_mode_changed = Signal(object)  # PTWavelengthMode enum

    def __init__(self, property_name="ionization", property_type="color", parent=None):
        super().__init__(parent)
        self.property_name = property_name
        # Convert string to enum if needed
        if isinstance(property_type, str):
            self.property_type = PTPropertyType.from_string(property_type)
        else:
            self.property_type = property_type

        # Property value range (absolute min/max from data)
        self.min_value = 0.0
        self.max_value = 100.0

        # Color mapping range (yellow tags)
        self.min_color_map = 0.0
        self.max_color_map = 100.0

        # Filter range (grey tags)
        self.min_filter = 0.0
        self.max_filter = 100.0

        # Default values for reset
        self.default_min_color_map = 0.0
        self.default_max_color_map = 100.0
        self.default_min_filter = 0.0
        self.default_max_filter = 100.0

        # Filter enabled state
        self.filter_enabled = True

        # Custom gradient colors (None = use smart defaults)
        self.custom_gradient_start = None
        self.custom_gradient_end = None

        # Wavelength display mode (PTWavelengthMode.SPECTRUM = rainbow, PTWavelengthMode.GRADIENT = A-B lerp)
        self.wavelength_mode = PTWavelengthMode.SPECTRUM

        # Dragging state
        self.dragging_tag = None  # 'min_color', 'max_color', 'min_filter', 'max_filter'
        self.drag_start_x = 0

        # UI dimensions
        self.bar_margin = 30  # Increased from 10 to make room for color swatches
        self.bar_y = 35
        self.bar_height = 30
        self.tag_width = 12
        self.tag_height = 15
        self.swatch_size = 16  # Color picker swatch size

        self.setMinimumHeight(110)
        self.setMaximumHeight(110)
        self.setMouseTracking(True)

    def set_property(self, property_name, property_type="color"):
        """Update the property being visualized"""
        self.property_name = property_name
        self.property_type = property_type
        self.update()

    def set_value_range(self, min_value, max_value):
        """Set the absolute property value range"""
        self.min_value = min_value
        self.max_value = max_value

        # Initialize defaults to full range
        self.default_min_color_map = min_value
        self.default_max_color_map = max_value
        self.default_min_filter = min_value
        self.default_max_filter = max_value

        # Initialize current values to defaults
        self.min_color_map = min_value
        self.max_color_map = max_value
        self.min_filter = min_value
        self.max_filter = max_value

        self.update()

    def set_color_map_range(self, min_map, max_map):
        """Set color mapping range (yellow tags)"""
        self.min_color_map = max(self.min_value, min(self.max_value, min_map))
        self.max_color_map = max(self.min_value, min(self.max_value, max_map))
        self.update()

    def set_filter_range(self, min_filter, max_filter):
        """Set filter range (grey tags)"""
        self.min_filter = max(self.min_value, min(self.max_value, min_filter))
        self.max_filter = max(self.min_value, min(self.max_value, max_filter))
        self.update()

    def reset_to_defaults(self):
        """Reset all values to defaults"""
        self.min_color_map = self.default_min_color_map
        self.max_color_map = self.default_max_color_map
        self.min_filter = self.default_min_filter
        self.max_filter = self.default_max_filter
        self.filter_enabled = True
        self.custom_gradient_start = None  # Reset to smart defaults
        self.custom_gradient_end = None
        self.update()
        self.color_range_changed.emit(self.min_color_map, self.max_color_map)
        self.filter_range_changed.emit(self.min_filter, self.max_filter)
        self.filter_changed.emit(self.filter_enabled)
        self.gradient_colors_changed.emit(None, None)  # Emit None to signal smart defaults

    def set_gradient_colors(self, start_color, end_color):
        """Set custom gradient colors (None for smart defaults)"""
        self.custom_gradient_start = start_color
        self.custom_gradient_end = end_color
        self.update()
        self.gradient_colors_changed.emit(start_color, end_color)

    def _get_property_gradient_colors(self):
        """Get start and end gradient colors for current property (custom or smart defaults)"""
        # If custom colors are set, use them
        if self.custom_gradient_start is not None and self.custom_gradient_end is not None:
            return (self.custom_gradient_start, self.custom_gradient_end)

        # Otherwise use smart defaults based on property type
        prop_enum = PTPropertyName.from_string(self.property_name)

        # Default colors based on property type
        if prop_enum in [PTPropertyName.MELTING, PTPropertyName.BOILING]:
            # Temperature: cool to warm (blue to red)
            return (QColor(50, 100, 255), QColor(255, 50, 50))
        elif prop_enum == PTPropertyName.IONIZATION:
            # Energy: purple to yellow
            return (QColor(120, 50, 200), QColor(255, 220, 50))
        elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
            # Electronegativity: green to magenta
            return (QColor(50, 200, 100), QColor(200, 50, 200))
        elif prop_enum == PTPropertyName.RADIUS:
            # Size: blue to orange
            return (QColor(80, 120, 255), QColor(255, 140, 50))
        elif prop_enum == PTPropertyName.DENSITY:
            # Density: cyan to brown
            return (QColor(100, 200, 220), QColor(150, 100, 50))
        elif prop_enum == PTPropertyName.ELECTRON_AFFINITY:
            # Electron affinity: teal to pink
            return (QColor(50, 180, 180), QColor(255, 100, 150))
        else:
            # Default: cool to warm
            return (QColor(100, 150, 255), QColor(255, 150, 100))

    def _generate_gradient_color(self, value):
        """Generate simple A-to-B gradient with white/black fading outside range"""
        # Get gradient colors for this property
        color_start, color_end = self._get_property_gradient_colors()

        # Determine which range we're in
        if value < self.min_color_map:
            # Below min: fade from white to color_start
            if self.min_color_map > self.min_value:
                fade_amount = 1.0 - ((self.min_color_map - value) / (self.min_color_map - self.min_value))
                fade_amount = max(0, min(1, fade_amount))
            else:
                fade_amount = 0
            # Lerp from white to color_start
            r = int(255 * (1 - fade_amount) + color_start.red() * fade_amount)
            g = int(255 * (1 - fade_amount) + color_start.green() * fade_amount)
            b = int(255 * (1 - fade_amount) + color_start.blue() * fade_amount)
            return QColor(r, g, b)
        elif value > self.max_color_map:
            # Above max: fade from color_end to black
            if self.max_value > self.max_color_map:
                fade_amount = (value - self.max_color_map) / (self.max_value - self.max_color_map)
                fade_amount = max(0, min(1, fade_amount))
            else:
                fade_amount = 1
            # Lerp from color_end to black
            r = int(color_end.red() * (1 - fade_amount))
            g = int(color_end.green() * (1 - fade_amount))
            b = int(color_end.blue() * (1 - fade_amount))
            return QColor(r, g, b)
        else:
            # Within range: simple A to B lerp
            if self.max_color_map > self.min_color_map:
                t = (value - self.min_color_map) / (self.max_color_map - self.min_color_map)
            else:
                t = 0.5
            # Lerp from color_start to color_end
            r = int(color_start.red() * (1 - t) + color_end.red() * t)
            g = int(color_start.green() * (1 - t) + color_end.green() * t)
            b = int(color_start.blue() * (1 - t) + color_end.blue() * t)
            return QColor(r, g, b)

    def _get_color_for_value(self, value):
        """Get color for a property value"""
        # Check if it's a wavelength property (spectrum, wavelength, emission_wavelength, etc.)
        if PTPropertyName.is_wavelength_property(self.property_name):
            # Check mode: spectrum (rainbow) or gradient (A-B lerp)
            if self.wavelength_mode == PTWavelengthMode.GRADIENT:
                # Use A-to-B gradient like other properties
                return self._generate_gradient_color(value)
            else:
                # Use rainbow spectrum
                return self._get_spectrum_color(value)
        elif self.property_name == "valence":
            # Valence uses discrete hue colors
            hue = (int(value) * 25) % 360
            return QColor.fromHsv(hue, 200, 255)
        elif self.property_name == "block":
            # Block uses discrete colors
            blocks = ['s', 'p', 'd', 'f']
            idx = int(value) % len(blocks)
            return get_block_color(blocks[idx])
        elif self.property_name == "atomic_number":
            # Atomic number uses rainbow hue
            z = value
            hue = int((z / 118.0) * 360)
            return QColor.fromHsv(hue, 220, 255)
        else:
            # For all other numeric properties, use simple A-to-B gradient with white/black fading
            # This matches the rendering in unified_table._generate_gradient_color()
            return self._generate_gradient_color(value)

    def _get_spectrum_color(self, wavelength):
        """Get color for wavelength with white->rainbow->black fading"""
        wl = wavelength

        if wl < self.min_color_map:
            # Below visualization range - fade from white (at min_value) to violet (at min_color_map)
            if wl <= self.min_value:
                return QColor(255, 255, 255)  # Pure white at minimum
            else:
                # Fade from white to violet as we approach min_color_map
                fade = (self.min_color_map - wl) / (self.min_color_map - self.min_value) if (self.min_color_map - self.min_value) > 0 else 0
                fade = max(0, min(1, fade))
                # Violet color
                violet_r, violet_g, violet_b = 138, 43, 226
                return QColor(
                    int(255 * fade + violet_r * (1 - fade)),
                    int(255 * fade + violet_g * (1 - fade)),
                    int(255 * fade + violet_b * (1 - fade))
                )
        elif wl > self.max_color_map:
            # Above visualization range - fade from red (at max_color_map) to black (at max_value)
            fade = (wl - self.max_color_map) / (self.max_value - self.max_color_map) if (self.max_value - self.max_color_map) > 0 else 1
            fade = max(0, min(1, fade))
            # Pure red
            red_r, red_g, red_b = 255, 0, 0
            return QColor(
                int(red_r * (1 - fade)),
                int(red_g * (1 - fade)),
                int(red_b * (1 - fade))
            )
        else:
            # Within visualization range - show rainbow
            rainbow_t = (wl - self.min_color_map) / (self.max_color_map - self.min_color_map) if (self.max_color_map - self.min_color_map) > 0 else 0

            # Create smooth rainbow from violet to red
            if rainbow_t < 0.17:  # Violet to Blue
                t = rainbow_t / 0.17
                r, g, b = int(138 + (0-138)*t), int(43 + (0-43)*t), 226
            elif rainbow_t < 0.33:  # Blue to Cyan
                t = (rainbow_t - 0.17) / 0.16
                r, g, b = 0, int(0 + 255*t), 255
            elif rainbow_t < 0.5:  # Cyan to Green
                t = (rainbow_t - 0.33) / 0.17
                r, g, b = 0, 255, int(255 - 255*t)
            elif rainbow_t < 0.67:  # Green to Yellow
                t = (rainbow_t - 0.5) / 0.17
                r, g, b = int(0 + 255*t), 255, 0
            elif rainbow_t < 0.83:  # Yellow to Orange
                t = (rainbow_t - 0.67) / 0.16
                r, g, b = 255, int(255 - 128*t), 0
            else:  # Orange to Red
                t = (rainbow_t - 0.83) / 0.17
                r, g, b = 255, int(127 - 127*t), 0

            return QColor(r, g, b)

    def _value_to_x(self, value):
        """Convert property value to x position"""
        width = self.width()
        bar_width = width - 2 * self.bar_margin

        if self.max_value == self.min_value:
            return self.bar_margin

        t = (value - self.min_value) / (self.max_value - self.min_value)
        return self.bar_margin + bar_width * t

    def _x_to_value(self, x):
        """Convert x position to property value"""
        width = self.width()
        bar_width = width - 2 * self.bar_margin

        t = (x - self.bar_margin) / bar_width
        t = max(0.0, min(1.0, t))

        return self.min_value + (self.max_value - self.min_value) * t

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        bar_width = width - 2 * self.bar_margin

        # Draw gradient bar (only for color properties)
        segments = 200
        seg_width = bar_width / segments

        if self.property_type == PTPropertyType.COLOR:
            # Check if this is a categorical property (block, period, etc.)
            prop_enum = PTPropertyName.from_string(self.property_name)

            if PTPropertyName.is_categorical_property(prop_enum):
                # Draw discrete color blocks for categorical properties
                if prop_enum == PTPropertyName.BLOCK:
                    # Draw 4 blocks for s, p, d, f
                    from periodica_app.utils.calculations import get_block_color
                    blocks = ['s', 'p', 'd', 'f']
                    block_width = bar_width / 4
                    for i, block in enumerate(blocks):
                        color = get_block_color(block)
                        x = self.bar_margin + i * block_width
                        painter.fillRect(int(x), self.bar_y, int(block_width), self.bar_height, color)
                # Add other categorical properties here if needed
            else:
                # Draw continuous color gradient
                for i in range(segments):
                    t = i / segments
                    value = self.min_value + (self.max_value - self.min_value) * t
                    color = self._get_color_for_value(value)
                    x = self.bar_margin + i * seg_width
                    painter.fillRect(int(x), self.bar_y, int(seg_width + 1), self.bar_height, color)
        else:
            # For size properties, draw empty bar with border only
            painter.setBrush(QColor(40, 40, 50, 100))
            painter.setPen(QPen(QColor(100, 100, 120, 150), 1))
            painter.drawRect(self.bar_margin, self.bar_y, bar_width, self.bar_height)

        # Draw bar border
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.bar_margin, self.bar_y, bar_width, self.bar_height)

        # Draw grey filter range tags (above bar)
        self._draw_filter_tag(painter, self.min_filter, "min_filter", is_min=True)
        self._draw_filter_tag(painter, self.max_filter, "max_filter", is_min=False)

        # Draw yellow mapping tags (below bar) - for both color and size properties
        # Color properties: controls color gradient range
        # Size properties: controls size mapping range (e.g., 1-10px)
        # Hide for categorical properties (block, period, etc.) since they have discrete values
        prop_enum = PTPropertyName.from_string(self.property_name)
        if not PTPropertyName.is_categorical_property(prop_enum):
            self._draw_color_tag(painter, self.min_color_map, "min_color", is_min=True)
            self._draw_color_tag(painter, self.max_color_map, "max_color", is_min=False)

        # Draw color picker swatches (for non-categorical, and wavelength in gradient mode)
        prop_enum = PTPropertyName.from_string(self.property_name)
        should_show_swatches = (
            self.property_type == PTPropertyType.COLOR and
            not PTPropertyName.is_categorical_property(prop_enum) and
            (not PTPropertyName.is_wavelength_property(prop_enum) or self.wavelength_mode == PTWavelengthMode.GRADIENT)
        )
        if should_show_swatches:
            self._draw_color_swatches(painter)

    def _draw_filter_tag(self, painter, value, tag_id, is_min):
        """Draw grey filter tag above the bar"""
        x = self._value_to_x(value)

        # Draw vertical line from tag to bar
        painter.setPen(QPen(QColor(150, 150, 150, 200), 2))
        painter.drawLine(int(x), self.bar_y - self.tag_height - 2, int(x), self.bar_y)

        # Draw triangle tag pointing down
        tag_y = self.bar_y - self.tag_height - 2
        triangle = QPolygonF([
            QPointF(x, tag_y + self.tag_height),
            QPointF(x - self.tag_width / 2, tag_y),
            QPointF(x + self.tag_width / 2, tag_y)
        ])

        # Highlight if dragging
        if self.dragging_tag == tag_id:
            painter.setBrush(QColor(200, 200, 200))
        else:
            painter.setBrush(QColor(150, 150, 150))
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawPolygon(triangle)

        # Draw value label above tag
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 8))
        label = f"{value:.1f}"
        text_width = painter.fontMetrics().horizontalAdvance(label)
        painter.drawText(int(x - text_width / 2), tag_y - 3, label)

    def _draw_color_tag(self, painter, value, tag_id, is_min):
        """Draw yellow color mapping tag below the bar"""
        x = self._value_to_x(value)

        # Draw vertical line from bar to tag
        painter.setPen(QPen(QColor(255, 255, 0, 220), 2))
        painter.drawLine(int(x), self.bar_y + self.bar_height, int(x), self.bar_y + self.bar_height + self.tag_height + 2)

        # Draw triangle tag pointing up
        tag_y = self.bar_y + self.bar_height + 2
        triangle = QPolygonF([
            QPointF(x, tag_y),
            QPointF(x - self.tag_width / 2, tag_y + self.tag_height),
            QPointF(x + self.tag_width / 2, tag_y + self.tag_height)
        ])

        # Highlight if dragging
        if self.dragging_tag == tag_id:
            painter.setBrush(QColor(255, 255, 100))
        else:
            painter.setBrush(QColor(255, 255, 0))
        painter.setPen(QPen(QColor(200, 200, 0), 1))
        painter.drawPolygon(triangle)

        # Draw value label below tag
        painter.setPen(QColor(255, 255, 0))
        painter.setFont(QFont("Arial", 8))
        label = f"{value:.1f}"
        text_width = painter.fontMetrics().horizontalAdvance(label)
        painter.drawText(int(x - text_width / 2), tag_y + self.tag_height + 12, label)

    def _draw_color_swatches(self, painter):
        """Draw color picker swatches on left and right of gradient bar"""
        # Get current gradient colors
        color_start, color_end = self._get_property_gradient_colors()

        # Left swatch (start color)
        left_x = self.bar_margin - self.swatch_size - 6
        swatch_y = self.bar_y + (self.bar_height - self.swatch_size) // 2

        painter.setBrush(QBrush(color_start))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
        painter.drawRect(int(left_x), int(swatch_y), self.swatch_size, self.swatch_size)

        # Right swatch (end color)
        right_x = self.bar_margin + (self.width() - 2 * self.bar_margin) + 6

        painter.setBrush(QBrush(color_end))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
        painter.drawRect(int(right_x), int(swatch_y), self.swatch_size, self.swatch_size)

    def _get_swatch_rects(self):
        """Get the clickable rectangles for color swatches"""
        prop_enum = PTPropertyName.from_string(self.property_name)

        # Return rects for non-categorical, and wavelength in gradient mode
        should_show_swatches = (
            self.property_type == PTPropertyType.COLOR and
            not PTPropertyName.is_categorical_property(prop_enum) and
            (not PTPropertyName.is_wavelength_property(prop_enum) or self.wavelength_mode == PTWavelengthMode.GRADIENT)
        )
        if not should_show_swatches:
            return []

        swatch_y = self.bar_y + (self.bar_height - self.swatch_size) // 2
        left_x = self.bar_margin - self.swatch_size - 6
        right_x = self.bar_margin + (self.width() - 2 * self.bar_margin) + 6

        return [
            ('start', QRectF(left_x, swatch_y, self.swatch_size, self.swatch_size)),
            ('end', QRectF(right_x, swatch_y, self.swatch_size, self.swatch_size))
        ]

    def mousePressEvent(self, event):
        """Handle mouse press for tag dragging and color swatch clicks"""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        x = event.position().x()
        y = event.position().y()

        # Check if clicking on color swatches first
        for swatch_id, swatch_rect in self._get_swatch_rects():
            if swatch_rect.contains(x, y):
                self._open_color_picker(swatch_id)
                return

        # Check if clicking on any tag
        # Build tag list based on property type
        prop_enum = PTPropertyName.from_string(self.property_name)
        is_categorical = PTPropertyName.is_categorical_property(prop_enum)

        tags = [
            ('min_filter', self._value_to_x(self.min_filter), self.bar_y - self.tag_height - 2, self.tag_height),
            ('max_filter', self._value_to_x(self.max_filter), self.bar_y - self.tag_height - 2, self.tag_height),
        ]

        # Only add yellow tags for non-categorical properties
        if not is_categorical:
            tags.extend([
                ('min_color', self._value_to_x(self.min_color_map), self.bar_y + self.bar_height + 2, self.tag_height),
                ('max_color', self._value_to_x(self.max_color_map), self.bar_y + self.bar_height + 2, self.tag_height),
            ])

        for tag_id, tag_x, tag_y, tag_h in tags:
            # Check if click is within tag triangle area
            if abs(x - tag_x) < self.tag_width and abs(y - (tag_y + tag_h / 2)) < tag_h:
                self.dragging_tag = tag_id
                self.drag_start_x = x
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.update()
                break

    def _open_color_picker(self, swatch_id):
        """Open color picker dialog for gradient start or end color"""
        from PySide6.QtWidgets import QColorDialog

        # Get current color
        color_start, color_end = self._get_property_gradient_colors()
        current_color = color_start if swatch_id == 'start' else color_end

        # Open color picker dialog
        color = QColorDialog.getColor(current_color, self, f"Choose Gradient {'Start' if swatch_id == 'start' else 'End'} Color")

        if color.isValid():
            # Update custom colors
            if swatch_id == 'start':
                # If end color is not custom yet, use smart default
                if self.custom_gradient_end is None:
                    _, default_end = self._get_property_gradient_colors()
                    self.custom_gradient_end = default_end
                self.custom_gradient_start = color
            else:  # end
                # If start color is not custom yet, use smart default
                if self.custom_gradient_start is None:
                    default_start, _ = self._get_property_gradient_colors()
                    self.custom_gradient_start = default_start
                self.custom_gradient_end = color

            self.gradient_colors_changed.emit(self.custom_gradient_start, self.custom_gradient_end)
            self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move for tag dragging"""
        if self.dragging_tag is None:
            # Update cursor when hovering over tags
            x = event.position().x()
            y = event.position().y()

            tags = [
                (self._value_to_x(self.min_filter), self.bar_y - self.tag_height - 2, self.tag_height),
                (self._value_to_x(self.max_filter), self.bar_y - self.tag_height - 2, self.tag_height),
                # Yellow tags for both color and size mapping
                (self._value_to_x(self.min_color_map), self.bar_y + self.bar_height + 2, self.tag_height),
                (self._value_to_x(self.max_color_map), self.bar_y + self.bar_height + 2, self.tag_height),
            ]

            hovering = False
            for tag_x, tag_y, tag_h in tags:
                if abs(x - tag_x) < self.tag_width and abs(y - (tag_y + tag_h / 2)) < tag_h:
                    hovering = True
                    break

            if hovering:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        # Dragging a tag
        x = event.position().x()
        new_value = self._x_to_value(x)

        if self.dragging_tag == 'min_filter':
            self.min_filter = max(self.min_value, min(self.max_filter, new_value))
            self.filter_range_changed.emit(self.min_filter, self.max_filter)
        elif self.dragging_tag == 'max_filter':
            self.max_filter = max(self.min_filter, min(self.max_value, new_value))
            self.filter_range_changed.emit(self.min_filter, self.max_filter)
        elif self.dragging_tag == 'min_color':
            self.min_color_map = max(self.min_value, min(self.max_color_map, new_value))
            self.color_range_changed.emit(self.min_color_map, self.max_color_map)
        elif self.dragging_tag == 'max_color':
            self.max_color_map = max(self.min_color_map, min(self.max_value, new_value))
            self.color_range_changed.emit(self.min_color_map, self.max_color_map)

        self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging"""
        if event.button() == Qt.MouseButton.LeftButton and self.dragging_tag is not None:
            self.dragging_tag = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()


class UnifiedPropertyControl(QWidget):
    """
    Complete property control widget with header (title, checkbox, reset button)
    and unified mapping visualization.
    """

    # Signals
    filter_changed = Signal(bool)
    color_range_changed = Signal(float, float)
    filter_range_changed = Signal(float, float)

    def __init__(self, title="Property", property_name="ionization", property_type="color", parent=None):
        super().__init__(parent)
        self.title = title
        self.property_name = property_name
        self.property_type = property_type

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Header with title, checkbox, and reset button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Filter checkbox
        self.filter_check = QCheckBox("Filter")
        self.filter_check.setStyleSheet("color: white; font-size: 10px;")
        self.filter_check.setChecked(True)
        self.filter_check.stateChanged.connect(self._on_filter_toggled)
        header_layout.addWidget(self.filter_check)

        # Reset button
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 70, 90, 200);
                color: white;
                border: 1px solid #4fc3f7;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: rgba(90, 90, 110, 200);
            }
            QPushButton:pressed {
                background-color: rgba(50, 50, 70, 200);
            }
        """)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        header_layout.addWidget(self.reset_btn)

        layout.addWidget(header)

        # Unified mapping widget
        self.mapping_widget = UnifiedPropertyMappingWidget(property_name, property_type)
        self.mapping_widget.filter_changed.connect(self._forward_filter_changed)
        self.mapping_widget.color_range_changed.connect(self._forward_color_range_changed)
        self.mapping_widget.filter_range_changed.connect(self._forward_filter_range_changed)
        layout.addWidget(self.mapping_widget)

    def set_property(self, property_name, property_type="color"):
        """Update the property being visualized"""
        self.property_name = property_name
        self.property_type = property_type
        self.mapping_widget.set_property(property_name, property_type)

    def set_value_range(self, min_value, max_value):
        """Set the absolute property value range"""
        self.mapping_widget.set_value_range(min_value, max_value)

    def set_color_map_range(self, min_map, max_map):
        """Set color mapping range"""
        self.mapping_widget.set_color_map_range(min_map, max_map)

    def set_filter_range(self, min_filter, max_filter):
        """Set filter range"""
        self.mapping_widget.set_filter_range(min_filter, max_filter)

    def _on_filter_toggled(self, state):
        """Handle filter checkbox toggle"""
        enabled = (state == Qt.CheckState.Checked.value)
        self.mapping_widget.filter_enabled = enabled
        self.filter_changed.emit(enabled)

    def _on_reset_clicked(self):
        """Handle reset button click"""
        self.mapping_widget.reset_to_defaults()
        self.filter_check.setChecked(True)

    def _forward_filter_changed(self, enabled):
        """Forward filter changed signal"""
        self.filter_check.setChecked(enabled)
        self.filter_changed.emit(enabled)

    def _forward_color_range_changed(self, min_map, max_map):
        """Forward color range changed signal"""
        self.color_range_changed.emit(min_map, max_map)

    def _forward_filter_range_changed(self, min_filter, max_filter):
        """Forward filter range changed signal"""
        self.filter_range_changed.emit(min_filter, max_filter)
