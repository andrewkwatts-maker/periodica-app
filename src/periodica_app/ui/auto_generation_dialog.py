"""
Auto-Generation Dialog
=======================
Generic reusable dialog for auto-generating data items
(molecules, alloys, proteins, etc.) with progress tracking.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QProgressBar, QPushButton, QSpinBox, QTextEdit, QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from periodica.utils.logger import get_logger

logger = get_logger('auto_generation_dialog')


class AutoGenerationWorker(QThread):
    """Background worker for auto-generation."""

    progress = Signal(int, str)
    finished = Signal(bool, str, list)  # success, message, results

    def __init__(self, generator_func, count_limit=50, parent=None):
        super().__init__(parent)
        self.generator_func = generator_func
        self.count_limit = count_limit
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            def on_progress(pct, msg):
                if self._cancelled:
                    raise InterruptedError("Generation cancelled")
                self.progress.emit(pct, msg)

            results = self.generator_func(
                count_limit=self.count_limit,
                progress_callback=on_progress,
            )
            self.finished.emit(True, f"Generated {len(results)} items", results)

        except InterruptedError:
            self.finished.emit(False, "Generation cancelled", [])
        except Exception as e:
            logger.error("Auto-generation failed: %s", e)
            self.finished.emit(False, f"Error: {e}", [])


class AutoGenerationDialog(QDialog):
    """
    Generic dialog for auto-generating data items.

    Supports molecules, alloys, proteins, and other asset types.
    """

    items_generated = Signal(list)  # emitted with list of generated dicts

    CATEGORY_DESCRIPTIONS = {
        "molecules": "Generate molecules from available elements using\n"
                     "bonding rules, valence constraints, and VSEPR geometry.",
        "alloys": "Generate alloy compositions from metallic elements\n"
                  "using rule of mixtures and phase diagram rules.",
        "materials": "Generate engineering materials from alloy compositions\n"
                     "with microstructure and mechanical property prediction.",
        "proteins": "Generate protein structures from amino acid sequences\n"
                    "with secondary structure and property prediction.",
        "amino_acids": "Generate the 20 standard amino acids with\n"
                       "properties derived from atomic composition.",
        "nucleic_acids": "Generate nucleic acid sequences with\n"
                         "GC content and melting temperature prediction.",
        "cells": "Generate cell types from available cell components\n"
                 "with volume and metabolic rate prediction.",
        "cell_components": "Generate cell components from proteins and\n"
                           "nucleic acids using biological assembly rules.",
        "biomaterials": "Generate biological materials from cell and\n"
                        "extracellular matrix composition data.",
    }

    def __init__(self, category: str, generator_func, parent=None):
        super().__init__(parent)
        self.category = category
        self.generator_func = generator_func
        self.worker = None
        self._results = []

        self.setWindowTitle(f"Auto-Generate {category.replace('_', ' ').title()}")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        info_group = QGroupBox("Generation Settings")
        info_layout = QVBoxLayout(info_group)

        desc = self.CATEGORY_DESCRIPTIONS.get(self.category, f"Auto-generate {self.category}.")
        info_layout.addWidget(QLabel(desc))

        # Count control
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Maximum items to generate:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(5, 500)
        self.count_spin.setValue(50)
        count_layout.addWidget(self.count_spin)
        count_layout.addStretch()
        info_layout.addLayout(count_layout)

        layout.addWidget(info_group)

        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready.")
        progress_layout.addWidget(self.status_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        progress_layout.addWidget(self.log_text)

        layout.addWidget(progress_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self._on_generate)
        btn_layout.addWidget(self.generate_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save All")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setVisible(False)
        btn_layout.addWidget(self.save_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _on_generate(self):
        self.generate_btn.setEnabled(False)
        self.log_text.clear()
        self.log_text.append(f"Starting {self.category} generation...")

        self.worker = AutoGenerationWorker(
            self.generator_func,
            count_limit=self.count_spin.value(),
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("Cancelling...")
        else:
            self.reject()

    def _on_progress(self, pct, msg):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)
        self.log_text.append(msg)

    def _on_finished(self, success, msg, results):
        self.progress_bar.setValue(100 if success else self.progress_bar.value())
        self.status_label.setText(msg)
        self.log_text.append(f"\n{'SUCCESS' if success else 'FAILED'}: {msg}")

        self._results = results

        self.generate_btn.setVisible(False)
        self.cancel_btn.setVisible(False)

        if success and results:
            self.save_btn.setVisible(True)
            self.close_btn.setVisible(True)
        else:
            self.close_btn.setVisible(True)

    def _on_save(self):
        if self._results:
            self.items_generated.emit(self._results)
            self.status_label.setText(f"Emitted {len(self._results)} items for saving.")
            self.save_btn.setVisible(False)
