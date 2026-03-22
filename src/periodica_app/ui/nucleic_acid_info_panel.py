"""
Nucleic Acid Info Panel
Displays detailed information about a selected nucleic acid including
sequence, base composition, Tm, and secondary structure predictions.
"""

import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QScrollArea, QFrame, QGridLayout, QGroupBox,
                                QTextEdit, QTabWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.nucleic_acid_enums import NucleicAcidType, BaseType, NucleicAcidFunction


class SequenceDisplayWidget(QWidget):
    """Widget to display nucleic acid sequence with base coloring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sequence = ""
        self._complement = ""
        self._show_complement = False
        self.setMinimumHeight(80)

    def set_sequence(self, sequence, complement=""):
        """Set sequence data."""
        self._sequence = sequence
        self._complement = complement
        self.update()

    def set_show_complement(self, show):
        """Toggle complement display."""
        self._show_complement = show
        self.update()

    def paintEvent(self, event):
        """Paint sequence with base coloring."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        if not self._sequence:
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

        base_colors = {
            'A': QColor("#4CAF50"),   # Green
            'T': QColor("#F44336"),   # Red
            'U': QColor("#FF5722"),   # Deep orange
            'G': QColor("#FFC107"),   # Amber
            'C': QColor("#2196F3"),   # Blue
        }

        for i, base in enumerate(self._sequence):
            row = i // chars_per_line
            col = i % chars_per_line

            x = margin + col * char_width
            y = margin + row * (char_height + 5) + char_height

            # Base color
            color = base_colors.get(base, QColor(ThemeColors.TEXT_PRIMARY))
            painter.setPen(color)
            painter.drawText(x, y, base)

            # Draw complement below if enabled
            if self._show_complement and i < len(self._complement):
                comp_y = y + char_height
                comp_base = self._complement[i]
                comp_color = base_colors.get(comp_base, QColor(ThemeColors.TEXT_SECONDARY))
                painter.setPen(comp_color)
                painter.drawText(x, comp_y, comp_base)

        painter.end()


class CompositionWidget(QWidget):
    """Widget to display base composition as a bar chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._composition = {}
        self.setMinimumHeight(100)

    def set_composition(self, composition):
        """Set base composition data."""
        self._composition = composition
        self.update()

    def paintEvent(self, event):
        """Paint composition bar chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        if not self._composition:
            painter.end()
            return

        w = self.width()
        h = self.height()
        margin = 40

        total = sum(self._composition.values())
        if total == 0:
            painter.end()
            return

        base_colors = {
            'A': QColor("#4CAF50"),
            'T': QColor("#F44336"),
            'U': QColor("#FF5722"),
            'G': QColor("#FFC107"),
            'C': QColor("#2196F3"),
        }

        bar_width = (w - 2 * margin) // max(1, len(self._composition))
        max_height = h - 60

        x = margin
        for base, count in sorted(self._composition.items()):
            percentage = count / total
            bar_height = int(max_height * percentage)

            color = base_colors.get(base, QColor(ThemeColors.TEXT_PRIMARY))
            painter.fillRect(x, h - 30 - bar_height, bar_width - 5, bar_height, color)

            # Label
            painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
            painter.drawText(x, h - 10, f"{base}: {count}")
            painter.drawText(x, h - 30 - bar_height - 5, f"{percentage*100:.1f}%")

            x += bar_width

        painter.end()


class NucleicAcidInfoPanel(QWidget):
    """Panel displaying detailed nucleic acid information."""

    nucleic_acid_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nucleic_acid = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the info panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        self.header_label = QLabel("No Nucleic Acid Selected")
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

        # Composition tab
        self.composition_widget = self._create_composition_tab()
        self.tabs.addTab(self.composition_widget, "Composition")

        # Structure tab
        self.structure_widget = self._create_structure_tab()
        self.tabs.addTab(self.structure_widget, "Structure")

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
            ("Type", "type"),
            ("Organism", "organism"),
            ("Function", "function"),
            ("Length", "length"),
            ("GC Content", "gc_content"),
            ("Molecular Mass", "molecular_mass"),
            ("Tm (NN)", "tm_nn"),
            ("Tm (GC)", "tm_gc"),
            ("Complement", "complement_preview"),
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
        self.sequence_display = SequenceDisplayWidget()
        layout.addWidget(self.sequence_display)

        # Legend
        legend_layout = QHBoxLayout()
        for base, color, name in [
            ('A', "#4CAF50", "Adenine"),
            ('T', "#F44336", "Thymine"),
            ('G', "#FFC107", "Guanine"),
            ('C', "#2196F3", "Cytosine"),
            ('U', "#FF5722", "Uracil"),
        ]:
            legend_item = QLabel(f"■ {base}")
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

    def _create_composition_tab(self):
        """Create base composition tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Composition chart
        self.comp_chart = CompositionWidget()
        layout.addWidget(self.comp_chart)

        # Detailed composition
        self.comp_details = QLabel()
        self.comp_details.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        self.comp_details.setWordWrap(True)
        layout.addWidget(self.comp_details)

        layout.addStretch()
        return widget

    def _create_structure_tab(self):
        """Create secondary structure tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {ThemeColors.BG_DARK}; border: none;")

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Hairpin predictions
        self.structure_label = QLabel("Secondary Structure Predictions")
        self.structure_label.setStyleSheet(f"""
            color: {ThemeColors.TEXT_PRIMARY};
            font-weight: bold;
            font-size: 14px;
        """)
        layout.addWidget(self.structure_label)

        self.hairpin_text = QTextEdit()
        self.hairpin_text.setReadOnly(True)
        self.hairpin_text.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
                font-family: monospace;
            }}
        """)
        layout.addWidget(self.hairpin_text)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def set_nucleic_acid(self, na_data):
        """Set and display nucleic acid data."""
        self._nucleic_acid = na_data

        if not na_data:
            self.header_label.setText("No Nucleic Acid Selected")
            return

        # Header
        name = na_data.get('name', 'Unknown')
        self.header_label.setText(name)

        # Properties
        self._update_property("type", na_data.get('type', '-').upper())
        self._update_property("organism", na_data.get('organism', '-'))
        self._update_property("function", na_data.get('function', '-'))
        self._update_property("length", f"{na_data.get('length', 0)} nt")
        self._update_property("gc_content", f"{na_data.get('gc_content', 0):.1f}%")
        self._update_property("molecular_mass", f"{na_data.get('molecular_mass', 0):.1f} Da")

        # Tm values
        tm = na_data.get('melting_temperature', {})
        if isinstance(tm, dict):
            self._update_property("tm_nn", f"{tm.get('nearest_neighbor', 0):.1f}°C")
            self._update_property("tm_gc", f"{tm.get('gc_method', 0):.1f}°C")
        else:
            self._update_property("tm_nn", f"{tm:.1f}°C")
            self._update_property("tm_gc", "-")

        # Complement preview
        complement = na_data.get('complement', '')
        if len(complement) > 30:
            complement = complement[:30] + "..."
        self._update_property("complement_preview", complement)

        # Sequence
        sequence = na_data.get('sequence', '')
        self.sequence_text.setText(sequence)
        self.sequence_display.set_sequence(sequence, na_data.get('complement', ''))

        # Composition
        composition = na_data.get('base_composition', {})
        self.comp_chart.set_composition(composition)

        total = sum(composition.values())
        comp_text = "Base Composition:\n"
        for base, count in sorted(composition.items()):
            pct = 100 * count / total if total > 0 else 0
            comp_text += f"  {base}: {count} ({pct:.1f}%)\n"
        self.comp_details.setText(comp_text)

        # Secondary structures
        structures = na_data.get('secondary_structures', {})
        hairpins = structures.get('details', [])
        if hairpins:
            hairpin_text = f"Predicted Hairpins: {len(hairpins)}\n\n"
            for i, hp in enumerate(hairpins[:5], 1):
                hairpin_text += f"Hairpin {i}:\n"
                hairpin_text += f"  Position: {hp.get('start', 0)}-{hp.get('end', 0)}\n"
                hairpin_text += f"  Stem: {hp.get('stem_sequence', '')} ({hp.get('stem_length', 0)} bp)\n"
                hairpin_text += f"  Loop: {hp.get('loop_sequence', '')} ({hp.get('loop_length', 0)} nt)\n"
                hairpin_text += f"  Stability: {hp.get('stability', 0):.2f}\n\n"
            self.hairpin_text.setText(hairpin_text)
        else:
            self.hairpin_text.setText("No significant hairpin structures predicted.")

    def _update_property(self, key, value):
        """Update a property label."""
        if key in self.property_labels:
            self.property_labels[key].setText(str(value))

    def get_current_nucleic_acid(self):
        """Get currently displayed nucleic acid data."""
        return self._nucleic_acid
