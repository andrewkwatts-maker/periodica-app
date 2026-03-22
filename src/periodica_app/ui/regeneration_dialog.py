"""
Regeneration Dialog
====================
UI dialog for regenerating data from first principles.
Shows progress and allows cancellation.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QGroupBox, QTextEdit,
)
from PySide6.QtCore import Qt

from periodica_app.utils.regeneration_worker import RegenerationWorker
from periodica.utils.logger import get_logger

logger = get_logger('regeneration_dialog')


class RegenerationDialog(QDialog):
    """
    Dialog for regenerating data categories from quark constants.

    Shows a progress bar and status text during regeneration.
    """

    def __init__(self, category: str = "elements", parent=None):
        super().__init__(parent)
        self.category = category
        self.worker = None

        self.setWindowTitle(f"Regenerate {category.title()} from Quarks")
        self.setMinimumSize(500, 350)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info section
        info_group = QGroupBox("Regeneration Info")
        info_layout = QVBoxLayout(info_group)

        self.info_label = QLabel(
            f"This will regenerate all {self.category} from quark constants\n"
            f"using the full derivation chain:\n\n"
            f"  Quarks → Hadrons → Nuclei → Atoms\n\n"
            f"Existing data in data/active/{self.category}/ will be overwritten."
        )
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        layout.addWidget(info_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to regenerate.")
        progress_layout.addWidget(self.status_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        progress_layout.addWidget(self.log_text)

        layout.addWidget(progress_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.regenerate_btn = QPushButton("Regenerate")
        self.regenerate_btn.clicked.connect(self._on_regenerate)
        button_layout.addWidget(self.regenerate_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _on_regenerate(self):
        """Start regeneration."""
        self.regenerate_btn.setEnabled(False)
        self.log_text.clear()
        self.log_text.append(f"Starting regeneration of {self.category}...")

        self.worker = RegenerationWorker(self.category)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_cancel(self):
        """Cancel regeneration or close dialog."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("Cancelling...")
        else:
            self.reject()

    def _on_progress(self, pct: int, msg: str):
        """Update progress display."""
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)
        self.log_text.append(msg)

    def _on_finished(self, success: bool, msg: str):
        """Handle regeneration completion."""
        self.progress_bar.setValue(100 if success else self.progress_bar.value())
        self.status_label.setText(msg)
        self.log_text.append(f"\n{'SUCCESS' if success else 'FAILED'}: {msg}")

        self.regenerate_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)
