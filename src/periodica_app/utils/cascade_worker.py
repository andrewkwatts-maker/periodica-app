"""
Cascade Regeneration Worker
============================
QThread worker for running cascade regeneration in the background.
"""

from PySide6.QtCore import QThread, Signal

from periodica.utils.cascade_engine import CascadeRegenerationEngine
from periodica.utils.logger import get_logger

logger = get_logger('cascade_worker')


class CascadeRegenerationWorker(QThread):
    """Background worker for cascade regeneration."""

    progress = Signal(int, str)  # percent, message
    stage_progress = Signal(str, int)  # category, percent
    finished = Signal(bool, str, dict)  # success, message, results

    def __init__(
        self,
        categories=None,
        preserve_manual=True,
        start_from=None,
        parent=None,
    ):
        super().__init__(parent)
        self.categories = categories
        self.preserve_manual = preserve_manual
        self.start_from = start_from
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            engine = CascadeRegenerationEngine()

            def on_progress(pct, msg):
                if self._cancelled:
                    raise InterruptedError("Cascade cancelled")
                self.progress.emit(pct, msg)

            if self.start_from:
                results = engine.regenerate_from(
                    self.start_from,
                    preserve_manual=self.preserve_manual,
                    progress_callback=on_progress,
                )
            else:
                results = engine.regenerate_all(
                    categories=self.categories,
                    preserve_manual=self.preserve_manual,
                    progress_callback=on_progress,
                )

            total = sum(results.values())
            self.finished.emit(
                True,
                f"Cascade complete: {total} items regenerated",
                results,
            )

        except InterruptedError:
            self.finished.emit(False, "Cascade cancelled", {})
        except Exception as e:
            logger.error(f"Cascade failed: {e}")
            self.finished.emit(False, f"Error: {e}", {})
