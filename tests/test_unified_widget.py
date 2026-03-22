#!/usr/bin/env python3
"""
Tests for the UnifiedPropertyControl widget.
Runs headlessly without opening any windows.
"""
import sys
import pytest
from unittest.mock import MagicMock

try:
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
    from PySide6.QtGui import QPalette, QColor
    from ui.components import UnifiedPropertyControl
    HAS_QT = True
except ImportError:
    HAS_QT = False

pytestmark = pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")


@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication exists for the test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def color_control(qapp):
    """Create a color-type UnifiedPropertyControl."""
    ctrl = UnifiedPropertyControl(
        title="Ionization Energy",
        property_name="ionization",
        property_type="color"
    )
    ctrl.set_value_range(3.5, 25.0)
    return ctrl


@pytest.fixture
def size_control(qapp):
    """Create a size-type UnifiedPropertyControl."""
    ctrl = UnifiedPropertyControl(
        title="Border Thickness",
        property_name="border",
        property_type="size"
    )
    ctrl.set_value_range(0, 10)
    return ctrl


class TestUnifiedPropertyControlCreation:
    """Test that UnifiedPropertyControl widgets can be created."""

    def test_color_control_created(self, color_control):
        assert color_control is not None

    def test_size_control_created(self, size_control):
        assert size_control is not None

    def test_spectrum_control_created(self, qapp):
        ctrl = UnifiedPropertyControl(
            title="Spectrum",
            property_name="spectrum",
            property_type="color"
        )
        ctrl.set_value_range(380, 750)
        assert ctrl is not None


class TestUnifiedPropertyControlSignals:
    """Test that signals are properly defined."""

    def test_color_range_signal_exists(self, color_control):
        assert hasattr(color_control, 'color_range_changed')

    def test_filter_range_signal_exists(self, color_control):
        assert hasattr(color_control, 'filter_range_changed')

    def test_filter_changed_signal_exists(self, color_control):
        assert hasattr(color_control, 'filter_changed')

    def test_color_range_signal_connectable(self, color_control):
        handler = MagicMock()
        color_control.color_range_changed.connect(handler)

    def test_filter_range_signal_connectable(self, color_control):
        handler = MagicMock()
        color_control.filter_range_changed.connect(handler)

    def test_filter_changed_signal_connectable(self, color_control):
        handler = MagicMock()
        color_control.filter_changed.connect(handler)


class TestUnifiedPropertyControlProperties:
    """Test widget property accessors."""

    def test_color_control_is_qwidget(self, color_control):
        assert isinstance(color_control, QWidget)

    def test_size_control_is_qwidget(self, size_control):
        assert isinstance(size_control, QWidget)

    def test_can_add_to_layout(self, qapp, color_control, size_control):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(color_control)
        layout.addWidget(size_control)
        assert layout.count() == 2
