"""
Centralized color palette and styling constants for the Periodica app.
All colors are RGBA tuples (0-1 range) for Kivy compatibility.
"""


def hex_to_rgba(hex_color, alpha=1.0):
    """Convert hex color string to RGBA tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return (r, g, b, alpha)


# =============================================================================
# COLOR PALETTE (RGBA tuples, 0-1 range)
# =============================================================================

# Primary accent colors
ACCENT_PRIMARY = hex_to_rgba("#667eea")
ACCENT_SECONDARY = hex_to_rgba("#764ba2")
ACCENT_SUCCESS = hex_to_rgba("#4CAF50")
ACCENT_WARNING = hex_to_rgba("#FF9800")
ACCENT_DANGER = hex_to_rgba("#ef5350")
ACCENT_INFO = hex_to_rgba("#4fc3f7")

# Domain-specific accents
DOMAIN_COLORS = {
    "quarks": hex_to_rgba("#ab47bc"),
    "subatomic": hex_to_rgba("#42a5f5"),
    "atoms": hex_to_rgba("#26a69a"),
    "molecules": hex_to_rgba("#66bb6a"),
    "alloys": hex_to_rgba("#ff7043"),
    "materials": hex_to_rgba("#78909c"),
    "amino_acids": hex_to_rgba("#ec407a"),
    "proteins": hex_to_rgba("#7e57c2"),
    "nucleic_acids": hex_to_rgba("#26c6da"),
    "cell_components": hex_to_rgba("#9ccc65"),
    "cells": hex_to_rgba("#ffca28"),
    "biomaterials": hex_to_rgba("#8d6e63"),
}

# Background colors
BG_DARK = (20 / 255, 20 / 255, 35 / 255, 1.0)
BG_PANEL = (30 / 255, 30 / 255, 50 / 255, 1.0)
BG_CONTROL = (45 / 255, 45 / 255, 65 / 255, 1.0)
BG_HOVER = (60 / 255, 60 / 255, 85 / 255, 1.0)
BG_CARD = (40 / 255, 40 / 255, 60 / 255, 1.0)

# Text colors
TEXT_PRIMARY = (1.0, 1.0, 1.0, 0.9)
TEXT_SECONDARY = (1.0, 1.0, 1.0, 0.7)
TEXT_DISABLED = (0.7, 0.7, 0.7, 0.47)

# Particle type colors (used across quarks/subatomic)
PARTICLE_TYPE_COLORS = {
    "quark": hex_to_rgba("#ff6b6b"),
    "antiquark": hex_to_rgba("#ff6b6b", 0.6),
    "lepton": hex_to_rgba("#4ecdc4"),
    "antilepton": hex_to_rgba("#4ecdc4", 0.6),
    "boson": hex_to_rgba("#ffe66d"),
    "gauge_boson": hex_to_rgba("#ffe66d"),
    "scalar_boson": hex_to_rgba("#ffd93d"),
    "baryon": hex_to_rgba("#6c5ce7"),
    "meson": hex_to_rgba("#a29bfe"),
    "composite": hex_to_rgba("#fd79a8"),
}

# Interaction force colors
FORCE_COLORS = {
    "strong": hex_to_rgba("#ff6464"),
    "electromagnetic": hex_to_rgba("#6496ff"),
    "weak": hex_to_rgba("#ffc864"),
    "gravitational": hex_to_rgba("#96ff96"),
}

# =============================================================================
# DIMENSION CONSTANTS
# =============================================================================

FONT_SIZE_SMALL = "10sp"
FONT_SIZE_NORMAL = "12sp"
FONT_SIZE_LARGE = "14sp"
FONT_SIZE_TITLE = "16sp"
FONT_SIZE_HEADER = "20sp"

PADDING_SMALL = "4dp"
PADDING_NORMAL = "8dp"
PADDING_LARGE = "16dp"

# =============================================================================
# TOOLTIPS
# =============================================================================

TOOLTIPS = {
    "add": "Add a new {item_type} to the collection",
    "edit": "Edit the selected {item_type}",
    "remove": "Remove the selected {item_type}",
    "export": "Export the selected {item_type} to a file",
    "import": "Import {item_type} data from a file",
    "duplicate": "Create a copy of the selected {item_type}",
    "reset_view": "Reset zoom and pan to default view",
    "reset_data": "Reset all data to default values",
}


def get_tooltip(key, **kwargs):
    """Get formatted tooltip text."""
    template = TOOLTIPS.get(key, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
