"""
Amino Acid Info Panel
Displays detailed information about selected amino acids.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame,
                                QStackedWidget)
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen, QRadialGradient

from periodica.core.amino_acid_enums import (AminoAcidCategory, AminoAcidPolarity,
                                    ChargeState, SecondaryStructure)


class AminoAcidStructureWidget(QFrame):
    """Widget to display amino acid structure diagram"""

    # Backbone atom positions (relative)
    BACKBONE_POSITIONS = {
        'N': (0.2, 0.5),    # Amino group
        'CA': (0.4, 0.5),   # Alpha carbon
        'C': (0.6, 0.5),    # Carbonyl carbon
        'O': (0.7, 0.35),   # Carbonyl oxygen
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.amino_acid = None
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 45, 200);
                border: 2px solid #66bb6a;
                border-radius: 12px;
            }
        """)

    def set_amino_acid(self, aa):
        """Set amino acid to display"""
        self.amino_acid = aa
        self.update()

    def paintEvent(self, event):
        """Paint the amino acid structure"""
        super().paintEvent(event)

        if not self.amino_acid:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Draw backbone
        self._draw_backbone(painter, w, h)

        # Draw side chain indicator
        self._draw_sidechain(painter, w, h)

        # Draw label
        symbol = self.amino_acid.get('symbol', '?')
        name = self.amino_acid.get('name', 'Unknown')

        painter.setPen(QPen(QColor(102, 187, 106)))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(10, 20, f"{name} ({symbol})")

        painter.end()

    def _draw_backbone(self, painter, w, h):
        """Draw the amino acid backbone"""
        # Atom colors
        atom_colors = {
            'N': QColor("#3050F8"),   # Blue
            'CA': QColor("#909090"),  # Grey
            'C': QColor("#909090"),   # Grey
            'O': QColor("#FF0D0D"),   # Red
        }

        # Draw bonds first
        bond_pen = QPen(QColor(180, 180, 180), 3)
        painter.setPen(bond_pen)

        # N - CA bond
        n_pos = QPointF(w * 0.2, h * 0.5)
        ca_pos = QPointF(w * 0.4, h * 0.5)
        c_pos = QPointF(w * 0.6, h * 0.5)
        o_pos = QPointF(w * 0.7, h * 0.35)

        painter.drawLine(n_pos, ca_pos)
        painter.drawLine(ca_pos, c_pos)
        painter.drawLine(c_pos, o_pos)

        # Draw atoms
        for atom, (rx, ry) in self.BACKBONE_POSITIONS.items():
            x = w * rx
            y = h * ry
            r = 15

            color = atom_colors.get(atom, QColor("#909090"))

            # Glow
            glow = QRadialGradient(x, y, r * 1.5)
            glow_color = QColor(color)
            glow_color.setAlpha(60)
            glow.setColorAt(0, glow_color)
            glow_color.setAlpha(0)
            glow.setColorAt(1, glow_color)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), r * 1.5, r * 1.5)

            # Atom
            gradient = QRadialGradient(x - r * 0.3, y - r * 0.3, r * 1.5)
            gradient.setColorAt(0, color.lighter(140))
            gradient.setColorAt(0.5, color)
            gradient.setColorAt(1, color.darker(130))
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(color.darker(150), 1))
            painter.drawEllipse(QPointF(x, y), r, r)

            # Label
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(QPointF(x - 5, y + 4), atom)

    def _draw_sidechain(self, painter, w, h):
        """Draw the side chain indicator"""
        if not self.amino_acid:
            return

        category = self.amino_acid.get('category', 'special')
        color = AminoAcidCategory.get_color(category)

        # Side chain position (branching from CA)
        ca_x = w * 0.4
        ca_y = h * 0.5
        r_x = w * 0.4
        r_y = h * 0.75

        # Draw bond to side chain
        painter.setPen(QPen(QColor(180, 180, 180), 3))
        painter.drawLine(QPointF(ca_x, ca_y), QPointF(r_x, r_y))

        # Draw R group (side chain)
        r = 20
        side_color = QColor(color)

        gradient = QRadialGradient(r_x - r * 0.3, r_y - r * 0.3, r * 1.5)
        gradient.setColorAt(0, side_color.lighter(140))
        gradient.setColorAt(0.5, side_color)
        gradient.setColorAt(1, side_color.darker(130))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(side_color.darker(150), 1))
        painter.drawEllipse(QPointF(r_x, r_y), r, r)

        # R label
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(QPointF(r_x - 5, r_y + 4), "R")


class AminoAcidInfoPanel(QWidget):
    """Panel displaying detailed amino acid information"""

    data_saved = Signal(dict)
    edit_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.amino_acid = None
        self._editor = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Display mode widget
        self.display_widget = QWidget()
        display_layout = QVBoxLayout(self.display_widget)
        display_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Amino Acid Analysis")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #66bb6a;")
        display_layout.addWidget(title)

        # Structure widget
        self.structure_widget = AminoAcidStructureWidget()
        display_layout.addWidget(self.structure_widget)

        # Info text
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background: rgba(25, 25, 45, 200);
                color: white;
                border: 2px solid #66bb6a;
                border-radius: 12px;
                padding: 15px;
                font-size: 13px;
            }
        """)
        display_layout.addWidget(self.info_text)

        self.stack.addWidget(self.display_widget)
        self.show_default()

    def show_default(self):
        """Show default message"""
        self.structure_widget.set_amino_acid(None)
        self.info_text.setHtml("""
            <h3 style='color: #66bb6a;'>Click any amino acid to view:</h3>
            <ul>
                <li><b>Structure Diagram</b></li>
                <li><b>pKa Values</b></li>
                <li><b>Charge at Current pH</b></li>
                <li><b>Secondary Structure Propensities</b></li>
                <li><b>Physical Properties</b></li>
            </ul>
            <p style='background: rgba(100,200,100,0.15); padding: 10px; border-radius: 5px;'>
            <b>Tip:</b> Adjust the pH slider to see how amino acid charges change.
            The charge calculation uses the Henderson-Hasselbalch equation.
            </p>
        """)

    def update_amino_acid(self, aa, pH=7.0):
        """Update panel with amino acid data"""
        if not aa:
            self.show_default()
            return

        self.amino_acid = aa
        self.structure_widget.set_amino_acid(aa)

        # Build HTML content
        name = aa.get('name', 'Unknown')
        symbol = aa.get('symbol', '?')
        three_letter = aa.get('three_letter_code', '???')
        formula = aa.get('molecular_formula', '')
        mass = aa.get('molecular_mass', 0)
        pKa_carboxyl = aa.get('pKa_carboxyl', 0)
        pKa_amino = aa.get('pKa_amino', 0)
        pKa_sidechain = aa.get('pKa_sidechain')
        pI = aa.get('isoelectric_point', 0)
        hydropathy = aa.get('hydropathy_index', 0)
        category = aa.get('category', 'special')
        polarity = aa.get('polarity', 'nonpolar')
        charge_pH7 = aa.get('charge_pH7', 0)
        helix_prop = aa.get('helix_propensity', 1.0)
        sheet_prop = aa.get('sheet_propensity', 1.0)
        turn_prop = aa.get('turn_propensity', 1.0)
        codons = aa.get('codons', [])
        description = aa.get('description', '')

        # Calculate current charge using Henderson-Hasselbalch
        from periodica.utils.predictors.biological.amino_acid_predictor import AminoAcidPredictor
        predictor = AminoAcidPredictor()
        is_acidic = symbol.upper() in {'D', 'E', 'C', 'Y'}
        current_charge = predictor.calculate_charge_at_pH(
            pH, pKa_carboxyl, pKa_amino, pKa_sidechain, is_acidic
        )

        # Get colors
        category_color = AminoAcidCategory.get_color(category)
        polarity_color = AminoAcidPolarity.get_color(polarity)
        charge_state = ChargeState.from_charge(current_charge)
        charge_color = ChargeState.get_color(charge_state)

        # Hydropathy color (blue for hydrophilic, yellow for hydrophobic)
        if hydropathy > 0:
            hydropathy_color = f"rgb(255, {int(255 - hydropathy * 40)}, 0)"
        else:
            hydropathy_color = f"rgb(0, {int(200 + hydropathy * 40)}, 255)"

        # Structure propensity colors
        helix_color = "#FF4081" if helix_prop > 1.0 else "#9E9E9E"
        sheet_color = "#448AFF" if sheet_prop > 1.0 else "#9E9E9E"
        turn_color = "#69F0AE" if turn_prop > 1.0 else "#9E9E9E"

        # Codons text
        codons_text = ", ".join(codons) if codons else "N/A"

        # pKa sidechain display
        pKa_sidechain_display = f"{pKa_sidechain:.2f}" if pKa_sidechain else "N/A"

        html = f"""
            <h2 style='color: #66bb6a;'>{name}</h2>
            <div style='font-size: 18px; font-weight: bold; color: white;'>
                {symbol} ({three_letter})
            </div>
            <div style='color: #aaa; font-size: 12px;'>{formula}</div>
            <hr style='border-color: #66bb6a;'>

            <h3 style='color: #66bb6a;'>Chemical Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Molecular Mass:</b></td>
                    <td><b style='color: #00ff88;'>{mass:.3f}</b> Da</td>
                </tr>
                <tr>
                    <td><b>pKa Carboxyl:</b></td>
                    <td>{pKa_carboxyl:.2f}</td>
                </tr>
                <tr>
                    <td><b>pKa Amino:</b></td>
                    <td>{pKa_amino:.2f}</td>
                </tr>
                <tr>
                    <td><b>pKa Side Chain:</b></td>
                    <td>{pKa_sidechain_display}</td>
                </tr>
                <tr>
                    <td><b>Isoelectric Point:</b></td>
                    <td><b style='color: #42a5f5;'>{pI:.2f}</b></td>
                </tr>
            </table>

            <h3 style='color: #66bb6a; margin-top: 15px;'>Charge at pH {pH:.1f}:</h3>
            <div style='background: {charge_color}; padding: 10px; border-radius: 8px;
                text-align: center; font-size: 20px; font-weight: bold;'>
                {current_charge:+.3f}
            </div>

            <h3 style='color: #66bb6a; margin-top: 15px;'>Physical Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Category:</b></td>
                    <td><span style='background: {category_color}; padding: 2px 8px;
                        border-radius: 4px; color: black;'>
                        {AminoAcidCategory.get_display_name(category)}</span></td>
                </tr>
                <tr>
                    <td><b>Polarity:</b></td>
                    <td><span style='background: {polarity_color}; padding: 2px 8px;
                        border-radius: 4px;'>{polarity.capitalize()}</span></td>
                </tr>
                <tr>
                    <td><b>Hydropathy:</b></td>
                    <td><span style='background: {hydropathy_color}; padding: 2px 8px;
                        border-radius: 4px; color: black;'>{hydropathy:+.1f}</span></td>
                </tr>
            </table>

            <h3 style='color: #66bb6a; margin-top: 15px;'>Structure Propensities:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Helix:</b></td>
                    <td><span style='background: {helix_color}; padding: 2px 8px;
                        border-radius: 4px;'>{helix_prop:.2f}</span></td>
                </tr>
                <tr>
                    <td><b>Sheet:</b></td>
                    <td><span style='background: {sheet_color}; padding: 2px 8px;
                        border-radius: 4px;'>{sheet_prop:.2f}</span></td>
                </tr>
                <tr>
                    <td><b>Turn:</b></td>
                    <td><span style='background: {turn_color}; padding: 2px 8px;
                        border-radius: 4px;'>{turn_prop:.2f}</span></td>
                </tr>
            </table>

            <h3 style='color: #66bb6a; margin-top: 15px;'>Genetic:</h3>
            <div style='color: white;'>
                <b>Codons ({len(codons)}):</b> {codons_text}
            </div>

            <div style='background: rgba(100,200,100,0.15); padding: 12px; border-radius: 8px;
                margin-top: 15px;'>
                <p style='margin: 0; font-style: italic;'>{description}</p>
            </div>
        """
        self.info_text.setHtml(html)

    def start_add(self, template_data=None):
        """Start add mode with inline editor"""
        from periodica_app.ui.inline_editor import InlineDataEditor
        from periodica.data.data_manager import DataCategory

        if self._editor is None:
            self._editor = InlineDataEditor()
            self._editor.data_saved.connect(self._on_editor_saved)
            self._editor.edit_cancelled.connect(self._on_editor_cancelled)
            self.stack.addWidget(self._editor)

        self._editor.start_add(DataCategory.AMINO_ACIDS, template_data)
        self.stack.setCurrentWidget(self._editor)

    def start_edit(self, data):
        """Start edit mode with inline editor"""
        from periodica_app.ui.inline_editor import InlineDataEditor
        from periodica.data.data_manager import DataCategory

        if self._editor is None:
            self._editor = InlineDataEditor()
            self._editor.data_saved.connect(self._on_editor_saved)
            self._editor.edit_cancelled.connect(self._on_editor_cancelled)
            self.stack.addWidget(self._editor)

        self._editor.start_edit(DataCategory.AMINO_ACIDS, data)
        self.stack.setCurrentWidget(self._editor)

    def _on_editor_saved(self, data):
        """Handle save from editor"""
        self.stack.setCurrentWidget(self.display_widget)
        self.data_saved.emit(data)

    def _on_editor_cancelled(self):
        """Handle cancel from editor"""
        self.stack.setCurrentWidget(self.display_widget)
        self.edit_cancelled.emit()
