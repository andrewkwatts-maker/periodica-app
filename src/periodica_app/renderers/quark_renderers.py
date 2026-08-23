"""
Quark layout renderers for Kivy Canvas.
Each renderer delegates position computation to periodica.layout_math
and handles only the drawing.
"""

import math

from kivy.graphics import Color, Ellipse, Rectangle, Line, RoundedRectangle
from kivy.core.text import Label as CoreLabel

from periodica.layout_math import (
    quark_standard, quark_circular, quark_linear, quark_alternative,
    quark_force_network, quark_mass_spiral, quark_fermion_boson,
    quark_charge_mass,
)

from periodica_app.renderers.base_renderer import BaseRenderer
from periodica_app.theme import (
    PARTICLE_TYPE_COLORS, TEXT_PRIMARY, BG_CARD, ACCENT_INFO,
    hex_to_rgba,
)
from periodica_app.utils.color_utils import (
    lerp_color, value_to_gradient_color, get_property_color,
)


# ── Shared particle drawing ─────────────────────────────────────────

def _get_particle_type(item):
    """Extract a simple particle type string from Classification list."""
    cls = item.get("Classification", [])
    if isinstance(cls, list):
        for c in cls:
            cl = c.lower()
            if "quark" in cl:
                return "quark"
            if "lepton" in cl:
                return "lepton"
            if "scalar" in cl:
                return "scalar_boson"
            if "gauge" in cl or "boson" in cl:
                return "gauge_boson"
    return "composite"


def _property_range(items, prop):
    """(min, max) of a numeric property across the drawn items.

    The gradient previously used a hardcoded 0..1 range, so any real-world
    property (mass runs 0.5 to ~173,000 MeV) saturated every particle to the
    end colour. Ranges must come from the data being drawn.
    """
    values = [
        v for v in (item.get(prop) for item in items)
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]
    if not values:
        return (0.0, 1.0)
    lo, hi = min(values), max(values)
    if lo == hi:  # all identical: keep the gradient midpoint stable
        return (lo - 0.5, hi + 0.5)
    return (lo, hi)


def _get_fill_color(item, state):
    """Get fill color for an item based on state fill_property."""
    fill_prop = state.get("fill_property", "particle_type")

    if fill_prop == "particle_type":
        ptype = _get_particle_type(item)
        return PARTICLE_TYPE_COLORS.get(ptype, (0.5, 0.5, 0.5, 1))

    # Numeric property — gradient over the DATA range, not a fixed 0..1
    value = item.get(fill_prop)
    if value is None:
        return (0.4, 0.4, 0.5, 1)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        lo, hi = _property_range(state.get("items", []), fill_prop)
        return value_to_gradient_color(
            value, lo, hi,
            start_color=(0.2, 0.3, 0.8, 1),
            end_color=(0.9, 0.2, 0.2, 1),
        )

    return PARTICLE_TYPE_COLORS.get(str(value).lower(), (0.5, 0.5, 0.5, 1))


def _draw_particle(renderer, canvas, item, state):
    """
    Draw a single particle cell on the Kivy canvas.
    Common drawing logic for all quark layout modes.
    """
    x = item.get("x", 0)
    y = item.get("y", 0)
    size = item.get("w", item.get("display_size", 60))
    half = size / 2

    fill_color = _get_fill_color(item, state)
    is_selected = (state.get("selected_item") is not None and
                   item.get("Name") == state["selected_item"].get("Name"))
    is_hovered = (state.get("hovered_item") is not None and
                  item.get("Name") == state["hovered_item"].get("Name"))

    # Glow for selected
    if is_selected:
        renderer.draw_glow(canvas, x, y, half * 1.3, ACCENT_INFO, layers=4)

    # Main cell — rounded rect
    cell_x = x - half
    cell_y = y - half

    # Darken fill slightly for the card background
    card_bg = (fill_color[0] * 0.3, fill_color[1] * 0.3, fill_color[2] * 0.3, 0.9)
    renderer.draw_rounded_rect(canvas, cell_x, cell_y, size, size, card_bg, radius=8)

    # Color accent bar at top
    bar_h = size * 0.08
    with canvas:
        Color(*fill_color)
        RoundedRectangle(
            pos=(cell_x + 2, cell_y + size - bar_h - 2),
            size=(size - 4, bar_h),
            radius=[4, 4, 0, 0],
        )

    # Symbol text (large, center)
    symbol = item.get("Symbol", item.get("label", "?"))
    renderer.draw_text(
        canvas, x, y + size * 0.05,
        symbol,
        font_size=max(10, int(size * 0.3)),
        color=fill_color,
        bold=True,
    )

    # Name text (small, below symbol)
    name = item.get("Name", "")
    if size > 45:
        # Truncate long names
        display_name = name[:12] + "..." if len(name) > 12 else name
        renderer.draw_text(
            canvas, x, y - size * 0.2,
            display_name,
            font_size=max(8, int(size * 0.14)),
            color=TEXT_PRIMARY,
        )

    # Mass text (tiny, bottom)
    mass = item.get("Mass_MeVc2")
    if mass is not None and size > 55:
        if mass >= 1000:
            mass_str = f"{mass / 1000:.1f} GeV"
        elif mass >= 1:
            mass_str = f"{mass:.1f} MeV"
        else:
            mass_str = f"{mass:.4f} MeV"
        renderer.draw_text(
            canvas, x, y - size * 0.35,
            mass_str,
            font_size=max(7, int(size * 0.11)),
            color=(1, 1, 1, 0.5),
        )

    # Selection outline
    if is_selected:
        renderer.draw_rounded_rect(
            canvas, cell_x - 2, cell_y - 2, size + 4, size + 4,
            (0, 0, 0, 0), radius=10,
            outline_color=ACCENT_INFO, outline_width=2,
        )
    elif is_hovered:
        renderer.draw_rounded_rect(
            canvas, cell_x - 1, cell_y - 1, size + 2, size + 2,
            (0, 0, 0, 0), radius=9,
            outline_color=(1, 1, 1, 0.3), outline_width=1,
        )


# ── Layout Renderers ─────────────────────────────────────────────────

class QuarkStandardRenderer(BaseRenderer):
    """Standard Model grid layout."""

    def create_layout(self, items, width, height, **kwargs):
        positioned = quark_standard.compute_positions(items, width, height)
        return self.merge_positions(items, positioned)

    def draw(self, canvas, items, state, width, height):
        # Draw section backgrounds
        self._draw_sections(canvas, items, width, height)
        # Draw particles
        for item in items:
            _draw_particle(self, canvas, item, state)

    def _draw_sections(self, canvas, items, width, height):
        """Draw colored section backgrounds for quark/lepton/boson groups."""
        sections = {}
        for item in items:
            ptype = _get_particle_type(item)
            if ptype not in sections:
                sections[ptype] = {"min_x": float("inf"), "min_y": float("inf"),
                                   "max_x": 0, "max_y": 0}
            s = item.get("w", 60)
            x, y = item.get("x", 0), item.get("y", 0)
            sections[ptype]["min_x"] = min(sections[ptype]["min_x"], x - s / 2)
            sections[ptype]["min_y"] = min(sections[ptype]["min_y"], y - s / 2)
            sections[ptype]["max_x"] = max(sections[ptype]["max_x"], x + s / 2)
            sections[ptype]["max_y"] = max(sections[ptype]["max_y"], y + s / 2)

        for ptype, bounds in sections.items():
            color = PARTICLE_TYPE_COLORS.get(ptype, (0.5, 0.5, 0.5, 1))
            bg = (color[0], color[1], color[2], 0.08)
            pad = 10
            self.draw_rounded_rect(
                canvas,
                bounds["min_x"] - pad, bounds["min_y"] - pad,
                bounds["max_x"] - bounds["min_x"] + 2 * pad,
                bounds["max_y"] - bounds["min_y"] + 2 * pad,
                bg, radius=12,
            )


class QuarkCircularRenderer(BaseRenderer):
    """Concentric ring layout."""

    def create_layout(self, items, width, height, **kwargs):
        positioned = quark_circular.compute_positions(items, width, height)
        return self.merge_positions(items, positioned)

    def draw(self, canvas, items, state, width, height):
        # Draw ring guides
        cx, cy = width / 2, height / 2
        for ratio in [0.25, 0.55, 0.85]:
            r = min(width, height) / 2 * ratio
            self.draw_circle(
                canvas, cx, cy, r, (0, 0, 0, 0),
                outline_color=(1, 1, 1, 0.1), outline_width=1,
            )
        for item in items:
            _draw_particle(self, canvas, item, state)


class QuarkLinearRenderer(BaseRenderer):
    """Linear sorted layout."""

    def create_layout(self, items, width, height, **kwargs):
        sort_prop = kwargs.get("sort_property", "Mass_MeVc2")
        positioned = quark_linear.compute_positions(
            items, width, height, sort_property=sort_prop,
        )
        return self.merge_positions(items, positioned)

    def draw(self, canvas, items, state, width, height):
        # Draw axis line
        if items:
            margin = 60
            self.draw_line(
                canvas,
                [margin, height / 2, width - margin, height / 2],
                (1, 1, 1, 0.15), width=1,
            )
        for item in items:
            _draw_particle(self, canvas, item, state)


class QuarkAlternativeRenderer(BaseRenderer):
    """Alternative grouped layout."""

    def create_layout(self, items, width, height, **kwargs):
        positioned = quark_alternative.compute_positions(items, width, height)
        return self.merge_positions(items, positioned)

    def draw(self, canvas, items, state, width, height):
        for item in items:
            _draw_particle(self, canvas, item, state)


class QuarkForceNetworkRenderer(BaseRenderer):
    """Force interaction network layout."""

    def create_layout(self, items, width, height, **kwargs):
        positioned = quark_force_network.compute_positions(items, width, height)
        return self.merge_positions(items, positioned)

    def draw(self, canvas, items, state, width, height):
        # Force lines are opt-in ("Show Force Lines" toggle). The O(n^2)
        # pairwise pass previously drew unconditionally, ignoring the toggle.
        if state.get("show_connections"):
            self._draw_force_lines(canvas, items)
        for item in items:
            _draw_particle(self, canvas, item, state)

    def _draw_force_lines(self, canvas, items):
        """Draw lines between particles that share interaction forces."""
        from periodica_app.theme import FORCE_COLORS
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                a_forces = set(a.get("InteractionForces", []))
                b_forces = set(b.get("InteractionForces", []))
                shared = a_forces & b_forces
                if shared:
                    force = list(shared)[0]
                    color = FORCE_COLORS.get(force.lower(), (0.5, 0.5, 0.5, 0.15))
                    line_color = (color[0], color[1], color[2], 0.12)
                    self.draw_line(
                        canvas,
                        [a["x"], a["y"], b["x"], b["y"]],
                        line_color, width=1,
                    )


class QuarkMassSpiralRenderer(BaseRenderer):
    """Mass-based spiral layout."""

    def create_layout(self, items, width, height, **kwargs):
        positioned = quark_mass_spiral.compute_positions(items, width, height)
        return self.merge_positions(items, positioned)

    def draw(self, canvas, items, state, width, height):
        for item in items:
            _draw_particle(self, canvas, item, state)


class QuarkFermionBosonRenderer(BaseRenderer):
    """Fermion/Boson split layout."""

    def create_layout(self, items, width, height, **kwargs):
        positioned = quark_fermion_boson.compute_positions(items, width, height)
        return self.merge_positions(items, positioned)

    def draw(self, canvas, items, state, width, height):
        # Draw dividing line
        self.draw_line(
            canvas,
            [width / 2, 30, width / 2, height - 30],
            (1, 1, 1, 0.1), width=1,
        )
        # Section labels
        self.draw_text(canvas, width * 0.25, height - 20, "Fermions",
                       font_size=14, color=(1, 1, 1, 0.5))
        self.draw_text(canvas, width * 0.75, height - 20, "Bosons",
                       font_size=14, color=(1, 1, 1, 0.5))
        for item in items:
            _draw_particle(self, canvas, item, state)


class QuarkChargeMassRenderer(BaseRenderer):
    """Charge vs Mass 2D scatter layout."""

    def create_layout(self, items, width, height, **kwargs):
        positioned = quark_charge_mass.compute_positions(items, width, height)
        return self.merge_positions(items, positioned)

    def draw(self, canvas, items, state, width, height):
        # Draw axes
        margin = 60
        # Y axis (charge)
        self.draw_line(canvas, [margin, margin, margin, height - margin],
                       (1, 1, 1, 0.2), width=1)
        self.draw_text(canvas, margin - 5, height / 2, "Charge",
                       font_size=11, color=(1, 1, 1, 0.4), anchor_x="right")
        # X axis (mass)
        self.draw_line(canvas, [margin, margin, width - margin, margin],
                       (1, 1, 1, 0.2), width=1)
        self.draw_text(canvas, width / 2, margin - 15, "Mass",
                       font_size=11, color=(1, 1, 1, 0.4))

        for item in items:
            _draw_particle(self, canvas, item, state)
