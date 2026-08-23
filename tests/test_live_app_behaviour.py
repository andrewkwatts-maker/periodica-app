"""Tests for the live Kivy app — the first to cover any shipping code.

The previous suite was three dead Qt-era files: 76 tests importing PySide6 and
a `ui` package that no longer exists (every failure in the suite came from
them), one file that skipped wholesale, and one that pytest collected zero
items from. All deleted. These tests target the defects actually fixed:

  * the flagship Standard Model layout rendered off-screen because the screen
    loaded RAW JSON with no sm_row/sm_col/particle_type enrichment
  * the antiparticle/composite toggles reloaded identical data
  * gradient colouring used a hardcoded 0..1 range, so real properties
    (mass: 0.5 to ~173,000 MeV) saturated every particle to the end colour
  * force lines drew unconditionally, ignoring the "Show Force Lines" toggle
"""
from __future__ import annotations

import os

os.environ.setdefault("KIVY_NO_ARGS", "1")

import pytest


# ── the enriching loader (the flagship fix) ──────────────────────────────────


def test_enriched_loader_supplies_standard_model_fields():
    """quark_loader adds sm_row/sm_col/particle_type; DataManager does not.

    quark_standard.compute_positions branches on sm_row >= 0. Raw JSON has no
    such key, so every particle failed the test and fell into the off-screen
    non-SM fallback -- the "Standard Model" default view was not a Standard
    Model table. The enriching loader is what the screen must use.
    """
    from periodica.data.quark_loader import get_quark_loader

    items = get_quark_loader().load_all_particles(
        include_antiparticles=False, include_composite=False
    )
    assert items, "loader returned nothing"
    placed = [p for p in items if p.get("sm_row", -1) >= 0]
    assert len(placed) >= 12, (
        f"only {len(placed)} particles carry an sm_row grid position"
    )
    assert all("particle_type" in p for p in items)


def test_raw_datamanager_items_lack_the_fields_the_layout_needs():
    """Documents the bug: the generic path returns un-enriched JSON."""
    from periodica.data.data_manager import DataCategory, get_data_manager

    raw = get_data_manager().get_all_items(DataCategory.QUARKS)
    raw_items = list(raw.values()) if isinstance(raw, dict) else list(raw)
    assert raw_items, "no raw items -- cannot demonstrate anything"
    assert all("sm_row" not in d for d in raw_items), (
        "raw items now carry sm_row; the enriching-loader workaround may be "
        "removable"
    )


def test_antiparticle_toggle_changes_what_is_loaded():
    """include_antiparticles must change the dataset, not re-fetch it."""
    from periodica.data.quark_loader import QuarkDataLoader

    loader = QuarkDataLoader()
    without = loader.load_all_particles(
        include_antiparticles=False, include_composite=False
    )
    with_ap = loader.load_all_particles(
        include_antiparticles=True, include_composite=False
    )
    assert len(with_ap) > len(without), (
        "antiparticle toggle loads an identical dataset"
    )


def test_standard_layout_positions_enriched_particles_in_a_grid():
    """Enriched particles land on multiple distinct grid rows."""
    from periodica.data.quark_loader import get_quark_loader
    from periodica.layout_math import quark_standard

    items = get_quark_loader().load_all_particles(
        include_antiparticles=False, include_composite=False
    )
    positioned = quark_standard.compute_positions(items, 1200, 800)
    assert positioned, "layout produced nothing"
    rows = {round(p["y"], 1) for p in positioned}
    assert len(rows) >= 3, (
        f"all particles collapsed onto {len(rows)} row(s) -- the non-SM "
        "fallback symptom"
    )


# ── gradient range (hardcoded 0..1 bug) ──────────────────────────────────────


def test_property_range_is_data_driven():
    from periodica_app.renderers.quark_renderers import _property_range

    items = [{"m": 0.5}, {"m": 173000.0}, {"m": 4.18}]
    assert _property_range(items, "m") == (0.5, 173000.0)


def test_property_range_handles_degenerate_inputs():
    from periodica_app.renderers.quark_renderers import _property_range

    assert _property_range([], "m") == (0.0, 1.0)
    lo, hi = _property_range([{"m": 7.0}, {"m": 7.0}], "m")
    assert lo < 7.0 < hi, "identical values must not produce a zero-width range"
    # booleans are ints in Python; they must not poison a numeric range
    assert _property_range([{"m": True}, {"m": 2.0}, {"m": 8.0}], "m") == (2.0, 8.0)


def test_fill_color_spans_the_gradient_over_real_masses():
    """With data-driven ranges, min and max of a property differ in colour.

    Under the old hardcoded 0..1 range both 0.5 MeV and 173,000 MeV clamped to
    the same end colour -- the encoding carried no information.
    """
    from periodica_app.renderers.quark_renderers import _get_fill_color

    items = [{"Name": "light", "m": 0.5}, {"Name": "heavy", "m": 173000.0}]
    state = {"fill_property": "m", "items": items}
    light = _get_fill_color(items[0], state)
    heavy = _get_fill_color(items[1], state)
    assert light != heavy, "min and max of the range render identically"
    # endpoints of the configured gradient: blue-ish start, red-ish end
    assert light[2] > light[0], "minimum should sit at the blue start"
    assert heavy[0] > heavy[2], "maximum should sit at the red end"


# ── force-line gating ────────────────────────────────────────────────────────


def test_force_lines_respect_the_toggle(monkeypatch):
    """draw() must consult show_connections; it previously never did."""
    import periodica_app.renderers.quark_renderers as qr

    monkeypatch.setattr(qr, "_draw_particle", lambda *a, **k: None)
    renderer = qr.QuarkForceNetworkRenderer()
    calls = []
    monkeypatch.setattr(
        renderer, "_draw_force_lines", lambda *a, **k: calls.append(1)
    )

    items = [{"Name": "a"}, {"Name": "b"}]
    renderer.draw(None, items, {"show_connections": False}, 800, 600)
    assert not calls, "force lines drawn with the toggle off"
    renderer.draw(None, items, {"show_connections": True}, 800, 600)
    assert calls, "force lines not drawn with the toggle on"


# ── screen-side toggle state ─────────────────────────────────────────────────


def test_domain_screen_records_toggle_state():
    """_on_action must record the value BEFORE dispatching, so a loader
    reading toggle_state() during the resulting reload sees the new value."""
    from periodica_app.screens.base_screen import DomainScreen

    screen = DomainScreen.__new__(DomainScreen)  # no Kivy init needed
    screen._toggle_state = {"show_antiparticles": False}
    seen = []
    screen._handle_toggle = lambda k, v: seen.append(
        screen.toggle_state("show_antiparticles")
    )
    DomainScreen._on_action(screen, "toggle_show_antiparticles", True)
    assert seen == [True], "handler ran before the state was recorded"
