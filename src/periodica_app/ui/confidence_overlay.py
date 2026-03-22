"""
Confidence Overlay
===================
Mixin/utility for adding confidence color bands to table widgets.
Reads _derivation.confidence from item data and applies color coding.
"""

from PySide6.QtGui import QColor
from typing import Dict, Optional

from periodica.utils.derivation_metadata import DerivationTracker, DerivationSource


def get_confidence_color(data: Dict) -> QColor:
    """
    Get a confidence-based color for a data item.

    Returns:
        QColor: Green (high confidence), Yellow (medium), Red (low),
                Gray (no metadata / manual)
    """
    source = DerivationTracker.get_source(data)

    if source is None:
        return QColor(128, 128, 128, 60)  # gray - no metadata

    if source == DerivationSource.MANUAL:
        return QColor(100, 100, 200, 60)  # blue-gray - manual

    if source == DerivationSource.LOADED_DEFAULT:
        return QColor(128, 128, 128, 40)  # light gray - default

    confidence = DerivationTracker.get_confidence(data)

    if confidence >= 0.8:
        return QColor(72, 187, 120, 80)   # green
    elif confidence >= 0.6:
        return QColor(236, 201, 75, 80)   # yellow
    elif confidence >= 0.4:
        return QColor(237, 137, 54, 80)   # orange
    else:
        return QColor(252, 129, 129, 80)  # red


def get_confidence_label(data: Dict) -> str:
    """Get a human-readable confidence label."""
    source = DerivationTracker.get_source(data)

    if source is None:
        return "No metadata"
    if source == DerivationSource.MANUAL:
        return "Manual"
    if source == DerivationSource.LOADED_DEFAULT:
        return "Default"

    confidence = DerivationTracker.get_confidence(data)
    if confidence >= 0.8:
        return f"High ({confidence:.0%})"
    elif confidence >= 0.6:
        return f"Medium ({confidence:.0%})"
    elif confidence >= 0.4:
        return f"Low ({confidence:.0%})"
    else:
        return f"Very Low ({confidence:.0%})"


def get_source_label(data: Dict) -> str:
    """Get a human-readable source label."""
    source = DerivationTracker.get_source(data)
    if source is None:
        return "Unknown"
    labels = {
        DerivationSource.QUARK_DERIVED: "Quark-derived",
        DerivationSource.PHYSICS_DERIVED: "Physics-derived",
        DerivationSource.MANUAL: "Manual",
        DerivationSource.LOADED_DEFAULT: "Default",
        DerivationSource.AI_GENERATED: "AI-generated",
        DerivationSource.AUTO_GENERATED: "Auto-generated",
    }
    return labels.get(source, source.value)
