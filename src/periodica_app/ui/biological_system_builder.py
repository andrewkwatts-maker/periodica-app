"""
Biological System Builder Dialog
Unified dialog for creating biological structures at any level of the hierarchy.
Supports atoms → molecules → proteins → cells → tissues → biomaterials.

All formulas are generic and configurable, not hardcoded for specific proteins.
Includes Voronoi spatial sampling for biological materials (like alloys have for grains).
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QComboBox, QTextEdit, QWidget, QTabWidget,
    QMessageBox, QDoubleSpinBox, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QSlider, QListWidget,
    QListWidgetItem, QFrame, QCheckBox, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QRadialGradient

import json
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

from periodica.utils.biological_derivation_chain import (
    BiologicalDerivationChain, BiologicalMixingSystem,
    BiologicalComponent, BiologicalLevel, AtomicComposition
)
from periodica.utils.biological_component_factory import BiologicalComponentFactory
from periodica_app.ui.predictor_settings_dialog import PredictorSettingsDialog
from periodica.utils.predictors.biological.protein_predictor import ProteinPredictor
from periodica.utils.predictors.biological.nucleic_acid_predictor import NucleicAcidPredictor


# Amino acid single-letter codes with full names
AMINO_ACIDS = {
    'A': 'Alanine', 'R': 'Arginine', 'N': 'Asparagine', 'D': 'Aspartic acid',
    'C': 'Cysteine', 'E': 'Glutamic acid', 'Q': 'Glutamine', 'G': 'Glycine',
    'H': 'Histidine', 'I': 'Isoleucine', 'L': 'Leucine', 'K': 'Lysine',
    'M': 'Methionine', 'F': 'Phenylalanine', 'P': 'Proline', 'S': 'Serine',
    'T': 'Threonine', 'W': 'Tryptophan', 'Y': 'Tyrosine', 'V': 'Valine'
}

# Nucleotide codes
DNA_BASES = {'A': 'Adenine', 'T': 'Thymine', 'G': 'Guanine', 'C': 'Cytosine'}
RNA_BASES = {'A': 'Adenine', 'U': 'Uracil', 'G': 'Guanine', 'C': 'Cytosine'}

# ECM component types
ECM_COMPONENTS = [
    'collagen_i', 'collagen_ii', 'collagen_iii', 'collagen_iv',
    'elastin', 'fibronectin', 'laminin', 'proteoglycans',
    'hyaluronan', 'water'
]

# Quick presets for common biological structures
BIOLOGICAL_PRESETS = {
    'protein': [
        ('Hemoglobin α', 'MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH'),
        ('Insulin B', 'FVNQHLCGSHLVEALYLVCGERGFFYTPKT'),
        ('Ubiquitin', 'MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG'),
        ('GFP (partial)', 'MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTLTYGVQCFSRYPDHMKQ'),
    ],
    'nucleic_acid': [
        ('Start Codon', 'ATG'),
        ('Kozak Sequence', 'GCCGCCACCATGG'),
        ('TATA Box', 'TATAAA'),
        ('Shine-Dalgarno', 'AGGAGGU'),
        ('Poly-A Signal', 'AATAAA'),
        ('CpG Island', 'CGCGCGCGCGCGCGCG'),
    ],
    'cell': [
        ('Red Blood Cell', {'type': 'erythrocyte', 'diameter_um': 7.5}),
        ('Neuron', {'type': 'neuron', 'diameter_um': 20.0}),
        ('Hepatocyte', {'type': 'hepatocyte', 'diameter_um': 25.0}),
        ('Fibroblast', {'type': 'fibroblast', 'diameter_um': 15.0}),
        ('Cardiomyocyte', {'type': 'cardiomyocyte', 'diameter_um': 100.0}),
    ],
    'biomaterial': [
        ('Cartilage', {'collagen_ii': 0.15, 'proteoglycans': 0.10, 'water': 0.75}),
        ('Bone Matrix', {'collagen_i': 0.30, 'water': 0.10}),
        ('Tendon', {'collagen_i': 0.70, 'elastin': 0.02, 'water': 0.28}),
        ('Skin Dermis', {'collagen_i': 0.25, 'elastin': 0.05, 'water': 0.70}),
        ('Hydrogel', {'water': 0.95, 'hyaluronan': 0.05}),
    ],
}

# ECM component properties (like alloy LatticeProperties)
ECM_MATERIAL_PROPERTIES = {
    'collagen_i': {
        'youngs_modulus_MPa': 1000.0,
        'density_g_cm3': 1.34,
        'poissons_ratio': 0.35,
        'thermal_conductivity_W_mK': 0.56,
        'structure': 'fibrillar',
        'fiber_diameter_nm': 100,
    },
    'collagen_ii': {
        'youngs_modulus_MPa': 500.0,
        'density_g_cm3': 1.30,
        'poissons_ratio': 0.40,
        'thermal_conductivity_W_mK': 0.54,
        'structure': 'fibrillar',
        'fiber_diameter_nm': 50,
    },
    'collagen_iii': {
        'youngs_modulus_MPa': 300.0,
        'density_g_cm3': 1.28,
        'poissons_ratio': 0.42,
        'thermal_conductivity_W_mK': 0.52,
        'structure': 'reticular',
        'fiber_diameter_nm': 40,
    },
    'collagen_iv': {
        'youngs_modulus_MPa': 100.0,
        'density_g_cm3': 1.25,
        'poissons_ratio': 0.45,
        'thermal_conductivity_W_mK': 0.50,
        'structure': 'network',
        'fiber_diameter_nm': 30,
    },
    'elastin': {
        'youngs_modulus_MPa': 0.6,
        'density_g_cm3': 1.30,
        'poissons_ratio': 0.49,
        'thermal_conductivity_W_mK': 0.45,
        'structure': 'amorphous',
        'fiber_diameter_nm': 200,
    },
    'fibronectin': {
        'youngs_modulus_MPa': 0.1,
        'density_g_cm3': 1.35,
        'poissons_ratio': 0.48,
        'thermal_conductivity_W_mK': 0.50,
        'structure': 'glycoprotein',
    },
    'laminin': {
        'youngs_modulus_MPa': 0.05,
        'density_g_cm3': 1.32,
        'poissons_ratio': 0.48,
        'thermal_conductivity_W_mK': 0.50,
        'structure': 'glycoprotein',
    },
    'proteoglycans': {
        'youngs_modulus_MPa': 0.001,
        'density_g_cm3': 1.10,
        'poissons_ratio': 0.495,
        'thermal_conductivity_W_mK': 0.60,
        'structure': 'gel',
        'water_content': 0.80,
    },
    'hyaluronan': {
        'youngs_modulus_MPa': 0.0001,
        'density_g_cm3': 1.05,
        'poissons_ratio': 0.499,
        'thermal_conductivity_W_mK': 0.62,
        'structure': 'gel',
        'water_content': 0.95,
    },
    'water': {
        'youngs_modulus_MPa': 0.0,
        'density_g_cm3': 1.00,
        'poissons_ratio': 0.50,
        'thermal_conductivity_W_mK': 0.60,
        'structure': 'fluid',
        'viscosity_Pa_s': 0.001,
    },
}


def _calculate_protein_composition(sequence: str) -> Dict[str, int]:
    """Calculate atomic composition (C, H, N, O, S) from amino acid sequence."""
    # Atomic composition for each amino acid (from peptide form, after water loss)
    AA_ATOMS = {
        'A': {'C': 3, 'H': 5, 'N': 1, 'O': 1, 'S': 0},   # Alanine
        'R': {'C': 6, 'H': 12, 'N': 4, 'O': 1, 'S': 0},  # Arginine
        'N': {'C': 4, 'H': 6, 'N': 2, 'O': 2, 'S': 0},   # Asparagine
        'D': {'C': 4, 'H': 5, 'N': 1, 'O': 3, 'S': 0},   # Aspartic acid
        'C': {'C': 3, 'H': 5, 'N': 1, 'O': 1, 'S': 1},   # Cysteine
        'E': {'C': 5, 'H': 7, 'N': 1, 'O': 3, 'S': 0},   # Glutamic acid
        'Q': {'C': 5, 'H': 8, 'N': 2, 'O': 2, 'S': 0},   # Glutamine
        'G': {'C': 2, 'H': 3, 'N': 1, 'O': 1, 'S': 0},   # Glycine
        'H': {'C': 6, 'H': 7, 'N': 3, 'O': 1, 'S': 0},   # Histidine
        'I': {'C': 6, 'H': 11, 'N': 1, 'O': 1, 'S': 0},  # Isoleucine
        'L': {'C': 6, 'H': 11, 'N': 1, 'O': 1, 'S': 0},  # Leucine
        'K': {'C': 6, 'H': 12, 'N': 2, 'O': 1, 'S': 0},  # Lysine
        'M': {'C': 5, 'H': 9, 'N': 1, 'O': 1, 'S': 1},   # Methionine
        'F': {'C': 9, 'H': 9, 'N': 1, 'O': 1, 'S': 0},   # Phenylalanine
        'P': {'C': 5, 'H': 7, 'N': 1, 'O': 1, 'S': 0},   # Proline
        'S': {'C': 3, 'H': 5, 'N': 1, 'O': 2, 'S': 0},   # Serine
        'T': {'C': 4, 'H': 7, 'N': 1, 'O': 2, 'S': 0},   # Threonine
        'W': {'C': 11, 'H': 10, 'N': 2, 'O': 1, 'S': 0}, # Tryptophan
        'Y': {'C': 9, 'H': 9, 'N': 1, 'O': 2, 'S': 0},   # Tyrosine
        'V': {'C': 5, 'H': 9, 'N': 1, 'O': 1, 'S': 0},   # Valine
    }

    composition = {'C': 0, 'H': 0, 'N': 0, 'O': 0, 'S': 0}

    for aa in sequence.upper():
        if aa in AA_ATOMS:
            for atom, count in AA_ATOMS[aa].items():
                composition[atom] += count

    # Add terminal groups: +H at N-terminus, +OH at C-terminus = +H2O
    if len(sequence) > 0:
        composition['H'] += 2
        composition['O'] += 1

    # Remove S if zero
    if composition['S'] == 0:
        del composition['S']

    return composition


def _calculate_na_composition(sequence: str, is_rna: bool = False) -> Dict[str, int]:
    """Calculate atomic composition for nucleic acid sequence."""
    # Nucleotide atoms (as nucleoside monophosphate in chain)
    DNA_ATOMS = {
        'A': {'C': 10, 'H': 12, 'N': 5, 'O': 6, 'P': 1},  # dAMP
        'T': {'C': 10, 'H': 13, 'N': 2, 'O': 8, 'P': 1},  # dTMP
        'G': {'C': 10, 'H': 12, 'N': 5, 'O': 7, 'P': 1},  # dGMP
        'C': {'C': 9, 'H': 12, 'N': 3, 'O': 7, 'P': 1},   # dCMP
    }
    RNA_ATOMS = {
        'A': {'C': 10, 'H': 12, 'N': 5, 'O': 7, 'P': 1},  # AMP
        'U': {'C': 9, 'H': 11, 'N': 2, 'O': 9, 'P': 1},   # UMP
        'G': {'C': 10, 'H': 12, 'N': 5, 'O': 8, 'P': 1},  # GMP
        'C': {'C': 9, 'H': 12, 'N': 3, 'O': 8, 'P': 1},   # CMP
    }

    atoms = RNA_ATOMS if is_rna else DNA_ATOMS
    composition = {'C': 0, 'H': 0, 'N': 0, 'O': 0, 'P': 0}

    for nt in sequence.upper():
        if nt in atoms:
            for atom, count in atoms[nt].items():
                composition[atom] += count

    return composition


def generate_comprehensive_json(component, level: str, microstructure_data: Dict = None,
                                 predictor_settings: Dict = None) -> Dict:
    """
    Generate publication-quality JSON for a biological component.

    Follows the standard format used in data/active/proteins/ with clean
    property names, atomic composition, cofactors, and metadata sections.
    Uses ProteinPredictor for accurate property calculations with minimal deviation.

    Args:
        component: BiologicalComponent instance
        level: Biological level (protein, nucleic_acid, cell, tissue, biomaterial)
        microstructure_data: Optional spatial distribution data for tissues/biomaterials
        predictor_settings: Optional predictor configuration parameters

    Returns:
        Dict with publication-ready JSON structure matching reference data format
    """
    props = component.properties if hasattr(component, 'properties') else {}
    name = component.name if hasattr(component, 'name') else "Unknown"

    if level == "protein":
        sequence = props.get('sequence', '')

        # Use ProteinPredictor for accurate calculations
        predictor = ProteinPredictor()

        # Full protein analysis using calibrated predictor
        analysis = predictor.analyze_protein(sequence, name)

        # Calculate atomic composition from sequence
        composition = _calculate_protein_composition(sequence)

        # Get function and localization from props or defaults
        function = props.get('function', 'unknown')
        localization = props.get('localization', 'cytoplasm')
        organism = props.get('organism', 'Homo sapiens')

        # Generate 4-char symbol from name if not provided
        symbol = props.get('symbol')
        if not symbol:
            # Generate from name: take first letters of words, up to 4 chars
            words = name.replace('-', ' ').replace('_', ' ').split()
            if len(words) >= 4:
                symbol = ''.join(w[0].upper() for w in words[:4])
            elif len(words) >= 2:
                symbol = ''.join(w[:2].upper() for w in words[:2])
            else:
                symbol = name[:4].upper() if name else 'PROT'

        result = {
            "name": name,
            "organism": organism,
            "function": function,
            "localization": localization,
            "sequence": sequence,
            "length": len(sequence),
            "molecular_mass": analysis['molecular_mass'],
            "isoelectric_point": analysis['isoelectric_point'],
            "charge_pH7": analysis['charge_pH7'],
            "gravy": analysis['gravy'],
            "amino_acid_composition": analysis['amino_acid_composition'],
            "secondary_structure": {
                "helix_percent": analysis['secondary_structure']['helix_percent'],
                "sheet_percent": analysis['secondary_structure']['sheet_percent'],
                "turn_percent": analysis['secondary_structure']['turn_percent'],
                "coil_percent": analysis['secondary_structure']['coil_percent'],
            },
            "residues": analysis['residues'],  # Per-residue phi/psi data
            "disulfide_bonds": analysis['disulfide_bonds'],
            "extinction_coefficient": {
                "reduced": analysis['extinction_coefficient_reduced'],
                "oxidized": analysis['extinction_coefficient_oxidized'],
            },
        }

        # Add optional fields if present in props
        if props.get('uniprot_id'):
            result['uniprot_id'] = props['uniprot_id']
        if props.get('pdb_id'):
            result['pdb_id'] = props['pdb_id']
        if props.get('description'):
            result['description'] = props['description']

        return result

    elif level == "nucleic_acid":
        sequence = props.get('sequence', '')
        na_type = props.get('type', 'DNA')
        is_rna = na_type.upper() == 'RNA'

        # Use NucleicAcidPredictor for accurate calculations
        na_predictor = NucleicAcidPredictor()
        analysis = na_predictor.analyze_sequence(sequence, name, is_rna)

        # Calculate atomic composition
        composition = _calculate_na_composition(sequence, is_rna)

        result = {
            "name": name,
            "type": na_type.upper(),
            "organism": props.get('organism', 'Homo sapiens'),
            "function": props.get('function', 'unknown'),
            "sequence": analysis['sequence'],
            "length": analysis['length'],
            "molecular_mass": analysis['molecular_mass'],
            "molecular_mass_double_stranded": analysis['molecular_mass_ds'],
            "gc_content": analysis['gc_content'],
            "at_content": analysis['at_content'],
            "base_composition": analysis['base_composition'],
            "composition": composition,
            "melting_temperature": {
                "Tm_nearest_neighbor": analysis['melting_temperature']['nearest_neighbor'],
                "Tm_gc_method": analysis['melting_temperature']['gc_method'],
                "Tm_basic": analysis['melting_temperature']['basic'],
            },
            "complement": analysis['complement'],
            "reverse_complement": analysis['reverse_complement'],
            "secondary_structures": {
                "predicted_hairpins": len(analysis['predicted_hairpins']),
                "hairpin_details": analysis['predicted_hairpins'][:5],
            },
            "topology": props.get('topology', 'linear'),
            "strandedness": props.get('strandedness', 'single'),
        }

        # Add optional fields
        if props.get('description'):
            result['description'] = props['description']

        return result

    elif level == "cell":
        return {
            "name": name,
            "cell_type": props.get('cell_type', 'generic'),
            "organism": props.get('organism', 'Homo sapiens'),
            "tissue_origin": props.get('tissue_origin', 'unknown'),
            "morphology": {
                "diameter_um": round(props.get('diameter_um', 10.0), 2),
                "volume_fL": round(props.get('volume_fl', 0), 2),
                "surface_area_um2": round(props.get('surface_area_um2', 0), 2),
                "surface_volume_ratio": round(props.get('surface_volume_ratio', 0), 3),
            },
            "properties": {
                "mass_pg": round(props.get('mass_pg', 0), 2),
                "density_g_cm3": round(props.get('density', 1.05), 3),
                "metabolic_rate_fW": round(props.get('metabolic_rate_fW', 0), 3),
                "doubling_time_hours": props.get('doubling_time_hours', 24),
            },
            "metabolic_model": {
                "scaling_law": "Kleiber",
                "exponent": 0.75,
                "B0_coefficient": 3.5e-12,
                "temperature_K": 310
            },
            "metadata": {
                "source": "BiologicalSystemBuilder",
                "created_by": "Periodics",
                "predictor_method": "Kleiber_Scaling"
            }
        }

    elif level == "tissue":
        ecm_comp = props.get('ecm_composition', {})

        return {
            "name": name,
            "tissue_type": props.get('tissue_type', 'connective'),
            "organism": props.get('organism', 'Homo sapiens'),
            "organ_system": props.get('organ_system', 'unknown'),
            "composition": {
                "cell_fraction": round(1.0 - sum(ecm_comp.values()), 3) if ecm_comp else 0.3,
                "ecm_fraction": round(sum(ecm_comp.values()), 3) if ecm_comp else 0.7,
                "vascularization": round(props.get('vascularization', 0.05), 3),
                "water_content": round(props.get('water_content', 0.7), 2),
            },
            "ecm_components": ecm_comp,
            "properties": {
                "density_g_cm3": round(props.get('density', 1.05), 3),
                "youngs_modulus_MPa": round(props.get('youngs_modulus_MPa', 0.01), 4),
                "poissons_ratio": round(props.get('poissons_ratio', 0.45), 2),
            },
            "microstructure": microstructure_data if microstructure_data else {
                "cell_density_per_mm3": props.get('cell_density', 1e6),
                "fiber_alignment": props.get('fiber_alignment', 'random'),
            },
            "metadata": {
                "source": "BiologicalSystemBuilder",
                "created_by": "Periodics",
                "predictor_method": "Voigt-Reuss"
            }
        }

    elif level == "biomaterial":
        ecm_comp = props.get('ecm_composition', {})
        porosity = props.get('porosity', 0)
        if porosity > 1:
            porosity = porosity / 100.0

        return {
            "name": name,
            "material_type": props.get('material_type', 'scaffold'),
            "category": props.get('stiffness_category', 'soft'),
            "composition": {
                "components": ecm_comp,
                "porosity": round(porosity, 3),
                "water_content": round(ecm_comp.get('water', 0), 3),
            },
            "properties": {
                "density_g_cm3": round(props.get('density_g_cm3', 1.0), 3),
                "youngs_modulus_MPa": round(props.get('youngs_modulus_MPa', 0.01), 4),
                "shear_modulus_MPa": round(props.get('shear_modulus_MPa', 0.003), 4),
                "poissons_ratio": round(props.get('poissons_ratio', 0.45), 2),
                "pore_size_um": props.get('pore_size_um', 100),
            },
            "mechanical_models": {
                "composite_model": props.get('composite_model', 'voigt_reuss_average'),
                "porosity_model": props.get('porosity_model', 'gibson_ashby'),
            },
            "component_properties": {
                comp: {k: round(v, 4) if isinstance(v, float) else v
                       for k, v in ECM_MATERIAL_PROPERTIES.get(comp, {}).items()}
                for comp in ecm_comp.keys()
            },
            "microstructure": microstructure_data if microstructure_data else {
                "fiber_diameter_nm": props.get('fiber_diameter_nm', 100),
                "fiber_alignment": props.get('fiber_alignment', 'random'),
                "crosslink_density": props.get('crosslink_density', 0.1),
                "spatial_distribution": "voronoi_sampled"
            },
            "biological": {
                "biocompatibility": props.get('biocompatibility', 'good'),
                "cell_adhesion": props.get('cell_adhesion', 'moderate'),
                "degradation_rate_per_day": props.get('degradation_rate', 0.01),
            },
            "metadata": {
                "source": "BiologicalSystemBuilder",
                "created_by": "Periodics",
                "predictor_method": "Gibson-Ashby/Voigt-Reuss"
            }
        }

    # Fallback for unknown levels
    return {
        "name": name,
        "level": level,
        "properties": props,
        "metadata": {
            "source": "BiologicalSystemBuilder",
            "created_by": "Periodics"
        }
    }


class SequenceEditorWidget(QWidget):
    """Widget for editing biological sequences with validation and palette."""

    sequence_changed = Signal(str)

    def __init__(self, sequence_type: str = "protein", parent=None):
        super().__init__(parent)
        self.sequence_type = sequence_type
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sequence input
        input_layout = QHBoxLayout()

        seq_label = QLabel(f"{self.sequence_type.title()} Sequence:")
        input_layout.addWidget(seq_label)

        self.sequence_edit = QTextEdit()
        self.sequence_edit.setPlaceholderText(
            "Enter amino acid sequence (e.g., MVLSPADKTNVK)"
            if self.sequence_type == "protein"
            else "Enter nucleotide sequence (e.g., ATGCGATCGA)"
        )
        self.sequence_edit.setMaximumHeight(100)
        self.sequence_edit.textChanged.connect(self._on_sequence_changed)
        self.sequence_edit.setStyleSheet("""
            QTextEdit {
                background: rgba(40, 40, 60, 200);
                color: #0f0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        input_layout.addWidget(self.sequence_edit)

        layout.addLayout(input_layout)

        # Sequence palette
        palette_label = QLabel("Quick Insert:")
        layout.addWidget(palette_label)

        palette_layout = QGridLayout()

        if self.sequence_type == "protein":
            codes = AMINO_ACIDS
        elif self.sequence_type == "dna":
            codes = DNA_BASES
        else:
            codes = RNA_BASES

        row, col = 0, 0
        max_cols = 10 if self.sequence_type == "protein" else 4

        for code, name in codes.items():
            btn = QPushButton(code)
            btn.setToolTip(name)
            btn.setFixedSize(32, 28)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(102, 126, 234, 150);
                    color: white;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: rgba(139, 92, 246, 200);
                }
            """)
            btn.clicked.connect(lambda checked, c=code: self._insert_code(c))
            palette_layout.addWidget(btn, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        layout.addLayout(palette_layout)

        # Validation status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

    def _insert_code(self, code: str):
        """Insert a code at cursor position."""
        cursor = self.sequence_edit.textCursor()
        cursor.insertText(code)

    def _on_sequence_changed(self):
        """Handle sequence changes with validation."""
        sequence = self.get_sequence()

        if not sequence:
            self.status_label.setText("")
            self.sequence_changed.emit("")
            return

        # Validate
        if self.sequence_type == "protein":
            valid_chars = set(AMINO_ACIDS.keys())
        elif self.sequence_type == "dna":
            valid_chars = set(DNA_BASES.keys())
        else:
            valid_chars = set(RNA_BASES.keys())

        invalid = set(sequence.upper()) - valid_chars

        if invalid:
            self.status_label.setText(f"Invalid characters: {invalid}")
            self.status_label.setStyleSheet("color: #f44336;")
        else:
            self.status_label.setText(f"Length: {len(sequence)} residues")
            self.status_label.setStyleSheet("color: #4CAF50;")

        self.sequence_changed.emit(sequence)

    def get_sequence(self) -> str:
        """Get the current sequence (cleaned)."""
        text = self.sequence_edit.toPlainText()
        # Remove whitespace and convert to uppercase
        return ''.join(text.split()).upper()

    def set_sequence(self, sequence: str):
        """Set the sequence."""
        self.sequence_edit.setPlainText(sequence.upper())


class ComponentMixerWidget(QWidget):
    """Widget for mixing components with fraction sliders."""

    composition_changed = Signal(dict)

    def __init__(self, component_type: str = "ecm", parent=None):
        super().__init__(parent)
        self.component_type = component_type
        self.sliders = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for many components
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(250)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        if self.component_type == "ecm":
            components = ECM_COMPONENTS
        else:
            components = []

        for comp in components:
            self._add_component_slider(scroll_layout, comp)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Total display
        total_layout = QHBoxLayout()
        total_layout.addWidget(QLabel("Total:"))
        self.total_label = QLabel("0.0%")
        self.total_label.setStyleSheet("font-weight: bold;")
        total_layout.addWidget(self.total_label)
        total_layout.addStretch()

        # Normalize button
        normalize_btn = QPushButton("Normalize to 100%")
        normalize_btn.clicked.connect(self._normalize)
        total_layout.addWidget(normalize_btn)

        layout.addLayout(total_layout)

    def _add_component_slider(self, layout: QVBoxLayout, name: str):
        """Add a slider for a component."""
        row = QHBoxLayout()

        label = QLabel(name.replace('_', ' ').title() + ":")
        label.setFixedWidth(120)
        row.addWidget(label)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 1000)  # 0-100% with 0.1% precision
        slider.setValue(0)
        slider.valueChanged.connect(self._on_slider_changed)
        row.addWidget(slider)

        value_label = QLabel("0.0%")
        value_label.setFixedWidth(50)
        row.addWidget(value_label)

        self.sliders[name] = (slider, value_label)
        layout.addLayout(row)

    def _on_slider_changed(self):
        """Handle slider changes."""
        total = 0
        for name, (slider, label) in self.sliders.items():
            value = slider.value() / 10.0
            label.setText(f"{value:.1f}%")
            total += value

        # Update total
        color = "#4CAF50" if abs(total - 100) < 1 else "#FF9800"
        self.total_label.setText(f"{total:.1f}%")
        self.total_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        self.composition_changed.emit(self.get_composition())

    def _normalize(self):
        """Normalize fractions to 100%."""
        total = sum(s.value() for s, _ in self.sliders.values())
        if total == 0:
            return

        for slider, _ in self.sliders.values():
            slider.setValue(int(slider.value() * 1000 / total))

    def get_composition(self) -> Dict[str, float]:
        """Get current composition as fractions."""
        result = {}
        for name, (slider, _) in self.sliders.items():
            value = slider.value() / 1000.0  # Convert to fraction
            if value > 0:
                result[name] = round(value, 4)
        return result

    def set_composition(self, composition: Dict[str, float]):
        """Set composition from fractions."""
        for name, (slider, _) in self.sliders.items():
            value = composition.get(name, 0.0)
            slider.setValue(int(value * 1000))


class HierarchyBrowserWidget(QWidget):
    """Visual browser for component hierarchy."""

    component_selected = Signal(object)  # BiologicalComponent

    def __init__(self, factory: BiologicalComponentFactory, parent=None):
        super().__init__(parent)
        self.factory = factory
        self.setup_ui()
        self.refresh_tree()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("Component Hierarchy"))

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.clicked.connect(self.refresh_tree)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Properties"])
        self.tree.setColumnWidth(0, 150)
        self.tree.setColumnWidth(1, 100)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background: rgba(102, 126, 234, 150);
            }
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

    def refresh_tree(self):
        """Refresh the hierarchy tree."""
        self.tree.clear()

        levels = [
            (BiologicalLevel.PROTEIN, "Proteins"),
            (BiologicalLevel.NUCLEIC_ACID, "Nucleic Acids"),
            (BiologicalLevel.CELL_COMPONENT, "Cell Components"),
            (BiologicalLevel.CELL, "Cells"),
            (BiologicalLevel.TISSUE, "Tissues"),
            (BiologicalLevel.BIOMATERIAL, "Biomaterials"),
        ]

        for level, name in levels:
            parent = QTreeWidgetItem(self.tree, [name, level.name, ""])
            parent.setExpanded(True)

            # Load available components
            try:
                components = self.factory.list_available_components(level)
                for comp_name in components:
                    child = QTreeWidgetItem(parent, [comp_name, "Saved", ""])
                    child.setData(0, Qt.UserRole, (level, comp_name))
            except Exception:
                pass

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item clicks."""
        data = item.data(0, Qt.UserRole)
        if data:
            level, name = data
            component = self.factory.load_component(level, name)
            if component:
                self.component_selected.emit(component)


class JsonEditorWidget(QWidget):
    """Editable JSON viewer with syntax highlighting and validation."""

    json_changed = Signal(dict)
    json_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_updating = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with edit toggle
        header = QHBoxLayout()
        header.addWidget(QLabel("Component JSON"))

        self.edit_toggle = QCheckBox("Edit Mode")
        self.edit_toggle.setToolTip("Enable to directly edit JSON properties")
        self.edit_toggle.toggled.connect(self._on_edit_toggle)
        header.addWidget(self.edit_toggle)

        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover { background: #45a049; }
            QPushButton:disabled { background: #555; color: #888; }
        """)
        self.apply_btn.clicked.connect(self._apply_changes)
        self.apply_btn.setEnabled(False)
        self.apply_btn.hide()
        header.addWidget(self.apply_btn)

        layout.addLayout(header)

        # JSON editor
        self.json_edit = QTextEdit()
        self.json_edit.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                border: 1px solid #444;
                border-radius: 4px;
                selection-background-color: #264f78;
            }
        """)
        self.json_edit.setReadOnly(True)
        self.json_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.json_edit)

        # Validation status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.status_label)

    def _on_edit_toggle(self, checked: bool):
        """Toggle edit mode."""
        self.json_edit.setReadOnly(not checked)
        self.apply_btn.setVisible(checked)
        if checked:
            self.json_edit.setStyleSheet("""
                QTextEdit {
                    background: #2d2d2d;
                    color: #e0e0e0;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 11px;
                    border: 2px solid #667eea;
                    border-radius: 4px;
                }
            """)
            self.status_label.setText("Edit mode: Modify JSON and click Apply")
            self.status_label.setStyleSheet("color: #667eea; font-size: 10px;")
        else:
            self.json_edit.setStyleSheet("""
                QTextEdit {
                    background: #1e1e1e;
                    color: #d4d4d4;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 11px;
                    border: 1px solid #444;
                    border-radius: 4px;
                }
            """)
            self.status_label.setText("")

    def _on_text_changed(self):
        """Handle text changes - validate JSON."""
        if self._is_updating or self.json_edit.isReadOnly():
            return

        text = self.json_edit.toPlainText()
        try:
            json.loads(text)
            self.status_label.setText("Valid JSON")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
            self.apply_btn.setEnabled(True)
        except json.JSONDecodeError as e:
            self.status_label.setText(f"Invalid: {e.msg} at line {e.lineno}")
            self.status_label.setStyleSheet("color: #f44336; font-size: 10px;")
            self.apply_btn.setEnabled(False)

    def _apply_changes(self):
        """Apply JSON changes."""
        try:
            data = json.loads(self.json_edit.toPlainText())
            self.json_changed.emit(data)
            self.status_label.setText("Changes applied!")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
        except json.JSONDecodeError as e:
            self.json_error.emit(str(e))

    def set_json(self, data: Dict):
        """Set JSON content."""
        self._is_updating = True
        try:
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.json_edit.setPlainText(formatted)
        finally:
            self._is_updating = False

    def get_json(self) -> Optional[Dict]:
        """Get current JSON content."""
        try:
            return json.loads(self.json_edit.toPlainText())
        except json.JSONDecodeError:
            return None


class PresetSelectorWidget(QWidget):
    """Quick preset selector for biological structures."""

    preset_selected = Signal(str, object)  # (name, data)

    def __init__(self, preset_type: str = "protein", parent=None):
        super().__init__(parent)
        self.preset_type = preset_type
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Quick Presets:")
        label.setStyleSheet("color: #888;")
        layout.addWidget(label)

        presets = BIOLOGICAL_PRESETS.get(self.preset_type, [])

        for name, data in presets[:5]:  # Limit to 5 presets
            btn = QPushButton(name)
            btn.setToolTip(f"Load {name} preset")
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(102, 126, 234, 120);
                    color: white;
                    padding: 4px 10px;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background: rgba(139, 92, 246, 180);
                }
            """)
            btn.clicked.connect(lambda checked, n=name, d=data: self.preset_selected.emit(n, d))
            layout.addWidget(btn)

        layout.addStretch()


@dataclass
class CellSite:
    """Data structure for a single cell in the spatial distribution."""
    id: int
    x: float  # Normalized 0-1
    y: float
    z: float
    cell_type: str
    diameter_um: float = 10.0
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def get_color(self) -> QColor:
        """Get color based on cell type."""
        colors = {
            'epithelial': QColor(100, 200, 255, 200),
            'fibroblast': QColor(255, 180, 100, 200),
            'neuron': QColor(200, 100, 255, 200),
            'muscle': QColor(255, 100, 100, 200),
            'adipocyte': QColor(255, 255, 150, 200),
            'chondrocyte': QColor(100, 255, 180, 200),
            'osteocyte': QColor(200, 200, 200, 200),
            'ecm': QColor(80, 120, 80, 150),
        }
        return colors.get(self.cell_type.lower(), QColor(150, 150, 200, 200))


class BiologicalMicrostructureWidget(QFrame):
    """
    Visualization widget for biological microstructure.
    Shows Voronoi-like spatial distribution of cells and ECM.
    Similar to GrainVisualizationWidget but for biological tissues.
    """

    cells_changed = Signal()
    cell_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QFrame {
                background: rgba(20, 25, 35, 255);
                border: 2px solid #4a9eff;
                border-radius: 8px;
            }
        """)

        # Cell data
        self.cells: List[CellSite] = []

        # Domain size (in micrometers)
        self.domain_x = 500.0
        self.domain_y = 500.0
        self.domain_z = 100.0

        # View settings
        self.depth_slice = 0.5
        self.depth_tolerance = 0.3

        # Zoom and pan
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        # Interaction
        self.selected_cell: Optional[int] = None
        self.hovered_cell: Optional[int] = None

        # ECM composition (for background coloring)
        self.ecm_composition: Dict[str, float] = {}
        self.cell_density_per_mm3 = 1e6  # Default cell density

    def generate_cells(self, num_cells: int, cell_types: Dict[str, float] = None,
                       seed: int = 42, distribution: str = 'poisson'):
        """Generate random cell distribution with Voronoi-like spacing."""
        random.seed(seed)
        self.cells = []

        if cell_types is None:
            cell_types = {'fibroblast': 1.0}

        # Normalize fractions
        total = sum(cell_types.values())
        if total > 0:
            cell_types = {k: v/total for k, v in cell_types.items()}

        # Create cumulative distribution for cell type selection
        types_list = list(cell_types.keys())
        fractions = list(cell_types.values())
        cumulative = []
        total = 0
        for f in fractions:
            total += f
            cumulative.append(total)

        def select_type():
            r = random.random()
            for i, c in enumerate(cumulative):
                if r <= c:
                    return types_list[i]
            return types_list[-1]

        if distribution == 'poisson':
            # Poisson disk sampling approximation
            min_dist = 1.0 / math.sqrt(num_cells)
            attempts = 0
            while len(self.cells) < num_cells and attempts < num_cells * 30:
                x, y, z = random.random(), random.random(), random.random()
                # Check minimum distance
                too_close = False
                for cell in self.cells:
                    dist = math.sqrt((x-cell.x)**2 + (y-cell.y)**2 + (z-cell.z)**2)
                    if dist < min_dist * 0.5:
                        too_close = True
                        break
                if not too_close:
                    cell_type = select_type()
                    self.cells.append(CellSite(
                        id=len(self.cells),
                        x=x, y=y, z=z,
                        cell_type=cell_type,
                        diameter_um=8.0 + random.uniform(-2, 5),
                        orientation=(random.uniform(0, 360), random.uniform(0, 90), random.uniform(0, 90))
                    ))
                attempts += 1
        elif distribution == 'regular':
            # Regular grid with perturbation
            side = int(num_cells ** (1/3)) + 1
            idx = 0
            for ix in range(side):
                for iy in range(side):
                    for iz in range(side):
                        if idx >= num_cells:
                            break
                        x = (ix + 0.5 + random.gauss(0, 0.1)) / side
                        y = (iy + 0.5 + random.gauss(0, 0.1)) / side
                        z = (iz + 0.5 + random.gauss(0, 0.1)) / side
                        x, y, z = max(0.02, min(0.98, x)), max(0.02, min(0.98, y)), max(0.02, min(0.98, z))
                        cell_type = select_type()
                        self.cells.append(CellSite(
                            id=idx, x=x, y=y, z=z,
                            cell_type=cell_type,
                            diameter_um=8.0 + random.uniform(-2, 5),
                            orientation=(random.uniform(0, 360), random.uniform(0, 90), random.uniform(0, 90))
                        ))
                        idx += 1
        else:
            # Random distribution
            for i in range(num_cells):
                cell_type = select_type()
                self.cells.append(CellSite(
                    id=i,
                    x=random.random(), y=random.random(), z=random.random(),
                    cell_type=cell_type,
                    diameter_um=8.0 + random.uniform(-2, 5),
                    orientation=(random.uniform(0, 360), random.uniform(0, 90), random.uniform(0, 90))
                ))

        self.update()
        self.cells_changed.emit()

    def _get_visible_cells(self) -> List[CellSite]:
        """Get cells visible in current Z-slice."""
        return [c for c in self.cells if abs(c.z - self.depth_slice) <= self.depth_tolerance]

    def _cell_to_screen(self, cell: CellSite) -> Tuple[float, float]:
        """Convert cell position to screen coordinates."""
        w, h = self.width(), self.height()
        margin = 15
        screen_x = margin + (cell.x * self.zoom + self.pan_x) * (w - 2 * margin)
        screen_y = margin + (cell.y * self.zoom + self.pan_y) * (h - 2 * margin)
        return screen_x, screen_y

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 15

        # Draw ECM background
        self._draw_ecm_background(painter, margin, w, h)

        # Draw grid
        self._draw_grid(painter, margin, w, h)

        # Draw cells
        visible = self._get_visible_cells()
        for cell in visible:
            self._draw_cell(painter, cell)

        # Draw info overlay
        self._draw_info_overlay(painter, w, h, len(visible))

        painter.end()

    def _draw_ecm_background(self, painter: QPainter, margin: int, w: int, h: int):
        """Draw ECM composition as subtle background pattern."""
        # Blend ECM component colors
        ecm_colors = {
            'collagen_i': QColor(200, 180, 160, 30),
            'collagen_ii': QColor(180, 200, 180, 30),
            'elastin': QColor(255, 220, 180, 30),
            'proteoglycans': QColor(180, 180, 220, 30),
            'hyaluronan': QColor(180, 220, 255, 30),
            'water': QColor(200, 220, 255, 20),
        }

        if self.ecm_composition:
            # Draw colored rectangles for each ECM component
            for comp, fraction in self.ecm_composition.items():
                if comp in ecm_colors and fraction > 0:
                    color = ecm_colors[comp]
                    color.setAlpha(int(fraction * 60))
                    painter.fillRect(margin, margin, w - 2*margin, h - 2*margin, color)

    def _draw_grid(self, painter: QPainter, margin: int, w: int, h: int):
        """Draw background grid."""
        painter.setPen(QPen(QColor(50, 60, 70), 1))
        for i in range(11):
            t = i / 10.0
            x = margin + t * self.zoom * (w - 2 * margin) + self.pan_x * (w - 2 * margin)
            y = margin + t * self.zoom * (h - 2 * margin) + self.pan_y * (h - 2 * margin)
            if margin <= x <= w - margin:
                painter.drawLine(int(x), margin, int(x), h - margin)
            if margin <= y <= h - margin:
                painter.drawLine(margin, int(y), w - margin, int(y))

    def _draw_cell(self, painter: QPainter, cell: CellSite):
        """Draw a single cell."""
        sx, sy = self._cell_to_screen(cell)
        w, h = self.width(), self.height()
        margin = 15

        if not (margin <= sx <= w - margin and margin <= sy <= h - margin):
            return

        # Size based on diameter and zoom
        size = (cell.diameter_um / self.domain_x) * (w - 2*margin) * self.zoom * 3
        size = max(5, min(40, size))

        color = cell.get_color()
        if cell.id == self.selected_cell:
            color = color.lighter(140)
        elif cell.id == self.hovered_cell:
            color = color.lighter(120)

        # Draw cell with gradient
        gradient = QRadialGradient(sx, sy, size)
        gradient.setColorAt(0, color.lighter(130))
        gradient.setColorAt(0.6, color)
        gradient.setColorAt(1, color.darker(120))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(60, 60, 80), 1))
        painter.drawEllipse(QPointF(sx, sy), size, size)

        # Draw nucleus (darker center)
        nucleus_size = size * 0.4
        nucleus_color = color.darker(150)
        painter.setBrush(QBrush(nucleus_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(sx, sy), nucleus_size, nucleus_size)

    def _draw_info_overlay(self, painter: QPainter, w: int, h: int, visible_count: int):
        """Draw info overlay."""
        painter.setPen(QPen(QColor(200, 220, 255)))
        painter.setFont(QFont("Arial", 9))

        info_lines = [
            f"Cells: {len(self.cells)} ({visible_count} visible)",
            f"Slice: Z = {self.depth_slice:.2f}",
            f"Domain: {self.domain_x:.0f}×{self.domain_y:.0f}×{self.domain_z:.0f} µm",
        ]

        y = 15
        for line in info_lines:
            painter.drawText(10, y, line)
            y += 14

    def get_microstructure_data(self) -> Dict:
        """Get microstructure data for JSON export (like alloy GrainStructure)."""
        # Calculate cell type distribution
        type_counts = {}
        for cell in self.cells:
            type_counts[cell.cell_type] = type_counts.get(cell.cell_type, 0) + 1

        type_fractions = {k: v/len(self.cells) if self.cells else 0
                          for k, v in type_counts.items()}

        return {
            'domain_size': {
                'x_um': self.domain_x,
                'y_um': self.domain_y,
                'z_um': self.domain_z
            },
            'num_cells': len(self.cells),
            'cell_density_per_mm3': self.cell_density_per_mm3,
            'cell_type_distribution': type_fractions,
            'ecm_composition': self.ecm_composition,
            'spatial_distribution': 'voronoi_sampled',
            'cells': [
                {
                    'id': c.id,
                    'x': c.x, 'y': c.y, 'z': c.z,
                    'cell_type': c.cell_type,
                    'diameter_um': c.diameter_um,
                    'orientation': list(c.orientation)
                }
                for c in self.cells
            ]
        }

    def set_ecm_composition(self, ecm: Dict[str, float]):
        """Set ECM composition for background visualization."""
        self.ecm_composition = ecm
        self.update()


class PropertiesSummaryWidget(QWidget):
    """Summary panel showing calculated properties like the alloy dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("""
            QLabel {
                color: #ccc;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                background: rgba(40, 40, 60, 150);
                padding: 10px;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.summary_label)

    def update_summary(self, component: Optional['BiologicalComponent'], level: str = ""):
        """Update the summary display."""
        if not component:
            self.summary_label.setText("Configure component to see properties...")
            return

        props = component.properties
        name = component.name

        # Build summary based on level
        lines = [f"<b style='color: #667eea;'>{name}</b>", ""]

        if level == "protein":
            lines.extend([
                "<b>Sequence Properties:</b>",
                f"  Length: {props.get('length', 'N/A')} residues",
                f"  Molecular Mass: {props.get('molecular_mass', 0):.2f} Da",
                f"  Formula: {props.get('molecular_formula', 'N/A')}",
                "",
                "<b>Physicochemical:</b>",
                f"  Isoelectric Point (pI): {props.get('isoelectric_point', 0):.2f}",
                f"  Charge at pH 7: {props.get('charge_pH7', 0):+.2f}",
                f"  GRAVY Score: {props.get('gravy', 0):.3f}",
                "",
                "<b>Stability:</b>",
                f"  Instability Index: {props.get('instability_index', 0):.2f}",
                f"  Stable: {'Yes' if props.get('is_stable') else 'No'}",
                f"  Aliphatic Index: {props.get('aliphatic_index', 0):.2f}",
            ])
        elif level == "nucleic_acid":
            lines.extend([
                f"<b>Type:</b> {props.get('type', 'DNA')}",
                f"<b>Length:</b> {props.get('length', 0)} bp",
                f"<b>GC Content:</b> {props.get('gc_content', 0):.1f}%",
                f"<b>Tm:</b> {props.get('melting_temperature', 0):.1f} °C",
                f"<b>Mass:</b> {props.get('molecular_mass', 0):.2f} Da",
            ])
        elif level == "cell":
            lines.extend([
                f"<b>Type:</b> {props.get('cell_type', 'generic')}",
                f"<b>Diameter:</b> {props.get('diameter_um', 0):.1f} μm",
                f"<b>Volume:</b> {props.get('volume_fl', 0):.2f} fL",
                f"<b>Mass:</b> {props.get('mass_pg', 0):.2f} pg",
                f"<b>Metabolic Rate:</b> {props.get('metabolic_rate_fW', 0):.2f} fW",
                f"<b>Surface Area:</b> {props.get('surface_area_um2', 0):.2f} μm²",
            ])
        elif level == "biomaterial":
            lines.extend([
                f"<b>Young's Modulus:</b> {props.get('youngs_modulus_MPa', 0):.4f} MPa",
                f"<b>Density:</b> {props.get('density_g_cm3', 0):.3f} g/cm³",
                f"<b>Porosity:</b> {props.get('porosity', 0):.1f}%",
                f"<b>Stiffness:</b> {props.get('stiffness_category', 'N/A')}",
            ])
        else:
            # Generic properties
            for key, value in list(props.items())[:10]:
                if isinstance(value, float):
                    lines.append(f"<b>{key.replace('_', ' ').title()}:</b> {value:.4g}")
                elif not isinstance(value, (dict, list)):
                    lines.append(f"<b>{key.replace('_', ' ').title()}:</b> {value}")

        self.summary_label.setText("<br>".join(lines))


class PropertyCalculatorWidget(QWidget):
    """Real-time property calculator with formula display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.props_table = QTableWidget(0, 2)
        self.props_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.props_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.props_table.setStyleSheet("""
            QTableWidget {
                background: rgba(40, 40, 60, 200);
                color: white;
                gridline-color: #555;
            }
            QHeaderView::section {
                background: #444;
                color: white;
                padding: 5px;
            }
        """)
        layout.addWidget(self.props_table)

        # Formula info
        self.formula_label = QLabel("")
        self.formula_label.setWordWrap(True)
        self.formula_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.formula_label)

    def update_properties(self, properties: Dict[str, Any], formulas: Dict[str, str] = None):
        """Update displayed properties."""
        self.props_table.setRowCount(len(properties))

        for i, (key, value) in enumerate(properties.items()):
            key_item = QTableWidgetItem(key.replace('_', ' ').title())
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.props_table.setItem(i, 0, key_item)

            if isinstance(value, float):
                value_str = f"{value:.4g}"
            elif isinstance(value, dict):
                value_str = json.dumps(value, indent=1)
            else:
                value_str = str(value)

            value_item = QTableWidgetItem(value_str)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            self.props_table.setItem(i, 1, value_item)

        # Update formula info
        if formulas:
            formula_text = "\n".join(f"• {k}: {v}" for k, v in formulas.items())
            self.formula_label.setText(f"Formulas used:\n{formula_text}")


class BiologicalSystemBuilderDialog(QDialog):
    """
    Main dialog for building biological systems at any level.
    Supports the complete hierarchy from atoms to biomaterials.
    """

    component_created = Signal(object)  # BiologicalComponent

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Biological System Builder")
        self.setMinimumSize(1100, 800)

        self.factory = BiologicalComponentFactory()
        self.current_component = None
        self.predictor_settings = {}  # Configurable formula parameters

        self.setup_ui()
        self._load_default_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title_layout = QHBoxLayout()
        title = QLabel("Build Biological Systems")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #667eea;")
        title_layout.addWidget(title)

        # Level indicator
        self.level_indicator = QLabel("")
        self.level_indicator.setStyleSheet("color: #4CAF50; font-weight: bold;")
        title_layout.addStretch()
        title_layout.addWidget(self.level_indicator)

        # Settings button
        settings_btn = QPushButton("⚙ Formula Settings")
        settings_btn.setToolTip("Configure predictor formulas and parameters")
        settings_btn.setStyleSheet("""
            QPushButton {
                background: rgba(102, 126, 234, 100);
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(139, 92, 246, 150);
            }
        """)
        settings_btn.clicked.connect(self._open_settings)
        title_layout.addWidget(settings_btn)

        layout.addLayout(title_layout)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Builder tabs
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.level_tabs = QTabWidget()
        # Note: connect to currentChanged AFTER props_summary is created to avoid AttributeError

        # Create tabs for each level
        self._create_protein_tab()
        self._create_nucleic_acid_tab()
        self._create_cell_component_tab()
        self._create_cell_tab()
        self._create_tissue_tab()
        self._create_biomaterial_tab()

        left_layout.addWidget(self.level_tabs)

        splitter.addWidget(left_panel)

        # Right panel - Preview and hierarchy
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Properties summary (like alloy dialog)
        summary_group = QGroupBox("Properties Summary")
        summary_group.setStyleSheet(self._get_group_style())
        summary_layout = QVBoxLayout(summary_group)

        self.props_summary = PropertiesSummaryWidget()
        summary_layout.addWidget(self.props_summary)

        # Connect tab changed signal now that props_summary exists
        self.level_tabs.currentChanged.connect(self._on_tab_changed)

        right_layout.addWidget(summary_group)

        # JSON Editor (editable)
        json_group = QGroupBox("Component JSON")
        json_group.setStyleSheet(self._get_group_style())
        json_layout = QVBoxLayout(json_group)

        self.json_editor = JsonEditorWidget()
        self.json_editor.json_changed.connect(self._on_json_edited)
        json_layout.addWidget(self.json_editor)

        right_layout.addWidget(json_group)

        # Hierarchy browser (collapsible)
        hierarchy_group = QGroupBox("Component Library")
        hierarchy_group.setStyleSheet(self._get_group_style())
        hierarchy_group.setCheckable(True)
        hierarchy_group.setChecked(False)  # Start collapsed
        hierarchy_layout = QVBoxLayout(hierarchy_group)

        self.hierarchy_browser = HierarchyBrowserWidget(self.factory)
        self.hierarchy_browser.component_selected.connect(self._on_component_selected)
        self.hierarchy_browser.setMaximumHeight(200)
        hierarchy_layout.addWidget(self.hierarchy_browser)

        right_layout.addWidget(hierarchy_group)

        # Keep old json_preview for backwards compatibility (hidden)
        self.json_preview = self.json_editor.json_edit

        splitter.addWidget(right_panel)
        splitter.setSizes([650, 450])

        layout.addWidget(splitter)

        # Bottom buttons
        btn_layout = QHBoxLayout()

        # Export button
        self.export_btn = QPushButton("Export JSON")
        self.export_btn.setToolTip("Export component to publication-ready JSON file")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:disabled { background: #666; }
        """)
        self.export_btn.clicked.connect(self._export_json)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)

        btn_layout.addStretch()

        self.save_btn = QPushButton("Save Component")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #45a049; }
            QPushButton:disabled { background: #666; }
        """)
        self.save_btn.clicked.connect(self._save_component)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)

        self.build_btn = QPushButton("Build & Add to Scene")
        self.build_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                color: white;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #8B5CF6; }
            QPushButton:disabled { background: #666; }
        """)
        self.build_btn.clicked.connect(self._build_component)
        self.build_btn.setEnabled(False)
        btn_layout.addWidget(self.build_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #666;
                color: white;
                padding: 10px 25px;
                border-radius: 5px;
            }
            QPushButton:hover { background: #777; }
        """)
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _get_group_style(self) -> str:
        return """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """

    # === Tab Creation ===

    def _create_protein_tab(self):
        """Create the protein building tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Quick presets
        preset_widget = PresetSelectorWidget("protein")
        preset_widget.preset_selected.connect(self._on_protein_preset_selected)
        layout.addWidget(preset_widget)

        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Protein Name:"))
        self.protein_name = QLineEdit()
        self.protein_name.setPlaceholderText("e.g., Custom Hemoglobin")
        self.protein_name.textChanged.connect(self._update_protein_preview)
        name_layout.addWidget(self.protein_name)
        layout.addLayout(name_layout)

        # Sequence editor
        self.protein_sequence = SequenceEditorWidget("protein")
        self.protein_sequence.sequence_changed.connect(self._update_protein_preview)
        layout.addWidget(self.protein_sequence)

        # Properties info with formulas
        props_info = QLabel(
            "<b>Formulas Used:</b><br>"
            "• <b>Mass:</b> Σ(residue_mass) - (n-1) × 18.015 Da (water loss)<br>"
            "• <b>pI:</b> pH where Σ(charges) = 0 (Henderson-Hasselbalch)<br>"
            "• <b>II:</b> (10/L) × Σ(DIWV[i,i+1]) (Guruprasad 1990)<br>"
            "• <b>AI:</b> X_A + 2.9×X_V + 3.9×(X_I + X_L) (Ikai 1980)<br>"
            "• <b>GRAVY:</b> Σ(hydropathy) / L (Kyte-Doolittle)"
        )
        props_info.setStyleSheet("color: #888; padding: 10px; background: rgba(40,40,60,100); border-radius: 5px;")
        layout.addWidget(props_info)

        layout.addStretch()

        self.level_tabs.addTab(tab, "🧬 Protein")

    def _create_nucleic_acid_tab(self):
        """Create the nucleic acid building tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Quick presets
        preset_widget = PresetSelectorWidget("nucleic_acid")
        preset_widget.preset_selected.connect(self._on_na_preset_selected)
        layout.addWidget(preset_widget)

        # Name and type
        header = QHBoxLayout()
        header.addWidget(QLabel("Name:"))
        self.na_name = QLineEdit()
        self.na_name.setPlaceholderText("e.g., Custom Gene")
        self.na_name.textChanged.connect(self._update_na_preview)
        header.addWidget(self.na_name)

        header.addWidget(QLabel("Type:"))
        self.na_type = QComboBox()
        self.na_type.addItems(["DNA", "RNA"])
        self.na_type.currentTextChanged.connect(self._on_na_type_changed)
        header.addWidget(self.na_type)
        layout.addLayout(header)

        # Sequence editor (stacked for DNA/RNA)
        self.na_sequence_stack = QStackedWidget()
        self.dna_sequence = SequenceEditorWidget("dna")
        self.dna_sequence.sequence_changed.connect(self._update_na_preview)
        self.na_sequence_stack.addWidget(self.dna_sequence)

        self.rna_sequence = SequenceEditorWidget("rna")
        self.rna_sequence.sequence_changed.connect(self._update_na_preview)
        self.na_sequence_stack.addWidget(self.rna_sequence)

        layout.addWidget(self.na_sequence_stack)

        # Properties info with formulas
        props_info = QLabel(
            "<b>Formulas Used:</b><br>"
            "• <b>Mass:</b> Σ(nucleotide_mass) - (n-1) × 18.015 Da<br>"
            "• <b>GC%:</b> 100 × (G+C) / L<br>"
            "• <b>Tm:</b> ΔG = ΔH - TΔS (SantaLucia NN, 1998)<br>"
            "• <b>Salt:</b> Tm += 16.6 × log₁₀([Na⁺])"
        )
        props_info.setStyleSheet("color: #888; padding: 10px; background: rgba(40,40,60,100); border-radius: 5px;")
        layout.addWidget(props_info)

        layout.addStretch()

        self.level_tabs.addTab(tab, "🔬 Nucleic Acid")

    def _create_cell_component_tab(self):
        """Create the cell component building tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Name and type
        header = QGridLayout()
        header.addWidget(QLabel("Component Name:"), 0, 0)
        self.comp_name = QLineEdit()
        self.comp_name.setPlaceholderText("e.g., Custom Ribosome")
        self.comp_name.textChanged.connect(self._update_component_preview)
        header.addWidget(self.comp_name, 0, 1)

        header.addWidget(QLabel("Type:"), 1, 0)
        self.comp_type = QComboBox()
        self.comp_type.addItems([
            "complex", "ribosome", "proteasome", "spliceosome",
            "mitochondrion", "membrane_protein", "channel", "enzyme"
        ])
        self.comp_type.setEditable(True)
        self.comp_type.currentTextChanged.connect(self._update_component_preview)
        header.addWidget(self.comp_type, 1, 1)

        header.addWidget(QLabel("Copy Number:"), 2, 0)
        self.comp_copy = QSpinBox()
        self.comp_copy.setRange(1, 1000000)
        self.comp_copy.setValue(1000)
        self.comp_copy.valueChanged.connect(self._update_component_preview)
        header.addWidget(self.comp_copy, 2, 1)

        layout.addLayout(header)

        # Protein subunits
        subunits_group = QGroupBox("Protein Subunits")
        subunits_layout = QVBoxLayout(subunits_group)

        self.subunit_list = QListWidget()
        self.subunit_list.setMaximumHeight(150)
        self.subunit_list.setStyleSheet("""
            QListWidget {
                background: rgba(40, 40, 60, 200);
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        subunits_layout.addWidget(self.subunit_list)

        subunit_btns = QHBoxLayout()
        add_subunit_btn = QPushButton("Add From Library")
        add_subunit_btn.clicked.connect(self._add_subunit_from_library)
        subunit_btns.addWidget(add_subunit_btn)

        add_custom_btn = QPushButton("Add Custom Sequence")
        add_custom_btn.clicked.connect(self._add_custom_subunit)
        subunit_btns.addWidget(add_custom_btn)

        subunits_layout.addLayout(subunit_btns)

        layout.addWidget(subunits_group)

        # Properties info
        props_info = QLabel(
            "<b>Properties Calculated:</b><br>"
            "• Total Molecular Mass (sum of subunits)<br>"
            "• Subunit Count<br>"
            "• Copy Number per Cell<br>"
            "• Cellular Mass Contribution"
        )
        props_info.setStyleSheet("color: #888; padding: 10px;")
        layout.addWidget(props_info)

        layout.addStretch()

        self.level_tabs.addTab(tab, "⚙️ Cell Component")

    def _create_cell_tab(self):
        """Create the cell building tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Quick presets
        preset_widget = PresetSelectorWidget("cell")
        preset_widget.preset_selected.connect(self._on_cell_preset_selected)
        layout.addWidget(preset_widget)

        # Cell properties
        props = QGridLayout()
        props.addWidget(QLabel("Cell Name:"), 0, 0)
        self.cell_name = QLineEdit()
        self.cell_name.setPlaceholderText("e.g., Custom Neuron")
        self.cell_name.textChanged.connect(self._update_cell_preview)
        props.addWidget(self.cell_name, 0, 1)

        props.addWidget(QLabel("Cell Type:"), 1, 0)
        self.cell_type = QComboBox()
        self.cell_type.addItems([
            "epithelial", "neuron", "muscle", "fibroblast",
            "hepatocyte", "cardiomyocyte", "osteocyte", "adipocyte"
        ])
        self.cell_type.setEditable(True)
        self.cell_type.currentTextChanged.connect(self._update_cell_preview)
        props.addWidget(self.cell_type, 1, 1)

        props.addWidget(QLabel("Diameter (μm):"), 2, 0)
        self.cell_diameter = QDoubleSpinBox()
        self.cell_diameter.setRange(0.1, 500.0)
        self.cell_diameter.setValue(10.0)
        self.cell_diameter.setSingleStep(0.5)
        self.cell_diameter.valueChanged.connect(self._update_cell_preview)
        props.addWidget(self.cell_diameter, 2, 1)

        layout.addLayout(props)

        # Components
        comp_group = QGroupBox("Cell Components")
        comp_layout = QVBoxLayout(comp_group)

        self.cell_comp_list = QListWidget()
        self.cell_comp_list.setMaximumHeight(120)
        self.cell_comp_list.setStyleSheet("""
            QListWidget {
                background: rgba(40, 40, 60, 200);
                color: white;
            }
        """)
        comp_layout.addWidget(self.cell_comp_list)

        comp_btns = QHBoxLayout()
        add_comp_btn = QPushButton("Add Component")
        add_comp_btn.clicked.connect(self._add_cell_component)
        comp_btns.addWidget(add_comp_btn)
        comp_layout.addLayout(comp_btns)

        layout.addWidget(comp_group)

        # Properties info
        props_info = QLabel(
            "<b>Properties Calculated (Kleiber's Law):</b><br>"
            "• Volume (4/3 πr³)<br>"
            "• Mass (volume × density)<br>"
            "• Metabolic Rate: B = B₀ × M^α (α ≈ 0.75)<br>"
            "• Surface Area (4πr²)<br>"
            "• Surface/Volume Ratio<br>"
            "• Doubling Time"
        )
        props_info.setStyleSheet("color: #888; padding: 10px;")
        layout.addWidget(props_info)

        layout.addStretch()

        self.level_tabs.addTab(tab, "🦠 Cell")

    def _create_tissue_tab(self):
        """Create the tissue building tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Tissue properties
        props = QGridLayout()
        props.addWidget(QLabel("Tissue Name:"), 0, 0)
        self.tissue_name = QLineEdit()
        self.tissue_name.setPlaceholderText("e.g., Custom Cartilage")
        self.tissue_name.textChanged.connect(self._update_tissue_preview)
        props.addWidget(self.tissue_name, 0, 1)

        props.addWidget(QLabel("Vascularization:"), 1, 0)
        self.tissue_vasc = QDoubleSpinBox()
        self.tissue_vasc.setRange(0.0, 0.5)
        self.tissue_vasc.setValue(0.05)
        self.tissue_vasc.setSingleStep(0.01)
        self.tissue_vasc.valueChanged.connect(self._update_tissue_preview)
        props.addWidget(self.tissue_vasc, 1, 1)

        layout.addLayout(props)

        # Cell composition
        cell_group = QGroupBox("Cell Composition")
        cell_layout = QVBoxLayout(cell_group)

        self.tissue_cell_list = QListWidget()
        self.tissue_cell_list.setMaximumHeight(100)
        cell_layout.addWidget(self.tissue_cell_list)

        add_cell_btn = QPushButton("Add Cell Type")
        add_cell_btn.clicked.connect(self._add_tissue_cell)
        cell_layout.addWidget(add_cell_btn)

        layout.addWidget(cell_group)

        # ECM composition
        ecm_group = QGroupBox("Extracellular Matrix")
        ecm_layout = QVBoxLayout(ecm_group)

        self.tissue_ecm_mixer = ComponentMixerWidget("ecm")
        self.tissue_ecm_mixer.composition_changed.connect(self._update_tissue_preview)
        ecm_layout.addWidget(self.tissue_ecm_mixer)

        layout.addWidget(ecm_group)

        # Properties info
        props_info = QLabel(
            "<b>Properties Calculated:</b><br>"
            "• Composite Modulus (Voigt-Reuss average)<br>"
            "• Tissue Density<br>"
            "• Cell Fraction<br>"
            "• Metabolic Rate per mm³"
        )
        props_info.setStyleSheet("color: #888; padding: 10px;")
        layout.addWidget(props_info)

        self.level_tabs.addTab(tab, "🫀 Tissue")

    def _create_biomaterial_tab(self):
        """Create the biomaterial building tab with Voronoi microstructure sampling."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Quick presets
        preset_widget = PresetSelectorWidget("biomaterial")
        preset_widget.preset_selected.connect(self._on_biomaterial_preset_selected)
        layout.addWidget(preset_widget)

        # Use splitter for properties and visualization
        splitter = QSplitter(Qt.Horizontal)

        # Left side - properties
        props_widget = QWidget()
        props_layout = QVBoxLayout(props_widget)
        props_layout.setContentsMargins(0, 0, 5, 0)

        # Material properties
        props = QGridLayout()
        props.addWidget(QLabel("Material Name:"), 0, 0)
        self.biomat_name = QLineEdit()
        self.biomat_name.setPlaceholderText("e.g., Custom Scaffold")
        self.biomat_name.textChanged.connect(self._update_biomaterial_preview)
        props.addWidget(self.biomat_name, 0, 1)

        props.addWidget(QLabel("Porosity (%):"), 1, 0)
        self.biomat_porosity = QDoubleSpinBox()
        self.biomat_porosity.setRange(0.0, 95.0)
        self.biomat_porosity.setValue(10.0)
        self.biomat_porosity.valueChanged.connect(self._update_biomaterial_preview)
        props.addWidget(self.biomat_porosity, 1, 1)

        props.addWidget(QLabel("Porosity Model:"), 2, 0)
        self.biomat_poro_model = QComboBox()
        self.biomat_poro_model.addItems(["gibson_ashby", "exponential", "linear"])
        self.biomat_poro_model.setToolTip(
            "Gibson-Ashby: E/E₀ = (1-φ)² (open-cell foam)\n"
            "Exponential: E/E₀ = (1-φ)^1.5\n"
            "Linear: E/E₀ = (1-φ)"
        )
        self.biomat_poro_model.currentTextChanged.connect(self._update_biomaterial_preview)
        props.addWidget(self.biomat_poro_model, 2, 1)

        props_layout.addLayout(props)

        # ECM composition
        ecm_group = QGroupBox("ECM Composition")
        ecm_layout = QVBoxLayout(ecm_group)
        self.biomat_ecm_mixer = ComponentMixerWidget("ecm")
        self.biomat_ecm_mixer.composition_changed.connect(self._on_biomat_ecm_changed)
        ecm_layout.addWidget(self.biomat_ecm_mixer)
        props_layout.addWidget(ecm_group)

        # Properties info
        props_info = QLabel(
            "<b>Properties Calculated:</b><br>"
            "• Young's Modulus: E = (E_voigt + E_reuss) / 2<br>"
            "• Porosity Effect: E_eff = E × (1-φ)^n<br>"
            "• Composite Density • Stiffness Category"
        )
        props_info.setStyleSheet("color: #888; padding: 5px; font-size: 10px;")
        props_layout.addWidget(props_info)

        splitter.addWidget(props_widget)

        # Right side - Microstructure visualization
        micro_widget = QWidget()
        micro_layout = QVBoxLayout(micro_widget)
        micro_layout.setContentsMargins(5, 0, 0, 0)

        micro_header = QHBoxLayout()
        micro_header.addWidget(QLabel("<b>Microstructure (Voronoi Sampling)</b>"))
        micro_header.addStretch()
        micro_layout.addLayout(micro_header)

        # Microstructure visualization
        self.biomat_microstructure = BiologicalMicrostructureWidget()
        self.biomat_microstructure.cells_changed.connect(self._update_biomaterial_preview)
        self.biomat_microstructure.setMinimumHeight(180)
        micro_layout.addWidget(self.biomat_microstructure)

        # Microstructure controls
        micro_controls = QHBoxLayout()

        micro_controls.addWidget(QLabel("Cells:"))
        self.biomat_cell_count = QSpinBox()
        self.biomat_cell_count.setRange(5, 500)
        self.biomat_cell_count.setValue(50)
        self.biomat_cell_count.setMaximumWidth(60)
        micro_controls.addWidget(self.biomat_cell_count)

        micro_controls.addWidget(QLabel("Dist:"))
        self.biomat_dist_combo = QComboBox()
        self.biomat_dist_combo.addItems(['poisson', 'random', 'regular'])
        self.biomat_dist_combo.setMaximumWidth(80)
        micro_controls.addWidget(self.biomat_dist_combo)

        micro_controls.addWidget(QLabel("Seed:"))
        self.biomat_seed = QSpinBox()
        self.biomat_seed.setRange(0, 9999)
        self.biomat_seed.setValue(42)
        self.biomat_seed.setMaximumWidth(60)
        micro_controls.addWidget(self.biomat_seed)

        regen_btn = QPushButton("Generate")
        regen_btn.setStyleSheet("""
            QPushButton {
                background: #4a9eff;
                color: white;
                padding: 3px 10px;
                border-radius: 3px;
            }
            QPushButton:hover { background: #3a8eef; }
        """)
        regen_btn.clicked.connect(self._regenerate_biomat_microstructure)
        micro_controls.addWidget(regen_btn)

        micro_controls.addStretch()
        micro_layout.addLayout(micro_controls)

        # Domain size
        domain_layout = QHBoxLayout()
        domain_layout.addWidget(QLabel("Domain (µm):"))
        self.biomat_domain_x = QSpinBox()
        self.biomat_domain_x.setRange(10, 2000)
        self.biomat_domain_x.setValue(500)
        self.biomat_domain_x.setMaximumWidth(60)
        self.biomat_domain_x.valueChanged.connect(self._on_biomat_domain_changed)
        domain_layout.addWidget(self.biomat_domain_x)
        domain_layout.addWidget(QLabel("×"))
        self.biomat_domain_y = QSpinBox()
        self.biomat_domain_y.setRange(10, 2000)
        self.biomat_domain_y.setValue(500)
        self.biomat_domain_y.setMaximumWidth(60)
        self.biomat_domain_y.valueChanged.connect(self._on_biomat_domain_changed)
        domain_layout.addWidget(self.biomat_domain_y)
        domain_layout.addWidget(QLabel("×"))
        self.biomat_domain_z = QSpinBox()
        self.biomat_domain_z.setRange(10, 500)
        self.biomat_domain_z.setValue(100)
        self.biomat_domain_z.setMaximumWidth(60)
        self.biomat_domain_z.valueChanged.connect(self._on_biomat_domain_changed)
        domain_layout.addWidget(self.biomat_domain_z)
        domain_layout.addStretch()
        micro_layout.addLayout(domain_layout)

        splitter.addWidget(micro_widget)
        splitter.setSizes([350, 350])

        layout.addWidget(splitter)

        self.level_tabs.addTab(tab, "🧱 Biomaterial")

    # === Event Handlers ===

    def _on_tab_changed(self, index: int):
        """Handle tab changes."""
        levels = ["Protein", "Nucleic Acid", "Cell Component", "Cell", "Tissue", "Biomaterial"]
        if 0 <= index < len(levels):
            self.level_indicator.setText(f"Building: {levels[index]}")

        # Trigger appropriate preview update
        update_funcs = [
            self._update_protein_preview,
            self._update_na_preview,
            self._update_component_preview,
            self._update_cell_preview,
            self._update_tissue_preview,
            self._update_biomaterial_preview,
        ]
        if 0 <= index < len(update_funcs):
            update_funcs[index]()

    def _on_na_type_changed(self, na_type: str):
        """Handle DNA/RNA type change."""
        self.na_sequence_stack.setCurrentIndex(0 if na_type == "DNA" else 1)
        self._update_na_preview()

    def _on_component_selected(self, component: BiologicalComponent):
        """Handle component selection from hierarchy browser."""
        self.current_component = component
        self.json_editor.set_json(component.to_dict())
        self.props_summary.update_summary(component, component.level.name.lower())
        self.save_btn.setEnabled(False)  # Already saved
        self.build_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

    def _on_json_edited(self, data: Dict):
        """Handle JSON edits from the editor."""
        if not data:
            return

        try:
            # Determine level from current tab
            level_map = {
                0: BiologicalLevel.PROTEIN,
                1: BiologicalLevel.NUCLEIC_ACID,
                2: BiologicalLevel.CELL_COMPONENT,
                3: BiologicalLevel.CELL,
                4: BiologicalLevel.TISSUE,
                5: BiologicalLevel.BIOMATERIAL,
            }
            level = level_map.get(self.level_tabs.currentIndex(), BiologicalLevel.PROTEIN)

            # Rebuild component from edited JSON
            name = data.get('name', 'Edited Component')
            props = data.get('properties', {})

            # Update input fields based on edited data
            if level == BiologicalLevel.PROTEIN and 'sequence' in props:
                self.protein_name.setText(name)
                self.protein_sequence.set_sequence(props['sequence'])
            elif level == BiologicalLevel.NUCLEIC_ACID and 'sequence' in props:
                self.na_name.setText(name)
                seq = props['sequence']
                if props.get('type') == 'RNA':
                    self.na_type.setCurrentText('RNA')
                    self.rna_sequence.set_sequence(seq)
                else:
                    self.na_type.setCurrentText('DNA')
                    self.dna_sequence.set_sequence(seq)
            elif level == BiologicalLevel.CELL:
                self.cell_name.setText(name)
                if 'diameter_um' in props:
                    self.cell_diameter.setValue(props['diameter_um'])
                if 'cell_type' in props:
                    self.cell_type.setCurrentText(props['cell_type'])
            elif level == BiologicalLevel.BIOMATERIAL:
                self.biomat_name.setText(name)
                if 'porosity' in props:
                    self.biomat_porosity.setValue(props['porosity'])
                if 'ecm_composition' in props:
                    self.biomat_ecm_mixer.set_composition(props['ecm_composition'])

        except Exception as e:
            QMessageBox.warning(self, "JSON Error", f"Could not apply JSON: {e}")

    # === Preset Handlers ===

    def _on_protein_preset_selected(self, name: str, sequence: str):
        """Handle protein preset selection."""
        self.protein_name.setText(name)
        self.protein_sequence.set_sequence(sequence)

    def _on_na_preset_selected(self, name: str, sequence: str):
        """Handle nucleic acid preset selection."""
        self.na_name.setText(name)
        # Determine if RNA based on U content
        if 'U' in sequence.upper():
            self.na_type.setCurrentText('RNA')
            self.rna_sequence.set_sequence(sequence)
        else:
            self.na_type.setCurrentText('DNA')
            self.dna_sequence.set_sequence(sequence)

    def _on_cell_preset_selected(self, name: str, data: Dict):
        """Handle cell preset selection."""
        self.cell_name.setText(name)
        if 'type' in data:
            self.cell_type.setCurrentText(data['type'])
        if 'diameter_um' in data:
            self.cell_diameter.setValue(data['diameter_um'])

    def _on_biomaterial_preset_selected(self, name: str, composition: Dict):
        """Handle biomaterial preset selection."""
        self.biomat_name.setText(name)
        self.biomat_ecm_mixer.set_composition(composition)
        # Update microstructure with ECM composition
        self.biomat_microstructure.set_ecm_composition(composition)
        self._regenerate_biomat_microstructure()

    def _on_biomat_ecm_changed(self, composition: Dict):
        """Handle ECM composition changes."""
        self.biomat_microstructure.set_ecm_composition(composition)
        self._update_biomaterial_preview()

    def _on_biomat_domain_changed(self):
        """Handle domain size changes."""
        self.biomat_microstructure.domain_x = self.biomat_domain_x.value()
        self.biomat_microstructure.domain_y = self.biomat_domain_y.value()
        self.biomat_microstructure.domain_z = self.biomat_domain_z.value()
        self.biomat_microstructure.update()
        self._update_biomaterial_preview()

    def _regenerate_biomat_microstructure(self):
        """Regenerate the biomaterial microstructure."""
        # Determine cell types based on ECM (if ECM-heavy, fewer cells)
        ecm = self.biomat_ecm_mixer.get_composition()
        ecm_fraction = sum(ecm.values()) if ecm else 0

        # Default cell type distribution
        cell_types = {'fibroblast': 0.7, 'chondrocyte': 0.2, 'adipocyte': 0.1}

        # Adjust based on ECM composition
        if ecm.get('collagen_ii', 0) > 0.1:
            cell_types = {'chondrocyte': 0.8, 'fibroblast': 0.2}
        elif ecm.get('elastin', 0) > 0.05:
            cell_types = {'fibroblast': 0.6, 'muscle': 0.3, 'adipocyte': 0.1}

        self.biomat_microstructure.generate_cells(
            num_cells=self.biomat_cell_count.value(),
            cell_types=cell_types,
            seed=self.biomat_seed.value(),
            distribution=self.biomat_dist_combo.currentText()
        )

    # === Preview Updates ===

    def _update_protein_preview(self):
        """Update protein preview with comprehensive simulation JSON."""
        sequence = self.protein_sequence.get_sequence()
        name = self.protein_name.text() or "Custom Protein"

        if not sequence:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({})
            self.save_btn.setEnabled(False)
            self.build_btn.setEnabled(False)
            return

        try:
            protein = self.factory.create_from_lower_level(
                BiologicalLevel.PROTEIN, [], name, sequence=sequence
            )
            self.current_component = protein

            # Update displays
            self.props_summary.update_summary(protein, "protein")

            # Generate comprehensive simulation JSON
            comprehensive_json = generate_comprehensive_json(
                protein, "protein",
                predictor_settings=self.predictor_settings
            )
            self.json_editor.set_json(comprehensive_json)

            self.save_btn.setEnabled(bool(name))
            self.build_btn.setEnabled(True)
            self.export_btn.setEnabled(True)

        except Exception as e:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"error": str(e)})

    def _update_na_preview(self):
        """Update nucleic acid preview with comprehensive simulation JSON."""
        is_rna = self.na_type.currentText() == "RNA"
        sequence_widget = self.rna_sequence if is_rna else self.dna_sequence
        sequence = sequence_widget.get_sequence()
        name = self.na_name.text() or "Custom NA"

        if not sequence:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({})
            self.save_btn.setEnabled(False)
            self.build_btn.setEnabled(False)
            return

        try:
            na = self.factory.create_from_lower_level(
                BiologicalLevel.NUCLEIC_ACID, [], name,
                sequence=sequence, is_rna=is_rna
            )
            self.current_component = na

            self.props_summary.update_summary(na, "nucleic_acid")

            # Generate comprehensive simulation JSON
            comprehensive_json = generate_comprehensive_json(
                na, "nucleic_acid",
                predictor_settings=self.predictor_settings
            )
            self.json_editor.set_json(comprehensive_json)

            self.save_btn.setEnabled(bool(name))
            self.build_btn.setEnabled(True)
            self.export_btn.setEnabled(True)

        except Exception as e:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"error": str(e)})

    def _update_component_preview(self):
        """Update cell component preview with comprehensive JSON."""
        name = self.comp_name.text() or "Custom Component"
        comp_type = self.comp_type.currentText()
        copy_number = self.comp_copy.value()

        # Gather subunit proteins
        proteins = []
        for i in range(self.subunit_list.count()):
            item = self.subunit_list.item(i)
            protein = item.data(Qt.UserRole)
            if protein:
                proteins.append(protein)

        if not proteins:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"info": "Add protein subunits to calculate properties"})
            self.save_btn.setEnabled(False)
            self.build_btn.setEnabled(False)
            return

        try:
            component = self.factory.derivation_chain.build_cell_component(
                name, proteins, copy_number, comp_type
            )
            self.current_component = component

            self.props_summary.update_summary(component, "cell_component")

            # Generate comprehensive JSON for cell component
            comp_json = {
                "Name": name,
                "Level": "CELL_COMPONENT",
                "Category": "Molecular Complex",
                "ComponentType": comp_type,

                "MolecularProperties": {
                    "TotalMass_Da": component.properties.get('total_mass_Da', 0),
                    "SubunitCount": len(proteins),
                    "CopyNumberPerCell": copy_number,
                },

                "Subunits": [
                    {
                        "name": p.name,
                        "mass_Da": p.properties.get('molecular_mass', 0),
                        "length": p.properties.get('length', 0),
                    }
                    for p in proteins
                ],

                "SimulationParameters": {
                    "Temperature_K": 310,
                    "pH": 7.4,
                    "IonicStrength_M": 0.15,
                }
            }
            self.json_editor.set_json(comp_json)

            self.save_btn.setEnabled(bool(name))
            self.build_btn.setEnabled(True)
            self.export_btn.setEnabled(True)

        except Exception as e:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"error": str(e)})

    def _update_cell_preview(self):
        """Update cell preview with comprehensive simulation JSON."""
        name = self.cell_name.text() or "Custom Cell"
        cell_type = self.cell_type.currentText()
        diameter = self.cell_diameter.value()

        try:
            cell = self.factory.create_component(
                BiologicalLevel.CELL,
                {
                    'name': name,
                    'type': cell_type,
                    'diameter_um': diameter
                }
            )
            self.current_component = cell

            self.props_summary.update_summary(cell, "cell")

            # Generate comprehensive simulation JSON
            comprehensive_json = generate_comprehensive_json(
                cell, "cell",
                predictor_settings=self.predictor_settings
            )
            self.json_editor.set_json(comprehensive_json)

            self.save_btn.setEnabled(bool(name))
            self.build_btn.setEnabled(True)
            self.export_btn.setEnabled(True)

        except Exception as e:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"error": str(e)})

    def _update_tissue_preview(self):
        """Update tissue preview with comprehensive simulation JSON."""
        name = self.tissue_name.text() or "Custom Tissue"
        vasc = self.tissue_vasc.value()
        ecm = self.tissue_ecm_mixer.get_composition()

        if not ecm:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"info": "Add ECM components to calculate properties"})
            return

        # Get cell composition
        cells = {}
        for i in range(self.tissue_cell_list.count()):
            item = self.tissue_cell_list.item(i)
            data = item.data(Qt.UserRole)
            if data:
                cell, fraction = data
                cells[cell] = fraction

        try:
            tissue = self.factory.mixing_system.create_tissue(
                name, cells or {}, ecm, vasc
            )
            self.current_component = tissue

            self.props_summary.update_summary(tissue, "tissue")

            # Generate comprehensive simulation JSON
            comprehensive_json = generate_comprehensive_json(
                tissue, "tissue",
                predictor_settings=self.predictor_settings
            )
            self.json_editor.set_json(comprehensive_json)

            self.save_btn.setEnabled(bool(name))
            self.build_btn.setEnabled(True)
            self.export_btn.setEnabled(True)

        except Exception as e:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"error": str(e)})

    def _update_biomaterial_preview(self):
        """Update biomaterial preview with comprehensive simulation JSON."""
        name = self.biomat_name.text() or "Custom Biomaterial"
        porosity = self.biomat_porosity.value() / 100.0
        ecm = self.biomat_ecm_mixer.get_composition()

        if not ecm:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"info": "Add ECM components to calculate properties"})
            return

        try:
            biomaterial = self.factory.derivation_chain.build_biomaterial(
                name, ecm, porosity=porosity
            )
            self.current_component = biomaterial

            # Add porosity model to properties
            biomaterial.properties['porosity_model'] = self.biomat_poro_model.currentText()
            biomaterial.properties['porosity'] = porosity

            self.props_summary.update_summary(biomaterial, "biomaterial")

            # Generate comprehensive simulation JSON with microstructure
            microstructure_data = self.biomat_microstructure.get_microstructure_data()
            comprehensive_json = generate_comprehensive_json(
                biomaterial, "biomaterial",
                microstructure_data=microstructure_data,
                predictor_settings=self.predictor_settings
            )
            self.json_editor.set_json(comprehensive_json)

            self.save_btn.setEnabled(bool(name))
            self.build_btn.setEnabled(True)
            self.export_btn.setEnabled(True)

        except Exception as e:
            self.props_summary.update_summary(None)
            self.json_editor.set_json({"error": str(e)})

    # === Component Addition Helpers ===

    def _add_subunit_from_library(self):
        """Add a protein subunit from the library."""
        proteins = self.factory.list_available_components(BiologicalLevel.PROTEIN)
        if not proteins:
            QMessageBox.information(self, "No Proteins",
                "No saved proteins found. Create and save proteins first.")
            return

        # Simple selection dialog
        from PySide6.QtWidgets import QInputDialog
        protein_name, ok = QInputDialog.getItem(
            self, "Select Protein", "Choose protein:", proteins, 0, False
        )

        if ok and protein_name:
            protein = self.factory.load_component(BiologicalLevel.PROTEIN, protein_name)
            if protein:
                item = QListWidgetItem(f"{protein.name} ({protein.properties.get('length', '?')} aa)")
                item.setData(Qt.UserRole, protein)
                self.subunit_list.addItem(item)
                self._update_component_preview()

    def _add_custom_subunit(self):
        """Add a custom protein subunit by sequence."""
        from PySide6.QtWidgets import QInputDialog
        sequence, ok = QInputDialog.getText(
            self, "Custom Protein", "Enter amino acid sequence:"
        )

        if ok and sequence:
            sequence = ''.join(sequence.split()).upper()
            protein = self.factory.create_from_lower_level(
                BiologicalLevel.PROTEIN, [], f"Subunit_{self.subunit_list.count()+1}",
                sequence=sequence
            )
            item = QListWidgetItem(f"Custom ({len(sequence)} aa)")
            item.setData(Qt.UserRole, protein)
            self.subunit_list.addItem(item)
            self._update_component_preview()

    def _add_cell_component(self):
        """Add a component to the cell."""
        components = self.factory.list_available_components(BiologicalLevel.CELL_COMPONENT)
        if not components:
            QMessageBox.information(self, "No Components",
                "No saved cell components found. Create and save components first.")
            return

        from PySide6.QtWidgets import QInputDialog
        comp_name, ok = QInputDialog.getItem(
            self, "Select Component", "Choose component:", components, 0, False
        )

        if ok and comp_name:
            component = self.factory.load_component(BiologicalLevel.CELL_COMPONENT, comp_name)
            if component:
                count, ok = QInputDialog.getInt(
                    self, "Copy Number", "How many copies?", 1000, 1, 1000000
                )
                if ok:
                    item = QListWidgetItem(f"{component.name} × {count}")
                    item.setData(Qt.UserRole, (component, count))
                    self.cell_comp_list.addItem(item)
                    self._update_cell_preview()

    def _add_tissue_cell(self):
        """Add a cell type to the tissue."""
        cells = self.factory.list_available_components(BiologicalLevel.CELL)
        if not cells:
            QMessageBox.information(self, "No Cells",
                "No saved cells found. Create and save cells first.")
            return

        from PySide6.QtWidgets import QInputDialog
        cell_name, ok = QInputDialog.getItem(
            self, "Select Cell", "Choose cell type:", cells, 0, False
        )

        if ok and cell_name:
            cell = self.factory.load_component(BiologicalLevel.CELL, cell_name)
            if cell:
                fraction, ok = QInputDialog.getDouble(
                    self, "Cell Fraction", "Volume fraction (0-1):",
                    0.1, 0.0, 1.0, 3
                )
                if ok:
                    item = QListWidgetItem(f"{cell.name}: {fraction*100:.1f}%")
                    item.setData(Qt.UserRole, (cell, fraction))
                    self.tissue_cell_list.addItem(item)
                    self._update_tissue_preview()

    # === Save/Build Actions ===

    def _export_json(self):
        """Export current component to publication-ready JSON file."""
        if not self.current_component:
            return

        from PySide6.QtWidgets import QFileDialog
        import os

        # Determine level for filename suggestion
        level_names = ["protein", "nucleic_acid", "cell_component", "cell", "tissue", "biomaterial"]
        level = level_names[self.level_tabs.currentIndex()] if 0 <= self.level_tabs.currentIndex() < len(level_names) else "component"

        # Clean name for filename
        safe_name = self.current_component.name.replace(' ', '_').replace('/', '_')
        suggested_name = f"{safe_name}.json"

        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON",
            suggested_name,
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Get microstructure data if available
            microstructure_data = None
            if hasattr(self, 'biomat_microstructure') and level == "biomaterial":
                microstructure_data = self.biomat_microstructure.get_microstructure_data()

            # Generate publication-quality JSON
            json_data = generate_comprehensive_json(
                self.current_component,
                level,
                microstructure_data=microstructure_data,
                predictor_settings=self.predictor_settings
            )

            # Write with proper formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            QMessageBox.information(
                self, "Exported",
                f"Component exported to:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export: {e}")

    def _save_component(self):
        """Save the current component to file."""
        if not self.current_component:
            return

        try:
            path = self.factory.save_component(self.current_component)
            self.hierarchy_browser.refresh_tree()
            QMessageBox.information(self, "Saved",
                f"Component saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save: {e}")

    def _build_component(self):
        """Build and emit the current component."""
        if not self.current_component:
            return

        self.component_created.emit(self.current_component)
        QMessageBox.information(self, "Built",
            f"Component '{self.current_component.name}' built successfully!")

    # === Settings Management ===

    def _load_default_settings(self):
        """Load default predictor settings."""
        self.predictor_settings = {
            'cell': {
                'B0': 3.5e-12,
                'ALPHA': 0.75,
                'reference_temperature_C': 37,
                'temperature_correction': True,
                'cell_density': 1.05,
            },
            'biomaterial': {
                'porosity_model': 'Gibson-Ashby (n=2.0)',
                'custom_exponent': 2.0,
                'composite_model': 'Voigt-Reuss Average',
            },
            'nucleic_acid': {
                'Na_concentration_M': 0.050,
                'Mg_concentration_M': 0.0,
                'oligo_concentration_M': 0.25e-6,
                'tm_method': 'Nearest-Neighbor (SantaLucia 1998)',
            },
            'protein': {
                'ss_window_size': 6,
                'helix_threshold': 1.03,
                'min_cys_distance': 10,
                'pI_precision': 2,
            }
        }

        # Initialize biomaterial microstructure with default cells
        if hasattr(self, 'biomat_microstructure'):
            self.biomat_microstructure.generate_cells(
                num_cells=50,
                cell_types={'fibroblast': 0.7, 'chondrocyte': 0.2, 'adipocyte': 0.1},
                seed=42,
                distribution='poisson'
            )

    def _open_settings(self):
        """Open the predictor settings dialog."""
        dialog = PredictorSettingsDialog(self)
        dialog.set_settings(self.predictor_settings)
        dialog.settings_changed.connect(self._apply_predictor_settings)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.predictor_settings = dialog.get_settings()
            self._apply_predictor_settings(self.predictor_settings)

    def _apply_predictor_settings(self, settings: Dict):
        """Apply new predictor settings."""
        self.predictor_settings = settings

        # Apply to cell predictor
        try:
            from periodica.utils.predictors.biological.cell_predictor import CellPredictor
            cell_settings = settings.get('cell', {})
            predictor = CellPredictor()
            if 'B0' in cell_settings:
                predictor.set_B0(cell_settings['B0'])
            if 'ALPHA' in cell_settings:
                predictor.set_alpha(cell_settings['ALPHA'])
            if 'reference_temperature_C' in cell_settings:
                predictor.set_temperature(cell_settings['reference_temperature_C'])
        except Exception as e:
            print(f"Could not apply cell settings: {e}")

        # Apply to nucleic acid predictor
        try:
            from periodica.utils.predictors.biological.nucleic_acid_predictor import NucleicAcidPredictor
            na_settings = settings.get('nucleic_acid', {})
            predictor = NucleicAcidPredictor()
            if 'Na_concentration_M' in na_settings and 'oligo_concentration_M' in na_settings:
                predictor.set_default_concentrations(
                    na_settings['Na_concentration_M'],
                    na_settings['oligo_concentration_M']
                )
        except Exception as e:
            print(f"Could not apply nucleic acid settings: {e}")

        # Refresh current preview
        self._on_tab_changed(self.level_tabs.currentIndex())

    def get_current_settings(self) -> Dict:
        """Get current predictor settings."""
        return self.predictor_settings.copy()


def open_biological_system_builder(parent=None) -> Optional[BiologicalComponent]:
    """Open the biological system builder dialog."""
    dialog = BiologicalSystemBuilderDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.current_component
    return None
