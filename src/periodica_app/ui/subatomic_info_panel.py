"""
Subatomic Info Panel - Particle Information Display
Shows detailed properties and quark composition for selected particles
"""

import math
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame, QHBoxLayout, QStackedWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen

from periodica.core.subatomic_enums import QuarkType, PARTICLE_COLORS
from periodica.data.data_manager import DataCategory
from periodica.data.layout_config_loader import get_subatomic_config
from periodica_app.ui.inline_editor import InlineDataEditor


class QuarkDiagram(QWidget):
    """Widget to display quark composition visually using data-driven configuration"""

    def __init__(self):
        super().__init__()
        self.particle = None
        self._load_config()

    def _load_config(self):
        """Load configuration from layout_config.json"""
        # Get quark diagram configuration with sensible defaults
        self.quark_size = get_subatomic_config('quark_diagram', 'quark_size', default=35)
        self.quark_size_min = get_subatomic_config('quark_diagram', 'quark_size_min', default=20)
        self.quark_size_max = get_subatomic_config('quark_diagram', 'quark_size_max', default=50)
        self.baryon_radius = get_subatomic_config('quark_diagram', 'baryon_radius', default=30)
        self.meson_spacing = get_subatomic_config('quark_diagram', 'meson_spacing', default=50)
        self.glow_extra_size = get_subatomic_config('quark_diagram', 'glow_extra_size', default=10)
        self.glow_alpha = get_subatomic_config('quark_diagram', 'glow_alpha', default=50)
        self.border_width = get_subatomic_config('quark_diagram', 'border_width', default=2)
        self.label_font_size = get_subatomic_config('quark_diagram', 'label_font_size', default=12)
        self.content_font_size = get_subatomic_config('quark_diagram', 'content_font_size', default=9)

        # Background and text colors
        bg = get_subatomic_config('quark_diagram', 'background_color', default=[25, 25, 45])
        self.background_color = QColor(bg[0], bg[1], bg[2])
        default_text = get_subatomic_config('quark_diagram', 'default_text_color', default=[100, 100, 100])
        self.default_text_color = QColor(default_text[0], default_text[1], default_text[2])
        label_text = get_subatomic_config('quark_diagram', 'label_text_color', default=[150, 150, 150])
        self.label_text_color = QColor(label_text[0], label_text[1], label_text[2])

        # Arrangement configurations for different quark counts
        self.arrangements = get_subatomic_config('quark_diagram', 'arrangements', default={})

        # Set widget height constraints based on config
        min_height = 100  # Default minimum
        max_height = 120  # Default maximum
        self.setMinimumHeight(min_height)
        self.setMaximumHeight(max_height)

    def set_particle(self, particle):
        """Set the particle to display"""
        self.particle = particle
        self.update()

    def _get_quarks_from_composition(self):
        """Extract quark list from particle's Composition field or _parsed_quarks"""
        if not self.particle:
            return []

        # First try _parsed_quarks (pre-processed data)
        quarks = self.particle.get('_parsed_quarks', [])
        if quarks:
            return quarks

        # Fall back to parsing Composition field from JSON
        composition = self.particle.get('Composition', [])
        if not composition:
            return []

        quarks = []
        for comp in composition:
            constituent = comp.get('Constituent', '')
            count = comp.get('Count', 1)
            symbol = comp.get('Symbol', '')
            is_anti = comp.get('IsAnti', False) or 'Anti' in constituent

            # Determine quark type from constituent name or symbol
            quark_type = symbol.replace('-bar', '') if symbol else constituent.split()[0].lower()[0]

            for _ in range(count):
                quarks.append({
                    'type': quark_type,
                    'is_anti': is_anti,
                    'constituent': constituent
                })

        return quarks

    def _calculate_quark_positions(self, quarks, center_x, center_y):
        """Calculate positions for quarks dynamically based on count and configuration"""
        positions = []
        num_quarks = len(quarks)

        if num_quarks == 0:
            return positions

        # Get arrangement config for this quark count
        arrangement = self.arrangements.get(str(num_quarks), {})
        arr_type = arrangement.get('type', 'linear' if num_quarks <= 2 else 'polygon')

        # Calculate dynamic quark size based on available space and count
        available_width = self.width() - 40  # Leave margins
        available_height = self.height() - 30  # Leave space for label
        max_size_by_space = min(available_width / max(num_quarks, 2), available_height) * 0.6
        quark_size = max(self.quark_size_min, min(self.quark_size, max_size_by_space, self.quark_size_max))

        if arr_type == 'linear' or num_quarks == 2:
            # Linear arrangement (mesons)
            spacing_ratio = arrangement.get('spacing_ratio', 1.4)
            spacing = self.meson_spacing * spacing_ratio
            for i, quark in enumerate(quarks):
                qx = center_x + (i - (num_quarks - 1) / 2) * spacing - quark_size / 2
                qy = center_y - quark_size / 2
                positions.append((qx, qy, quark_size, quark))

        elif arr_type == 'triangle' or num_quarks == 3:
            # Triangle arrangement (baryons)
            radius_ratio = arrangement.get('radius_ratio', 1.0)
            top_offset = arrangement.get('top_offset', -1.0)
            bottom_offset = arrangement.get('bottom_offset', 0.6)
            radius = self.baryon_radius * radius_ratio

            # Top quark
            positions.append((
                center_x - quark_size / 2,
                center_y + radius * top_offset - quark_size / 2,
                quark_size, quarks[0]
            ))
            # Bottom left
            if len(quarks) > 1:
                positions.append((
                    center_x - radius * 1.2 - quark_size / 2,
                    center_y + radius * bottom_offset - quark_size / 2,
                    quark_size, quarks[1]
                ))
            # Bottom right
            if len(quarks) > 2:
                positions.append((
                    center_x + radius * 1.2 - quark_size / 2,
                    center_y + radius * bottom_offset - quark_size / 2,
                    quark_size, quarks[2]
                ))

        else:
            # Generic polygon arrangement for 4+ quarks
            radius_ratio = arrangement.get('radius_ratio', 1.2)
            radius = self.baryon_radius * radius_ratio
            for i, quark in enumerate(quarks):
                angle = (i * 360 / num_quarks - 90) * math.pi / 180
                qx = center_x + radius * math.cos(angle) - quark_size / 2
                qy = center_y + radius * math.sin(angle) - quark_size / 2
                positions.append((qx, qy, quark_size, quark))

        return positions

    def paintEvent(self, event):
        """Paint the quark diagram using data-driven configuration"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background from config
        painter.fillRect(self.rect(), self.background_color)

        if not self.particle:
            painter.setPen(QPen(self.default_text_color))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select a particle")
            painter.end()
            return

        # Get quarks from particle's Composition field or _parsed_quarks
        quarks = self._get_quarks_from_composition()
        if not quarks:
            painter.setPen(QPen(self.default_text_color))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No quark data")
            painter.end()
            return

        # Calculate center position
        center_x = self.width() / 2
        center_y = self.height() / 2

        # Calculate dynamic positions based on composition and configuration
        positions = self._calculate_quark_positions(quarks, center_x, center_y)

        # Draw quarks at calculated positions
        for qx, qy, quark_size, quark in positions:
            self._draw_quark(painter, qx, qy, quark_size, quark)

        # Draw particle name/content below using config font size
        painter.setPen(QPen(self.label_text_color))
        font = QFont("Arial", self.content_font_size)
        painter.setFont(font)
        quark_content = self.particle.get('QuarkContent', '')
        painter.drawText(0, self.height() - 15, self.width(), 15,
                        Qt.AlignmentFlag.AlignCenter, quark_content)

        painter.end()

    def _draw_quark(self, painter, x, y, size, quark):
        """Draw a single quark using configuration values"""
        quark_type = quark.get('type', 'u')
        is_anti = quark.get('is_anti', False)

        # Get color from quark type
        if is_anti:
            quark_type_full = f"{quark_type}-bar"
        else:
            quark_type_full = quark_type

        color_tuple = QuarkType.get_color(QuarkType.from_string(quark_type_full))
        color = QColor(color_tuple[0], color_tuple[1], color_tuple[2])

        # Draw glow with configurable size and alpha
        glow = QColor(color)
        glow.setAlpha(self.glow_alpha)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        glow_padding = self.glow_extra_size // 2
        painter.drawEllipse(int(x - glow_padding), int(y - glow_padding),
                           int(size + self.glow_extra_size), int(size + self.glow_extra_size))

        # Draw quark circle with configurable border width
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(255, 255, 255), self.border_width))
        painter.drawEllipse(int(x), int(y), int(size), int(size))

        # Draw label with configurable font size
        painter.setPen(QPen(QColor(0, 0, 0)))
        font = QFont("Arial", self.label_font_size, QFont.Weight.Bold)
        painter.setFont(font)
        label = quark_type.upper()
        if is_anti:
            # Draw label with overline for antiquarks
            painter.drawText(int(x), int(y), int(size), int(size),
                           Qt.AlignmentFlag.AlignCenter, label)
            # Draw overline manually
            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(label)
            line_y = y + size / 2 - 8
            line_x = x + (size - text_width) / 2
            painter.drawLine(int(line_x), int(line_y), int(line_x + text_width), int(line_y))
        else:
            painter.drawText(int(x), int(y), int(size), int(size),
                           Qt.AlignmentFlag.AlignCenter, label)


class SubatomicInfoPanel(QWidget):
    """Panel displaying detailed particle information"""

    data_saved = Signal(dict)
    edit_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.particle = None
        self._editor = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create stacked widget for display/edit modes
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Display widget (existing content)
        display_widget = QWidget()
        display_layout = QVBoxLayout(display_widget)
        display_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Particle Analysis")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        display_layout.addWidget(title)

        # Quark diagram
        self.quark_diagram = QuarkDiagram()
        display_layout.addWidget(self.quark_diagram)

        # Info text
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background: rgba(25, 25, 45, 200);
                color: white;
                border: 2px solid #4fc3f7;
                border-radius: 12px;
                padding: 15px;
                font-size: 13px;
            }
        """)
        display_layout.addWidget(self.info_text)

        self.stack.addWidget(display_widget)

        self.show_default()

    def show_default(self):
        """Show default message when no particle is selected"""
        self.quark_diagram.set_particle(None)
        self.info_text.setHtml("""
            <h3 style='color: #4fc3f7;'>Click any particle to view:</h3>
            <ul>
                <li><b>Quark Composition</b> - Visual diagram</li>
                <li><b>Mass</b> (MeV/c^2 and GeV/c^2)</li>
                <li><b>Charge</b> (in elementary charge units)</li>
                <li><b>Spin</b> (in units of h-bar)</li>
                <li><b>Half-Life</b> and decay products</li>
                <li><b>Classification</b> - Baryon/Meson type</li>
            </ul>
            <p style='background: rgba(255,200,0,0.2); padding: 10px; border-radius: 5px;'>
            <b>Particle Physics Note:</b> Baryons contain 3 quarks, while mesons contain
            a quark-antiquark pair. Color charge ensures quarks are always confined.
            </p>
        """)

    def update_particle(self, particle):
        """Update panel with particle data"""
        if not particle:
            self.show_default()
            return

        self.particle = particle
        self.quark_diagram.set_particle(particle)

        # Build info HTML
        name = particle.get('Name', 'Unknown')
        symbol = particle.get('Symbol', name)
        charge = particle.get('Charge_e', 0)
        charge_str = f"+{charge}" if charge > 0 else str(charge)
        mass = particle.get('Mass_MeVc2', 0)
        mass_gev = mass / 1000
        spin = particle.get('Spin_hbar', 0)
        stability = particle.get('Stability', 'Unknown')
        half_life = particle.get('HalfLife_s')

        # Get category color
        category = particle.get('_category', 'baryon')
        color = PARTICLE_COLORS.get(category, (102, 126, 234))
        color_hex = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"

        # Classification
        classification = particle.get('Classification', [])
        class_str = ", ".join(classification[:4])

        # Quark content
        quark_content = particle.get('QuarkContent', 'Unknown')

        # Decay products
        decay_products = particle.get('DecayProducts', [])
        decay_str = ", ".join(decay_products[:5]) if decay_products else "Stable or unknown"

        # Decay modes with branching ratios
        decay_modes = particle.get('DecayModes', [])
        decay_modes_html = ""
        if decay_modes:
            decay_modes_html = "<h3 style='color: #4fc3f7; margin-top: 15px;'>Decay Modes:</h3><table style='width: 100%; color: white;'>"
            for mode in decay_modes[:5]:
                products = " + ".join(mode.get('Products', []))
                ratio = mode.get('BranchingRatio', 0) * 100
                decay_modes_html += f"<tr><td>{products}</td><td style='color: #00ff88;'>{ratio:.1f}%</td></tr>"
            decay_modes_html += "</table>"

        # Half-life formatting
        if half_life:
            if half_life >= 1:
                half_life_str = f"{half_life:.2f} s"
            elif half_life >= 1e-6:
                half_life_str = f"{half_life * 1e6:.2f} us"
            elif half_life >= 1e-9:
                half_life_str = f"{half_life * 1e9:.2f} ns"
            elif half_life >= 1e-12:
                half_life_str = f"{half_life * 1e12:.2f} ps"
            elif half_life >= 1e-15:
                half_life_str = f"{half_life * 1e15:.2f} fs"
            else:
                half_life_str = f"{half_life:.2e} s"
        else:
            half_life_str = "Stable" if stability == "Stable" else "Unknown"

        # Antiparticle info
        antiparticle = particle.get('Antiparticle', {})
        anti_name = antiparticle.get('Name', 'Unknown')

        # Additional properties
        isospin = particle.get('Isospin_I')
        strangeness = particle.get('Strangeness', 0)
        baryon_num = particle.get('BaryonNumber_B', 0)
        parity = particle.get('Parity_P', 0)
        parity_str = "+" if parity == 1 else "-" if parity == -1 else "?"

        html = f"""
            <h2 style='color: {color_hex};'>{symbol}</h2>
            <div style='color: #aaa; font-size: 11px; margin-top: -5px;'>
                {name} | {class_str}
            </div>
            <hr style='border-color: #4fc3f7;'>

            <h3 style='color: #4fc3f7;'>Quark Composition:</h3>
            <p style='font-size: 16px; color: white;'><b>{quark_content}</b></p>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Charge:</b></td>
                    <td><b style='color: #00ff88;'>{charge_str} e</b></td>
                </tr>
                <tr>
                    <td><b>Mass:</b></td>
                    <td><b style='color: #ff8800;'>{mass:.2f} MeV/c^2</b><br>
                    <span style='color: #aaa;'>({mass_gev:.4f} GeV/c^2)</span></td>
                </tr>
                <tr>
                    <td><b>Spin:</b></td>
                    <td><b style='color: #ff8800;'>{spin}</b> h-bar</td>
                </tr>
                <tr>
                    <td><b>Parity:</b></td>
                    <td><b>{parity_str}</b></td>
                </tr>
                <tr>
                    <td><b>Baryon Number:</b></td>
                    <td><b>{baryon_num}</b></td>
                </tr>
        """

        if strangeness != 0:
            html += f"""
                <tr>
                    <td><b>Strangeness:</b></td>
                    <td><b style='color: #00ff88;'>{strangeness}</b></td>
                </tr>
            """

        if isospin is not None:
            html += f"""
                <tr>
                    <td><b>Isospin:</b></td>
                    <td><b>{isospin}</b></td>
                </tr>
            """

        html += f"""
            </table>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Stability:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Status:</b></td>
                    <td><b style='color: {"#00ff88" if stability == "Stable" else "#ff8800"};'>{stability}</b></td>
                </tr>
                <tr>
                    <td><b>Half-Life:</b></td>
                    <td><b>{half_life_str}</b></td>
                </tr>
                <tr>
                    <td><b>Decays to:</b></td>
                    <td>{decay_str}</td>
                </tr>
            </table>

            {decay_modes_html}

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Antiparticle:</h3>
            <p>{anti_name}</p>

            <div style='background: rgba(100,200,255,0.15); padding: 12px; border-radius: 8px;
            border-left: 4px solid #4fc3f7; margin-top: 15px;'>
                <p style='margin: 0;'><b>Physics Note:</b> {"This baryon contains 3 quarks bound by the strong force via gluon exchange." if particle.get('_is_baryon') else "This meson is a quark-antiquark bound state. Its properties arise from the combination of quark flavors."}</p>
            </div>
        """

        self.info_text.setHtml(html)

    def start_add(self, template_data=None):
        """Start add mode with inline editor"""
        self._editor = InlineDataEditor(DataCategory.SUBATOMIC, template_data)
        self._editor.saved.connect(self._on_editor_saved)
        self._editor.cancelled.connect(self._on_editor_cancelled)
        self.stack.addWidget(self._editor)
        self.stack.setCurrentWidget(self._editor)

    def start_edit(self, data):
        """Start edit mode with inline editor"""
        self._editor = InlineDataEditor(DataCategory.SUBATOMIC, data, edit_mode=True)
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
