"""
Protein Info Panel
Displays detailed information about a selected protein including
sequence, secondary structure, phi/psi angles, and computed properties.
"""

import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QScrollArea, QFrame, QGridLayout, QGroupBox,
                                QTextEdit, QSplitter, QTabWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.protein_enums import (SecondaryStructureType, ProteinFunction,
                                 CellularLocalization, FoldingState)


class RamachandranWidget(QWidget):
    """Widget to display Ramachandran plot for protein."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 250)
        self._residues = []

    def set_residues(self, residues):
        """Set residue data with phi/psi angles."""
        self._residues = residues
        self.update()

    def paintEvent(self, event):
        """Paint Ramachandran plot."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 40

        # Background
        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        # Plot area
        plot_w = w - 2 * margin
        plot_h = h - 2 * margin

        # Draw axes
        painter.setPen(QPen(QColor(ThemeColors.TEXT_SECONDARY), 1))
        painter.drawRect(margin, margin, plot_w, plot_h)

        # Draw center lines
        painter.setPen(QPen(QColor(ThemeColors.BORDER), 1, Qt.PenStyle.DashLine))
        painter.drawLine(margin + plot_w // 2, margin,
                        margin + plot_w // 2, margin + plot_h)
        painter.drawLine(margin, margin + plot_h // 2,
                        margin + plot_w, margin + plot_h // 2)

        # Draw allowed regions (simplified)
        painter.setPen(Qt.PenStyle.NoPen)

        # Alpha helix region
        painter.setBrush(QBrush(QColor(255, 64, 129, 40)))  # Pink
        helix_x = margin + int(((-80 + 180) / 360) * plot_w)
        helix_y = margin + int(((-59 + 180) / 360) * plot_h)
        helix_w = int((32 / 360) * plot_w)
        helix_h = int((32 / 360) * plot_h)
        painter.drawEllipse(helix_x, helix_y, helix_w * 2, helix_h * 2)

        # Beta sheet region
        painter.setBrush(QBrush(QColor(68, 138, 255, 40)))  # Blue
        beta_x = margin + int(((-150 + 180) / 360) * plot_w)
        beta_y = margin + int(((90 + 180) / 360) * plot_h)
        beta_w = int((60 / 360) * plot_w)
        beta_h = int((60 / 360) * plot_h)
        painter.drawEllipse(beta_x, beta_y, beta_w * 2, beta_h * 2)

        # Draw points for each residue
        for res in self._residues:
            phi = res.get('phi', 0)
            psi = res.get('psi', 0)
            structure = res.get('structure', 'C')

            # Convert to plot coordinates
            x = margin + int(((phi + 180) / 360) * plot_w)
            y = margin + int(((-psi + 180) / 360) * plot_h)  # Invert Y

            # Color by structure
            if structure == 'H':
                color = QColor("#FF4081")  # Pink for helix
            elif structure == 'E':
                color = QColor("#448AFF")  # Blue for sheet
            elif structure == 'T':
                color = QColor("#69F0AE")  # Green for turn
            else:
                color = QColor("#9E9E9E")  # Grey for coil

            painter.setPen(QPen(color.darker(120), 1))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(x - 3, y - 3, 6, 6)

        # Draw axis labels
        painter.setPen(QPen(QColor(ThemeColors.TEXT_PRIMARY)))
        font = QFont("Arial", 9)
        painter.setFont(font)

        # X axis (phi)
        painter.drawText(margin - 5, h - 10, "-180")
        painter.drawText(margin + plot_w - 15, h - 10, "180")
        painter.drawText(w // 2 - 20, h - 10, "φ (phi)")

        # Y axis (psi)
        painter.save()
        painter.translate(15, h // 2)
        painter.rotate(-90)
        painter.drawText(-20, 0, "ψ (psi)")
        painter.restore()

        painter.drawText(5, margin + 10, "180")
        painter.drawText(5, margin + plot_h, "-180")

        painter.end()


class SequenceWidget(QWidget):
    """Widget to display protein sequence with secondary structure coloring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._residues = []
        self.setMinimumHeight(60)

    def set_residues(self, residues):
        """Set residue data."""
        self._residues = residues
        self.update()

    def paintEvent(self, event):
        """Paint sequence with structure coloring."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        if not self._residues:
            painter.setPen(QColor(ThemeColors.TEXT_SECONDARY))
            painter.drawText(10, 30, "No sequence loaded")
            painter.end()
            return

        font = QFont("Courier New", 10)
        painter.setFont(font)

        char_width = 12
        char_height = 16
        margin = 10
        chars_per_line = max(1, (self.width() - 2 * margin) // char_width)

        for i, res in enumerate(self._residues):
            row = i // chars_per_line
            col = i % chars_per_line

            x = margin + col * char_width
            y = margin + row * (char_height + 5) + char_height

            # Structure color bar
            structure = res.get('structure', 'C')
            if structure == 'H':
                color = QColor("#FF4081")
            elif structure == 'E':
                color = QColor("#448AFF")
            elif structure == 'T':
                color = QColor("#69F0AE")
            else:
                color = QColor("#9E9E9E")

            painter.fillRect(x, y + 2, char_width - 2, 3, color)

            # Residue letter
            painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
            painter.drawText(x, y, res.get('residue', '?'))

        painter.end()

    def sizeHint(self):
        if not self._residues:
            return super().sizeHint()
        char_width = 12
        margin = 10
        chars_per_line = max(1, (self.width() - 2 * margin) // char_width)
        rows = (len(self._residues) + chars_per_line - 1) // chars_per_line
        return super().sizeHint()


class ProteinInfoPanel(QWidget):
    """Panel displaying detailed protein information."""

    protein_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._protein = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the info panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        self.header_label = QLabel("No Protein Selected")
        self.header_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {ThemeColors.ACCENT};
            padding: 5px;
        """)
        layout.addWidget(self.header_label)

        # Tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                background: {ThemeColors.BG_DARK};
            }}
            QTabBar::tab {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                padding: 8px 16px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            QTabBar::tab:selected {{
                background: {ThemeColors.ACCENT};
            }}
        """)
        layout.addWidget(self.tabs)

        # Properties tab
        self.properties_widget = self._create_properties_tab()
        self.tabs.addTab(self.properties_widget, "Properties")

        # Sequence tab
        self.sequence_widget = self._create_sequence_tab()
        self.tabs.addTab(self.sequence_widget, "Sequence")

        # Structure tab
        self.structure_widget = self._create_structure_tab()
        self.tabs.addTab(self.structure_widget, "Structure")

        # Ramachandran tab
        self.ramachandran_widget = RamachandranWidget()
        self.tabs.addTab(self.ramachandran_widget, "Ramachandran")

    def _create_properties_tab(self):
        """Create properties display tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {ThemeColors.BG_DARK}; border: none;")

        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.property_labels = {}
        properties = [
            ("Organism", "organism"),
            ("Function", "function"),
            ("Localization", "localization"),
            ("Length", "length"),
            ("Molecular Mass", "molecular_mass"),
            ("Isoelectric Point", "isoelectric_point"),
            ("Charge at pH 7", "charge_pH7"),
            ("GRAVY", "gravy"),
            ("Helix %", "helix_percent"),
            ("Sheet %", "sheet_percent"),
            ("Disulfide Bonds", "disulfide_bonds"),
        ]

        for i, (label_text, key) in enumerate(properties):
            label = QLabel(f"{label_text}:")
            label.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-weight: bold;")
            layout.addWidget(label, i, 0)

            value_label = QLabel("-")
            value_label.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
            value_label.setWordWrap(True)
            layout.addWidget(value_label, i, 1)
            self.property_labels[key] = value_label

        layout.setRowStretch(len(properties), 1)
        scroll.setWidget(widget)
        return scroll

    def _create_sequence_tab(self):
        """Create sequence display tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Sequence display
        self.sequence_display = SequenceWidget()
        layout.addWidget(self.sequence_display)

        # Legend
        legend_layout = QHBoxLayout()
        for struct, color, name in [
            ('H', "#FF4081", "Helix"),
            ('E', "#448AFF", "Sheet"),
            ('T', "#69F0AE", "Turn"),
            ('C', "#9E9E9E", "Coil"),
        ]:
            legend_item = QLabel(f"■ {name}")
            legend_item.setStyleSheet(f"color: {color}; font-size: 11px;")
            legend_layout.addWidget(legend_item)
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        # Raw sequence text
        self.sequence_text = QTextEdit()
        self.sequence_text.setReadOnly(True)
        self.sequence_text.setMaximumHeight(100)
        self.sequence_text.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                font-family: monospace;
            }}
        """)
        layout.addWidget(self.sequence_text)

        return widget

    def _create_structure_tab(self):
        """Create structure analysis tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {ThemeColors.BG_DARK}; border: none;")

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Secondary structure summary
        self.structure_summary = QLabel()
        self.structure_summary.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        self.structure_summary.setWordWrap(True)
        layout.addWidget(self.structure_summary)

        # Amino acid composition
        comp_group = QGroupBox("Amino Acid Composition")
        comp_group.setStyleSheet(f"""
            QGroupBox {{
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
        """)
        comp_layout = QGridLayout(comp_group)
        self.composition_labels = {}

        aa_order = ['A', 'R', 'N', 'D', 'C', 'E', 'Q', 'G', 'H', 'I',
                   'L', 'K', 'M', 'F', 'P', 'S', 'T', 'W', 'Y', 'V']
        for i, aa in enumerate(aa_order):
            row = i // 5
            col = i % 5
            label = QLabel(f"{aa}: -")
            label.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY}; font-family: monospace;")
            comp_layout.addWidget(label, row, col)
            self.composition_labels[aa] = label

        layout.addWidget(comp_group)

        # Disulfide bonds
        self.disulfide_label = QLabel("Disulfide Bonds: None")
        self.disulfide_label.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        self.disulfide_label.setWordWrap(True)
        layout.addWidget(self.disulfide_label)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def set_protein(self, protein_data):
        """Set and display protein data."""
        self._protein = protein_data

        if not protein_data:
            self.header_label.setText("No Protein Selected")
            return

        # Header
        name = protein_data.get('name', 'Unknown')
        self.header_label.setText(name)

        # Properties
        self._update_property("organism", protein_data.get('organism', '-'))
        self._update_property("function", protein_data.get('function', '-'))
        self._update_property("localization", protein_data.get('localization', '-'))
        self._update_property("length", f"{protein_data.get('length', 0)} residues")
        self._update_property("molecular_mass", f"{protein_data.get('molecular_mass', 0):.2f} Da")
        self._update_property("isoelectric_point", f"{protein_data.get('isoelectric_point', 0):.2f}")
        self._update_property("charge_pH7", f"{protein_data.get('charge_pH7', 0):.2f}")
        self._update_property("gravy", f"{protein_data.get('gravy', 0):.3f}")

        ss = protein_data.get('secondary_structure', {})
        self._update_property("helix_percent", f"{ss.get('helix_percent', 0):.1f}%")
        self._update_property("sheet_percent", f"{ss.get('sheet_percent', 0):.1f}%")

        bonds = protein_data.get('disulfide_bonds', [])
        if bonds:
            bond_str = ", ".join([f"C{b[0]}-C{b[1]}" for b in bonds])
            self._update_property("disulfide_bonds", bond_str)
        else:
            self._update_property("disulfide_bonds", "None")

        # Sequence
        sequence = protein_data.get('sequence', '')
        self.sequence_text.setText(sequence)

        residues = protein_data.get('residues', [])
        self.sequence_display.set_residues(residues)
        self.ramachandran_widget.set_residues(residues)

        # Structure summary
        self.structure_summary.setText(
            f"Secondary Structure:\n"
            f"  • Alpha Helix: {ss.get('helix_percent', 0):.1f}%\n"
            f"  • Beta Sheet: {ss.get('sheet_percent', 0):.1f}%\n"
            f"  • Turns: {ss.get('turn_percent', 0):.1f}%\n"
            f"  • Coil: {ss.get('coil_percent', 0):.1f}%"
        )

        # Composition
        composition = protein_data.get('amino_acid_composition', {})
        for aa, label in self.composition_labels.items():
            count = composition.get(aa, 0)
            label.setText(f"{aa}: {count}")

        # Disulfide bonds
        if bonds:
            self.disulfide_label.setText(f"Disulfide Bonds: {bond_str}")
        else:
            self.disulfide_label.setText("Disulfide Bonds: None")

    def _update_property(self, key, value):
        """Update a property label."""
        if key in self.property_labels:
            self.property_labels[key].setText(str(value))

    def get_current_protein(self):
        """Get currently displayed protein data."""
        return self._protein
