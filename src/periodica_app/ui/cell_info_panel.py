"""
Cell Info Panel
Displays detailed information about a selected cell including
size, metabolic properties, organelles, and functional characteristics.
"""

import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QScrollArea, QFrame, QGridLayout, QGroupBox,
                                QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.cell_enums import CellType, TissueType, MetabolicState


class MetabolicWidget(QWidget):
    """Widget to display metabolic rate visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._metabolic_rate = 0
        self._atp_turnover = 0
        self._o2_consumption = 0
        self.setMinimumHeight(150)

    def set_data(self, metabolic_rate, atp_turnover, o2_consumption):
        """Set metabolic data."""
        self._metabolic_rate = metabolic_rate
        self._atp_turnover = atp_turnover
        self._o2_consumption = o2_consumption
        self.update()

    def paintEvent(self, event):
        """Paint metabolic visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        w = self.width()
        h = self.height()

        # Draw metabolic rate bar
        painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(10, 25, "Metabolic Rate")

        # Normalize rate to bar width (log scale)
        if self._metabolic_rate > 0:
            log_rate = math.log10(self._metabolic_rate)
            bar_width = int(min(max(log_rate * 50, 20), w - 100))
        else:
            bar_width = 20

        # Color based on rate
        if self._metabolic_rate < 10:
            bar_color = QColor("#4CAF50")
        elif self._metabolic_rate < 100:
            bar_color = QColor("#FF9800")
        else:
            bar_color = QColor("#F44336")

        painter.fillRect(10, 35, bar_width, 20, bar_color)

        # Draw rate value
        painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
        if self._metabolic_rate >= 1000:
            rate_str = f"{self._metabolic_rate/1000:.1f} pW"
        else:
            rate_str = f"{self._metabolic_rate:.1f} fW"
        painter.drawText(bar_width + 20, 50, rate_str)

        # Draw ATP turnover
        painter.drawText(10, 80, "ATP Turnover")
        if self._atp_turnover >= 1e9:
            atp_str = f"{self._atp_turnover/1e9:.1f}×10⁹/s"
        elif self._atp_turnover >= 1e6:
            atp_str = f"{self._atp_turnover/1e6:.1f}×10⁶/s"
        else:
            atp_str = f"{self._atp_turnover:.0f}/s"
        painter.drawText(120, 80, atp_str)

        # Draw O2 consumption
        painter.drawText(10, 105, "O₂ Consumption")
        if self._o2_consumption >= 1e9:
            o2_str = f"{self._o2_consumption/1e9:.1f}×10⁹/s"
        elif self._o2_consumption >= 1e6:
            o2_str = f"{self._o2_consumption/1e6:.1f}×10⁶/s"
        else:
            o2_str = f"{self._o2_consumption:.0f}/s"
        painter.drawText(120, 105, o2_str)

        # Draw Kleiber's Law note
        painter.setPen(QColor(ThemeColors.TEXT_SECONDARY))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(10, h - 10, "Based on Kleiber's Law: B = B₀ × M^0.75")

        painter.end()


class CellSizeWidget(QWidget):
    """Widget to visualize cell size relative to scale."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._diameter = 10
        self._cell_name = ""
        self.setMinimumHeight(180)

    def set_data(self, diameter, name):
        """Set cell size data."""
        self._diameter = diameter
        self._cell_name = name
        self.update()

    def paintEvent(self, event):
        """Paint cell size visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        w = self.width()
        h = self.height()

        # Draw scale bar
        painter.setPen(QColor(ThemeColors.TEXT_SECONDARY))
        scale_y = h - 20
        painter.drawLine(10, scale_y, w - 10, scale_y)

        # Scale marks (10μm increments)
        scale_width = w - 20
        pixels_per_um = scale_width / 150  # Max 150μm shown

        for um in range(0, 151, 10):
            x = 10 + int(um * pixels_per_um)
            painter.drawLine(x, scale_y - 5, x, scale_y + 5)
            if um % 50 == 0:
                painter.drawText(x - 10, scale_y + 18, f"{um}μm")

        # Draw cell circle
        cell_pixels = max(10, int(self._diameter * pixels_per_um))
        center_x = w // 2
        center_y = h // 2 - 10

        # Cell color based on size
        if self._diameter < 10:
            cell_color = QColor("#4CAF50")
        elif self._diameter < 30:
            cell_color = QColor("#2196F3")
        elif self._diameter < 50:
            cell_color = QColor("#FF9800")
        else:
            cell_color = QColor("#F44336")

        painter.setBrush(QBrush(cell_color.lighter(150)))
        painter.setPen(QPen(cell_color, 2))
        painter.drawEllipse(
            center_x - cell_pixels // 2,
            center_y - cell_pixels // 2,
            cell_pixels, cell_pixels
        )

        # Draw cell name
        painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(10, 20, self._cell_name)

        # Draw diameter
        painter.setFont(QFont("Arial", 10))
        painter.drawText(10, 40, f"Diameter: {self._diameter} μm")

        painter.end()


class CellInfoPanel(QWidget):
    """Panel displaying detailed cell information."""

    cell_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cell = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the info panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        self.header_label = QLabel("No Cell Selected")
        self.header_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {ThemeColors.ACCENT};
            padding: 5px;
        """)
        layout.addWidget(self.header_label)

        # Type/tissue indicator
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

        # Size tab
        self.size_widget = self._create_size_tab()
        self.tabs.addTab(self.size_widget, "Size")

        # Metabolism tab
        self.metabolism_widget = self._create_metabolism_tab()
        self.tabs.addTab(self.metabolism_widget, "Metabolism")

        # Components tab
        self.components_widget = self._create_components_tab()
        self.tabs.addTab(self.components_widget, "Components")

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
            ("Organism", "organism"),
            ("Tissue", "tissue"),
            ("Diameter", "diameter"),
            ("Volume", "volume"),
            ("Mass", "mass"),
            ("Lifespan", "lifespan"),
            ("Nucleus", "nucleus"),
            ("Mitochondria", "mitochondria"),
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

    def _create_size_tab(self):
        """Create size visualization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.size_visual = CellSizeWidget()
        layout.addWidget(self.size_visual)

        # Additional size info
        self.size_details = QLabel()
        self.size_details.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        self.size_details.setWordWrap(True)
        layout.addWidget(self.size_details)

        layout.addStretch()
        return widget

    def _create_metabolism_tab(self):
        """Create metabolism visualization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.metabolic_visual = MetabolicWidget()
        layout.addWidget(self.metabolic_visual)

        # Additional metabolic info
        self.metabolic_details = QTextEdit()
        self.metabolic_details.setReadOnly(True)
        self.metabolic_details.setMaximumHeight(150)
        self.metabolic_details.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColors.BG_MEDIUM};
                color: {ThemeColors.TEXT_PRIMARY};
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.metabolic_details)

        return widget

    def _create_components_tab(self):
        """Create components/organelles tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Components tree
        self.components_tree = QTreeWidget()
        self.components_tree.setHeaderLabels(["Component", "Count/Value"])
        self.components_tree.setStyleSheet(f"""
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
        layout.addWidget(self.components_tree)

        return widget

    def _create_function_tab(self):
        """Create function/description tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {ThemeColors.BG_DARK}; border: none;")

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Function
        func_label = QLabel("Function")
        func_label.setStyleSheet(f"""
            color: {ThemeColors.TEXT_PRIMARY};
            font-weight: bold;
            font-size: 14px;
        """)
        layout.addWidget(func_label)

        self.function_text = QLabel()
        self.function_text.setWordWrap(True)
        self.function_text.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        layout.addWidget(self.function_text)

        # Description
        desc_label = QLabel("Description")
        desc_label.setStyleSheet(f"""
            color: {ThemeColors.TEXT_PRIMARY};
            font-weight: bold;
            font-size: 14px;
            margin-top: 15px;
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

        # Key proteins
        proteins_label = QLabel("Key Proteins")
        proteins_label.setStyleSheet(f"""
            color: {ThemeColors.TEXT_PRIMARY};
            font-weight: bold;
            font-size: 14px;
            margin-top: 15px;
        """)
        layout.addWidget(proteins_label)

        self.proteins_text = QLabel()
        self.proteins_text.setWordWrap(True)
        self.proteins_text.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        layout.addWidget(self.proteins_text)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def set_cell(self, cell_data):
        """Set and display cell data."""
        self._cell = cell_data

        if not cell_data:
            self.header_label.setText("No Cell Selected")
            self.type_label.setText("")
            return

        # Header
        name = cell_data.get('name', 'Unknown')
        self.header_label.setText(name)

        # Type/tissue line
        cell_type = cell_data.get('type', 'unknown').replace('_', ' ').title()
        tissue = cell_data.get('tissue', 'unknown').replace('_', ' ').title()
        self.type_label.setText(f"{cell_type} • {tissue}")

        # Properties
        self._update_property("type", cell_type)
        self._update_property("organism", cell_data.get('organism', '-'))
        self._update_property("tissue", tissue)

        diameter = cell_data.get('diameter_um', 0)
        self._update_property("diameter", f"{diameter} μm")

        volume = cell_data.get('volume_fL', 0)
        self._update_property("volume", f"{volume:.1f} fL")

        mass = cell_data.get('mass_pg', 0)
        self._update_property("mass", f"{mass:.1f} pg")

        lifespan = cell_data.get('lifespan_days', 0)
        if lifespan == -1:
            self._update_property("lifespan", "Lifetime")
        elif lifespan > 365:
            self._update_property("lifespan", f"~{lifespan/365:.1f} years")
        else:
            self._update_property("lifespan", f"{lifespan} days")

        nucleus = cell_data.get('nucleus', True)
        self._update_property("nucleus", "Yes" if nucleus else "No")

        mito = cell_data.get('mitochondria_count', 0)
        self._update_property("mitochondria", str(mito))

        # Size visualization
        self.size_visual.set_data(diameter, name.split("(")[0].strip())

        surface_area = cell_data.get('surface_area_um2', 0)
        sa_v_ratio = cell_data.get('surface_volume_ratio', 0)
        self.size_details.setText(
            f"Surface Area: {surface_area:.1f} μm²\n"
            f"Surface/Volume Ratio: {sa_v_ratio:.4f} /μm"
        )

        # Metabolism visualization
        metabolic_rate = cell_data.get('metabolic_rate_fW', 0)
        atp_turnover = cell_data.get('atp_turnover_per_s', 0)
        o2_consumption = cell_data.get('o2_consumption_per_s', 0)
        self.metabolic_visual.set_data(metabolic_rate, atp_turnover, o2_consumption)

        doubling_time = cell_data.get('estimated_doubling_time_hours', 0)
        metabolic_text = f"Estimated Doubling Time: {doubling_time:.1f} hours\n\n"

        derived = cell_data.get('derived_properties', {})
        if derived:
            scaling = derived.get('metabolic_scaling', {})
            metabolic_text += f"Scaling Law: {scaling.get('law', 'Unknown')}\n"
            metabolic_text += f"Equation: {scaling.get('equation', '')}\n"
        self.metabolic_details.setText(metabolic_text)

        # Components tree
        self.components_tree.clear()

        # Add organelles
        organelles_item = QTreeWidgetItem(["Organelles", ""])
        if mito > 0:
            QTreeWidgetItem(organelles_item, ["Mitochondria", str(mito)])
        if nucleus:
            nuclei = cell_data.get('nuclei_count', 1)
            QTreeWidgetItem(organelles_item, ["Nucleus", str(nuclei)])

        organelles = cell_data.get('organelles', {})
        for org_name, org_value in organelles.items():
            QTreeWidgetItem(organelles_item, [org_name.replace('_', ' ').title(), str(org_value)])

        if organelles_item.childCount() > 0:
            self.components_tree.addTopLevelItem(organelles_item)
            organelles_item.setExpanded(True)

        # Add membrane composition
        membrane = cell_data.get('membrane_composition', {})
        if membrane:
            membrane_item = QTreeWidgetItem(["Membrane Composition", ""])
            for comp, value in membrane.items():
                QTreeWidgetItem(membrane_item, [comp.replace('_', ' ').title(), f"{value*100:.0f}%"])
            self.components_tree.addTopLevelItem(membrane_item)
            membrane_item.setExpanded(True)

        # Function
        func = cell_data.get('function', 'Unknown')
        self.function_text.setText(func)

        # Description
        desc = cell_data.get('description', 'No description available.')
        self.description_text.setText(desc)

        # Key proteins
        proteins = cell_data.get('key_proteins', [])
        if proteins:
            self.proteins_text.setText(", ".join(proteins))
        else:
            self.proteins_text.setText("Not specified")

    def _update_property(self, key, value):
        """Update a property label."""
        if key in self.property_labels:
            self.property_labels[key].setText(str(value))

    def get_current_cell(self):
        """Get currently displayed cell data."""
        return self._cell
