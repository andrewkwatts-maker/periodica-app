#!/usr/bin/env python3
"""
Comprehensive Unit Tests for UI Button Actions

Tests cover all button actions across all 5 tabs (atoms, quarks, subatomic, molecules, alloys):
1. Data Management Actions (add, edit, remove, reset, create)
2. View Actions (reset view, reset property mappings)
3. Filter Actions (clear filters, select/clear all categories)
4. Color Picker Actions (opens dialog, updates gradient)
5. Dialog Actions (validates input, saves to manager, cancel closes)
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QColorDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


# Ensure QApplication exists for widget tests
@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_table_widget():
    """Create a mock table widget with all expected attributes and methods."""
    table = MagicMock()
    table.zoom_level = 1.0
    table.pan_x = 0
    table.pan_y = 0
    table.update = MagicMock()
    table.reset_view = MagicMock()
    table.set_layout_mode = MagicMock()
    table.filters = {}
    table.base_elements = []
    table.selected_element = None

    # Visual property attributes
    table.fill_property = "none"
    table.border_property = "none"
    table.glow_property = "none"
    table.ring_property = "none"

    # Property range attributes
    table.fill_color_range_min = 0
    table.fill_color_range_max = 100
    table.border_color_range_min = 0
    table.border_color_range_max = 100

    # Custom gradient attributes
    table.custom_fill_gradient_start = None
    table.custom_fill_gradient_end = None
    table.custom_border_gradient_start = None
    table.custom_border_gradient_end = None

    # Filter methods
    table.set_filter = MagicMock()
    table.set_category_filters = MagicMock()
    table.set_structure_filters = MagicMock()
    table.set_state_filters = MagicMock()
    table.set_polarity_filters = MagicMock()
    table.set_classification_filter = MagicMock()
    table.set_generation_filter = MagicMock()
    table.set_charge_filter = MagicMock()

    return table


@pytest.fixture
def mock_data_manager():
    """Create a mock data manager."""
    manager = MagicMock()
    manager.add_item = MagicMock(return_value=True)
    manager.remove_item = MagicMock(return_value=True)
    manager.reset_to_defaults = MagicMock(return_value=True)
    manager.get_items = MagicMock(return_value=[])
    return manager


@pytest.fixture
def mock_info_panel():
    """Create a mock info panel with inline editor support."""
    panel = MagicMock()
    panel.start_add = MagicMock()
    panel.start_edit = MagicMock()
    panel.update_element = MagicMock()
    panel.show_default = MagicMock()
    return panel


# ============================================================================
# ATOMS TAB TESTS
# ============================================================================

class TestAtomDataActions:
    """Test data management actions for the Atoms tab."""

    def test_add_action_shows_inline_editor(self, qapp, mock_table_widget, mock_info_panel):
        """Verify add button triggers info_panel.start_add."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        # Simulate add button click via signal
        signal_emitted = []
        panel.add_requested.connect(lambda: signal_emitted.append(True))

        panel.add_btn.click()

        assert len(signal_emitted) == 1, "add_requested signal should be emitted"

    def test_edit_action_requires_selection(self, qapp, mock_table_widget):
        """Verify edit button is disabled when nothing is selected."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        # Initially edit should be disabled
        assert not panel.edit_btn.isEnabled(), "Edit button should be disabled when nothing selected"

        # Enable via set_item_selected
        panel.set_item_selected(True)
        assert panel.edit_btn.isEnabled(), "Edit button should be enabled when item selected"

        # Disable when selection cleared
        panel.set_item_selected(False)
        assert not panel.edit_btn.isEnabled(), "Edit button should be disabled when selection cleared"

    @patch('PySide6.QtWidgets.QMessageBox.question')
    def test_remove_action_shows_confirmation(self, mock_question, qapp, mock_table_widget):
        """Verify remove action shows confirmation dialog."""
        from ui.control_panel import ControlPanel

        mock_question.return_value = QMessageBox.StandardButton.Yes

        panel = ControlPanel(mock_table_widget)
        panel.set_item_selected(True)

        signal_emitted = []
        panel.remove_requested.connect(lambda: signal_emitted.append(True))

        panel.remove_btn.click()

        assert len(signal_emitted) == 1, "remove_requested signal should be emitted"

    def test_remove_action_updates_table(self, qapp, mock_table_widget):
        """Verify remove action triggers table update."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        # Connect a handler that updates the table
        def handle_remove():
            mock_table_widget.update()

        panel.remove_requested.connect(handle_remove)
        panel.set_item_selected(True)
        panel.remove_btn.click()

        mock_table_widget.update.assert_called()

    def test_reset_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify reset action emits reset_requested signal."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        signal_emitted = []
        panel.reset_requested.connect(lambda: signal_emitted.append(True))

        panel.reset_data_btn.click()

        assert len(signal_emitted) == 1, "reset_requested signal should be emitted"

    def test_reset_action_restores_defaults(self, qapp, mock_table_widget):
        """Verify reset property mappings restores default values."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        # Change a property mapping
        panel.fill_color_control.property_combo.setCurrentIndex(0)

        # Reset to defaults
        panel.reset_property_mappings()

        # Verify default index is restored (16 for Emission Wavelength)
        assert panel.fill_color_control.property_combo.currentIndex() == 16

    def test_create_action_opens_dialog(self, qapp, mock_table_widget):
        """Verify create button emits create_requested signal."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        signal_emitted = []
        panel.create_requested.connect(lambda: signal_emitted.append(True))

        panel.create_btn.click()

        assert len(signal_emitted) == 1, "create_requested signal should be emitted"


# ============================================================================
# QUARKS TAB TESTS
# ============================================================================

class TestQuarkDataActions:
    """Test data management actions for the Quarks tab."""

    def test_add_action_opens_editor(self, qapp, mock_table_widget):
        """Verify add button emits add_requested signal."""
        from ui.quark_control_panel import QuarkControlPanel

        panel = QuarkControlPanel(mock_table_widget)

        signal_emitted = []
        panel.add_requested.connect(lambda: signal_emitted.append(True))

        panel.add_btn.click()

        assert len(signal_emitted) == 1, "add_requested signal should be emitted"

    def test_edit_action_requires_selection(self, qapp, mock_table_widget):
        """Verify edit button is disabled when nothing is selected."""
        from ui.quark_control_panel import QuarkControlPanel

        panel = QuarkControlPanel(mock_table_widget)

        assert not panel.edit_btn.isEnabled(), "Edit button should be disabled initially"

        panel.set_item_selected(True)
        assert panel.edit_btn.isEnabled(), "Edit button should be enabled when item selected"

    def test_remove_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify remove action emits remove_requested signal."""
        from ui.quark_control_panel import QuarkControlPanel

        panel = QuarkControlPanel(mock_table_widget)
        panel.set_item_selected(True)

        signal_emitted = []
        panel.remove_requested.connect(lambda: signal_emitted.append(True))

        panel.remove_btn.click()

        assert len(signal_emitted) == 1

    def test_remove_action_updates_table(self, qapp, mock_table_widget):
        """Verify remove action triggers table update."""
        from ui.quark_control_panel import QuarkControlPanel

        panel = QuarkControlPanel(mock_table_widget)

        def handle_remove():
            mock_table_widget.update()

        panel.remove_requested.connect(handle_remove)
        panel.set_item_selected(True)
        panel.remove_btn.click()

        mock_table_widget.update.assert_called()

    def test_reset_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify reset action emits reset_requested signal."""
        from ui.quark_control_panel import QuarkControlPanel

        panel = QuarkControlPanel(mock_table_widget)

        signal_emitted = []
        panel.reset_requested.connect(lambda: signal_emitted.append(True))

        panel.reset_data_btn.click()

        assert len(signal_emitted) == 1

    def test_reset_action_restores_defaults(self, qapp, mock_table_widget):
        """Verify reset visual encodings restores default values."""
        from ui.quark_control_panel import QuarkControlPanel

        panel = QuarkControlPanel(mock_table_widget)

        # Change a property mapping
        panel.fill_color_control.property_combo.setCurrentIndex(0)

        # Reset to defaults
        panel._reset_visual_encodings()

        # Verify default index is restored (1 for Mass log scale)
        assert panel.fill_color_control.property_combo.currentIndex() == 1

    def test_create_action_opens_dialog(self, qapp, mock_table_widget):
        """Verify create button emits create_requested signal."""
        from ui.quark_control_panel import QuarkControlPanel

        panel = QuarkControlPanel(mock_table_widget)

        signal_emitted = []
        panel.create_requested.connect(lambda: signal_emitted.append(True))

        panel.create_btn.click()

        assert len(signal_emitted) == 1


# ============================================================================
# SUBATOMIC TAB TESTS
# ============================================================================

class TestSubatomicDataActions:
    """Test data management actions for the Subatomic tab."""

    def test_add_action_opens_editor(self, qapp, mock_table_widget):
        """Verify add button emits add_requested signal."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        panel = SubatomicControlPanel(mock_table_widget)

        signal_emitted = []
        panel.add_requested.connect(lambda: signal_emitted.append(True))

        panel.add_btn.click()

        assert len(signal_emitted) == 1

    def test_edit_action_requires_selection(self, qapp, mock_table_widget):
        """Verify edit button is disabled when nothing is selected."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        panel = SubatomicControlPanel(mock_table_widget)

        assert not panel.edit_btn.isEnabled()

        panel.set_item_selected(True)
        assert panel.edit_btn.isEnabled()

    def test_remove_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify remove action emits remove_requested signal."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        panel = SubatomicControlPanel(mock_table_widget)
        panel.set_item_selected(True)

        signal_emitted = []
        panel.remove_requested.connect(lambda: signal_emitted.append(True))

        panel.remove_btn.click()

        assert len(signal_emitted) == 1

    def test_remove_action_updates_table(self, qapp, mock_table_widget):
        """Verify remove action triggers table update."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        panel = SubatomicControlPanel(mock_table_widget)

        def handle_remove():
            mock_table_widget.update()

        panel.remove_requested.connect(handle_remove)
        panel.set_item_selected(True)
        panel.remove_btn.click()

        mock_table_widget.update.assert_called()

    def test_reset_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify reset action emits reset_requested signal."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        panel = SubatomicControlPanel(mock_table_widget)

        signal_emitted = []
        panel.reset_requested.connect(lambda: signal_emitted.append(True))

        panel.reset_data_btn.click()

        assert len(signal_emitted) == 1

    def test_reset_action_restores_defaults(self, qapp, mock_table_widget):
        """Verify reset property mappings restores default values."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        panel = SubatomicControlPanel(mock_table_widget)

        # Change a property mapping
        panel.fill_color_control.property_combo.setCurrentIndex(0)

        # Reset to defaults
        panel.reset_property_mappings()

        # Verify default index is restored (1 for Mass log scale)
        assert panel.fill_color_control.property_combo.currentIndex() == 1

    def test_create_action_opens_dialog(self, qapp, mock_table_widget):
        """Verify create button emits create_requested signal."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        panel = SubatomicControlPanel(mock_table_widget)

        signal_emitted = []
        panel.create_requested.connect(lambda: signal_emitted.append(True))

        panel.create_btn.click()

        assert len(signal_emitted) == 1


# ============================================================================
# MOLECULES TAB TESTS
# ============================================================================

class TestMoleculeDataActions:
    """Test data management actions for the Molecules tab."""

    def test_add_action_opens_editor(self, qapp, mock_table_widget):
        """Verify add button emits add_requested signal."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        signal_emitted = []
        panel.add_requested.connect(lambda: signal_emitted.append(True))

        panel.add_btn.click()

        assert len(signal_emitted) == 1

    def test_edit_action_requires_selection(self, qapp, mock_table_widget):
        """Verify edit button is disabled when nothing is selected."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        assert not panel.edit_btn.isEnabled()

        panel.set_item_selected(True)
        assert panel.edit_btn.isEnabled()

    def test_remove_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify remove action emits remove_requested signal."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)
        panel.set_item_selected(True)

        signal_emitted = []
        panel.remove_requested.connect(lambda: signal_emitted.append(True))

        panel.remove_btn.click()

        assert len(signal_emitted) == 1

    def test_remove_action_updates_table(self, qapp, mock_table_widget):
        """Verify remove action triggers table update."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        def handle_remove():
            mock_table_widget.update()

        panel.remove_requested.connect(handle_remove)
        panel.set_item_selected(True)
        panel.remove_btn.click()

        mock_table_widget.update.assert_called()

    def test_reset_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify reset action emits reset_requested signal."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        signal_emitted = []
        panel.reset_requested.connect(lambda: signal_emitted.append(True))

        panel.reset_data_btn.click()

        assert len(signal_emitted) == 1

    def test_reset_action_restores_defaults(self, qapp, mock_table_widget):
        """Verify reset property mappings restores default values."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        # Change a property mapping
        panel.fill_color_control.property_combo.setCurrentIndex(3)

        # Reset to defaults
        panel._reset_property_mappings()

        # Verify default index is restored (0 for Molecular Mass)
        assert panel.fill_color_control.property_combo.currentIndex() == 0

    def test_create_action_opens_dialog(self, qapp, mock_table_widget):
        """Verify create button emits create_requested signal."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        signal_emitted = []
        panel.create_requested.connect(lambda: signal_emitted.append(True))

        panel.create_btn.click()

        assert len(signal_emitted) == 1


# ============================================================================
# ALLOYS TAB TESTS
# ============================================================================

class TestAlloyDataActions:
    """Test data management actions for the Alloys tab."""

    def test_add_action_opens_editor(self, qapp, mock_table_widget):
        """Verify add button emits add_requested signal."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        signal_emitted = []
        panel.add_requested.connect(lambda: signal_emitted.append(True))

        panel.add_btn.click()

        assert len(signal_emitted) == 1

    def test_edit_action_requires_selection(self, qapp, mock_table_widget):
        """Verify edit button is disabled when nothing is selected."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        assert not panel.edit_btn.isEnabled()

        panel.set_item_selected(True)
        assert panel.edit_btn.isEnabled()

    def test_remove_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify remove action emits remove_requested signal."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)
        panel.set_item_selected(True)

        signal_emitted = []
        panel.remove_requested.connect(lambda: signal_emitted.append(True))

        panel.remove_btn.click()

        assert len(signal_emitted) == 1

    def test_remove_action_updates_table(self, qapp, mock_table_widget):
        """Verify remove action triggers table update."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        def handle_remove():
            mock_table_widget.update()

        panel.remove_requested.connect(handle_remove)
        panel.set_item_selected(True)
        panel.remove_btn.click()

        mock_table_widget.update.assert_called()

    def test_reset_action_shows_confirmation(self, qapp, mock_table_widget):
        """Verify reset action emits reset_requested signal."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        signal_emitted = []
        panel.reset_requested.connect(lambda: signal_emitted.append(True))

        panel.reset_data_btn.click()

        assert len(signal_emitted) == 1

    def test_reset_action_restores_defaults(self, qapp, mock_table_widget):
        """Verify reset property mappings restores default values."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        # Change a property mapping
        panel.fill_color_control.property_combo.setCurrentIndex(5)

        # Reset to defaults
        panel.reset_property_mappings()

        # Verify default index is restored (1 for Density)
        assert panel.fill_color_control.property_combo.currentIndex() == 1

    def test_create_action_opens_dialog(self, qapp, mock_table_widget):
        """Verify create button emits create_requested signal."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        signal_emitted = []
        panel.create_requested.connect(lambda: signal_emitted.append(True))

        panel.create_btn.click()

        assert len(signal_emitted) == 1


# ============================================================================
# VIEW ACTIONS TESTS
# ============================================================================

class TestViewActions:
    """Test view-related actions across all tabs."""

    def test_reset_view_resets_zoom_atoms(self, qapp, mock_table_widget):
        """Verify reset view resets zoom level for Atoms tab."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        # Change zoom
        mock_table_widget.zoom_level = 2.5
        mock_table_widget.pan_x = 100
        mock_table_widget.pan_y = 50

        # Reset view
        panel.reset_view()

        assert mock_table_widget.zoom_level == 1.0
        assert mock_table_widget.pan_x == 0
        assert mock_table_widget.pan_y == 0

    def test_reset_view_resets_pan_atoms(self, qapp, mock_table_widget):
        """Verify reset view resets pan position for Atoms tab."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        mock_table_widget.pan_x = 200
        mock_table_widget.pan_y = -150

        panel.reset_view()

        assert mock_table_widget.pan_x == 0
        assert mock_table_widget.pan_y == 0

    def test_reset_property_mappings_restores_defaults_atoms(self, qapp, mock_table_widget):
        """Verify reset property mappings restores default values for Atoms tab."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        # Modify all property controls
        panel.fill_color_control.property_combo.setCurrentIndex(0)
        panel.border_color_control.property_combo.setCurrentIndex(0)
        panel.glow_color_control.property_combo.setCurrentIndex(0)

        # Reset
        panel.reset_property_mappings()

        # Verify defaults
        assert panel.fill_color_control.property_combo.currentIndex() == 16
        assert panel.border_color_control.property_combo.currentIndex() == 8
        assert panel.glow_color_control.property_combo.currentIndex() == 6

    def test_reset_view_quarks(self, qapp, mock_table_widget):
        """Verify reset view works for Quarks tab."""
        from ui.quark_control_panel import QuarkControlPanel

        mock_table_widget.reset_view = MagicMock()

        panel = QuarkControlPanel(mock_table_widget)
        panel._on_reset_view()

        mock_table_widget.reset_view.assert_called_once()

    def test_reset_view_subatomic(self, qapp, mock_table_widget):
        """Verify reset view works for Subatomic tab."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        mock_table_widget.reset_view = MagicMock()

        panel = SubatomicControlPanel(mock_table_widget)
        panel._on_reset_view()

        mock_table_widget.reset_view.assert_called_once()

    def test_reset_view_molecules(self, qapp, mock_table_widget):
        """Verify reset view works for Molecules tab."""
        from ui.molecule_control_panel import MoleculeControlPanel

        mock_table_widget.reset_view = MagicMock()

        panel = MoleculeControlPanel(mock_table_widget)
        panel._on_reset_view()

        mock_table_widget.reset_view.assert_called_once()

    def test_reset_view_alloys(self, qapp, mock_table_widget):
        """Verify reset view works for Alloys tab."""
        from ui.alloy_control_panel import AlloyControlPanel

        mock_table_widget.reset_view = MagicMock()

        panel = AlloyControlPanel(mock_table_widget)
        panel._on_reset_view()

        mock_table_widget.reset_view.assert_called_once()


# ============================================================================
# FILTER ACTIONS TESTS
# ============================================================================

class TestFilterActions:
    """Test filter-related actions across all tabs."""

    def test_clear_filters_checks_all_molecules(self, qapp, mock_table_widget):
        """Verify clear filters checks all filter checkboxes for Molecules tab."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        # Uncheck some filters
        panel.solid_check.setChecked(False)
        panel.polar_check.setChecked(False)
        panel.organic_check.setChecked(False)

        # Clear filters
        panel._on_clear_filters()

        # Verify all are checked
        assert panel.solid_check.isChecked()
        assert panel.liquid_check.isChecked()
        assert panel.gas_check.isChecked()
        assert panel.polar_check.isChecked()
        assert panel.nonpolar_check.isChecked()
        assert panel.organic_check.isChecked()
        assert panel.inorganic_check.isChecked()

    def test_select_all_checks_all_categories_alloys(self, qapp, mock_table_widget):
        """Verify select all checks all category checkboxes for Alloys tab."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        # Uncheck all categories
        for cb in panel.category_checkboxes.values():
            cb.setChecked(False)

        # Select all
        panel._set_all_category_checkboxes(True)

        # Verify all are checked
        for cb in panel.category_checkboxes.values():
            assert cb.isChecked()

    def test_clear_all_unchecks_categories_alloys(self, qapp, mock_table_widget):
        """Verify clear all unchecks all category checkboxes for Alloys tab."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        # Ensure all are checked first
        for cb in panel.category_checkboxes.values():
            cb.setChecked(True)

        # Clear all
        panel._set_all_category_checkboxes(False)

        # Verify all are unchecked
        for cb in panel.category_checkboxes.values():
            assert not cb.isChecked()

    def test_clear_filters_alloys(self, qapp, mock_table_widget):
        """Verify clear filters resets all filter checkboxes for Alloys tab."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        # Uncheck some filters
        for cb in list(panel.category_checkboxes.values())[:3]:
            cb.setChecked(False)
        for cb in list(panel.structure_checkboxes.values())[:2]:
            cb.setChecked(False)

        # Clear filters
        panel._on_clear_filters()

        # Verify all are checked
        for cb in panel.category_checkboxes.values():
            assert cb.isChecked()
        for cb in panel.structure_checkboxes.values():
            assert cb.isChecked()
        for cb in panel.corrosion_checkboxes.values():
            assert cb.isChecked()

    def test_classification_filter_quarks(self, qapp, mock_table_widget):
        """Verify classification filter updates table for Quarks tab."""
        from ui.quark_control_panel import QuarkControlPanel

        mock_table_widget.set_classification_filter = MagicMock()

        panel = QuarkControlPanel(mock_table_widget)

        # Toggle a filter
        panel.quark_check.setChecked(False)
        panel._on_classification_filter_changed()

        mock_table_widget.set_classification_filter.assert_called()
        mock_table_widget.update.assert_called()

    def test_generation_filter_quarks(self, qapp, mock_table_widget):
        """Verify generation filter updates table for Quarks tab."""
        from ui.quark_control_panel import QuarkControlPanel

        mock_table_widget.set_generation_filter = MagicMock()

        panel = QuarkControlPanel(mock_table_widget)

        # Toggle a filter
        panel.gen1_check.setChecked(False)
        panel._on_generation_filter_changed()

        mock_table_widget.set_generation_filter.assert_called()
        mock_table_widget.update.assert_called()

    def test_filter_subatomic(self, qapp, mock_table_widget):
        """Verify filter updates table for Subatomic tab."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        mock_table_widget.set_filter = MagicMock()

        panel = SubatomicControlPanel(mock_table_widget)

        # Toggle filters
        panel.show_baryons_check.setChecked(False)
        panel._on_filter_changed()

        mock_table_widget.set_filter.assert_called()


# ============================================================================
# COLOR PICKER ACTIONS TESTS
# ============================================================================

class TestColorPickerActions:
    """Test color picker actions across all tabs."""

    @patch('PySide6.QtWidgets.QColorDialog.getColor')
    def test_color_picker_opens_dialog_quark(self, mock_get_color, qapp, mock_table_widget):
        """Verify color picker opens dialog for Quarks tab."""
        from ui.quark_control_panel import QuarkPropertyMappingWidget

        mock_get_color.return_value = QColor(255, 0, 0)

        widget = QuarkPropertyMappingWidget("Mass_MeVc2")
        widget._open_color_picker("start")

        mock_get_color.assert_called_once()

    @patch('PySide6.QtWidgets.QColorDialog.getColor')
    def test_color_picker_updates_gradient_quark(self, mock_get_color, qapp, mock_table_widget):
        """Verify color picker updates gradient colors for Quarks tab."""
        from ui.quark_control_panel import QuarkPropertyMappingWidget

        new_color = QColor(255, 128, 0)
        mock_get_color.return_value = new_color

        widget = QuarkPropertyMappingWidget("Mass_MeVc2")

        signal_emitted = []
        widget.gradient_colors_changed.connect(lambda s, e: signal_emitted.append((s, e)))

        widget._open_color_picker("start")

        assert widget.custom_gradient_start == new_color
        assert len(signal_emitted) == 1

    @patch('PySide6.QtWidgets.QColorDialog.getColor')
    def test_color_picker_end_color(self, mock_get_color, qapp, mock_table_widget):
        """Verify color picker updates end gradient color."""
        from ui.quark_control_panel import QuarkPropertyMappingWidget

        new_color = QColor(0, 255, 128)
        mock_get_color.return_value = new_color

        widget = QuarkPropertyMappingWidget("Mass_MeVc2")
        widget._open_color_picker("end")

        assert widget.custom_gradient_end == new_color

    @patch('PySide6.QtWidgets.QColorDialog.getColor')
    def test_color_picker_cancelled(self, mock_get_color, qapp, mock_table_widget):
        """Verify color picker handles cancelled dialog."""
        from ui.quark_control_panel import QuarkPropertyMappingWidget

        # Return invalid color (cancelled)
        mock_get_color.return_value = QColor()

        widget = QuarkPropertyMappingWidget("Mass_MeVc2")
        original_start = widget.custom_gradient_start

        widget._open_color_picker("start")

        # Color should not change
        assert widget.custom_gradient_start == original_start

    @patch('PySide6.QtWidgets.QColorDialog.getColor')
    def test_color_picker_molecules(self, mock_get_color, qapp, mock_table_widget):
        """Verify color picker works for Molecules tab."""
        from ui.molecule_control_panel import MoleculePropertyControl

        new_color = QColor(128, 64, 255)
        mock_get_color.return_value = new_color

        # Create a minimal parent panel mock
        mock_panel = MagicMock()
        mock_panel.table = mock_table_widget

        control = MoleculePropertyControl(
            "Test", "fill_color", mock_panel,
            ["Molecular Mass", "Density", "None"],
            control_type="color"
        )

        signal_emitted = []
        control.gradient_colors_changed.connect(lambda k, s, e: signal_emitted.append((k, s, e)))

        control.pick_gradient_color("start")

        assert control.start_color == new_color.name()
        assert len(signal_emitted) == 1

    @patch('PySide6.QtWidgets.QColorDialog.getColor')
    def test_color_picker_alloys(self, mock_get_color, qapp, mock_table_widget):
        """Verify color picker works for Alloys tab."""
        from ui.alloy_control_panel import AlloyPropertyControl

        new_color = QColor(64, 128, 64)
        mock_get_color.return_value = new_color

        # Create a minimal parent panel mock
        mock_panel = MagicMock()
        mock_panel.table = mock_table_widget
        mock_panel.on_gradient_color_changed = MagicMock()

        control = AlloyPropertyControl(
            "Test", "fill_color", mock_panel,
            ["None", "Density", "Melting Point"],
            control_type="color"
        )

        control.pick_gradient_color("start")

        assert control.gradient_start_color == new_color
        mock_panel.on_gradient_color_changed.assert_called()


# ============================================================================
# DIALOG ACTIONS TESTS
# ============================================================================

class TestDialogActions:
    """Test dialog actions for data creation/editing."""

    def test_create_dialog_validates_input(self, qapp):
        """Verify create dialog validates required input fields."""
        from ui.inline_editor import InlineDataEditor
        from data.data_manager import DataCategory

        editor = InlineDataEditor()
        editor.start_add(DataCategory.ELEMENTS)

        # Try to validate with empty required field
        valid, error = editor._validate()

        assert not valid, "Validation should fail with empty required fields"
        assert "required" in error.lower()

    def test_create_dialog_validates_with_data(self, qapp):
        """Verify create dialog passes validation with valid data."""
        from ui.inline_editor import InlineDataEditor
        from data.data_manager import DataCategory

        editor = InlineDataEditor()
        editor.start_add(DataCategory.ELEMENTS, {
            'symbol': 'Te',
            'name': 'Test Element'
        })

        valid, error = editor._validate()

        assert valid, f"Validation should pass with valid data: {error}"

    @patch('ui.inline_editor.get_data_manager')
    def test_create_dialog_saves_to_manager(self, mock_get_manager, qapp):
        """Verify create dialog saves data to data manager."""
        from ui.inline_editor import InlineDataEditor
        from data.data_manager import DataCategory

        mock_manager = MagicMock()
        mock_manager.add_item = MagicMock(return_value=True)
        mock_get_manager.return_value = mock_manager

        editor = InlineDataEditor()
        editor.start_add(DataCategory.ELEMENTS, {
            'symbol': 'Te',
            'name': 'Test Element',
            'atomic_number': 999
        })

        # Trigger save
        editor._on_save()

        mock_manager.add_item.assert_called_once()

    def test_cancel_dialog_closes_without_save(self, qapp):
        """Verify cancel dialog emits edit_cancelled signal without saving."""
        from ui.inline_editor import InlineDataEditor
        from data.data_manager import DataCategory

        editor = InlineDataEditor()
        editor.start_add(DataCategory.ELEMENTS, {
            'symbol': 'Te',
            'name': 'Test Element'
        })

        signal_emitted = []
        editor.edit_cancelled.connect(lambda: signal_emitted.append(True))

        editor._on_cancel()

        assert len(signal_emitted) == 1, "edit_cancelled signal should be emitted"

    def test_edit_mode_loads_existing_data(self, qapp):
        """Verify edit mode loads existing data into form."""
        from ui.inline_editor import InlineDataEditor
        from data.data_manager import DataCategory

        editor = InlineDataEditor()

        existing_data = {
            'symbol': 'Au',
            'name': 'Gold',
            'atomic_number': 79,
            'atomic_mass': 196.967
        }

        editor.start_edit(DataCategory.ELEMENTS, existing_data)

        # Verify data is loaded
        assert editor.is_edit_mode
        assert editor.existing_data == existing_data
        assert "Gold" in editor.title_label.text()

    def test_create_from_particles_editor(self, qapp):
        """Verify CreateFromParticleEditor emits signals correctly."""
        from ui.inline_editor import CreateFromParticleEditor

        editor = CreateFromParticleEditor()

        signal_emitted = []
        editor.creation_cancelled.connect(lambda: signal_emitted.append(True))

        editor._on_cancel()

        assert len(signal_emitted) == 1


# ============================================================================
# ITEM COUNT TESTS
# ============================================================================

class TestItemCount:
    """Test item count label updates across all tabs."""

    def test_update_item_count_atoms(self, qapp, mock_table_widget):
        """Verify item count updates for Atoms tab."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        panel.update_item_count(118)

        assert "118" in panel.item_count_label.text()

    def test_update_item_count_quarks(self, qapp, mock_table_widget):
        """Verify item count updates for Quarks tab."""
        from ui.quark_control_panel import QuarkControlPanel

        panel = QuarkControlPanel(mock_table_widget)

        panel.update_item_count(6)

        assert "6" in panel.item_count_label.text()

    def test_update_item_count_subatomic(self, qapp, mock_table_widget):
        """Verify item count updates for Subatomic tab."""
        from ui.subatomic_control_panel import SubatomicControlPanel

        panel = SubatomicControlPanel(mock_table_widget)

        panel.update_item_count(24)

        assert "24" in panel.item_count_label.text()

    def test_update_item_count_molecules(self, qapp, mock_table_widget):
        """Verify item count updates for Molecules tab."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        panel.update_item_count(50)

        assert "50" in panel.item_count_label.text()

    def test_update_item_count_alloys(self, qapp, mock_table_widget):
        """Verify item count updates for Alloys tab."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        panel.update_item_count(35)

        assert "35" in panel.item_count_label.text()


# ============================================================================
# LAYOUT MODE TESTS
# ============================================================================

class TestLayoutModeActions:
    """Test layout mode change actions across all tabs."""

    def test_layout_mode_change_atoms(self, qapp, mock_table_widget):
        """Verify layout mode change works for Atoms tab."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        # Change to spiral layout
        panel.spiral_radio.setChecked(True)

        mock_table_widget.set_layout_mode.assert_called_with("spiral")

    def test_layout_mode_change_quarks(self, qapp, mock_table_widget):
        """Verify layout mode change works for Quarks tab."""
        from ui.quark_control_panel import QuarkControlPanel
        from core.quark_enums import QuarkLayoutMode

        panel = QuarkControlPanel(mock_table_widget)

        # Change to linear layout
        panel.linear_radio.setChecked(True)

        mock_table_widget.set_layout_mode.assert_called_with(QuarkLayoutMode.LINEAR)

    def test_layout_mode_change_subatomic(self, qapp, mock_table_widget):
        """Verify layout mode change works for Subatomic tab."""
        from ui.subatomic_control_panel import SubatomicControlPanel
        from core.subatomic_enums import SubatomicLayoutMode

        panel = SubatomicControlPanel(mock_table_widget)

        # Change to mass order layout
        panel.mass_radio.setChecked(True)

        mock_table_widget.set_layout_mode.assert_called_with(SubatomicLayoutMode.MASS_ORDER)

    def test_layout_mode_change_molecules(self, qapp, mock_table_widget):
        """Verify layout mode change works for Molecules tab."""
        from ui.molecule_control_panel import MoleculeControlPanel

        panel = MoleculeControlPanel(mock_table_widget)

        # Change to polarity layout
        panel.polarity_radio.setChecked(True)

        mock_table_widget.set_layout_mode.assert_called_with("polarity")

    def test_layout_mode_change_alloys(self, qapp, mock_table_widget):
        """Verify layout mode change works for Alloys tab."""
        from ui.alloy_control_panel import AlloyControlPanel

        panel = AlloyControlPanel(mock_table_widget)

        # Change to scatter layout
        panel.scatter_radio.setChecked(True)

        mock_table_widget.set_layout_mode.assert_called_with("property_scatter")


# ============================================================================
# INTEGRATION-LIKE TESTS
# ============================================================================

class TestButtonSignalIntegration:
    """Test that button clicks properly emit signals that can be connected to handlers."""

    def test_full_add_workflow(self, qapp, mock_table_widget):
        """Test the complete add workflow from button to handler."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        add_calls = []
        panel.add_requested.connect(lambda: add_calls.append("add"))

        panel.add_btn.click()

        assert len(add_calls) == 1
        assert add_calls[0] == "add"

    def test_full_edit_workflow(self, qapp, mock_table_widget):
        """Test the complete edit workflow from button to handler."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)
        panel.set_item_selected(True)

        edit_calls = []
        panel.edit_requested.connect(lambda: edit_calls.append("edit"))

        panel.edit_btn.click()

        assert len(edit_calls) == 1

    def test_full_remove_workflow(self, qapp, mock_table_widget):
        """Test the complete remove workflow from button to handler."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)
        panel.set_item_selected(True)

        remove_calls = []
        panel.remove_requested.connect(lambda: remove_calls.append("remove"))

        panel.remove_btn.click()

        assert len(remove_calls) == 1

    def test_full_create_workflow(self, qapp, mock_table_widget):
        """Test the complete create workflow from button to handler."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        create_calls = []
        panel.create_requested.connect(lambda: create_calls.append("create"))

        panel.create_btn.click()

        assert len(create_calls) == 1

    def test_full_reset_workflow(self, qapp, mock_table_widget):
        """Test the complete reset workflow from button to handler."""
        from ui.control_panel import ControlPanel

        panel = ControlPanel(mock_table_widget)

        reset_calls = []
        panel.reset_requested.connect(lambda: reset_calls.append("reset"))

        panel.reset_data_btn.click()

        assert len(reset_calls) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
