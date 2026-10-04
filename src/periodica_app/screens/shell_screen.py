"""
ShellScreen -- the frame every screen shares.

Layout: a collapsible ``ControlDrawer`` on the left; on the right a toolbar
(drawer toggle, title, Info button), the ``view_host`` holding the screen's
main view, and a collapsible ``InfoSheet`` at the bottom.

Subclasses supply the main view by overriding ``create_view()``; it is added
to ``view_host`` and published as ``self.view`` and ``self.ids[view_id]``.
``DomainScreen`` puts a 2-D ``CanvasView`` there, ``SceneScreen`` a GPU view.
"""

from kivy.lang import Builder
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.screenmanager import Screen

from periodica_app.theme import ACCENT_PRIMARY

# Imported for their side effect: defining a Widget subclass registers it
# with the kv Factory, which the <ShellScreen> rule below instantiates by name.
from periodica_app.widgets.control_drawer import ControlDrawer  # noqa: F401
from periodica_app.widgets.info_sheet import InfoSheet  # noqa: F401

Builder.load_string("""
<ShellScreen>:
    BoxLayout:
        orientation: 'horizontal'
        pos: root.pos
        size: root.size

        # Left: Control drawer (collapsible)
        ControlDrawer:
            id: control_drawer
            size_hint_x: None
            width: dp(280) if root.show_controls else 0
            opacity: 1 if root.show_controls else 0
            title: root.domain_title
            accent_color: root.accent_color

        # Right: toolbar, main view, info sheet
        BoxLayout:
            orientation: 'vertical'

            BoxLayout:
                id: toolbar
                size_hint_y: None
                height: dp(48)
                padding: dp(8)
                spacing: dp(8)
                canvas.before:
                    Color:
                        rgba: 0.12, 0.12, 0.2, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size

                Button:
                    text: '\\u2630'
                    size_hint_x: None
                    width: dp(48)
                    font_size: '20sp'
                    background_color: 0, 0, 0, 0
                    color: 1, 1, 1, 0.9
                    on_release: root.toggle_controls()

                Label:
                    text: root.domain_title
                    font_size: '16sp'
                    bold: True
                    color: root.accent_color
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size

                Button:
                    text: 'Info'
                    size_hint_x: None
                    width: dp(64)
                    font_size: '13sp'
                    background_color: root.accent_color
                    color: 1, 1, 1, 1
                    on_release: root.toggle_info()

            # Main view (supplied by the subclass via create_view)
            BoxLayout:
                id: view_host

            InfoSheet:
                id: info_sheet
                size_hint_y: None
                height: dp(300) if root.show_info else 0
                opacity: 1 if root.show_info else 0
                accent_color: root.accent_color
""")


class ShellScreen(Screen):
    """Toolbar + ControlDrawer + InfoSheet around a subclass-provided view."""

    #: title shown in the toolbar and the drawer header
    domain_title = StringProperty("Domain")
    accent_color = ObjectProperty(ACCENT_PRIMARY)
    show_controls = BooleanProperty(True)
    show_info = BooleanProperty(False)

    #: the main view widget living in ``ids.view_host``
    view = ObjectProperty(None, allownone=True)

    #: key under which the main view is also published in ``self.ids``
    view_id = "view"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_view(self.create_view())

    def create_view(self):
        """Return the screen's main view widget (override); None = empty."""
        return None

    def set_view(self, widget):
        """Replace the main view."""
        host = self.ids.view_host
        host.clear_widgets()
        if self.view is not None:
            self.ids.pop(self.view_id, None)
        self.view = widget
        if widget is not None:
            host.add_widget(widget)
            self.ids[self.view_id] = widget

    # ── UI toggles ───────────────────────────────────────────────────

    def toggle_controls(self):
        self.show_controls = not self.show_controls

    def toggle_info(self):
        self.show_info = not self.show_info
