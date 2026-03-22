"""
Centralized UI styling constants for the Periodics application.

This module provides a single source of truth for all UI styling including:
- Color palettes (accents, backgrounds, text)
- Button style templates
- Tooltip templates with formatting
- Keyboard shortcut definitions
"""

from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt


# =============================================================================
# COLOR PALETTE
# =============================================================================

# Primary accent colors
ACCENT_PRIMARY = "#667eea"      # Blue-purple for primary actions
ACCENT_SECONDARY = "#764ba2"    # Purple for secondary actions
ACCENT_SUCCESS = "#4CAF50"      # Green for success states
ACCENT_WARNING = "#FF9800"      # Orange for warnings
ACCENT_DANGER = "#ef5350"       # Red for destructive actions
ACCENT_INFO = "#4fc3f7"         # Cyan for info

# Tab-specific accents
ACCENT_ATOMS = "#26a69a"        # Teal for Atoms tab
ACCENT_QUARKS = "#ab47bc"       # Purple for Quarks tab
ACCENT_SUBATOMIC = "#42a5f5"    # Blue for Subatomic tab
ACCENT_MOLECULES = "#66bb6a"    # Green for Molecules tab
ACCENT_ALLOYS = "#ff7043"       # Orange for Alloys tab

# Background colors
BG_DARK = "rgb(20, 20, 35)"
BG_PANEL = "rgb(30, 30, 50)"
BG_CONTROL = "rgb(45, 45, 65)"
BG_HOVER = "rgb(60, 60, 85)"

# Text colors
TEXT_PRIMARY = "rgba(255, 255, 255, 230)"
TEXT_SECONDARY = "rgba(255, 255, 255, 180)"
TEXT_DISABLED = "rgba(180, 180, 180, 120)"


# =============================================================================
# BUTTON STYLE TEMPLATES
# =============================================================================

def get_button_style(style_type: str = "primary") -> str:
    """
    Get stylesheet for button type.

    Args:
        style_type: One of "primary", "secondary", "danger", "success", "warning", "info"

    Returns:
        CSS stylesheet string for the button
    """
    style_configs = {
        "primary": {
            "bg": ACCENT_PRIMARY,
            "bg_hover": "#7b8fed",
            "bg_pressed": "#5269d4",
            "text": "#ffffff",
        },
        "secondary": {
            "bg": ACCENT_SECONDARY,
            "bg_hover": "#8b5cb5",
            "bg_pressed": "#643d8c",
            "text": "#ffffff",
        },
        "danger": {
            "bg": ACCENT_DANGER,
            "bg_hover": "#f27573",
            "bg_pressed": "#d32f2f",
            "text": "#ffffff",
        },
        "success": {
            "bg": ACCENT_SUCCESS,
            "bg_hover": "#66bb6a",
            "bg_pressed": "#388e3c",
            "text": "#ffffff",
        },
        "warning": {
            "bg": ACCENT_WARNING,
            "bg_hover": "#ffb74d",
            "bg_pressed": "#f57c00",
            "text": "#000000",
        },
        "info": {
            "bg": ACCENT_INFO,
            "bg_hover": "#81d4fa",
            "bg_pressed": "#29b6f6",
            "text": "#000000",
        },
    }

    config = style_configs.get(style_type, style_configs["primary"])

    return f"""
        QPushButton {{
            background-color: {config['bg']};
            color: {config['text']};
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {config['bg_hover']};
        }}
        QPushButton:pressed {{
            background-color: {config['bg_pressed']};
        }}
        QPushButton:disabled {{
            background-color: {BG_CONTROL};
            color: {TEXT_DISABLED};
        }}
    """


def get_disabled_style() -> str:
    """
    Get consistent disabled state styling for any widget.

    Returns:
        CSS stylesheet string for disabled state
    """
    return f"""
        *:disabled {{
            background-color: {BG_CONTROL};
            color: {TEXT_DISABLED};
            border-color: rgba(100, 100, 120, 100);
        }}
    """


def get_tab_button_style(tab_type: str) -> str:
    """
    Get stylesheet for tab-specific buttons.

    Args:
        tab_type: One of "atoms", "quarks", "subatomic", "molecules", "alloys"

    Returns:
        CSS stylesheet string for the tab button
    """
    tab_accents = {
        "atoms": ACCENT_ATOMS,
        "quarks": ACCENT_QUARKS,
        "subatomic": ACCENT_SUBATOMIC,
        "molecules": ACCENT_MOLECULES,
        "alloys": ACCENT_ALLOYS,
    }

    accent = tab_accents.get(tab_type.lower(), ACCENT_PRIMARY)

    return f"""
        QPushButton {{
            background-color: {accent};
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {accent};
            filter: brightness(1.2);
        }}
        QPushButton:pressed {{
            background-color: {accent};
            filter: brightness(0.8);
        }}
        QPushButton:disabled {{
            background-color: {BG_CONTROL};
            color: {TEXT_DISABLED};
        }}
    """


def get_panel_style() -> str:
    """
    Get stylesheet for panel containers.

    Returns:
        CSS stylesheet string for panels
    """
    return f"""
        QWidget {{
            background-color: {BG_PANEL};
            color: {TEXT_PRIMARY};
        }}
    """


def get_control_style() -> str:
    """
    Get stylesheet for control widgets (inputs, combos, etc).

    Returns:
        CSS stylesheet string for controls
    """
    return f"""
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {BG_CONTROL};
            color: {TEXT_PRIMARY};
            border: 1px solid rgba(100, 100, 120, 150);
            border-radius: 4px;
            padding: 6px 10px;
        }}
        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
            background-color: {BG_HOVER};
            border-color: {ACCENT_PRIMARY};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border-color: {ACCENT_PRIMARY};
            border-width: 2px;
        }}
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
            background-color: {BG_CONTROL};
            color: {TEXT_DISABLED};
        }}
    """


# =============================================================================
# TOOLTIP TEMPLATES
# =============================================================================

TOOLTIPS = {
    "add": "Add a new {item_type} to the collection",
    "edit": "Edit the selected {item_type} (Ctrl+E)",
    "remove": "Remove the selected {item_type} (Del)",
    "export": "Export the selected {item_type} to a file (Ctrl+S)",
    "import": "Import {item_type} data from a file (Ctrl+O)",
    "duplicate": "Create a copy of the selected {item_type} (Ctrl+D)",
    "reset_view": "Reset zoom and pan to default view",
    "reset_data": "Reset all data to default values (cannot be undone)",
    "create": "Create new {target} from {source}",
    "search": "Search for {item_type} by name or property",
    "filter": "Filter {item_type} by category or attribute",
    "sort": "Sort {item_type} by the selected criteria",
    "select_all": "Select all {item_type} items (Ctrl+A)",
    "deselect_all": "Clear selection",
    "zoom_in": "Zoom in (+)",
    "zoom_out": "Zoom out (-)",
    "fit_view": "Fit all items in view",
    "toggle_grid": "Toggle grid visibility",
    "toggle_labels": "Toggle label visibility",
    "properties": "View/edit properties of selected {item_type}",
    "help": "Open help documentation",
    "settings": "Open application settings",
    "undo": "Undo last action (Ctrl+Z)",
    "redo": "Redo last undone action (Ctrl+Y)",
}


def get_tooltip(key: str, **kwargs) -> str:
    """
    Get formatted tooltip text.

    Args:
        key: The tooltip key from TOOLTIPS dictionary
        **kwargs: Format arguments to substitute in the template

    Returns:
        Formatted tooltip string, or empty string if key not found

    Example:
        >>> get_tooltip("add", item_type="element")
        "Add a new element to the collection"
        >>> get_tooltip("create", target="molecule", source="atoms")
        "Create new molecule from atoms"
    """
    template = TOOLTIPS.get(key, "")
    if not template:
        return ""

    try:
        return template.format(**kwargs)
    except KeyError:
        # Return template with unfilled placeholders if kwargs missing
        return template


# =============================================================================
# KEYBOARD SHORTCUT DEFINITIONS
# =============================================================================

SHORTCUTS = {
    "add": QKeySequence.StandardKey.New,
    "edit": Qt.Modifier.CTRL | Qt.Key.Key_E,
    "remove": QKeySequence.StandardKey.Delete,
    "export": QKeySequence.StandardKey.Save,
    "import": QKeySequence.StandardKey.Open,
    "duplicate": Qt.Modifier.CTRL | Qt.Key.Key_D,
    "undo": QKeySequence.StandardKey.Undo,
    "redo": QKeySequence.StandardKey.Redo,
    "select_all": QKeySequence.StandardKey.SelectAll,
    "find": QKeySequence.StandardKey.Find,
    "copy": QKeySequence.StandardKey.Copy,
    "paste": QKeySequence.StandardKey.Paste,
    "cut": QKeySequence.StandardKey.Cut,
    "close": QKeySequence.StandardKey.Close,
    "quit": QKeySequence.StandardKey.Quit,
    "refresh": QKeySequence.StandardKey.Refresh,
    "zoom_in": QKeySequence.StandardKey.ZoomIn,
    "zoom_out": QKeySequence.StandardKey.ZoomOut,
    "help": QKeySequence.StandardKey.HelpContents,
    "preferences": QKeySequence.StandardKey.Preferences,
    "toggle_fullscreen": Qt.Modifier.CTRL | Qt.Key.Key_F11,
    "escape": Qt.Key.Key_Escape,
    "enter": Qt.Key.Key_Return,
    "tab_next": Qt.Modifier.CTRL | Qt.Key.Key_Tab,
    "tab_prev": Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_Tab,
}


def get_shortcut(key: str) -> QKeySequence:
    """
    Get a QKeySequence for the given shortcut key.

    Args:
        key: The shortcut key from SHORTCUTS dictionary

    Returns:
        QKeySequence for the shortcut, or empty sequence if not found
    """
    shortcut = SHORTCUTS.get(key)
    if shortcut is None:
        return QKeySequence()

    if isinstance(shortcut, QKeySequence.StandardKey):
        return QKeySequence(shortcut)

    return QKeySequence(shortcut)


def get_shortcut_text(key: str) -> str:
    """
    Get human-readable text for a shortcut.

    Args:
        key: The shortcut key from SHORTCUTS dictionary

    Returns:
        Human-readable shortcut string (e.g., "Ctrl+E")
    """
    sequence = get_shortcut(key)
    return sequence.toString(QKeySequence.SequenceFormat.NativeText)


# =============================================================================
# THEME COLORS CLASS (convenience wrapper)
# =============================================================================

class ThemeColors:
    """Convenience class wrapping theme color constants."""
    # Accents
    ACCENT = ACCENT_PRIMARY
    ACCENT_LIGHT = "#7b8fed"
    ACCENT_DARK = "#5269d4"
    ACCENT_SUCCESS = ACCENT_SUCCESS
    ACCENT_WARNING = ACCENT_WARNING
    ACCENT_DANGER = ACCENT_DANGER

    # Backgrounds
    BG_DARK = BG_DARK
    BG_MEDIUM = BG_PANEL
    BG_LIGHT = BG_CONTROL
    BG_HOVER = BG_HOVER

    # Text
    TEXT_PRIMARY = TEXT_PRIMARY
    TEXT_SECONDARY = TEXT_SECONDARY
    TEXT_DISABLED = TEXT_DISABLED

    # Borders
    BORDER = "rgba(100, 100, 120, 150)"
    BORDER_ACTIVE = ACCENT_PRIMARY


# =============================================================================
# FONT DEFINITIONS
# =============================================================================

FONT_FAMILY = "Segoe UI, Arial, sans-serif"
FONT_FAMILY_MONO = "Consolas, Monaco, monospace"

FONT_SIZE_SMALL = 10
FONT_SIZE_NORMAL = 12
FONT_SIZE_LARGE = 14
FONT_SIZE_TITLE = 16
FONT_SIZE_HEADER = 20


# =============================================================================
# DIMENSION CONSTANTS
# =============================================================================

BORDER_RADIUS_SMALL = 2
BORDER_RADIUS_NORMAL = 4
BORDER_RADIUS_LARGE = 8

PADDING_SMALL = 4
PADDING_NORMAL = 8
PADDING_LARGE = 16

MARGIN_SMALL = 4
MARGIN_NORMAL = 8
MARGIN_LARGE = 16

ICON_SIZE_SMALL = 16
ICON_SIZE_NORMAL = 24
ICON_SIZE_LARGE = 32

BUTTON_HEIGHT_SMALL = 28
BUTTON_HEIGHT_NORMAL = 36
BUTTON_HEIGHT_LARGE = 44
