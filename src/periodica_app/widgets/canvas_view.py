"""
CanvasView — Main visualization widget using Kivy Canvas.
Replaces the QPainter-based UnifiedTable from the PySide6 version.
Handles rendering, touch interaction (tap, pan, zoom), and item selection.
"""

from kivy.uix.widget import Widget
from kivy.properties import (
    ObjectProperty, NumericProperty, BooleanProperty, DictProperty, ListProperty
)
from kivy.graphics import Color, Rectangle, PushMatrix, PopMatrix, Translate, Scale
from kivy.clock import Clock
from kivy.core.window import Window


class CanvasView(Widget):
    """
    Interactive canvas for rendering scientific visualizations.
    Delegates actual drawing to a renderer object.
    """

    renderer = ObjectProperty(None, allownone=True)
    items = ListProperty([])
    selected_item = ObjectProperty(None, allownone=True)
    hovered_item = ObjectProperty(None, allownone=True)

    # Visual encoding state
    fill_property = ObjectProperty("particle_type")
    border_property = ObjectProperty("charge")
    glow_property = ObjectProperty("mass")
    order_property = ObjectProperty("mass")

    # Whether renderers should draw inter-item connection lines (the force
    # network). A plain canvas-level flag so any domain can gate on it.
    show_connections = BooleanProperty(False)

    # Zoom/pan
    zoom_level = NumericProperty(1.0)
    pan_x = NumericProperty(0)
    pan_y = NumericProperty(0)

    # Layout state
    layout_mode = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._is_panning = False
        self._pan_start = (0, 0)
        self._pan_start_offset = (0, 0)
        self._long_press_event = None
        self._touch_start_pos = None
        self._positioned_items = []

        # Bind to size changes for re-layout
        self.bind(size=self._on_size_change)
        self.bind(items=self._on_items_change)
        self.bind(renderer=self._request_layout)
        self.bind(layout_mode=self._request_layout)
        self.bind(fill_property=self._request_redraw)
        self.bind(border_property=self._request_redraw)
        self.bind(show_connections=self._request_redraw)
        # Sort feeds the LAYOUT (sort_property in _request_layout), so it
        # needs a re-layout, not a redraw. Without this binding the Sort
        # spinner did nothing until something else relaid the canvas.
        self.bind(order_property=self._request_layout)
        self.bind(glow_property=self._request_redraw)

    def _on_size_change(self, *args):
        if self.width > 1 and self.height > 1:
            self._request_layout()

    def _on_items_change(self, *args):
        self._request_layout()

    def _request_layout(self, *args):
        """Recompute positions and redraw."""
        if not self.renderer or not self.items or self.width <= 1:
            self._positioned_items = []
            self._redraw()
            return

        self._positioned_items = self.renderer.create_layout(
            self.items,
            width=self.width,
            height=self.height,
            sort_property=self.order_property,
        )
        self._redraw()

    def _request_redraw(self, *args):
        """Redraw without recomputing layout."""
        self._redraw()

    def _redraw(self, *args):
        """Render everything onto the canvas."""
        self.canvas.clear()
        with self.canvas:
            # Dark background
            Color(20 / 255, 20 / 255, 35 / 255, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Apply pan and zoom transforms
            PushMatrix()
            Translate(self.pan_x + self.x, self.pan_y + self.y)
            Scale(self.zoom_level, self.zoom_level, 1)

        if self.renderer and self._positioned_items:
            state = {
                "fill_property": self.fill_property,
                "border_property": self.border_property,
                "glow_property": self.glow_property,
                "order_property": self.order_property,
                "selected_item": self.selected_item,
                "hovered_item": self.hovered_item,
                "show_connections": self.show_connections,
                "items": self._positioned_items,
            }
            self.renderer.draw(
                self.canvas, self._positioned_items, state,
                self.width, self.height,
            )

        with self.canvas:
            PopMatrix()

    def _screen_to_canvas(self, sx, sy):
        """Convert screen coordinates to canvas (pre-transform) coordinates."""
        cx = (sx - self.x - self.pan_x) / self.zoom_level
        cy = (sy - self.y - self.pan_y) / self.zoom_level
        return cx, cy

    # ── Touch handling ───────────────────────────────────────────────

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        touch.grab(self)
        self._touch_start_pos = touch.pos

        # Multi-touch: pinch-to-zoom
        if hasattr(touch, "is_mouse_scrolling") and touch.is_mouse_scrolling:
            self._handle_scroll(touch)
            return True

        # Check for multi-touch (pinch) via touch.uid
        if len(self._get_grabbed_touches(touch)) > 1:
            return True

        # Start potential pan
        self._is_panning = False
        self._pan_start = touch.pos
        self._pan_start_offset = (self.pan_x, self.pan_y)

        # Schedule long-press detection
        self._long_press_event = Clock.schedule_once(
            lambda dt: self._on_long_press(touch), 0.5
        )

        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False

        # Cancel long-press if moved significantly
        if self._long_press_event and self._touch_start_pos:
            dx = abs(touch.x - self._touch_start_pos[0])
            dy = abs(touch.y - self._touch_start_pos[1])
            if dx > 10 or dy > 10:
                self._long_press_event.cancel()
                self._long_press_event = None
                self._is_panning = True

        if self._is_panning:
            self.pan_x = self._pan_start_offset[0] + (touch.x - self._pan_start[0])
            self.pan_y = self._pan_start_offset[1] + (touch.y - self._pan_start[1])
            self._redraw()

        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False

        touch.ungrab(self)

        if self._long_press_event:
            self._long_press_event.cancel()
            self._long_press_event = None

        if not self._is_panning and self._touch_start_pos:
            # This was a tap — select item
            dx = abs(touch.x - self._touch_start_pos[0])
            dy = abs(touch.y - self._touch_start_pos[1])
            if dx < 10 and dy < 10:
                self._handle_tap(touch)

        self._is_panning = False
        self._touch_start_pos = None
        return True

    def _handle_tap(self, touch):
        """Handle a tap to select an item."""
        cx, cy = self._screen_to_canvas(touch.x, touch.y)
        if self.renderer and self._positioned_items:
            item = self.renderer.get_item_at(cx, cy, self._positioned_items)
            old_selected = self.selected_item
            self.selected_item = item
            if item != old_selected:
                self._redraw()

    def _on_long_press(self, touch):
        """Handle long-press for detailed info."""
        cx, cy = self._screen_to_canvas(touch.x, touch.y)
        if self.renderer and self._positioned_items:
            item = self.renderer.get_item_at(cx, cy, self._positioned_items)
            if item:
                self.selected_item = item
                self._redraw()

    def _handle_scroll(self, touch):
        """Handle mouse scroll for zooming."""
        if touch.button == "scrollup":
            factor = 1.1
        elif touch.button == "scrolldown":
            factor = 0.9
        else:
            return

        # Zoom toward cursor position
        mx, my = touch.x - self.x, touch.y - self.y
        old_zoom = self.zoom_level
        new_zoom = max(0.3, min(5.0, old_zoom * factor))

        # Adjust pan to zoom toward mouse
        self.pan_x = mx - (mx - self.pan_x) * (new_zoom / old_zoom)
        self.pan_y = my - (my - self.pan_y) * (new_zoom / old_zoom)
        self.zoom_level = new_zoom
        self._redraw()

    def _get_grabbed_touches(self, touch):
        """Get all touches currently grabbed by this widget."""
        return [touch]

    def reset_view(self):
        """Reset zoom and pan to defaults."""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._redraw()

    def refresh(self):
        """Force a full re-layout and redraw."""
        self._request_layout()
