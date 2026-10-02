"""Typed, validated specs for the generic ControlDrawer sections.

Pure Python (no Kivy) so configs are checked by tier-A tests.  A config dict
may carry these sections, each a list of mappings:

    "spinners":  [{"key", "label", "values", "default"?}]
    "segmented": [{"key", "label", "options", "default"?}]
    "sliders":   [{"key", "label", "min", "max", "default"?, "step"?, "format"?}]
    "buttons":   [{"key", "label"}]

Every control reports changes as ``on_control(key, value)``; buttons report
``value=None``.  Keys must be unique across all generic sections.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class ControlSpecError(ValueError):
    """A drawer config section is malformed."""


def _require(spec: Mapping[str, Any], field: str, section: str):
    if field not in spec:
        raise ControlSpecError(f"{section} entry {dict(spec)!r} is missing '{field}'")
    return spec[field]


def _choices(spec: Mapping[str, Any], field: str, section: str) -> tuple[str, ...]:
    values = tuple(str(v) for v in _require(spec, field, section))
    if not values:
        raise ControlSpecError(f"{section} '{spec.get('key')}' has no {field}")
    if len(set(values)) != len(values):
        raise ControlSpecError(f"{section} '{spec.get('key')}' repeats a value in {field}")
    return values


def _default_choice(spec: Mapping[str, Any], choices: Sequence[str], section: str) -> str:
    default = str(spec.get("default", choices[0]))
    if default not in choices:
        raise ControlSpecError(
            f"{section} '{spec['key']}' default {default!r} is not one of {list(choices)}"
        )
    return default


@dataclass(frozen=True)
class SpinnerSpec:
    key: str
    label: str
    values: tuple[str, ...]
    default: str

    @classmethod
    def from_mapping(cls, spec: Mapping[str, Any]) -> "SpinnerSpec":
        values = _choices(spec, "values", "spinner")
        return cls(
            key=str(_require(spec, "key", "spinner")),
            label=str(spec.get("label", spec["key"])),
            values=values,
            default=_default_choice(spec, values, "spinner"),
        )


@dataclass(frozen=True)
class SegmentedSpec:
    """Mutually exclusive options shown side by side (radio behaviour)."""

    key: str
    label: str
    options: tuple[str, ...]
    default: str

    @classmethod
    def from_mapping(cls, spec: Mapping[str, Any]) -> "SegmentedSpec":
        options = _choices(spec, "options", "segmented")
        return cls(
            key=str(_require(spec, "key", "segmented")),
            label=str(spec.get("label", spec["key"])),
            options=options,
            default=_default_choice(spec, options, "segmented"),
        )


@dataclass(frozen=True)
class SliderSpec:
    key: str
    label: str
    min: float
    max: float
    default: float
    step: float = 0.0  # 0 = continuous
    format: str = "{:.3g}"

    @classmethod
    def from_mapping(cls, spec: Mapping[str, Any]) -> "SliderSpec":
        key = str(_require(spec, "key", "slider"))
        lo = float(_require(spec, "min", "slider"))
        hi = float(_require(spec, "max", "slider"))
        if not (math.isfinite(lo) and math.isfinite(hi)) or lo >= hi:
            raise ControlSpecError(f"slider '{key}' needs finite min < max, got {lo}..{hi}")
        default = float(spec.get("default", lo))
        if not lo <= default <= hi:
            raise ControlSpecError(f"slider '{key}' default {default} outside {lo}..{hi}")
        step = float(spec.get("step", 0.0))
        if step < 0 or step > hi - lo:
            raise ControlSpecError(f"slider '{key}' step {step} invalid for {lo}..{hi}")
        fmt = str(spec.get("format", "{:.3g}"))
        try:
            fmt.format(default)
        except (ValueError, IndexError, KeyError) as exc:
            raise ControlSpecError(f"slider '{key}' format {fmt!r}: {exc}") from exc
        return cls(key=key, label=str(spec.get("label", key)), min=lo, max=hi,
                   default=default, step=step, format=fmt)

    def snap(self, value: float) -> float:
        """Clamp to [min, max] and round to the step grid anchored at min."""
        value = min(self.max, max(self.min, float(value)))
        if self.step:
            value = self.min + round((value - self.min) / self.step) * self.step
            value = min(self.max, value)
        return value

    def display(self, value: float) -> str:
        return self.format.format(value)


@dataclass(frozen=True)
class ButtonSpec:
    key: str
    label: str

    @classmethod
    def from_mapping(cls, spec: Mapping[str, Any]) -> "ButtonSpec":
        key = str(_require(spec, "key", "button"))
        return cls(key=key, label=str(spec.get("label", key.replace("_", " ").title())))


SECTION_SPECS = {
    "spinners": SpinnerSpec,
    "segmented": SegmentedSpec,
    "sliders": SliderSpec,
    "buttons": ButtonSpec,
}


def parse_generic_sections(config: Mapping[str, Any]) -> dict[str, list]:
    """Validate and type every generic section present in ``config``.

    Returns ``{section_name: [spec, ...]}`` for the sections present, in
    ``SECTION_SPECS`` order.  Raises ControlSpecError on malformed input or a
    key used twice.
    """
    parsed: dict[str, list] = {}
    seen: set[str] = set()
    for section, spec_cls in SECTION_SPECS.items():
        entries = config.get(section)
        if entries is None:
            continue
        specs = [spec_cls.from_mapping(entry) for entry in entries]
        for spec in specs:
            if spec.key in seen:
                raise ControlSpecError(f"control key '{spec.key}' is used more than once")
            seen.add(spec.key)
        parsed[section] = specs
    return parsed


def initial_values(parsed: Mapping[str, list]) -> dict[str, Any]:
    """The value every stateful control starts with (buttons have none)."""
    values: dict[str, Any] = {}
    for specs in parsed.values():
        for spec in specs:
            if not isinstance(spec, ButtonSpec):
                values[spec.key] = spec.default
    return values
