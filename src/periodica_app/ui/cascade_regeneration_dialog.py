"""
Cascade Regeneration Dialog
============================
UI dialog for running cascade regeneration from quarks through to biomaterials.
Shows per-category checkboxes, progress bars, and status indicators.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QProgressBar, QPushButton, QCheckBox, QTextEdit, QGridLayout,
)
from PySide6.QtCore import Qt, Signal

from periodica.utils.cascade_engine import DERIVATION_ORDER
from periodica_app.utils.cascade_worker import CascadeRegenerationWorker
from periodica.utils.logger import get_logger

logger = get_logger('cascade_dialog')

_CATEGORY_LABELS = {
    'quarks': 'Quarks (source)',
    'subatomic': 'Subatomic Particles',
    'elements': 'Elements (118)',
    'molecules': 'Molecules',
    'alloys': 'Alloys',
    'materials': 'Materials',
    'amino_acids': 'Amino Acids',
    'proteins': 'Proteins',
    'nucleic_acids': 'Nucleic Acids',
    'cell_components': 'Cell Components',
    'cells': 'Cells',
    'biomaterials': 'Biomaterials',
}


class CascadeRegenerationDialog(QDialog):
    """Dialog for cascade regeneration from quarks."""

    regeneration_complete = Signal(dict)  # {category: count}

    def __init__(self, parent=None, start_from=None):
        super().__init__(parent)
        self.worker = None
        self._start_from = start_from
        self._results = {}

        self.setWindowTitle("Regenerate All from Quarks")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Description
        desc = QLabel(
            "Regenerate all derived data from quark constants.\n"
            "Each category is regenerated in dependency order.\n"
            "Quarks and subatomic particles are source data (not regenerated)."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Category checkboxes
        cat_group = QGroupBox("Categories to Regenerate")
        cat_layout = QGridLayout(cat_group)
        self._checkboxes = {}

        for i, category in enumerate(DERIVATION_ORDER):
            cb = QCheckBox(_CATEGORY_LABELS.get(category, category))
            # Quarks and subatomic are source data
            if category in ('quarks', 'subatomic'):
                cb.setChecked(False)
                cb.setEnabled(False)
                cb.setToolTip("Source data - not regenerated")
            else:
                cb.setChecked(True)
                if self._start_from and DERIVATION_ORDER.index(category) < DERIVATION_ORDER.index(self._start_from):
                    cb.setChecked(False)

            self._checkboxes[category] = cb
            row, col = divmod(i, 3)
            cat_layout.addWidget(cb, row, col)

        layout.addWidget(cat_group)

        # Preserve manual edits checkbox
        self.preserve_manual_cb = QCheckBox("Preserve manual edits")
        self.preserve_manual_cb.setChecked(True)
        self.preserve_manual_cb.setToolTip(
            "When checked, items with source='manual' will not be overwritten"
        )
        layout.addWidget(self.preserve_manual_cb)

        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to regenerate.")
        progress_layout.addWidget(self.status_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        progress_layout.addWidget(self.log_text)

        layout.addWidget(progress_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.regenerate_btn = QPushButton("Regenerate")
        self.regenerate_btn.clicked.connect(self._on_regenerate)
        btn_layout.addWidget(self.regenerate_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _on_regenerate(self):
        self.regenerate_btn.setEnabled(False)
        self.log_text.clear()

        # Gather selected categories
        selected = [
            cat for cat in DERIVATION_ORDER
            if self._checkboxes[cat].isChecked()
        ]

        if not selected:
            self.status_label.setText("No categories selected.")
            self.regenerate_btn.setEnabled(True)
            return

        self.log_text.append(f"Starting cascade regeneration for {len(selected)} categories...")

        self.worker = CascadeRegenerationWorker(
            categories=selected,
            preserve_manual=self.preserve_manual_cb.isChecked(),
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
        self._results = results

        if success and results:
            self.log_text.append("\n--- Results ---")
            for cat, count in results.items():
                self.log_text.append(f"  {cat}: {count} items")
            total = sum(results.values())
            self.log_text.append(f"\nTotal: {total} items regenerated")

        self.log_text.append(f"\n{'SUCCESS' if success else 'FAILED'}: {msg}")

        self.regenerate_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)

        if success:
            self.regeneration_complete.emit(results)
