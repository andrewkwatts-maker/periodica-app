"""
Periodics - Interactive Periodic Table Application
Main entry point with tabbed interface for different views:
- Atoms (Periodic Table)
- Quarks (Fundamental Particles)
- Subatomic (Hadrons)
- Molecules
- Alloys
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QMessageBox, QStatusBar, QLabel, QFileDialog
)
from periodica.utils.report_logger import get_report_logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor

# Import tab components
# Atoms tab
try:
    from periodica_app.core.unified_table import UnifiedPeriodicTable
    from periodica_app.ui.control_panel import ControlPanel
    from periodica_app.ui.element_info_panel import ElementInfoPanel
    HAS_ATOMS_TAB = True
except ImportError as e:
    print(f"Atoms tab not available: {e}")
    HAS_ATOMS_TAB = False

# Quarks tab
try:
    from periodica_app.core.quark_unified_table import QuarkUnifiedTable
    from periodica_app.ui.quark_control_panel import QuarkControlPanel
    from periodica_app.ui.quark_info_panel import QuarkInfoPanel
    HAS_QUARKS_TAB = True
except ImportError as e:
    print(f"Quarks tab not available: {e}")
    HAS_QUARKS_TAB = False

# Subatomic tab
try:
    from periodica_app.core.subatomic_unified_table import SubatomicUnifiedTable
    from periodica_app.ui.subatomic_control_panel import SubatomicControlPanel
    from periodica_app.ui.subatomic_info_panel import SubatomicInfoPanel
    HAS_SUBATOMIC_TAB = True
except ImportError as e:
    print(f"Subatomic tab not available: {e}")
    HAS_SUBATOMIC_TAB = False

# Molecules tab
try:
    from periodica_app.core.molecule_unified_table import MoleculeUnifiedTable
    from periodica_app.ui.molecule_control_panel import MoleculeControlPanel
    from periodica_app.ui.molecule_info_panel import MoleculeInfoPanel
    HAS_MOLECULES_TAB = True
except ImportError as e:
    print(f"Molecules tab not available: {e}")
    HAS_MOLECULES_TAB = False

# Alloys tab
try:
    from periodica_app.core.alloy_unified_table import AlloyUnifiedTable
    from periodica_app.ui.alloy_control_panel import AlloyControlPanel
    from periodica_app.ui.alloy_info_panel import AlloyInfoPanel
    from periodica_app.ui.alloy_creation_dialog import AlloyCreationDialog
    HAS_ALLOYS_TAB = True
except ImportError as e:
    print(f"Alloys tab not available: {e}")
    HAS_ALLOYS_TAB = False

# Materials tab
try:
    from periodica_app.core.material_unified_table import MaterialUnifiedTable
    from periodica_app.ui.material_control_panel import MaterialControlPanel
    from periodica_app.ui.material_info_panel import MaterialInfoPanel
    HAS_MATERIALS_TAB = True
except ImportError as e:
    print(f"Materials tab not available: {e}")
    HAS_MATERIALS_TAB = False

# Amino Acids tab
try:
    from periodica_app.ui.amino_acid_table import AminoAcidTableWidget
    from periodica_app.ui.amino_acid_control_panel import AminoAcidControlPanel
    from periodica_app.ui.amino_acid_info_panel import AminoAcidInfoPanel
    HAS_AMINO_ACIDS_TAB = True
except ImportError as e:
    print(f"Amino Acids tab not available: {e}")
    HAS_AMINO_ACIDS_TAB = False

# Proteins tab
try:
    from periodica_app.ui.protein_table import ProteinTableWidget
    from periodica_app.ui.protein_control_panel import ProteinControlPanel
    from periodica_app.ui.protein_info_panel import ProteinInfoPanel
    from periodica.utils.predictors.biological.protein_predictor import ProteinPredictor
    HAS_PROTEINS_TAB = True
except ImportError as e:
    print(f"Proteins tab not available: {e}")
    HAS_PROTEINS_TAB = False

# Nucleic Acids tab
try:
    from periodica_app.ui.nucleic_acid_table import NucleicAcidTableWidget
    from periodica_app.ui.nucleic_acid_control_panel import NucleicAcidControlPanel
    from periodica_app.ui.nucleic_acid_info_panel import NucleicAcidInfoPanel
    from periodica.utils.predictors.biological.nucleic_acid_predictor import NucleicAcidPredictor
    HAS_NUCLEIC_ACIDS_TAB = True
except ImportError as e:
    print(f"Nucleic Acids tab not available: {e}")
    HAS_NUCLEIC_ACIDS_TAB = False

# Cell Components tab
try:
    from periodica_app.ui.cell_component_table import CellComponentTableWidget
    from periodica_app.ui.cell_component_control_panel import CellComponentControlPanel
    from periodica_app.ui.cell_component_info_panel import CellComponentInfoPanel
    HAS_CELL_COMPONENTS_TAB = True
except ImportError as e:
    print(f"Cell Components tab not available: {e}")
    HAS_CELL_COMPONENTS_TAB = False

# Cells tab
try:
    from periodica_app.ui.cell_table import CellTableWidget
    from periodica_app.ui.cell_control_panel import CellControlPanel
    from periodica_app.ui.cell_info_panel import CellInfoPanel
    from periodica.utils.predictors.biological.cell_predictor import CellPredictor
    HAS_CELLS_TAB = True
except ImportError as e:
    print(f"Cells tab not available: {e}")
    HAS_CELLS_TAB = False

# Biological Materials tab
try:
    from periodica_app.ui.biomaterial_table import BiomaterialTableWidget
    from periodica_app.ui.biomaterial_control_panel import BiomaterialControlPanel
    from periodica_app.ui.biomaterial_info_panel import BiomaterialInfoPanel
    from periodica.utils.predictors.biological.biomaterial_predictor import BiomaterialPredictor
    HAS_BIOMATERIALS_TAB = True
except ImportError as e:
    print(f"Biological Materials tab not available: {e}")
    HAS_BIOMATERIALS_TAB = False

# Data management
from periodica.data.data_manager import get_data_manager, DataCategory
from periodica_app.ui.data_editor_dialog import DataEditorDialog


class PeriodicsMainWindow(QMainWindow):
    """Main application window with tabbed interface"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Periodics - Interactive Particle Explorer")
        self.setMinimumSize(1400, 900)

        self.setup_ui()
        self.setup_statusbar()
        self.apply_dark_theme()

    def setup_ui(self):
        """Setup the main UI components"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: rgb(20, 20, 35);
            }
            QTabBar::tab {
                background: rgb(45, 45, 65);
                color: white;
                padding: 12px 25px;
                margin-right: 3px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(80, 80, 120), stop:1 rgb(60, 60, 90));
            }
            QTabBar::tab:hover:!selected {
                background: rgb(60, 60, 85);
            }
        """)

        # Add tabs
        if HAS_ATOMS_TAB:
            self._add_atoms_tab()

        if HAS_QUARKS_TAB:
            self._add_quarks_tab()

        if HAS_SUBATOMIC_TAB:
            self._add_subatomic_tab()

        if HAS_MOLECULES_TAB:
            self._add_molecules_tab()

        if HAS_ALLOYS_TAB:
            self._add_alloys_tab()

        if HAS_MATERIALS_TAB:
            self._add_materials_tab()

        if HAS_AMINO_ACIDS_TAB:
            self._add_amino_acids_tab()

        if HAS_PROTEINS_TAB:
            self._add_proteins_tab()

        if HAS_NUCLEIC_ACIDS_TAB:
            self._add_nucleic_acids_tab()

        if HAS_CELL_COMPONENTS_TAB:
            self._add_cell_components_tab()

        if HAS_CELLS_TAB:
            self._add_cells_tab()

        if HAS_BIOMATERIALS_TAB:
            self._add_biomaterials_tab()

        main_layout.addWidget(self.tabs)

    def _add_atoms_tab(self):
        """Add the Atoms (Periodic Table) tab"""
        atoms_widget = QWidget()
        atoms_layout = QHBoxLayout(atoms_widget)
        atoms_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Control panel
        self.atom_table = UnifiedPeriodicTable()
        self.atom_control = ControlPanel(self.atom_table)
        self.atom_control.setFixedWidth(360)
        splitter.addWidget(self.atom_control)

        # Main table
        splitter.addWidget(self.atom_table)

        # Info panel
        self.atom_info = ElementInfoPanel()
        self.atom_info.setFixedWidth(350)
        splitter.addWidget(self.atom_info)

        # Connect signals
        self.atom_table.element_selected.connect(self._on_atom_selected)
        self.atom_table.element_hovered.connect(lambda e: self.statusBar().showMessage(
            f"Element: {e.get('name', '')} ({e.get('symbol', '')})" if e else ""))

        # Connect data management signals
        self.atom_control.add_requested.connect(self._on_atom_add)
        self.atom_control.edit_requested.connect(self._on_atom_edit)
        self.atom_control.remove_requested.connect(self._on_atom_remove)
        self.atom_control.reset_requested.connect(self._on_atom_reset)
        self.atom_control.create_requested.connect(self._on_atom_create)
        self.atom_control.export_requested.connect(self._on_atom_export)
        self.atom_control.import_requested.connect(self._on_atom_import)
        self.atom_control.duplicate_requested.connect(self._on_atom_duplicate)
        self.atom_info.data_saved.connect(self._on_atom_data_saved)
        self.atom_info.edit_cancelled.connect(lambda: self.atom_info.show_default())
        self.atom_control.ai_generate_requested.connect(self._on_atom_ai_generate)
        self.atom_control.ai_settings_requested.connect(self._on_ai_settings)

        # Update item count
        self.atom_control.update_item_count(len(self.atom_table.base_elements))

        atoms_layout.addWidget(splitter)
        self.tabs.addTab(atoms_widget, "Atoms")

    def _add_quarks_tab(self):
        """Add the Quarks tab"""
        quarks_widget = QWidget()
        quarks_layout = QHBoxLayout(quarks_widget)
        quarks_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        self.quark_table = QuarkUnifiedTable()
        self.quark_control = QuarkControlPanel(self.quark_table)
        self.quark_control.setFixedWidth(360)
        splitter.addWidget(self.quark_control)

        splitter.addWidget(self.quark_table)

        self.quark_info = QuarkInfoPanel()
        self.quark_info.setFixedWidth(350)
        splitter.addWidget(self.quark_info)

        self.quark_table.quark_selected.connect(self._on_quark_selected)

        # Connect data management signals
        self.quark_control.add_requested.connect(self._on_quark_add)
        self.quark_control.edit_requested.connect(self._on_quark_edit)
        self.quark_control.remove_requested.connect(self._on_quark_remove)
        self.quark_control.reset_requested.connect(self._on_quark_reset)
        self.quark_control.create_requested.connect(self._on_quark_create)
        self.quark_control.export_requested.connect(self._on_quark_export)
        self.quark_control.import_requested.connect(self._on_quark_import)
        self.quark_control.duplicate_requested.connect(self._on_quark_duplicate)
        self.quark_info.data_saved.connect(self._on_quark_data_saved)
        self.quark_info.edit_cancelled.connect(lambda: self.quark_info.show_default())
        self.quark_control.ai_generate_requested.connect(self._on_quark_ai_generate)
        self.quark_control.ai_settings_requested.connect(self._on_ai_settings)
        self.quark_control.cascade_regenerate_requested.connect(self._on_cascade_regenerate)

        # Update item count
        self.quark_control.update_item_count(len(self.quark_table.base_particles))

        quarks_layout.addWidget(splitter)
        self.tabs.addTab(quarks_widget, "Quarks")

    def _add_subatomic_tab(self):
        """Add the Subatomic particles tab"""
        subatomic_widget = QWidget()
        subatomic_layout = QHBoxLayout(subatomic_widget)
        subatomic_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        self.subatomic_table = SubatomicUnifiedTable()
        self.subatomic_control = SubatomicControlPanel(self.subatomic_table)
        self.subatomic_control.setFixedWidth(360)
        splitter.addWidget(self.subatomic_control)

        splitter.addWidget(self.subatomic_table)

        self.subatomic_info = SubatomicInfoPanel()
        self.subatomic_info.setFixedWidth(350)
        splitter.addWidget(self.subatomic_info)

        self.subatomic_table.particle_selected.connect(self._on_subatomic_selected)

        # Connect data management signals
        self.subatomic_control.add_requested.connect(self._on_subatomic_add)
        self.subatomic_control.edit_requested.connect(self._on_subatomic_edit)
        self.subatomic_control.remove_requested.connect(self._on_subatomic_remove)
        self.subatomic_control.reset_requested.connect(self._on_subatomic_reset)
        self.subatomic_control.create_requested.connect(self._on_subatomic_create)
        self.subatomic_control.export_requested.connect(self._on_subatomic_export)
        self.subatomic_control.import_requested.connect(self._on_subatomic_import)
        self.subatomic_control.duplicate_requested.connect(self._on_subatomic_duplicate)
        self.subatomic_info.data_saved.connect(self._on_subatomic_data_saved)
        self.subatomic_info.edit_cancelled.connect(lambda: self.subatomic_info.show_default())
        self.subatomic_control.ai_generate_requested.connect(self._on_subatomic_ai_generate)
        self.subatomic_control.ai_settings_requested.connect(self._on_ai_settings)

        # Update item count
        self.subatomic_control.update_item_count(len(self.subatomic_table.particles))

        subatomic_layout.addWidget(splitter)
        self.tabs.addTab(subatomic_widget, "Subatomic")

    def _add_molecules_tab(self):
        """Add the Molecules tab"""
        molecules_widget = QWidget()
        molecules_layout = QHBoxLayout(molecules_widget)
        molecules_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        self.molecule_table = MoleculeUnifiedTable()
        self.molecule_control = MoleculeControlPanel(self.molecule_table)
        self.molecule_control.setFixedWidth(360)
        splitter.addWidget(self.molecule_control)

        splitter.addWidget(self.molecule_table)

        self.molecule_info = MoleculeInfoPanel()
        self.molecule_info.setFixedWidth(350)
        splitter.addWidget(self.molecule_info)

        self.molecule_table.molecule_selected.connect(self._on_molecule_selected)

        # Connect rotation controls to info panel structure widget
        self.molecule_control.rotation_changed.connect(
            self.molecule_info.structure_widget.set_rotation
        )

        # Connect data management signals
        self.molecule_control.add_requested.connect(self._on_molecule_add)
        self.molecule_control.edit_requested.connect(self._on_molecule_edit)
        self.molecule_control.remove_requested.connect(self._on_molecule_remove)
        self.molecule_control.reset_requested.connect(self._on_molecule_reset)
        self.molecule_control.create_requested.connect(self._on_molecule_create)
        self.molecule_control.export_requested.connect(self._on_molecule_export)
        self.molecule_control.import_requested.connect(self._on_molecule_import)
        self.molecule_control.duplicate_requested.connect(self._on_molecule_duplicate)
        self.molecule_info.data_saved.connect(self._on_molecule_data_saved)
        self.molecule_info.edit_cancelled.connect(lambda: self.molecule_info.show_default())
        self.molecule_control.ai_generate_requested.connect(self._on_molecule_ai_generate)
        self.molecule_control.ai_settings_requested.connect(self._on_ai_settings)

        # Update item count
        self.molecule_control.update_item_count(len(self.molecule_table.base_molecules))

        molecules_layout.addWidget(splitter)
        self.tabs.addTab(molecules_widget, "Molecules")

    def _add_alloys_tab(self):
        """Add the Alloys tab"""
        alloys_widget = QWidget()
        alloys_layout = QHBoxLayout(alloys_widget)
        alloys_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create alloy table
        self.alloy_table = AlloyUnifiedTable()

        # Control panel
        self.alloy_control = AlloyControlPanel(self.alloy_table)
        self.alloy_control.setFixedWidth(360)
        splitter.addWidget(self.alloy_control)

        # Main visualization
        splitter.addWidget(self.alloy_table)

        # Info panel
        self.alloy_info = AlloyInfoPanel()
        self.alloy_info.setFixedWidth(400)
        splitter.addWidget(self.alloy_info)

        # Connect signals
        self.alloy_table.alloy_selected.connect(self._on_alloy_selected)
        self.alloy_table.alloy_hovered.connect(lambda a: self.statusBar().showMessage(
            f"Alloy: {a.get('name', '')} - {a.get('category', '')}" if a else ""))

        # Connect data management signals
        self.alloy_control.add_requested.connect(self._on_alloy_add)
        self.alloy_control.edit_requested.connect(self._on_alloy_edit)
        self.alloy_control.remove_requested.connect(self._on_alloy_remove)
        self.alloy_control.reset_requested.connect(self._on_alloy_reset)
        self.alloy_control.create_requested.connect(self._on_alloy_create)
        self.alloy_control.export_requested.connect(self._on_alloy_export)
        self.alloy_control.import_requested.connect(self._on_alloy_import)
        self.alloy_control.duplicate_requested.connect(self._on_alloy_duplicate)
        self.alloy_control.ai_generate_requested.connect(self._on_alloy_ai_generate)
        self.alloy_control.ai_settings_requested.connect(self._on_ai_settings)
        self.alloy_control.auto_generate_requested.connect(self._on_alloy_auto_generate)
        self.alloy_info.data_saved.connect(self._on_alloy_data_saved)

        # Update item count
        self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))

        alloys_layout.addWidget(splitter)
        self.tabs.addTab(alloys_widget, "Alloys")

    def _add_materials_tab(self):
        """Add the Materials (Engineering) tab"""
        materials_widget = QWidget()
        materials_layout = QHBoxLayout(materials_widget)
        materials_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create material table
        self.material_table = MaterialUnifiedTable()

        # Control panel
        self.material_control = MaterialControlPanel(self.material_table)
        self.material_control.setFixedWidth(360)
        splitter.addWidget(self.material_control)

        # Main visualization
        splitter.addWidget(self.material_table)

        # Info panel
        self.material_info = MaterialInfoPanel()
        self.material_info.setFixedWidth(400)
        splitter.addWidget(self.material_info)

        # Connect signals
        self.material_table.material_selected.connect(self._on_material_selected)
        self.material_table.material_hovered.connect(lambda m: self.statusBar().showMessage(
            f"Material: {m.get('Name', '')} - {m.get('Category', '')}" if m else ""))

        # Connect data management signals
        self.material_control.add_material_requested.connect(self._on_material_add)
        self.material_control.edit_material_requested.connect(self._on_material_edit)
        self.material_control.delete_material_requested.connect(self._on_material_delete)
        self.material_control.export_requested.connect(self._on_material_export)
        self.material_control.import_requested.connect(self._on_material_import)
        self.material_control.duplicate_requested.connect(self._on_material_duplicate)
        self.material_control.ai_generate_requested.connect(self._on_material_ai_generate)
        self.material_control.ai_settings_requested.connect(self._on_ai_settings)
        self.material_control.auto_generate_requested.connect(self._on_material_auto_generate)

        materials_layout.addWidget(splitter)
        self.tabs.addTab(materials_widget, "Materials")

    def _add_amino_acids_tab(self):
        """Add the Amino Acids tab"""
        amino_acids_widget = QWidget()
        amino_acids_layout = QHBoxLayout(amino_acids_widget)
        amino_acids_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create amino acid table
        self.amino_acid_table = AminoAcidTableWidget()

        # Control panel
        self.amino_acid_control = AminoAcidControlPanel(self.amino_acid_table)
        self.amino_acid_control.setFixedWidth(360)
        splitter.addWidget(self.amino_acid_control)

        # Main visualization
        splitter.addWidget(self.amino_acid_table)

        # Info panel
        self.amino_acid_info = AminoAcidInfoPanel()
        self.amino_acid_info.setFixedWidth(380)
        splitter.addWidget(self.amino_acid_info)

        # Connect signals
        self.amino_acid_table.amino_acid_selected.connect(self._on_amino_acid_selected)

        # Connect pH control to both table and info panel
        self.amino_acid_control.pH_changed.connect(self._on_amino_acid_pH_changed)

        # Connect data management signals
        self.amino_acid_control.add_requested.connect(self._on_amino_acid_add)
        self.amino_acid_control.edit_requested.connect(self._on_amino_acid_edit)
        self.amino_acid_control.ai_update_requested.connect(self._on_amino_acid_ai_update)
        self.amino_acid_control.remove_requested.connect(self._on_amino_acid_remove)
        self.amino_acid_control.reset_requested.connect(self._on_amino_acid_reset)
        self.amino_acid_control.export_requested.connect(self._on_amino_acid_export)
        self.amino_acid_control.import_requested.connect(self._on_amino_acid_import)
        self.amino_acid_control.duplicate_requested.connect(self._on_amino_acid_duplicate)
        self.amino_acid_info.data_saved.connect(self._on_amino_acid_data_saved)
        self.amino_acid_info.edit_cancelled.connect(lambda: self.amino_acid_info.show_default())
        self.amino_acid_control.ai_generate_requested.connect(self._on_amino_acid_ai_generate)
        self.amino_acid_control.ai_settings_requested.connect(self._on_ai_settings)
        self.amino_acid_control.auto_generate_requested.connect(self._on_amino_acid_auto_generate)

        # Update item count
        self.amino_acid_control.update_item_count(self.amino_acid_table.get_amino_acid_count())

        amino_acids_layout.addWidget(splitter)
        self.tabs.addTab(amino_acids_widget, "Amino Acids")

    def _on_amino_acid_selected(self, aa):
        """Handle amino acid selection"""
        self.amino_acid_info.update_amino_acid(aa, self.amino_acid_control.pH_spinbox.value())
        self.amino_acid_control.set_item_selected(aa is not None)

    def _on_amino_acid_pH_changed(self, pH):
        """Handle pH change - update info panel with new charge"""
        selected = self.amino_acid_table.get_selected_amino_acid()
        if selected:
            self.amino_acid_info.update_amino_acid(selected, pH)

    def _on_amino_acid_add(self):
        """Handle amino acid add request"""
        self.amino_acid_info.start_add(None)

    def _on_amino_acid_edit(self):
        """Handle amino acid edit request"""
        selected = self.amino_acid_table.get_selected_amino_acid()
        if selected:
            self.amino_acid_info.start_edit(selected)

    def _on_amino_acid_remove(self):
        """Handle amino acid remove request"""
        selected = self.amino_acid_table.get_selected_amino_acid()
        if selected:
            name = selected.get('name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Amino Acid",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import os
                aa_dir = Path(__file__).parent / "data" / "active" / "amino_acids"
                for f in aa_dir.glob("*.json"):
                    if f.stem == name or f.stem.replace('_', ' ') == name:
                        os.remove(f)
                        self.amino_acid_table.refresh()
                        self.amino_acid_info.show_default()
                        self.amino_acid_control.set_item_selected(False)
                        self.amino_acid_control.update_item_count(
                            self.amino_acid_table.get_amino_acid_count())
                        break

    def _on_amino_acid_reset(self):
        """Handle amino acid reset request"""
        reply = QMessageBox.question(
            self, "Reset Amino Acids",
            "Are you sure you want to reset all amino acids to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.amino_acid_table.refresh()
            self.amino_acid_info.show_default()
            QMessageBox.information(self, "Success", "Amino acids reset to defaults.")

    def _on_amino_acid_data_saved(self, data):
        """Called when amino acid data is saved"""
        self.amino_acid_table.refresh()
        self.amino_acid_info.show_default()
        self.amino_acid_control.update_item_count(self.amino_acid_table.get_amino_acid_count())

    def _on_amino_acid_export(self):
        """Handle amino acid export request"""
        from periodica_app.ui.action_handler import ExportHandler

        selected = self.amino_acid_table.get_selected_amino_acid()
        if selected:
            name = selected.get('name', 'amino_acid')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(selected, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_amino_acid_import(self):
        """Handle amino acid import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Amino Acid", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                name = data.get('name', 'Imported')
                dest_path = Path(__file__).parent / "data" / "active" / "amino_acids" / f"{name.replace(' ', '_')}.json"
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                if ExportHandler.export_json(data, dest_path):
                    self.amino_acid_table.refresh()
                    self.amino_acid_control.update_item_count(self.amino_acid_table.get_amino_acid_count())
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to import amino acid")
            else:
                QMessageBox.warning(self, "Error", "Failed to read import file")

    def _on_amino_acid_duplicate(self):
        """Handle amino acid duplicate request"""
        from periodica_app.ui.action_handler import DuplicateHandler, ExportHandler

        selected = self.amino_acid_table.get_selected_amino_acid()
        if selected:
            duplicated = DuplicateHandler.duplicate_item(selected, name_key='name')
            name = duplicated.get('name', 'Unknown')
            dest_path = Path(__file__).parent / "data" / "active" / "amino_acids" / f"{name.replace(' ', '_')}.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if ExportHandler.export_json(duplicated, dest_path):
                self.amino_acid_table.refresh()
                self.amino_acid_control.update_item_count(self.amino_acid_table.get_amino_acid_count())
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    def _add_proteins_tab(self):
        """Add the Proteins tab"""
        proteins_widget = QWidget()
        proteins_layout = QHBoxLayout(proteins_widget)
        proteins_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create protein table
        self.protein_table = ProteinTableWidget()

        # Control panel
        self.protein_control = ProteinControlPanel()
        self.protein_control.setFixedWidth(360)
        splitter.addWidget(self.protein_control)

        # Main visualization
        splitter.addWidget(self.protein_table)

        # Info panel
        self.protein_info = ProteinInfoPanel()
        self.protein_info.setFixedWidth(400)
        splitter.addWidget(self.protein_info)

        # Connect signals
        self.protein_table.protein_selected.connect(self._on_protein_selected)
        self.protein_table.protein_hovered.connect(lambda p: self.statusBar().showMessage(
            f"Protein: {p.get('name', '')} - {p.get('function', '')}" if p else ""))

        # Connect control panel signals
        self.protein_control.layout_changed.connect(self.protein_table.set_layout_mode)
        self.protein_control.color_property_changed.connect(self.protein_table.set_color_property)
        self.protein_control.size_property_changed.connect(self.protein_table.set_size_property)
        self.protein_control.filter_changed.connect(self.protein_table.set_function_filters)
        self.protein_control.sequence_submitted.connect(self._on_protein_sequence_submitted)
        self.protein_control.ai_generate_requested.connect(self._on_protein_ai_generate)
        self.protein_control.ai_settings_requested.connect(self._on_ai_settings)
        self.protein_control.auto_generate_requested.connect(self._on_protein_auto_generate)

        # Connect data management signals
        self.protein_control.add_requested.connect(self._on_protein_add)
        self.protein_control.edit_requested.connect(self._on_protein_edit)
        self.protein_control.ai_update_requested.connect(self._on_protein_ai_update)
        self.protein_control.remove_requested.connect(self._on_protein_remove)
        self.protein_control.reset_requested.connect(self._on_protein_reset)
        self.protein_control.export_requested.connect(self._on_protein_export)
        self.protein_control.import_requested.connect(self._on_protein_import)
        self.protein_control.duplicate_requested.connect(self._on_protein_duplicate)

        # Update item count
        self.protein_control.update_item_count(self.protein_table.get_protein_count())

        proteins_layout.addWidget(splitter)
        self.tabs.addTab(proteins_widget, "Proteins")

    def _on_protein_selected(self, protein):
        """Handle protein selection"""
        self.protein_info.set_protein(protein)
        self.protein_control.set_item_selected(protein is not None)

    def _on_protein_sequence_submitted(self, sequence):
        """Handle protein sequence analysis from control panel"""
        predictor = ProteinPredictor()
        analysis = predictor.analyze_protein(sequence, "Custom Sequence")
        self.protein_info.set_protein(analysis)
        self.statusBar().showMessage(
            f"Analyzed sequence: {len(sequence)} residues, MW: {analysis['molecular_mass']:.2f} Da")

    def _add_nucleic_acids_tab(self):
        """Add the Nucleic Acids tab"""
        na_widget = QWidget()
        na_layout = QHBoxLayout(na_widget)
        na_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create nucleic acid table
        self.nucleic_acid_table = NucleicAcidTableWidget()

        # Control panel
        self.nucleic_acid_control = NucleicAcidControlPanel()
        self.nucleic_acid_control.setFixedWidth(360)
        splitter.addWidget(self.nucleic_acid_control)

        # Main visualization
        splitter.addWidget(self.nucleic_acid_table)

        # Info panel
        self.nucleic_acid_info = NucleicAcidInfoPanel()
        self.nucleic_acid_info.setFixedWidth(400)
        splitter.addWidget(self.nucleic_acid_info)

        # Connect signals
        self.nucleic_acid_table.nucleic_acid_selected.connect(self._on_nucleic_acid_selected)
        self.nucleic_acid_table.nucleic_acid_hovered.connect(lambda na: self.statusBar().showMessage(
            f"Nucleic Acid: {na.get('name', '')} - {na.get('type', '').upper()}" if na else ""))

        # Connect control panel signals
        self.nucleic_acid_control.layout_changed.connect(self.nucleic_acid_table.set_layout_mode)
        self.nucleic_acid_control.color_property_changed.connect(self.nucleic_acid_table.set_color_property)
        self.nucleic_acid_control.size_property_changed.connect(self.nucleic_acid_table.set_size_property)
        self.nucleic_acid_control.type_filter_changed.connect(self.nucleic_acid_table.set_type_filters)
        self.nucleic_acid_control.sequence_submitted.connect(self._on_nucleic_acid_sequence_submitted)
        self.nucleic_acid_control.ai_generate_requested.connect(self._on_nucleic_acid_ai_generate)
        self.nucleic_acid_control.ai_settings_requested.connect(self._on_ai_settings)
        self.nucleic_acid_control.auto_generate_requested.connect(self._on_nucleic_acid_auto_generate)

        # Connect data management signals
        self.nucleic_acid_control.add_requested.connect(self._on_nucleic_acid_add)
        self.nucleic_acid_control.edit_requested.connect(self._on_nucleic_acid_edit)
        self.nucleic_acid_control.ai_update_requested.connect(self._on_nucleic_acid_ai_update)
        self.nucleic_acid_control.remove_requested.connect(self._on_nucleic_acid_remove)
        self.nucleic_acid_control.reset_requested.connect(self._on_nucleic_acid_reset)
        self.nucleic_acid_control.export_requested.connect(self._on_nucleic_acid_export)
        self.nucleic_acid_control.import_requested.connect(self._on_nucleic_acid_import)
        self.nucleic_acid_control.duplicate_requested.connect(self._on_nucleic_acid_duplicate)

        na_layout.addWidget(splitter)
        self.tabs.addTab(na_widget, "Nucleic Acids")

    def _on_nucleic_acid_selected(self, na):
        """Handle nucleic acid selection"""
        self.nucleic_acid_info.set_nucleic_acid(na)

    def _on_nucleic_acid_sequence_submitted(self, sequence, is_rna):
        """Handle nucleic acid sequence analysis from control panel"""
        predictor = NucleicAcidPredictor()
        analysis = predictor.analyze_sequence(sequence, "Custom Sequence", is_rna)
        self.nucleic_acid_info.set_nucleic_acid(analysis)
        self.statusBar().showMessage(
            f"Analyzed sequence: {len(sequence)} nt, GC: {analysis['gc_content']:.1f}%, "
            f"Tm: {analysis['melting_temperature']['nearest_neighbor']:.1f}°C")

    def _add_cell_components_tab(self):
        """Add the Cell Components tab"""
        cell_comp_widget = QWidget()
        cell_comp_layout = QHBoxLayout(cell_comp_widget)
        cell_comp_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create cell component table
        self.cell_component_table = CellComponentTableWidget()

        # Control panel
        self.cell_component_control = CellComponentControlPanel()
        self.cell_component_control.setFixedWidth(360)
        splitter.addWidget(self.cell_component_control)

        # Main visualization
        splitter.addWidget(self.cell_component_table)

        # Info panel
        self.cell_component_info = CellComponentInfoPanel()
        self.cell_component_info.setFixedWidth(400)
        splitter.addWidget(self.cell_component_info)

        # Connect signals
        self.cell_component_table.component_selected.connect(self._on_cell_component_selected)

        # Connect control panel signals
        self.cell_component_control.layout_changed.connect(self.cell_component_table.set_layout_mode)
        self.cell_component_control.color_property_changed.connect(self.cell_component_table.set_color_property)
        self.cell_component_control.size_property_changed.connect(self.cell_component_table.set_size_property)
        self.cell_component_control.type_filter_changed.connect(self.cell_component_table.set_type_filters)
        self.cell_component_control.ai_generate_requested.connect(self._on_cell_component_ai_generate)
        self.cell_component_control.ai_settings_requested.connect(self._on_ai_settings)
        self.cell_component_control.auto_generate_requested.connect(self._on_cell_component_auto_generate)

        # Connect data management signals
        self.cell_component_control.add_requested.connect(self._on_cell_component_add)
        self.cell_component_control.edit_requested.connect(self._on_cell_component_edit)
        self.cell_component_control.ai_update_requested.connect(self._on_cell_component_ai_update)
        self.cell_component_control.remove_requested.connect(self._on_cell_component_remove)
        self.cell_component_control.reset_requested.connect(self._on_cell_component_reset)
        self.cell_component_control.export_requested.connect(self._on_cell_component_export)
        self.cell_component_control.import_requested.connect(self._on_cell_component_import)
        self.cell_component_control.duplicate_requested.connect(self._on_cell_component_duplicate)

        # Update component count
        self.cell_component_control.set_component_count(self.cell_component_table.get_component_count())

        cell_comp_layout.addWidget(splitter)
        self.tabs.addTab(cell_comp_widget, "Cell Components")

    def _on_cell_component_selected(self, component):
        """Handle cell component selection"""
        self.cell_component_info.set_component(component)
        self.cell_component_control.set_item_selected(component is not None)
        self.statusBar().showMessage(
            f"Component: {component.get('name', '')} - {component.get('function', '')}" if component else "")

    def _add_cells_tab(self):
        """Add the Cells tab"""
        cells_widget = QWidget()
        cells_layout = QHBoxLayout(cells_widget)
        cells_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create cell table
        self.cell_table = CellTableWidget()

        # Control panel
        self.cell_control = CellControlPanel()
        self.cell_control.setFixedWidth(360)
        splitter.addWidget(self.cell_control)

        # Main visualization
        splitter.addWidget(self.cell_table)

        # Info panel
        self.cell_info = CellInfoPanel()
        self.cell_info.setFixedWidth(400)
        splitter.addWidget(self.cell_info)

        # Connect signals
        self.cell_table.cell_selected.connect(self._on_cell_selected)
        self.cell_table.cell_hovered.connect(lambda c: self.statusBar().showMessage(
            f"Cell: {c.get('name', '')} - {c.get('type', '')}" if c else ""))

        # Connect control panel signals
        self.cell_control.layout_changed.connect(self.cell_table.set_layout_mode)
        self.cell_control.color_property_changed.connect(self.cell_table.set_color_property)
        self.cell_control.size_property_changed.connect(self.cell_table.set_size_property)
        self.cell_control.type_filter_changed.connect(self.cell_table.set_type_filters)
        self.cell_control.tissue_filter_changed.connect(self.cell_table.set_tissue_filters)
        self.cell_control.ai_generate_requested.connect(self._on_cell_ai_generate)
        self.cell_control.ai_settings_requested.connect(self._on_ai_settings)
        self.cell_control.auto_generate_requested.connect(self._on_cell_auto_generate)

        # Connect data management signals
        self.cell_control.add_requested.connect(self._on_cell_add)
        self.cell_control.edit_requested.connect(self._on_cell_edit)
        self.cell_control.ai_update_requested.connect(self._on_cell_ai_update)
        self.cell_control.remove_requested.connect(self._on_cell_remove)
        self.cell_control.reset_requested.connect(self._on_cell_reset)
        self.cell_control.export_requested.connect(self._on_cell_export)
        self.cell_control.import_requested.connect(self._on_cell_import)
        self.cell_control.duplicate_requested.connect(self._on_cell_duplicate)

        # Update cell count
        self.cell_control.set_cell_count(self.cell_table.get_cell_count())

        cells_layout.addWidget(splitter)
        self.tabs.addTab(cells_widget, "Cells")

    def _on_cell_selected(self, cell):
        """Handle cell selection"""
        self.cell_info.set_cell(cell)
        self.statusBar().showMessage(
            f"Cell: {cell.get('name', '')} - {cell.get('function', '')}" if cell else "")

    def _add_biomaterials_tab(self):
        """Add the Biological Materials tab"""
        biomat_widget = QWidget()
        biomat_layout = QHBoxLayout(biomat_widget)
        biomat_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create biomaterial table
        self.biomaterial_table = BiomaterialTableWidget()

        # Control panel
        self.biomaterial_control = BiomaterialControlPanel()
        self.biomaterial_control.setFixedWidth(360)
        splitter.addWidget(self.biomaterial_control)

        # Main visualization
        splitter.addWidget(self.biomaterial_table)

        # Info panel
        self.biomaterial_info = BiomaterialInfoPanel()
        self.biomaterial_info.setFixedWidth(400)
        splitter.addWidget(self.biomaterial_info)

        # Connect signals
        self.biomaterial_table.biomaterial_selected.connect(self._on_biomaterial_selected)
        self.biomaterial_table.biomaterial_hovered.connect(lambda m: self.statusBar().showMessage(
            f"Material: {m.get('name', '')} - {m.get('type', '')}" if m else ""))

        # Connect control panel signals
        self.biomaterial_control.layout_changed.connect(self.biomaterial_table.set_layout_mode)
        self.biomaterial_control.color_property_changed.connect(self.biomaterial_table.set_color_property)
        self.biomaterial_control.size_property_changed.connect(self.biomaterial_table.set_size_property)
        self.biomaterial_control.type_filter_changed.connect(self.biomaterial_table.set_type_filters)
        self.biomaterial_control.ai_generate_requested.connect(self._on_biomaterial_ai_generate)
        self.biomaterial_control.ai_settings_requested.connect(self._on_ai_settings)
        self.biomaterial_control.auto_generate_requested.connect(self._on_biomaterial_auto_generate)

        # Connect CRUD signals
        self.biomaterial_control.add_requested.connect(self._on_biomaterial_add)
        self.biomaterial_control.edit_requested.connect(self._on_biomaterial_edit)
        self.biomaterial_control.ai_update_requested.connect(self._on_biomaterial_ai_update)
        self.biomaterial_control.remove_requested.connect(self._on_biomaterial_remove)
        self.biomaterial_control.reset_requested.connect(self._on_biomaterial_reset)
        self.biomaterial_control.export_requested.connect(self._on_biomaterial_export)
        self.biomaterial_control.import_requested.connect(self._on_biomaterial_import)
        self.biomaterial_control.duplicate_requested.connect(self._on_biomaterial_duplicate)

        # Update material count
        self.biomaterial_control.set_material_count(self.biomaterial_table.get_material_count())

        biomat_layout.addWidget(splitter)
        self.tabs.addTab(biomat_widget, "Biological Materials")

    def _on_biomaterial_selected(self, material):
        """Handle biomaterial selection"""
        self.biomaterial_info.set_material(material)
        mech = material.get('mechanical_properties', {}) if material else {}
        E = mech.get('youngs_modulus_MPa', 0)
        if E >= 1000:
            E_str = f"{E/1000:.1f} GPa"
        else:
            E_str = f"{E:.1f} MPa"
        self.statusBar().showMessage(
            f"Material: {material.get('name', '')} - E={E_str}" if material else "")

    def _on_material_selected(self, material):
        """Handle material selection"""
        self.material_info.set_material(material)

    def _on_material_add(self):
        """Handle material add request"""
        QMessageBox.information(self, "Add Material",
            "Material creation from composition will be available soon.\n"
            "For now, please add materials via JSON files in data/active/materials/")

    def _on_material_edit(self):
        """Handle material edit request"""
        if hasattr(self.material_table, 'selected_material') and self.material_table.selected_material:
            QMessageBox.information(self, "Edit Material",
                "Material editing will be available soon.\n"
                "For now, please edit the JSON files directly.")

    def _on_material_delete(self):
        """Handle material delete request"""
        if hasattr(self.material_table, 'selected_material') and self.material_table.selected_material:
            mat = self.material_table.selected_material
            name = mat.get('Name', 'Unknown')
            reply = QMessageBox.question(
                self, "Delete Material",
                f"Are you sure you want to delete '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import os
                mat_dir = Path(__file__).parent / "data" / "active" / "materials"
                for f in mat_dir.glob("*.json"):
                    if f.stem.replace('_', ' ') in name or name in f.stem:
                        os.remove(f)
                        self.material_table.loader.reload()
                        self.material_table.base_materials = list(
                            self.material_table.loader.get_all_materials().values())
                        self.material_table._update_layout()
                        self.material_table.update()
                        QMessageBox.information(self, "Success", f"Deleted '{name}'")
                        break

    def _on_material_export(self):
        """Handle material export request"""
        if hasattr(self.material_table, 'selected_material') and self.material_table.selected_material:
            from periodica_app.ui.action_handler import ExportHandler

            mat = self.material_table.selected_material
            name = mat.get('Name', 'material')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(mat, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_material_import(self):
        """Handle material import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Material", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                name = data.get('Name', 'Imported')
                dest_path = Path(__file__).parent / "data" / "active" / "materials" / f"{name.replace(' ', '_')}.json"
                if ExportHandler.export_json(data, dest_path):
                    self.material_table.loader.reload()
                    self.material_table.base_materials = list(
                        self.material_table.loader.get_all_materials().values())
                    self.material_table._update_layout()
                    self.material_table.update()
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported material")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_material_duplicate(self):
        """Handle material duplicate request"""
        if hasattr(self.material_table, 'selected_material') and self.material_table.selected_material:
            from periodica_app.ui.action_handler import DuplicateHandler, ExportHandler

            mat = self.material_table.selected_material
            duplicated = DuplicateHandler.duplicate_item(mat, name_key='Name')
            name = duplicated.get('Name', 'Unknown')
            dest_path = Path(__file__).parent / "data" / "active" / "materials" / f"{name.replace(' ', '_')}.json"
            if ExportHandler.export_json(duplicated, dest_path):
                self.material_table.loader.reload()
                self.material_table.base_materials = list(
                    self.material_table.loader.get_all_materials().values())
                self.material_table._update_layout()
                self.material_table.update()
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    def _on_alloy_selected(self, alloy):
        """Handle alloy selection"""
        self.alloy_info.update_alloy(alloy)
        self.alloy_control.set_item_selected(alloy is not None)

    def _on_alloy_add(self):
        """Handle alloy add request"""
        dialog = DataEditorDialog(DataCategory.ALLOYS, parent=self)
        if dialog.exec():
            self.alloy_table.reload_data()
            self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))

    def _on_alloy_edit(self):
        """Handle alloy edit request"""
        if self.alloy_table.selected_alloy:
            dialog = DataEditorDialog(
                DataCategory.ALLOYS,
                existing_data=self.alloy_table.selected_alloy,
                parent=self
            )
            if dialog.exec():
                self.alloy_table.reload_data()

    def _on_alloy_remove(self):
        """Handle alloy remove request"""
        if self.alloy_table.selected_alloy:
            name = self.alloy_table.selected_alloy.get('name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Alloy",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                manager = get_data_manager()
                filename = self.alloy_table.selected_alloy.get('_filename', name.replace(' ', '_'))
                if manager.remove_item(DataCategory.ALLOYS, filename):
                    self.alloy_table.reload_data()
                    self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))
                    self.alloy_info.show_default()
                    self.alloy_control.set_item_selected(False)

    def _on_alloy_reset(self):
        """Handle alloy reset request"""
        reply = QMessageBox.question(
            self, "Reset Alloys",
            "Are you sure you want to reset all alloys to defaults?\nThis will remove any custom alloys.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            manager = get_data_manager()
            if manager.reset_category(DataCategory.ALLOYS):
                self.alloy_table.reload_data()
                self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))
                self.alloy_info.show_default()
                QMessageBox.information(self, "Success", "Alloys reset to defaults.")

    def _on_alloy_create(self):
        """Handle alloy creation from elements"""
        dialog = AlloyCreationDialog(self)
        dialog.alloy_created.connect(lambda: self._on_alloy_created())
        dialog.exec()

    def _on_alloy_created(self):
        """Called when a new alloy is created"""
        self.alloy_table.reload_data()
        self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))

    def _on_alloy_data_saved(self, data):
        """Called when alloy data is saved via inline editor"""
        self.alloy_table.reload_data()
        self.alloy_info.show_default()
        self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))

    def _on_alloy_export(self):
        """Handle alloy export request"""
        if hasattr(self.alloy_table, 'selected_alloy') and self.alloy_table.selected_alloy:
            from periodica_app.ui.action_handler import ExportHandler

            alloy = self.alloy_table.selected_alloy
            name = alloy.get('name', 'alloy')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(alloy, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_alloy_import(self):
        """Handle alloy import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Alloy", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                manager = get_data_manager()
                name = data.get('name', 'Imported')
                if manager.add_item(DataCategory.ALLOYS, name.replace(' ', '_'), data):
                    self.alloy_table.reload_data()
                    self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported alloy")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_alloy_duplicate(self):
        """Handle alloy duplicate request"""
        if hasattr(self.alloy_table, 'selected_alloy') and self.alloy_table.selected_alloy:
            from periodica_app.ui.action_handler import DuplicateHandler

            alloy = self.alloy_table.selected_alloy
            duplicated = DuplicateHandler.duplicate_item(alloy, name_key='name')
            manager = get_data_manager()
            name = duplicated.get('name', 'Unknown')
            if manager.add_item(DataCategory.ALLOYS, name.replace(' ', '_'), duplicated):
                self.alloy_table.reload_data()
                self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    def _on_alloy_ai_generate(self):
        """Handle AI-powered alloy generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog

        dialog = AIGenerationDialog("alloy", self)
        dialog.asset_generated.connect(self._on_alloy_ai_generated)
        dialog.exec()

    def _on_alloy_ai_generated(self, config: dict):
        """Handle AI-generated alloy configuration"""
        manager = get_data_manager()
        name = config.get('name', 'AI_Generated_Alloy')
        logger = get_report_logger()
        if manager.add_item(DataCategory.ALLOYS, name.replace(' ', '_'), config):
            self.alloy_table.reload_data()
            self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))
            report_path = logger.log_ai_generation("alloy", name, True, config)
            self.statusBar().showMessage(f"AI generated alloy '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("alloy", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI alloy - report: {report_path}", 5000)

    # ==================== AI GENERATION HANDLERS ====================

    def _on_atom_ai_generate(self):
        """Handle AI-powered element generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("element", self)
        dialog.asset_generated.connect(self._on_atom_ai_generated)
        dialog.exec()

    def _on_atom_ai_generated(self, config: dict):
        """Handle AI-generated element configuration"""
        manager = get_data_manager()
        name = config.get('name', 'AI_Generated_Element')
        z = config.get('atomic_number', 999)
        symbol = config.get('symbol', 'X')
        filename = f"{z:03d}_{symbol}"
        logger = get_report_logger()
        if manager.add_item(DataCategory.ELEMENTS, filename, config):
            self.atom_table.reload_data()
            self.atom_control.update_item_count(len(self.atom_table.base_elements))
            report_path = logger.log_ai_generation("element", name, True, config)
            self.statusBar().showMessage(f"AI generated element '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("element", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI element - report: {report_path}", 5000)

    def _on_material_ai_generate(self):
        """Handle AI-powered material generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("material", self)
        dialog.asset_generated.connect(self._on_material_ai_generated)
        dialog.exec()

    def _on_material_ai_generated(self, config: dict):
        """Handle AI-generated material configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('Name', config.get('name', 'AI_Generated_Material'))
        dest_path = Path(__file__).parent / "data" / "active" / "materials" / f"{name.replace(' ', '_')}.json"
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            self.material_table.loader.reload()
            self.material_table.base_materials = list(
                self.material_table.loader.get_all_materials().values())
            self.material_table._update_layout()
            self.material_table.update()
            report_path = logger.log_ai_generation("material", name, True, config)
            self.statusBar().showMessage(f"AI generated material '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("material", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI material - report: {report_path}", 5000)

    def _on_quark_ai_generate(self):
        """Handle AI-powered quark generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("quark", self)
        dialog.asset_generated.connect(self._on_quark_ai_generated)
        dialog.exec()

    def _on_quark_ai_generated(self, config: dict):
        """Handle AI-generated quark configuration"""
        manager = get_data_manager()
        name = config.get('Name', config.get('name', 'AI_Generated_Quark'))
        logger = get_report_logger()
        if manager.add_item(DataCategory.QUARKS, name.replace(' ', '_'), config):
            self.quark_table.reload_data()
            self.quark_control.update_item_count(len(self.quark_table.base_particles))
            report_path = logger.log_ai_generation("quark", name, True, config)
            self.statusBar().showMessage(f"AI generated quark '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("quark", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI quark - report: {report_path}", 5000)

    def _on_subatomic_ai_generate(self):
        """Handle AI-powered subatomic particle generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("subatomic", self)
        dialog.asset_generated.connect(self._on_subatomic_ai_generated)
        dialog.exec()

    def _on_subatomic_ai_generated(self, config: dict):
        """Handle AI-generated subatomic configuration"""
        manager = get_data_manager()
        name = config.get('Name', config.get('name', 'AI_Generated_Hadron'))
        logger = get_report_logger()
        if manager.add_item(DataCategory.SUBATOMIC, name.replace(' ', '_'), config):
            self.subatomic_table.reload_data()
            self.subatomic_control.update_item_count(len(self.subatomic_table.particles))
            report_path = logger.log_ai_generation("subatomic", name, True, config)
            self.statusBar().showMessage(f"AI generated particle '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("subatomic", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI particle - report: {report_path}", 5000)

    def _on_molecule_ai_generate(self):
        """Handle AI-powered molecule generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("molecule", self)
        dialog.asset_generated.connect(self._on_molecule_ai_generated)
        dialog.exec()

    def _on_molecule_ai_generated(self, config: dict):
        """Handle AI-generated molecule configuration"""
        manager = get_data_manager()
        name = config.get('Name', config.get('name', 'AI_Generated_Molecule'))
        logger = get_report_logger()
        if manager.add_item(DataCategory.MOLECULES, name.replace(' ', '_'), config):
            self.molecule_table.reload_data()
            self.molecule_control.update_item_count(len(self.molecule_table.base_molecules))
            report_path = logger.log_ai_generation("molecule", name, True, config)
            self.statusBar().showMessage(f"AI generated molecule '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("molecule", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI molecule - report: {report_path}", 5000)

    def _on_amino_acid_ai_generate(self):
        """Handle AI-powered amino acid generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("amino_acid", self)
        dialog.asset_generated.connect(self._on_amino_acid_ai_generated)
        dialog.exec()

    def _on_amino_acid_ai_generated(self, config: dict):
        """Handle AI-generated amino acid configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Generated_AminoAcid')
        dest_path = Path(__file__).parent / "data" / "active" / "amino_acids" / f"{name.replace(' ', '_')}.json"
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            self.amino_acid_table.refresh()
            self.amino_acid_control.update_item_count(self.amino_acid_table.get_amino_acid_count())
            report_path = logger.log_ai_generation("amino_acid", name, True, config)
            self.statusBar().showMessage(f"AI generated amino acid '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("amino_acid", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI amino acid - report: {report_path}", 5000)

    def _on_amino_acid_ai_update(self):
        """Handle AI-powered amino acid update"""
        selected = self.amino_acid_table.get_selected_amino_acid()
        if selected:
            from periodica_app.ui.ai_update_dialog import AIUpdateDialog
            dialog = AIUpdateDialog("amino_acid", selected, self)
            dialog.asset_updated.connect(self._on_amino_acid_ai_updated)
            dialog.exec()

    def _on_amino_acid_ai_updated(self, config: dict):
        """Handle AI-updated amino acid configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Updated_AminoAcid')
        dest_path = Path(__file__).parent / "data" / "active" / "amino_acids" / f"{name.replace(' ', '_')}.json"
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            self.amino_acid_table.refresh()
            self.amino_acid_control.update_item_count(self.amino_acid_table.get_amino_acid_count())
            report_path = logger.log_ai_generation("amino_acid", name, True, config)
            self.statusBar().showMessage(f"AI updated amino acid '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("amino_acid", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI-updated amino acid - report: {report_path}", 5000)

    def _on_protein_ai_generate(self):
        """Handle AI-powered protein generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("protein", self)
        dialog.asset_generated.connect(self._on_protein_ai_generated)
        dialog.exec()

    def _on_protein_ai_generated(self, config: dict):
        """Handle AI-generated protein configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Generated_Protein')
        dest_path = Path(__file__).parent / "data" / "active" / "proteins" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.protein_table, 'refresh'):
                self.protein_table.refresh()
            report_path = logger.log_ai_generation("protein", name, True, config)
            self.statusBar().showMessage(f"AI generated protein '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("protein", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI protein - report: {report_path}", 5000)

    def _on_protein_ai_update(self):
        """Handle AI-powered protein update"""
        selected = self.protein_table.get_selected_protein()
        if selected:
            from periodica_app.ui.ai_update_dialog import AIUpdateDialog
            dialog = AIUpdateDialog("protein", selected, self)
            dialog.asset_updated.connect(self._on_protein_ai_updated)
            dialog.exec()

    def _on_protein_ai_updated(self, config: dict):
        """Handle AI-updated protein configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Updated_Protein')
        dest_path = Path(__file__).parent / "data" / "active" / "proteins" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.protein_table, 'refresh'):
                self.protein_table.refresh()
            report_path = logger.log_ai_generation("protein", name, True, config)
            self.statusBar().showMessage(f"AI updated protein '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("protein", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI-updated protein - report: {report_path}", 5000)

    def _on_protein_add(self):
        """Handle protein add request"""
        QMessageBox.information(self, "Add Protein",
            "Protein creation will be available soon.\n"
            "For now, please add proteins via JSON files in data/active/proteins/\n"
            "or use the AI Generate feature.")

    def _on_protein_edit(self):
        """Handle protein edit request"""
        selected = self.protein_table.get_selected_protein()
        if selected:
            QMessageBox.information(self, "Edit Protein",
                "Protein editing will be available soon.\n"
                "For now, please edit the JSON files directly in data/active/proteins/")

    def _on_protein_remove(self):
        """Handle protein remove request"""
        selected = self.protein_table.get_selected_protein()
        if selected:
            name = selected.get('name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Protein",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import os
                protein_dir = Path(__file__).parent / "data" / "active" / "proteins"
                for f in protein_dir.glob("*.json"):
                    if f.stem == name.replace(' ', '_') or f.stem.replace('_', ' ') == name:
                        os.remove(f)
                        self.protein_table.refresh()
                        self.protein_control.set_item_selected(False)
                        self.protein_control.update_item_count(
                            self.protein_table.get_protein_count())
                        break

    def _on_protein_reset(self):
        """Handle protein reset request"""
        reply = QMessageBox.question(
            self, "Reset Proteins",
            "Are you sure you want to reset all proteins to defaults?\nThis will remove any custom proteins.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.protein_table.refresh()
            self.protein_control.update_item_count(self.protein_table.get_protein_count())
            QMessageBox.information(self, "Success", "Proteins reset to defaults.")

    def _on_protein_export(self):
        """Handle protein export request"""
        from periodica_app.ui.action_handler import ExportHandler

        selected = self.protein_table.get_selected_protein()
        if selected:
            name = selected.get('name', 'protein')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(selected, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_protein_import(self):
        """Handle protein import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Protein", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                name = data.get('name', 'Imported')
                dest_path = Path(__file__).parent / "data" / "active" / "proteins" / f"{name.replace(' ', '_')}.json"
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                if ExportHandler.export_json(data, dest_path):
                    self.protein_table.refresh()
                    self.protein_control.update_item_count(self.protein_table.get_protein_count())
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported protein")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_protein_duplicate(self):
        """Handle protein duplicate request"""
        from periodica_app.ui.action_handler import DuplicateHandler, ExportHandler

        selected = self.protein_table.get_selected_protein()
        if selected:
            duplicated = DuplicateHandler.duplicate_item(selected, name_key='name')
            name = duplicated.get('name', 'Unknown')
            dest_path = Path(__file__).parent / "data" / "active" / "proteins" / f"{name.replace(' ', '_')}.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if ExportHandler.export_json(duplicated, dest_path):
                self.protein_table.refresh()
                self.protein_control.update_item_count(self.protein_table.get_protein_count())
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    def _on_nucleic_acid_ai_generate(self):
        """Handle AI-powered nucleic acid generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("nucleic_acid", self)
        dialog.asset_generated.connect(self._on_nucleic_acid_ai_generated)
        dialog.exec()

    def _on_nucleic_acid_ai_generated(self, config: dict):
        """Handle AI-generated nucleic acid configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Generated_NucleicAcid')
        dest_path = Path(__file__).parent / "data" / "active" / "nucleic_acids" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.nucleic_acid_table, 'refresh'):
                self.nucleic_acid_table.refresh()
            report_path = logger.log_ai_generation("nucleic_acid", name, True, config)
            self.statusBar().showMessage(f"AI generated nucleic acid '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("nucleic_acid", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI nucleic acid - report: {report_path}", 5000)

    def _on_nucleic_acid_ai_update(self):
        """Handle AI-powered nucleic acid update"""
        selected = self.nucleic_acid_table.get_selected_nucleic_acid()
        if selected:
            from periodica_app.ui.ai_update_dialog import AIUpdateDialog
            dialog = AIUpdateDialog("nucleic_acid", selected, self)
            dialog.asset_updated.connect(self._on_nucleic_acid_ai_updated)
            dialog.exec()

    def _on_nucleic_acid_ai_updated(self, config: dict):
        """Handle AI-updated nucleic acid configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Updated_NucleicAcid')
        dest_path = Path(__file__).parent / "data" / "active" / "nucleic_acids" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.nucleic_acid_table, 'refresh'):
                self.nucleic_acid_table.refresh()
            report_path = logger.log_ai_generation("nucleic_acid", name, True, config)
            self.statusBar().showMessage(f"AI updated nucleic acid '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("nucleic_acid", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI-updated nucleic acid - report: {report_path}", 5000)

    def _on_nucleic_acid_add(self):
        """Handle nucleic acid add request"""
        QMessageBox.information(self, "Add Nucleic Acid",
            "Nucleic acid creation will be available soon.\n"
            "For now, please add nucleic acids via JSON files in data/active/nucleic_acids/")

    def _on_nucleic_acid_edit(self):
        """Handle nucleic acid edit request"""
        selected = self.nucleic_acid_table.get_selected_nucleic_acid()
        if selected:
            QMessageBox.information(self, "Edit Nucleic Acid",
                "Nucleic acid editing will be available soon.\n"
                "For now, please edit the JSON files directly.")

    def _on_nucleic_acid_remove(self):
        """Handle nucleic acid remove request"""
        selected = self.nucleic_acid_table.get_selected_nucleic_acid()
        if selected:
            name = selected.get('name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Nucleic Acid",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import os
                na_dir = Path(__file__).parent / "data" / "active" / "nucleic_acids"
                for f in na_dir.glob("*.json"):
                    if f.stem == name or f.stem.replace('_', ' ') == name:
                        os.remove(f)
                        self.nucleic_acid_table.refresh()
                        self.nucleic_acid_info.set_nucleic_acid(None)
                        self.nucleic_acid_control.set_item_selected(False)
                        self.nucleic_acid_control.update_item_count(
                            self.nucleic_acid_table.get_nucleic_acid_count())
                        break

    def _on_nucleic_acid_reset(self):
        """Handle nucleic acid reset request"""
        reply = QMessageBox.question(
            self, "Reset Nucleic Acids",
            "Are you sure you want to reset all nucleic acids to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.nucleic_acid_table.refresh()
            self.nucleic_acid_info.set_nucleic_acid(None)
            QMessageBox.information(self, "Success", "Nucleic acids reset to defaults.")

    def _on_nucleic_acid_export(self):
        """Handle nucleic acid export request"""
        selected = self.nucleic_acid_table.get_selected_nucleic_acid()
        if selected:
            from periodica_app.ui.action_handler import ExportHandler

            name = selected.get('name', 'nucleic_acid')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(selected, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_nucleic_acid_import(self):
        """Handle nucleic acid import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Nucleic Acid", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                name = data.get('name', 'Imported')
                dest_path = Path(__file__).parent / "data" / "active" / "nucleic_acids" / f"{name.replace(' ', '_')}.json"
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                if ExportHandler.export_json(data, dest_path):
                    self.nucleic_acid_table.refresh()
                    self.nucleic_acid_control.update_item_count(
                        self.nucleic_acid_table.get_nucleic_acid_count())
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported nucleic acid")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_nucleic_acid_duplicate(self):
        """Handle nucleic acid duplicate request"""
        selected = self.nucleic_acid_table.get_selected_nucleic_acid()
        if selected:
            from periodica_app.ui.action_handler import DuplicateHandler, ExportHandler

            duplicated = DuplicateHandler.duplicate_item(selected, name_key='name')
            name = duplicated.get('name', 'Unknown')
            dest_path = Path(__file__).parent / "data" / "active" / "nucleic_acids" / f"{name.replace(' ', '_')}.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if ExportHandler.export_json(duplicated, dest_path):
                self.nucleic_acid_table.refresh()
                self.nucleic_acid_control.update_item_count(
                    self.nucleic_acid_table.get_nucleic_acid_count())
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    def _on_cell_component_ai_generate(self):
        """Handle AI-powered cell component generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("cell_component", self)
        dialog.asset_generated.connect(self._on_cell_component_ai_generated)
        dialog.exec()

    def _on_cell_component_ai_generated(self, config: dict):
        """Handle AI-generated cell component configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Generated_Component')
        dest_path = Path(__file__).parent / "data" / "active" / "cell_components" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.cell_component_table, 'refresh'):
                self.cell_component_table.refresh()
            self.cell_component_control.set_component_count(self.cell_component_table.get_component_count())
            report_path = logger.log_ai_generation("cell_component", name, True, config)
            self.statusBar().showMessage(f"AI generated component '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("cell_component", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI component - report: {report_path}", 5000)

    def _on_cell_component_ai_update(self):
        """Handle AI-powered cell component update"""
        selected = self.cell_component_table.get_selected_component()
        if selected:
            from periodica_app.ui.ai_update_dialog import AIUpdateDialog
            dialog = AIUpdateDialog("cell_component", selected, self)
            dialog.asset_updated.connect(self._on_cell_component_ai_updated)
            dialog.exec()

    def _on_cell_component_ai_updated(self, config: dict):
        """Handle AI-updated cell component configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Updated_Component')
        dest_path = Path(__file__).parent / "data" / "active" / "cell_components" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.cell_component_table, 'refresh'):
                self.cell_component_table.refresh()
            self.cell_component_control.set_component_count(self.cell_component_table.get_component_count())
            report_path = logger.log_ai_generation("cell_component", name, True, config)
            self.statusBar().showMessage(f"AI updated component '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("cell_component", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI-updated component - report: {report_path}", 5000)

    def _on_cell_component_add(self):
        """Handle cell component add request"""
        from periodica_app.ui.action_handler import ExportHandler
        # Create a new blank component template
        new_component = {
            "name": "New_Component",
            "type": "other",
            "function": "Unknown",
            "compartment": "cytoplasm",
            "diameter_nm": 100,
            "mass_kda": 50,
            "copy_number": 1000,
            "description": "New cell component"
        }
        dest_path = Path(__file__).parent / "data" / "active" / "cell_components" / "New_Component.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # Find unique name if file exists
        counter = 1
        while dest_path.exists():
            new_component["name"] = f"New_Component_{counter}"
            dest_path = Path(__file__).parent / "data" / "active" / "cell_components" / f"New_Component_{counter}.json"
            counter += 1
        if ExportHandler.export_json(new_component, dest_path):
            self.cell_component_table.refresh()
            self.cell_component_control.set_component_count(self.cell_component_table.get_component_count())
            self.statusBar().showMessage(f"Created new component: {new_component['name']}", 3000)
        else:
            QMessageBox.warning(self, "Error", "Failed to create new component")

    def _on_cell_component_edit(self):
        """Handle cell component edit request"""
        selected = self.cell_component_table.get_selected_component()
        if selected:
            from periodica_app.ui.json_editor_dialog import JSONEditorDialog
            dialog = JSONEditorDialog(selected, f"Edit {selected.get('name', 'Component')}", self)
            if dialog.exec():
                from periodica_app.ui.action_handler import ExportHandler
                edited_data = dialog.get_data()
                name = edited_data.get('name', 'Component')
                dest_path = Path(__file__).parent / "data" / "active" / "cell_components" / f"{name.replace(' ', '_')}.json"
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                # Remove old file if name changed
                old_name = selected.get('name', '')
                if old_name and old_name != name:
                    old_path = Path(__file__).parent / "data" / "active" / "cell_components" / f"{old_name.replace(' ', '_')}.json"
                    if old_path.exists():
                        import os
                        os.remove(old_path)
                if ExportHandler.export_json(edited_data, dest_path):
                    self.cell_component_table.refresh()
                    self.cell_component_control.set_component_count(self.cell_component_table.get_component_count())
                    self.statusBar().showMessage(f"Updated component: {name}", 3000)
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save component '{name}'")

    def _on_cell_component_remove(self):
        """Handle cell component remove request"""
        selected = self.cell_component_table.get_selected_component()
        if selected:
            name = selected.get('name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Cell Component",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import os
                comp_dir = Path(__file__).parent / "data" / "active" / "cell_components"
                for f in comp_dir.glob("*.json"):
                    if f.stem == name or f.stem.replace('_', ' ') == name:
                        os.remove(f)
                        self.cell_component_table.refresh()
                        self.cell_component_info.set_component(None)
                        self.cell_component_control.set_item_selected(False)
                        self.cell_component_control.set_component_count(
                            self.cell_component_table.get_component_count())
                        self.statusBar().showMessage(f"Removed component: {name}", 3000)
                        break

    def _on_cell_component_reset(self):
        """Handle cell component reset request"""
        reply = QMessageBox.question(
            self, "Reset Cell Components",
            "Are you sure you want to reset all cell components to defaults?\nThis will remove any custom components.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            import shutil
            active_dir = Path(__file__).parent / "data" / "active" / "cell_components"
            defaults_dir = Path(__file__).parent / "data" / "defaults" / "cell_components"
            # Clear active directory
            if active_dir.exists():
                shutil.rmtree(active_dir)
            # Copy defaults if they exist
            if defaults_dir.exists():
                shutil.copytree(defaults_dir, active_dir)
            else:
                active_dir.mkdir(parents=True, exist_ok=True)
            self.cell_component_table.refresh()
            self.cell_component_info.set_component(None)
            self.cell_component_control.set_component_count(self.cell_component_table.get_component_count())
            QMessageBox.information(self, "Success", "Cell components reset to defaults.")

    def _on_cell_component_export(self):
        """Handle cell component export request"""
        selected = self.cell_component_table.get_selected_component()
        if selected:
            from periodica_app.ui.action_handler import ExportHandler
            name = selected.get('name', 'component')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(selected, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_cell_component_import(self):
        """Handle cell component import request"""
        from periodica_app.ui.action_handler import ExportHandler
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Cell Component", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                name = data.get('name', 'Imported_Component')
                dest_path = Path(__file__).parent / "data" / "active" / "cell_components" / f"{name.replace(' ', '_')}.json"
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                if ExportHandler.export_json(data, dest_path):
                    self.cell_component_table.refresh()
                    self.cell_component_control.set_component_count(self.cell_component_table.get_component_count())
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported component")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_cell_component_duplicate(self):
        """Handle cell component duplicate request"""
        selected = self.cell_component_table.get_selected_component()
        if selected:
            from periodica_app.ui.action_handler import DuplicateHandler, ExportHandler
            duplicated = DuplicateHandler.duplicate_item(selected, name_key='name')
            name = duplicated.get('name', 'Unknown')
            dest_path = Path(__file__).parent / "data" / "active" / "cell_components" / f"{name.replace(' ', '_')}.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if ExportHandler.export_json(duplicated, dest_path):
                self.cell_component_table.refresh()
                self.cell_component_control.set_component_count(self.cell_component_table.get_component_count())
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    def _on_cell_ai_generate(self):
        """Handle AI-powered cell generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("cell", self)
        dialog.asset_generated.connect(self._on_cell_ai_generated)
        dialog.exec()

    def _on_cell_ai_generated(self, config: dict):
        """Handle AI-generated cell configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Generated_Cell')
        dest_path = Path(__file__).parent / "data" / "active" / "cells" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.cell_table, 'refresh'):
                self.cell_table.refresh()
            self.cell_control.set_cell_count(self.cell_table.get_cell_count())
            report_path = logger.log_ai_generation("cell", name, True, config)
            self.statusBar().showMessage(f"AI generated cell '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("cell", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI cell - report: {report_path}", 5000)

    def _on_cell_ai_update(self):
        """Handle AI-powered cell update"""
        selected = self.cell_table.get_selected_cell()
        if selected:
            from periodica_app.ui.ai_update_dialog import AIUpdateDialog
            dialog = AIUpdateDialog("cell", selected, self)
            dialog.asset_updated.connect(self._on_cell_ai_updated)
            dialog.exec()

    def _on_cell_ai_updated(self, config: dict):
        """Handle AI-updated cell configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Updated_Cell')
        dest_path = Path(__file__).parent / "data" / "active" / "cells" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.cell_table, 'refresh'):
                self.cell_table.refresh()
            self.cell_control.set_cell_count(self.cell_table.get_cell_count())
            report_path = logger.log_ai_generation("cell", name, True, config)
            self.statusBar().showMessage(f"AI updated cell '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("cell", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI-updated cell - report: {report_path}", 5000)

    def _on_cell_add(self):
        """Handle cell add request"""
        QMessageBox.information(self, "Add Cell",
            "Cell creation will be available soon.\n"
            "For now, please add cells via JSON files in data/active/cells/")

    def _on_cell_edit(self):
        """Handle cell edit request"""
        selected = self.cell_table.get_selected_cell()
        if selected:
            QMessageBox.information(self, "Edit Cell",
                f"Editing '{selected.get('name', 'Unknown')}' will be available soon.\n"
                "For now, please edit the JSON file directly in data/active/cells/")

    def _on_cell_remove(self):
        """Handle cell remove request"""
        selected = self.cell_table.get_selected_cell()
        if selected:
            name = selected.get('name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Cell",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import os
                cell_dir = Path(__file__).parent / "data" / "active" / "cells"
                for f in cell_dir.glob("*.json"):
                    if f.stem == name or f.stem.replace('_', ' ') == name:
                        os.remove(f)
                        self.cell_table.refresh()
                        self.cell_info.set_cell(None)
                        self.cell_control.set_cell_count(self.cell_table.get_cell_count())
                        self.statusBar().showMessage(f"Removed cell '{name}'", 3000)
                        break

    def _on_cell_reset(self):
        """Handle cell reset request"""
        reply = QMessageBox.question(
            self, "Reset Cells",
            "Are you sure you want to reset all cells to defaults?\n"
            "This will remove any custom cells you have added.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            import shutil
            cell_dir = Path(__file__).parent / "data" / "active" / "cells"
            # Remove custom cells (keep defaults)
            if cell_dir.exists():
                for f in cell_dir.glob("*.json"):
                    f.unlink()
            self.cell_table.refresh()
            self.cell_info.set_cell(None)
            self.cell_control.set_cell_count(self.cell_table.get_cell_count())
            QMessageBox.information(self, "Success", "Cells reset to defaults.")

    def _on_cell_export(self):
        """Handle cell export request"""
        selected = self.cell_table.get_selected_cell()
        if selected:
            from periodica_app.ui.action_handler import ExportHandler

            name = selected.get('name', 'cell')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(selected, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_cell_import(self):
        """Handle cell import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Cell", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                name = data.get('name', 'Imported')
                dest_path = Path(__file__).parent / "data" / "active" / "cells" / f"{name.replace(' ', '_')}.json"
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                if ExportHandler.export_json(data, dest_path):
                    self.cell_table.refresh()
                    self.cell_control.set_cell_count(self.cell_table.get_cell_count())
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported cell")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_cell_duplicate(self):
        """Handle cell duplicate request"""
        selected = self.cell_table.get_selected_cell()
        if selected:
            from periodica_app.ui.action_handler import DuplicateHandler, ExportHandler

            duplicated = DuplicateHandler.duplicate_item(selected, name_key='name')
            name = duplicated.get('name', 'Unknown')
            dest_path = Path(__file__).parent / "data" / "active" / "cells" / f"{name.replace(' ', '_')}.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if ExportHandler.export_json(duplicated, dest_path):
                self.cell_table.refresh()
                self.cell_control.set_cell_count(self.cell_table.get_cell_count())
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    def _on_biomaterial_ai_generate(self):
        """Handle AI-powered biomaterial generation"""
        from periodica_app.ui.ai_generation_dialog import AIGenerationDialog
        dialog = AIGenerationDialog("biomaterial", self)
        dialog.asset_generated.connect(self._on_biomaterial_ai_generated)
        dialog.exec()

    def _on_biomaterial_ai_generated(self, config: dict):
        """Handle AI-generated biomaterial configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Generated_Biomaterial')
        dest_path = Path(__file__).parent / "data" / "active" / "biomaterials" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.biomaterial_table, 'refresh'):
                self.biomaterial_table.refresh()
            self.biomaterial_control.set_material_count(self.biomaterial_table.get_material_count())
            report_path = logger.log_ai_generation("biomaterial", name, True, config)
            self.statusBar().showMessage(f"AI generated biomaterial '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("biomaterial", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI biomaterial - report: {report_path}", 5000)

    def _on_biomaterial_ai_update(self):
        """Handle AI-powered biomaterial update"""
        selected = self.biomaterial_table.get_selected_material()
        if selected:
            from periodica_app.ui.ai_update_dialog import AIUpdateDialog
            dialog = AIUpdateDialog("biomaterial", selected, self)
            dialog.asset_updated.connect(self._on_biomaterial_ai_updated)
            dialog.exec()

    def _on_biomaterial_ai_updated(self, config: dict):
        """Handle AI-updated biomaterial configuration"""
        from periodica_app.ui.action_handler import ExportHandler
        name = config.get('name', 'AI_Updated_Biomaterial')
        dest_path = Path(__file__).parent / "data" / "active" / "biomaterials" / f"{name.replace(' ', '_')}.json"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger = get_report_logger()
        if ExportHandler.export_json(config, dest_path):
            if hasattr(self.biomaterial_table, 'refresh'):
                self.biomaterial_table.refresh()
            self.biomaterial_control.set_material_count(self.biomaterial_table.get_material_count())
            report_path = logger.log_ai_generation("biomaterial", name, True, config)
            self.statusBar().showMessage(f"AI updated biomaterial '{name}' - report: {report_path}", 5000)
        else:
            report_path = logger.log_ai_generation("biomaterial", name, False, error="Failed to save")
            self.statusBar().showMessage(f"Failed to save AI-updated biomaterial - report: {report_path}", 5000)

    def _on_biomaterial_add(self):
        """Handle biomaterial add request"""
        QMessageBox.information(self, "Add Biomaterial",
            "Biomaterial creation will be available soon.\n"
            "For now, please add biomaterials via JSON files in data/active/biomaterials/")

    def _on_biomaterial_edit(self):
        """Handle biomaterial edit request"""
        material = self.biomaterial_table.get_selected_material()
        if material:
            QMessageBox.information(self, "Edit Biomaterial",
                "Biomaterial editing will be available soon.\n"
                "For now, please edit the JSON files directly.")

    def _on_biomaterial_remove(self):
        """Handle biomaterial remove request"""
        material = self.biomaterial_table.get_selected_material()
        if material:
            name = material.get('name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Biomaterial",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import os
                mat_dir = Path(__file__).parent / "data" / "active" / "biomaterials"
                for f in mat_dir.glob("*.json"):
                    if f.stem.replace('_', ' ') == name or name.replace(' ', '_') == f.stem:
                        os.remove(f)
                        self.biomaterial_table.refresh()
                        self.biomaterial_control.set_material_count(self.biomaterial_table.get_material_count())
                        self.biomaterial_info.set_material(None)
                        self.biomaterial_control.set_item_selected(False)
                        QMessageBox.information(self, "Success", f"Removed '{name}'")
                        break

    def _on_biomaterial_reset(self):
        """Handle biomaterial reset request"""
        reply = QMessageBox.question(
            self, "Reset Biomaterials",
            "Are you sure you want to reset all biomaterials to defaults?\nThis will remove any custom biomaterials.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            import shutil
            active_dir = Path(__file__).parent / "data" / "active" / "biomaterials"
            default_dir = Path(__file__).parent / "data" / "default" / "biomaterials"
            if active_dir.exists():
                shutil.rmtree(active_dir)
            if default_dir.exists():
                shutil.copytree(default_dir, active_dir)
            else:
                active_dir.mkdir(parents=True, exist_ok=True)
            self.biomaterial_table.refresh()
            self.biomaterial_control.set_material_count(self.biomaterial_table.get_material_count())
            self.biomaterial_info.set_material(None)
            QMessageBox.information(self, "Success", "Biomaterials reset to defaults.")

    def _on_biomaterial_export(self):
        """Handle biomaterial export request"""
        material = self.biomaterial_table.get_selected_material()
        if material:
            from periodica_app.ui.action_handler import ExportHandler

            name = material.get('name', 'biomaterial')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(material, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_biomaterial_import(self):
        """Handle biomaterial import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Biomaterial", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                name = data.get('name', 'Imported')
                dest_path = Path(__file__).parent / "data" / "active" / "biomaterials" / f"{name.replace(' ', '_')}.json"
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                if ExportHandler.export_json(data, dest_path):
                    self.biomaterial_table.refresh()
                    self.biomaterial_control.set_material_count(self.biomaterial_table.get_material_count())
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported biomaterial")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_biomaterial_duplicate(self):
        """Handle biomaterial duplicate request"""
        material = self.biomaterial_table.get_selected_material()
        if material:
            from periodica_app.ui.action_handler import DuplicateHandler, ExportHandler

            duplicated = DuplicateHandler.duplicate_item(material, name_key='name')
            name = duplicated.get('name', 'Unknown')
            dest_path = Path(__file__).parent / "data" / "active" / "biomaterials" / f"{name.replace(' ', '_')}.json"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if ExportHandler.export_json(duplicated, dest_path):
                self.biomaterial_table.refresh()
                self.biomaterial_control.set_material_count(self.biomaterial_table.get_material_count())
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    def _on_ai_settings(self):
        """Open AI settings dialog"""
        from periodica_app.ui.api_settings_dialog import APISettingsDialog

        dialog = APISettingsDialog(self)
        dialog.api_key_changed.connect(self._on_api_key_changed)
        dialog.exec()

    def _on_api_key_changed(self, configured: bool):
        """Handle API key configuration change"""
        # Refresh AI status in all control panels that have AI widgets
        control_panels = [
            'atom_control', 'alloy_control', 'protein_control', 'nucleic_acid_control',
            'molecule_control', 'cell_control', 'biomaterial_control',
            'material_control', 'subatomic_control', 'quark_control',
            'amino_acid_control', 'cell_component_control'
        ]
        for panel_name in control_panels:
            if hasattr(self, panel_name):
                panel = getattr(self, panel_name)
                if hasattr(panel, 'refresh_ai_status'):
                    panel.refresh_ai_status()

    # ==================== ATOMS TAB HANDLERS ====================

    def _on_atom_selected(self, element):
        """Handle atom selection"""
        self.atom_info.update_element(element)
        self.atom_control.set_item_selected(element is not None)

    def _on_atom_add(self):
        """Handle atom add request - show inline editor"""
        # Get selected element as template if available
        template = None
        if hasattr(self.atom_table, 'selected_element'):
            template = self.atom_table.selected_element
        self.atom_info.start_add(template)

    def _on_atom_edit(self):
        """Handle atom edit request - show inline editor"""
        if hasattr(self.atom_table, 'selected_element') and self.atom_table.selected_element:
            self.atom_info.start_edit(self.atom_table.selected_element)

    def _on_atom_remove(self):
        """Handle atom remove request"""
        if hasattr(self.atom_table, 'selected_element') and self.atom_table.selected_element:
            elem = self.atom_table.selected_element
            name = elem.get('name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Element",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                manager = get_data_manager()
                z = elem.get('atomic_number', 0)
                symbol = elem.get('symbol', 'X')
                filename = f"{z:03d}_{symbol}"
                if manager.remove_item(DataCategory.ELEMENTS, filename):
                    self.atom_table.reload_data()
                    self.atom_info.show_default()
                    self.atom_control.set_item_selected(False)

    def _on_atom_reset(self):
        """Handle atom reset request"""
        reply = QMessageBox.question(
            self, "Reset Elements",
            "Are you sure you want to reset all elements to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            manager = get_data_manager()
            if manager.reset_category(DataCategory.ELEMENTS):
                self.atom_table.reload_data()
                self.atom_info.show_default()
                QMessageBox.information(self, "Success", "Elements reset to defaults.")

    def _on_atom_create(self):
        """Handle atom creation from subatomic particles"""
        from periodica_app.ui.creation_dialog import AtomCreationDialog
        dialog = AtomCreationDialog(self)
        dialog.atom_created.connect(lambda: self._on_atom_data_saved(None))
        dialog.exec()

    def _on_atom_data_saved(self, data):
        """Called when atom data is saved"""
        self.atom_table.reload_data()
        self.atom_info.show_default()
        self.atom_control.update_item_count(len(self.atom_table.base_elements))

    def _on_atom_export(self):
        """Handle atom export request"""
        if hasattr(self.atom_table, 'selected_element') and self.atom_table.selected_element:
            from periodica_app.ui.action_handler import ExportHandler

            elem = self.atom_table.selected_element
            name = elem.get('name', 'element')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(elem, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_atom_import(self):
        """Handle atom import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Element", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                manager = get_data_manager()
                name = data.get('name', 'Imported')
                if manager.add_item(DataCategory.ELEMENTS, name.replace(' ', '_'), data):
                    self.atom_table.reload_data()
                    self.atom_control.update_item_count(len(self.atom_table.base_elements))
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported element")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_atom_duplicate(self):
        """Handle atom duplicate request"""
        if hasattr(self.atom_table, 'selected_element') and self.atom_table.selected_element:
            from periodica_app.ui.action_handler import DuplicateHandler

            elem = self.atom_table.selected_element
            duplicated = DuplicateHandler.duplicate_item(elem, name_key='name')
            manager = get_data_manager()
            name = duplicated.get('name', 'Unknown')
            if manager.add_item(DataCategory.ELEMENTS, name.replace(' ', '_'), duplicated):
                self.atom_table.reload_data()
                self.atom_control.update_item_count(len(self.atom_table.base_elements))
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    # ==================== QUARKS TAB HANDLERS ====================

    def _on_quark_selected(self, quark):
        """Handle quark selection"""
        self.quark_info.update_quark(quark)
        self.quark_control.set_item_selected(quark is not None)

    def _on_quark_add(self):
        """Handle quark add request - show inline editor"""
        template = None
        if hasattr(self.quark_table, 'selected_quark'):
            template = self.quark_table.selected_quark
        self.quark_info.start_add(template)

    def _on_quark_edit(self):
        """Handle quark edit request - show inline editor"""
        if hasattr(self.quark_table, 'selected_quark') and self.quark_table.selected_quark:
            self.quark_info.start_edit(self.quark_table.selected_quark)

    def _on_quark_remove(self):
        """Handle quark remove request"""
        if hasattr(self.quark_table, 'selected_quark') and self.quark_table.selected_quark:
            quark = self.quark_table.selected_quark
            name = quark.get('Name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Quark",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                manager = get_data_manager()
                filename = name.replace(' ', '_')
                if manager.remove_item(DataCategory.QUARKS, filename):
                    self.quark_table.reload_data()
                    self.quark_info.show_default()
                    self.quark_control.set_item_selected(False)

    def _on_quark_reset(self):
        """Handle quark reset request"""
        reply = QMessageBox.question(
            self, "Reset Quarks",
            "Are you sure you want to reset all quarks to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            manager = get_data_manager()
            if manager.reset_category(DataCategory.QUARKS):
                self.quark_table.reload_data()
                self.quark_info.show_default()
                QMessageBox.information(self, "Success", "Quarks reset to defaults.")

    def _on_quark_create(self):
        """Handle quark creation (quarks are fundamental, so just add)"""
        self.quark_info.start_add(None)

    def _on_quark_data_saved(self, data):
        """Called when quark data is saved"""
        self.quark_table.reload_data()
        self.quark_info.show_default()
        self.quark_control.update_item_count(len(self.quark_table.base_particles))

    def _on_quark_export(self):
        """Handle quark export request"""
        if hasattr(self.quark_table, 'selected_quark') and self.quark_table.selected_quark:
            from periodica_app.ui.action_handler import ExportHandler

            quark = self.quark_table.selected_quark
            name = quark.get('Name', 'quark')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(quark, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_quark_import(self):
        """Handle quark import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Quark", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                manager = get_data_manager()
                name = data.get('Name', 'Imported')
                if manager.add_item(DataCategory.QUARKS, name.replace(' ', '_'), data):
                    self.quark_table.reload_data()
                    self.quark_control.update_item_count(len(self.quark_table.base_particles))
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported quark")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_quark_duplicate(self):
        """Handle quark duplicate request"""
        if hasattr(self.quark_table, 'selected_quark') and self.quark_table.selected_quark:
            from periodica_app.ui.action_handler import DuplicateHandler

            quark = self.quark_table.selected_quark
            duplicated = DuplicateHandler.duplicate_item(quark, name_key='Name')
            manager = get_data_manager()
            name = duplicated.get('Name', 'Unknown')
            if manager.add_item(DataCategory.QUARKS, name.replace(' ', '_'), duplicated):
                self.quark_table.reload_data()
                self.quark_control.update_item_count(len(self.quark_table.base_particles))
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    # ==================== SUBATOMIC TAB HANDLERS ====================

    def _on_subatomic_selected(self, particle):
        """Handle subatomic particle selection"""
        self.subatomic_info.update_particle(particle)
        self.subatomic_control.set_item_selected(particle is not None)

    def _on_subatomic_add(self):
        """Handle subatomic add request - show inline editor"""
        template = None
        if hasattr(self.subatomic_table, 'selected_particle'):
            template = self.subatomic_table.selected_particle
        self.subatomic_info.start_add(template)

    def _on_subatomic_edit(self):
        """Handle subatomic edit request - show inline editor"""
        if hasattr(self.subatomic_table, 'selected_particle') and self.subatomic_table.selected_particle:
            self.subatomic_info.start_edit(self.subatomic_table.selected_particle)

    def _on_subatomic_remove(self):
        """Handle subatomic remove request"""
        if hasattr(self.subatomic_table, 'selected_particle') and self.subatomic_table.selected_particle:
            particle = self.subatomic_table.selected_particle
            name = particle.get('Name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Particle",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                manager = get_data_manager()
                filename = name.replace(' ', '_')
                if manager.remove_item(DataCategory.SUBATOMIC, filename):
                    self.subatomic_table.reload_data()
                    self.subatomic_info.show_default()
                    self.subatomic_control.set_item_selected(False)

    def _on_subatomic_reset(self):
        """Handle subatomic reset request"""
        reply = QMessageBox.question(
            self, "Reset Subatomic Particles",
            "Are you sure you want to reset all subatomic particles to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            manager = get_data_manager()
            if manager.reset_category(DataCategory.SUBATOMIC):
                self.subatomic_table.reload_data()
                self.subatomic_info.show_default()
                QMessageBox.information(self, "Success", "Subatomic particles reset to defaults.")

    def _on_subatomic_create(self):
        """Handle subatomic creation from quarks"""
        from periodica_app.ui.creation_dialog import SubatomicCreationDialog
        dialog = SubatomicCreationDialog(self)
        dialog.particle_created.connect(lambda: self._on_subatomic_data_saved(None))
        dialog.exec()

    def _on_subatomic_data_saved(self, data):
        """Called when subatomic data is saved"""
        self.subatomic_table.reload_data()
        self.subatomic_info.show_default()
        self.subatomic_control.update_item_count(len(self.subatomic_table.particles))

    def _on_subatomic_export(self):
        """Handle subatomic export request"""
        if hasattr(self.subatomic_table, 'selected_particle') and self.subatomic_table.selected_particle:
            from periodica_app.ui.action_handler import ExportHandler

            particle = self.subatomic_table.selected_particle
            name = particle.get('Name', 'particle')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(particle, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_subatomic_import(self):
        """Handle subatomic import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Particle", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                manager = get_data_manager()
                name = data.get('Name', 'Imported')
                if manager.add_item(DataCategory.SUBATOMIC, name.replace(' ', '_'), data):
                    self.subatomic_table.reload_data()
                    self.subatomic_control.update_item_count(len(self.subatomic_table.particles))
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported particle")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_subatomic_duplicate(self):
        """Handle subatomic duplicate request"""
        if hasattr(self.subatomic_table, 'selected_particle') and self.subatomic_table.selected_particle:
            from periodica_app.ui.action_handler import DuplicateHandler

            particle = self.subatomic_table.selected_particle
            duplicated = DuplicateHandler.duplicate_item(particle, name_key='Name')
            manager = get_data_manager()
            name = duplicated.get('Name', 'Unknown')
            if manager.add_item(DataCategory.SUBATOMIC, name.replace(' ', '_'), duplicated):
                self.subatomic_table.reload_data()
                self.subatomic_control.update_item_count(len(self.subatomic_table.particles))
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    # ==================== MOLECULES TAB HANDLERS ====================

    def _on_molecule_selected(self, molecule):
        """Handle molecule selection"""
        self.molecule_info.update_molecule(molecule)
        self.molecule_control.set_item_selected(molecule is not None)

    def _on_molecule_add(self):
        """Handle molecule add request - show inline editor"""
        template = None
        if hasattr(self.molecule_table, 'selected_molecule'):
            template = self.molecule_table.selected_molecule
        self.molecule_info.start_add(template)

    def _on_molecule_edit(self):
        """Handle molecule edit request - show inline editor"""
        if hasattr(self.molecule_table, 'selected_molecule') and self.molecule_table.selected_molecule:
            self.molecule_info.start_edit(self.molecule_table.selected_molecule)

    def _on_molecule_remove(self):
        """Handle molecule remove request"""
        if hasattr(self.molecule_table, 'selected_molecule') and self.molecule_table.selected_molecule:
            mol = self.molecule_table.selected_molecule
            name = mol.get('Name', 'Unknown')
            reply = QMessageBox.question(
                self, "Remove Molecule",
                f"Are you sure you want to remove '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                manager = get_data_manager()
                filename = name.replace(' ', '_')
                if manager.remove_item(DataCategory.MOLECULES, filename):
                    self.molecule_table.reload_data()
                    self.molecule_info.show_default()
                    self.molecule_control.set_item_selected(False)

    def _on_molecule_reset(self):
        """Handle molecule reset request"""
        reply = QMessageBox.question(
            self, "Reset Molecules",
            "Are you sure you want to reset all molecules to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            manager = get_data_manager()
            if manager.reset_category(DataCategory.MOLECULES):
                self.molecule_table.reload_data()
                self.molecule_info.show_default()
                QMessageBox.information(self, "Success", "Molecules reset to defaults.")

    def _on_molecule_create(self):
        """Handle molecule creation from atoms"""
        from periodica_app.ui.creation_dialog import MoleculeCreationDialog
        dialog = MoleculeCreationDialog(self)
        dialog.molecule_created.connect(lambda: self._on_molecule_data_saved(None))
        dialog.exec()

    def _on_molecule_data_saved(self, data):
        """Called when molecule data is saved"""
        self.molecule_table.reload_data()
        self.molecule_info.show_default()
        self.molecule_control.update_item_count(len(self.molecule_table.base_molecules))

    def _on_molecule_export(self):
        """Handle molecule export request"""
        if hasattr(self.molecule_table, 'selected_molecule') and self.molecule_table.selected_molecule:
            from periodica_app.ui.action_handler import ExportHandler

            mol = self.molecule_table.selected_molecule
            name = mol.get('Name', 'molecule')
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {name}", f"{name}.json", "JSON Files (*.json)"
            )
            if filepath:
                if ExportHandler.export_json(mol, Path(filepath)):
                    QMessageBox.information(self, "Success", f"Exported '{name}' to {filepath}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to export '{name}'")

    def _on_molecule_import(self):
        """Handle molecule import request"""
        from periodica_app.ui.action_handler import ExportHandler

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Molecule", "", "JSON Files (*.json)"
        )
        if filepath:
            data = ExportHandler.import_json(Path(filepath))
            if data:
                manager = get_data_manager()
                name = data.get('Name', 'Imported')
                if manager.add_item(DataCategory.MOLECULES, name.replace(' ', '_'), data):
                    self.molecule_table.reload_data()
                    self.molecule_control.update_item_count(len(self.molecule_table.base_molecules))
                    QMessageBox.information(self, "Success", f"Imported '{name}'")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to save imported molecule")
            else:
                QMessageBox.warning(self, "Error", "Failed to import file")

    def _on_molecule_duplicate(self):
        """Handle molecule duplicate request"""
        if hasattr(self.molecule_table, 'selected_molecule') and self.molecule_table.selected_molecule:
            from periodica_app.ui.action_handler import DuplicateHandler

            mol = self.molecule_table.selected_molecule
            duplicated = DuplicateHandler.duplicate_item(mol, name_key='Name')
            manager = get_data_manager()
            name = duplicated.get('Name', 'Unknown')
            if manager.add_item(DataCategory.MOLECULES, name.replace(' ', '_'), duplicated):
                self.molecule_table.reload_data()
                self.molecule_control.update_item_count(len(self.molecule_table.base_molecules))
                QMessageBox.information(self, "Success", f"Created duplicate: '{name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to create duplicate")

    # ==================== AUTO-GENERATION HANDLERS ====================

    def _on_alloy_auto_generate(self):
        """Handle auto-generation of alloys"""
        from periodica_app.ui.auto_generation_dialog import AutoGenerationDialog
        from periodica.utils.alloy_generator import AlloyGenerator

        gen = AlloyGenerator()
        dialog = AutoGenerationDialog("alloys", gen.generate_all, self)
        dialog.items_generated.connect(self._on_alloy_auto_generated)
        dialog.exec()

    def _on_alloy_auto_generated(self, items):
        """Save auto-generated alloys and refresh table"""
        from periodica.utils.alloy_generator import AlloyGenerator
        gen = AlloyGenerator()
        saved = gen.save_alloys(items)
        self.alloy_table.reload_data()
        self.alloy_control.update_item_count(len(self.alloy_table.base_alloys))
        self.statusBar().showMessage(f"Auto-generated {saved} alloys", 5000)

    def _on_material_auto_generate(self):
        """Handle auto-generation of materials"""
        from periodica_app.ui.auto_generation_dialog import AutoGenerationDialog
        from periodica.utils.material_generator import MaterialGenerator

        gen = MaterialGenerator()
        # Material generator needs alloy data; wrap to match expected signature
        def generate_func(count_limit=50, progress_callback=None):
            from periodica.data.material_loader import MaterialLoader
            loader = MaterialLoader()
            alloys_path = Path(__file__).parent / "data" / "active" / "alloys"
            import json
            alloys = []
            if alloys_path.exists():
                for f in alloys_path.glob("*.json"):
                    try:
                        with open(f, 'r', encoding='utf-8') as fh:
                            alloys.append(json.load(fh))
                    except Exception:
                        pass
            if not alloys:
                raise ValueError("No alloy data found. Generate alloys first.")
            return gen.generate_all(alloys, count_limit=count_limit, progress_callback=progress_callback)

        dialog = AutoGenerationDialog("materials", generate_func, self)
        dialog.items_generated.connect(self._on_material_auto_generated)
        dialog.exec()

    def _on_material_auto_generated(self, items):
        """Save auto-generated materials and refresh table"""
        import json
        dest_dir = Path(__file__).parent / "data" / "active" / "materials"
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved = 0
        for item in items:
            name = item.get('Name', f'material_{saved}')
            safe_name = name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
            filepath = dest_dir / f"{safe_name}.json"
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(item, f, indent=2, ensure_ascii=False)
                saved += 1
            except Exception:
                pass
        self.material_table.loader.reload()
        self.material_table.base_materials = list(
            self.material_table.loader.get_all_materials().values())
        self.material_table._update_layout()
        self.material_table.update()
        self.statusBar().showMessage(f"Auto-generated {saved} materials", 5000)

    def _on_amino_acid_auto_generate(self):
        """Handle auto-generation of amino acids"""
        from periodica_app.ui.auto_generation_dialog import AutoGenerationDialog
        from periodica.utils.biological_generator import BiologicalGenerator

        gen = BiologicalGenerator()
        def generate_func(count_limit=50, progress_callback=None):
            return gen.generate_category('amino_acids', count_limit=count_limit, progress_callback=progress_callback)

        dialog = AutoGenerationDialog("amino_acids", generate_func, self)
        dialog.items_generated.connect(lambda items: self._on_bio_auto_generated(items, 'amino_acids'))
        dialog.exec()

    def _on_protein_auto_generate(self):
        """Handle auto-generation of proteins"""
        from periodica_app.ui.auto_generation_dialog import AutoGenerationDialog
        from periodica.utils.biological_generator import BiologicalGenerator

        gen = BiologicalGenerator()
        def generate_func(count_limit=50, progress_callback=None):
            return gen.generate_category('proteins', count_limit=count_limit, progress_callback=progress_callback)

        dialog = AutoGenerationDialog("proteins", generate_func, self)
        dialog.items_generated.connect(lambda items: self._on_bio_auto_generated(items, 'proteins'))
        dialog.exec()

    def _on_nucleic_acid_auto_generate(self):
        """Handle auto-generation of nucleic acids"""
        from periodica_app.ui.auto_generation_dialog import AutoGenerationDialog
        from periodica.utils.biological_generator import BiologicalGenerator

        gen = BiologicalGenerator()
        def generate_func(count_limit=50, progress_callback=None):
            return gen.generate_category('nucleic_acids', count_limit=count_limit, progress_callback=progress_callback)

        dialog = AutoGenerationDialog("nucleic_acids", generate_func, self)
        dialog.items_generated.connect(lambda items: self._on_bio_auto_generated(items, 'nucleic_acids'))
        dialog.exec()

    def _on_cell_component_auto_generate(self):
        """Handle auto-generation of cell components"""
        from periodica_app.ui.auto_generation_dialog import AutoGenerationDialog
        from periodica.utils.biological_generator import BiologicalGenerator

        gen = BiologicalGenerator()
        def generate_func(count_limit=50, progress_callback=None):
            return gen.generate_category('cell_components', count_limit=count_limit, progress_callback=progress_callback)

        dialog = AutoGenerationDialog("cell_components", generate_func, self)
        dialog.items_generated.connect(lambda items: self._on_bio_auto_generated(items, 'cell_components'))
        dialog.exec()

    def _on_cell_auto_generate(self):
        """Handle auto-generation of cells"""
        from periodica_app.ui.auto_generation_dialog import AutoGenerationDialog
        from periodica.utils.biological_generator import BiologicalGenerator

        gen = BiologicalGenerator()
        def generate_func(count_limit=50, progress_callback=None):
            return gen.generate_category('cells', count_limit=count_limit, progress_callback=progress_callback)

        dialog = AutoGenerationDialog("cells", generate_func, self)
        dialog.items_generated.connect(lambda items: self._on_bio_auto_generated(items, 'cells'))
        dialog.exec()

    def _on_biomaterial_auto_generate(self):
        """Handle auto-generation of biomaterials"""
        from periodica_app.ui.auto_generation_dialog import AutoGenerationDialog
        from periodica.utils.biological_generator import BiologicalGenerator

        gen = BiologicalGenerator()
        def generate_func(count_limit=50, progress_callback=None):
            return gen.generate_category('biomaterials', count_limit=count_limit, progress_callback=progress_callback)

        dialog = AutoGenerationDialog("biomaterials", generate_func, self)
        dialog.items_generated.connect(lambda items: self._on_bio_auto_generated(items, 'biomaterials'))
        dialog.exec()

    def _on_bio_auto_generated(self, items, category):
        """Save auto-generated biological items and refresh the corresponding table"""
        from periodica.utils.biological_generator import BiologicalGenerator
        gen = BiologicalGenerator()
        saved = gen.save_items(items, category)

        # Refresh the appropriate table
        table_map = {
            'amino_acids': 'amino_acid_table',
            'proteins': 'protein_table',
            'nucleic_acids': 'nucleic_acid_table',
            'cell_components': 'cell_component_table',
            'cells': 'cell_table',
            'biomaterials': 'biomaterial_table',
        }
        table_name = table_map.get(category)
        if table_name and hasattr(self, table_name):
            table = getattr(self, table_name)
            if hasattr(table, 'refresh'):
                table.refresh()
            elif hasattr(table, 'reload_data'):
                table.reload_data()

        self.statusBar().showMessage(f"Auto-generated {saved} {category.replace('_', ' ')}", 5000)

    # ==================== CASCADE REGENERATION HANDLER ====================

    def _on_cascade_regenerate(self):
        """Handle cascade regeneration from quarks"""
        from periodica_app.ui.cascade_regeneration_dialog import CascadeRegenerationDialog

        dialog = CascadeRegenerationDialog(self)
        dialog.regeneration_complete.connect(self._on_cascade_complete)
        dialog.exec()

    def _on_cascade_complete(self, results):
        """Handle cascade regeneration completion — refresh all affected tables"""
        refreshed = []
        table_map = {
            'elements': ('atom_table', 'reload_data'),
            'molecules': ('molecule_table', 'reload_data'),
            'alloys': ('alloy_table', 'reload_data'),
            'amino_acids': ('amino_acid_table', 'refresh'),
            'proteins': ('protein_table', 'refresh'),
            'nucleic_acids': ('nucleic_acid_table', 'refresh'),
            'cell_components': ('cell_component_table', 'refresh'),
            'cells': ('cell_table', 'refresh'),
            'biomaterials': ('biomaterial_table', 'refresh'),
        }

        for category, count in results.items():
            if count > 0 and category in table_map:
                table_name, method_name = table_map[category]
                if hasattr(self, table_name):
                    table = getattr(self, table_name)
                    if hasattr(table, method_name):
                        getattr(table, method_name)()
                        refreshed.append(category)

        # Material table has a special reload pattern
        if 'materials' in results and results['materials'] > 0:
            if hasattr(self, 'material_table'):
                self.material_table.loader.reload()
                self.material_table.base_materials = list(
                    self.material_table.loader.get_all_materials().values())
                self.material_table._update_layout()
                self.material_table.update()
                refreshed.append('materials')

        total = sum(results.values())
        self.statusBar().showMessage(
            f"Cascade regeneration complete: {total} items across {len(refreshed)} categories", 8000)

    def setup_statusbar(self):
        """Setup the status bar"""
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background: rgb(30, 30, 45);
                color: white;
                padding: 5px;
            }
        """)
        self.statusBar().showMessage("Ready")

    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(20, 20, 35))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(30, 30, 50))
        palette.setColor(QPalette.AlternateBase, QColor(40, 40, 60))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(50, 50, 70))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(100, 150, 255))
        palette.setColor(QPalette.Highlight, QColor(100, 100, 150))
        palette.setColor(QPalette.HighlightedText, Qt.white)

        self.setPalette(palette)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = PeriodicsMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
