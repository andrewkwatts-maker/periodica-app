"""
Base renderer for Kivy Canvas-based scientific visualizations.
Provides a QPainter-like API over Kivy Canvas instructions.
All domain renderers inherit from this.
"""

from abc import ABC, abstractmethod
import math

from kivy.graphics import (
    Color, Ellipse, Rectangle, Line, RoundedRectangle,
    PushMatrix, PopMatrix, Translate, Scale, Rotate,
)
from kivy.core.text import Label as CoreLabel

from periodica_app.utils.color_utils import lerp_color


class BaseRenderer(ABC):
    """
    Abstract base class for layout renderers.
    Subclasses implement create_layout() and draw().
    """

    def __init__(self):
        self._text_cache = {}

    @abstractmethod
    def create_layout(self, items, width, height, **kwargs):
        """
        Position items within the given dimensions.

        Args:
            items: List of data dictionaries
            width: Available width in pixels
            height: Available height in pixels
            **kwargs: Layout-specific parameters

        Returns:
            List of items with added 'x', 'y', 'display_size' keys.
            Original item data is merged into each positioned dict.
        """
        pass

    @staticmethod
    def merge_positions(original_items, positioned_items):
        """
        Merge original item data into positioned items from layout_math.
        layout_math returns {x, y, w, h, label, color_rgb, metadata}
        but renderers need access to the original data fields (Name, Mass_MeVc2, etc.)
        """
        # Build lookup from label/name to original item
        by_label = {}
        by_name = {}
        for item in original_items:
            symbol = item.get("Symbol", item.get("symbol", ""))
            name = item.get("Name", item.get("name", ""))
            if symbol:
                by_label[symbol] = item
            if name:
                by_name[name] = item

        merged = []
        for pos in positioned_items:
            # Start with the original data
            label = pos.get("label", "")
            meta_name = pos.get("metadata", {}).get("name", "")
            original = by_label.get(label) or by_name.get(meta_name) or {}

            # Merge: original data as base, position data on top
            result = dict(original)
            result["x"] = pos.get("x", 0)
            result["y"] = pos.get("y", 0)
            result["w"] = pos.get("w", 60)
            result["h"] = pos.get("h", 60)
            result["display_size"] = pos.get("w", 60)
            result["label"] = label
            result["color_rgb"] = pos.get("color_rgb", (150, 150, 150))
            # Preserve any extra metadata
            meta = pos.get("metadata", {})
            result["in_layout"] = meta.get("in_layout", True)
            merged.append(result)

        return merged

    @abstractmethod
    def draw(self, canvas, items, state, width, height):
        """
        Render items onto a Kivy Canvas.

        Args:
            canvas: Kivy Canvas object
            items: List of positioned item dicts (from create_layout)
            state: Dict with visualization state (fill_property, selected_item, etc.)
            width: Widget width
            height: Widget height
        """
        pass

    def get_item_at(self, x, y, items):
        """
        Hit-test: find which item contains the point (x, y).
        Default implementation checks circular bounds.

        Args:
            x, y: Point coordinates (in widget space, y=0 at bottom)

        Returns:
            Item dict or None
        """
        for item in reversed(items):
            ix = item.get("x", 0)
            iy = item.get("y", 0)
            size = item.get("display_size", 40)
            half = size / 2
            if abs(x - ix) <= half and abs(y - iy) <= half:
                return item
        return None

    # ── Drawing helpers ──────────────────────────────────────────────

    def draw_circle(self, canvas, x, y, radius, color, outline_color=None, outline_width=1):
        """Draw a filled circle with optional outline."""
        with canvas:
            Color(*color)
            Ellipse(pos=(x - radius, y - radius), size=(radius * 2, radius * 2))
            if outline_color:
                Color(*outline_color)
                Line(ellipse=(x - radius, y - radius, radius * 2, radius * 2),
                     width=outline_width)

    def draw_rounded_rect(self, canvas, x, y, w, h, color, radius=8,
                          outline_color=None, outline_width=1):
        """Draw a filled rounded rectangle."""
        with canvas:
            Color(*color)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[radius])
            if outline_color:
                Color(*outline_color)
                Line(rounded_rectangle=(x, y, w, h, radius), width=outline_width)

    def draw_rect(self, canvas, x, y, w, h, color):
        """Draw a filled rectangle."""
        with canvas:
            Color(*color)
            Rectangle(pos=(x, y), size=(w, h))

    def draw_text(self, canvas, x, y, text, font_size=14, color=(1, 1, 1, 1),
                  anchor_x="center", anchor_y="center", bold=False):
        """
        Draw text at position using CoreLabel texture.
        (x, y) is the anchor point; anchor_x/anchor_y control alignment.
        """
        cache_key = (text, font_size, color, bold)
        if cache_key not in self._text_cache:
            label = CoreLabel(
                text=str(text),
                font_size=font_size,
                color=color,
                bold=bold,
            )
            label.refresh()
            self._text_cache[cache_key] = label.texture
            if len(self._text_cache) > 500:
                # Evict oldest entries
                keys = list(self._text_cache.keys())
                for k in keys[:100]:
                    del self._text_cache[k]

        texture = self._text_cache[cache_key]
        tw, th = texture.size

        # Compute draw position from anchor
        if anchor_x == "center":
            dx = x - tw / 2
        elif anchor_x == "right":
            dx = x - tw
        else:
            dx = x

        if anchor_y == "center":
            dy = y - th / 2
        elif anchor_y == "top":
            dy = y - th
        else:
            dy = y

        with canvas:
            Color(1, 1, 1, color[3] if len(color) > 3 else 1.0)
            Rectangle(texture=texture, pos=(dx, dy), size=texture.size)

    def draw_line(self, canvas, points, color, width=1):
        """Draw a line through a list of points [x1, y1, x2, y2, ...]."""
        with canvas:
            Color(*color)
            Line(points=points, width=width)

    def draw_glow(self, canvas, x, y, radius, color, layers=3):
        """Draw a glow effect using layered transparent circles."""
        for i in range(layers, 0, -1):
            alpha = color[3] * (0.15 / i) if len(color) > 3 else 0.15 / i
            r = radius * (1 + 0.4 * i)
            glow_color = (color[0], color[1], color[2], alpha)
            with canvas:
                Color(*glow_color)
                Ellipse(pos=(x - r, y - r), size=(r * 2, r * 2))

    def clear_text_cache(self):
        """Clear the text texture cache."""
        self._text_cache.clear()
