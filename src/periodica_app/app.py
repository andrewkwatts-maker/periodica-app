"""
Main application entry point.
MDApp subclass with ScreenManager and navigation drawer.
"""

import os

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty

from kivymd.app import MDApp

from periodica_app.theme import (
    BG_DARK, BG_PANEL, BG_CONTROL, TEXT_PRIMARY, TEXT_SECONDARY,
    DOMAIN_COLORS, ACCENT_PRIMARY, hex_to_rgba,
)

# Domain registry: (key, display_name, group)
DOMAINS = [
    # Physics
    ("quarks", "Quarks", "Physics"),
    ("subatomic", "Subatomic", "Physics"),
    ("atoms", "Atoms", "Physics"),
    # Chemistry
    ("molecules", "Molecules", "Chemistry"),
    ("alloys", "Alloys", "Chemistry"),
    ("materials", "Materials", "Chemistry"),
    # Biology
    ("amino_acids", "Amino Acids", "Biology"),
    ("proteins", "Proteins", "Biology"),
    ("nucleic_acids", "Nucleic Acids", "Biology"),
    ("cell_components", "Cell Components", "Biology"),
    ("cells", "Cells", "Biology"),
    ("biomaterials", "Biomaterials", "Biology"),
]

# Lazy screen factories — import only when navigated to
SCREEN_FACTORIES = {}


def register_screen(domain_key, factory):
    """Register a screen factory for a domain."""
    SCREEN_FACTORIES[domain_key] = factory


# Register available screens
def _register_defaults():
    try:
        from periodica_app.screens.quarks_screen import create_quarks_screen
        register_screen("quarks", create_quarks_screen)
    except ImportError as e:
        print(f"Quarks screen not available: {e}")


KV = """
#:import SlideTransition kivy.uix.screenmanager.SlideTransition

<NavButton@Button>:
    size_hint_y: None
    height: dp(44)
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 0.9
    font_size: '14sp'
    halign: 'left'
    valign: 'middle'
    text_size: self.width - dp(32), None
    padding: dp(24), 0

<NavGroupLabel@Label>:
    size_hint_y: None
    height: dp(32)
    font_size: '11sp'
    bold: True
    color: 0.5, 0.5, 0.7, 1
    halign: 'left'
    valign: 'bottom'
    text_size: self.width - dp(16), None
    padding: dp(16), 0

<RootLayout>:
    orientation: 'horizontal'

    # Navigation panel
    BoxLayout:
        id: nav_panel
        orientation: 'vertical'
        size_hint_x: None
        width: dp(220) if root.nav_open else 0
        opacity: 1 if root.nav_open else 0
        canvas.before:
            Color:
                rgba: 0.1, 0.1, 0.18, 1
            Rectangle:
                pos: self.pos
                size: self.size

        # App title
        BoxLayout:
            size_hint_y: None
            height: dp(64)
            padding: dp(16), dp(12)
            Label:
                text: 'Periodica'
                font_size: '22sp'
                bold: True
                color: 0.4, 0.5, 0.92, 1
                halign: 'left'
                valign: 'middle'
                text_size: self.size

        # Domain list
        ScrollView:
            do_scroll_x: False
            bar_color: 0.3, 0.3, 0.5, 0.5
            bar_width: dp(3)

            BoxLayout:
                id: nav_list
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(4)
                spacing: dp(2)

    # Main content area
    ScreenManager:
        id: screen_manager
        transition: SlideTransition(direction='left', duration=0.2)
"""


class RootLayout(BoxLayout):
    nav_open = ObjectProperty(True)

    def toggle_nav(self):
        self.nav_open = not self.nav_open


class PeriodicaApp(MDApp):
    """Main KivyMD application."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._loaded_screens = set()

    def build(self):
        self.title = "Periodica"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        # Set window properties
        Window.clearcolor = BG_DARK
        Window.size = (1200, 800)
        Window.minimum_width = 800
        Window.minimum_height = 600
        Window.left = 100
        Window.top = 100

        Builder.load_string(KV)
        _register_defaults()

        self.root = RootLayout()
        self._build_nav()

        # Navigate to first available screen
        for key, name, group in DOMAINS:
            if key in SCREEN_FACTORIES:
                self._navigate_to(key)
                break

        return self.root

    def _build_nav(self):
        """Build the navigation list with grouped domains."""
        nav_list = self.root.ids.nav_list
        nav_list.clear_widgets()

        current_group = None
        for key, display_name, group in DOMAINS:
            # Add group header
            if group != current_group:
                current_group = group
                header = Label(
                    text=group.upper(),
                    size_hint_y=None,
                    height=dp(32),
                    font_size="11sp",
                    bold=True,
                    color=(0.5, 0.5, 0.7, 1),
                    halign="left",
                    valign="bottom",
                )
                header.bind(size=lambda w, s: setattr(w, "text_size",
                            (s[0] - dp(16), None)))
                header.padding = (dp(16), 0)
                nav_list.add_widget(header)

            # Domain color indicator
            domain_color = DOMAIN_COLORS.get(key, ACCENT_PRIMARY)
            available = key in SCREEN_FACTORIES

            btn = Button(
                text=f"  {display_name}",
                size_hint_y=None,
                height=dp(44),
                background_color=(0, 0, 0, 0),
                color=domain_color if available else (0.3, 0.3, 0.4, 1),
                font_size="14sp",
                halign="left",
                valign="middle",
                disabled=not available,
            )
            btn.bind(size=lambda w, s: setattr(w, "text_size",
                     (s[0] - dp(32), None)))
            btn.padding = (dp(24), 0)
            if available:
                btn.bind(on_release=lambda inst, k=key: self._navigate_to(k))
            nav_list.add_widget(btn)

    def _navigate_to(self, domain_key):
        """Navigate to a domain screen, creating it lazily if needed."""
        sm = self.root.ids.screen_manager

        if domain_key not in self._loaded_screens:
            factory = SCREEN_FACTORIES.get(domain_key)
            if factory:
                screen = factory()
                screen.name = domain_key
                sm.add_widget(screen)
                self._loaded_screens.add(domain_key)

        if domain_key in self._loaded_screens:
            sm.current = domain_key


def main():
    """Entry point for the application."""
    PeriodicaApp().run()


if __name__ == "__main__":
    main()
