"""
Element Info Panel
Displays detailed information about selected elements.
Supports inline editing mode for Add/Edit operations.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit,
                                QStackedWidget, QFrame, QHBoxLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QRadialGradient, QBrush, QPen

from periodica.data.data_manager import DataCategory


class ElementVisualizationWidget(QFrame):
    """Widget to display element visualization (electron shells)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.element = None
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 45, 200);
                border: 2px solid #4fc3f7;
                border-radius: 12px;
            }
        """)

    def set_element(self, elem):
        """Set element to display"""
        self.element = elem
        self.update()

    def paintEvent(self, event):
        """Paint the element visualization"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        max_radius = min(self.width(), self.height()) * 0.4

        if not self.element:
            painter.setPen(QPen(QColor(150, 150, 150)))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select an element")
            painter.end()
            return

        # Draw nucleus
        nucleus_radius = 20
        gradient = QRadialGradient(cx - 5, cy - 5, nucleus_radius * 1.5)

        # Get element color or use default
        color_str = self.element.get('color', '#4fc3f7')
        if isinstance(color_str, str) and color_str.startswith('#'):
            base_color = QColor(color_str)
        else:
            base_color = QColor('#4fc3f7')

        gradient.setColorAt(0, base_color.lighter(150))
        gradient.setColorAt(0.5, base_color)
        gradient.setColorAt(1, base_color.darker(150))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(base_color.darker(120), 2))
        painter.drawEllipse(int(cx - nucleus_radius), int(cy - nucleus_radius),
                           nucleus_radius * 2, nucleus_radius * 2)

        # Draw element symbol
        symbol = self.element.get('symbol', '?')
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        painter.drawText(int(cx - 10), int(cy + 5), symbol)

        # Draw electron shells
        shells = self.element.get('shells', [])
        shell_radii = [40, 60, 80, 100, 120, 140, 160]

        for i, electrons in enumerate(shells[:len(shell_radii)]):
            radius = shell_radii[i] if i < len(shell_radii) else shell_radii[-1] + 20 * (i - len(shell_radii) + 1)
            if radius > max_radius:
                radius = max_radius - 5

            # Draw shell orbit
            painter.setPen(QPen(QColor(100, 150, 200, 100), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

            # Draw electrons
            import math
            for j in range(electrons):
                angle = 2 * math.pi * j / electrons
                ex = cx + radius * math.cos(angle)
                ey = cy + radius * math.sin(angle)

                # Electron glow
                elec_gradient = QRadialGradient(ex, ey, 8)
                elec_gradient.setColorAt(0, QColor(100, 200, 255))
                elec_gradient.setColorAt(1, QColor(100, 200, 255, 0))
                painter.setBrush(QBrush(elec_gradient))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(int(ex - 8), int(ey - 8), 16, 16)

                # Electron core
                painter.setBrush(QBrush(QColor(150, 220, 255)))
                painter.drawEllipse(int(ex - 4), int(ey - 4), 8, 8)

        painter.end()


class ElementInfoPanel(QWidget):
    """Panel displaying detailed element information with inline editing support"""

    # Signals for data management
    data_saved = Signal(dict)
    edit_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.element = None
        self._editor = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for switching between display and edit modes
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Display mode widget
        self.display_widget = QWidget()
        display_layout = QVBoxLayout(self.display_widget)
        display_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Element Analysis")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        display_layout.addWidget(title)

        # Element visualization
        self.viz_widget = ElementVisualizationWidget()
        display_layout.addWidget(self.viz_widget)

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

        self.stack.addWidget(self.display_widget)
        self.show_default()

    def start_add(self, template_data=None):
        """Start add mode with inline editor"""
        from periodica_app.ui.inline_editor import InlineDataEditor

        if self._editor is None:
            self._editor = InlineDataEditor()
            self._editor.data_saved.connect(self._on_editor_saved)
            self._editor.edit_cancelled.connect(self._on_editor_cancelled)
            self.stack.addWidget(self._editor)

        self._editor.start_add(DataCategory.ELEMENTS, template_data)
        self.stack.setCurrentWidget(self._editor)

    def start_edit(self, data):
        """Start edit mode with inline editor"""
        from periodica_app.ui.inline_editor import InlineDataEditor

        if self._editor is None:
            self._editor = InlineDataEditor()
            self._editor.data_saved.connect(self._on_editor_saved)
            self._editor.edit_cancelled.connect(self._on_editor_cancelled)
            self.stack.addWidget(self._editor)

        self._editor.start_edit(DataCategory.ELEMENTS, data)
        self.stack.setCurrentWidget(self._editor)

    def _on_editor_saved(self, data):
        """Handle save from editor"""
        self.stack.setCurrentWidget(self.display_widget)
        self.data_saved.emit(data)

    def _on_editor_cancelled(self):
        """Handle cancel from editor"""
        self.stack.setCurrentWidget(self.display_widget)
        self.edit_cancelled.emit()

    def show_default(self):
        """Show default message"""
        self.viz_widget.set_element(None)
        self.info_text.setHtml("""
            <h3 style='color: #4fc3f7;'>Click any element to view:</h3>
            <ul>
                <li><b>Atomic Structure</b> (electron shells)</li>
                <li><b>Physical Properties</b></li>
                <li><b>Chemical Properties</b></li>
                <li><b>Classification</b></li>
            </ul>
            <p style='background: rgba(100,200,255,0.15); padding: 10px; border-radius: 5px;'>
            <b>Tip:</b> Use the control panel to filter elements by block,
            category, or physical properties.
            </p>
        """)

    def update_element(self, elem):
        """Update panel with element data"""
        if not elem:
            self.show_default()
            return

        self.element = elem
        self.viz_widget.set_element(elem)

        # Build HTML content
        name = elem.get('name', 'Unknown')
        symbol = elem.get('symbol', '?')
        z = elem.get('atomic_number', 0)
        mass = elem.get('atomic_mass', 0)
        category = elem.get('category', 'Unknown')
        block = elem.get('block', '?')
        period = elem.get('period', 0)
        group = elem.get('group', 0)

        # Electronic properties
        config = elem.get('electron_configuration', 'Unknown')
        shells = elem.get('shells', [])
        electroneg = elem.get('electronegativity', 0)
        ie = elem.get('ionization_energy', 0)
        ea = elem.get('electron_affinity', 0)

        # Physical properties
        density = elem.get('density', 0)
        melting = elem.get('melting_point', 0)
        boiling = elem.get('boiling_point', 0)
        radius = elem.get('atomic_radius', 0)
        phase = elem.get('phase', 'Unknown')

        # Get color based on category
        category_colors = {
            'alkali metal': '#ff6666',
            'alkaline earth metal': '#ffd966',
            'transition metal': '#ffcc99',
            'post-transition metal': '#99cc99',
            'metalloid': '#66cccc',
            'nonmetal': '#99ff99',
            'halogen': '#ffff99',
            'noble gas': '#99ccff',
            'lanthanide': '#ffb3ff',
            'actinide': '#ff99cc',
        }
        cat_color = category_colors.get(category.lower(), '#cccccc')

        shells_str = " → ".join(str(s) for s in shells) if shells else "N/A"

        html = f"""
            <h2 style='color: #4fc3f7;'>{name}</h2>
            <div style='font-size: 24px; font-weight: bold; color: white;'>{symbol}</div>
            <hr style='border-color: #4fc3f7;'>

            <h3 style='color: #4fc3f7;'>Classification:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Atomic Number:</b></td>
                    <td><b style='color: #00ff88;'>{z}</b></td>
                </tr>
                <tr>
                    <td><b>Category:</b></td>
                    <td><span style='background: {cat_color}; padding: 2px 8px;
                        border-radius: 4px; color: black;'>{category}</span></td>
                </tr>
                <tr>
                    <td><b>Block:</b></td>
                    <td><b style='color: #ff8800;'>{block}</b>-block</td>
                </tr>
                <tr>
                    <td><b>Period:</b></td>
                    <td>{period}</td>
                </tr>
                <tr>
                    <td><b>Group:</b></td>
                    <td>{group if group else 'N/A'}</td>
                </tr>
            </table>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Electronic Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Configuration:</b></td>
                    <td style='font-family: monospace;'>{config}</td>
                </tr>
                <tr>
                    <td><b>Shells:</b></td>
                    <td>{shells_str}</td>
                </tr>
                <tr>
                    <td><b>Electronegativity:</b></td>
                    <td>{electroneg:.2f}</td>
                </tr>
                <tr>
                    <td><b>Ionization Energy:</b></td>
                    <td>{ie:.2f} eV</td>
                </tr>
            </table>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Physical Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Atomic Mass:</b></td>
                    <td><b style='color: #00ff88;'>{mass:.4f}</b> u</td>
                </tr>
                <tr>
                    <td><b>Density:</b></td>
                    <td>{density:.3f} g/cm³</td>
                </tr>
                <tr>
                    <td><b>Melting Point:</b></td>
                    <td>{melting:.1f} K</td>
                </tr>
                <tr>
                    <td><b>Boiling Point:</b></td>
                    <td>{boiling:.1f} K</td>
                </tr>
                <tr>
                    <td><b>Atomic Radius:</b></td>
                    <td>{radius} pm</td>
                </tr>
                <tr>
                    <td><b>Phase at STP:</b></td>
                    <td>{phase}</td>
                </tr>
            </table>
        """
        self.info_text.setHtml(html)
