"""
Cell Component Info Panel
Displays detailed information about a selected cell component including
composition, proteins, nucleic acids, and functional properties.
"""

import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QScrollArea, QFrame, QGridLayout, QGroupBox,
                                QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.cell_component_enums import (OrganelleType, ComponentFunction,
                                        CellularCompartment)


class CompositionPieWidget(QWidget):
    """Widget to display component composition as a pie chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
        self.setMinimumSize(200, 200)

    def set_data(self, data):
        """Set pie chart data {label: value}."""
        self._data = data
        self.update()

    def paintEvent(self, event):
        """Paint pie chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        if not self._data:
            painter.setPen(QColor(ThemeColors.TEXT_SECONDARY))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data")
            painter.end()
            return

        w = self.width()
        h = self.height()
        center_x = w // 2
        center_y = h // 2
        radius = min(w, h) // 2 - 40

        total = sum(self._data.values())
        if total == 0:
            painter.end()
            return

        colors = [
            QColor("#2196F3"), QColor("#4CAF50"), QColor("#FF9800"),
            QColor("#9C27B0"), QColor("#F44336"), QColor("#00BCD4"),
            QColor("#FFC107"), QColor("#E91E63"), QColor("#795548"),
        ]

        start_angle = 0
        for i, (label, value) in enumerate(self._data.items()):
            span_angle = int(360 * 16 * value / total)
            color = colors[i % len(colors)]

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPie(
                center_x - radius, center_y - radius,
                radius * 2, radius * 2,
                start_angle, span_angle
            )

            # Draw label
            angle_mid = (start_angle + span_angle / 2) / 16 * 3.14159 / 180
            import math
            label_x = center_x + int((radius + 25) * math.cos(angle_mid))
            label_y = center_y - int((radius + 25) * math.sin(angle_mid))

            painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
            painter.setFont(QFont("Arial", 8))
            pct = 100 * value / total
            painter.drawText(label_x - 20, label_y, f"{label[:10]}: {pct:.0f}%")

            start_angle += span_angle

        painter.end()


class CellComponentInfoPanel(QWidget):
    """Panel displaying detailed cell component information."""

    component_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._component = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the info panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        self.header_label = QLabel("No Component Selected")
        self.header_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {ThemeColors.ACCENT};
            padding: 5px;
        """)
        layout.addWidget(self.header_label)

        # Type/function indicator
        self.type_label = QLabel("")
        self.type_label.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY};")
        layout.addWidget(self.type_label)

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

        # Composition tab
        self.composition_widget = self._create_composition_tab()
        self.tabs.addTab(self.composition_widget, "Composition")

        # Proteins tab
        self.proteins_widget = self._create_proteins_tab()
        self.tabs.addTab(self.proteins_widget, "Proteins")

        # Nucleic Acids tab
        self.nucleic_acids_widget = self._create_nucleic_acids_tab()
        self.tabs.addTab(self.nucleic_acids_widget, "Nucleic Acids")

        # Function tab
        self.function_widget = self._create_function_tab()
        self.tabs.addTab(self.function_widget, "Function")

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
            ("Function", "function"),
            ("Localization", "localization"),
            ("Diameter", "diameter"),
            ("Mass", "mass"),
            ("Copy Number", "copy_number"),
            ("Protein Count", "protein_count"),
            ("RNA Count", "rna_count"),
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

    def _create_composition_tab(self):
        """Create composition visualization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Pie chart
        self.composition_pie = CompositionPieWidget()
        layout.addWidget(self.composition_pie)

        # Composition details
        self.composition_text = QTextEdit()
        self.composition_text.setReadOnly(True)
        self.composition_text.setMaximumHeight(150)
        self.composition_text.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.composition_text)

        return widget

    def _create_proteins_tab(self):
        """Create proteins list tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Proteins tree
        self.proteins_tree = QTreeWidget()
        self.proteins_tree.setHeaderLabels(["Protein", "Count", "Function"])
        self.proteins_tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
            }}
            QTreeWidget::item:selected {{
                background: {ThemeColors.ACCENT};
            }}
            QHeaderView::section {{
                background: {ThemeColors.BG_DARK};
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                padding: 5px;
            }}
        """)
        layout.addWidget(self.proteins_tree)

        # Summary
        self.proteins_summary = QLabel("Total: 0 proteins")
        self.proteins_summary.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY};")
        layout.addWidget(self.proteins_summary)

        return widget

    def _create_nucleic_acids_tab(self):
        """Create nucleic acids list tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Nucleic acids tree
        self.na_tree = QTreeWidget()
        self.na_tree.setHeaderLabels(["Nucleic Acid", "Type", "Count"])
        self.na_tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
            }}
            QTreeWidget::item:selected {{
                background: {ThemeColors.ACCENT};
            }}
            QHeaderView::section {{
                background: {ThemeColors.BG_DARK};
                color: {ThemeColors.TEXT_PRIMARY};
                border: none;
                padding: 5px;
            }}
        """)
        layout.addWidget(self.na_tree)

        # Summary
        self.na_summary = QLabel("Total: 0 nucleic acids")
        self.na_summary.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY};")
        layout.addWidget(self.na_summary)

        return widget

    def _create_function_tab(self):
        """Create function/description tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {ThemeColors.BG_DARK}; border: none;")

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Description
        desc_label = QLabel("Description")
        desc_label.setStyleSheet(f"""
            color: {ThemeColors.TEXT_PRIMARY};
            font-weight: bold;
            font-size: 14px;
        """)
        layout.addWidget(desc_label)

        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.description_text)

        # Processes involved
        process_label = QLabel("Cellular Processes")
        process_label.setStyleSheet(f"""
            color: {ThemeColors.TEXT_PRIMARY};
            font-weight: bold;
            font-size: 14px;
        """)
        layout.addWidget(process_label)

        self.processes_text = QTextEdit()
        self.processes_text.setReadOnly(True)
        self.processes_text.setMaximumHeight(100)
        self.processes_text.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.processes_text)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def set_component(self, comp_data):
        """Set and display component data."""
        self._component = comp_data

        if not comp_data:
            self.header_label.setText("No Component Selected")
            self.type_label.setText("")
            return

        # Header
        name = comp_data.get('name', 'Unknown')
        self.header_label.setText(name)

        # Type/function line
        comp_type = comp_data.get('type', 'unknown').replace('_', ' ').title()
        func = comp_data.get('function', 'unknown').replace('_', ' ').title()
        self.type_label.setText(f"{comp_type} • {func}")

        # Properties
        self._update_property("type", comp_type)
        self._update_property("function", func)

        # Localization
        loc = comp_data.get('localization', [])
        if isinstance(loc, list):
            loc_str = ", ".join(l.replace('_', ' ').title() for l in loc)
        else:
            loc_str = str(loc).replace('_', ' ').title()
        self._update_property("localization", loc_str)

        # Size properties
        diameter_um = comp_data.get('diameter_um')
        diameter_nm = comp_data.get('diameter_nm')
        if diameter_um:
            self._update_property("diameter", f"{diameter_um} μm")
        elif diameter_nm:
            self._update_property("diameter", f"{diameter_nm} nm")
        else:
            self._update_property("diameter", "-")

        mass = comp_data.get('mass_kDa', comp_data.get('mass_MDa', 0))
        unit = "MDa" if 'mass_MDa' in comp_data else "kDa"
        self._update_property("mass", f"{mass} {unit}" if mass else "-")

        copy_num = comp_data.get('copy_number_per_cell', 0)
        if copy_num >= 1000000:
            copy_str = f"{copy_num/1000000:.1f}M"
        elif copy_num >= 1000:
            copy_str = f"{copy_num/1000:.0f}k"
        else:
            copy_str = str(copy_num)
        self._update_property("copy_number", copy_str)

        # Proteins
        proteins = comp_data.get('proteins', [])
        protein_count = sum(p.get('count', 1) for p in proteins) if isinstance(proteins, list) else 0
        self._update_property("protein_count", str(protein_count))

        # Nucleic acids
        nucleic_acids = comp_data.get('nucleic_acids', [])
        na_count = sum(na.get('count', 1) for na in nucleic_acids) if isinstance(nucleic_acids, list) else 0
        self._update_property("rna_count", str(na_count))

        # Composition pie chart
        composition_data = {}
        if proteins:
            composition_data["Proteins"] = len(proteins)
        if nucleic_acids:
            composition_data["Nucleic Acids"] = len(nucleic_acids)
        lipids = comp_data.get('lipid_composition', {})
        if lipids:
            composition_data["Lipids"] = len(lipids)
        self.composition_pie.set_data(composition_data)

        # Composition text
        comp_text = "Component Breakdown:\n\n"
        if proteins:
            comp_text += f"Proteins: {len(proteins)} types, {protein_count} total\n"
        if nucleic_acids:
            comp_text += f"Nucleic Acids: {len(nucleic_acids)} types, {na_count} total\n"
        if lipids:
            comp_text += f"Lipids: {len(lipids)} types\n"
        self.composition_text.setText(comp_text)

        # Proteins tree
        self.proteins_tree.clear()
        for prot in proteins:
            item = QTreeWidgetItem([
                prot.get('name', 'Unknown'),
                str(prot.get('count', 1)),
                prot.get('function', '-')
            ])
            self.proteins_tree.addTopLevelItem(item)
        self.proteins_summary.setText(f"Total: {protein_count} proteins ({len(proteins)} types)")

        # Nucleic acids tree
        self.na_tree.clear()
        for na in nucleic_acids:
            item = QTreeWidgetItem([
                na.get('name', 'Unknown'),
                na.get('type', 'RNA').upper(),
                str(na.get('count', 1))
            ])
            self.na_tree.addTopLevelItem(item)
        self.na_summary.setText(f"Total: {na_count} nucleic acids ({len(nucleic_acids)} types)")

        # Description
        desc = comp_data.get('description', 'No description available.')
        self.description_text.setText(desc)

        # Processes
        processes = comp_data.get('cellular_processes', [])
        if processes:
            proc_text = "\n".join(f"• {p}" for p in processes)
        else:
            proc_text = "No cellular processes listed."
        self.processes_text.setText(proc_text)

    def _update_property(self, key, value):
        """Update a property label."""
        if key in self.property_labels:
            self.property_labels[key].setText(str(value))

    def get_current_component(self):
        """Get currently displayed component data."""
        return self._component
