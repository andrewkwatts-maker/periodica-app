"""
Creation Dialogs
Dialogs for creating particles from constituent components.
- Atoms from protons/neutrons/electrons
- Subatomic particles from quarks
- Molecules from atoms
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSpinBox, QLineEdit, QGroupBox, QComboBox, QListWidget, QListWidgetItem,
    QTextEdit, QScrollArea, QWidget, QFrame, QMessageBox, QCheckBox,
    QDoubleSpinBox, QTabWidget, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

import json
from typing import Dict, List, Optional

from periodica.utils.physics_calculator import AtomCalculator, SubatomicCalculator, MoleculeCalculator
from periodica.data.data_manager import get_data_manager, DataCategory


class AtomCreationDialog(QDialog):
    """
    Dialog for creating atoms from protons, neutrons, and electrons.
    """
    atom_created = Signal(dict)  # Emitted when atom is created

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Atom from Subatomic Particles")
        self.setMinimumSize(700, 600)
        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Create New Atom")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        layout.addWidget(title)

        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Input
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Particle selection group
        particle_group = QGroupBox("Constituent Particles")
        particle_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        particle_layout = QGridLayout(particle_group)

        # Protons
        protons_label = QLabel("Protons (Z):")
        protons_label.setToolTip("Atomic number - defines the element identity")
        particle_layout.addWidget(protons_label, 0, 0)
        self.protons_spin = QSpinBox()
        self.protons_spin.setToolTip("Number of protons in the nucleus (1-118)")
        self.protons_spin.setRange(1, 118)
        self.protons_spin.setValue(1)
        self.protons_spin.valueChanged.connect(self.on_particle_changed)
        particle_layout.addWidget(self.protons_spin, 0, 1)

        # Neutrons
        neutrons_label = QLabel("Neutrons (N):")
        neutrons_label.setToolTip("Determines the isotope - affects atomic mass and stability")
        particle_layout.addWidget(neutrons_label, 1, 0)
        self.neutrons_spin = QSpinBox()
        self.neutrons_spin.setToolTip("Number of neutrons in the nucleus (0-200)")
        self.neutrons_spin.setRange(0, 200)
        self.neutrons_spin.setValue(0)
        self.neutrons_spin.valueChanged.connect(self.on_particle_changed)
        particle_layout.addWidget(self.neutrons_spin, 1, 1)

        # Electrons
        electrons_label = QLabel("Electrons:")
        electrons_label.setToolTip("Determines ionic charge - neutral when equal to protons")
        particle_layout.addWidget(electrons_label, 2, 0)
        self.electrons_spin = QSpinBox()
        self.electrons_spin.setToolTip("Number of electrons orbiting the nucleus (0-118)")
        self.electrons_spin.setRange(0, 118)
        self.electrons_spin.setValue(1)
        self.electrons_spin.valueChanged.connect(self.on_particle_changed)
        particle_layout.addWidget(self.electrons_spin, 2, 1)

        # Match electrons checkbox
        self.match_electrons = QCheckBox("Match electrons to protons (neutral)")
        self.match_electrons.setToolTip("Keep the atom electrically neutral by matching electrons to protons")
        self.match_electrons.setChecked(True)
        self.match_electrons.stateChanged.connect(self.on_match_electrons_changed)
        particle_layout.addWidget(self.match_electrons, 3, 0, 1, 2)

        left_layout.addWidget(particle_group)

        # Naming group
        name_group = QGroupBox("Element Identity")
        name_layout = QGridLayout(name_group)

        symbol_label = QLabel("Symbol:")
        symbol_label.setToolTip("1-3 letter element symbol (e.g., H, He, Li)")
        name_layout.addWidget(symbol_label, 0, 0)
        self.symbol_edit = QLineEdit()
        self.symbol_edit.setToolTip("Enter a unique element symbol (required)")
        self.symbol_edit.setMaxLength(3)
        self.symbol_edit.setPlaceholderText("e.g., H, He, Li")
        self.symbol_edit.textChanged.connect(self.update_preview)
        name_layout.addWidget(self.symbol_edit, 0, 1)

        name_label = QLabel("Name:")
        name_label.setToolTip("Full element name")
        name_layout.addWidget(name_label, 1, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("Enter the element's full name (required)")
        self.name_edit.setPlaceholderText("e.g., Hydrogen, Helium")
        self.name_edit.textChanged.connect(self.update_preview)
        name_layout.addWidget(self.name_edit, 1, 1)

        left_layout.addWidget(name_group)

        # Calculated properties summary
        props_group = QGroupBox("Calculated Properties")
        props_layout = QVBoxLayout(props_group)
        self.props_summary = QLabel()
        self.props_summary.setWordWrap(True)
        self.props_summary.setStyleSheet("color: #aaa; font-family: monospace;")
        props_layout.addWidget(self.props_summary)
        left_layout.addWidget(props_group)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Right panel - JSON Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        preview_label = QLabel("JSON Preview")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        right_layout.addWidget(preview_label)

        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                border: 1px solid #444;
                border-radius: 4px;
            }
        """)
        right_layout.addWidget(self.json_preview)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 400])

        layout.addWidget(splitter)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.create_btn = QPushButton("Create Atom")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.create_btn.clicked.connect(self.create_atom)
        btn_layout.addWidget(self.create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def on_match_electrons_changed(self, state):
        if state:
            self.electrons_spin.setValue(self.protons_spin.value())
            self.electrons_spin.setEnabled(False)
        else:
            self.electrons_spin.setEnabled(True)

    def on_particle_changed(self):
        if self.match_electrons.isChecked():
            self.electrons_spin.setValue(self.protons_spin.value())
        self.update_preview()

    def update_preview(self):
        protons = self.protons_spin.value()
        neutrons = self.neutrons_spin.value()
        electrons = self.electrons_spin.value()

        symbol = self.symbol_edit.text() or None
        name = self.name_edit.text() or None

        # Generate atom data
        atom_data = AtomCalculator.create_atom_from_particles(
            protons, neutrons, electrons, name, symbol
        )

        # Update properties summary
        block, period, group = AtomCalculator.get_block_period_group(protons)
        is_stable, half_life = AtomCalculator.determine_stability(protons, neutrons)

        summary = f"""
Atomic Number (Z): {protons}
Mass Number (A): {protons + neutrons}
Charge: {protons - electrons:+d}

Block: {block.upper()}-block
Period: {period}
Group: {group or 'N/A'}

Atomic Mass: {atom_data['atomic_mass']:.4f} u
Ionization Energy: {atom_data['ionization_energy']:.2f} eV
Electronegativity: {atom_data['electronegativity']:.2f}
Atomic Radius: {atom_data['atomic_radius']} pm

Stability: {'Stable' if is_stable else 'Unstable'}
{f'Half-life: {half_life}' if half_life else ''}
        """.strip()
        self.props_summary.setText(summary)

        # Update JSON preview
        json_str = json.dumps(atom_data, indent=2, ensure_ascii=False)
        self.json_preview.setPlainText(json_str)

        self._current_data = atom_data

    def create_atom(self):
        if not self.symbol_edit.text():
            QMessageBox.warning(self, "Missing Symbol", "Please enter an element symbol.")
            return

        if not self.name_edit.text():
            QMessageBox.warning(self, "Missing Name", "Please enter an element name.")
            return

        # Update data with user-provided name and symbol
        self._current_data['symbol'] = self.symbol_edit.text()
        self._current_data['name'] = self.name_edit.text()

        # Save to data manager
        manager = get_data_manager()
        z = self._current_data['atomic_number']
        filename = f"{z:03d}_{self._current_data['symbol']}"

        if manager.add_item(DataCategory.ELEMENTS, filename, self._current_data):
            self.atom_created.emit(self._current_data)
            QMessageBox.information(self, "Success", f"Atom '{self._current_data['name']}' created successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to create atom. It may already exist.")


class SubatomicCreationDialog(QDialog):
    """
    Dialog for creating subatomic particles from quarks.
    """
    particle_created = Signal(dict)

    AVAILABLE_QUARKS = [
        ('u', 'Up quark (+2/3)'),
        ('d', 'Down quark (-1/3)'),
        ('s', 'Strange quark (-1/3)'),
        ('c', 'Charm quark (+2/3)'),
        ('b', 'Bottom quark (-1/3)'),
        ('t', 'Top quark (+2/3)'),
        ('u̅', 'Anti-up (-2/3)'),
        ('d̅', 'Anti-down (+1/3)'),
        ('s̅', 'Anti-strange (+1/3)'),
        ('c̅', 'Anti-charm (-2/3)'),
        ('b̅', 'Anti-bottom (+1/3)'),
        ('t̅', 'Anti-top (-2/3)'),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Subatomic Particle from Quarks")
        self.setMinimumSize(800, 650)
        self.selected_quarks = []
        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Create Subatomic Particle from Quarks")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #ff9800;")
        layout.addWidget(title)

        # Info label
        info = QLabel("Select 3 quarks for a baryon (e.g., proton=uud) or 2 for a meson (quark + antiquark)")
        info.setStyleSheet("color: #888; font-style: italic;")
        info.setToolTip(
            "Baryons: 3 quarks (e.g., proton = uud, neutron = udd)\n"
            "Mesons: 1 quark + 1 antiquark (e.g., pion+ = u + anti-d)"
        )
        layout.addWidget(info)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Quark selection
        quark_group = QGroupBox("Select Quarks")
        quark_layout = QVBoxLayout(quark_group)

        # Available quarks
        available_label = QLabel("Available Quarks:")
        quark_layout.addWidget(available_label)

        self.quark_list = QListWidget()
        self.quark_list.setSelectionMode(QListWidget.MultiSelection)
        for symbol, name in self.AVAILABLE_QUARKS:
            item = QListWidgetItem(f"{symbol}  -  {name}")
            item.setData(Qt.UserRole, symbol)
            self.quark_list.addItem(item)
        self.quark_list.itemSelectionChanged.connect(self.on_quark_selection_changed)
        quark_layout.addWidget(self.quark_list)

        # Quick presets
        preset_label = QLabel("Quick Presets:")
        quark_layout.addWidget(preset_label)

        preset_layout = QHBoxLayout()
        presets = [
            ("Proton", ['u', 'u', 'd']),
            ("Neutron", ['u', 'd', 'd']),
            ("Pion+", ['u', 'd̅']),
            ("Pion-", ['d', 'u̅']),
        ]
        for name, quarks in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, q=quarks: self.set_quarks(q))
            preset_layout.addWidget(btn)
        quark_layout.addLayout(preset_layout)

        left_layout.addWidget(quark_group)

        # Selected quarks display
        selected_group = QGroupBox("Selected Quarks")
        selected_layout = QVBoxLayout(selected_group)
        self.selected_label = QLabel("None selected")
        self.selected_label.setStyleSheet("font-size: 16px; color: #4fc3f7;")
        selected_layout.addWidget(self.selected_label)

        clear_btn = QPushButton("Clear Selection")
        clear_btn.clicked.connect(self.clear_selection)
        selected_layout.addWidget(clear_btn)

        left_layout.addWidget(selected_group)

        # Naming
        name_group = QGroupBox("Particle Identity")
        name_layout = QGridLayout(name_group)

        symbol_label = QLabel("Symbol:")
        symbol_label.setToolTip("Standard particle symbol (e.g., p for proton)")
        name_layout.addWidget(symbol_label, 0, 0)
        self.symbol_edit = QLineEdit()
        self.symbol_edit.setToolTip("Enter the particle symbol (optional but recommended)")
        self.symbol_edit.setPlaceholderText("e.g., p, n, π⁺")
        self.symbol_edit.textChanged.connect(self.update_preview)
        name_layout.addWidget(self.symbol_edit, 0, 1)

        name_label = QLabel("Name:")
        name_label.setToolTip("Full particle name")
        name_layout.addWidget(name_label, 1, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("Enter the particle's full name (required)")
        self.name_edit.setPlaceholderText("e.g., Proton, Neutron")
        self.name_edit.textChanged.connect(self.update_preview)
        name_layout.addWidget(self.name_edit, 1, 1)

        # Spin alignment
        self.spin_aligned = QCheckBox("Spins aligned (higher spin state)")
        self.spin_aligned.setToolTip(
            "When checked, quark spins are aligned for a higher total spin.\n"
            "Example: Delta baryons have aligned spins (spin 3/2)"
        )
        self.spin_aligned.stateChanged.connect(self.update_preview)
        name_layout.addWidget(self.spin_aligned, 2, 0, 1, 2)

        left_layout.addWidget(name_group)

        # Properties summary
        props_group = QGroupBox("Calculated Properties")
        props_layout = QVBoxLayout(props_group)
        self.props_summary = QLabel("Select quarks to see properties")
        self.props_summary.setWordWrap(True)
        self.props_summary.setStyleSheet("color: #aaa; font-family: monospace;")
        props_layout.addWidget(self.props_summary)
        left_layout.addWidget(props_group)

        splitter.addWidget(left_panel)

        # Right panel - JSON preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        preview_label = QLabel("JSON Preview")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        right_layout.addWidget(preview_label)

        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        right_layout.addWidget(self.json_preview)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])

        layout.addWidget(splitter)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.create_btn = QPushButton("Create Particle")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        self.create_btn.clicked.connect(self.create_particle)
        self.create_btn.setEnabled(False)
        btn_layout.addWidget(self.create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def set_quarks(self, quarks: List[str]):
        """Set quarks from preset."""
        self.quark_list.clearSelection()
        for i in range(self.quark_list.count()):
            item = self.quark_list.item(i)
            if item.data(Qt.UserRole) in quarks:
                item.setSelected(True)
        self.selected_quarks = quarks.copy()
        self.update_preview()

    def clear_selection(self):
        self.quark_list.clearSelection()
        self.selected_quarks = []
        self.update_preview()

    def on_quark_selection_changed(self):
        self.selected_quarks = []
        for item in self.quark_list.selectedItems():
            self.selected_quarks.append(item.data(Qt.UserRole))
        self.update_preview()

    def update_preview(self):
        if not self.selected_quarks:
            self.selected_label.setText("None selected")
            self.props_summary.setText("Select quarks to see properties")
            self.json_preview.clear()
            self.create_btn.setEnabled(False)
            return

        self.selected_label.setText(" + ".join(self.selected_quarks))

        # Validate quark count
        valid = len(self.selected_quarks) in [2, 3]
        self.create_btn.setEnabled(valid and bool(self.name_edit.text()))

        if not valid:
            self.props_summary.setText("Select 2 quarks (meson) or 3 quarks (baryon)")
            self.json_preview.clear()
            return

        # Generate particle data
        symbol = self.symbol_edit.text() or None
        name = self.name_edit.text() or None
        spin_aligned = self.spin_aligned.isChecked()

        particle_data = SubatomicCalculator.create_particle_from_quarks(
            self.selected_quarks, name, symbol, spin_aligned
        )

        # Update summary
        charge = SubatomicCalculator.calculate_charge(self.selected_quarks)
        mass = SubatomicCalculator.calculate_mass(self.selected_quarks)
        spin = SubatomicCalculator.calculate_spin(self.selected_quarks, spin_aligned)
        baryon = SubatomicCalculator.calculate_baryon_number(self.selected_quarks)
        ptype = SubatomicCalculator.determine_particle_type(self.selected_quarks)
        stability, half_life = SubatomicCalculator.estimate_stability(self.selected_quarks)

        summary = f"""
Quark Composition: {' + '.join(self.selected_quarks)}
Particle Type: {ptype}

Charge: {charge:+.2f} e
Mass: {mass:.2f} MeV/c²
Spin: {spin}
Baryon Number: {baryon}

Stability: {stability}
{f'Half-life: {half_life}' if half_life else ''}

Interactions: {', '.join(SubatomicCalculator.get_interaction_forces(self.selected_quarks))}
        """.strip()
        self.props_summary.setText(summary)

        # Update JSON
        json_str = json.dumps(particle_data, indent=2, ensure_ascii=False)
        self.json_preview.setPlainText(json_str)

        self._current_data = particle_data

    def create_particle(self):
        if not self.name_edit.text():
            QMessageBox.warning(self, "Missing Name", "Please enter a particle name.")
            return

        self._current_data['Name'] = self.name_edit.text()
        if self.symbol_edit.text():
            self._current_data['Symbol'] = self.symbol_edit.text()

        manager = get_data_manager()
        filename = self.name_edit.text().replace(' ', '_')

        if manager.add_item(DataCategory.SUBATOMIC, filename, self._current_data):
            self.particle_created.emit(self._current_data)
            QMessageBox.information(self, "Success", f"Particle '{self._current_data['Name']}' created!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to create particle. It may already exist.")


class MoleculeCreationDialog(QDialog):
    """
    Dialog for creating molecules from atoms.
    """
    molecule_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Molecule from Atoms")
        self.setMinimumSize(800, 650)
        self.composition = []  # List of {"Element": symbol, "Count": n}
        self.atom_data = {}  # Cache of atom data
        self.setup_ui()
        self.load_available_atoms()
        self.update_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Create Molecule from Atoms")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #9c27b0;")
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Atom selection
        atom_group = QGroupBox("Add Atoms")
        atom_layout = QGridLayout(atom_group)

        element_label = QLabel("Element:")
        element_label.setToolTip("Select an element to add to the molecule")
        atom_layout.addWidget(element_label, 0, 0)
        self.atom_combo = QComboBox()
        self.atom_combo.setToolTip("Choose from available elements or type a symbol")
        self.atom_combo.setEditable(True)
        atom_layout.addWidget(self.atom_combo, 0, 1)

        count_label = QLabel("Count:")
        count_label.setToolTip("Number of atoms of this element in the molecule")
        atom_layout.addWidget(count_label, 1, 0)
        self.count_spin = QSpinBox()
        self.count_spin.setToolTip("How many atoms of this element to add (1-100)")
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(1)
        atom_layout.addWidget(self.count_spin, 1, 1)

        add_btn = QPushButton("Add to Molecule")
        add_btn.clicked.connect(self.add_atom)
        add_btn.setStyleSheet("background-color: #4caf50; color: white;")
        atom_layout.addWidget(add_btn, 2, 0, 1, 2)

        left_layout.addWidget(atom_group)

        # Composition display
        comp_group = QGroupBox("Current Composition")
        comp_layout = QVBoxLayout(comp_group)

        self.comp_list = QListWidget()
        comp_layout.addWidget(self.comp_list)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_atom)
        comp_layout.addWidget(remove_btn)

        self.formula_label = QLabel("Formula: -")
        self.formula_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #9c27b0;")
        comp_layout.addWidget(self.formula_label)

        left_layout.addWidget(comp_group)

        # Quick presets
        preset_group = QGroupBox("Quick Presets")
        preset_layout = QHBoxLayout(preset_group)
        presets = [
            ("H₂O", [("H", 2), ("O", 1)]),
            ("CO₂", [("C", 1), ("O", 2)]),
            ("CH₄", [("C", 1), ("H", 4)]),
            ("NaCl", [("Na", 1), ("Cl", 1)]),
        ]
        for name, comp in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, c=comp: self.set_composition(c))
            preset_layout.addWidget(btn)
        left_layout.addWidget(preset_group)

        # Naming
        name_group = QGroupBox("Molecule Identity")
        name_layout = QGridLayout(name_group)

        name_label = QLabel("Name:")
        name_label.setToolTip("A descriptive name for the molecule")
        name_layout.addWidget(name_label, 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("Enter a common or IUPAC name for the molecule (required)")
        self.name_edit.setPlaceholderText("e.g., Water, Methane")
        self.name_edit.textChanged.connect(self.update_preview)
        name_layout.addWidget(self.name_edit, 0, 1)

        left_layout.addWidget(name_group)

        # Properties
        props_group = QGroupBox("Calculated Properties")
        props_layout = QVBoxLayout(props_group)
        self.props_summary = QLabel("Add atoms to see properties")
        self.props_summary.setWordWrap(True)
        self.props_summary.setStyleSheet("color: #aaa; font-family: monospace;")
        props_layout.addWidget(self.props_summary)
        left_layout.addWidget(props_group)

        splitter.addWidget(left_panel)

        # Right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        preview_label = QLabel("JSON Preview")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        right_layout.addWidget(preview_label)

        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        right_layout.addWidget(self.json_preview)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])

        layout.addWidget(splitter)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.create_btn = QPushButton("Create Molecule")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #9c27b0;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """)
        self.create_btn.clicked.connect(self.create_molecule)
        self.create_btn.setEnabled(False)
        btn_layout.addWidget(self.create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def load_available_atoms(self):
        """Load available atoms from data manager."""
        manager = get_data_manager()
        elements = manager.get_all_items(DataCategory.ELEMENTS)

        self.atom_combo.clear()
        for elem in elements:
            symbol = elem.get('symbol', '')
            name = elem.get('name', '')
            self.atom_combo.addItem(f"{symbol} - {name}", symbol)
            self.atom_data[symbol] = elem

    def add_atom(self):
        """Add atom to composition."""
        symbol = self.atom_combo.currentData()
        if not symbol:
            symbol = self.atom_combo.currentText().split(' ')[0]

        count = self.count_spin.value()

        # Check if already in composition
        for comp in self.composition:
            if comp['Element'] == symbol:
                comp['Count'] += count
                self.update_composition_list()
                self.update_preview()
                return

        self.composition.append({"Element": symbol, "Count": count})
        self.update_composition_list()
        self.update_preview()

    def remove_atom(self):
        """Remove selected atom from composition."""
        current = self.comp_list.currentRow()
        if current >= 0 and current < len(self.composition):
            del self.composition[current]
            self.update_composition_list()
            self.update_preview()

    def set_composition(self, comp: List[tuple]):
        """Set composition from preset."""
        self.composition = [{"Element": e, "Count": c} for e, c in comp]
        self.update_composition_list()
        self.update_preview()

    def update_composition_list(self):
        """Update the composition list widget."""
        self.comp_list.clear()
        for comp in self.composition:
            self.comp_list.addItem(f"{comp['Element']} × {comp['Count']}")

    def update_preview(self):
        if not self.composition:
            self.formula_label.setText("Formula: -")
            self.props_summary.setText("Add atoms to see properties")
            self.json_preview.clear()
            self.create_btn.setEnabled(False)
            return

        # Generate formula
        formula = MoleculeCalculator.generate_formula(self.composition)
        self.formula_label.setText(f"Formula: {formula}")

        self.create_btn.setEnabled(bool(self.name_edit.text()))

        # Generate molecule data
        name = self.name_edit.text() or None
        molecule_data = MoleculeCalculator.create_molecule_from_atoms(
            self.composition, name, self.atom_data
        )

        # Update summary
        mass = molecule_data['MolecularMass_amu']
        bond_type = molecule_data['BondType']
        geometry = molecule_data['Geometry']
        polarity = molecule_data['Polarity']
        state = molecule_data['State_STP']

        summary = f"""
Formula: {formula}
Molecular Mass: {mass:.3f} g/mol

Bond Type: {bond_type}
Geometry: {geometry}
Polarity: {polarity}

Melting Point: {molecule_data['MeltingPoint_K']:.1f} K
Boiling Point: {molecule_data['BoilingPoint_K']:.1f} K
Density: {molecule_data['Density_g_cm3']:.3f} g/cm³

State at STP: {state}
Dipole Moment: {molecule_data['DipoleMoment_D']:.2f} D
        """.strip()
        self.props_summary.setText(summary)

        # Update JSON
        json_str = json.dumps(molecule_data, indent=2, ensure_ascii=False)
        self.json_preview.setPlainText(json_str)

        self._current_data = molecule_data

    def create_molecule(self):
        if not self.name_edit.text():
            QMessageBox.warning(self, "Missing Name", "Please enter a molecule name.")
            return

        if not self.composition:
            QMessageBox.warning(self, "No Atoms", "Please add at least one atom to the molecule composition.")
            return

        self._current_data['Name'] = self.name_edit.text()

        manager = get_data_manager()
        filename = self.name_edit.text().replace(' ', '_')

        if manager.add_item(DataCategory.MOLECULES, filename, self._current_data):
            self.molecule_created.emit(self._current_data)
            QMessageBox.information(self, "Success", f"Molecule '{self._current_data['Name']}' created!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to create molecule. It may already exist.")


# Convenience functions
def open_atom_creation_dialog(parent=None) -> Optional[Dict]:
    """Open atom creation dialog and return created data or None."""
    dialog = AtomCreationDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog._current_data
    return None


def open_subatomic_creation_dialog(parent=None) -> Optional[Dict]:
    """Open subatomic creation dialog and return created data or None."""
    dialog = SubatomicCreationDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog._current_data
    return None


def open_molecule_creation_dialog(parent=None) -> Optional[Dict]:
    """Open molecule creation dialog and return created data or None."""
    dialog = MoleculeCreationDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog._current_data
    return None
