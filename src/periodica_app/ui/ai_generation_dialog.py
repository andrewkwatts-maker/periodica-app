"""
AI Generation Dialog for creating assets using Gemini AI.
Provides an interface for users to describe what they want to generate
and handles the recursive refinement process.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTextEdit, QComboBox, QProgressBar,
    QMessageBox, QFrame, QScrollArea, QWidget, QSplitter
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont

# Add scripts directory to path for importing generator
scripts_dir = Path(__file__).parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))


class GenerationWorker(QObject):
    """Worker thread for running Gemini generation."""

    progress = Signal(str, int)  # message, percentage
    finished = Signal(dict)  # result config
    error = Signal(str)  # error message

    def __init__(self, asset_type: str, intent: str, components: List[str],
                 target_properties: Dict[str, Any]):
        super().__init__()
        self.asset_type = asset_type
        self.intent = intent
        self.components = components
        self.target_properties = target_properties
        self._cancelled = False

    def cancel(self):
        """Cancel the generation."""
        self._cancelled = True

    def run(self):
        """Run the generation process."""
        try:
            from gemini_asset_generator import GeminiAssetGenerator

            self.progress.emit("Initializing Gemini...", 5)

            generator = GeminiAssetGenerator(self.asset_type, verbose=False)

            self.progress.emit("Planning configuration...", 10)

            # Run generation with progress callbacks
            def progress_callback(step: int, message: str):
                if self._cancelled:
                    raise InterruptedError("Generation cancelled")
                # Map steps to percentages (8 total steps)
                percentage = 10 + int((step / 8) * 85)
                self.progress.emit(message, percentage)

            result = generator.generate(
                user_intent=self.intent,
                components=self.components,
                target_properties=self.target_properties
            )

            if self._cancelled:
                return

            self.progress.emit("Generation complete!", 100)

            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Generation returned no result")

        except InterruptedError:
            self.error.emit("Generation cancelled")
        except ImportError as e:
            self.error.emit(f"Missing dependency: {e}\n\nInstall with: pip install google-generativeai")
        except Exception as e:
            self.error.emit(f"Generation failed: {str(e)}")


class AIGenerationDialog(QDialog):
    """Dialog for AI-powered asset generation."""

    # Emitted when a new asset is generated
    asset_generated = Signal(dict)

    # Asset type configurations
    ASSET_CONFIGS = {
        "alloy": {
            "title": "AI Alloy Generator",
            "description": "Generate alloy configurations using Gemini AI with recursive refinement.",
            "component_label": "Elements",
            "component_placeholder": "Fe, C, Mn, Cr (comma-separated element symbols)",
            "intent_placeholder": "Describe your alloy, e.g., 'high strength stainless steel for marine applications'",
            "properties_placeholder": '{"tensile_strength": 800, "corrosion_resistance": 0.9}',
            "examples": [
                ("High Strength Steel", "Fe, C, Mn, Cr, Mo", "High strength low alloy steel for structural applications"),
                ("Stainless Steel", "Fe, Cr, Ni, Mo", "Corrosion resistant stainless steel"),
                ("Aluminum Alloy", "Al, Cu, Mg, Si", "Lightweight aerospace aluminum alloy"),
            ]
        },
        "protein": {
            "title": "AI Protein Generator",
            "description": "Generate protein/peptide configurations using Gemini AI.",
            "component_label": "Amino Acids",
            "component_placeholder": "A, V, I, L, K (comma-separated 1-letter codes)",
            "intent_placeholder": "Describe your protein, e.g., 'hydrophobic membrane-spanning peptide'",
            "properties_placeholder": '{"hydropathy": 2.0, "molecular_weight": 5000}',
            "examples": [
                ("Hydrophobic Peptide", "A, V, I, L, F, M", "Hydrophobic peptide for membrane insertion"),
                ("Basic Peptide", "K, R, H, A, L", "Positively charged cell-penetrating peptide"),
                ("Structural Protein", "G, A, V, L, P", "Flexible structural protein"),
            ]
        },
        "nucleic_acid": {
            "title": "AI Nucleic Acid Generator",
            "description": "Generate DNA/RNA sequence configurations using Gemini AI.",
            "component_label": "Nucleotides",
            "component_placeholder": "A, T, G, C (comma-separated bases)",
            "intent_placeholder": "Describe your sequence, e.g., 'high GC content PCR primer with Tm ~65C'",
            "properties_placeholder": '{"gc_content": 0.6, "melting_temperature": 65}',
            "examples": [
                ("High GC Primer", "G, C, A, T", "PCR primer with high melting temperature"),
                ("AT-Rich Promoter", "A, T, G, C", "AT-rich promoter region sequence"),
                ("GC Clamp", "G, C, A, T", "Primer with 3' GC clamp for specificity"),
            ]
        },
        "molecule": {
            "title": "AI Molecule Generator",
            "description": "Generate molecular configurations using Gemini AI with VSEPR geometry.",
            "component_label": "Atoms",
            "component_placeholder": "C, H, O, N (comma-separated element symbols)",
            "intent_placeholder": "Describe your molecule, e.g., 'polar organic solvent molecule'",
            "properties_placeholder": '{"polarity": "polar", "geometry": "tetrahedral"}',
            "examples": [
                ("Water", "H, O", "Simple polar molecule"),
                ("Methane", "C, H", "Tetrahedral nonpolar molecule"),
                ("Ammonia", "N, H", "Polar molecule with lone pair"),
            ]
        },
        "cell": {
            "title": "AI Cell Generator",
            "description": "Generate cell configurations using Gemini AI with Kleiber's Law scaling.",
            "component_label": "Organelles",
            "component_placeholder": "Nucleus, Mitochondrion, Ribosome (comma-separated)",
            "intent_placeholder": "Describe your cell, e.g., 'high metabolism liver cell'",
            "properties_placeholder": '{"volume": 5000, "metabolic_rate": 2.0}',
            "examples": [
                ("Hepatocyte", "Nucleus, Mitochondrion, ER, Golgi", "Metabolically active liver cell"),
                ("Neuron", "Nucleus, Mitochondrion, Ribosome", "Electrically active nerve cell"),
                ("Muscle Cell", "Nucleus, Mitochondrion, Ribosome", "High energy muscle fiber"),
            ]
        },
        "biomaterial": {
            "title": "AI Biomaterial Generator",
            "description": "Generate biomaterial configurations using Gemini AI.",
            "component_label": "Components",
            "component_placeholder": "Collagen, Elastin, Cells (comma-separated)",
            "intent_placeholder": "Describe your biomaterial, e.g., 'soft tissue scaffold for cartilage repair'",
            "properties_placeholder": '{"stiffness": "soft", "porosity": 0.8}',
            "examples": [
                ("Cartilage Scaffold", "Collagen, Chondrocytes, Proteoglycans", "Tissue engineering scaffold"),
                ("Bone Substitute", "Hydroxyapatite, Collagen, Osteoblasts", "Bone repair material"),
                ("Skin Graft", "Keratinocytes, Fibroblasts, Collagen", "Wound healing material"),
            ]
        },
        "material": {
            "title": "AI Material Generator",
            "description": "Generate engineering material configurations using Gemini AI.",
            "component_label": "Material Type",
            "component_placeholder": "Steel, Polymer, Ceramic, Composite (category or specific type)",
            "intent_placeholder": "Describe your material, e.g., 'lightweight structural material with high fatigue resistance'",
            "properties_placeholder": '{"tensile_strength": 500, "density": 2.7, "youngs_modulus": 70}',
            "examples": [
                ("Aerospace Aluminum", "Aluminum, 7075-T6", "High strength aluminum for aircraft structures"),
                ("Carbon Fiber Composite", "Composite, Carbon, Epoxy", "Lightweight high-stiffness composite"),
                ("Tool Steel", "Steel, Tool, High-Speed", "Wear-resistant steel for cutting tools"),
            ]
        },
        "subatomic": {
            "title": "AI Subatomic Particle Generator",
            "description": "Generate subatomic particle configurations using Gemini AI with quantum properties.",
            "component_label": "Particle Components",
            "component_placeholder": "Proton, Neutron, Electron, Quark (comma-separated)",
            "intent_placeholder": "Describe your particle, e.g., 'hadron with specific baryon number'",
            "properties_placeholder": '{"mass_MeV": 938, "charge": 1, "spin": 0.5}',
            "examples": [
                ("Proton", "Up Quark, Up Quark, Down Quark", "Stable baryon with +1 charge"),
                ("Neutron", "Up Quark, Down Quark, Down Quark", "Neutral baryon"),
                ("Pion", "Quark, Antiquark", "Lightest meson"),
            ]
        },
        "quark": {
            "title": "AI Quark/Particle Generator",
            "description": "Generate fundamental particle configurations using Gemini AI with Standard Model properties.",
            "component_label": "Particle Type",
            "component_placeholder": "Quark, Lepton, Boson, Fermion (particle category)",
            "intent_placeholder": "Describe your particle, e.g., 'heavy quark with specific color charge'",
            "properties_placeholder": '{"mass_MeV": 4180, "charge": -0.333, "generation": 3}',
            "examples": [
                ("Bottom Quark", "Quark, Third Generation", "Heavy third-generation quark"),
                ("Tau Lepton", "Lepton, Third Generation", "Heaviest charged lepton"),
                ("W Boson", "Boson, Weak Force", "Massive weak force carrier"),
            ]
        },
        "amino_acid": {
            "title": "AI Amino Acid Generator",
            "description": "Generate amino acid configurations using Gemini AI with biochemical properties.",
            "component_label": "Side Chain Elements",
            "component_placeholder": "C, H, O, N, S (comma-separated elements)",
            "intent_placeholder": "Describe your amino acid, e.g., 'hydrophobic aromatic amino acid'",
            "properties_placeholder": '{"hydropathy": 2.8, "molecular_weight": 165, "pI": 5.5}',
            "examples": [
                ("Aromatic Hydrophobic", "C, H, Benzene Ring", "Aromatic hydrophobic residue like Phe/Tyr"),
                ("Polar Charged", "C, H, O, N, Amino", "Basic charged residue like Lys/Arg"),
                ("Small Nonpolar", "C, H", "Small aliphatic residue like Ala/Val"),
            ]
        },
        "cell_component": {
            "title": "AI Cell Component Generator",
            "description": "Generate organelle configurations using Gemini AI with cellular properties.",
            "component_label": "Proteins/Molecules",
            "component_placeholder": "Membrane, Ribosome, DNA, ATP (comma-separated components)",
            "intent_placeholder": "Describe your organelle, e.g., 'energy-producing organelle with high ATP output'",
            "properties_placeholder": '{"diameter_nm": 500, "membrane_layers": 2, "function": "energy"}',
            "examples": [
                ("Mitochondrion", "Membrane, Cristae, ATP Synthase, mtDNA", "Powerhouse of the cell"),
                ("Ribosome", "rRNA, Proteins, Large Subunit, Small Subunit", "Protein synthesis machinery"),
                ("Nucleus", "Nuclear Envelope, DNA, Nuclear Pores, Nucleolus", "Genetic information center"),
            ]
        },
        "element": {
            "title": "AI Element Generator",
            "description": "Generate element configurations using Gemini AI with atomic properties.",
            "component_label": "Subatomic Particles",
            "component_placeholder": "Protons, Neutrons, Electrons (specify counts or let AI determine)",
            "intent_placeholder": "Describe your element, e.g., 'noble gas with specific electron configuration'",
            "properties_placeholder": '{"atomic_number": 118, "atomic_mass": 294, "electronegativity": 2.2}',
            "examples": [
                ("Alkali Metal", "1 valence electron", "Highly reactive alkali metal element"),
                ("Noble Gas", "Full outer shell", "Inert noble gas element"),
                ("Transition Metal", "d-block element", "Transition metal with catalytic properties"),
            ]
        }
    }

    def __init__(self, asset_type: str, parent=None):
        super().__init__(parent)
        self.asset_type = asset_type
        self.config = self.ASSET_CONFIGS.get(asset_type, self.ASSET_CONFIGS["alloy"])
        self.worker = None
        self.thread = None
        self.generated_config = None

        self.setWindowTitle(self.config["title"])
        self.setMinimumSize(800, 600)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(20, 20, 35);
            }
            QLabel {
                color: white;
            }
            QLineEdit, QTextEdit {
                background-color: rgb(45, 45, 65);
                color: white;
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #667eea;
            }
            QGroupBox {
                color: white;
                border: 2px solid #667eea;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QComboBox {
                background-color: rgb(45, 45, 65);
                color: white;
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 4px;
                padding: 6px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: rgb(30, 30, 50);
                color: white;
                selection-background-color: #667eea;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel(self.config["title"])
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)

        # Description
        desc = QLabel(self.config["description"])
        desc.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Input
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # Quick examples
        examples_group = QGroupBox("Quick Examples")
        examples_group.setStyleSheet("""
            QGroupBox {
                border-color: #607D8B;
            }
        """)
        examples_layout = QVBoxLayout()

        self.example_combo = QComboBox()
        self.example_combo.addItem("-- Select an example --")
        for name, components, intent in self.config["examples"]:
            self.example_combo.addItem(name)
        self.example_combo.currentIndexChanged.connect(self.on_example_selected)
        examples_layout.addWidget(self.example_combo)

        examples_group.setLayout(examples_layout)
        left_layout.addWidget(examples_group)

        # Input group
        input_group = QGroupBox("Configuration Input")
        input_layout = QVBoxLayout()

        # Components input
        comp_label = QLabel(f"{self.config['component_label']}:")
        comp_label.setStyleSheet("font-weight: bold;")
        input_layout.addWidget(comp_label)

        self.components_input = QLineEdit()
        self.components_input.setPlaceholderText(self.config["component_placeholder"])
        input_layout.addWidget(self.components_input)

        # Intent input
        intent_label = QLabel("Description / Intent:")
        intent_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        input_layout.addWidget(intent_label)

        self.intent_input = QTextEdit()
        self.intent_input.setPlaceholderText(self.config["intent_placeholder"])
        self.intent_input.setMaximumHeight(80)
        input_layout.addWidget(self.intent_input)

        # Target properties (optional)
        props_label = QLabel("Target Properties (optional JSON):")
        props_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        input_layout.addWidget(props_label)

        self.properties_input = QLineEdit()
        self.properties_input.setPlaceholderText(self.config["properties_placeholder"])
        input_layout.addWidget(self.properties_input)

        input_group.setLayout(input_layout)
        left_layout.addWidget(input_group)
        left_layout.addStretch()

        splitter.addWidget(left_panel)

        # Right panel - Preview/Output
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)

        # Output preview
        output_group = QGroupBox("Generated Configuration")
        output_layout = QVBoxLayout()

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
            }
        """)
        self.output_text.setPlaceholderText("Generated configuration will appear here...")
        output_layout.addWidget(self.output_text)

        output_group.setLayout(output_layout)
        right_layout.addWidget(output_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])

        layout.addWidget(splitter)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 4px;
                background: rgb(45, 45, 65);
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #667eea, stop:1 #764ba2);
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.generate_btn = QPushButton("Generate with AI")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #7b8fed, stop:1 #8b5cb5);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """)
        self.generate_btn.clicked.connect(self.start_generation)
        button_row.addWidget(self.generate_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100, 100, 120, 150);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(120, 120, 140, 180);
            }
        """)
        self.cancel_btn.clicked.connect(self.on_cancel)
        button_row.addWidget(self.cancel_btn)

        self.use_btn = QPushButton("Use Configuration")
        self.use_btn.setStyleSheet("""
            QPushButton {
                background: rgba(76, 175, 80, 180);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(76, 175, 80, 220);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """)
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self.use_configuration)
        button_row.addWidget(self.use_btn)

        layout.addLayout(button_row)

    def on_example_selected(self, index: int):
        """Handle example selection."""
        if index == 0:
            return

        name, components, intent = self.config["examples"][index - 1]
        self.components_input.setText(components)
        self.intent_input.setPlainText(intent)
        self.properties_input.clear()

    def start_generation(self):
        """Start the AI generation process."""
        # Validate inputs
        components = [c.strip() for c in self.components_input.text().split(",") if c.strip()]
        intent = self.intent_input.toPlainText().strip()

        if not components:
            QMessageBox.warning(self, "Missing Input", f"Please enter at least one {self.config['component_label'].lower()}.")
            return

        if not intent:
            QMessageBox.warning(self, "Missing Input", "Please describe what you want to generate.")
            return

        # Parse target properties
        target_properties = {}
        props_text = self.properties_input.text().strip()
        if props_text:
            try:
                target_properties = json.loads(props_text)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Invalid JSON", "Target properties must be valid JSON.")
                return

        # Disable UI during generation
        self.generate_btn.setEnabled(False)
        self.components_input.setEnabled(False)
        self.intent_input.setEnabled(False)
        self.properties_input.setEnabled(False)
        self.example_combo.setEnabled(False)

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting generation...")

        # Create worker and thread
        self.thread = QThread()
        self.worker = GenerationWorker(
            self.asset_type, intent, components, target_properties
        )
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)

        # Start
        self.thread.start()

    def on_progress(self, message: str, percentage: int):
        """Handle progress update."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)

    def on_finished(self, result: dict):
        """Handle generation completion."""
        self.generated_config = result
        self.output_text.setPlainText(json.dumps(result, indent=2))
        self.status_label.setText("Generation complete! Review the configuration and click 'Use Configuration' to apply.")
        self.use_btn.setEnabled(True)
        self.reset_ui_state()

    def on_error(self, error_message: str):
        """Handle generation error."""
        self.status_label.setText(f"Error: {error_message}")
        self.output_text.setPlainText(f"Generation failed:\n\n{error_message}")
        self.reset_ui_state()
        QMessageBox.critical(self, "Generation Failed", error_message)

    def reset_ui_state(self):
        """Reset UI to editable state."""
        self.generate_btn.setEnabled(True)
        self.components_input.setEnabled(True)
        self.intent_input.setEnabled(True)
        self.properties_input.setEnabled(True)
        self.example_combo.setEnabled(True)
        self.progress_bar.setVisible(False)

    def on_cancel(self):
        """Handle cancel button."""
        if self.worker:
            self.worker.cancel()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        self.reject()

    def use_configuration(self):
        """Use the generated configuration."""
        if self.generated_config:
            self.asset_generated.emit(self.generated_config)
            self.accept()

    def closeEvent(self, event):
        """Handle dialog close."""
        self.on_cancel()
        event.accept()
