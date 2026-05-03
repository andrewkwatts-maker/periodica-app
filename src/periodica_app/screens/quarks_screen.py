"""
Quarks screen — data-driven configuration for the Quarks domain tab.
This file is the template for all subsequent domain screens.
"""

from periodica.data.data_manager import DataCategory

from periodica_app.screens.base_screen import DomainScreen
from periodica_app.theme import DOMAIN_COLORS
from periodica_app.renderers.quark_renderers import (
    QuarkStandardRenderer,
    QuarkCircularRenderer,
    QuarkLinearRenderer,
    QuarkAlternativeRenderer,
    QuarkForceNetworkRenderer,
    QuarkMassSpiralRenderer,
    QuarkFermionBosonRenderer,
    QuarkChargeMassRenderer,
)

# Layout mode keys (matching periodica.core.quark_enums.QuarkLayoutMode names)
LAYOUT_MODES = {
    "Standard Model": "standard",
    "Circular": "circular",
    "Linear": "linear",
    "Alternative": "alternative",
    "Force Network": "force_network",
    "Mass Spiral": "mass_spiral",
    "Fermion / Boson": "fermion_boson",
    "Charge vs Mass": "charge_mass",
}

# Renderer instances for each layout mode
RENDERERS = {
    "standard": QuarkStandardRenderer(),
    "circular": QuarkCircularRenderer(),
    "linear": QuarkLinearRenderer(),
    "alternative": QuarkAlternativeRenderer(),
    "force_network": QuarkForceNetworkRenderer(),
    "mass_spiral": QuarkMassSpiralRenderer(),
    "fermion_boson": QuarkFermionBosonRenderer(),
    "charge_mass": QuarkChargeMassRenderer(),
}

# Visual encoding properties (display_name → JSON key in particle data)
PROPERTIES = {
    "Particle Type": "particle_type",
    "Mass (MeV/c²)": "Mass_MeVc2",
    "Charge (e)": "Charge_e",
    "Spin (ℏ)": "Spin_hbar",
    "Baryon Number": "BaryonNumber_B",
    "Lepton Number": "LeptonNumber_L",
    "Isospin (I)": "Isospin_I",
    "Isospin I3": "Isospin_I3",
    "Stability": "Stability",
    "Half-Life (s)": "HalfLife_s",
    "None": "none",
}

# Info panel display configuration
DISPLAY_CONFIG = [
    {
        "title": "Identity",
        "fields": [
            {"key": "Name", "label": "Name"},
            {"key": "Symbol", "label": "Symbol"},
            {"key": "Type", "label": "Type"},
        ],
    },
    {
        "title": "Properties",
        "fields": [
            {"key": "Charge_e", "label": "Charge (e)", "format": "{:.4f}"},
            {"key": "Mass_MeVc2", "label": "Mass (MeV/c²)", "format": "{:.2f}"},
            {"key": "Spin_hbar", "label": "Spin (ℏ)", "format": "{:.1f}"},
        ],
    },
    {
        "title": "Quantum Numbers",
        "fields": [
            {"key": "BaryonNumber_B", "label": "Baryon Number"},
            {"key": "LeptonNumber_L", "label": "Lepton Number"},
            {"key": "Isospin_I", "label": "Isospin (I)"},
            {"key": "Isospin_I3", "label": "Isospin I₃"},
        ],
    },
    {
        "title": "Stability & Decay",
        "fields": [
            {"key": "Stability", "label": "Stability"},
            {"key": "HalfLife_s", "label": "Half-Life (s)"},
        ],
    },
]

TOGGLES = [
    {"label": "Show Antiparticles", "key": "show_antiparticles", "default": False},
    {"label": "Show Composites", "key": "show_composites", "default": False},
    {"label": "Show Force Lines", "key": "show_connections", "default": False},
]


class QuarksScreen(DomainScreen):
    """Quarks domain screen — fully data-driven."""

    def __init__(self, **kwargs):
        super().__init__(
            domain_title="Quarks",
            accent_color=DOMAIN_COLORS["quarks"],
            data_category=DataCategory.QUARKS,
            layout_modes=LAYOUT_MODES,
            renderers=RENDERERS,
            prop_options=PROPERTIES,
            default_layout="Standard Model",
            fill_default="Particle Type",
            border_default="Charge (e)",
            glow_default="None",
            sort_default="Mass (MeV/c²)",
            toggles=TOGGLES,
            display_config=DISPLAY_CONFIG,
            **kwargs,
        )

    def _handle_toggle(self, key, value):
        """Handle quark-specific toggles."""
        if key == "show_antiparticles":
            # Reload with or without antiparticles
            self.reload_data()
        elif key == "show_composites":
            self.reload_data()
        elif key == "show_connections":
            # Just redraw
            self.ids.canvas_view.refresh()


def create_quarks_screen():
    """Factory function for lazy screen creation."""
    return QuarksScreen()
