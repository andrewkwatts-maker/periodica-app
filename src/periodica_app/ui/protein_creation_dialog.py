"""
Protein Creation Dialog
Dialog for creating custom proteins from amino acid sequences.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QComboBox, QTextEdit, QWidget,
    QMessageBox, QSplitter, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

import json
from pathlib import Path
from typing import Dict, List, Optional

from periodica_app.ui.theme_constants import ThemeColors


# Standard amino acid codes
AMINO_ACID_CODES = {
    'A': 'Alanine', 'R': 'Arginine', 'N': 'Asparagine', 'D': 'Aspartic acid',
    'C': 'Cysteine', 'E': 'Glutamic acid', 'Q': 'Glutamine', 'G': 'Glycine',
    'H': 'Histidine', 'I': 'Isoleucine', 'L': 'Leucine', 'K': 'Lysine',
    'M': 'Methionine', 'F': 'Phenylalanine', 'P': 'Proline', 'S': 'Serine',
    'T': 'Threonine', 'W': 'Tryptophan', 'Y': 'Tyrosine', 'V': 'Valine'
}

# Amino acid properties for calculations
AMINO_ACID_MW = {
    'A': 89.09, 'R': 174.20, 'N': 132.12, 'D': 133.10, 'C': 121.15,
    'E': 147.13, 'Q': 146.15, 'G': 75.07, 'H': 155.16, 'I': 131.17,
    'L': 131.17, 'K': 146.19, 'M': 149.21, 'F': 165.19, 'P': 115.13,
    'S': 105.09, 'T': 119.12, 'W': 204.23, 'Y': 181.19, 'V': 117.15
}

AMINO_ACID_HYDROPATHY = {
    'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5,
    'E': -3.5, 'Q': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5,
    'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8, 'P': -1.6,
    'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2
}

AMINO_ACID_PK = {
    'D': 3.9, 'E': 4.1, 'H': 6.0, 'C': 8.3, 'Y': 10.1,
    'K': 10.5, 'R': 12.5
}


class AminoAcidPaletteButton(QFrame):
    """Button for amino acid selection in the palette."""
    clicked = Signal(str)

    def __init__(self, code: str, name: str, parent=None):
        super().__init__(parent)
        self.code = code
        self.name = name
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def _update_style(self):
        # Color by amino acid category
        if self.code in 'GAVLIMFWP':  # Nonpolar
            color = "#FF9800"
        elif self.code in 'STCYNQ':  # Polar uncharged
            color = "#4CAF50"
        elif self.code in 'DE':  # Acidic
            color = "#F44336"
        elif self.code in 'KRH':  # Basic
            color = "#2196F3"
        else:
            color = "#9E9E9E"

        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(40, 40, 60, 220),
                    stop:1 rgba(50, 50, 80, 220));
                border: 2px solid {color};
                border-radius: 5px;
            }}
            QFrame:hover {{
                border: 2px solid #66BB6A;
                background: rgba(60, 60, 80, 220);
            }}
        """)
        self.setToolTip(f"{self.code} - {self.name}")

    def paintEvent(self, event):
        super().paintEvent(event)
        from PySide6.QtGui import QPainter, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.code)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.code)


class ProteinCreationDialog(QDialog):
    """Dialog for creating proteins from amino acid sequences."""
    protein_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Protein from Amino Acids")
        self.setMinimumSize(900, 700)
        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Build Protein from Amino Acid Sequence")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #AB47BC;")
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Input
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Amino acid palette
        palette_group = QGroupBox("Amino Acid Palette")
        palette_group.setStyleSheet(self._get_group_style())
        palette_layout = QGridLayout(palette_group)
        palette_layout.setSpacing(5)

        row, col = 0, 0
        for code, name in sorted(AMINO_ACID_CODES.items()):
            btn = AminoAcidPaletteButton(code, name)
            btn.clicked.connect(self._add_amino_acid)
            palette_layout.addWidget(btn, row, col)
            col += 1
            if col >= 5:
                col = 0
                row += 1

        left_layout.addWidget(palette_group)

        # Sequence input
        sequence_group = QGroupBox("Amino Acid Sequence")
        sequence_group.setStyleSheet(self._get_group_style())
        sequence_layout = QVBoxLayout(sequence_group)

        self.sequence_edit = QTextEdit()
        self.sequence_edit.setPlaceholderText("Enter or build sequence (e.g., MVLSPADKTNVK...)")
        self.sequence_edit.setMaximumHeight(100)
        self.sequence_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 5px;
                font-family: monospace;
                font-size: 12px;
            }}
        """)
        self.sequence_edit.textChanged.connect(self.update_preview)
        sequence_layout.addWidget(self.sequence_edit)

        # Sequence controls
        seq_btn_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(self._get_button_style())
        clear_btn.clicked.connect(self.sequence_edit.clear)
        seq_btn_layout.addWidget(clear_btn)

        backspace_btn = QPushButton("Backspace")
        backspace_btn.setStyleSheet(self._get_button_style())
        backspace_btn.clicked.connect(self._backspace)
        seq_btn_layout.addWidget(backspace_btn)

        sequence_layout.addLayout(seq_btn_layout)

        self.sequence_count_label = QLabel("Sequence length: 0 amino acids")
        self.sequence_count_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px;")
        sequence_layout.addWidget(self.sequence_count_label)

        left_layout.addWidget(sequence_group)

        # Example sequences
        examples_group = QGroupBox("Example Sequences")
        examples_group.setStyleSheet(self._get_group_style())
        examples_layout = QVBoxLayout(examples_group)

        examples = [
            ("Insulin B-chain", "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"),
            ("Hemoglobin alpha", "VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH"),
            ("Glucagon", "HSQGTFTSDYSKYLDSRRAQDFVQWLMNT"),
        ]

        for name, seq in examples:
            btn = QPushButton(name)
            btn.setStyleSheet(self._get_button_style())
            btn.clicked.connect(lambda checked, s=seq: self._set_sequence(s))
            examples_layout.addWidget(btn)

        left_layout.addWidget(examples_group)

        # Protein settings
        settings_group = QGroupBox("Protein Settings")
        settings_group.setStyleSheet(self._get_group_style())
        settings_layout = QGridLayout(settings_group)

        name_label = QLabel("Name:")
        settings_layout.addWidget(name_label, 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., My Custom Protein")
        self.name_edit.setStyleSheet(self._get_input_style())
        self.name_edit.textChanged.connect(self.update_preview)
        settings_layout.addWidget(self.name_edit, 0, 1)

        function_label = QLabel("Function:")
        settings_layout.addWidget(function_label, 1, 0)
        self.function_combo = QComboBox()
        self.function_combo.addItems([
            "Enzyme", "Structural", "Transport", "Signaling",
            "Receptor", "Antibody", "Storage", "Regulatory"
        ])
        self.function_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(self.function_combo, 1, 1)

        localization_label = QLabel("Localization:")
        settings_layout.addWidget(localization_label, 2, 0)
        self.localization_combo = QComboBox()
        self.localization_combo.addItems([
            "Cytoplasm", "Nucleus", "Membrane", "Mitochondria",
            "ER", "Golgi", "Extracellular", "Lysosome"
        ])
        self.localization_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(self.localization_combo, 2, 1)

        left_layout.addWidget(settings_group)
        left_layout.addStretch()

        splitter.addWidget(left_panel)

        # Right panel - Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Composition preview
        comp_group = QGroupBox("Amino Acid Composition")
        comp_group.setStyleSheet(self._get_group_style())
        comp_layout = QVBoxLayout(comp_group)

        self.composition_label = QTextEdit()
        self.composition_label.setReadOnly(True)
        self.composition_label.setMaximumHeight(150)
        self.composition_label.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(40, 40, 60, 200);
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                font-family: monospace;
                font-size: 10px;
            }}
        """)
        comp_layout.addWidget(self.composition_label)

        right_layout.addWidget(comp_group)

        # Calculated properties
        props_group = QGroupBox("Calculated Properties")
        props_group.setStyleSheet(self._get_group_style())
        props_layout = QVBoxLayout(props_group)

        self.props_text = QTextEdit()
        self.props_text.setReadOnly(True)
        self.props_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(40, 40, 60, 200);
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                font-size: 11px;
            }}
        """)
        props_layout.addWidget(self.props_text)

        right_layout.addWidget(props_group)

        # Structure prediction
        structure_group = QGroupBox("Structure Prediction")
        structure_group.setStyleSheet(self._get_group_style())
        structure_layout = QVBoxLayout(structure_group)

        self.structure_text = QTextEdit()
        self.structure_text.setReadOnly(True)
        self.structure_text.setMaximumHeight(100)
        self.structure_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(40, 40, 60, 200);
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                font-size: 11px;
            }}
        """)
        structure_layout.addWidget(self.structure_text)

        right_layout.addWidget(structure_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([450, 450])

        layout.addWidget(splitter)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._get_button_style())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("Create Protein")
        create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #AB47BC, stop:1 #7B1FA2);
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7B1FA2, stop:1 #AB47BC);
            }
        """)
        create_btn.clicked.connect(self.create_protein)
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)

    def _add_amino_acid(self, code: str):
        """Add amino acid to sequence."""
        current = self.sequence_edit.toPlainText()
        self.sequence_edit.setText(current + code)

    def _backspace(self):
        """Remove last amino acid."""
        current = self.sequence_edit.toPlainText()
        if current:
            self.sequence_edit.setText(current[:-1])

    def _set_sequence(self, sequence: str):
        """Set the sequence from an example."""
        self.sequence_edit.setText(sequence)

    def update_preview(self):
        """Update the preview panels based on current sequence."""
        sequence = self._get_clean_sequence()

        # Update sequence count
        self.sequence_count_label.setText(f"Sequence length: {len(sequence)} amino acids")

        if not sequence:
            self.composition_label.setText("Enter a sequence to see composition")
            self.props_text.setText("Enter a sequence to calculate properties")
            self.structure_text.setText("Enter a sequence to predict structure")
            return

        # Calculate composition
        composition = {}
        for aa in sequence:
            composition[aa] = composition.get(aa, 0) + 1

        comp_lines = []
        for aa, count in sorted(composition.items(), key=lambda x: -x[1]):
            name = AMINO_ACID_CODES.get(aa, "Unknown")
            percent = count / len(sequence) * 100
            comp_lines.append(f"{aa} ({name}): {count} ({percent:.1f}%)")
        self.composition_label.setText("\n".join(comp_lines[:10]))

        # Calculate properties
        props = self._calculate_properties(sequence)
        props_text = f"""
Molecular Weight: {props['molecular_weight']:.2f} Da
Isoelectric Point (pI): {props['isoelectric_point']:.2f}
GRAVY (Hydropathy): {props['gravy']:.2f}
Net Charge at pH 7: {props['charge_pH7']:.1f}
Instability Index: {props['instability_index']:.1f}
Aliphatic Index: {props['aliphatic_index']:.1f}
        """.strip()
        self.props_text.setText(props_text)

        # Predict structure
        structure = self._predict_structure(sequence)
        structure_text = f"""
Helix Content: {structure['helix_percent']:.1f}%
Sheet Content: {structure['sheet_percent']:.1f}%
Coil Content: {structure['coil_percent']:.1f}%
        """.strip()
        self.structure_text.setText(structure_text)

    def _get_clean_sequence(self) -> str:
        """Get cleaned sequence (uppercase, only valid amino acids)."""
        text = self.sequence_edit.toPlainText().upper()
        return ''.join(aa for aa in text if aa in AMINO_ACID_CODES)

    def _calculate_properties(self, sequence: str) -> dict:
        """Calculate protein properties from sequence."""
        if not sequence:
            return {
                'molecular_weight': 0, 'isoelectric_point': 7.0,
                'gravy': 0, 'charge_pH7': 0, 'instability_index': 0,
                'aliphatic_index': 0
            }

        # Molecular weight
        mw = sum(AMINO_ACID_MW.get(aa, 110) for aa in sequence)
        mw -= 18.015 * (len(sequence) - 1)  # Water loss in peptide bonds

        # GRAVY (Grand Average of Hydropathy)
        gravy = sum(AMINO_ACID_HYDROPATHY.get(aa, 0) for aa in sequence) / len(sequence)

        # Approximate pI calculation
        pi = self._calculate_pi(sequence)

        # Charge at pH 7
        charge = self._calculate_charge(sequence, 7.0)

        # Instability index (simplified)
        instability = self._calculate_instability_index(sequence)

        # Aliphatic index
        aliphatic = self._calculate_aliphatic_index(sequence)

        return {
            'molecular_weight': mw,
            'isoelectric_point': pi,
            'gravy': gravy,
            'charge_pH7': charge,
            'instability_index': instability,
            'aliphatic_index': aliphatic
        }

    def _calculate_pi(self, sequence: str) -> float:
        """Calculate isoelectric point."""
        # Bisection method
        pH_low, pH_high = 0.0, 14.0
        for _ in range(50):
            pH_mid = (pH_low + pH_high) / 2
            charge = self._calculate_charge(sequence, pH_mid)
            if charge > 0:
                pH_low = pH_mid
            else:
                pH_high = pH_mid
        return (pH_low + pH_high) / 2

    def _calculate_charge(self, sequence: str, pH: float) -> float:
        """Calculate net charge at given pH."""
        charge = 0.0

        # N-terminus
        charge += 10 ** (9.69 - pH) / (1 + 10 ** (9.69 - pH))
        # C-terminus
        charge -= 10 ** (pH - 2.34) / (1 + 10 ** (pH - 2.34))

        # Side chains
        for aa in sequence:
            if aa in 'DE':  # Acidic
                pK = AMINO_ACID_PK.get(aa, 4.0)
                charge -= 10 ** (pH - pK) / (1 + 10 ** (pH - pK))
            elif aa in 'KRH':  # Basic
                pK = AMINO_ACID_PK.get(aa, 10.0)
                charge += 10 ** (pK - pH) / (1 + 10 ** (pK - pH))
            elif aa == 'C':
                charge -= 10 ** (pH - 8.3) / (1 + 10 ** (pH - 8.3))
            elif aa == 'Y':
                charge -= 10 ** (pH - 10.1) / (1 + 10 ** (pH - 10.1))

        return charge

    def _calculate_instability_index(self, sequence: str) -> float:
        """Calculate instability index (simplified)."""
        if len(sequence) < 2:
            return 0.0
        # This is a simplified calculation
        instability = 0.0
        for aa in sequence:
            if aa in 'RKNDEMW':
                instability += 1
        return (instability / len(sequence)) * 100

    def _calculate_aliphatic_index(self, sequence: str) -> float:
        """Calculate aliphatic index."""
        if not sequence:
            return 0.0
        a = sequence.count('A') / len(sequence) * 100
        v = sequence.count('V') / len(sequence) * 100
        i = sequence.count('I') / len(sequence) * 100
        l = sequence.count('L') / len(sequence) * 100
        return a + 2.9 * v + 3.9 * (i + l)

    def _predict_structure(self, sequence: str) -> dict:
        """Predict secondary structure content."""
        if not sequence:
            return {'helix_percent': 0, 'sheet_percent': 0, 'coil_percent': 0}

        # Simplified prediction based on amino acid propensities
        helix_formers = 'AELM'
        sheet_formers = 'VIY'

        helix_count = sum(1 for aa in sequence if aa in helix_formers)
        sheet_count = sum(1 for aa in sequence if aa in sheet_formers)
        total = len(sequence)

        helix = (helix_count / total) * 50  # Scale to reasonable percentages
        sheet = (sheet_count / total) * 40
        coil = 100 - helix - sheet

        return {
            'helix_percent': helix,
            'sheet_percent': sheet,
            'coil_percent': coil
        }

    def create_protein(self):
        """Create the protein and emit signal."""
        sequence = self._get_clean_sequence()
        name = self.name_edit.text().strip()

        if not sequence:
            QMessageBox.warning(self, "Invalid Sequence",
                              "Please enter a valid amino acid sequence.")
            return

        if not name:
            QMessageBox.warning(self, "Name Required",
                              "Please enter a name for the protein.")
            return

        # Calculate all properties
        props = self._calculate_properties(sequence)
        structure = self._predict_structure(sequence)

        protein_data = {
            'name': name,
            'sequence': sequence,
            'length': len(sequence),
            'function': self.function_combo.currentText().lower(),
            'localization': self.localization_combo.currentText().lower(),
            'molecular_mass': props['molecular_weight'],
            'isoelectric_point': props['isoelectric_point'],
            'gravy': props['gravy'],
            'charge_pH7': props['charge_pH7'],
            'instability_index': props['instability_index'],
            'aliphatic_index': props['aliphatic_index'],
            'secondary_structure': {
                'helix_percent': structure['helix_percent'],
                'sheet_percent': structure['sheet_percent'],
                'coil_percent': structure['coil_percent']
            },
            'is_custom': True
        }

        # Save to file
        proteins_dir = Path(__file__).parent.parent / "data" / "active" / "proteins"
        proteins_dir.mkdir(parents=True, exist_ok=True)

        filename = name.replace(" ", "_").replace("/", "_")
        filepath = proteins_dir / f"{filename}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(protein_data, f, indent=2)

        self.protein_created.emit(protein_data)
        self.accept()

    def _get_group_style(self):
        return f"""
            QGroupBox {{
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """

    def _get_button_style(self):
        return f"""
            QPushButton {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background: {ThemeColors.ACCENT};
                border-color: {ThemeColors.ACCENT};
            }}
        """

    def _get_input_style(self):
        return f"""
            QLineEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 8px;
            }}
        """

    def _get_combo_style(self):
        return f"""
            QComboBox {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                padding: 5px 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {ThemeColors.BG_DARK};
                color: {ThemeColors.TEXT_PRIMARY};
                selection-background-color: {ThemeColors.ACCENT};
            }}
        """
