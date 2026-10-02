"""Tier A: validation of the generic ControlDrawer sections."""
from __future__ import annotations

import pytest

from periodica_app.widgets.control_specs import (
    ButtonSpec, ControlSpecError, SegmentedSpec, SliderSpec, SpinnerSpec,
    initial_values, parse_generic_sections,
)

SCENE_CONFIG = {
    "spinners": [{"key": "state", "label": "State", "values": ["1s", "2s", "2p"],
                  "default": "2s"}],
    "segmented": [{"key": "mode", "label": "Mode",
                   "options": ["Real-time", "Averaged", "Step", "Collapse"],
                   "default": "Averaged"}],
    "sliders": [{"key": "kappa", "label": "κ", "min": 0.0, "max": 10.0,
                 "default": 3.0, "step": 0.5, "format": "{:.1f}"}],
    "buttons": [{"key": "reset_camera", "label": "Reset camera"}],
}


def test_full_config_parses_in_section_order():
    parsed = parse_generic_sections(SCENE_CONFIG)
    assert list(parsed) == ["spinners", "segmented", "sliders", "buttons"]
    assert parsed["spinners"] == [SpinnerSpec("state", "State", ("1s", "2s", "2p"), "2s")]
    assert parsed["segmented"][0] == SegmentedSpec(
        "mode", "Mode", ("Real-time", "Averaged", "Step", "Collapse"), "Averaged")
    assert parsed["buttons"] == [ButtonSpec("reset_camera", "Reset camera")]


def test_initial_values_cover_stateful_controls_only():
    values = initial_values(parse_generic_sections(SCENE_CONFIG))
    assert values == {"state": "2s", "mode": "Averaged", "kappa": 3.0}


def test_domain_only_config_has_no_generic_sections():
    quarks_like = {"layout_modes": {"Standard Model": "standard"},
                   "toggles": [{"key": "x", "label": "X"}], "actions": ["add"]}
    assert parse_generic_sections(quarks_like) == {}


def test_defaults_fall_back_to_the_first_choice_and_minimum():
    parsed = parse_generic_sections({
        "spinners": [{"key": "a", "values": ["x", "y"]}],
        "sliders": [{"key": "s", "min": -1, "max": 1}],
        "buttons": [{"key": "go_now"}],
    })
    assert parsed["spinners"][0].default == "x"
    assert parsed["spinners"][0].label == "a"
    assert parsed["sliders"][0].default == -1.0
    assert parsed["buttons"][0].label == "Go Now"


@pytest.mark.parametrize("bad", [
    {"spinners": [{"label": "no key", "values": ["a"]}]},
    {"spinners": [{"key": "a", "values": []}]},
    {"spinners": [{"key": "a", "values": ["x", "x"]}]},
    {"segmented": [{"key": "m", "options": ["a", "b"], "default": "c"}]},
    {"sliders": [{"key": "s", "min": 1.0, "max": 1.0}]},
    {"sliders": [{"key": "s", "min": 0.0, "max": float("inf")}]},
    {"sliders": [{"key": "s", "min": 0.0, "max": 1.0, "default": 2.0}]},
    {"sliders": [{"key": "s", "min": 0.0, "max": 1.0, "step": -0.1}]},
    {"sliders": [{"key": "s", "min": 0.0, "max": 1.0, "format": "{:q}"}]},
    {"spinners": [{"key": "dup", "values": ["a"]}], "buttons": [{"key": "dup"}]},
])
def test_malformed_sections_are_rejected(bad):
    with pytest.raises(ControlSpecError):
        parse_generic_sections(bad)


def test_slider_snaps_to_its_grid_and_range():
    spec = SliderSpec.from_mapping({"key": "s", "min": 0.25, "max": 1.0, "step": 0.25})
    assert spec.snap(0.6) == pytest.approx(0.5)
    assert spec.snap(0.9) == pytest.approx(1.0)
    assert spec.snap(5.0) == 1.0
    assert spec.snap(-5.0) == 0.25
    continuous = SliderSpec.from_mapping({"key": "c", "min": 0, "max": 1})
    assert continuous.snap(0.123) == 0.123


def test_slider_display_uses_its_format():
    spec = SliderSpec.from_mapping({"key": "s", "min": 0, "max": 1, "format": "{:.2f}"})
    assert spec.display(0.5) == "0.50"
