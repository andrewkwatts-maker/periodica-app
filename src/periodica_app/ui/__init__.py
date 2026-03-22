"""UI components for the periodic table application."""

from periodica_app.ui.components import (ColorGradientBar, BorderThicknessLegend,
                           GlowIntensityLegend, InnerRingLegend)
from periodica_app.ui.control_panel import ControlPanel
from periodica_app.ui.spectroscopy_panel import SpectroscopyPanel
from periodica_app.ui.molecule_control_panel import MoleculeControlPanel
from periodica_app.ui.molecule_info_panel import MoleculeInfoPanel

# Quark UI components
from periodica_app.ui.quark_control_panel import QuarkControlPanel
from periodica_app.ui.quark_info_panel import QuarkInfoPanel

# Subatomic UI components
from periodica_app.ui.subatomic_control_panel import SubatomicControlPanel
from periodica_app.ui.subatomic_info_panel import SubatomicInfoPanel

# Data management dialogs
from periodica_app.ui.data_editor_dialog import DataEditorDialog, DataListDialog
from periodica_app.ui.creation_dialog import (
    AtomCreationDialog, SubatomicCreationDialog, MoleculeCreationDialog,
    open_atom_creation_dialog, open_subatomic_creation_dialog, open_molecule_creation_dialog
)

__all__ = [
    'ColorGradientBar',
    'BorderThicknessLegend',
    'GlowIntensityLegend',
    'InnerRingLegend',
    'ControlPanel',
    'SpectroscopyPanel',
    'MoleculeControlPanel',
    'MoleculeInfoPanel',
    # Quark exports
    'QuarkControlPanel',
    'QuarkInfoPanel',
    # Subatomic exports
    'SubatomicControlPanel',
    'SubatomicInfoPanel',
    # Data management exports
    'DataEditorDialog',
    'DataListDialog',
    'AtomCreationDialog',
    'SubatomicCreationDialog',
    'MoleculeCreationDialog',
    'open_atom_creation_dialog',
    'open_subatomic_creation_dialog',
    'open_molecule_creation_dialog',
]
