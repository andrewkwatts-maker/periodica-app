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
            # particle_type_name comes from the enriching loader; the raw
            # "Type" field is the constant "Subatomic Particle" for every item.
            {"key": "particle_type_name", "label": "Type"},
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


def _load_enriched_quarks(screen):
    """Load particles through the enriching QuarkDataLoader.

    The generic DataManager path returns raw JSON with no sm_row/sm_col/
    particle_type, so quark_standard.compute_positions dropped every particle
    into the off-screen non-SM fallback -- the default "Standard Model" view
    did not render as a Standard Model table. The loader's _process_particle
    adds those fields, and its include flags are what make the antiparticle /
    composite toggles actually change the loaded data.
    """
    from periodica.data.quark_loader import get_quark_loader

    return get_quark_loader().load_all_particles(
        include_antiparticles=screen.toggle_state("show_antiparticles"),
        include_composite=screen.toggle_state("show_composites"),
    )


class QuarksScreen(DomainScreen):
    """Quarks domain screen — fully data-driven."""

    def __init__(self, **kwargs):
        super().__init__(
            data_loader=_load_enriched_quarks,
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
        if key in ("show_antiparticles", "show_composites"):
            # The enriching loader reads toggle_state, so a reload now loads
            # genuinely different data (it previously re-fetched the same set).
            self.reload_data()
        elif key == "show_connections":
            # The renderer gates force lines on this canvas property.
            self.ids.canvas_view.show_connections = value


def create_quarks_screen():
    """Factory function for lazy screen creation."""
    return QuarksScreen()
