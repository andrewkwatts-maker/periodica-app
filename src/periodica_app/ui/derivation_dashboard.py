"""
Derivation Dashboard
=====================
Provides an overview of the derivation chain status, showing per-category
statistics, chain integrity, and quick-action buttons.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QGridLayout, QProgressBar, QTextEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from periodica.utils.cascade_engine import CascadeRegenerationEngine, DERIVATION_ORDER
from periodica.utils.logger import get_logger

logger = get_logger('derivation_dashboard')


class DerivationDashboard(QWidget):
    """Dashboard showing derivation chain status and controls."""

    regenerate_all_requested = Signal()
    regenerate_category_requested = Signal(str)
    clear_derived_requested = Signal()
    gut_parameters_requested = Signal()
    validation_report_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = CascadeRegenerationEngine()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("Derivation Chain Dashboard")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        # Chain integrity
        integrity_group = QGroupBox("Chain Integrity")
        integrity_layout = QGridLayout(integrity_group)
        self._integrity_labels = {}

        for i, category in enumerate(DERIVATION_ORDER):
            row, col = divmod(i, 4)
            label = QLabel(f"{category}: --")
            label.setStyleSheet("color: gray;")
            self._integrity_labels[category] = label
            integrity_layout.addWidget(label, row, col)

        layout.addWidget(integrity_group)

        # Statistics
        stats_group = QGroupBox("Category Statistics")
        self._stats_layout = QGridLayout(stats_group)

        headers = ['Category', 'Total', 'Derived', 'Manual', 'Confidence']
        for col, header in enumerate(headers):
            lbl = QLabel(header)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self._stats_layout.addWidget(lbl, 0, col)

        self._stats_rows = {}
        for i, category in enumerate(DERIVATION_ORDER):
            row = i + 1
            labels = []
            for col in range(5):
                lbl = QLabel("--")
                self._stats_layout.addWidget(lbl, row, col)
                labels.append(lbl)
            labels[0].setText(category)
            self._stats_rows[category] = labels

        layout.addWidget(stats_group)

        # Quick actions
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)

        regen_btn = QPushButton("Regenerate All")
        regen_btn.clicked.connect(self.regenerate_all_requested.emit)
        actions_layout.addWidget(regen_btn)

        gut_btn = QPushButton("GUT Parameters")
        gut_btn.clicked.connect(self.gut_parameters_requested.emit)
        actions_layout.addWidget(gut_btn)

        validate_btn = QPushButton("Validation Report")
        validate_btn.clicked.connect(self.validation_report_requested.emit)
        actions_layout.addWidget(validate_btn)

        clear_btn = QPushButton("Clear Derived")
        clear_btn.clicked.connect(self.clear_derived_requested.emit)
        actions_layout.addWidget(clear_btn)

        layout.addWidget(actions_group)
        layout.addStretch()

    def refresh(self):
        """Refresh all dashboard data."""
        self._refresh_integrity()
        self._refresh_stats()

    def _refresh_integrity(self):
        """Update chain integrity indicators."""
        try:
            integrity = self._engine.check_chain_integrity()
            for category, has_data in integrity.items():
                label = self._integrity_labels.get(category)
                if label:
                    if has_data:
                        label.setText(f"{category}: OK")
                        label.setStyleSheet("color: #48bb78;")
                    else:
                        label.setText(f"{category}: EMPTY")
                        label.setStyleSheet("color: #fc8181;")
        except Exception as e:
            logger.error(f"Failed to check integrity: {e}")

    def _refresh_stats(self):
        """Update category statistics."""
        try:
            stats = self._engine.get_category_stats()
            for category, data in stats.items():
                labels = self._stats_rows.get(category)
                if labels:
                    labels[1].setText(str(data['total']))
                    labels[2].setText(str(data['derived']))
                    labels[3].setText(str(data['manual']))
                    conf = data['avg_confidence']
                    labels[4].setText(f"{conf:.1%}" if conf > 0 else "--")

                    # Color confidence
                    if conf >= 0.8:
                        labels[4].setStyleSheet("color: #48bb78;")
                    elif conf >= 0.5:
                        labels[4].setStyleSheet("color: #ecc94b;")
                    elif conf > 0:
                        labels[4].setStyleSheet("color: #fc8181;")
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
