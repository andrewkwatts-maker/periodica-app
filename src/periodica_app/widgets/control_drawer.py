"""
ControlDrawer -- side drawer for a screen's controls, built from a config dict.

Two families of sections:

* domain sections (``layout_modes``, ``properties``, ``toggles``,
  ``actions``) with their dedicated callbacks, used by DomainScreen;
* generic sections (``spinners``, ``segmented``, ``sliders``, ``buttons``),
  validated by ``control_specs`` and reported through one callback,
  ``on_control(key, value)``, with the live values kept in ``control_values``.

Sections render in a fixed order (``SECTION_ORDER``), so a config without
generic sections builds exactly the drawer it always did.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.slider import Slider
from kivy.uix.togglebutton import ToggleButton
from kivy.properties import DictProperty, ObjectProperty, StringProperty
from kivy.metrics import dp
from kivy.lang import Builder

from periodica_app.theme import (
    BG_PANEL, BG_CONTROL, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY,
)
from periodica_app.widgets.control_specs import initial_values, parse_generic_sections

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
""")


class SectionLabel(Label):
    """Section header label for control groups."""
    pass


SPINNER_BACKGROUND = (0.176, 0.176, 0.255, 1)

# Render order of the config sections.
SECTION_ORDER = (
    "layout_modes", "properties", "spinners", "segmented", "sliders",
    "toggles", "buttons", "actions",
)

# Visual-encoding spinners of the "properties" section:
# (heading, attribute, config default key, fallback default, handler name).
# A fallback of None means "the first property".
PROPERTY_SPINNERS = (
    ("Fill Color", "fill_spinner", "fill_default", None, "_on_fill_spinner_change"),
    ("Border Color", "border_spinner", "border_default", None, "_on_border_spinner_change"),
    ("Glow Effect", "glow_spinner", "glow_default", "None", "_on_glow_spinner_change"),
    ("Sort By", "sort_spinner", "sort_default", None, "_on_sort_spinner_change"),
)


def make_spinner(text, values):
    """A styled Spinner for one drawer option.

    ``kivy.uix.spinner`` imports ``kivy.uix.dropdown``, which creates the
    Window at import time.  Importing it here, at build time, keeps this
    module importable without a GL context (tier-A tests, headless CI).
    """
    from kivy.uix.spinner import Spinner

    return Spinner(
        text=text,
        values=values,
        size_hint_y=None,
        height=dp(40),
        background_color=SPINNER_BACKGROUND,
        color=(1, 1, 1, 0.9),
        font_size="13sp",
    )


def _fit_text(label):
    """Wrap a label's text to its width."""
    label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
    return label


class ControlDrawer(BoxLayout):
    """
    Side drawer containing visualization controls.
    Built dynamically from a config dict (see ``build_controls``).
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

    # Callbacks of the domain sections
    on_layout_change = ObjectProperty(None, allownone=True)
    on_fill_change = ObjectProperty(None, allownone=True)
    on_border_change = ObjectProperty(None, allownone=True)
    on_glow_change = ObjectProperty(None, allownone=True)
    on_sort_change = ObjectProperty(None, allownone=True)
    on_action = ObjectProperty(None, allownone=True)  # toggles + CRUD buttons

    # Generic sections: callable(key, value); value is None for buttons
    on_control = ObjectProperty(None, allownone=True)
    # Current value of every stateful generic control, by key
    control_values = DictProperty({})

    def build_controls(self, config):
        """
        Build control widgets from a config dict.

        Domain sections:
        {
            "layout_modes": {"display_name": enum_value, ...},
            "default_layout": "display_name",
            "properties": {"display_name": "json_key", ...},
            "fill_default": "display_name",
            "border_default": "display_name",
            "glow_default": "display_name",
            "sort_default": "display_name",
            "toggles": [{"label": str, "key": str, "default": bool}, ...],
            "actions": ["add", "edit", "remove", "export", "import", "duplicate", "reset"],
        }

        Generic sections (see ``control_specs``), reported via ``on_control``:
        {
            "spinners":  [{"key", "label", "values", "default"}],
            "segmented": [{"key", "label", "options", "default"}],
            "sliders":   [{"key", "label", "min", "max", "default", "step", "format"}],
            "buttons":   [{"key", "label"}],
        }

        Raises ``ControlSpecError`` before touching the drawer if a generic
        section is malformed.
        """
        generic = parse_generic_sections(config)
        box = self.ids.controls_box
        box.clear_widgets()
        self.control_values = initial_values(generic)

        for section in SECTION_ORDER:
            if section in generic:
                getattr(self, f"_build_{section}")(box, generic[section])
            elif section in config:
                getattr(self, f"_build_{section}")(box, config)

    # -- domain sections -------------------------------------------------

    def _section(self, box, text):
        box.add_widget(SectionLabel(text=text, color=self.accent_color))

    def _build_layout_modes(self, box, config):
        self._section(box, "Layout Mode")
        layout_names = list(config["layout_modes"].keys())
        default = config.get("default_layout", layout_names[0])
        spinner = make_spinner(default, layout_names)
        spinner.bind(text=self._on_layout_spinner_change)
        self.layout_spinner = spinner
        box.add_widget(spinner)

    def _build_properties(self, box, config):
        prop_names = list(config["properties"].keys())
        for heading, attr, default_key, fallback, handler in PROPERTY_SPINNERS:
            self._section(box, heading)
            default = config.get(default_key, fallback if fallback else prop_names[0])
            spinner = make_spinner(default, prop_names)
            spinner.bind(text=getattr(self, handler))
            setattr(self, attr, spinner)
            box.add_widget(spinner)

    def _build_toggles(self, box, config):
        self._section(box, "Display Options")
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
            lbl = _fit_text(Label(
                text=toggle["label"],
                font_size="13sp",
                color=TEXT_PRIMARY,
                halign="left",
                valign="middle",
            ))
            row.add_widget(cb)
            row.add_widget(lbl)
            box.add_widget(row)

    def _build_actions(self, box, config):
        self._section(box, "Data Operations")
        for action_name in config["actions"]:
            btn = self._button(action_name.replace("_", " ").title())
            btn.bind(on_release=lambda inst, a=action_name:
                     self._on_action_button(a))
            box.add_widget(btn)

    # -- generic sections ------------------------------------------------

    def _build_spinners(self, box, specs):
        for spec in specs:
            self._section(box, spec.label)
            spinner = make_spinner(spec.default, list(spec.values))
            spinner.bind(text=lambda inst, text, k=spec.key: self._set_control(k, text))
            box.add_widget(spinner)

    def _build_segmented(self, box, specs):
        for spec in specs:
            self._section(box, spec.label)
            row = BoxLayout(orientation="horizontal", size_hint_y=None,
                            height=dp(36), spacing=dp(2))
            # ToggleButton groups are global: make the name unique per drawer.
            group = f"control-drawer-{self.uid}-{spec.key}"
            for option in spec.options:
                button = ToggleButton(
                    text=option,
                    group=group,
                    allow_no_selection=False,
                    state="down" if option == spec.default else "normal",
                    background_color=BG_CONTROL,
                    color=TEXT_PRIMARY,
                    font_size="12sp",
                )
                button.bind(state=lambda inst, state, k=spec.key:
                            self._on_segment(k, inst, state))
                row.add_widget(button)
            box.add_widget(row)

    def _build_sliders(self, box, specs):
        for spec in specs:
            header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(32))
            header.add_widget(SectionLabel(text=spec.label, color=self.accent_color))
            readout = Label(text=spec.display(spec.default), font_size="12sp",
                            color=TEXT_SECONDARY, size_hint_x=None, width=dp(72),
                            halign="right", valign="bottom")
            readout.bind(size=lambda w, s: setattr(w, "text_size", s))
            header.add_widget(readout)
            box.add_widget(header)
            slider = Slider(min=spec.min, max=spec.max, value=spec.default, step=spec.step,
                            size_hint_y=None, height=dp(32))
            slider.bind(value=lambda inst, value, sp=spec, out=readout:
                        self._on_slider(sp, out, value))
            box.add_widget(slider)

    def _build_buttons(self, box, specs):
        for spec in specs:
            btn = self._button(spec.label)
            btn.bind(on_release=lambda inst, k=spec.key: self._emit_control(k, None))
            box.add_widget(btn)

    def _button(self, text):
        return Button(
            text=text,
            size_hint_y=None,
            height=dp(40),
            background_color=BG_CONTROL,
            color=TEXT_PRIMARY,
            font_size="13sp",
        )

    # -- callbacks -------------------------------------------------------

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

    def _on_segment(self, key, button, state):
        if state != "down":
            return
        # Kivy only releases the rest of a group on a touch press; enforce
        # exclusivity here so selecting from code behaves the same.
        for other in ToggleButton.get_widgets(button.group):
            if other is not button:
                other.state = "normal"
        self._set_control(key, button.text)

    def _on_slider(self, spec, readout, value):
        value = spec.snap(value)
        readout.text = spec.display(value)
        self._set_control(spec.key, value)

    def _set_control(self, key, value):
        """Record a stateful control's new value and report it (once)."""
        if self.control_values.get(key) == value:
            return
        self.control_values[key] = value
        self._emit_control(key, value)

    def _emit_control(self, key, value):
        if self.on_control:
            self.on_control(key, value)
