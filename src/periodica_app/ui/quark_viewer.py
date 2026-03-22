#====== Playtow/PeriodicTable2/ui/quark_viewer.py ======#
#!copyright (c) 2025 Andrew Keith Watts. All rights reserved.
#!
#!This is the intellectual property of Andrew Keith Watts. Unauthorized
#!reproduction, distribution, or modification of this code, in whole or in part,
#!without the express written permission of Andrew Keith Watts is strictly prohibited.
#!
#!For inquiries, please contact AndrewKWatts@Gmail.com

"""
Quark Viewer Widget
Displays standard model particles from JSON files in the Quarks folder
"""

import json
import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QCheckBox, QScrollArea, QGridLayout, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class QuarkCard(QFrame):
    """Individual card widget for displaying a quark/particle"""
    def __init__(self, particle_data):
        super().__init__()
        self.particle_data = particle_data
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(60, 60, 80, 200), stop:1 rgba(40, 40, 60, 200));
                border: 2px solid rgba(102, 126, 234, 150);
                border-radius: 10px;
                padding: 10px;
            }
            QFrame:hover {
                border: 2px solid rgba(102, 126, 234, 255);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(70, 70, 90, 220), stop:1 rgba(50, 50, 70, 220));
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Name
        name = self.particle_data.get('Name', 'Unknown')
        name_label = QLabel(name)
        name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #4fc3f7; background: transparent; border: none;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # Symbol
        symbol = self.particle_data.get('Symbol', '')
        if symbol:
            symbol_label = QLabel(symbol)
            symbol_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            symbol_label.setStyleSheet("color: white; background: transparent; border: none;")
            symbol_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(symbol_label)

        # Classification
        classification = self.particle_data.get('Classification', [])
        if classification:
            class_text = ", ".join(classification[:2])  # Show first 2 classifications
            class_label = QLabel(class_text)
            class_label.setFont(QFont("Arial", 9))
            class_label.setStyleSheet("color: rgba(255,255,255,180); background: transparent; border: none;")
            class_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            class_label.setWordWrap(True)
            layout.addWidget(class_label)

        # Key properties
        props_layout = QVBoxLayout()
        props_layout.setSpacing(3)

        # Charge
        charge = self.particle_data.get('Charge_e')
        if charge is not None:
            charge_label = QLabel(f"Charge: {charge:+.2f} e")
            charge_label.setFont(QFont("Arial", 9))
            charge_label.setStyleSheet("color: rgba(255,255,255,200); background: transparent; border: none;")
            props_layout.addWidget(charge_label)

        # Mass
        mass = self.particle_data.get('Mass_MeVc2')
        if mass is not None:
            if mass < 0.001:
                mass_label = QLabel(f"Mass: {mass:.2e} MeV/c²")
            elif mass < 1:
                mass_label = QLabel(f"Mass: {mass:.4f} MeV/c²")
            else:
                mass_label = QLabel(f"Mass: {mass:.2f} MeV/c²")
            mass_label.setFont(QFont("Arial", 9))
            mass_label.setStyleSheet("color: rgba(255,255,255,200); background: transparent; border: none;")
            props_layout.addWidget(mass_label)

        # Spin
        spin = self.particle_data.get('Spin_hbar')
        if spin is not None:
            spin_label = QLabel(f"Spin: {spin} ℏ")
            spin_label.setFont(QFont("Arial", 9))
            spin_label.setStyleSheet("color: rgba(255,255,255,200); background: transparent; border: none;")
            props_layout.addWidget(spin_label)

        layout.addLayout(props_layout)
        layout.addStretch()


class QuarkViewer(QWidget):
    """Main quark viewer widget with grid of particle cards"""
    def __init__(self):
        super().__init__()
        self.quarks_data = []
        self.antiquarks_data = []
        self.show_antiquarks = False
        self.load_data()
        self.setup_ui()

    def load_data(self):
        """Load quark and antiquark data from JSON files"""
        # Get the base directory (PeriodicTable2)
        base_dir = Path(__file__).parent.parent

        # Load quarks from Quarks folder
        quarks_dir = base_dir / "Quarks"
        if quarks_dir.exists():
            for json_file in quarks_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Only include standard model particles
                        classification = data.get('Classification', [])
                        if any(c in classification for c in ['Quark', 'Lepton', 'Boson', 'Fundamental Particle']):
                            self.quarks_data.append(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        # Load antiquarks from AntiQuarks folder
        antiquarks_dir = base_dir / "AntiQuarks"
        if antiquarks_dir.exists():
            for json_file in antiquarks_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.antiquarks_data.append(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        # Sort by mass
        self.quarks_data.sort(key=lambda x: x.get('Mass_MeVc2', 0))
        self.antiquarks_data.sort(key=lambda x: x.get('Mass_MeVc2', 0))

    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Standard Model Particles")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Antiquark checkbox
        self.antiquark_checkbox = QCheckBox("Show Antiparticles")
        self.antiquark_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                spacing: 8px;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #667eea;
                border-radius: 4px;
                background: rgba(40, 40, 60, 200);
            }
            QCheckBox::indicator:checked {
                background: #667eea;
            }
        """)
        self.antiquark_checkbox.toggled.connect(self.on_antiquark_toggled)
        header_layout.addWidget(self.antiquark_checkbox)

        main_layout.addLayout(header_layout)

        # Particle count info
        self.count_label = QLabel(f"Showing {len(self.quarks_data)} standard model particles")
        self.count_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 10px;")
        main_layout.addWidget(self.count_label)

        # Scroll area for particle cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(40, 40, 60, 100);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(79, 195, 247, 150);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Container for grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)

        scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(scroll_area)

        # Populate grid
        self.populate_grid()

    def populate_grid(self):
        """Populate the grid with particle cards"""
        # Clear existing cards
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Determine which data to show
        data_to_show = self.quarks_data.copy()
        if self.show_antiquarks:
            data_to_show.extend(self.antiquarks_data)

        # Update count label
        self.count_label.setText(
            f"Showing {len(data_to_show)} particles "
            f"({len(self.quarks_data)} standard model + {len(self.antiquarks_data) if self.show_antiquarks else 0} antiparticles)"
        )

        # Add cards to grid (4 columns)
        cols = 4
        for i, particle_data in enumerate(data_to_show):
            card = QuarkCard(particle_data)
            card.setMinimumSize(200, 200)
            card.setMaximumSize(250, 250)
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)

        # Add stretch to push cards to top-left
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
        self.grid_layout.setColumnStretch(cols, 1)

    def on_antiquark_toggled(self, checked):
        """Handle antiquark checkbox toggle"""
        self.show_antiquarks = checked
        self.populate_grid()
