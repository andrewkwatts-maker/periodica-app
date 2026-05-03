"""
InfoSheet — Bottom sheet panel for displaying selected item details.
Replaces the right-side InfoPanel from the PySide6 version.
Data-driven: renders any domain's item data from config.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.properties import ObjectProperty, StringProperty, DictProperty
from kivy.metrics import dp
from kivy.lang import Builder

from periodica_app.theme import (
    BG_PANEL, BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_INFO,
    FORCE_COLORS, PARTICLE_TYPE_COLORS,
)

Builder.load_string("""
<InfoSheet>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(350)
    canvas.before:
        Color:
            rgba: root.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16), dp(16), 0, 0]

    # Handle bar
    Widget:
        size_hint_y: None
        height: dp(24)
        canvas:
            Color:
                rgba: 0.5, 0.5, 0.5, 0.5
            RoundedRectangle:
                pos: self.center_x - dp(20), self.center_y - dp(2)
                size: dp(40), dp(4)
                radius: [dp(2)]

    # Title
    Label:
        id: title_label
        text: root.title_text
        font_size: '18sp'
        bold: True
        color: root.accent_color
        size_hint_y: None
        height: dp(36)
        halign: 'left'
        valign: 'middle'
        text_size: self.width - dp(32), None
        padding: dp(16), 0

    # Scrollable content
    ScrollView:
        do_scroll_x: False
        bar_color: 0.5, 0.5, 0.7, 0.5
        bar_width: dp(4)

        BoxLayout:
            id: content_box
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: dp(16)
            spacing: dp(8)
""")


class InfoSheet(BoxLayout):
    """
    Bottom sheet displaying detailed information for a selected item.
    Fully data-driven — builds display from item dict keys.
    """

    item = ObjectProperty(None, allownone=True)
    title_text = StringProperty("Select an item")
    accent_color = ObjectProperty(ACCENT_INFO)
    bg_color = ObjectProperty(BG_PANEL)

    # Config: list of property groups to display
    # Each group: {"title": str, "fields": [{"key": str, "label": str, "format": str|None}]}
    display_config = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(item=self._update_display)

    def _update_display(self, *args):
        content = self.ids.content_box
        content.clear_widgets()

        if not self.item:
            self.title_text = "Select an item"
            self._add_hint_text(content)
            return

        name = self.item.get("Name", self.item.get("name", "Unknown"))
        symbol = self.item.get("Symbol", self.item.get("symbol", ""))
        self.title_text = f"{symbol}  {name}" if symbol else name

        if self.display_config:
            self._render_from_config(content)
        else:
            self._render_generic(content)

    def _add_hint_text(self, container):
        hint = Label(
            text="Tap any item to view details",
            color=TEXT_SECONDARY,
            font_size="14sp",
            size_hint_y=None,
            height=dp(40),
        )
        container.add_widget(hint)

    def _render_from_config(self, container):
        """Render item details using display_config groups."""
        for group in self.display_config:
            self._add_section_header(container, group["title"])
            for field in group["fields"]:
                key = field["key"]
                label = field["label"]
                value = self.item.get(key)
                if value is not None:
                    fmt = field.get("format")
                    display_val = fmt.format(value) if fmt else str(value)
                    self._add_property_row(container, label, display_val)

    def _render_generic(self, container):
        """Render all item properties generically."""
        # Skip internal/layout keys
        skip_keys = {"x", "y", "display_size", "in_layout", "sm_row", "sm_col",
                     "sort_index", "angle", "radius", "ring"}

        for key, value in self.item.items():
            if key in skip_keys:
                continue
            if isinstance(value, (dict, list)):
                if isinstance(value, list) and len(value) < 10:
                    display_val = ", ".join(str(v) for v in value)
                else:
                    display_val = str(value)[:100]
            else:
                display_val = str(value)

            label = key.replace("_", " ").title()
            self._add_property_row(container, label, display_val)

    def _add_section_header(self, container, title):
        header = Label(
            text=title,
            font_size="14sp",
            bold=True,
            color=self.accent_color,
            size_hint_y=None,
            height=dp(28),
            halign="left",
            valign="middle",
        )
        header.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        container.add_widget(header)

    def _add_property_row(self, container, label, value):
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(24),
            spacing=dp(8),
        )
        lbl = Label(
            text=label,
            font_size="12sp",
            color=TEXT_SECONDARY,
            size_hint_x=0.4,
            halign="left",
            valign="middle",
        )
        lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))

        val = Label(
            text=str(value),
            font_size="12sp",
            color=TEXT_PRIMARY,
            size_hint_x=0.6,
            halign="left",
            valign="middle",
        )
        val.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))

        row.add_widget(lbl)
        row.add_widget(val)
        container.add_widget(row)

    def clear(self):
        """Clear the info display."""
        self.item = None
