"""
Material Info Panel
Displays detailed information about selected engineering materials.
"""

import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                                QTabWidget, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient

from periodica.core.material_enums import MaterialCategory, MaterialProperty


class PropertyBarChart(QFrame):
    """Widget to display material properties as horizontal bar chart"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.material = None
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 45, 200);
                border: 2px solid #667eea;
                border-radius: 12px;
            }
        """)

    def set_material(self, material):
        """Set material to display"""
        self.material = material
        self.update()

    def paintEvent(self, event):
        """Paint the bar chart"""
        super().paintEvent(event)
        if not self.material:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Properties to display with their max typical values
        properties = [
            ('Yield Strength', 'StrengthProperties', 'YieldStrength_MPa', 1500),
            ('UTS', 'StrengthProperties', 'UltimateTensileStrength_MPa', 2000),
            ("Young's Modulus", 'ElasticProperties', 'YoungsModulus_GPa', 400),
            ('Hardness (HV)', 'Hardness', 'Vickers_HV', 1500),
            ('Elongation (%)', 'Ductility', 'Elongation_percent', 100),
            ('Fracture Tough.', 'FractureMechanics', 'FractureToughness_KIC_MPa_sqrt_m', 200),
        ]

        margin = 15
        bar_height = 22
        label_width = 100
        y = margin

        # Title
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(margin, y + 12, "Mechanical Properties")
        y += 25

        value_font = QFont("Segoe UI", 8)
        for name, section, key, max_val in properties:
            section_data = self.material.get(section, {})
            value = section_data.get(key, 0)
            if isinstance(value, dict):
                value = list(value.values())[0] if value else 0

            # Draw label
            painter.setFont(value_font)
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(margin, int(y + bar_height * 0.7), name)

            # Draw bar background
            bar_x = margin + label_width
            bar_width = self.width() - bar_x - margin - 50
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(50, 50, 70))
            painter.drawRoundedRect(QRectF(bar_x, y, bar_width, bar_height - 4), 3, 3)

            # Draw bar fill
            fill_width = min(value / max_val, 1.0) * bar_width if max_val > 0 else 0
            gradient = QLinearGradient(bar_x, y, bar_x + fill_width, y)
            gradient.setColorAt(0, QColor("#667eea"))
            gradient.setColorAt(1, QColor("#764ba2"))
            painter.setBrush(gradient)
            painter.drawRoundedRect(QRectF(bar_x, y, fill_width, bar_height - 4), 3, 3)

            # Draw value
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(int(bar_x + bar_width + 5), int(y + bar_height * 0.7), f"{value:.0f}")

            y += bar_height + 5

        painter.end()


class ThermalPropertiesWidget(QFrame):
    """Widget to display thermal properties"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.material = None
        self.setMinimumHeight(150)
        self.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 45, 200);
                border: 2px solid #ff6b6b;
                border-radius: 12px;
            }
        """)

    def set_material(self, material):
        self.material = material
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.material:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        thermal = self.material.get('ThermalProperties', {})
        margin = 15
        y = margin

        # Title
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(255, 150, 150))
        painter.drawText(margin, y + 12, "Thermal Properties")
        y += 30

        # Properties
        props = [
            ('Melting Point', thermal.get('MeltingPoint_K', 0), 'K'),
            ('Thermal Conductivity', self._get_value(thermal.get('ThermalConductivity_W_mK', 0)), 'W/m·K'),
            ('Specific Heat', self._get_value(thermal.get('SpecificHeat_J_kgK', 0)), 'J/kg·K'),
            ('Thermal Expansion', thermal.get('ThermalExpansion_per_K', 0) * 1e6, 'µm/m·K'),
        ]

        value_font = QFont("Segoe UI", 9)
        painter.setFont(value_font)
        for name, value, unit in props:
            painter.setPen(QColor(180, 180, 200))
            painter.drawText(margin, int(y), f"{name}:")
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(int(self.width() / 2), int(y), f"{value:.2f} {unit}")
            y += 22

        painter.end()

    def _get_value(self, val):
        """Extract value from dict or return as-is"""
        if isinstance(val, dict):
            return list(val.values())[0] if val else 0
        return val if val else 0


class MaterialInfoPanel(QWidget):
    """Panel displaying detailed material information"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.material = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the info panel UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header
        self.header = QLabel("Select a material")
        self.header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.header.setStyleSheet("color: white;")
        self.header.setWordWrap(True)
        main_layout.addWidget(self.header)

        # Category and standard
        self.category_label = QLabel("")
        self.category_label.setStyleSheet("color: #aaa; font-size: 11px;")
        main_layout.addWidget(self.category_label)

        # Description
        self.description_label = QLabel("")
        self.description_label.setStyleSheet("color: #ccc; font-size: 10px;")
        self.description_label.setWordWrap(True)
        main_layout.addWidget(self.description_label)

        # Tab widget for different property views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #667eea;
                border-radius: 8px;
                background: rgba(30, 30, 50, 150);
            }
            QTabBar::tab {
                background: rgba(40, 40, 60, 200);
                color: white;
                padding: 8px 15px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #667eea;
            }
        """)

        # Mechanical tab
        mechanical_tab = QWidget()
        mechanical_layout = QVBoxLayout(mechanical_tab)
        self.bar_chart = PropertyBarChart()
        mechanical_layout.addWidget(self.bar_chart)
        mechanical_layout.addStretch()
        self.tabs.addTab(mechanical_tab, "Mechanical")

        # Thermal tab
        thermal_tab = QWidget()
        thermal_layout = QVBoxLayout(thermal_tab)
        self.thermal_widget = ThermalPropertiesWidget()
        thermal_layout.addWidget(self.thermal_widget)
        thermal_layout.addStretch()
        self.tabs.addTab(thermal_tab, "Thermal")

        # FEA Parameters tab
        fea_tab = self._create_fea_tab()
        self.tabs.addTab(fea_tab, "FEA/CFD")

        # Service Conditions tab
        service_tab = self._create_service_tab()
        self.tabs.addTab(service_tab, "Service")

        main_layout.addWidget(self.tabs)

        # Applications
        self.apps_label = QLabel("")
        self.apps_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self.apps_label.setWordWrap(True)
        main_layout.addWidget(self.apps_label)

    def _create_fea_tab(self):
        """Create FEA/CFD parameters tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.fea_labels = {}
        params = [
            'Mesh Size (mm)', 'Stress Model', 'Tangent Modulus (GPa)',
            'Damage Model', 'Surface Roughness (µm)'
        ]
        for param in params:
            row = QHBoxLayout()
            label = QLabel(f"{param}:")
            label.setStyleSheet("color: #aaa;")
            value = QLabel("-")
            value.setStyleSheet("color: white;")
            self.fea_labels[param] = value
            row.addWidget(label)
            row.addWidget(value)
            row.addStretch()
            layout.addLayout(row)

        layout.addStretch()
        return tab

    def _create_service_tab(self):
        """Create service conditions tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.service_labels = {}
        params = [
            'Min Temp (K)', 'Max Temp (K)', 'Corrosion Resistance',
            'Safety Factor', 'Max Von Mises (MPa)'
        ]
        for param in params:
            row = QHBoxLayout()
            label = QLabel(f"{param}:")
            label.setStyleSheet("color: #aaa;")
            value = QLabel("-")
            value.setStyleSheet("color: white;")
            self.service_labels[param] = value
            row.addWidget(label)
            row.addWidget(value)
            row.addStretch()
            layout.addLayout(row)

        layout.addStretch()
        return tab

    def set_material(self, material):
        """Set material to display"""
        self.material = material
        if not material:
            self.header.setText("Select a material")
            self.category_label.setText("")
            self.description_label.setText("")
            self.apps_label.setText("")
            return

        # Update header
        name = material.get('Name', 'Unknown')
        self.header.setText(name)

        # Update category
        category = material.get('Category', 'Unknown')
        standard = material.get('Standard', '')
        self.category_label.setText(f"{category} | {standard}" if standard else category)

        # Update description
        desc = material.get('Description', '')
        self.description_label.setText(desc)

        # Update charts
        self.bar_chart.set_material(material)
        self.thermal_widget.set_material(material)

        # Update FEA tab
        sim = material.get('SimulationParameters', {}).get('FEA', {})
        cfd = material.get('SimulationParameters', {}).get('CFD', {})
        self.fea_labels['Mesh Size (mm)'].setText(str(sim.get('RecommendedMeshSize_mm', '-')))
        self.fea_labels['Stress Model'].setText(sim.get('StressStrainModel', '-'))
        self.fea_labels['Tangent Modulus (GPa)'].setText(str(sim.get('TangentModulus_GPa', '-')))
        self.fea_labels['Damage Model'].setText(sim.get('DamageModel', '-'))
        self.fea_labels['Surface Roughness (µm)'].setText(str(cfd.get('SurfaceRoughness_um', '-')))

        # Update service tab
        service = material.get('ServiceConditions', {})
        failure = material.get('FailureCriteria', {})
        self.service_labels['Min Temp (K)'].setText(str(service.get('MinServiceTemperature_K', '-')))
        self.service_labels['Max Temp (K)'].setText(str(service.get('MaxServiceTemperature_K', '-')))
        self.service_labels['Corrosion Resistance'].setText(service.get('CorrosionResistance', '-'))
        self.service_labels['Safety Factor'].setText(str(service.get('SafetyFactor_recommended', '-')))
        self.service_labels['Max Von Mises (MPa)'].setText(str(failure.get('VonMisesStress_MPa', '-')))

        # Update applications
        apps = material.get('Applications', [])
        if apps:
            self.apps_label.setText(f"Applications: {', '.join(apps)}")
        else:
            self.apps_label.setText("")
