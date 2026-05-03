"""
ControlDrawer — Side drawer for domain controls.
Replaces the left-side ControlPanel from the PySide6 version.
Data-driven: builds controls from a config dict.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.metrics import dp
from kivy.lang import Builder

from periodica_app.theme import (
    BG_PANEL, BG_CONTROL, BG_HOVER, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_PRIMARY, hex_to_rgba,
)

Builder.load_string("""
<ControlDrawer>:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: root.bg_color
        Rectangle:
            pos: self.pos
            size: self.size

    # Header
    BoxLayout:
        size_hint_y: None
        height: dp(56)
        padding: dp(16), dp(8)

        Label:
            text: root.title
            font_size: '18sp'
            bold: True
            color: root.accent_color
            halign: 'left'
            valign: 'middle'
            text_size: self.size

    # Scrollable controls
    ScrollView:
        do_scroll_x: False
        bar_color: 0.5, 0.5, 0.7, 0.5
        bar_width: dp(4)

        BoxLayout:
            id: controls_box
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: dp(12)
            spacing: dp(8)

<SectionLabel>:
    size_hint_y: None
    height: dp(32)
    font_size: '13sp'
    bold: True
    halign: 'left'
    valign: 'bottom'
    text_size: self.size
    padding: 0, dp(8)

<ControlSpinner>:
    size_hint_y: None
    height: dp(40)
    background_color: 0.176, 0.176, 0.255, 1
    color: 1, 1, 1, 0.9
    font_size: '13sp'
""")


class SectionLabel(Label):
    """Section header label for control groups."""
    pass


class ControlSpinner(Spinner):
    """Styled spinner for control options."""
    pass


class ControlDrawer(BoxLayout):
    """
    Side drawer containing visualization controls.
    Built dynamically from a config dict.
    """

    title = StringProperty("Controls")
    accent_color = ObjectProperty(ACCENT_PRIMARY)
    bg_color = ObjectProperty(BG_PANEL)

    # References to key controls for external binding
    layout_spinner = ObjectProperty(None, allownone=True)
    fill_spinner = ObjectProperty(None, allownone=True)
    border_spinner = ObjectProperty(None, allownone=True)
    glow_spinner = ObjectProperty(None, allownone=True)
    sort_spinner = ObjectProperty(None, allownone=True)

    # Callbacks
    on_layout_change = ObjectProperty(None, allownone=True)
    on_fill_change = ObjectProperty(None, allownone=True)
    on_border_change = ObjectProperty(None, allownone=True)
    on_glow_change = ObjectProperty(None, allownone=True)
    on_sort_change = ObjectProperty(None, allownone=True)
    on_action = ObjectProperty(None, allownone=True)  # For CRUD buttons

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build_controls(self, config):
        """
        Build control widgets from a config dict.

        Config format:
        {
            "layout_modes": {"display_name": enum_value, ...},
            "default_layout": "display_name",
            "properties": {"display_name": "json_key", ...},
            "fill_default": "display_name",
            "border_default": "display_name",
            "glow_default": "display_name",
            "sort_default": "display_name",
            "filters": [{"label": str, "key": str, "default": bool}, ...],
            "toggles": [{"label": str, "key": str, "default": bool}, ...],
            "actions": ["add", "edit", "remove", "export", "import", "duplicate", "reset"],
        }
        """
        box = self.ids.controls_box
        box.clear_widgets()

        # Layout mode selector
        if "layout_modes" in config:
            box.add_widget(SectionLabel(text="Layout Mode", color=self.accent_color))
            layout_names = list(config["layout_modes"].keys())
            default = config.get("default_layout", layout_names[0])
            spinner = ControlSpinner(
                text=default,
                values=layout_names,
            )
            spinner.bind(text=self._on_layout_spinner_change)
            self.layout_spinner = spinner
            box.add_widget(spinner)

        # Visual encoding properties
        if "properties" in config:
            prop_names = list(config["properties"].keys())

            box.add_widget(SectionLabel(text="Fill Color", color=self.accent_color))
            self.fill_spinner = ControlSpinner(
                text=config.get("fill_default", prop_names[0]),
                values=prop_names,
            )
            self.fill_spinner.bind(text=self._on_fill_spinner_change)
            box.add_widget(self.fill_spinner)

            box.add_widget(SectionLabel(text="Border Color", color=self.accent_color))
            self.border_spinner = ControlSpinner(
                text=config.get("border_default", prop_names[0]),
                values=prop_names,
            )
            self.border_spinner.bind(text=self._on_border_spinner_change)
            box.add_widget(self.border_spinner)

            box.add_widget(SectionLabel(text="Glow Effect", color=self.accent_color))
            self.glow_spinner = ControlSpinner(
                text=config.get("glow_default", "None"),
                values=prop_names,
            )
            self.glow_spinner.bind(text=self._on_glow_spinner_change)
            box.add_widget(self.glow_spinner)

            # Sort property (for linear layouts)
            box.add_widget(SectionLabel(text="Sort By", color=self.accent_color))
            self.sort_spinner = ControlSpinner(
                text=config.get("sort_default", prop_names[0]),
                values=prop_names,
            )
            self.sort_spinner.bind(text=self._on_sort_spinner_change)
            box.add_widget(self.sort_spinner)

        # Toggle options
        if "toggles" in config:
            box.add_widget(SectionLabel(text="Display Options", color=self.accent_color))
            for toggle in config["toggles"]:
                row = BoxLayout(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(36),
                    spacing=dp(8),
                )
                cb = CheckBox(
                    active=toggle.get("default", False),
                    size_hint_x=None,
                    width=dp(36),
                    color=self.accent_color,
                )
                toggle_key = toggle["key"]
                cb.bind(active=lambda inst, val, k=toggle_key:
                        self._on_toggle(k, val))
                lbl = Label(
                    text=toggle["label"],
                    font_size="13sp",
                    color=TEXT_PRIMARY,
                    halign="left",
                    valign="middle",
                )
                lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
                row.add_widget(cb)
                row.add_widget(lbl)
                box.add_widget(row)

        # Action buttons
        if "actions" in config:
            box.add_widget(SectionLabel(text="Data Operations", color=self.accent_color))
            for action_name in config["actions"]:
                btn = Button(
                    text=action_name.replace("_", " ").title(),
                    size_hint_y=None,
                    height=dp(40),
                    background_color=BG_CONTROL,
                    color=TEXT_PRIMARY,
                    font_size="13sp",
                )
                btn.bind(on_release=lambda inst, a=action_name:
                         self._on_action_button(a))
                box.add_widget(btn)

    def _on_layout_spinner_change(self, spinner, text):
        if self.on_layout_change:
            self.on_layout_change(text)

    def _on_fill_spinner_change(self, spinner, text):
        if self.on_fill_change:
            self.on_fill_change(text)

    def _on_border_spinner_change(self, spinner, text):
        if self.on_border_change:
            self.on_border_change(text)

    def _on_glow_spinner_change(self, spinner, text):
        if self.on_glow_change:
            self.on_glow_change(text)

    def _on_sort_spinner_change(self, spinner, text):
        if self.on_sort_change:
            self.on_sort_change(text)

    def _on_toggle(self, key, value):
        if self.on_action:
            self.on_action(f"toggle_{key}", value)

    def _on_action_button(self, action):
        if self.on_action:
            self.on_action(action, None)
