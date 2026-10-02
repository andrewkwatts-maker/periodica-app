"""
DomainScreen -- generic screen template for the scientific domains.

Each domain screen is a config dict + this class: layout modes mapped to
renderers, encodable properties, toggles, an info-sheet layout and an
optional enriching data loader.  The frame (toolbar, ControlDrawer,
InfoSheet) comes from ShellScreen; DomainScreen supplies a 2-D CanvasView as
the main view, published as ``ids.canvas_view``, and wires data, controls and
selection to it.
"""

from kivy.properties import ObjectProperty, StringProperty, DictProperty, ListProperty
from kivy.clock import Clock

from periodica.data.data_manager import get_data_manager

from periodica_app.screens.shell_screen import ShellScreen
from periodica_app.widgets.canvas_view import CanvasView


class DomainScreen(ShellScreen):
    """
    Base screen for any scientific domain tab.
    Subclasses provide a config dict and optionally override methods.
    """

    view_id = "canvas_view"

    # ── Configuration (set by subclass) ──────────────────────────────

    # Data category from periodica.data.data_manager.DataCategory
    data_category = ObjectProperty(None, allownone=True)

    # Enum class for layout modes
    layout_enum = ObjectProperty(None, allownone=True)

    # Map of display_name → layout_mode_enum_value
    layout_modes = DictProperty({})

    # Map of display_name → json_key for visual encoding properties
    prop_options = DictProperty({})

    # Map of layout_mode_enum_value → renderer instance
    renderers = DictProperty({})

    # Default selections
    default_layout = StringProperty("")
    fill_default = StringProperty("")
    border_default = StringProperty("")
    glow_default = StringProperty("")
    sort_default = StringProperty("")

    # Toggles config
    toggles = ListProperty([])

    # Info display config
    display_config = ObjectProperty(None, allownone=True)

    # Optional enriching loader: callable(screen) -> list[dict]. When set it
    # replaces the generic DataManager path, which returns RAW JSON dicts --
    # for quarks that meant no sm_row/sm_col/particle_type, so the flagship
    # Standard Model layout dropped every particle into the off-screen
    # non-SM fallback. Domains needing computed fields supply this.
    data_loader = ObjectProperty(None, allownone=True)

    def create_view(self):
        return CanvasView()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._data_manager = get_data_manager()
        self._items = []
        self._current_layout_mode = None
        Clock.schedule_once(self._initialize, 0)

    def _initialize(self, dt):
        """Deferred initialization after widgets are ready."""
        # Screen-side record of every drawer toggle, keyed by toggle key,
        # so the data loader can read 'Show Antiparticles' etc. and load
        # DIFFERENT data instead of reloading identical data.
        self._toggle_state = {
            t["key"]: t.get("default", False) for t in (self.toggles or [])
        }
        self._load_data()
        self._setup_controls()
        self._setup_info()

        # Set initial renderer
        if self.default_layout and self.layout_modes:
            mode = self.layout_modes.get(self.default_layout)
            if mode is not None:
                self._set_renderer(mode)

        # Push items to canvas
        canvas_view = self.ids.canvas_view
        canvas_view.items = self._items
        canvas_view.bind(selected_item=self._on_item_selected)

    def toggle_state(self, key, default=False):
        """Current value of a drawer toggle (recorded in _on_action)."""
        return self._toggle_state.get(key, default)

    def _load_data(self):
        """Load items -- via the domain's enriching loader when it has one."""
        if self.data_loader is not None:
            try:
                self._items = list(self.data_loader(self) or [])
            except Exception as e:
                print(f"[{self.domain_title}] Error loading data: {e}")
                self._items = []
            return
        if self.data_category is None:
            return
        try:
            items = self._data_manager.get_all_items(self.data_category)
            if isinstance(items, dict):
                # DataManager returns dict keyed by name
                self._items = list(items.values())
            elif isinstance(items, list):
                self._items = items
            else:
                self._items = []
        except Exception as e:
            print(f"[{self.domain_title}] Error loading data: {e}")
            self._items = []

    def _setup_controls(self):
        """Configure the control drawer with domain-specific config."""
        control = self.ids.control_drawer
        config = {
            "layout_modes": {name: name for name in self.layout_modes},
            "default_layout": self.default_layout,
            "properties": self.prop_options,
            "fill_default": self.fill_default,
            "border_default": self.border_default,
            "glow_default": self.glow_default,
            "sort_default": self.sort_default,
            "toggles": self.toggles,
            "actions": ["add", "edit", "remove", "export", "import", "reset"],
        }
        control.build_controls(config)
        control.on_layout_change = self._on_layout_change
        control.on_fill_change = self._on_fill_change
        control.on_border_change = self._on_border_change
        control.on_glow_change = self._on_glow_change
        control.on_sort_change = self._on_sort_change
        control.on_action = self._on_action

    def _setup_info(self):
        """Configure the info sheet."""
        info = self.ids.info_sheet
        if self.display_config:
            info.display_config = self.display_config

    # ── Event handlers ───────────────────────────────────────────────

    def _on_layout_change(self, layout_name):
        mode = self.layout_modes.get(layout_name)
        if mode is not None:
            self._set_renderer(mode)

    def _set_renderer(self, mode):
        self._current_layout_mode = mode
        renderer = self.renderers.get(mode)
        if renderer:
            self.ids.canvas_view.renderer = renderer
            self.ids.canvas_view.layout_mode = mode

    def _on_fill_change(self, prop_name):
        key = self.prop_options.get(prop_name, prop_name)
        self.ids.canvas_view.fill_property = key

    def _on_border_change(self, prop_name):
        key = self.prop_options.get(prop_name, prop_name)
        self.ids.canvas_view.border_property = key

    def _on_glow_change(self, prop_name):
        key = self.prop_options.get(prop_name, prop_name)
        self.ids.canvas_view.glow_property = key

    def _on_sort_change(self, prop_name):
        key = self.prop_options.get(prop_name, prop_name)
        self.ids.canvas_view.order_property = key

    def _on_item_selected(self, canvas_view, item):
        """When an item is selected on the canvas, show it in the info sheet."""
        self.ids.info_sheet.item = item
        if item and not self.show_info:
            self.show_info = True

    def _on_action(self, action, value):
        """Handle CRUD and toggle actions."""
        if action.startswith("toggle_"):
            toggle_key = action[7:]
            self._toggle_state[toggle_key] = value
            self._handle_toggle(toggle_key, value)
        elif action == "add":
            self._handle_add()
        elif action == "edit":
            self._handle_edit()
        elif action == "remove":
            self._handle_remove()
        elif action == "export":
            self._handle_export()
        elif action == "import":
            self._handle_import()
        elif action == "reset":
            self._handle_reset()

    # ── CRUD operations (generic via DataManager) ─────────────────

    def _handle_add(self):
        # TODO: Open add dialog
        print(f"[{self.domain_title}] Add requested")

    def _handle_edit(self):
        item = self.ids.canvas_view.selected_item
        if item:
            print(f"[{self.domain_title}] Edit: {item.get('Name', 'unknown')}")

    def _handle_remove(self):
        item = self.ids.canvas_view.selected_item
        if not item or self.data_category is None:
            return
        name = item.get("Name", item.get("name"))
        if name:
            try:
                self._data_manager.remove_item(self.data_category, name)
                self._load_data()
                self.ids.canvas_view.items = self._items
                self.ids.canvas_view.selected_item = None
                self.ids.info_sheet.item = None
            except Exception as e:
                print(f"[{self.domain_title}] Remove error: {e}")

    def _handle_export(self):
        print(f"[{self.domain_title}] Export requested")

    def _handle_import(self):
        print(f"[{self.domain_title}] Import requested")

    def _handle_reset(self):
        if self.data_category is None:
            return
        try:
            self._data_manager.reset_category(self.data_category)
            self._load_data()
            self.ids.canvas_view.items = self._items
            self.ids.canvas_view.selected_item = None
            self.ids.info_sheet.item = None
        except Exception as e:
            print(f"[{self.domain_title}] Reset error: {e}")

    def _handle_toggle(self, key, value):
        """Override in subclass for domain-specific toggles."""
        print(f"[{self.domain_title}] Toggle {key} = {value}")

    def reload_data(self):
        """Reload data from backend and refresh display."""
        self._load_data()
        self.ids.canvas_view.items = self._items
