"""
Biomaterial Info Panel
Displays detailed information about a selected biological material including
composition, mechanical properties, and physiological characteristics.
"""

import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QScrollArea, QFrame, QGridLayout, QGroupBox,
                                QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.biomaterial_enums import BiomaterialType, ECMComponent


class CompositionBarWidget(QWidget):
    """Widget to display ECM composition as stacked bar chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._composition = {}
        self.setMinimumHeight(100)

    def set_composition(self, composition):
        """Set composition data {component: fraction}."""
        self._composition = composition
        self.update()

    def paintEvent(self, event):
        """Paint composition bar chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        if not self._composition:
            painter.setPen(QColor(ThemeColors.TEXT_SECONDARY))
            painter.drawText(10, 30, "No composition data")
            painter.end()
            return

        w = self.width()
        h = self.height()
        bar_height = 30
        bar_y = 30

        # Sort by value
        sorted_comp = sorted(self._composition.items(), key=lambda x: x[1], reverse=True)
        total = sum(v for _, v in sorted_comp)

        if total == 0:
            painter.end()
            return

        # Draw stacked bar
        x = 20
        bar_width = w - 40

        for comp, value in sorted_comp:
            comp_width = int(bar_width * value / total)
            if comp_width < 2:
                continue

            color = QColor(ECMComponent.get_color(comp))
            painter.fillRect(x, bar_y, comp_width, bar_height, color)

            x += comp_width

        # Draw legend below
        x = 20
        y = bar_y + bar_height + 15
        painter.setFont(QFont("Arial", 8))

        for comp, value in sorted_comp[:6]:  # Show top 6
            if value < 0.01:
                continue

            color = QColor(ECMComponent.get_color(comp))
            painter.fillRect(x, y, 10, 10, color)

            painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
            name = comp.replace('_', ' ').title()
            if len(name) > 12:
                name = name[:10] + ".."
            painter.drawText(x + 14, y + 9, f"{name}: {value*100:.0f}%")

            x += 90
            if x > w - 100:
                x = 20
                y += 15

        painter.end()


class StiffnessScaleWidget(QWidget):
    """Widget to display stiffness on a log scale."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._modulus = 0
        self._name = ""
        self.setMinimumHeight(80)

    def set_data(self, modulus, name):
        """Set modulus data."""
        self._modulus = modulus
        self._name = name
        self.update()

    def paintEvent(self, event):
        """Paint stiffness scale."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(ThemeColors.BG_MEDIUM))

        w = self.width()
        h = self.height()

        # Draw scale bar (log scale from 0.001 to 100000 MPa)
        scale_y = 40
        scale_start = 30
        scale_width = w - 60

        # Background gradient
        gradient_start = QColor("#4CAF50")  # Soft
        gradient_end = QColor("#9C27B0")    # Hard
        for i in range(scale_width):
            t = i / scale_width
            r = int(gradient_start.red() * (1-t) + gradient_end.red() * t)
            g = int(gradient_start.green() * (1-t) + gradient_end.green() * t)
            b = int(gradient_start.blue() * (1-t) + gradient_end.blue() * t)
            painter.setPen(QColor(r, g, b))
            painter.drawLine(scale_start + i, scale_y, scale_start + i, scale_y + 15)

        # Scale markers
        painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
        painter.setFont(QFont("Arial", 8))
        markers = [0.001, 0.1, 1, 10, 100, 1000, 10000, 100000]
        for E in markers:
            x = scale_start + int(scale_width * (math.log10(E) + 3) / 8)  # -3 to 5 log scale
            painter.drawLine(x, scale_y - 3, x, scale_y + 18)
            if E >= 1000:
                label = f"{E/1000:.0f}GPa"
            elif E >= 1:
                label = f"{E:.0f}"
            else:
                label = f"{E*1000:.0f}kPa"
            painter.drawText(x - 15, scale_y + 30, label)

        # Draw marker for current material
        if self._modulus > 0:
            pos = scale_start + int(scale_width * (math.log10(self._modulus) + 3) / 8)
            painter.setBrush(QBrush(QColor(ThemeColors.ACCENT)))
            painter.setPen(QPen(QColor(ThemeColors.ACCENT), 2))
            painter.drawPolygon([
                (pos, scale_y - 5),
                (pos - 5, scale_y - 15),
                (pos + 5, scale_y - 15)
            ])

            # Label
            painter.setPen(QColor(ThemeColors.TEXT_PRIMARY))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            if self._modulus >= 1000:
                E_str = f"E = {self._modulus/1000:.2f} GPa"
            elif self._modulus >= 1:
                E_str = f"E = {self._modulus:.2f} MPa"
            else:
                E_str = f"E = {self._modulus*1000:.2f} kPa"
            painter.drawText(10, h - 5, E_str)

        painter.end()


class BiomaterialInfoPanel(QWidget):
    """Panel displaying detailed biomaterial information."""

    biomaterial_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._material = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the info panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        self.header_label = QLabel("No Material Selected")
        self.header_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {ThemeColors.ACCENT};
            padding: 5px;
        """)
        layout.addWidget(self.header_label)

        # Type indicator
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

        # Mechanical tab
        self.mechanical_widget = self._create_mechanical_tab()
        self.tabs.addTab(self.mechanical_widget, "Mechanical")

        # Composition tab
        self.composition_widget = self._create_composition_tab()
        self.tabs.addTab(self.composition_widget, "Composition")

        # Cells tab
        self.cells_widget = self._create_cells_tab()
        self.tabs.addTab(self.cells_widget, "Cells")

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
            ("Organ System", "organ_system"),
            ("Density", "density"),
            ("Water Content", "water_content"),
            ("Porosity", "porosity"),
            ("Vascularization", "vascularization"),
            ("Innervation", "innervation"),
            ("Healing Time", "healing_time"),
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

    def _create_mechanical_tab(self):
        """Create mechanical properties tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Stiffness scale
        self.stiffness_scale = StiffnessScaleWidget()
        layout.addWidget(self.stiffness_scale)

        # Mechanical properties grid
        mech_grid = QGridLayout()
        self.mech_labels = {}

        mech_props = [
            ("Young's Modulus", "youngs_modulus"),
            ("Ultimate Strength", "ultimate_strength"),
            ("Poisson's Ratio", "poissons_ratio"),
            ("Shear Modulus", "shear_modulus"),
            ("Stiffness Category", "stiffness_category"),
        ]

        for i, (label_text, key) in enumerate(mech_props):
            label = QLabel(f"{label_text}:")
            label.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-weight: bold;")
            mech_grid.addWidget(label, i, 0)

            value_label = QLabel("-")
            value_label.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
            mech_grid.addWidget(value_label, i, 1)
            self.mech_labels[key] = value_label

        layout.addLayout(mech_grid)

        # Model info
        self.model_label = QLabel()
        self.model_label.setWordWrap(True)
        self.model_label.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-size: 10px;")
        layout.addWidget(self.model_label)

        layout.addStretch()
        return widget

    def _create_composition_tab(self):
        """Create composition visualization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Composition bar
        self.composition_bar = CompositionBarWidget()
        layout.addWidget(self.composition_bar)

        # Composition tree
        self.composition_tree = QTreeWidget()
        self.composition_tree.setHeaderLabels(["Component", "Fraction", "Modulus (MPa)"])
        self.composition_tree.setStyleSheet(f"""
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
        layout.addWidget(self.composition_tree)

        return widget

    def _create_cells_tab(self):
        """Create cells composition tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Cell composition tree
        self.cells_tree = QTreeWidget()
        self.cells_tree.setHeaderLabels(["Cell Type", "Fraction"])
        self.cells_tree.setStyleSheet(f"""
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
        layout.addWidget(self.cells_tree)

        # Summary
        self.cells_summary = QLabel()
        self.cells_summary.setWordWrap(True)
        self.cells_summary.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY};")
        layout.addWidget(self.cells_summary)

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

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def set_material(self, mat_data):
        """Set and display material data."""
        self._material = mat_data

        if not mat_data:
            self.header_label.setText("No Material Selected")
            self.type_label.setText("")
            return

        # Header
        name = mat_data.get('name', 'Unknown')
        self.header_label.setText(name)

        # Type line
        mat_type = mat_data.get('type', 'unknown').replace('_', ' ').title()
        organ_system = mat_data.get('organ_system', 'unknown').replace('_', ' ').title()
        self.type_label.setText(f"{mat_type} • {organ_system}")

        # Properties
        self._update_property("type", mat_type)
        self._update_property("organ_system", organ_system)

        phys = mat_data.get('physical_properties', {})
        self._update_property("density", f"{phys.get('density_g_cm3', 0):.3f} g/cm³")
        self._update_property("water_content", f"{phys.get('water_content_percent', 0):.1f}%")
        self._update_property("porosity", f"{mat_data.get('porosity', 0):.1f}%")
        self._update_property("vascularization", mat_data.get('vascularization', '-').replace('_', ' ').title())
        self._update_property("innervation", "Yes" if mat_data.get('innervation', False) else "No")
        healing = mat_data.get('healing_time_weeks', 0)
        self._update_property("healing_time", f"~{healing} weeks" if healing else "-")

        # Mechanical properties
        mech = mat_data.get('mechanical_properties', {})
        E = mech.get('youngs_modulus_MPa', 0)

        self.stiffness_scale.set_data(E, name)

        if E >= 1000:
            self._update_mech("youngs_modulus", f"{E/1000:.2f} GPa")
        elif E >= 1:
            self._update_mech("youngs_modulus", f"{E:.2f} MPa")
        else:
            self._update_mech("youngs_modulus", f"{E*1000:.2f} kPa")

        UTS = mech.get('ultimate_strength_MPa', 0)
        self._update_mech("ultimate_strength", f"{UTS:.2f} MPa")
        self._update_mech("poissons_ratio", f"{mech.get('poissons_ratio', 0):.3f}")

        G = mech.get('shear_modulus_MPa', 0)
        if G >= 1000:
            self._update_mech("shear_modulus", f"{G/1000:.2f} GPa")
        else:
            self._update_mech("shear_modulus", f"{G:.2f} MPa")

        derived = mat_data.get('derived_properties', {})
        self._update_mech("stiffness_category", derived.get('stiffness_category', '-'))
        self.model_label.setText(f"Model: {derived.get('model_used', 'Unknown')}")

        # Composition
        ecm = mat_data.get('ecm_composition', {})
        self.composition_bar.set_composition(ecm)

        self.composition_tree.clear()
        ecm_moduli = {
            'collagen_i': 1000, 'collagen_ii': 800, 'collagen_iii': 600,
            'elastin': 0.6, 'hydroxyapatite': 117000, 'water': 0,
            'proteoglycans': 0.01, 'hyaluronan': 0.001
        }
        for comp, frac in sorted(ecm.items(), key=lambda x: x[1], reverse=True):
            mod = ecm_moduli.get(comp.lower(), 1)
            item = QTreeWidgetItem([
                comp.replace('_', ' ').title(),
                f"{frac*100:.1f}%",
                str(mod) if mod >= 1 else f"{mod*1000:.1f}kPa"
            ])
            self.composition_tree.addTopLevelItem(item)

        # Cells
        cells = mat_data.get('cell_composition', {})
        self.cells_tree.clear()
        total_cells = sum(cells.values())
        for cell_type, frac in sorted(cells.items(), key=lambda x: x[1], reverse=True):
            item = QTreeWidgetItem([
                cell_type.replace('_', ' ').title(),
                f"{frac*100:.1f}%"
            ])
            self.cells_tree.addTopLevelItem(item)
        self.cells_summary.setText(f"Total cell fraction: {total_cells*100:.1f}%")

        # Function
        self.function_text.setText(mat_data.get('function', 'Unknown'))
        self.description_text.setText(mat_data.get('description', 'No description available.'))

    def _update_property(self, key, value):
        """Update a property label."""
        if key in self.property_labels:
            self.property_labels[key].setText(str(value))

    def _update_mech(self, key, value):
        """Update a mechanical property label."""
        if key in self.mech_labels:
            self.mech_labels[key].setText(str(value))

    def get_current_material(self):
        """Get currently displayed material data."""
        return self._material
