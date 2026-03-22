"""
Alloy Info Panel
Displays detailed information about selected alloys including:
- Microstructure visualization
- Properties bar chart
- Component pie chart
- Phase diagram view
"""

import json
import math
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QFrame, QTabWidget, QStackedWidget
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen, QRadialGradient, QPainterPath, QLinearGradient

from periodica.core.alloy_enums import (AlloyCategory, CrystalStructure, ComponentRole, get_element_color)
from periodica.data.data_manager import DataCategory
from periodica_app.ui.inline_editor import InlineDataEditor
from periodica_app.ui.grain_visualization import GrainVisualizationWidget


def load_layout_config():
    """Load layout configuration from JSON file"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'layout_config', 'layout_config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Global layout config cache
_layout_config = None


def get_layout_config():
    """Get cached layout configuration"""
    global _layout_config
    if _layout_config is None:
        _layout_config = load_layout_config()
    return _layout_config


def get_alloys_layout():
    """Get alloys-specific layout configuration with defaults"""
    config = get_layout_config()
    return config.get('alloys', {})

# Import crystalline math for microstructure visualization
try:
    from periodica.utils.crystalline_math import VoronoiTessellation, SimplexNoise, MicrostructureRenderer
    HAS_CRYSTALLINE_MATH = True
except ImportError:
    HAS_CRYSTALLINE_MATH = False


class MicrostructureWidget(QFrame):
    """Widget to display alloy microstructure"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alloy = None
        self._layout_config = get_alloys_layout().get('microstructure', {})
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 45, 200);
                border: 2px solid #667eea;
                border-radius: 12px;
            }
        """)

    def set_alloy(self, alloy):
        """Set alloy to display"""
        self.alloy = alloy
        self.update()

    def _get_microstructure_params(self):
        """Extract microstructure parameters from alloy JSON data"""
        if not self.alloy:
            return {}

        # Try to get from nested Microstructure.GrainStructure first (proper JSON format)
        microstructure = self.alloy.get('Microstructure', {})
        grain_structure = microstructure.get('GrainStructure', {})

        # Get crystallographic orientation for IPF coloring
        orientation = self.alloy.get('CrystallographicOrientation', {})
        odf = orientation.get('ODF', {})

        # Get layout defaults
        defaults = self._layout_config

        return {
            'grain_seed_density': grain_structure.get('VoronoiSeedDensity_per_mm2',
                                    self.alloy.get('grain_seed_density',
                                    defaults.get('default_grain_seed_density', 400))),
            'grain_size': grain_structure.get('AverageGrainSize_um',
                            self.alloy.get('grain_size',
                            defaults.get('default_grain_size', 50))),
            'grain_aspect_ratio': grain_structure.get('GrainAspectRatio', 1.0),
            'grain_std_dev': grain_structure.get('GrainSizeStdDev', 0.35),
            'phi1_range': odf.get('Phi1_range', [0, 360]),
            'phi_range': odf.get('Phi_range', [0, 90]),
            'phi2_range': odf.get('Phi2_range', [0, 90]),
        }

    def _get_crystal_structure(self):
        """Get crystal structure from alloy JSON data"""
        if not self.alloy:
            return 'Unknown'

        # Try LatticeProperties.PrimaryStructure first (proper JSON format)
        lattice = self.alloy.get('LatticeProperties', {})
        if lattice.get('PrimaryStructure'):
            return lattice['PrimaryStructure']

        # Fallback to flat structure
        return self.alloy.get('crystal_structure', 'Unknown')

    def paintEvent(self, event):
        """Paint the microstructure visualization"""
        super().paintEvent(event)

        if not self.alloy:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Voronoi grain structure
        self._draw_grain_structure(painter)

        # Draw structure legend
        self._draw_legend(painter)

        painter.end()

    def _draw_grain_structure(self, painter):
        """Draw Voronoi-like grain structure with IPF coloring"""
        # Get layout config values
        config = self._layout_config
        margin = config.get('margin', 15)
        legend_height = config.get('legend_height', 30)
        grain_count_range = config.get('grain_count_range', [10, 50])
        grain_size_scale = config.get('grain_size_scale', 0.3)
        grain_sides = config.get('grain_sides', 6)

        # Calculate drawing area dynamically
        width = self.width() - 2 * margin
        height = self.height() - 2 * margin - legend_height

        # Get microstructure parameters from alloy data
        params = self._get_microstructure_params()
        grain_seed_density = params['grain_seed_density']
        grain_size = params['grain_size']
        grain_aspect_ratio = params['grain_aspect_ratio']
        grain_std_dev = params['grain_std_dev']
        phi1_range = params['phi1_range']
        phi_range = params['phi_range']
        phi2_range = params['phi2_range']

        # Calculate number of grains based on area and seed density
        area_mm2 = (width * height) / 10000  # Convert to mm^2 approx
        num_grains = max(grain_count_range[0],
                        min(grain_count_range[1],
                            int(area_mm2 * grain_seed_density / 10000)))

        # Generate deterministic grain centers based on alloy name
        seed = sum(ord(c) for c in self.alloy.get('Name', self.alloy.get('name', 'alloy')))

        grain_centers = []
        for i in range(num_grains):
            # Pseudo-random positions based on seed
            gx = margin + ((seed * (i + 1) * 17 + i * 31) % int(width))
            gy = margin + ((seed * (i + 1) * 23 + i * 43) % int(height))

            # Orientation for IPF coloring from alloy's ODF ranges
            phi1 = phi1_range[0] + ((seed * (i + 3) * 7) % (phi1_range[1] - phi1_range[0]))
            phi = phi_range[0] + ((seed * (i + 5) * 11) % (phi_range[1] - phi_range[0]))
            phi2 = phi2_range[0] + ((seed * (i + 7) * 13) % (phi2_range[1] - phi2_range[0]))

            # Size variation based on grain_std_dev
            size_variation = 0.8 + grain_std_dev * ((seed + i) % 10) / 10

            grain_centers.append({
                'x': gx, 'y': gy,
                'orientation': (phi1, phi, phi2),
                'size': grain_size * size_variation,
                'aspect_ratio': grain_aspect_ratio
            })

        # Draw grain regions
        for i, grain in enumerate(grain_centers):
            # IPF-like coloring based on orientation
            phi1, phi, phi2 = grain['orientation']
            phi1_norm = (phi1 - phi1_range[0]) / max(1, phi1_range[1] - phi1_range[0])
            phi_norm = (phi - phi_range[0]) / max(1, phi_range[1] - phi_range[0])
            phi2_norm = (phi2 - phi2_range[0]) / max(1, phi2_range[1] - phi2_range[0])

            r = int(phi1_norm * 200 + 55)
            g = int(phi_norm * 200 + 55)
            b = int(phi2_norm * 200 + 55)
            grain_color = QColor(r, g, b, 180)

            # Draw grain as polygon-like region
            size = grain['size'] * grain_size_scale

            gradient = QRadialGradient(grain['x'], grain['y'], size)
            gradient.setColorAt(0, grain_color.lighter(115))
            gradient.setColorAt(0.7, grain_color)
            gradient.setColorAt(1, grain_color.darker(110))

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)

            # Draw as slightly irregular polygon with configurable sides
            path = QPainterPath()
            angle_step = 2 * math.pi / grain_sides
            for j in range(grain_sides):
                angle = j * angle_step + (seed + i * j) % 10 * 0.1
                r_var = size * (0.9 + 0.2 * ((seed + i + j) % 10) / 10)
                # Apply aspect ratio to y dimension
                px = grain['x'] + r_var * math.cos(angle)
                py = grain['y'] + r_var * math.sin(angle) * grain['aspect_ratio']
                if j == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            path.closeSubpath()
            painter.drawPath(path)

        # Draw grain boundaries
        painter.setPen(QPen(QColor(30, 30, 40, 200), 1))
        for idx, grain in enumerate(grain_centers):
            size = grain['size'] * grain_size_scale
            path = QPainterPath()
            angle_step = 2 * math.pi / grain_sides
            for j in range(grain_sides):
                angle = j * angle_step + (seed + idx * j) % 10 * 0.1
                r_var = size * (0.9 + 0.2 * ((seed + idx + j) % 10) / 10)
                px = grain['x'] + r_var * math.cos(angle)
                py = grain['y'] + r_var * math.sin(angle) * grain['aspect_ratio']
                if j == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            path.closeSubpath()
            painter.drawPath(path)

    def _draw_legend(self, painter):
        """Draw structure legend at bottom"""
        config = self._layout_config
        legend_height = config.get('legend_height', 30)

        structure = self._get_crystal_structure()
        structure_color = QColor(CrystalStructure.get_color(structure))

        # Calculate legend position dynamically
        legend_y = self.height() - legend_height
        legend_rect = QRectF(10, legend_y, self.width() - 20, legend_height - 8)

        # Background
        painter.setBrush(QBrush(QColor(30, 30, 50, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(legend_rect, 5, 5)

        # Structure indicator - positioned relative to legend
        indicator_y = legend_y + (legend_height - 8) / 2
        painter.setBrush(QBrush(structure_color))
        painter.drawEllipse(QPointF(25, indicator_y), 6, 6)

        # Text
        painter.setPen(QPen(QColor(200, 200, 220)))
        painter.setFont(QFont("Arial", 9))
        text_y = legend_y + (legend_height - 8) / 2 + 4
        painter.drawText(int(legend_rect.left() + 25), int(text_y),
                        f"{structure} - IPF Colored Grains")


class PropertiesBarWidget(QFrame):
    """Widget to display properties as bar chart"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alloy = None
        self._layout_config = get_alloys_layout().get('properties_bar', {})
        self.setMinimumHeight(150)
        self.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 45, 200);
                border: 2px solid #667eea;
                border-radius: 12px;
            }
        """)

    def set_alloy(self, alloy):
        """Set alloy to display"""
        self.alloy = alloy
        self.update()

    def _get_mechanical_properties(self):
        """Extract mechanical properties from alloy JSON data"""
        if not self.alloy:
            return {}

        # Try to get from nested MechanicalProperties first (proper JSON format)
        mech = self.alloy.get('MechanicalProperties', {})
        phys = self.alloy.get('PhysicalProperties', {})

        return {
            'tensile_strength': mech.get('TensileStrength_MPa',
                                  self.alloy.get('tensile_strength', 0)),
            'yield_strength': mech.get('YieldStrength_MPa',
                                self.alloy.get('yield_strength', 0)),
            'hardness': phys.get('BrinellHardness_HB',
                          self.alloy.get('hardness', 0)),
            'elongation': mech.get('Elongation_percent',
                            self.alloy.get('elongation', 0)),
        }

    def paintEvent(self, event):
        """Paint the properties bar chart"""
        super().paintEvent(event)

        if not self.alloy:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get layout config values
        config = self._layout_config
        margin = config.get('margin', 15)
        bar_height = config.get('bar_height', 18)
        spacing = config.get('bar_spacing', 8)
        label_width_ratio = config.get('label_width_ratio', 0.35)
        value_text_width = config.get('value_text_width', 50)
        title_height = config.get('title_height', 25)
        property_ranges = config.get('property_ranges', {})

        # Calculate dynamic layout
        label_width = int(self.width() * label_width_ratio)
        bar_start = margin + label_width
        bar_width = self.width() - bar_start - margin - value_text_width

        # Get actual property values from alloy data
        props = self._get_mechanical_properties()

        # Build properties list with values from JSON and ranges from config
        properties = []
        prop_configs = [
            ('Tensile Strength', 'tensile_strength'),
            ('Yield Strength', 'yield_strength'),
            ('Hardness (HB)', 'hardness'),
            ('Elongation (%)', 'elongation'),
        ]

        for display_name, key in prop_configs:
            value = props.get(key, 0)
            range_config = property_ranges.get(key, {})
            max_val = range_config.get('max', 100)
            unit = range_config.get('unit', '')
            color = range_config.get('color', '#888888')
            properties.append((display_name, value, max_val, color, unit))

        y = margin

        # Title
        painter.setPen(QPen(QColor(200, 200, 220)))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(margin, y + 12, "Mechanical Properties")
        y += title_height

        painter.setFont(QFont("Arial", 9))

        for name, value, max_val, color, unit in properties:
            # Label
            painter.setPen(QPen(QColor(180, 180, 200)))
            painter.drawText(margin, int(y + bar_height - 4), name)

            # Bar background
            bar_rect = QRectF(bar_start, y, bar_width, bar_height)
            painter.setBrush(QBrush(QColor(50, 50, 70)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_rect, 3, 3)

            # Value bar - calculate fill based on value / max
            fill_ratio = min(1.0, value / max_val) if max_val > 0 else 0
            fill_width = fill_ratio * bar_width
            fill_rect = QRectF(bar_start, y, fill_width, bar_height)

            gradient = QLinearGradient(bar_start, y, bar_start + fill_width, y)
            bar_color = QColor(color)
            gradient.setColorAt(0, bar_color.darker(120))
            gradient.setColorAt(1, bar_color)

            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(fill_rect, 3, 3)

            # Value text
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(int(bar_start + bar_width + 5), int(y + bar_height - 4),
                           f"{value:.0f}{unit}")

            y += bar_height + spacing

        painter.end()


class CompositionPieWidget(QFrame):
    """Widget to display composition as pie chart"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alloy = None
        self._layout_config = get_alloys_layout().get('composition_pie', {})
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 45, 200);
                border: 2px solid #667eea;
                border-radius: 12px;
            }
        """)

    def set_alloy(self, alloy):
        """Set alloy to display"""
        self.alloy = alloy
        self.update()

    def _get_composition_data(self):
        """Extract and process composition data from alloy JSON"""
        if not self.alloy:
            return []

        components = self.alloy.get('Components', [])
        if not components:
            return []

        # Get min display threshold from config
        min_display_pct = self._layout_config.get('min_display_percent', 0.5)

        # Calculate average percentages and filter/sort by amount
        comp_data = []
        for comp in components:
            elem = comp.get('Element', '?')
            min_pct = comp.get('MinPercent', 0)
            max_pct = comp.get('MaxPercent', 0)
            avg_pct = (min_pct + max_pct) / 2
            if avg_pct >= min_display_pct:
                comp_data.append((elem, avg_pct))

        # Sort by percentage descending
        comp_data.sort(key=lambda x: -x[1])
        return comp_data

    def paintEvent(self, event):
        """Paint the composition pie chart"""
        super().paintEvent(event)

        if not self.alloy:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get layout config values
        config = self._layout_config
        center_x_ratio = config.get('center_x_ratio', 0.3)
        center_y_ratio = config.get('center_y_ratio', 0.55)
        radius_ratio = config.get('radius_ratio', 0.28)
        donut_hole_ratio = config.get('donut_hole_ratio', 0.4)
        legend_x_ratio = config.get('legend_x_ratio', 0.55)
        legend_y_offset = config.get('legend_y_offset', 40)
        legend_item_height = config.get('legend_item_height', 18)
        max_legend_items = config.get('max_legend_items', 6)
        start_angle_deg = config.get('start_angle_deg', 90)

        # Calculate dynamic positions based on widget size
        widget_width = self.width()
        widget_height = self.height()

        cx = int(widget_width * center_x_ratio)
        cy = int(widget_height * center_y_ratio)
        radius = int(min(widget_width, widget_height) * radius_ratio)

        # Title
        painter.setPen(QPen(QColor(200, 200, 220)))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(15, 22, "Composition")

        # Get processed composition data
        comp_data = self._get_composition_data()
        if not comp_data:
            painter.setFont(QFont("Arial", 9))
            painter.drawText(15, 60, "No composition data")
            painter.end()
            return

        total = sum(pct for _, pct in comp_data)

        # Draw pie chart with angles calculated from composition percentages
        start_angle = start_angle_deg * 16  # Qt uses 1/16th of a degree

        for elem, pct in comp_data:
            # Calculate span angle based on composition percentage
            span_angle = int((pct / total) * 360 * 16) if total > 0 else 0

            color = QColor(get_element_color(elem))
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))

            pie_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            painter.drawPie(pie_rect, start_angle, span_angle)

            start_angle += span_angle

        # Draw center circle (donut hole)
        hole_radius = radius * donut_hole_ratio
        painter.setBrush(QBrush(QColor(30, 30, 50)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), hole_radius, hole_radius)

        # Draw legend with dynamic positioning
        legend_x = int(widget_width * legend_x_ratio)
        legend_y = legend_y_offset
        painter.setFont(QFont("Arial", 8))

        # Limit legend items based on config
        display_items = comp_data[:max_legend_items]

        for i, (elem, pct) in enumerate(display_items):
            color = QColor(get_element_color(elem))

            # Color box
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(legend_x, legend_y + i * legend_item_height, 12, 12)

            # Text with percentage
            painter.setPen(QPen(QColor(200, 200, 220)))
            painter.drawText(legend_x + 18, legend_y + i * legend_item_height + 10,
                           f"{elem}: {pct:.1f}%")

        painter.end()


class AlloyInfoPanel(QWidget):
    """Panel displaying detailed alloy information"""

    data_saved = Signal(dict)
    edit_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.alloy = None
        self._editor = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create stacked widget to switch between display and edit modes
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Display widget (index 0)
        display_widget = QWidget()
        display_layout = QVBoxLayout(display_widget)
        display_layout.setContentsMargins(15, 15, 15, 15)
        display_layout.setSpacing(10)

        title = QLabel("Alloy Analysis")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        display_layout.addWidget(title)

        # Create tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #667eea;
                border-radius: 8px;
                background: rgba(25, 25, 45, 150);
            }
            QTabBar::tab {
                background: rgba(40, 40, 60, 200);
                color: white;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #667eea;
            }
            QTabBar::tab:hover {
                background: rgba(102, 126, 234, 150);
            }
        """)

        # Overview tab
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)
        overview_layout.setSpacing(10)

        # Use the unified grain visualization widget (read-only mode)
        self.microstructure_widget = GrainVisualizationWidget(editable=False)
        self.microstructure_widget.setMinimumHeight(200)
        overview_layout.addWidget(self.microstructure_widget)

        self.properties_widget = PropertiesBarWidget()
        overview_layout.addWidget(self.properties_widget)

        self.tabs.addTab(overview_widget, "Overview")

        # Composition tab
        comp_widget = QWidget()
        comp_layout = QVBoxLayout(comp_widget)

        self.composition_widget = CompositionPieWidget()
        comp_layout.addWidget(self.composition_widget)

        self.tabs.addTab(comp_widget, "Composition")

        # Details tab
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background: rgba(25, 25, 45, 200);
                color: white;
                border: 2px solid #667eea;
                border-radius: 12px;
                padding: 15px;
                font-size: 12px;
            }
        """)
        self.tabs.addTab(self.info_text, "Details")

        display_layout.addWidget(self.tabs)

        self.stack.addWidget(display_widget)

        self.show_default()

    def show_default(self):
        """Show default message"""
        # Clear the grain visualization
        self.microstructure_widget.viz.grains = []
        self.microstructure_widget.viz.update()
        self.properties_widget.set_alloy(None)
        self.composition_widget.set_alloy(None)

        self.info_text.setHtml("""
            <h3 style='color: #667eea;'>Click any alloy to view:</h3>
            <ul>
                <li><b>Microstructure Visualization</b></li>
                <li><b>Mechanical Properties</b></li>
                <li><b>Elemental Composition</b></li>
                <li><b>Lattice Properties</b></li>
                <li><b>Applications</b></li>
            </ul>
            <p style='background: rgba(102,126,234,0.15); padding: 10px; border-radius: 5px;'>
            <b>Tip:</b> Use the control panel to filter alloys by category,
            crystal structure, or primary element.
            </p>
        """)

    def update_alloy(self, alloy):
        """Update panel with alloy data"""
        if not alloy:
            self.show_default()
            return

        self.alloy = alloy
        # Update microstructure using unified grain visualization
        self.microstructure_widget.set_from_alloy_data(alloy)
        self.properties_widget.set_alloy(alloy)
        self.composition_widget.set_alloy(alloy)

        # Build HTML content - support both nested and flat JSON structures
        name = alloy.get('Name', 'Unknown')
        formula = alloy.get('Formula', alloy.get('formula', ''))
        category = alloy.get('Category', alloy.get('category', 'Unknown'))
        subcategory = alloy.get('SubCategory', alloy.get('subcategory', ''))
        description = alloy.get('Description', alloy.get('description', ''))

        # Physical properties - read from nested PhysicalProperties or flat structure
        phys = alloy.get('PhysicalProperties', {})
        density = phys.get('Density_g_cm3', alloy.get('density', 0))
        melting_point = phys.get('MeltingPoint_K', alloy.get('melting_point', 0))
        thermal_cond = phys.get('ThermalConductivity_W_mK', alloy.get('thermal_conductivity', 0))
        youngs_mod = phys.get('YoungsModulus_GPa', alloy.get('youngs_modulus', 0))

        # Mechanical properties - read from nested MechanicalProperties or flat structure
        mech = alloy.get('MechanicalProperties', {})
        tensile = mech.get('TensileStrength_MPa', alloy.get('tensile_strength', 0))
        yield_str = mech.get('YieldStrength_MPa', alloy.get('yield_strength', 0))
        hardness = phys.get('BrinellHardness_HB', alloy.get('hardness', 0))
        elongation = mech.get('Elongation_percent', alloy.get('elongation', 0))

        # Lattice properties - read from nested LatticeProperties or flat structure
        lattice = alloy.get('LatticeProperties', {})
        lattice_params = lattice.get('LatticeParameters', {})
        structure = lattice.get('PrimaryStructure', alloy.get('crystal_structure', 'Unknown'))
        lattice_a = lattice_params.get('a_pm', alloy.get('lattice_parameter_a', 0))
        packing = lattice.get('AtomicPackingFactor', alloy.get('packing_factor', 0))

        # Colors
        category_color = AlloyCategory.get_color(category)
        structure_color = CrystalStructure.get_color(structure)

        # Applications
        applications = alloy.get('Applications', [])
        apps_html = ""
        if applications:
            apps_html = "<h3 style='color: #667eea; margin-top: 15px;'>Applications:</h3><ul>"
            for app in applications[:5]:
                apps_html += f"<li>{app}</li>"
            apps_html += "</ul>"

        # Components
        components = alloy.get('Components', [])
        comp_html = ""
        if components:
            comp_html = "<h3 style='color: #667eea; margin-top: 15px;'>Components:</h3>"
            comp_html += "<table style='width: 100%; color: white;'>"
            for comp in components[:8]:
                elem = comp.get('Element', '?')
                min_pct = comp.get('MinPercent', 0)
                max_pct = comp.get('MaxPercent', 0)
                role = comp.get('Role', '')
                role_color = ComponentRole.get_color(role)
                comp_html += f"""
                    <tr>
                        <td><b>{elem}</b></td>
                        <td>{min_pct:.1f} - {max_pct:.1f}%</td>
                        <td><span style='color: {role_color};'>{role}</span></td>
                    </tr>
                """
            comp_html += "</table>"

        html = f"""
            <h2 style='color: #667eea;'>{name}</h2>
            <div style='font-size: 16px; font-weight: bold; color: white;'>{formula}</div>
            <div style='color: #aaa; font-size: 11px;'>{description[:100]}{'...' if len(description) > 100 else ''}</div>
            <hr style='border-color: #667eea;'>

            <h3 style='color: #667eea;'>Physical Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Density:</b></td>
                    <td><b style='color: #00ff88;'>{density:.2f}</b> g/cm³</td>
                </tr>
                <tr>
                    <td><b>Melting Point:</b></td>
                    <td><b style='color: #00ff88;'>{melting_point:.0f} K</b> ({melting_point - 273.15:.0f}°C)</td>
                </tr>
                <tr>
                    <td><b>Thermal Conductivity:</b></td>
                    <td>{thermal_cond:.1f} W/m·K</td>
                </tr>
                <tr>
                    <td><b>Young's Modulus:</b></td>
                    <td>{youngs_mod:.0f} GPa</td>
                </tr>
            </table>

            <h3 style='color: #667eea; margin-top: 15px;'>Mechanical Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Tensile Strength:</b></td>
                    <td><b style='color: #4CAF50;'>{tensile:.0f}</b> MPa</td>
                </tr>
                <tr>
                    <td><b>Yield Strength:</b></td>
                    <td><b style='color: #2196F3;'>{yield_str:.0f}</b> MPa</td>
                </tr>
                <tr>
                    <td><b>Hardness:</b></td>
                    <td>{hardness:.0f} HB</td>
                </tr>
                <tr>
                    <td><b>Elongation:</b></td>
                    <td>{elongation:.0f}%</td>
                </tr>
            </table>

            <h3 style='color: #667eea; margin-top: 15px;'>Lattice Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Crystal Structure:</b></td>
                    <td><span style='background: {structure_color}; padding: 2px 8px;
                        border-radius: 4px; color: black;'>{structure}</span></td>
                </tr>
                <tr>
                    <td><b>Lattice Parameter:</b></td>
                    <td>{lattice_a:.2f} pm</td>
                </tr>
                <tr>
                    <td><b>Packing Factor:</b></td>
                    <td>{packing:.2f}</td>
                </tr>
            </table>

            {comp_html}

            {apps_html}

            <div style='background: rgba(102,126,234,0.15); padding: 12px; border-radius: 8px;
                border-left: 4px solid {category_color}; margin-top: 15px;'>
                <p style='margin: 0;'><b>Category:</b> {category}</p>
                <p style='margin: 0;'><b>Sub-category:</b> {subcategory}</p>
            </div>
        """
        self.info_text.setHtml(html)

    def start_add(self, template_data=None):
        """Start add mode with inline editor"""
        self._editor = InlineDataEditor(DataCategory.ALLOYS, template_data)
        self._editor.saved.connect(self._on_editor_saved)
        self._editor.cancelled.connect(self._on_editor_cancelled)
        self.stack.addWidget(self._editor)
        self.stack.setCurrentWidget(self._editor)

    def start_edit(self, data):
        """Start edit mode with inline editor"""
        self._editor = InlineDataEditor(DataCategory.ALLOYS, data, edit_mode=True)
        self._editor.saved.connect(self._on_editor_saved)
        self._editor.cancelled.connect(self._on_editor_cancelled)
        self.stack.addWidget(self._editor)
        self.stack.setCurrentWidget(self._editor)

    def _on_editor_saved(self, data):
        """Handle editor save"""
        self.stack.setCurrentIndex(0)
        if self._editor:
            self.stack.removeWidget(self._editor)
            self._editor.deleteLater()
            self._editor = None
        self.data_saved.emit(data)

    def _on_editor_cancelled(self):
        """Handle editor cancel"""
        self.stack.setCurrentIndex(0)
        if self._editor:
            self.stack.removeWidget(self._editor)
            self._editor.deleteLater()
            self._editor = None
        self.edit_cancelled.emit()
