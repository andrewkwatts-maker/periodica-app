"""
Regeneration Worker
====================
QThread-based worker for running regeneration in the background
with progress reporting. Prevents UI freezing during regeneration.
"""

from PySide6.QtCore import QThread, Signal

from periodica.utils.regeneration_engine import RegenerationEngine
from periodica.utils.logger import get_logger

logger = get_logger('regeneration_worker')


class RegenerationWorker(QThread):
    """
    Background worker for data regeneration.

    Signals:
        progress(int, str): Emitted with (percentage, status_message)
        finished(bool, str): Emitted when done with (success, result_message)
    """

    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, category: str = "elements", parent=None):
        super().__init__(parent)
        self.category = category
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the regeneration."""
        self._cancelled = True

    def run(self):
        """Execute regeneration in background thread."""
        try:
            engine = RegenerationEngine()

            def on_progress(pct, msg):
                if self._cancelled:
                    raise InterruptedError("Regeneration cancelled")
                self.progress.emit(pct, msg)

            results = engine.regenerate_category(self.category, on_progress)
            self.finished.emit(True, f"Regenerated {len(results)} items")

        except InterruptedError:
            self.finished.emit(False, "Regeneration cancelled")
        except Exception as e:
            logger.error("Regeneration failed: %s", e)
            self.finished.emit(False, f"Error: {e}")
