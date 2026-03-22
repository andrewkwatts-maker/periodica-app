#====== Playtow/PeriodicTable2/core/unified_table.py ======#
#!copyright (c) 2025 Andrew Keith Watts. All rights reserved.
#!
#!This is the intellectual property of Andrew Keith Watts. Unauthorized
#!reproduction, distribution, or modification of this code, in whole or in part,
#!without the express written permission of Andrew Keith Watts is strictly prohibited.
#!
#!For inquiries, please contact AndrewKWatts@Gmail.com

"""
UnifiedTable - Main visualization widget
Handles all layout modes and user interactions
"""

import json
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QFont, QPainterPath,
                           QLinearGradient, QRadialGradient, QPolygonF, QGuiApplication)

# Import element data loader (JSON-based)
from periodica.data.element_loader import get_loader, ElementDataLoader

# Import helper functions that are still needed from element_data
from periodica.data.element_data import (get_electron_config, get_valence_electrons,
                                get_electron_shell_distribution, get_electron_quantum_numbers)

# Import enums
from periodica.core.pt_enums import (PTPropertyName, PTEncodingKey, PTWavelengthMode, PTElementDataKey,
                           PTPropertyType, PTEncodingType, PTLayoutMode, ENCODING_KEY_TO_TYPE)

# Import calculation functions
from periodica_app.utils.calculations import (get_block_color, ev_to_frequency, ev_to_wavelength,
                                 wavelength_to_rgb, get_ie_color, get_electroneg_color,
                                 calculate_emission_spectrum, draw_spectrum_bar,
                                 get_melting_color, get_radius_color, get_density_color,
                                 get_electron_affinity_color, get_boiling_color, C)

# Import position calculator
from periodica.utils.position_calculator import PositionCalculator

# Import orbital cloud functions
from periodica.utils.orbital_clouds import (get_orbital_probability, get_available_orbitals,
                                   get_orbital_name, get_real_shell_radii)

# Import SDF renderer for smooth particle visualization
from periodica_app.utils.sdf_renderer import SDFRenderer

# Import layout renderers
from periodica_app.layouts import (CircularLayoutRenderer, SpiralLayoutRenderer,
                    LinearLayoutRenderer, TableLayoutRenderer)


def normalize_angle(angle):
    """Normalize angle to [-π, π] range"""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


class UnifiedTable(QWidget):
    """Unified widget that can display both circular and serpentine layouts"""

    # Signals
    element_selected = Signal(dict)  # Emitted when an element is selected
    element_hovered = Signal(dict)   # Emitted when an element is hovered

    def __init__(self):
        super().__init__()
        self.setMinimumSize(900, 900)
        self.elements = []

        # Spectrum calculation settings (must be set before create_element_data)
        self.spectrum_max_n = 30  # Maximum quantum number for spectrum calculation (10=fast, 20=default, 50=detailed)

        self.create_element_data()

        self.hovered_element = None
        self.selected_element = None
        self.setMouseTracking(True)

        # Mouse interaction state
        self.is_rotating = False
        self.is_panning = False

        # Layout mode
        self.layout_mode = PTLayoutMode.CIRCULAR

        # Visualization modes - flexible mapping
        self.fill_property = "wavelength"  # Default to emission wavelength
        self.border_color_property = "electron_affinity"  # Border color
        self.glow_property = "melting"
        self.glow_color_property = "melting"  # Alias for glow_property (color)
        self.ring_property = "block"
        self.inner_ring_property = "block"  # Alias for ring_property
        self.radial_property = "none"  # For spiral mode: property to control radial offset
        self.show_isotopes = True
        self.selected_neutron_offset = 0  # Neutron offset for isotope selection (N - Z)

        # Property-based sizing
        self.border_size_property = "valence"  # Border size
        self.ring_size_property = "none"
        self.glow_radius_property = "none"
        self.glow_intensity_property = "none"

        # Text color properties
        self.symbol_text_color_property = "melting"  # Default to melting point
        self.atomic_number_text_color_property = "boiling"  # Default to boiling point

        # Custom gradient colors (None = use smart defaults)
        self.custom_fill_gradient_start = None
        self.custom_fill_gradient_end = None
        self.custom_border_gradient_start = None
        self.custom_border_gradient_end = None
        self.custom_ring_gradient_start = None
        self.custom_ring_gradient_end = None
        self.custom_glow_gradient_start = None
        self.custom_glow_gradient_end = None
        self.custom_symbol_text_gradient_start = None
        self.custom_symbol_text_gradient_end = None
        self.custom_atomic_number_text_gradient_start = None
        self.custom_atomic_number_text_gradient_end = None

        # Wavelength display modes (PTWavelengthMode.SPECTRUM = rainbow, PTWavelengthMode.GRADIENT = A-B lerp)
        self.fill_wavelength_mode = PTWavelengthMode.SPECTRUM
        self.border_wavelength_mode = PTWavelengthMode.SPECTRUM
        self.ring_wavelength_mode = PTWavelengthMode.SPECTRUM
        self.glow_wavelength_mode = PTWavelengthMode.SPECTRUM
        self.symbol_text_wavelength_mode = PTWavelengthMode.SPECTRUM
        self.atomic_number_text_wavelength_mode = PTWavelengthMode.SPECTRUM

        # Legacy property name for backwards compatibility (maps to border_size_property)
        self.border_property = "valence"

        # Default value flags - when True, use default color/size instead of property mapping
        self.use_default_fill = False
        self.use_default_border_color = False
        self.use_default_border_size = False
        self.use_default_ring_color = False
        self.use_default_ring_size = False
        self.use_default_glow_color = False
        self.use_default_glow_intensity = False
        self.use_default_symbol_text_color = False
        self.use_default_atomic_number_text_color = False

        # Glow type (auto-set by layout mode: circular/table=internal, spiral/serpentine=external)
        self.glow_type = "internal"

        # Zoom and pan for serpentine mode
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # Filter ranges - store min/max for each property
        self.filters = {
            'ionization': {'min': 3.5, 'max': 25.0, 'active': False},
            'electronegativity': {'min': 0.0, 'max': 4.0, 'active': False},
            'melting': {'min': 0, 'max': 4000, 'active': False},
            'boiling': {'min': 0, 'max': 4000, 'active': False},
            'radius': {'min': 30, 'max': 350, 'active': False},
            'density': {'min': 0.0001, 'max': 25, 'active': False},
            'electron_affinity': {'min': -10, 'max': 350, 'active': False},
            'valence': {'min': 1, 'max': 8, 'active': False},
            'atomic_number': {'min': 1, 'max': 118, 'active': False},
            'wavelength': {'min': 0, 'max': 1000, 'active': False},
            'emission_wavelength': {'min': 0, 'max': 1000, 'active': False},
            'visible_emission_wavelength': {'min': 380, 'max': 780, 'active': False},
            'ionization_wavelength': {'min': 0, 'max': 1000, 'active': False},
            'spectrum': {'min': 0, 'max': 1000, 'active': False}
        }

        # Linear mode ordering property
        self.order_property = "atomic_number"

        # Orbital visualization settings
        self.show_orbital_cloud = True
        self.orbital_n = 1  # Principal quantum number
        self.orbital_l = 0  # Angular momentum (0=s, 1=p, 2=d, 3=f)
        self.orbital_m = 0  # Magnetic quantum number
        self.nucleus_to_shell_ratio = 1.0  # Scale factor for nucleus vs shells (0.1 to 10)
        self.cloud_power = 5.0  # Power scaling for clouds (Distance * ratio^power), 0.0-10.0, default to 50 (5.0 on 0-10 scale)
        self.shell_power = 1.0  # Power scaling for shells (Distance * ratio^power), 0.0-10.0
        self.show_subatomic_particles = False  # Show protons/neutrons/electrons overlay
        self.show_element_table = True  # Show/hide the element table (keeps center visualizations)
        self.show_shells = True  # Show electron shells
        self.show_electrons = True  # Show individual electrons

        # 3D rotation angles for nucleus and electron clouds (in radians)
        self.rotation_x = 0.0  # Rotation around X axis (pitch)
        self.rotation_y = 0.0  # Rotation around Y axis (yaw)

        # Spectrum visualization settings
        self.show_spectrum_background = False  # Legacy - now controlled by property selection (spectrum property)
        self.show_prominent_spectrum_only = False  # If True, only show prominent lines (intensity > 0.3)
        self.show_spectrum_lines = False  # Show spectrum lines overlay on elements
        # spectrum_max_n is set earlier in __init__ before create_element_data()

        # Color range mapping - shift color spectrum for properties
        self.color_range_min = 380  # nm for wavelength (violet), or min value for other properties
        self.color_range_max = 780  # nm for wavelength (red), or max value for other properties

        # Per-property fade values (0.0 = no fade, 1.0 = fully transparent)
        self.fill_fade = 0.0
        self.border_color_fade = 0.0
        self.ring_color_fade = 0.0
        self.glow_color_fade = 0.0
        self.symbol_text_color_fade = 0.0
        self.atomic_number_text_color_fade = 0.0

        # Per-property color ranges (for properties that use color mapping)
        self.fill_color_range_min = 380.0
        self.fill_color_range_max = 780.0
        self.border_color_range_min = 0.0
        self.border_color_range_max = 350.0
        self.ring_color_range_min = 0.0
        self.ring_color_range_max = 4000.0
        self.glow_color_range_min = 0.0
        self.glow_color_range_max = 4000.0
        self.symbol_text_color_range_min = 0.0
        self.symbol_text_color_range_max = 4000.0
        self.atomic_number_text_color_range_min = 0.0
        self.atomic_number_text_color_range_max = 4000.0

        # Per-property size ranges (OUTPUT ranges - pixels, fractions, etc.)
        self.border_size_min = 1.0
        self.border_size_max = 6.0
        self.ring_size_min = 0.1
        self.ring_size_max = 0.5
        self.glow_intensity_min = 0.0
        self.glow_intensity_max = 1.0

        # Per-property INPUT ranges (property value ranges for size mapping - set by yellow tags)
        self.border_size_property_min = 0.0
        self.border_size_property_max = 100.0
        self.ring_size_property_min = 0.0
        self.ring_size_property_max = 100.0
        self.glow_intensity_property_min = 0.0
        self.glow_intensity_property_max = 100.0

        # Electron position tracking for click detection
        self.electron_positions = []  # List of (x, y, n, l, m, radius) for each electron

        # Cloud opacity control
        self.cloud_opacity = 0.33  # Default to 1/3 opacity (0.0 to 1.0)

        # Animation for electron cloud fuzzy effect
        self.cloud_animation_phase = 0.0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_cloud)
        self.animation_timer.start(50)  # Update every 50ms (20fps)

    def animate_cloud(self):
        """Update cloud animation phase for fuzzy effect"""
        self.cloud_animation_phase += 0.1
        if self.cloud_animation_phase > math.pi * 2:
            self.cloud_animation_phase = 0.0
        # Only update if cloud is visible
        if self.selected_element and self.show_orbital_cloud:
            self.update()

    def set_layout_mode(self, mode):
        """Switch between circular, spiral, serpentine, and table layouts

        Args:
            mode: PTLayoutMode enum or string layout mode
        """
        # Convert string to enum if needed
        if isinstance(mode, str):
            mode = PTLayoutMode.from_string(mode)

        self.layout_mode = mode

        # Auto-set glow type based on layout mode
        if mode == PTLayoutMode.CIRCULAR:
            self.glow_type = "internal"
            self.create_circular_layout()
        elif mode == PTLayoutMode.SPIRAL:
            self.glow_type = "external"
            # Reset zoom and pan when switching to spiral
            self.zoom_level = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.create_spiral_layout()
        elif mode == PTLayoutMode.SERPENTINE:
            self.glow_type = "external"
            # Reset zoom and pan when switching to serpentine
            self.zoom_level = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.create_serpentine_layout()
        elif mode == PTLayoutMode.TABLE:
            self.glow_type = "internal"
            self.create_table_layout()

        # Update mode description in UI
        self.update_mode_description()
        self.update()

    def update_mode_description(self):
        """Update the mode description - now handled by control panel mode-specific UI"""
        # Mode descriptions are now shown in mode-specific control panel widgets
        pass

    def set_property_mapping(self, property_key, property_name):
        """Map a visual property encoding to a data property.

        Args:
            property_key: Visual encoding key (e.g., 'fill_color', 'border_color', 'border_size',
                         'ring_color', 'ring_size', 'glow_color', 'glow_intensity',
                         'symbol_text_color', 'atomic_number_text_color')
            property_name: Data property name to map to (e.g., 'ionization', 'electronegativity',
                          'melting', 'boiling', 'radius', 'density', 'electron_affinity',
                          'valence', 'atomic_number', 'wavelength', 'emission_wavelength',
                          'visible_emission_wavelength', 'ionization_wavelength', 'spectrum',
                          'block', 'none')
        """
        # Map property_key to the correct attribute name
        property_map = {
            'fill_color': 'fill_property',
            'border_color': 'border_color_property',
            'border_size': 'border_size_property',
            'ring_color': 'ring_property',
            'ring_size': 'ring_size_property',
            'glow_color': 'glow_property',
            'glow_intensity': 'glow_intensity_property',
            'symbol_text_color': 'symbol_text_color_property',
            'atomic_number_text_color': 'atomic_number_text_color_property',
        }

        attr_name = property_map.get(property_key)
        if attr_name:
            setattr(self, attr_name, property_name)
            # Also update legacy aliases for backwards compatibility
            if property_key == 'glow_color':
                self.glow_color_property = property_name
            elif property_key == 'ring_color':
                self.inner_ring_property = property_name
            elif property_key == 'border_size':
                self.border_property = property_name  # Legacy alias
            elif property_key == 'glow_intensity':
                self.glow_radius_property = property_name
            self.update()

    def set_property_filter_range(self, property_key, min_val, max_val):
        """Set the filter range for a property. Elements outside this range will be greyed out.

        Args:
            property_key: Visual encoding key (e.g., 'fill_color', 'border_color')
            min_val: Minimum value for the filter
            max_val: Maximum value for the filter
        """
        # Map property_key to the data property name being used for that encoding
        property_map = {
            'fill_color': 'fill_property',
            'border_color': 'border_color_property',
            'border_size': 'border_size_property',
            'ring_color': 'ring_property',
            'ring_size': 'ring_size_property',
            'glow_color': 'glow_property',
            'glow_intensity': 'glow_intensity_property',
            'symbol_text_color': 'symbol_text_color_property',
            'atomic_number_text_color': 'atomic_number_text_color_property',
        }

        attr_name = property_map.get(property_key)
        if attr_name:
            # Get the property name being mapped
            prop_name = getattr(self, attr_name, 'none')

            # Update the filter for that property
            if prop_name in self.filters:
                self.filters[prop_name]['min'] = min_val
                self.filters[prop_name]['max'] = max_val
                self.filters[prop_name]['active'] = True
            else:
                # Create filter entry if it doesn't exist
                self.filters[prop_name] = {
                    'min': min_val,
                    'max': max_val,
                    'active': True
                }
            self.update()

    def set_gradient_colors(self, property_key, start_color, end_color):
        """Set custom gradient colors for a visual property encoding.

        Args:
            property_key: Visual encoding key (e.g., 'fill_color', 'border_color')
            start_color: Start color (QColor or hex string like '#6495ED')
            end_color: End color (QColor or hex string like '#FF6347')
        """
        # Convert hex strings to QColor if needed
        if isinstance(start_color, str):
            start_color = QColor(start_color)
        if isinstance(end_color, str):
            end_color = QColor(end_color)

        # Map property_key to gradient attribute names
        gradient_map = {
            'fill_color': ('custom_fill_gradient_start', 'custom_fill_gradient_end'),
            'border_color': ('custom_border_gradient_start', 'custom_border_gradient_end'),
            'ring_color': ('custom_ring_gradient_start', 'custom_ring_gradient_end'),
            'glow_color': ('custom_glow_gradient_start', 'custom_glow_gradient_end'),
            'symbol_text_color': ('custom_symbol_text_gradient_start', 'custom_symbol_text_gradient_end'),
            'atomic_number_text_color': ('custom_atomic_number_text_gradient_start', 'custom_atomic_number_text_gradient_end'),
        }

        if property_key in gradient_map:
            start_attr, end_attr = gradient_map[property_key]
            setattr(self, start_attr, start_color)
            setattr(self, end_attr, end_color)
            self.update()

    def set_fade_value(self, property_key, fade_value):
        """Set the fade amount for a visual property encoding.

        Args:
            property_key: Visual encoding key (e.g., 'fill_color', 'border_color')
            fade_value: Fade amount from 0.0 (no fade) to 1.0 (fully transparent)
        """
        # Map property_key to fade attribute names
        fade_map = {
            'fill_color': 'fill_fade',
            'border_color': 'border_color_fade',
            'ring_color': 'ring_color_fade',
            'glow_color': 'glow_color_fade',
            'symbol_text_color': 'symbol_text_color_fade',
            'atomic_number_text_color': 'atomic_number_text_color_fade',
        }

        attr_name = fade_map.get(property_key)
        if attr_name:
            setattr(self, attr_name, max(0.0, min(1.0, fade_value)))
            self.update()

    def reset_view(self):
        """Reset zoom and pan to default values.

        This restores the view to its initial state with no zoom or panning applied.
        """
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update()

    def set_zoom(self, zoom_level):
        """Set the zoom level for the view.

        Args:
            zoom_level: Zoom factor where 1.0 is 100%, 2.0 is 200%, etc.
        """
        self.zoom_level = max(0.1, min(10.0, zoom_level))
        self.update()

    def create_element_data(self):
        """Create base element data from JSON files"""
        # Get the element data loader (loads from JSON files)
        loader = get_loader()

        self.base_elements = []
        for element in loader.get_all_elements():
            symbol = element['symbol']
            z = element['atomic_number']
            ie = element.get('ionization_energy', 10.0)
            block = element.get('block', 's')
            electroneg = element.get('electronegativity', 0.0) or 0.0
            radius = element.get('atomic_radius', 100)
            melting = element.get('melting_point', 300) or 300
            # Convert isotopes from JSON dict format to tuple format (mass, abundance)
            raw_isotopes = element.get('isotopes', [])
            isotopes = []
            for iso in raw_isotopes:
                if isinstance(iso, dict):
                    mass = iso.get('mass_number', 0)
                    abundance = iso.get('abundance', 0)
                    isotopes.append((mass, abundance))
                elif isinstance(iso, (list, tuple)) and len(iso) >= 2:
                    isotopes.append((iso[0], iso[1]))
            density = element.get('density', 1.0) or 1.0
            boiling = element.get('boiling_point', 300) or 300
            electron_affinity = element.get('electron_affinity', 0) or 0
            valence = element.get('valence_electrons') or get_valence_electrons(z, block)
            name = element.get('name', symbol)
            group = element.get('group')
            period = element.get('period', 1)

            # Calculate emission spectrum lines for this element
            # Use configurable max_n for spectrum detail level
            spectrum_lines = calculate_emission_spectrum(z, ie, max_n=self.spectrum_max_n)

            # Extract wavelengths from calculated spectrum_lines
            # Primary emission: from JSON or calculated
            primary_wavelength = element.get('primary_emission_wavelength')
            if primary_wavelength is None:
                if spectrum_lines:
                    # Use strongest calculated line
                    primary_wavelength = max(spectrum_lines, key=lambda x: x[1])[0]
                else:
                    primary_wavelength = ev_to_wavelength(ie)

            # Visible emission: from JSON or calculated
            visible_wavelength = element.get('visible_emission_wavelength')
            if visible_wavelength is None:
                if spectrum_lines:
                    # Find strongest line in visible range from calculated spectrum
                    visible_lines = [(wl, intensity) for wl, intensity in spectrum_lines if 380 <= wl <= 780]
                    if visible_lines:
                        visible_wavelength = max(visible_lines, key=lambda x: x[1])[0]
                    else:
                        visible_wavelength = primary_wavelength
                else:
                    visible_wavelength = primary_wavelength

            # Ionization wavelength: wavelength corresponding to ionization energy
            ionization_wavelength = ev_to_wavelength(ie)

            self.base_elements.append({
                'symbol': symbol,
                'name': name,
                'z': z,
                'ie': ie,
                'ionization_energy': ie,  # Alias for tests
                'block': block,
                'block_color': get_block_color(block),
                'period': period,
                'group': group,
                'freq_phz': ev_to_frequency(ie),
                'wavelength_nm': primary_wavelength,  # Primary emission wavelength
                'emission_wavelength': primary_wavelength,  # Strongest emission line (may be UV/IR)
                'visible_emission_wavelength': visible_wavelength,  # Most prominent visible line
                'ionization_wavelength': ionization_wavelength,  # Wavelength from IE
                'electronegativity': electroneg,
                'atomic_radius': radius,
                'melting_point': melting,
                'melting': melting,  # Alias for tests
                'boiling_point': boiling,
                'boiling': boiling,  # Alias for tests
                'density': density,
                'electron_affinity': electron_affinity,
                'valence_electrons': valence,
                'valence': valence,  # Alias for tests
                'electron_config': element.get('electron_configuration') or get_electron_config(z),
                'isotopes': isotopes,
                'spectrum_lines': spectrum_lines
            })

        # Select hydrogen (Z=1) by default on launch
        if self.base_elements:
            hydrogen = next((elem for elem in self.base_elements if elem['z'] == 1), None)
            if hydrogen:
                self.selected_element = hydrogen

        self.create_circular_layout()

    def passes_filters(self, elem):
        """Check if element passes all active filters and isotope selection"""
        # First check isotope availability (for non-spiral layouts)
        if self.layout_mode != "spiral" and self.selected_neutron_offset != 0:
            # Check if this element has an isotope with the selected neutron offset
            if not self._has_isotope_with_offset(elem, self.selected_neutron_offset):
                return False

        # Then check property filters
        for prop, filter_data in self.filters.items():
            if not filter_data['active']:
                continue

            # Get the element's value for this property
            # Convert string property name to enum for comparison
            prop_enum = PTPropertyName.from_string(prop) if isinstance(prop, str) else prop

            if prop_enum == PTPropertyName.IONIZATION:
                value = elem.get('ie', 0)
            elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
                value = elem.get('electronegativity', 0)
            elif prop_enum == PTPropertyName.MELTING:
                value = elem.get('melting_point', 0)
            elif prop_enum == PTPropertyName.BOILING:
                value = elem.get('boiling_point', 0)
            elif prop_enum == PTPropertyName.RADIUS:
                value = elem.get('atomic_radius', 0)
            elif prop_enum == PTPropertyName.DENSITY:
                value = elem.get('density', 0)
            elif prop_enum == PTPropertyName.ELECTRON_AFFINITY:
                value = elem.get('electron_affinity', 0)
            elif prop_enum == PTPropertyName.VALENCE:
                value = elem.get('valence_electrons', 0)
            elif prop_enum == PTPropertyName.ATOMIC_NUMBER:
                value = elem.get('z', 0)
            elif PTPropertyName.is_wavelength_property(prop_enum):
                # All wavelength properties use the same underlying wavelength_nm data
                value = elem.get('wavelength_nm', 0)
            else:
                continue

            # Check if value is within range
            if value < filter_data['min'] or value > filter_data['max']:
                return False

        return True

    def _has_isotope_with_offset(self, elem, neutron_offset):
        """Check if element has an isotope with the specified neutron offset (N - Z)"""
        symbol = elem.get('symbol', '')
        z = elem.get('z', 0)

        isotopes = elem.get('isotopes', [])
        if not isotopes:
            # No isotope data - assume N = Z
            return neutron_offset == 0

        # Check if any isotope has the desired neutron offset
        for mass, abundance in isotopes:
            neutron_count = mass - z
            if neutron_count - z == neutron_offset:
                return True

        return False

    def create_circular_layout(self):
        """Create circular wedge layout with dynamic radii based on widget size"""
        # Calculate dynamic radii based on widget dimensions
        min_dimension = min(self.width(), self.height())
        max_radius = min_dimension / 2 * 0.85  # Use 85% of available radius

        # Calculate period radii dynamically
        num_periods = 7
        ring_thickness = max_radius / (num_periods + 1)

        period_radii = []
        for i in range(num_periods):
            r_inner = (i + 1) * ring_thickness
            r_outer = (i + 2) * ring_thickness
            period_radii.append((r_inner, r_outer))

        # Store the outermost radius for electron shell rendering
        self.outermost_radius = period_radii[-1][1]  # r_outer of period 7

        start_angle = -math.pi / 2

        self.elements = []
        current_z = 0
        for elem in self.base_elements:
            period_idx = elem['period'] - 1
            r_inner, r_outer = period_radii[period_idx]

            # Count elements in this period
            period_elements = [e for e in self.base_elements if e['period'] == elem['period']]
            num_elements = len(period_elements)
            elem_idx_in_period = period_elements.index(elem)

            angle_per_elem = (2 * math.pi) / num_elements
            angle_start = start_angle + elem_idx_in_period * angle_per_elem
            angle_end = angle_start + angle_per_elem
            angle_mid = (angle_start + angle_end) / 2

            self.elements.append({
                **elem,
                'layout': 'circular',
                'r_inner': r_inner,
                'r_outer': r_outer,
                'angle_start': angle_start,
                'angle_end': angle_end,
                'angle_mid': angle_mid
            })

    def create_spiral_layout(self):
        """
        Create spiral layout with main element positions on period circles.
        Isotopes are stored as radial offsets for rendering.
        """
        self.elements = []

        # Spiral parameters
        margin = 50
        width = self.width() - 2 * margin
        height = self.height() - 2 * margin

        # Calculate dynamic period radii
        num_periods = max(elem['period'] for elem in self.base_elements)
        available_radius = min(width, height) / 2 - 50
        base_radius = available_radius * 0.18
        ring_spacing = (available_radius - base_radius) / (num_periods - 1) if num_periods > 1 else 0

        period_radii = {}
        for period in range(1, num_periods + 1):
            period_radii[period] = base_radius + (period - 1) * ring_spacing

        # Spiral center
        spiral_center_x = width / 2
        spiral_center_y = height / 2

        # Angular spacing - 4 full rotations over all ELEMENTS (not isotopes)
        total_elements = len(self.base_elements)
        angular_spacing_per_element = (8 * math.pi) / max(total_elements, 1)

        element_positions = []
        current_angle = 0

        for elem_idx, elem in enumerate(self.base_elements):
            period = elem['period']
            base_radius_elem = period_radii[period]

            # Main element position is on the period circle
            spiral_angle = current_angle
            current_angle += angular_spacing_per_element

            # Element position on period circle (no radius variation for main line)
            x = spiral_center_x + base_radius_elem * math.cos(spiral_angle)
            y = spiral_center_y + base_radius_elem * math.sin(spiral_angle)

            # Get isotopes for this element
            isotopes = elem.get('isotopes', [])
            if not isotopes:
                isotopes = [(elem['z'] * 2, 100)]

            # Calculate isotope positions with radial offsets
            elem_isotope_data = []
            for iso_idx, (mass, abundance) in enumerate(isotopes):
                neutron_count = mass - elem['z']
                neutron_delta = neutron_count - elem['z']

                # Calculate radius offset based on neutron delta
                # Map to range [base_radius - ring_spacing/2, base_radius + ring_spacing/2]
                max_delta = max(abs(n - elem['z']) for n, _ in [(m - elem['z'], a) for m, a in isotopes])
                if max_delta > 0:
                    radius_offset = (neutron_delta / max_delta) * (ring_spacing / 2)
                else:
                    radius_offset = 0

                isotope_radius = base_radius_elem + radius_offset

                elem_isotope_data.append({
                    'angle': spiral_angle,
                    'radius': isotope_radius,
                    'base_radius': base_radius_elem,
                    'mass': mass,
                    'abundance': abundance,
                    'neutron_count': neutron_count,
                    'neutron_delta': neutron_delta,
                    'isotope_index': iso_idx
                })

            element_positions.append({
                'x': x,
                'y': y,
                'angle': spiral_angle,
                'radius': base_radius_elem,
                'base_radius': base_radius_elem,
                'elem': elem,
                'isotopes': elem_isotope_data,
                'element_index': elem_idx,
                'period': period,
                'ring_spacing': ring_spacing
            })

        # Store for rendering
        self.element_spiral_positions = element_positions
        self.period_radii = period_radii
        self.spiral_center = (spiral_center_x, spiral_center_y)
        self.ring_spacing = ring_spacing

        # Now create element entries for drawing
        for pos_data in element_positions:
            elem = pos_data['elem']
            self.elements.append({
                **elem,
                'layout': 'spiral',
                'x': pos_data['x'],
                'y': pos_data['y'],
                'angle': pos_data['angle'],
                'radius': pos_data['radius'],
                'base_radius': pos_data['base_radius'],
                'isotopes': pos_data['isotopes'],
                'has_element': True,
                'element_index': pos_data['element_index'],
                'period': pos_data['period'],
                'ring_spacing': pos_data['ring_spacing']
            })

        # Store the outermost radius for electron shell rendering
        self.outermost_radius = period_radii[max(period_radii.keys())]

    def create_serpentine_layout(self):
        """Create linear graph layout with configurable ordering and property lines"""
        # Use the LinearLayoutRenderer to create layout
        renderer = LinearLayoutRenderer(self.width(), self.height())
        self.elements = renderer.create_layout(
            self.base_elements,
            position_calculator=None,
            order_property=self.order_property
        )

        # Store renderer for painting
        self.linear_renderer = renderer
        self.period_boundaries = renderer.period_boundaries

    def get_order_value(self, elem):
        """Get the value to order elements by in linear mode"""
        prop_enum = PTPropertyName.from_string(self.order_property)

        if prop_enum == PTPropertyName.ATOMIC_NUMBER:
            return elem.get('z', 0)
        elif self.order_property == "ionization":
            return elem.get('ie', 0)
        elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
            return elem.get('electronegativity', 0)
        elif self.order_property == "melting":
            return elem.get('melting_point', 0)
        elif self.order_property == "boiling":
            return elem.get('boiling_point', 0)
        elif prop_enum == PTPropertyName.RADIUS:
            return elem.get('atomic_radius', 0)
        elif self.order_property == "density":
            return elem.get('density', 0)
        elif self.order_property == "electron_affinity":
            return elem.get('electron_affinity', 0)
        elif self.order_property == "valence":
            return elem.get('valence_electrons', 0)
        else:
            return elem.get('z', 0)

    def create_table_layout(self):
        """Create traditional periodic table layout - positions calculated dynamically from atomic properties"""
        self.elements = []

        # Dynamic calculation - NO hardcoded positions!
        calc = PositionCalculator()
        cell_size = 60
        margin_left = 50
        margin_top = 50

        for elem in self.base_elements:
            symbol = elem['symbol']
            z = elem['z']

            # Calculate position dynamically based on atomic number and properties
            row, col = calc.get_table_position(z, symbol)

            # Calculate pixel coordinates from grid position
            x = margin_left + (col - 1) * cell_size
            y = margin_top + (row - 1) * cell_size

            self.elements.append({
                **elem,
                'layout': 'table',
                'x': x,
                'y': y,
                'cell_size': cell_size,
                'grid_row': row,
                'grid_col': col
            })

    def _get_wavelength_mode(self, property_type):
        """Get wavelength display mode for a property type

        Args:
            property_type: PTEncodingType enum or string encoding type

        Returns:
            PTWavelengthMode enum (SPECTRUM for rainbow display or GRADIENT for A-B lerp)
        """
        # Convert string to enum if needed
        if isinstance(property_type, str):
            property_type = PTEncodingType.from_string(property_type)

        # Use the enum's helper method to get the attribute name
        attr_name = property_type.get_wavelength_mode_attr()
        return getattr(self, attr_name, PTWavelengthMode.SPECTRUM)

    def _get_property_gradient_colors(self, property_name, encoding_type="fill"):
        """Get the start and end gradient colors for a property (custom or smart defaults)

        Args:
            property_name: Name of the property (e.g., 'ionization', 'density')
            encoding_type: PTEncodingType enum or string encoding type
        """
        # Convert string to enum if needed
        if isinstance(encoding_type, str):
            encoding_type = PTEncodingType.from_string(encoding_type)

        # Check for custom colors first based on encoding type
        custom_start_attr = f"custom_{encoding_type.value}_gradient_start"
        custom_end_attr = f"custom_{encoding_type.value}_gradient_end"

        custom_start = getattr(self, custom_start_attr, None)
        custom_end = getattr(self, custom_end_attr, None)

        # If custom colors are set, use them
        if custom_start is not None and custom_end is not None:
            return (custom_start, custom_end)

        # Otherwise use smart defaults based on property type
        from periodica.core.pt_enums import PTPropertyName
        prop_enum = PTPropertyName.from_string(property_name)

        # Default colors based on property type
        if prop_enum in [PTPropertyName.MELTING, PTPropertyName.BOILING]:
            # Temperature properties: cool to warm (blue to red)
            return (QColor(50, 100, 255), QColor(255, 50, 50))
        elif prop_enum == PTPropertyName.IONIZATION:
            # Energy properties: purple to yellow
            return (QColor(120, 50, 200), QColor(255, 220, 50))
        elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
            # Electronegativity: green to magenta
            return (QColor(50, 200, 100), QColor(200, 50, 200))
        elif prop_enum == PTPropertyName.RADIUS:
            # Size: small=blue, large=orange
            return (QColor(80, 120, 255), QColor(255, 140, 50))
        elif prop_enum == PTPropertyName.DENSITY:
            # Density: light to heavy (cyan to brown)
            return (QColor(100, 200, 220), QColor(150, 100, 50))
        elif prop_enum == PTPropertyName.ELECTRON_AFFINITY:
            # Electron affinity: teal to pink
            return (QColor(50, 180, 180), QColor(255, 100, 150))
        else:
            # Default: cool to warm
            return (QColor(100, 150, 255), QColor(255, 150, 100))

    def _generate_gradient_color(self, value, min_value, max_value, property_name="", fade=0.0, encoding_type="fill"):
        """Generate a simple A-to-B gradient with white/black fading outside range

        Args:
            value: Current property value
            min_value: Minimum value for mapping (yellow tag min)
            max_value: Maximum value for mapping (yellow tag max)
            property_name: Name of property being mapped
            fade: Additional fade factor (0.0-1.0)
            encoding_type: Type of visual encoding (fill, border, ring, glow, symbol_text, atomic_number_text)
        """
        # Get the gradient colors for this property and encoding type
        color_start, color_end = self._get_property_gradient_colors(property_name, encoding_type)

        # Determine which range we're in
        if value < min_value:
            # Below min: fade from white to color_start
            if min_value > 0:
                fade_amount = 1.0 - ((min_value - value) / min_value)
                fade_amount = max(0, min(1, fade_amount))
            else:
                fade_amount = 0
            # Lerp from white to color_start
            r = int(255 * (1 - fade_amount) + color_start.red() * fade_amount)
            g = int(255 * (1 - fade_amount) + color_start.green() * fade_amount)
            b = int(255 * (1 - fade_amount) + color_start.blue() * fade_amount)
            color = QColor(r, g, b)
        elif value > max_value:
            # Above max: fade from color_end to black
            if max_value > 0:
                fade_amount = (value - max_value) / max_value
                fade_amount = max(0, min(1, fade_amount))
            else:
                fade_amount = 1
            # Lerp from color_end to black
            r = int(color_end.red() * (1 - fade_amount))
            g = int(color_end.green() * (1 - fade_amount))
            b = int(color_end.blue() * (1 - fade_amount))
            color = QColor(r, g, b)
        else:
            # Within range: simple A to B lerp
            if max_value > min_value:
                t = (value - min_value) / (max_value - min_value)
            else:
                t = 0.5
            # Lerp from color_start to color_end
            r = int(color_start.red() * (1 - t) + color_end.red() * t)
            g = int(color_start.green() * (1 - t) + color_end.green() * t)
            b = int(color_start.blue() * (1 - t) + color_end.blue() * t)
            color = QColor(r, g, b)

        color.setAlpha(int(255 * (1.0 - fade)))
        return color

    def get_property_color(self, elem, property_name, property_type="fill"):
        """Get color based on property name and type (for per-property fade)

        Args:
            elem: Element dictionary
            property_name: Name of the property ("atomic_number", "wavelength", etc.)
            property_type: PTEncodingType enum or string encoding type
        """
        # Convert string to enum if needed
        if isinstance(property_type, str):
            property_type = PTEncodingType.from_string(property_type)

        # Get the appropriate fade value for this property type
        fade_attr = f"{property_type.value}_{'fade' if property_type == PTEncodingType.FILL else 'color_fade'}"
        fade = getattr(self, fade_attr, 0.0)

        # Get the appropriate color range for this property type
        color_range_min_attr = f"{property_type.value}_color_range_min"
        color_range_max_attr = f"{property_type.value}_color_range_max"

        color_range_min = getattr(self, color_range_min_attr, self.color_range_min)
        color_range_max = getattr(self, color_range_max_attr, self.color_range_max)

        # Return default gray-blue color for "none" property
        prop_enum = PTPropertyName.from_string(property_name)

        if prop_enum == PTPropertyName.NONE:
            return QColor(100, 100, 150, 255)

        if prop_enum == PTPropertyName.ATOMIC_NUMBER:
            # Color by atomic number (1-118)
            z = elem['z']
            # Map 1-118 to 0-360 hue (rainbow spectrum)
            hue = int((z / 118.0) * 360)
            color = QColor.fromHsv(hue, 220, 255)
            color.setAlpha(int(255 * (1.0 - fade)))
            return color
        elif property_name == "ionization":
            # Use configurable color range instead of hardcoded get_ie_color
            return self._generate_gradient_color(elem['ie'], color_range_min, color_range_max, property_name, fade, property_type)
        elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
            # Use configurable color range instead of hardcoded get_electroneg_color
            return self._generate_gradient_color(elem['electronegativity'], color_range_min, color_range_max, property_name, fade, property_type)
        elif prop_enum == PTPropertyName.BLOCK:
            color = QColor(elem['block_color'])
            color.setAlpha(int(255 * (1.0 - fade)))
            return color
        elif prop_enum == PTPropertyName.WAVELENGTH:
            # Legacy: uses emission wavelength
            # Check wavelength mode for this property type
            mode = self._get_wavelength_mode(property_type)
            if mode == PTWavelengthMode.GRADIENT:
                return self._generate_gradient_color(elem[PTElementDataKey.WAVELENGTH_NM.value], color_range_min, color_range_max, property_name, fade, property_type)
            else:
                return wavelength_to_rgb(elem[PTElementDataKey.WAVELENGTH_NM.value], color_range_min, color_range_max, fade)
        elif prop_enum == PTPropertyName.EMISSION_WAVELENGTH:
            # Most prominent emission line (may be UV/IR)
            mode = self._get_wavelength_mode(property_type)
            if mode == PTWavelengthMode.GRADIENT:
                return self._generate_gradient_color(elem[PTElementDataKey.EMISSION_WAVELENGTH.value], color_range_min, color_range_max, property_name, fade, property_type)
            else:
                return wavelength_to_rgb(elem[PTElementDataKey.EMISSION_WAVELENGTH.value], color_range_min, color_range_max, fade)
        elif prop_enum == PTPropertyName.VISIBLE_EMISSION_WAVELENGTH:
            # Most prominent visible emission line (flame test colors)
            mode = self._get_wavelength_mode(property_type)
            if mode == PTWavelengthMode.GRADIENT:
                return self._generate_gradient_color(elem[PTElementDataKey.VISIBLE_EMISSION_WAVELENGTH.value], color_range_min, color_range_max, property_name, fade, property_type)
            else:
                return wavelength_to_rgb(elem[PTElementDataKey.VISIBLE_EMISSION_WAVELENGTH.value], color_range_min, color_range_max, fade)
        elif prop_enum == PTPropertyName.IONIZATION_WAVELENGTH:
            # Wavelength corresponding to ionization energy
            mode = self._get_wavelength_mode(property_type)
            if mode == PTWavelengthMode.GRADIENT:
                return self._generate_gradient_color(elem[PTElementDataKey.IONIZATION_WAVELENGTH.value], color_range_min, color_range_max, property_name, fade, property_type)
            else:
                return wavelength_to_rgb(elem[PTElementDataKey.IONIZATION_WAVELENGTH.value], color_range_min, color_range_max, fade)
        elif prop_enum == PTPropertyName.SPECTRUM:
            # Use spectrum background - blend colors from all emission lines
            # This creates a mixed color representing the element's spectrum
            if PTElementDataKey.SPECTRUM_LINES.value not in elem or not elem[PTElementDataKey.SPECTRUM_LINES.value]:
                # Fallback to primary emission wavelength if no spectrum data
                mode = self._get_wavelength_mode(property_type)
                if mode == PTWavelengthMode.GRADIENT:
                    return self._generate_gradient_color(elem[PTElementDataKey.WAVELENGTH_NM.value], color_range_min, color_range_max, property_name, fade, property_type)
                else:
                    return wavelength_to_rgb(elem[PTElementDataKey.WAVELENGTH_NM.value], color_range_min, color_range_max, fade)

            # Check wavelength mode
            mode = self._get_wavelength_mode(property_type)

            if mode == PTWavelengthMode.GRADIENT:
                # Use A-B gradient: calculate average wavelength weighted by intensity
                total_wl = 0.0
                total_weight = 0.0

                for wavelength, intensity in elem[PTElementDataKey.SPECTRUM_LINES.value]:
                    # Only include lines within the mapping range
                    if wavelength < color_range_min or wavelength > color_range_max:
                        continue

                    total_wl += wavelength * intensity
                    total_weight += intensity

                if total_weight > 0:
                    avg_wavelength = total_wl / total_weight
                    return self._generate_gradient_color(avg_wavelength, color_range_min, color_range_max, property_name, fade, property_type)
                else:
                    # No lines in range, return neutral color with fade
                    return QColor(128, 128, 128, int(255 * (1.0 - fade)))
            else:
                # Use rainbow spectrum: blend colors from all emission lines weighted by intensity
                total_r, total_g, total_b = 0.0, 0.0, 0.0
                total_weight = 0.0

                for wavelength, intensity in elem[PTElementDataKey.SPECTRUM_LINES.value]:
                    # Only include lines within the mapping range
                    if wavelength < color_range_min or wavelength > color_range_max:
                        continue

                    # Get color for this wavelength (with remapping, but NO fade yet - we'll apply it to final color)
                    color = wavelength_to_rgb(wavelength, color_range_min, color_range_max, 0.0)
                    weight = intensity

                    total_r += color.red() * weight
                    total_g += color.green() * weight
                    total_b += color.blue() * weight
                    total_weight += weight

                if total_weight > 0:
                    # Return weighted average color with fade applied
                    final_color = QColor(
                        int(total_r / total_weight),
                        int(total_g / total_weight),
                        int(total_b / total_weight)
                    )
                    # Apply fade to final blended color
                    final_color.setAlpha(int(255 * (1.0 - fade)))
                    return final_color
                else:
                    # No lines in range, return neutral color with fade
                    return QColor(128, 128, 128, int(255 * (1.0 - fade)))
        elif property_name == "melting":
            # Use configurable color range instead of hardcoded get_melting_color
            return self._generate_gradient_color(elem['melting_point'], color_range_min, color_range_max, property_name, fade, property_type)
        elif prop_enum == PTPropertyName.RADIUS:
            # Use configurable color range instead of hardcoded get_radius_color
            return self._generate_gradient_color(elem['atomic_radius'], color_range_min, color_range_max, property_name, fade, property_type)
        elif property_name == "density":
            # Use configurable color range instead of hardcoded get_density_color
            # Density uses log scale
            log_density = math.log10(max(elem.get('density', 1.0), 0.0001))
            return self._generate_gradient_color(log_density, color_range_min, color_range_max, property_name, fade, property_type)
        elif property_name == "boiling":
            # Use configurable color range instead of hardcoded get_boiling_color
            return self._generate_gradient_color(elem.get('boiling_point', 300), color_range_min, color_range_max, property_name, fade, property_type)
        elif property_name == "electron_affinity":
            # Use configurable color range instead of hardcoded get_electron_affinity_color
            return self._generate_gradient_color(elem.get('electron_affinity', 0), color_range_min, color_range_max, property_name, fade, property_type)
        elif property_name == "valence":
            # Color by valence electron count
            valence = elem.get('valence_electrons', 1)
            hue = (valence * 25) % 360
            color = QColor.fromHsv(hue, 200, 255)
            color.setAlpha(int(255 * (1.0 - fade)))
            return color
        color = QColor(150, 150, 150)
        color.setAlpha(int(255 * (1.0 - fade)))
        return color

    def get_border_width(self, elem):
        """Get border width based on border size property"""
        # Use border_size_property (the correct one) with fallback to legacy border_property
        property_name = getattr(self, 'border_size_property', self.border_property)
        prop_enum = PTPropertyName.from_string(property_name)

        if prop_enum == PTPropertyName.NONE:
            return 1

        # Get property value
        value = self._get_property_value(elem, property_name)

        # Special handling for density (log scale)
        if prop_enum == PTPropertyName.DENSITY:
            value = math.log10(max(value, 0.0001))

        # Use border_size_property_min/max for INPUT range (set by yellow tags)
        # Use border_size_min/max for OUTPUT range (always 1-6 pixels)
        input_min = self.border_size_property_min
        input_max = self.border_size_property_max

        # Normalize to 0-1 based on INPUT range
        if input_max > input_min:
            normalized = (value - input_min) / (input_max - input_min)
            normalized = max(0, min(1, normalized))
        else:
            normalized = 0

        # Map to OUTPUT range (always 1-6 pixels)
        return self.border_size_min + (self.border_size_max - self.border_size_min) * normalized

    def _get_property_value(self, elem, property_name):
        """Get raw property value from element"""
        prop_enum = PTPropertyName.from_string(property_name)

        if prop_enum == PTPropertyName.ATOMIC_NUMBER:
            return elem.get('z', 0)
        elif prop_enum == PTPropertyName.RADIUS:
            return elem.get('atomic_radius', 0)
        elif prop_enum == PTPropertyName.IONIZATION:
            return elem.get('ie', 0)
        elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
            return elem.get('electronegativity', 0)
        elif prop_enum == PTPropertyName.MELTING:
            return elem.get('melting_point', 0)
        elif prop_enum == PTPropertyName.BOILING:
            return elem.get('boiling_point', 0)
        elif prop_enum == PTPropertyName.DENSITY:
            return elem.get('density', 0)
        elif prop_enum == PTPropertyName.ELECTRON_AFFINITY:
            return elem.get('electron_affinity', 0)
        elif prop_enum == PTPropertyName.VALENCE:
            return elem.get('valence_electrons', 0)
        return 0

    def _map_property_to_range(self, elem, property_name, input_min, input_max, output_min, output_max):
        """Map property value to output range using configurable input range"""
        value = self._get_property_value(elem, property_name)

        # Normalize to 0-1 based on input range
        if input_max > input_min:
            normalized = (value - input_min) / (input_max - input_min)
            normalized = max(0, min(1, normalized))  # Clamp to 0-1
        else:
            normalized = 0

        # Map to output range
        return output_min + (output_max - output_min) * normalized

    def get_inner_ring_size(self, elem):
        """Get inner ring size (0.0-1.0 fraction) based on ring_size_property"""
        prop_enum = PTPropertyName.from_string(self.ring_size_property)

        if prop_enum == PTPropertyName.NONE:
            return 0.3  # Default 30%

        # Get property value
        value = self._get_property_value(elem, self.ring_size_property)

        # Special handling for density (log scale)
        if prop_enum == PTPropertyName.DENSITY:
            value = math.log10(max(value, 0.0001))

        # Use ring_size_property_min/max for INPUT range (set by yellow tags)
        # Use ring_size_min/max for OUTPUT range (always 0.1-0.5 fraction)
        input_min = self.ring_size_property_min
        input_max = self.ring_size_property_max

        # Normalize to 0-1 based on INPUT range
        if input_max > input_min:
            normalized = (value - input_min) / (input_max - input_min)
            normalized = max(0, min(1, normalized))
        else:
            normalized = 0

        # Map to OUTPUT range (always 0.1-0.5 fraction)
        return self.ring_size_min + (self.ring_size_max - self.ring_size_min) * normalized

    def get_glow_radius_percent(self, elem):
        """Get glow radius as percentage of widget size (0.0-1.0) based on glow_radius_property"""
        prop_enum = PTPropertyName.from_string(self.glow_radius_property)

        if prop_enum == PTPropertyName.NONE:
            return 0.05  # Default 5%
        elif prop_enum == PTPropertyName.ATOMIC_NUMBER:
            return 0.02 + 0.08 * (elem['z'] / 118.0)  # 2%-10% range
        elif prop_enum == PTPropertyName.RADIUS:
            return 0.02 + 0.08 * ((elem['atomic_radius'] - 30) / 320)
        elif self.glow_radius_property == "ionization":
            return 0.02 + 0.08 * ((elem['ie'] - 3.5) / (25.0 - 3.5))
        elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
            if elem['electronegativity'] == 0:
                return 0.02
            return 0.02 + 0.08 * (elem['electronegativity'] / 4.0)
        elif self.glow_radius_property == "melting":
            return 0.02 + 0.08 * min(elem['melting_point'] / 4000.0, 1.0)
        elif self.glow_radius_property == "boiling":
            return 0.02 + 0.08 * min(elem.get('boiling_point', 300) / 4000.0, 1.0)
        elif self.glow_radius_property == "density":
            log_density = math.log10(max(elem.get('density', 1.0), 0.0001))
            normalized = (log_density + 4) / 5.3
            return 0.02 + 0.08 * max(0, min(1, normalized))
        elif self.glow_radius_property == "electron_affinity":
            affinity = elem.get('electron_affinity', 0)
            normalized = (affinity + 10) / 360
            return 0.02 + 0.08 * max(0, min(1, normalized))
        elif self.glow_radius_property == "valence":
            valence = elem.get('valence_electrons', 1)
            return 0.02 + 0.08 * (valence / 8.0)
        return 0.05

    def get_glow_intensity(self, elem):
        """Get glow intensity (0.0-1.0) based on glow_intensity_property"""
        prop_enum = PTPropertyName.from_string(self.glow_intensity_property)

        if prop_enum == PTPropertyName.NONE:
            return 0.5  # Default 50%
        elif prop_enum == PTPropertyName.ATOMIC_NUMBER:
            return elem['z'] / 118.0
        elif prop_enum == PTPropertyName.RADIUS:
            return (elem['atomic_radius'] - 30) / 320
        elif self.glow_intensity_property == "ionization":
            return (elem['ie'] - 3.5) / (25.0 - 3.5)
        elif prop_enum == PTPropertyName.ELECTRONEGATIVITY:
            if elem['electronegativity'] == 0:
                return 0
            return elem['electronegativity'] / 4.0
        elif self.glow_intensity_property == "melting":
            return min(elem['melting_point'] / 4000.0, 1.0)
        elif self.glow_intensity_property == "boiling":
            return min(elem.get('boiling_point', 300) / 4000.0, 1.0)
        elif self.glow_intensity_property == "density":
            log_density = math.log10(max(elem.get('density', 1.0), 0.0001))
            return max(0, min(1, (log_density + 4) / 5.3))
        elif self.glow_intensity_property == "electron_affinity":
            affinity = elem.get('electron_affinity', 0)
            return max(0, min(1, (affinity + 10) / 360))
        elif self.glow_intensity_property == "valence":
            valence = elem.get('valence_electrons', 1)
            return valence / 8.0
        return 0.5

    def get_glow_params(self, elem):
        """Get glow size and intensity based on glow property (DEPRECATED - kept for compatibility)"""
        prop_enum = PTPropertyName.from_string(self.glow_property)

        if prop_enum == PTPropertyName.NONE:
            return 0, 0
        elif self.glow_property == "melting":
            intensity = min(elem['melting_point'] / 4000.0, 1.0)
            size = 20 + 30 * intensity
            return size, intensity
        elif self.glow_property == "ionization":
            intensity = (elem['ie'] - 3.5) / (25.0 - 3.5)
            size = 20 + 30 * intensity
            return size, intensity
        elif self.glow_property == "radius":
            intensity = (elem['atomic_radius'] - 30) / 320
            size = 20 + 30 * intensity
            return size, intensity
        elif self.glow_property == "boiling":
            intensity = min(elem.get('boiling_point', 300) / 4000.0, 1.0)
            size = 20 + 30 * intensity
            return size, intensity
        elif self.glow_property == "density":
            log_density = math.log10(max(elem.get('density', 1.0), 0.0001))
            intensity = max(0, min(1, (log_density + 4) / 5.3))
            size = 20 + 30 * intensity
            return size, intensity
        elif self.glow_property == "electron_affinity":
            affinity = elem.get('electron_affinity', 0)
            intensity = max(0, min(1, (affinity + 10) / 360))
            size = 20 + 30 * intensity
            return size, intensity
        elif self.glow_property == "electronegativity":
            if elem['electronegativity'] == 0:
                return 0, 0
            intensity = elem['electronegativity'] / 4.0
            size = 20 + 30 * intensity
            return size, intensity
        elif self.glow_property == "valence":
            valence = elem.get('valence_electrons', 1)
            intensity = valence / 8.0
            size = 20 + 30 * intensity
            return size, intensity
        return 0, 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Cosmic background
        gradient = QRadialGradient(self.width()/2, self.height()/2,
                                  max(self.width(), self.height())/2)
        gradient.setColorAt(0, QColor(20, 20, 40))
        gradient.setColorAt(1, QColor(5, 5, 15))
        painter.fillRect(self.rect(), QBrush(gradient))

        if self.layout_mode == PTLayoutMode.CIRCULAR:
            self.paint_circular(painter)
        elif self.layout_mode == PTLayoutMode.SPIRAL:
            self.paint_spiral(painter)
        elif self.layout_mode == PTLayoutMode.SERPENTINE:
            self.paint_serpentine(painter)
        elif self.layout_mode == PTLayoutMode.TABLE:
            self.paint_table(painter)

    def paint_circular(self, painter):
        """Paint circular wedge layout"""
        # Apply zoom and pan transformations
        painter.save()
        painter.translate(self.pan_x, self.pan_y)
        painter.scale(self.zoom_level, self.zoom_level)

        center_x = self.width() / 2
        center_y = self.height() / 2

        # Draw electron probability cloud for selected element
        if self.selected_element and self.show_orbital_cloud:
            self.draw_electron_probability_cloud(painter, center_x, center_y)

        # Draw period guide rings (hide when showing subatomic particles)
        if not self.show_subatomic_particles:
            painter.setPen(QPen(QColor(60, 60, 100, 80), 1, Qt.PenStyle.DotLine))
            for i in range(1, 8):
                r = 45 + i * 52
                painter.drawEllipse(QPointF(center_x, center_y), r, r)

        # Draw element table if enabled
        if self.show_element_table:
            # If showing subatomic particles, only draw selected element
            if self.show_subatomic_particles and self.selected_element:
                passes_filter = self.passes_filters(self.selected_element)
                self.draw_circular_element(painter, self.selected_element, center_x, center_y, passes_filter)
            else:
                # Draw all elements normally
                for elem in self.elements:
                    passes_filter = self.passes_filters(elem)
                    self.draw_circular_element(painter, elem, center_x, center_y, passes_filter)

        # Draw subatomic particles overlay (before shells)
        if self.selected_element:
            self.draw_subatomic_particles(painter, center_x, center_y)

        # Draw electron shells for selected element (on top)
        if self.selected_element:
            self.draw_electron_shells(painter, center_x, center_y)

        # Draw centered element display when an element is selected
        if self.selected_element:
            self.draw_centered_element_display(painter, center_x, center_y)

        painter.restore()

    def draw_circular_element(self, painter, elem, center_x, center_y, passes_filter=True):
        """Draw circular wedge element"""
        # Filtered elements are drawn as grey transparent boxes with no details
        if not passes_filter:
            # Create simple wedge path
            path = QPainterPath()

            x1 = center_x + elem['r_inner'] * math.cos(elem['angle_start'])
            y1 = center_y + elem['r_inner'] * math.sin(elem['angle_start'])
            path.moveTo(x1, y1)

            rect_inner = QRectF(center_x - elem['r_inner'], center_y - elem['r_inner'],
                               elem['r_inner'] * 2, elem['r_inner'] * 2)
            span_angle = math.degrees(elem['angle_end'] - elem['angle_start'])
            path.arcTo(rect_inner, -math.degrees(elem['angle_start']), -span_angle)

            x2 = center_x + elem['r_outer'] * math.cos(elem['angle_end'])
            y2 = center_y + elem['r_outer'] * math.sin(elem['angle_end'])
            path.lineTo(x2, y2)

            rect_outer = QRectF(center_x - elem['r_outer'], center_y - elem['r_outer'],
                               elem['r_outer'] * 2, elem['r_outer'] * 2)
            path.arcTo(rect_outer, -math.degrees(elem['angle_end']), span_angle)
            path.closeSubpath()

            # Fill with grey transparent color
            grey_color = QColor(100, 100, 100, 60)
            painter.fillPath(path, grey_color)

            # Draw border
            painter.setPen(QPen(QColor(80, 80, 80, 80), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            return  # Skip all other drawing for filtered elements

        # Normal element drawing (passes filter)
        alpha = 255

        # Create wedge path
        path = QPainterPath()

        x1 = center_x + elem['r_inner'] * math.cos(elem['angle_start'])
        y1 = center_y + elem['r_inner'] * math.sin(elem['angle_start'])
        path.moveTo(x1, y1)

        rect_inner = QRectF(center_x - elem['r_inner'], center_y - elem['r_inner'],
                           elem['r_inner'] * 2, elem['r_inner'] * 2)
        span_angle = math.degrees(elem['angle_end'] - elem['angle_start'])
        path.arcTo(rect_inner, -math.degrees(elem['angle_start']), -span_angle)

        x2 = center_x + elem['r_outer'] * math.cos(elem['angle_end'])
        y2 = center_y + elem['r_outer'] * math.sin(elem['angle_end'])
        path.lineTo(x2, y2)

        rect_outer = QRectF(center_x - elem['r_outer'], center_y - elem['r_outer'],
                           elem['r_outer'] * 2, elem['r_outer'] * 2)
        path.arcTo(rect_outer, -math.degrees(elem['angle_end']), span_angle)
        path.closeSubpath()

        r_mid = (elem['r_inner'] + elem['r_outer']) / 2
        x_center = center_x + r_mid * math.cos(elem['angle_mid'])
        y_center = center_y + r_mid * math.sin(elem['angle_mid'])

        # Draw spectrum bar (DEPRECATED - this was the old spectrum visualization)
        # Now we use "Show Spectrum Lines" overlay instead
        # Only draw if the legacy flag is enabled (not used in UI anymore)
        if self.show_spectrum_background and 'spectrum_lines' in elem:
            painter.save()
            painter.setClipPath(path)  # Clip to wedge shape

            # Create a rectangle for the spectrum bar at the bottom of the wedge
            wedge_height = elem['r_outer'] - elem['r_inner']
            bar_height = wedge_height * 0.3  # Use bottom 30% of wedge for spectrum
            bar_r_outer = elem['r_outer']
            bar_r_inner = elem['r_outer'] - bar_height

            # We need to approximate the wedge section as a rectangle for spectrum drawing
            # Use the mid-angle to position the bar
            angle_mid = elem['angle_mid']
            angle_span = elem['angle_end'] - elem['angle_start']

            # Calculate approximate rectangular region at outer edge
            bar_x = center_x + (bar_r_inner + bar_r_outer) / 2 * math.cos(angle_mid)
            bar_y = center_y + (bar_r_inner + bar_r_outer) / 2 * math.sin(angle_mid)
            bar_width = angle_span * r_mid  # Arc length approximation

            # Create rect for spectrum bar (rotated to follow wedge orientation)
            spectrum_rect = QRectF(bar_x - bar_width / 2, bar_y - bar_height / 2,
                                  bar_width, bar_height)

            # Rotate painter to align with wedge
            painter.translate(bar_x, bar_y)
            painter.rotate(math.degrees(angle_mid) + 90)  # +90 to align with radial direction
            painter.translate(-bar_x, -bar_y)

            draw_spectrum_bar(painter, spectrum_rect, elem['spectrum_lines'],
                            self.show_prominent_spectrum_only)

            painter.restore()

        # Get fill color (already has fade alpha applied)
        fill_color = self.get_property_color(elem, self.fill_property, "fill")
        # Combine fade alpha with scene alpha
        fade_alpha = fill_color.alpha()
        combined_alpha = int((fade_alpha / 255.0) * alpha)
        fill_color.setAlpha(combined_alpha)

        # Highlight hovered and selected elements (unless showing subatomic particles)
        if elem == self.hovered_element and not self.show_subatomic_particles:
            fill_color = fill_color.lighter(130)
        if elem == self.selected_element and not self.show_subatomic_particles:
            fill_color = fill_color.lighter(150)

        # External Glow (drawn before main shape)
        glow_radius_pct = self.get_glow_radius_percent(elem)
        glow_intensity = self.get_glow_intensity(elem)
        if glow_radius_pct > 0 and passes_filter and self.glow_type == "external":
            # Enhance glow for hovered/selected (unless showing subatomic particles)
            if (elem == self.hovered_element or elem == self.selected_element) and not self.show_subatomic_particles:
                glow_radius_pct *= 1.5
                glow_intensity *= 1.2
            # External glow as circle around the widget
            glow_color = self.get_property_color(elem, self.glow_property, "glow")
            # Calculate glow size as percentage of widget radial extent
            widget_radius = elem['r_outer']
            glow_size = widget_radius * glow_radius_pct
            glow_radius = elem['r_outer'] + glow_size
            glow_grad = QRadialGradient(x_center, y_center, glow_radius)
            glow_c = QColor(glow_color)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(int(150 * glow_intensity * (alpha / 255)))
            glow_grad.setColorAt(0.8, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x_center, y_center), glow_radius, glow_radius)

        # Inner ring (drawn as split of main widget)
        inner_ring_fraction = self.get_inner_ring_size(elem)
        if self.ring_property != "none" and inner_ring_fraction > 0:
            # Calculate ring boundary using per-element fraction
            radial_thickness = elem['r_outer'] - elem['r_inner']
            ring_thickness = radial_thickness * inner_ring_fraction
            r_ring_outer = elem['r_inner'] + ring_thickness

            # Create inner ring path
            ring_path = QPainterPath()
            x1_ring = center_x + elem['r_inner'] * math.cos(elem['angle_start'])
            y1_ring = center_y + elem['r_inner'] * math.sin(elem['angle_start'])
            ring_path.moveTo(x1_ring, y1_ring)

            rect_inner_ring = QRectF(center_x - elem['r_inner'], center_y - elem['r_inner'],
                                     elem['r_inner'] * 2, elem['r_inner'] * 2)
            ring_path.arcTo(rect_inner_ring, -math.degrees(elem['angle_start']), -span_angle)

            x2_ring = center_x + r_ring_outer * math.cos(elem['angle_end'])
            y2_ring = center_y + r_ring_outer * math.sin(elem['angle_end'])
            ring_path.lineTo(x2_ring, y2_ring)

            rect_outer_ring = QRectF(center_x - r_ring_outer, center_y - r_ring_outer,
                                     r_ring_outer * 2, r_ring_outer * 2)
            ring_path.arcTo(rect_outer_ring, -math.degrees(elem['angle_end']), span_angle)
            ring_path.closeSubpath()

            # Fill inner ring
            ring_color = self.get_property_color(elem, self.ring_property, "ring")
            # Combine fade alpha with scene alpha
            fade_alpha_ring = ring_color.alpha()
            combined_alpha_ring = int((fade_alpha_ring / 255.0) * alpha)
            ring_color.setAlpha(combined_alpha_ring)
            painter.fillPath(ring_path, ring_color)

            # Update path for main fill (exclude inner ring)
            path = QPainterPath()
            x1_main = center_x + r_ring_outer * math.cos(elem['angle_start'])
            y1_main = center_y + r_ring_outer * math.sin(elem['angle_start'])
            path.moveTo(x1_main, y1_main)

            rect_main_inner = QRectF(center_x - r_ring_outer, center_y - r_ring_outer,
                                     r_ring_outer * 2, r_ring_outer * 2)
            path.arcTo(rect_main_inner, -math.degrees(elem['angle_start']), -span_angle)

            x2_main = center_x + elem['r_outer'] * math.cos(elem['angle_end'])
            y2_main = center_y + elem['r_outer'] * math.sin(elem['angle_end'])
            path.lineTo(x2_main, y2_main)

            rect_outer = QRectF(center_x - elem['r_outer'], center_y - elem['r_outer'],
                               elem['r_outer'] * 2, elem['r_outer'] * 2)
            path.arcTo(rect_outer, -math.degrees(elem['angle_end']), span_angle)
            path.closeSubpath()

        # Main wedge fill
        # Check if we should use spectrum gradient instead of solid color
        if (self.fill_property == PTPropertyName.SPECTRUM.value and
            'spectrum_lines' in elem and elem['spectrum_lines']):
            # Create gradient from inner to outer radius showing spectrum lines
            spectrum_gradient = self.create_spectrum_gradient(
                elem, center_x, center_y, self.fill_color_range_min, self.fill_color_range_max
            )
            painter.fillPath(path, QBrush(spectrum_gradient))
        else:
            # Normal solid/radial gradient fill
            wedge_gradient = QRadialGradient(x_center, y_center, elem['r_outer'] - elem['r_inner'])
            bright_color = fill_color.lighter(115)
            wedge_gradient.setColorAt(0, bright_color)
            wedge_gradient.setColorAt(1, fill_color)
            painter.fillPath(path, QBrush(wedge_gradient))

        # Internal Glow (drawn after main shape, inside the widget)
        if glow_radius_pct > 0 and passes_filter and self.glow_type == "internal":
            glow_intensity_adj = glow_intensity
            glow_radius_pct_adj = glow_radius_pct
            if elem == self.hovered_element or elem == self.selected_element:
                glow_radius_pct_adj *= 1.5
                glow_intensity_adj *= 1.2
            # Internal glow within the widget bounds
            glow_color = self.get_property_color(elem, self.glow_property, "glow")
            # Calculate glow size as percentage of radial extent
            radial_extent = elem['r_outer'] - elem['r_inner']
            glow_size = radial_extent * glow_radius_pct_adj
            # Constrain glow to widget interior
            max_glow = radial_extent * 0.8
            constrained_glow = min(glow_size, max_glow)
            glow_grad = QRadialGradient(x_center, y_center, constrained_glow)
            glow_c = QColor(glow_color)
            glow_c.setAlpha(int(120 * glow_intensity_adj * (alpha / 255)))
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            # Clip to wedge path
            painter.save()
            painter.setClipPath(path)
            painter.drawEllipse(QPointF(x_center, y_center), constrained_glow, constrained_glow)
            painter.restore()

        # Isotope visualization (if enabled)
        if self.show_isotopes:
            isotopes = elem.get('isotopes', [])
            if isotopes:
                # Draw isotope markers as small circles along the arc
                num_isotopes = len(isotopes)
                for iso_idx, (mass, abundance) in enumerate(isotopes):
                    # Position along the wedge
                    iso_factor = (iso_idx + 1) / (num_isotopes + 1)
                    r_iso = elem['r_inner'] + iso_factor * (elem['r_outer'] - elem['r_inner'])

                    # Angle position (slightly offset for visibility)
                    angle_iso = elem['angle_mid']

                    x_iso = center_x + r_iso * math.cos(angle_iso)
                    y_iso = center_y + r_iso * math.sin(angle_iso)

                    # Size based on abundance
                    iso_size = 2 + (abundance / 100) * 4

                    # Color based on neutron count
                    neutron_count = mass - elem['z']
                    iso_color = QColor(150 + neutron_count * 5, 150 + neutron_count * 3, 255, 180)

                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(iso_color))
                    painter.drawEllipse(QPointF(x_iso, y_iso), iso_size, iso_size)

                    # Draw abundance bar
                    if abundance > 20:
                        bar_length = (abundance / 100) * 15
                        angle_perp = angle_iso + math.pi / 2
                        bar_x1 = x_iso - bar_length/2 * math.cos(angle_perp)
                        bar_y1 = y_iso - bar_length/2 * math.sin(angle_perp)
                        bar_x2 = x_iso + bar_length/2 * math.cos(angle_perp)
                        bar_y2 = y_iso + bar_length/2 * math.sin(angle_perp)

                        painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
                        painter.drawLine(QPointF(bar_x1, bar_y1), QPointF(bar_x2, bar_y2))

        # Border
        border_width = self.get_border_width(elem)
        border_width = max(1, min(6, border_width))
        if elem == self.selected_element and not self.show_subatomic_particles:
            border_width += 2

        # Get border color from property
        # DEBUG: Print what property is being used for border
        if elem.get('z') == 6:  # Carbon for debugging
            pass  # print(f"Border color property: {self.border_color_property}")
        border_color = self.get_property_color(elem, self.border_color_property, "border")
        # Increase alpha for selected/hovered elements
        if (elem == self.hovered_element or elem == self.selected_element) and not self.show_subatomic_particles:
            current_alpha = border_color.alpha()
            border_color.setAlpha(min(255, int(current_alpha * 1.5)))
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Text with colored fills and white borders
        # Element Symbol
        symbol_text_color = self.get_property_color(elem, self.symbol_text_color_property, "symbol_text")
        font = QFont('Arial', 9 if elem['period'] < 6 else 8, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = QRectF(x_center - 25, y_center - 15, 50, 18)

        # Draw symbol with white border
        symbol_path = QPainterPath()
        symbol_path.addText(text_rect.left() + text_rect.width()/2 - painter.fontMetrics().horizontalAdvance(elem['symbol'])/2,
                           text_rect.top() + text_rect.height()/2 + painter.fontMetrics().ascent()/2,
                           font, elem['symbol'])
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(symbol_path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(symbol_text_color))
        painter.drawPath(symbol_path)

        # Atomic Number
        atomic_num_text_color = self.get_property_color(elem, self.atomic_number_text_color_property, "atomic_number_text")
        font_tiny = QFont('Arial', 5)
        painter.setFont(font_tiny)
        num_rect = QRectF(x_center - 25, y_center + 5, 50, 12)

        # Draw atomic number with white border
        num_path = QPainterPath()
        num_str = str(elem['z'])
        num_path.addText(num_rect.left() + num_rect.width()/2 - painter.fontMetrics().horizontalAdvance(num_str)/2,
                        num_rect.top() + num_rect.height()/2 + painter.fontMetrics().ascent()/2,
                        font_tiny, num_str)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(num_path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(atomic_num_text_color))
        painter.drawPath(num_path)

        # Spectrum lines overlay (drawn last, on top of everything)
        if self.show_spectrum_lines and 'spectrum_lines' in elem and elem['spectrum_lines']:
            self.draw_spectrum_lines_overlay(painter, elem, path, center_x, center_y)

    def create_spectrum_gradient(self, elem, center_x, center_y, range_min, range_max):
        """Create a linear gradient that shows spectrum lines as a lerped rainbow across the wedge"""
        # Create linear gradient from angle_start to angle_end
        # Map from inner radius along the angular direction
        angle_mid = elem['angle_mid']
        r_mid = (elem['r_inner'] + elem['r_outer']) / 2

        # Start and end points along the angular span
        angle_start = elem['angle_start']
        angle_end = elem['angle_end']

        # Create points at the angular start and end
        x1 = center_x + r_mid * math.cos(angle_start)
        y1 = center_y + r_mid * math.sin(angle_start)
        x2 = center_x + r_mid * math.cos(angle_end)
        y2 = center_y + r_mid * math.sin(angle_end)

        gradient = QLinearGradient(x1, y1, x2, y2)

        # Get spectrum lines sorted by wavelength
        spectrum_lines = sorted(elem['spectrum_lines'], key=lambda x: x[0])

        # Filter to only lines within range
        visible_lines = [(wl, intensity) for wl, intensity in spectrum_lines
                        if range_min <= wl <= range_max]

        if not visible_lines:
            # No lines in range, use neutral color
            gradient.setColorAt(0, QColor(128, 128, 128))
            gradient.setColorAt(1, QColor(128, 128, 128))
            return gradient

        # Map each spectral line to a position in the gradient (0.0 to 1.0)
        # and create gradient stops with interpolation
        for wavelength, intensity in visible_lines:
            # Position in gradient (0.0 = angle_start, 1.0 = angle_end)
            t = (wavelength - range_min) / (range_max - range_min)
            t = max(0, min(1, t))

            # Get color for this wavelength
            color = wavelength_to_rgb(wavelength, range_min, range_max, 0.0)

            gradient.setColorAt(t, color)

        # Add edge colors if needed (interpolate to edges)
        # Add start color (blend toward first line)
        if visible_lines[0][0] > range_min:
            first_color = wavelength_to_rgb(range_min, range_min, range_max, 0.0)
            gradient.setColorAt(0, first_color)

        # Add end color (blend toward last line)
        if visible_lines[-1][0] < range_max:
            last_color = wavelength_to_rgb(range_max, range_min, range_max, 0.0)
            gradient.setColorAt(1, last_color)

        return gradient

    def _create_table_spectrum_gradient(self, elem, x1, y1, x2, y2, alpha):
        """Create a linear gradient showing spectrum lines for table layout"""
        spectrum_lines = elem['spectrum_lines']

        # Filter to visible spectrum
        visible_lines = [(wl, intensity) for wl, intensity in spectrum_lines
                        if 380 <= wl <= 750]

        if not visible_lines:
            return None

        # Sort by wavelength
        visible_lines.sort(key=lambda x: x[0])

        # Find wavelength range
        min_wl = min(wl for wl, _ in visible_lines)
        max_wl = max(wl for wl, _ in visible_lines)
        wl_range = max_wl - min_wl
        if wl_range == 0:
            wl_range = 1

        # Create gradient
        gradient = QLinearGradient(x1, y1, x2, y2)

        # Add color stops for each spectral line
        first_wl = visible_lines[0][0]
        last_wl = visible_lines[-1][0]

        # Add first color stop at 0
        first_color = wavelength_to_rgb(first_wl)
        first_color.setAlpha(alpha)
        gradient.setColorAt(0.0, first_color)

        for wavelength, intensity in visible_lines:
            # Position along gradient (0 to 1)
            t = (wavelength - min_wl) / wl_range

            # Get color for this wavelength
            color = wavelength_to_rgb(wavelength)
            color.setAlpha(alpha)

            # Add color stop
            gradient.setColorAt(t, color)

        # Add last color stop at 1
        last_color = wavelength_to_rgb(last_wl)
        last_color.setAlpha(alpha)
        gradient.setColorAt(1.0, last_color)

        return gradient

    def _get_spectrum_color_at_position(self, elem, position_fraction, alpha=255):
        """
        Get spectrum color at a specific position along the element's spectrum.

        Args:
            elem: Element dictionary with spectrum_lines data
            position_fraction: Position along spectrum (0.0 to 1.0)
            alpha: Base alpha value (default 255)

        Returns:
            QColor at the specified position or neutral color if no spectrum data
        """
        if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
            # Fallback to primary emission wavelength
            return wavelength_to_rgb(elem.get('wavelength_nm', 550))

        spectrum_lines = elem['spectrum_lines']

        # Filter to visible spectrum and sort by wavelength
        visible_lines = [(wl, intensity) for wl, intensity in spectrum_lines
                        if 380 <= wl <= 750]

        if not visible_lines:
            return QColor(128, 128, 128, alpha)

        visible_lines.sort(key=lambda x: x[0])

        # Find wavelength at this position
        min_wl = min(wl for wl, _ in visible_lines)
        max_wl = max(wl for wl, _ in visible_lines)
        target_wl = min_wl + position_fraction * (max_wl - min_wl)

        # Find the two closest spectrum lines and interpolate
        for i in range(len(visible_lines) - 1):
            wl1, intensity1 = visible_lines[i]
            wl2, intensity2 = visible_lines[i + 1]

            if wl1 <= target_wl <= wl2:
                # Interpolate between the two lines
                if wl2 - wl1 > 0:
                    t = (target_wl - wl1) / (wl2 - wl1)
                    interp_wl = wl1 + t * (wl2 - wl1)
                else:
                    interp_wl = wl1

                color = wavelength_to_rgb(interp_wl)
                color.setAlpha(alpha)
                return color

        # If we didn't find a match, use closest line
        closest_line = min(visible_lines, key=lambda x: abs(x[0] - target_wl))
        color = wavelength_to_rgb(closest_line[0])
        color.setAlpha(alpha)
        return color

    def draw_spectrum_lines_overlay(self, painter, elem, clip_path, center_x, center_y):
        """Draw spectrum emission lines as colored vertical bars overlaid on the element"""
        painter.save()
        painter.setClipPath(clip_path)  # Clip to element shape

        # Get the current color mapping range (from fill color property if it's wavelength-based)
        if PTPropertyName.is_wavelength_property(self.fill_property):
            range_min = self.fill_color_range_min
            range_max = self.fill_color_range_max
        else:
            # Default to visible spectrum
            range_min = 380.0
            range_max = 780.0

        # Draw each spectrum line as a colored radial line within the wedge
        for wavelength, intensity in elem['spectrum_lines']:
            # Only draw lines within the mapping range
            if wavelength < range_min or wavelength > range_max:
                continue

            # Skip very faint lines for clarity
            if intensity < 0.1:
                continue

            # Map wavelength to position within the wedge (from inner to outer radius)
            t = (wavelength - range_min) / (range_max - range_min) if (range_max - range_min) > 0 else 0.5
            t = max(0, min(1, t))  # Clamp to 0-1

            # Calculate position along the angular span
            angle_line = elem['angle_start'] + t * (elem['angle_end'] - elem['angle_start'])

            # Draw radial line from inner to outer radius
            r_inner = elem['r_inner']
            r_outer = elem['r_outer']

            x1 = center_x + r_inner * math.cos(angle_line)
            y1 = center_y + r_inner * math.sin(angle_line)
            x2 = center_x + r_outer * math.cos(angle_line)
            y2 = center_y + r_outer * math.sin(angle_line)

            # Get color for this wavelength (using the full visible spectrum for color, not the remapped range)
            line_color = wavelength_to_rgb(wavelength, 280, 905, 0.0)  # Use expanded range for pure colors

            # Set line width and alpha based on intensity
            line_width = 1 + intensity * 2  # 1-3 pixels
            line_alpha = int(180 * intensity)  # Semi-transparent based on intensity
            line_color.setAlpha(line_alpha)

            painter.setPen(QPen(line_color, line_width))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        painter.restore()

    def paint_spiral(self, painter):
        """Paint serpentine with continuous layer bands and element notches"""
        # Apply zoom and pan transformations
        painter.save()
        painter.translate(self.pan_x, self.pan_y)
        painter.scale(self.zoom_level, self.zoom_level)

        # Draw electron probability cloud for selected element (before period circles)
        if self.selected_element and self.show_orbital_cloud and hasattr(self, 'spiral_center'):
            self.draw_electron_probability_cloud(painter, self.spiral_center[0], self.spiral_center[1])

        # Draw 7 concentric circles for periods (background layer, hide when showing subatomic particles)
        if not self.show_subatomic_particles:
            self.draw_period_circles(painter)

        # If showing subatomic particles, hide all isotope visuals
        if not self.show_subatomic_particles:
            # Draw isotope spiral lines with property-based colors
            self.draw_isotope_spirals(painter)

            # Draw wedges between isotopes (property visualization)
            self.draw_isotope_wedges(painter)

            # Draw element names and markers
            self.draw_element_labels(painter)

        # Draw subatomic particles overlay (before shells)
        if self.selected_element and hasattr(self, 'spiral_center'):
            self.draw_subatomic_particles(painter, self.spiral_center[0], self.spiral_center[1])

        # Draw electron shells for selected element (on top)
        if self.selected_element and hasattr(self, 'spiral_center'):
            self.draw_electron_shells(painter, self.spiral_center[0], self.spiral_center[1])

        painter.restore()

        # Draw property legend (outside transform)
        painter.save()
        self.draw_spiral_legend(painter)
        painter.restore()

    def draw_spiral_legend(self, painter):
        """Draw legend showing property encodings in spiral mode"""
        if not hasattr(self, 'spiral_center'):
            return

        # Position legend in bottom left corner (before zoom transform)
        legend_x = 20
        legend_y = self.height() - 150

        # Background box
        painter.setPen(QPen(QColor(100, 100, 120, 200), 2))
        painter.setBrush(QBrush(QColor(20, 20, 40, 200)))
        painter.drawRect(legend_x, legend_y, 250, 130)

        # Title
        painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
        font = QFont('Arial', 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(legend_x + 10, legend_y + 20, "Property Encoding")

        # Property mappings
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)

        y_offset = legend_y + 40
        line_height = 22

        # Line color
        painter.drawText(legend_x + 10, y_offset, "Line Color:")
        painter.drawText(legend_x + 110, y_offset, self.fill_property.title())
        y_offset += line_height

        # Line thickness
        painter.drawText(legend_x + 10, y_offset, "Line Thickness:")
        painter.drawText(legend_x + 110, y_offset, "Isotope Abundance")
        y_offset += line_height

        # Wedge fill
        if self.show_isotopes:
            painter.drawText(legend_x + 10, y_offset, "Wedge Fill:")
            painter.drawText(legend_x + 110, y_offset, self.border_property.title())
            y_offset += line_height

            # Wedge border
            painter.drawText(legend_x + 10, y_offset, "Wedge Border:")
            painter.drawText(legend_x + 110, y_offset, self.glow_property.title())
            y_offset += line_height

        # Period circles
        painter.drawText(legend_x + 10, y_offset, "Period Circles:")
        painter.drawText(legend_x + 110, y_offset, "Orbital Blocks")

    def paint_serpentine(self, painter):
        """Paint linear graph layout with configurable property lines"""
        if not hasattr(self, 'linear_renderer'):
            return

        # Build table state for renderer
        table_state = {
            'fill_property': self.fill_property,
            'border_property': self.border_property,
            'glow_property': self.glow_property,
            'ring_property': self.ring_property,
            'show_isotopes': self.show_isotopes,
            'hovered_element': self.hovered_element,
            'selected_element': self.selected_element,
            'show_subatomic_particles': self.show_subatomic_particles
        }

        # Use the LinearLayoutRenderer to paint
        self.linear_renderer.paint(
            painter,
            self.elements,
            table_state,
            self.passes_filters,
            zoom_level=self.zoom_level,
            pan_x=self.pan_x,
            pan_y=self.pan_y
        )

        # Draw orbital/cloud visualization for selected element (if in subatomic mode)
        if self.selected_element and self.show_subatomic_particles:
            painter.save()
            painter.translate(self.pan_x, self.pan_y)
            painter.scale(self.zoom_level, self.zoom_level)

            center_x = self.selected_element['x']
            center_y = self.selected_element['y']
            if self.show_orbital_cloud:
                self.draw_electron_probability_cloud(painter, center_x, center_y)
            self.draw_subatomic_particles(painter, center_x, center_y)
            self.draw_electron_shells(painter, center_x, center_y)

            painter.restore()

    def draw_linear_property_lines(self, painter):
        """Draw configurable property lines showing trends across elements"""
        if not self.elements:
            return

        margin_left = 80
        margin_top = 100
        height = self.height() - margin_top - 100
        center_y = margin_top + height / 2

        # Three configurable property lines
        property_configs = [
            {'property': self.fill_property, 'color': QColor(100, 180, 255, 200), 'offset': -100},
            {'property': self.border_property, 'color': QColor(255, 180, 100, 200), 'offset': 0},
            {'property': self.glow_property, 'color': QColor(180, 255, 100, 200), 'offset': 100}
        ]

        for config in property_configs:
            if config['property'] == 'none':
                continue

            path = QPainterPath()
            first = True

            for elem in self.elements:
                x = elem['x']
                # Normalize property value to -1 to 1 range
                normalized_value = self.get_normalized_property_value(elem, config['property'])
                y = center_y + config['offset'] + normalized_value * 150

                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)

            painter.setPen(QPen(config['color'], 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    def get_normalized_property_value(self, elem, property_name):
        """Get normalized property value in range -1 to 1"""
        if property_name == "ionization":
            value = elem.get('ie', 0)
            return (value - 14) / 11  # Normalize around 14 eV, range ~11 eV
        elif property_name == "electronegativity":
            value = elem.get('electronegativity', 0)
            return (value - 2) / 2  # Normalize around 2, range ~2
        elif property_name == "melting":
            value = elem.get('melting_point', 0)
            return (value - 1500) / 1500  # Normalize around 1500K
        elif property_name == "boiling":
            value = elem.get('boiling_point', 0)
            return (value - 2000) / 2000  # Normalize around 2000K
        elif property_name == "radius":
            value = elem.get('atomic_radius', 0)
            return (value - 150) / 150  # Normalize around 150pm
        elif property_name == "density":
            value = elem.get('density', 1)
            log_d = math.log10(max(value, 0.001))
            return log_d / 1.5  # Log scale normalization
        elif property_name == "electron_affinity":
            value = elem.get('electron_affinity', 0)
            return (value - 100) / 150
        elif property_name == "valence":
            value = elem.get('valence_electrons', 1)
            return (value - 4) / 4
        return 0

    def draw_linear_element(self, painter, elem, passes_filter):
        """Draw element marker in linear layout"""
        x = elem['x']
        y = elem['y']

        # Filtered elements are drawn as grey transparent circles
        if not passes_filter:
            marker_size = 8
            if elem == self.hovered_element:
                marker_size = 12
            if elem == self.selected_element:
                marker_size = 14

            # Draw grey transparent circle
            grey_color = QColor(100, 100, 100, 60)
            painter.setPen(QPen(QColor(80, 80, 80, 80), 1))
            painter.setBrush(QBrush(grey_color))
            painter.drawEllipse(QPointF(x, y), marker_size, marker_size)
            return  # Skip all other drawing for filtered elements

        # Normal element drawing (passes filter)
        alpha = 255

        # Get fill color (already has fade alpha applied)
        fill_color = self.get_property_color(elem, self.fill_property, "fill")
        # Combine fade alpha with scene alpha
        fade_alpha = fill_color.alpha()
        combined_alpha = int((fade_alpha / 255.0) * alpha)
        fill_color.setAlpha(combined_alpha)

        # External Glow
        glow_radius_pct = self.get_glow_radius_percent(elem)
        glow_intensity = self.get_glow_intensity(elem)
        marker_size = 8
        if elem == self.hovered_element:
            marker_size = 12
        if elem == self.selected_element:
            marker_size = 14

        if glow_radius_pct > 0 and passes_filter and self.glow_type == "external":
            glow_intensity_adj = glow_intensity
            glow_radius_pct_adj = glow_radius_pct
            if elem == self.hovered_element or elem == self.selected_element:
                glow_radius_pct_adj *= 1.5
                glow_intensity_adj *= 1.2
            glow_color = self.get_property_color(elem, self.glow_property, "glow")
            # Calculate glow size as percentage of marker size
            glow_size = marker_size * glow_radius_pct_adj
            glow_radius = marker_size + glow_size
            glow_grad = QRadialGradient(x, y, glow_radius)
            glow_c = QColor(glow_color)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(int(150 * glow_intensity_adj * (alpha / 255)))
            glow_grad.setColorAt(0.6, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), glow_radius, glow_radius)

        # Inner ring (drawn as split of circle)
        inner_ring_fraction = self.get_inner_ring_size(elem)
        if self.ring_property != "none" and inner_ring_fraction > 0:
            ring_radius = marker_size * inner_ring_fraction
            ring_color = self.get_property_color(elem, self.ring_property, "ring")
            # Combine fade alpha with scene alpha
            fade_alpha_ring = ring_color.alpha()
            combined_alpha_ring = int((fade_alpha_ring / 255.0) * alpha)
            ring_color.setAlpha(combined_alpha_ring)

            # Draw inner ring circle
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(ring_color))
            painter.drawEllipse(QPointF(x, y), ring_radius, ring_radius)

            # Draw outer main circle (annulus)
            if elem == self.hovered_element:
                fill_color = fill_color.lighter(130)
            if elem == self.selected_element:
                fill_color = fill_color.lighter(150)

            painter.setPen(QPen(fill_color, marker_size - ring_radius))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(x, y), (marker_size + ring_radius) / 2, (marker_size + ring_radius) / 2)
        else:
            # Draw full main marker circle
            if elem == self.hovered_element:
                fill_color = fill_color.lighter(130)
            if elem == self.selected_element:
                fill_color = fill_color.lighter(150)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(fill_color))
            painter.drawEllipse(QPointF(x, y), marker_size, marker_size)

        # Internal Glow
        if glow_radius_pct > 0 and passes_filter and self.glow_type == "internal":
            glow_intensity_adj = glow_intensity
            glow_radius_pct_adj = glow_radius_pct
            if elem == self.hovered_element or elem == self.selected_element:
                glow_radius_pct_adj *= 1.5
                glow_intensity_adj *= 1.2
            glow_color = self.get_property_color(elem, self.glow_property, "glow")
            # Calculate glow size as percentage of marker size
            glow_size = marker_size * glow_radius_pct_adj
            # Constrain to marker interior
            max_glow = marker_size * 0.8
            constrained_glow = min(glow_size, max_glow)
            glow_grad = QRadialGradient(x, y, constrained_glow)
            glow_c = QColor(glow_color)
            glow_c.setAlpha(int(120 * glow_intensity_adj * (alpha / 255)))
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), constrained_glow, constrained_glow)

        # Border
        border_width = self.get_border_width(elem)
        border_color = self.get_property_color(elem, self.border_color_property, "border")
        # Combine fade alpha with scene alpha
        fade_alpha_border = border_color.alpha()
        combined_alpha_border = int((fade_alpha_border / 255.0) * alpha)
        border_color.setAlpha(combined_alpha_border)
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(x, y), marker_size, marker_size)

        # Draw element label
        if elem == self.hovered_element or elem == self.selected_element or passes_filter:
            text_alpha = alpha
            symbol_text_color = self.get_property_color(elem, self.symbol_text_color_property, "symbol_text")
            symbol_text_color.setAlpha(text_alpha)
            font = QFont('Arial', 9 if passes_filter else 7, QFont.Weight.Bold)

            if elem == self.hovered_element or elem == self.selected_element:
                font.setPointSize(11)

            painter.setFont(font)
            text_rect = QRectF(x - 20, y - 30, 40, 20)

            # Draw symbol with white border
            symbol_path = QPainterPath()
            symbol_path.addText(text_rect.left() + text_rect.width()/2 - painter.fontMetrics().horizontalAdvance(elem.get('symbol', ''))/2,
                              text_rect.top() + text_rect.height()/2 + painter.fontMetrics().ascent()/2,
                              font, elem.get('symbol', ''))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(symbol_path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(symbol_text_color))
            painter.drawPath(symbol_path)

        # Draw isotopes if enabled
        if self.show_isotopes and passes_filter:
            isotopes = elem.get('isotopes', [])
            if isotopes:
                iso_y_offset = 15
                for iso_idx, (mass, abundance) in enumerate(isotopes[:3]):  # Limit to 3 isotopes
                    iso_y = y + iso_y_offset + iso_idx * 5
                    iso_size = 1 + (abundance / 100) * 3
                    neutron_count = mass - elem['z']
                    iso_color = QColor(150 + neutron_count * 5, 150 + neutron_count * 3, 255, alpha)

                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(iso_color))
                    painter.drawEllipse(QPointF(x, iso_y), iso_size, iso_size)

    def paint_table(self, painter):
        """Paint traditional periodic table layout"""
        # Apply zoom and pan transformations
        painter.save()
        painter.translate(self.pan_x, self.pan_y)
        painter.scale(self.zoom_level, self.zoom_level)

        # Draw electron probability cloud for selected element (if in subatomic mode)
        if self.selected_element and self.show_orbital_cloud and 'cell_size' in self.selected_element:
            center_x = self.selected_element['x'] + self.selected_element['cell_size'] / 2
            center_y = self.selected_element['y'] + self.selected_element['cell_size'] / 2
            self.draw_electron_probability_cloud(painter, center_x, center_y)

        # If showing subatomic particles, only draw selected element
        if self.show_subatomic_particles and self.selected_element:
            passes_filter = self.passes_filters(self.selected_element)
            self.draw_table_element(painter, self.selected_element, passes_filter)
        else:
            # Draw all elements normally
            for elem in self.elements:
                passes_filter = self.passes_filters(elem)
                self.draw_table_element(painter, elem, passes_filter)

        # Draw subatomic particles and shells for selected element (on top)
        if self.selected_element and self.show_subatomic_particles and 'cell_size' in self.selected_element:
            center_x = self.selected_element['x'] + self.selected_element['cell_size'] / 2
            center_y = self.selected_element['y'] + self.selected_element['cell_size'] / 2
            self.draw_subatomic_particles(painter, center_x, center_y)
            self.draw_electron_shells(painter, center_x, center_y)

        painter.restore()

    def draw_table_element(self, painter, elem, passes_filter=True):
        """Draw element cell in table layout"""
        x = elem['x']
        y = elem['y']
        cell_size = elem['cell_size']

        # Filtered elements are drawn as grey transparent boxes
        if not passes_filter:
            # Draw grey transparent box
            grey_color = QColor(100, 100, 100, 60)
            painter.setPen(QPen(QColor(80, 80, 80, 80), 1))
            painter.setBrush(QBrush(grey_color))
            painter.drawRoundedRect(QRectF(x, y, cell_size, cell_size), 5, 5)
            return  # Skip all other drawing for filtered elements

        # Normal element drawing (passes filter)
        alpha = 255

        # Get fill color (already has fade alpha applied)
        fill_color = self.get_property_color(elem, self.fill_property, "fill")
        # Combine fade alpha with scene alpha
        fade_alpha = fill_color.alpha()
        combined_alpha = int((fade_alpha / 255.0) * alpha)
        fill_color.setAlpha(combined_alpha)

        if elem == self.hovered_element:
            fill_color = fill_color.lighter(130)
        if elem == self.selected_element:
            fill_color = fill_color.lighter(150)

        # External Glow (drawn before box)
        glow_radius_pct = self.get_glow_radius_percent(elem)
        glow_intensity = self.get_glow_intensity(elem)
        if glow_radius_pct > 0 and passes_filter and self.glow_type == "external":
            glow_intensity_adj = glow_intensity
            glow_radius_pct_adj = glow_radius_pct
            if elem == self.hovered_element or elem == self.selected_element:
                glow_radius_pct_adj *= 1.5
                glow_intensity_adj *= 1.2
            # External glow as circle around the box
            glow_color = self.get_property_color(elem, self.glow_property, "glow")
            # Calculate glow size as percentage of cell size
            glow_size = cell_size * glow_radius_pct_adj
            glow_radius = (cell_size / 2) + glow_size
            glow_grad = QRadialGradient(x + cell_size/2, y + cell_size/2, glow_radius)
            glow_c = QColor(glow_color)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(int(150 * glow_intensity_adj * (alpha / 255)))
            glow_grad.setColorAt(0.7, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x + cell_size/2, y + cell_size/2), glow_radius, glow_radius)

        # Inner ring (drawn as split of box - bottom portion)
        inner_ring_fraction = self.get_inner_ring_size(elem)
        if self.ring_property != "none" and inner_ring_fraction > 0:
            ring_height = cell_size * inner_ring_fraction
            ring_color = self.get_property_color(elem, self.ring_property, "ring")
            # Combine fade alpha with scene alpha
            fade_alpha_ring = ring_color.alpha()
            combined_alpha_ring = int((fade_alpha_ring / 255.0) * alpha)
            ring_color.setAlpha(combined_alpha_ring)

            # Draw inner ring at bottom
            painter.setBrush(QBrush(ring_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, y + cell_size - ring_height, cell_size, ring_height), 5, 5)

            # Main cell fill (top portion, excluding ring)
            # Check for spectrum gradient
            if (PTPropertyName.from_string(self.fill_property) == PTPropertyName.SPECTRUM and
                'spectrum_lines' in elem and elem['spectrum_lines']):
                gradient = self._create_table_spectrum_gradient(elem, x, y, x + cell_size, y, combined_alpha)
                if gradient:
                    painter.setBrush(QBrush(gradient))
                else:
                    painter.setBrush(QBrush(fill_color))
            else:
                painter.setBrush(QBrush(fill_color))
            painter.drawRoundedRect(QRectF(x, y, cell_size, cell_size - ring_height), 5, 5)
        else:
            # Main cell fill (full box)
            # Check for spectrum gradient
            if (PTPropertyName.from_string(self.fill_property) == PTPropertyName.SPECTRUM and
                'spectrum_lines' in elem and elem['spectrum_lines']):
                gradient = self._create_table_spectrum_gradient(elem, x, y, x + cell_size, y, combined_alpha)
                if gradient:
                    painter.setBrush(QBrush(gradient))
                else:
                    painter.setBrush(QBrush(fill_color))
            else:
                painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, y, cell_size, cell_size), 5, 5)

        # Internal Glow (drawn after box, inside)
        if glow_radius_pct > 0 and passes_filter and self.glow_type == "internal":
            glow_intensity_adj = glow_intensity
            glow_radius_pct_adj = glow_radius_pct
            if elem == self.hovered_element or elem == self.selected_element:
                glow_radius_pct_adj *= 1.5
                glow_intensity_adj *= 1.2
            # Internal glow within the box
            glow_color = self.get_property_color(elem, self.glow_property, "glow")
            # Calculate glow size as percentage of cell size
            glow_size = cell_size * glow_radius_pct_adj
            # Constrain to box interior
            max_glow = cell_size * 0.4
            constrained_glow = min(glow_size, max_glow)
            glow_grad = QRadialGradient(x + cell_size/2, y + cell_size/2, constrained_glow)
            glow_c = QColor(glow_color)
            glow_c.setAlpha(int(120 * glow_intensity_adj * (alpha / 255)))
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            # Clip to box
            painter.save()
            box_path = QPainterPath()
            box_path.addRoundedRect(QRectF(x, y, cell_size, cell_size), 5, 5)
            painter.setClipPath(box_path)
            painter.drawEllipse(QPointF(x + cell_size/2, y + cell_size/2), constrained_glow, constrained_glow)
            painter.restore()

        # Border
        border_width = self.get_border_width(elem)
        border_color = self.get_property_color(elem, self.border_color_property, "border")
        # Combine fade alpha with scene alpha
        fade_alpha_border = border_color.alpha()
        combined_alpha_border = int((fade_alpha_border / 255.0) * alpha)
        border_color.setAlpha(combined_alpha_border)
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(x, y, cell_size, cell_size), 5, 5)

        # Draw element info with colored text and white borders
        if passes_filter or elem == self.hovered_element or elem == self.selected_element:
            text_alpha = alpha

            # Atomic number (top left) with colored text and white border
            atomic_num_text_color = self.get_property_color(elem, self.atomic_number_text_color_property, "atomic_number_text")
            atomic_num_text_color.setAlpha(text_alpha)
            font = QFont('Arial', 8)
            painter.setFont(font)
            num_str = str(elem['z'])
            num_rect = QRectF(x + 3, y + 2, cell_size - 6, 12)

            # Draw atomic number with white border
            num_path = QPainterPath()
            num_path.addText(num_rect.left(), num_rect.top() + painter.fontMetrics().ascent(), font, num_str)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(num_path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(atomic_num_text_color))
            painter.drawPath(num_path)

            # Symbol (center, large) with colored text and white border
            symbol_text_color = self.get_property_color(elem, self.symbol_text_color_property, "symbol_text")
            symbol_text_color.setAlpha(text_alpha)
            font = QFont('Arial', 18 if passes_filter else 14, QFont.Weight.Bold)
            painter.setFont(font)
            symbol_rect = QRectF(x, y + cell_size/2 - 12, cell_size, 24)

            # Draw symbol with white border
            symbol_path = QPainterPath()
            symbol_path.addText(symbol_rect.left() + symbol_rect.width()/2 - painter.fontMetrics().horizontalAdvance(elem.get('symbol', ''))/2,
                              symbol_rect.top() + symbol_rect.height()/2 + painter.fontMetrics().ascent()/2,
                              font, elem.get('symbol', ''))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(symbol_path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(symbol_text_color))
            painter.drawPath(symbol_path)

            # Mass/other info (bottom, small)
            painter.setPen(QPen(QColor(200, 200, 200, text_alpha), 1))
            font = QFont('Arial', 7)
            painter.setFont(font)
            # Show property value based on fill property
            if self.fill_property == "ionization":
                value_text = f"{elem['ie']:.1f}eV"
            elif self.fill_property == "electronegativity":
                value_text = f"{elem['electronegativity']:.2f}"
            elif self.fill_property == "melting":
                value_text = f"{elem['melting_point']:.0f}K"
            else:
                value_text = ""
            painter.drawText(QRectF(x + 2, y + cell_size - 12, cell_size - 4, 10), Qt.AlignmentFlag.AlignCenter, value_text)

    def draw_serpentine_band(self, painter, segments, period):
        """Draw continuous band along serpentine path"""
        if len(segments) < 2:
            return

        # Get color for this period
        colors = {
            1: QColor(255, 100, 120, 100),
            2: QColor(100, 160, 255, 100),
            3: QColor(100, 160, 255, 100),
            4: QColor(255, 210, 100, 100),
            5: QColor(255, 210, 100, 100),
            6: QColor(140, 255, 170, 100),
            7: QColor(140, 255, 170, 100)
        }

        # Draw symmetric bands on both sides of path
        for side in [1, -1]:
            path = QPainterPath()
            first = True

            for seg in segments:
                x, y = seg['x'], seg['y']
                perp = seg['perp_angle']
                offset = seg['center_offset'] * side

                edge_x = x + offset * math.cos(perp)
                edge_y = y + offset * math.sin(perp)

                if first:
                    path.moveTo(edge_x, edge_y)
                    first = False
                else:
                    path.lineTo(edge_x, edge_y)

            painter.setPen(QPen(QColor(200, 200, 220, 120), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

            # Fill area between inner and outer edges
            inner_path = QPainterPath()
            outer_path = QPainterPath()
            band_width = segments[0]['band_width']

            first_inner = True
            first_outer = True
            for seg in segments:
                x, y = seg['x'], seg['y']
                perp = seg['perp_angle']
                center_offset = seg['center_offset'] * side

                inner_offset = center_offset - (band_width / 2) * side
                outer_offset = center_offset + (band_width / 2) * side

                inner_x = x + inner_offset * math.cos(perp)
                inner_y = y + inner_offset * math.sin(perp)
                outer_x = x + outer_offset * math.cos(perp)
                outer_y = y + outer_offset * math.sin(perp)

                if first_inner:
                    inner_path.moveTo(inner_x, inner_y)
                    outer_path.moveTo(outer_x, outer_y)
                    first_inner = False
                    first_outer = False
                else:
                    inner_path.lineTo(inner_x, inner_y)
                    outer_path.lineTo(outer_x, outer_y)

            # Combine paths
            band_polygon = QPainterPath()
            band_polygon.addPath(inner_path)

            outer_points = []
            for i in range(outer_path.elementCount()):
                elem = outer_path.elementAt(i)
                outer_points.append(QPointF(elem.x, elem.y))

            for pt in reversed(outer_points):
                band_polygon.lineTo(pt)

            band_polygon.closeSubpath()

            painter.setPen(QPen(QColor(200, 200, 220, 120), 1.5))
            painter.setBrush(QBrush(colors.get(period, QColor(150, 150, 150, 100))))
            painter.drawPath(band_polygon)

    def draw_serpentine_isotope_bands(self, painter, segments):
        """Draw isotope sub-bands within the period bands"""
        if len(segments) < 2:
            return

        for elem in segments:
            if not elem.get('has_element'):
                continue

            isotopes = elem.get('isotopes', [])
            if not isotopes:
                continue

            x, y = elem['x'], elem['y']
            perp = elem['perp_angle']
            center_offset = elem['center_offset']
            band_width = elem['band_width']

            # Draw thin lines for each isotope within the band
            num_isotopes = len(isotopes)
            for iso_idx, (mass, abundance) in enumerate(isotopes):
                # Position within the band (both sides)
                for side in [1, -1]:
                    iso_factor = (iso_idx + 1) / (num_isotopes + 1)
                    offset = center_offset * side
                    iso_offset = offset - (band_width/2 * side) + iso_factor * band_width * side

                    # Draw thin isotope line
                    line_length = 8 + (abundance / 100) * 12
                    line_x1 = x + iso_offset * math.cos(perp) - line_length/2 * math.sin(perp)
                    line_y1 = y + iso_offset * math.sin(perp) + line_length/2 * math.cos(perp)
                    line_x2 = x + iso_offset * math.cos(perp) + line_length/2 * math.sin(perp)
                    line_y2 = y + iso_offset * math.sin(perp) - line_length/2 * math.cos(perp)

                    # Color based on neutron count
                    neutron_count = mass - elem['z']
                    iso_color = QColor(180 + neutron_count * 4, 180 + neutron_count * 3, 255, 150)

                    # Thickness based on abundance
                    thickness = 1 + (abundance / 100) * 2

                    painter.setPen(QPen(iso_color, thickness, Qt.PenStyle.SolidLine))
                    painter.drawLine(QPointF(line_x1, line_y1), QPointF(line_x2, line_y2))

    def draw_serpentine_property_notches(self, painter, elem):
        """Draw property-encoded notches perpendicular to the path"""
        x, y = elem['x'], elem['y']
        perp = elem['perp_angle']
        center_offset = elem['center_offset']

        # Draw multiple property notches at different offsets
        # Notch 1: Border property (inner)
        notch1_offset = center_offset * 0.6
        notch1_color = self.get_property_color(elem, self.border_property, "border")
        notch1_length = 5 + self.get_border_width(elem) * 3

        for side in [1, -1]:
            notch_x1 = x + notch1_offset * side * math.cos(perp)
            notch_y1 = y + notch1_offset * side * math.sin(perp)
            notch_x2 = notch_x1 + notch1_length * side * math.cos(perp)
            notch_y2 = notch_y1 + notch1_length * side * math.sin(perp)

            painter.setPen(QPen(notch1_color, 2, Qt.PenStyle.SolidLine))
            painter.drawLine(QPointF(notch_x1, notch_y1), QPointF(notch_x2, notch_y2))

        # Notch 2: Glow property (outer, with glow effect)
        glow_size, glow_intensity = self.get_glow_params(elem)
        if glow_size > 0:
            notch2_offset = center_offset * 1.2
            notch2_color = self.get_property_color(elem, self.glow_property, "glow")
            notch2_length = 6 + glow_intensity * 8

            for side in [1, -1]:
                notch_x1 = x + notch2_offset * side * math.cos(perp)
                notch_y1 = y + notch2_offset * side * math.sin(perp)
                notch_x2 = notch_x1 + notch2_length * side * math.cos(perp)
                notch_y2 = notch_y1 + notch2_length * side * math.sin(perp)

                # Draw with glow
                glow_grad = QRadialGradient((notch_x1 + notch_x2)/2, (notch_y1 + notch_y2)/2, glow_size * 0.3)
                glow_c = QColor(notch2_color)
                glow_c.setAlpha(int(100 * glow_intensity))
                glow_grad.setColorAt(0, glow_c)
                glow_c.setAlpha(0)
                glow_grad.setColorAt(1, glow_c)
                painter.setBrush(QBrush(glow_grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF((notch_x1 + notch_x2)/2, (notch_y1 + notch_y2)/2),
                                   glow_size * 0.3, glow_size * 0.3)

                painter.setPen(QPen(notch2_color, 2, Qt.PenStyle.SolidLine))
                painter.drawLine(QPointF(notch_x1, notch_y1), QPointF(notch_x2, notch_y2))

    def draw_serpentine_element_marker(self, painter, elem):
        """Draw element marker on serpentine path"""
        x, y = elem['x'], elem['y']
        perp = elem['perp_angle']
        center_offset = elem['center_offset']

        # Draw marker dot (fill property color)
        marker_color = self.get_property_color(elem, self.fill_property, "fill")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(marker_color))
        painter.drawEllipse(QPointF(x, y), 5, 5)

        # Draw element label with colored text and white border
        text_x = x + center_offset * math.cos(perp)
        text_y = y + center_offset * math.sin(perp)

        symbol_text_color = self.get_property_color(elem, self.symbol_text_color_property, "symbol_text")
        font = QFont('Arial', 10, QFont.Weight.Bold)

        if elem == self.hovered_element or elem == self.selected_element:
            font.setPointSize(12)

        painter.setFont(font)
        text_rect = QRectF(text_x - 20, text_y - 10, 40, 20)

        # Draw symbol with white border
        symbol_path = QPainterPath()
        symbol_path.addText(text_rect.left() + text_rect.width()/2 - painter.fontMetrics().horizontalAdvance(elem.get('symbol', ''))/2,
                          text_rect.top() + text_rect.height()/2 + painter.fontMetrics().ascent()/2,
                          font, elem.get('symbol', ''))
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(symbol_path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(symbol_text_color))
        painter.drawPath(symbol_path)

    def draw_period_circles(self, painter):
        """Draw 7 concentric circles representing periods"""
        if not hasattr(self, 'spiral_center') or not hasattr(self, 'period_radii'):
            return

        center_x, center_y = self.spiral_center

        # Draw circles from innermost to outermost
        for period in range(1, 8):
            radius = self.period_radii[period]

            # Color based on orbital block - more saturated
            if period <= 2:
                color = QColor(255, 100, 120, 120)  # s-block (red)
            elif period == 3:
                color = QColor(100, 160, 255, 120)  # p-block (blue)
            elif period in [4, 5]:
                color = QColor(255, 210, 100, 120)  # d-block (gold)
            else:
                color = QColor(140, 255, 170, 120)  # f-block (green)

            # Draw thicker circle with gradient effect
            painter.setPen(QPen(color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

            # Draw period label
            label_angle = math.pi / 4  # 45 degrees
            label_x = center_x + radius * math.cos(label_angle)
            label_y = center_y + radius * math.sin(label_angle)

            painter.setPen(QPen(QColor(200, 200, 220, 200), 1))
            font = QFont('Arial', 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QPointF(label_x + 5, label_y - 5), f"P{period}")

    def draw_isotope_spirals(self, painter):
        """Draw main spiral line and isotope lines with property-based colors and borders"""
        if not hasattr(self, 'element_spiral_positions') or not self.element_spiral_positions:
            return

        center_x, center_y = self.spiral_center

        # Draw isotope lines first (if enabled)
        if self.show_isotopes:
            self._draw_isotope_offset_lines(painter, center_x, center_y)

        # Draw main spiral line
        self._draw_main_spiral_line(painter, center_x, center_y)

        # Draw spectrum lines as pixels on top of isotope/main lines (if enabled)
        if self.show_spectrum_lines:
            self._draw_spectrum_pixels_on_spiral(painter, center_x, center_y)

        # Draw element dots with glow
        self._draw_element_dots_spiral(painter, center_x, center_y)

    def _draw_main_spiral_line(self, painter, center_x, center_y):
        """Draw the main spiral line connecting all elements."""
        for i in range(len(self.element_spiral_positions) - 1):
            pos1 = self.element_spiral_positions[i]
            pos2 = self.element_spiral_positions[i + 1]

            elem1 = pos1['elem']

            # Get fill color
            fill_color = self.get_property_color(elem1, self.fill_property, "fill")

            # Get border properties
            border_color = self.get_property_color(elem1, self.border_property, "border")
            border_width = self.get_border_width(elem1)

            # Draw border (outer line)
            if border_width > 1:
                painter.setPen(QPen(border_color, border_width + 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(pos1['x'], pos1['y']), QPointF(pos2['x'], pos2['y']))

            # Draw main line
            painter.setPen(QPen(fill_color, max(border_width, 3), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(pos1['x'], pos1['y']), QPointF(pos2['x'], pos2['y']))

    def _draw_isotope_offset_lines(self, painter, center_x, center_y):
        """Draw isotope lines at radial offsets from period circles."""
        for i, pos_data in enumerate(self.element_spiral_positions):
            elem = pos_data['elem']
            isotopes = pos_data['isotopes']

            # Draw lines for each isotope
            for iso_idx, isotope in enumerate(isotopes):
                angle = isotope['angle']
                radius = isotope['radius']

                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)

                # Connect to next position
                if i < len(self.element_spiral_positions) - 1:
                    next_pos = self.element_spiral_positions[i + 1]
                    next_isotopes = next_pos['isotopes']

                    # Find corresponding isotope
                    if iso_idx < len(next_isotopes):
                        next_iso = next_isotopes[iso_idx]
                    else:
                        next_iso = next_isotopes[0]

                    next_x = center_x + next_iso['radius'] * math.cos(next_iso['angle'])
                    next_y = center_y + next_iso['radius'] * math.sin(next_iso['angle'])

                    # Get fill color
                    fill_color = self.get_property_color(elem, self.fill_property, "fill")

                    # Get border properties
                    border_color = self.get_property_color(elem, self.border_color_property, "border")
                    border_width = self.get_border_width(elem)

                    # Scale by abundance
                    abundance_scale = isotope['abundance'] / 100.0
                    scaled_border = max(1, border_width * abundance_scale)

                    # Draw border
                    if border_width > 1:
                        painter.setPen(QPen(border_color, scaled_border + 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                        painter.drawLine(QPointF(x, y), QPointF(next_x, next_y))

                    # Draw isotope line
                    painter.setPen(QPen(fill_color, max(scaled_border, 2), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    painter.drawLine(QPointF(x, y), QPointF(next_x, next_y))

    def _draw_spectrum_pixels_on_spiral(self, painter, center_x, center_y):
        """Draw spectrum emission lines as colored pixels on the spiral/isotope lines."""
        # Determine which lines to draw on based on show_isotopes
        if self.show_isotopes:
            # Draw on all isotope lines
            for i, pos_data in enumerate(self.element_spiral_positions):
                elem = pos_data['elem']
                isotopes = pos_data['isotopes']

                if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
                    continue

                # Draw spectrum pixels for each isotope line
                for iso_idx, isotope in enumerate(isotopes):
                    if i >= len(self.element_spiral_positions) - 1:
                        continue

                    angle = isotope['angle']
                    radius = isotope['radius']
                    x1 = center_x + radius * math.cos(angle)
                    y1 = center_y + radius * math.sin(angle)

                    next_pos = self.element_spiral_positions[i + 1]
                    next_isotopes = next_pos['isotopes']
                    if iso_idx < len(next_isotopes):
                        next_iso = next_isotopes[iso_idx]
                    else:
                        next_iso = next_isotopes[0]

                    x2 = center_x + next_iso['radius'] * math.cos(next_iso['angle'])
                    y2 = center_y + next_iso['radius'] * math.sin(next_iso['angle'])

                    self._draw_spectrum_pixels_on_line(painter, elem, x1, y1, x2, y2)
        else:
            # Draw only on main spiral line
            for i in range(len(self.element_spiral_positions) - 1):
                pos1 = self.element_spiral_positions[i]
                pos2 = self.element_spiral_positions[i + 1]
                elem = pos1['elem']

                if 'spectrum_lines' not in elem or not elem['spectrum_lines']:
                    continue

                self._draw_spectrum_pixels_on_line(painter, elem, pos1['x'], pos1['y'], pos2['x'], pos2['y'])

    def _draw_spectrum_pixels_on_line(self, painter, elem, x1, y1, x2, y2):
        """Draw spectrum emission lines as colored pixels along a line segment."""
        spectrum_lines = elem['spectrum_lines']

        # Filter to visible spectrum
        visible_lines = [(wl, intensity) for wl, intensity in spectrum_lines
                        if 380 <= wl <= 750]

        if not visible_lines:
            return

        # Calculate line length and direction
        dx = x2 - x1
        dy = y2 - y1
        line_length = math.sqrt(dx * dx + dy * dy)

        if line_length < 1:
            return

        # Normalize direction
        dx_norm = dx / line_length
        dy_norm = dy / line_length

        # Draw each spectral line as a small perpendicular mark
        for wavelength, intensity in visible_lines:
            # Skip faint lines
            if intensity < 0.1:
                continue

            # Position along line (map wavelength to position)
            # Use normalized wavelength position (0-1 across visible spectrum)
            t = (wavelength - 380) / (750 - 380)
            t = max(0, min(1, t))

            # Calculate position on line
            px = x1 + dx * t
            py = y1 + dy * t

            # Perpendicular direction
            perp_x = -dy_norm
            perp_y = dx_norm

            # Line length based on intensity (2-6 pixels)
            mark_length = 2 + intensity * 4

            # Draw short perpendicular line
            color = wavelength_to_rgb(wavelength)
            color.setAlpha(int(255 * intensity))

            painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))
            painter.drawLine(
                QPointF(px - perp_x * mark_length / 2, py - perp_y * mark_length / 2),
                QPointF(px + perp_x * mark_length / 2, py + perp_y * mark_length / 2)
            )

    def _draw_element_dots_spiral(self, painter, center_x, center_y):
        """Draw dots at element positions with ring color and glow."""
        for pos_data in self.element_spiral_positions:
            elem = pos_data['elem']
            x, y = pos_data['x'], pos_data['y']

            # Get ring color
            ring_color = self.get_property_color(elem, self.ring_property, "ring")

            # Get ring size (map to dot size 3-8 pixels)
            ring_size_val = self.get_inner_ring_size(elem)
            dot_size = 3 + ring_size_val * 5

            # Draw glow
            glow_size = self.get_glow_radius_percent(elem) * 30
            glow_intensity = self.get_glow_intensity(elem)
            if glow_size > 0:
                glow_color = self.get_property_color(elem, self.glow_property, "glow")
                glow_grad = QRadialGradient(x, y, glow_size)
                glow_c = QColor(glow_color)
                glow_c.setAlpha(int(150 * glow_intensity))
                glow_grad.setColorAt(0, glow_c)
                glow_c.setAlpha(0)
                glow_grad.setColorAt(1, glow_c)
                painter.setBrush(QBrush(glow_grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(x, y), glow_size, glow_size)

            # Draw dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(ring_color))
            painter.drawEllipse(QPointF(x, y), dot_size, dot_size)

    def draw_isotope_wedges(self, painter):
        """Draw wedges between isotopes showing property variations"""
        if not hasattr(self, 'isotope_spiral_lines'):
            return

        # Only draw wedges if isotopes are enabled
        if not self.show_isotopes:
            return

        center_x, center_y = self.spiral_center

        # Draw wedges between consecutive isotopes of the same element
        for i in range(len(self.isotope_spiral_lines) - 1):
            iso1 = self.isotope_spiral_lines[i]
            iso2 = self.isotope_spiral_lines[i + 1]

            # Only draw wedge if they're from the same element
            if iso1['elem']['symbol'] != iso2['elem']['symbol']:
                continue

            # Create wedge from center to both isotope points
            path = QPainterPath()

            # Start at inner edge (closer to center)
            inner_radius = max(iso1['base_radius'] - 25, 10)
            inner_x1 = center_x + inner_radius * math.cos(iso1['angle'])
            inner_y1 = center_y + inner_radius * math.sin(iso1['angle'])
            inner_x2 = center_x + inner_radius * math.cos(iso2['angle'])
            inner_y2 = center_y + inner_radius * math.sin(iso2['angle'])

            # Outer edge at isotope positions
            outer_x1 = iso1['x']
            outer_y1 = iso1['y']
            outer_x2 = iso2['x']
            outer_y2 = iso2['y']

            # Build wedge polygon
            path.moveTo(inner_x1, inner_y1)
            path.lineTo(outer_x1, outer_y1)
            path.lineTo(outer_x2, outer_y2)
            path.lineTo(inner_x2, inner_y2)
            path.closeSubpath()

            # Fill color based on border property
            fill_color = self.get_property_color(iso1['elem'], self.border_property)
            fill_color.setAlpha(40)

            # Border color based on glow property
            border_color = self.get_property_color(iso1['elem'], self.glow_property)
            border_width = self.get_border_width(iso1['elem'])

            painter.setPen(QPen(border_color, border_width * 0.5))
            painter.setBrush(QBrush(fill_color))
            painter.drawPath(path)

    def draw_element_labels(self, painter):
        """Draw element symbols at their positions with colored text and white borders"""
        center_x, center_y = self.spiral_center

        for elem in self.elements:
            if not elem.get('has_element'):
                continue

            # Draw element symbol
            symbol = elem.get('symbol', '')
            if not symbol:
                continue

            # Position at the element's primary isotope location
            angle = elem['angle']
            radius = elem['base_radius']

            # Place label outside the circle
            label_radius = radius + 25
            text_x = center_x + label_radius * math.cos(angle)
            text_y = center_y + label_radius * math.sin(angle)

            # Get symbol text color
            symbol_text_color = self.get_property_color(elem, self.symbol_text_color_property, "symbol_text")
            font = QFont('Arial', 10, QFont.Weight.Bold)

            # Highlight if selected/hovered
            if elem == self.hovered_element or elem == self.selected_element:
                font.setPointSize(12)

            painter.setFont(font)
            text_rect = QRectF(text_x - 20, text_y - 10, 40, 20)

            # Draw symbol with white border
            symbol_path = QPainterPath()
            symbol_path.addText(text_rect.left() + text_rect.width()/2 - painter.fontMetrics().horizontalAdvance(symbol)/2,
                              text_rect.top() + text_rect.height()/2 + painter.fontMetrics().ascent()/2,
                              font, symbol)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(symbol_path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(symbol_text_color))
            painter.drawPath(symbol_path)

            # Draw a small marker dot at the isotope position
            marker_color = self.get_property_color(elem, self.fill_property, "fill")
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(marker_color))
            painter.drawEllipse(QPointF(elem['x'], elem['y']), 4, 4)

    def draw_orbital_background_bands(self, painter, period_segments):
        """Draw large colored background bands for orbital types (s, p, d, f)"""
        # Orbital type regions
        orbital_bands = {
            's': {'periods': [1, 2], 'start': 0, 'end': 112, 'color': QColor(255, 80, 100, 25)},
            'p': {'periods': [2, 3], 'start': 112, 'end': 288, 'color': QColor(80, 150, 255, 25)},
            'd': {'periods': [4, 5], 'start': 288, 'end': 528, 'color': QColor(255, 200, 80, 25)},
            'f': {'periods': [6, 7], 'start': 528, 'end': 800, 'color': QColor(120, 255, 150, 25)}
        }

        # Get any segment list that has elements to define the path
        any_segments = None
        for period in range(1, 8):
            if len(period_segments[period]) > 1:
                any_segments = period_segments[period]
                break

        if not any_segments:
            return

        # Draw each orbital type background band
        for orbital_name, band_info in orbital_bands.items():
            inner_offset = band_info['start']
            outer_offset = band_info['end']
            color = band_info['color']

            # Create wide background ribbon following the path
            inner_path = QPainterPath()
            outer_path = QPainterPath()

            first = True
            for seg in any_segments:
                x, y = seg['x'], seg['y']
                perp = seg['perp_angle']

                inner_x = x + inner_offset * math.cos(perp)
                inner_y = y + inner_offset * math.sin(perp)
                outer_x = x + outer_offset * math.cos(perp)
                outer_y = y + outer_offset * math.sin(perp)

                if first:
                    inner_path.moveTo(inner_x, inner_y)
                    outer_path.moveTo(outer_x, outer_y)
                    first = False
                else:
                    inner_path.lineTo(inner_x, inner_y)
                    outer_path.lineTo(outer_x, outer_y)

            # Combine paths
            band_polygon = QPainterPath()
            band_polygon.addPath(inner_path)

            outer_points = []
            for i in range(outer_path.elementCount()):
                elem = outer_path.elementAt(i)
                outer_points.append(QPointF(elem.x, elem.y))

            for pt in reversed(outer_points):
                band_polygon.lineTo(pt)

            band_polygon.closeSubpath()

            # Draw the large background band
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPath(band_polygon)

    def draw_inflection_labels(self, painter):
        """Draw labels at the inflection points (peaks/troughs) of semicircles"""
        if len(self.elements) == 0:
            return

        # Find inflection points - every ~10 elements (top/bottom of each arc)
        labeled_points = set()

        for elem in self.elements:
            if not elem.get('has_element'):
                continue

            elem_idx = elem.get('element_index', 0)

            # Label every 10th element (at the peak/trough of each semicircle)
            if elem_idx % 10 == 5:  # Middle of semicircle = peak/trough
                key = (round(elem['x'], 1), round(elem['y'], 1))
                if key not in labeled_points:
                    labeled_points.add(key)

                    # Draw label
                    label_text = f"Z={elem['z']}"
                    painter.setPen(QPen(QColor(200, 200, 255, 200), 1))
                    font = QFont('Arial', 9, QFont.Weight.Bold)
                    painter.setFont(font)

                    text_rect = QRectF(elem['x'] - 30, elem['y'] - 30, 60, 20)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label_text)

    def draw_continuous_band(self, painter, segments, period):
        """Draw symmetric ribbon bands on BOTH sides of the path"""
        if len(segments) < 2:
            return

        # Draw band on POSITIVE side (above/right of path)
        self.draw_single_sided_band(painter, segments, period, side=1)

        # Draw band on NEGATIVE side (below/left of path)
        self.draw_single_sided_band(painter, segments, period, side=-1)

    def draw_single_sided_band(self, painter, segments, period, side):
        """Draw a single-sided band (side = 1 or -1 for above/below path)"""
        if len(segments) < 2:
            return

        # Create two parallel paths for inner and outer edges
        inner_path = QPainterPath()
        outer_path = QPainterPath()

        first = True
        for seg in segments:
            x, y = seg['x'], seg['y']
            perp = seg['perp_angle']
            center_offset = seg['center_offset'] * side  # Apply side multiplier
            band_width = seg['band_width']

            # Inner and outer edge positions
            inner_offset = center_offset - (band_width / 2) * side
            outer_offset = center_offset + (band_width / 2) * side

            inner_x = x + inner_offset * math.cos(perp)
            inner_y = y + inner_offset * math.sin(perp)
            outer_x = x + outer_offset * math.cos(perp)
            outer_y = y + outer_offset * math.sin(perp)

            if first:
                inner_path.moveTo(inner_x, inner_y)
                outer_path.moveTo(outer_x, outer_y)
                first = False
            else:
                inner_path.lineTo(inner_x, inner_y)
                outer_path.lineTo(outer_x, outer_y)

        # Combine into filled band
        band_polygon = QPainterPath()
        band_polygon.addPath(inner_path)

        outer_points = []
        for i in range(outer_path.elementCount()):
            elem = outer_path.elementAt(i)
            outer_points.append(QPointF(elem.x, elem.y))

        for pt in reversed(outer_points):
            band_polygon.lineTo(pt)

        band_polygon.closeSubpath()

        # Elegant color scheme - semi-transparent with subtle borders
        block_colors = {
            1: QColor(255, 100, 120, 100),   # Soft red (s-block)
            2: QColor(100, 160, 255, 100),   # Soft blue (s/p transition)
            3: QColor(100, 160, 255, 100),   # Soft blue (p-block)
            4: QColor(255, 210, 100, 100),   # Soft gold (d-block starts)
            5: QColor(255, 210, 100, 100),   # Soft gold (d-block)
            6: QColor(140, 255, 170, 100),   # Soft green (f-block)
            7: QColor(140, 255, 170, 100)    # Soft green (f-block)
        }

        border_thickness = 1.5
        painter.setPen(QPen(QColor(200, 200, 220, 120), border_thickness))
        painter.setBrush(QBrush(block_colors.get(period, QColor(150, 150, 150, 100))))
        painter.drawPath(band_polygon)

    def draw_wedge_segments(self, painter, segments, period):
        """Draw wedge segments between elements with borders and glows for property encoding"""
        if len(segments) < 2:
            return

        # Draw on BOTH sides (symmetric)
        for side in [1, -1]:
            for i in range(len(segments) - 1):
                seg1 = segments[i]
                seg2 = segments[i + 1]

                if not seg1.get('has_element'):
                    continue

                # Get positions and angles
                x1, y1 = seg1['x'], seg1['y']
                x2, y2 = seg2['x'], seg2['y']
                perp1 = seg1['perp_angle']
                perp2 = seg2['perp_angle']
                tang1 = seg1['tangent_angle']

                # Get band dimensions (scaled by side)
                center_offset1 = seg1['center_offset'] * side
                center_offset2 = seg2['center_offset'] * side
                band_width = seg1['band_width']

                inner_offset1 = center_offset1 - (band_width / 2) * side
                outer_offset1 = center_offset1 + (band_width / 2) * side
                inner_offset2 = center_offset2 - (band_width / 2) * side
                outer_offset2 = center_offset2 + (band_width / 2) * side

                # Create trapezoid connecting the two elements
                path = QPainterPath()

                # Start at inner edge of first element
                inner_x1 = x1 + inner_offset1 * math.cos(perp1)
                inner_y1 = y1 + inner_offset1 * math.sin(perp1)

                # Outer edge of first element
                outer_x1 = x1 + outer_offset1 * math.cos(perp1)
                outer_y1 = y1 + outer_offset1 * math.sin(perp1)

                # Inner edge of second element
                inner_x2 = x2 + inner_offset2 * math.cos(perp2)
                inner_y2 = y2 + inner_offset2 * math.sin(perp2)

                # Outer edge of second element
                outer_x2 = x2 + outer_offset2 * math.cos(perp2)
                outer_y2 = y2 + outer_offset2 * math.sin(perp2)

                # Build wedge polygon
                path.moveTo(inner_x1, inner_y1)
                path.lineTo(inner_x2, inner_y2)
                path.lineTo(outer_x2, outer_y2)
                path.lineTo(outer_x1, outer_y1)
                path.closeSubpath()

                # Get element properties for encoding
                elem = seg1

                # Glow effect based on glow property
                glow_size, glow_intensity = self.get_glow_params(elem)
                if glow_size > 0 and glow_intensity > 0:
                    # Draw glow around wedge center
                    wedge_center_x = (inner_x1 + inner_x2 + outer_x1 + outer_x2) / 4
                    wedge_center_y = (inner_y1 + inner_y2 + outer_y1 + outer_y2) / 4

                    fill_color = self.get_property_color(elem, self.fill_property, "fill")
                    glow_grad = QRadialGradient(wedge_center_x, wedge_center_y, glow_size * 1.5)
                    glow_c = QColor(fill_color)
                    glow_c.setAlpha(int(60 * glow_intensity))
                    glow_grad.setColorAt(0, glow_c)
                    glow_c.setAlpha(0)
                    glow_grad.setColorAt(1, glow_c)
                    painter.setBrush(QBrush(glow_grad))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(wedge_center_x, wedge_center_y), glow_size * 1.5, glow_size * 1.5)

                # Border based on border property
                border_width = self.get_border_width(elem)
                border_color = self.get_property_color(elem, self.border_color_property, "border")

                # Draw border around wedge segment
                painter.setPen(QPen(border_color, border_width, Qt.PenStyle.SolidLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)

    def draw_isotope_parallel_bands(self, painter, period_segments):
        """Draw isotopes as thin white parallel bands along the main path"""
        # Get any period with elements to follow the path
        any_segments = None
        for period in range(1, 8):
            if len(period_segments[period]) > 1:
                any_segments = period_segments[period]
                break

        if not any_segments:
            return

        # Draw thin white parallel lines for elements with isotopes
        for seg in any_segments:
            if not seg.get('has_element') or not seg.get('isotopes'):
                continue

            x, y = seg['x'], seg['y']
            perp = seg['perp_angle']
            isotopes = seg['isotopes']

            # Draw thin lines near the path for each isotope
            num_isotopes = len(isotopes)
            spacing = 6  # Pixels between isotope lines

            for iso_idx, (mass, abundance) in enumerate(isotopes):
                # Position isotope lines close to the main path
                offset = (iso_idx - num_isotopes / 2) * spacing

                # Line along the path
                line_x1 = x + offset * math.cos(perp) - 5 * math.sin(perp)
                line_y1 = y + offset * math.sin(perp) + 5 * math.cos(perp)
                line_x2 = x + offset * math.cos(perp) + 5 * math.sin(perp)
                line_y2 = y + offset * math.sin(perp) - 5 * math.cos(perp)

                # Thickness based on abundance
                line_thickness = 0.5 + (abundance / 100) * 2

                # White/light color
                iso_color = QColor(255, 255, 255, int(100 + (abundance / 100) * 100))

                painter.setPen(QPen(iso_color, line_thickness, Qt.PenStyle.SolidLine))
                painter.drawLine(QPointF(line_x1, line_y1), QPointF(line_x2, line_y2))

    def draw_isotope_substrata(self, painter, segments, period):
        """Draw isotope sub-strata as fine lines within the layer band"""
        if len(segments) < 2:
            return

        # Draw isotope indicators for elements that have them
        for seg in segments:
            if not seg.get('has_element') or not seg.get('isotopes'):
                continue

            x, y = seg['x'], seg['y']
            perp = seg['perp_angle']
            center_offset = seg['center_offset']
            band_width = seg['band_width']

            isotopes = seg['isotopes']
            if not isotopes:
                continue

            # Draw thin lines for each isotope within the band
            num_isotopes = len(isotopes)
            for iso_idx, (mass, abundance) in enumerate(isotopes):
                # Position isotope line within the band based on its index
                iso_offset_factor = (iso_idx + 1) / (num_isotopes + 1)
                iso_offset = center_offset - band_width/2 + iso_offset_factor * band_width

                # Line length proportional to abundance
                line_length = (abundance / 100) * 15

                iso_x1 = x + iso_offset * math.cos(perp)
                iso_y1 = y + iso_offset * math.sin(perp)
                iso_x2 = iso_x1 + line_length * math.cos(perp)
                iso_y2 = iso_y1 + line_length * math.sin(perp)

                # Color based on neutron count
                neutron_count = mass - seg['z']
                iso_color = QColor(150 + neutron_count * 8, 150 + neutron_count * 5, 255, 120)

                painter.setPen(QPen(iso_color, 1, Qt.PenStyle.SolidLine))
                painter.drawLine(QPointF(iso_x1, iso_y1), QPointF(iso_x2, iso_y2))

    def draw_element_marker(self, painter, elem):
        """Draw elegant element marker - clean and minimal"""
        if not elem.get('symbol'):
            return

        x, y = elem['x'], elem['y']
        perp = elem['perp_angle']
        center_offset = elem['center_offset']
        band_width = elem['band_width']

        # Draw a small dot at the spiral path position
        dot_color = self.get_property_color(elem, self.fill_property, "fill")

        # Highlight if hovered/selected
        if elem == self.hovered_element:
            dot_color = dot_color.lighter(150)
            dot_size = 5
        elif elem == self.selected_element:
            dot_color = dot_color.lighter(170)
            dot_size = 6
        else:
            dot_size = 3

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(QPointF(x, y), dot_size, dot_size)

        # Draw element symbol on the outermost layer (period 7 position)
        # This keeps text from overlapping and cluttering
        text_offset = center_offset
        text_x = x + text_offset * math.cos(perp)
        text_y = y + text_offset * math.sin(perp)

        # Only show text for selected/hovered or every Nth element
        show_text = (elem == self.hovered_element or
                     elem == self.selected_element or
                     elem.get('element_index', 0) % 5 == 0)

        if show_text:
            # Draw symbol with colored text and white border
            symbol_text_color = self.get_property_color(elem, self.symbol_text_color_property, "symbol_text")
            symbol_text_color.setAlpha(220)
            font = QFont('Arial', 9, QFont.Weight.Bold)
            painter.setFont(font)
            text_rect = QRectF(text_x - 20, text_y - 10, 40, 20)

            # Draw symbol with white border
            symbol_path = QPainterPath()
            symbol_path.addText(text_rect.left() + text_rect.width()/2 - painter.fontMetrics().horizontalAdvance(elem['symbol'])/2,
                              text_rect.top() + text_rect.height()/2 + painter.fontMetrics().ascent()/2,
                              font, elem['symbol'])
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(symbol_path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(symbol_text_color))
            painter.drawPath(symbol_path)

    def draw_placeholder_wedge(self, painter, sample_elem, period):
        """Draw transparent placeholder wedge for missing element"""
        x, y = sample_elem['x'], sample_elem['y']
        tangent = sample_elem['tangent_angle']
        perp = sample_elem['perp_angle']
        half_span = sample_elem['wedge_half_span']

        # Calculate offsets for this period
        period_wedge_widths = {1: 50, 2: 55, 3: 60, 4: 70, 5: 80, 6: 90, 7: 100}
        period_offsets = {1: 0}
        for p in range(2, 8):
            period_offsets[p] = period_offsets[p-1] + period_wedge_widths[p-1]

        inner_offset = period_offsets[period]
        outer_offset = inner_offset + period_wedge_widths[period]

        # Create wedge path
        path = QPainterPath()

        # Inner edge points
        inner_x1 = x + inner_offset * math.cos(perp) - half_span * math.cos(tangent)
        inner_y1 = y + inner_offset * math.sin(perp) - half_span * math.sin(tangent)
        inner_x2 = x + inner_offset * math.cos(perp) + half_span * math.cos(tangent)
        inner_y2 = y + inner_offset * math.sin(perp) + half_span * math.sin(tangent)

        # Outer edge points
        outer_x1 = x + outer_offset * math.cos(perp) - half_span * math.cos(tangent)
        outer_y1 = y + outer_offset * math.sin(perp) - half_span * math.sin(tangent)
        outer_x2 = x + outer_offset * math.cos(perp) + half_span * math.cos(tangent)
        outer_y2 = y + outer_offset * math.sin(perp) + half_span * math.sin(tangent)

        # Build wedge polygon
        path.moveTo(inner_x1, inner_y1)
        path.lineTo(inner_x2, inner_y2)
        path.lineTo(outer_x2, outer_y2)
        path.lineTo(outer_x1, outer_y1)
        path.closeSubpath()

        # Draw transparent outline
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(100, 100, 120, 40), 1, Qt.PenStyle.DotLine))
        painter.drawPath(path)

    def draw_serpentine_element(self, painter, elem):
        """Draw serpentine element as wedge extending from path"""
        x, y = elem['x'], elem['y']
        tangent = elem['tangent_angle']
        perp = elem['perp_angle']
        inner_offset = elem['inner_offset']
        outer_offset = elem['outer_offset']
        half_span = elem['wedge_half_span']

        # Get fill color
        fill_color = self.get_property_color(elem, self.fill_property, "fill")

        if elem == self.hovered_element:
            fill_color = fill_color.lighter(130)
        if elem == self.selected_element:
            fill_color = fill_color.lighter(150)

        # Calculate wedge center (midpoint between inner and outer edges)
        mid_offset = (inner_offset + outer_offset) / 2
        wedge_center_x = x + mid_offset * math.cos(perp)
        wedge_center_y = y + mid_offset * math.sin(perp)

        # External Glow
        glow_radius_pct = self.get_glow_radius_percent(elem)
        glow_intensity = self.get_glow_intensity(elem)
        if glow_radius_pct > 0 and self.glow_type == "external":
            glow_intensity_adj = glow_intensity
            glow_radius_pct_adj = glow_radius_pct
            if elem == self.hovered_element or elem == self.selected_element:
                glow_radius_pct_adj *= 1.5
                glow_intensity_adj *= 1.2
            glow_color = self.get_property_color(elem, self.glow_property, "glow")
            # Calculate glow size as percentage of wedge thickness
            wedge_extent = outer_offset - inner_offset
            glow_size = wedge_extent * glow_radius_pct_adj
            glow_grad = QRadialGradient(wedge_center_x, wedge_center_y, glow_size + wedge_extent)
            glow_c = QColor(glow_color)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(int(120 * glow_intensity_adj))
            glow_grad.setColorAt(0.7, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(wedge_center_x, wedge_center_y), glow_size + wedge_extent, glow_size + wedge_extent)

        # Create wedge path as a quadrilateral
        path = QPainterPath()

        # Inner edge points
        inner_x1 = x + inner_offset * math.cos(perp) - half_span * math.cos(tangent)
        inner_y1 = y + inner_offset * math.sin(perp) - half_span * math.sin(tangent)
        inner_x2 = x + inner_offset * math.cos(perp) + half_span * math.cos(tangent)
        inner_y2 = y + inner_offset * math.sin(perp) + half_span * math.sin(tangent)

        # Outer edge points
        outer_x1 = x + outer_offset * math.cos(perp) - half_span * math.cos(tangent)
        outer_y1 = y + outer_offset * math.sin(perp) - half_span * math.sin(tangent)
        outer_x2 = x + outer_offset * math.cos(perp) + half_span * math.cos(tangent)
        outer_y2 = y + outer_offset * math.sin(perp) + half_span * math.sin(tangent)

        # Inner ring as split (inner portion of wedge)
        inner_ring_fraction = self.get_inner_ring_size(elem)
        if self.ring_property != "none" and inner_ring_fraction > 0:
            wedge_thickness = outer_offset - inner_offset
            ring_thickness = wedge_thickness * inner_ring_fraction
            ring_outer_offset = inner_offset + ring_thickness

            # Inner ring path
            ring_path = QPainterPath()
            ring_path.moveTo(inner_x1, inner_y1)
            ring_path.lineTo(inner_x2, inner_y2)

            # Ring outer edge points
            ring_outer_x2 = x + ring_outer_offset * math.cos(perp) + half_span * math.cos(tangent)
            ring_outer_y2 = y + ring_outer_offset * math.sin(perp) + half_span * math.sin(tangent)
            ring_outer_x1 = x + ring_outer_offset * math.cos(perp) - half_span * math.cos(tangent)
            ring_outer_y1 = y + ring_outer_offset * math.sin(perp) - half_span * math.sin(tangent)

            ring_path.lineTo(ring_outer_x2, ring_outer_y2)
            ring_path.lineTo(ring_outer_x1, ring_outer_y1)
            ring_path.closeSubpath()

            # Fill inner ring
            ring_color = self.get_property_color(elem, self.ring_property, "ring")
            painter.fillPath(ring_path, ring_color)

            # Update main path to exclude ring
            path = QPainterPath()
            ring_inner_x1 = ring_outer_x1
            ring_inner_y1 = ring_outer_y1
            ring_inner_x2 = ring_outer_x2
            ring_inner_y2 = ring_outer_y2

            path.moveTo(ring_inner_x1, ring_inner_y1)
            path.lineTo(ring_inner_x2, ring_inner_y2)
            path.lineTo(outer_x2, outer_y2)
            path.lineTo(outer_x1, outer_y1)
            path.closeSubpath()
        else:
            # Build full wedge polygon
            path.moveTo(inner_x1, inner_y1)
            path.lineTo(inner_x2, inner_y2)
            path.lineTo(outer_x2, outer_y2)
            path.lineTo(outer_x1, outer_y1)
            path.closeSubpath()

        # Fill wedge with gradient
        wedge_gradient = QLinearGradient(
            x + inner_offset * math.cos(perp), y + inner_offset * math.sin(perp),
            x + outer_offset * math.cos(perp), y + outer_offset * math.sin(perp)
        )
        bright_color = fill_color.lighter(115)
        wedge_gradient.setColorAt(0, bright_color)
        wedge_gradient.setColorAt(1, fill_color)
        painter.fillPath(path, QBrush(wedge_gradient))

        # Internal Glow
        if glow_radius_pct > 0 and self.glow_type == "internal":
            glow_intensity_adj = glow_intensity
            glow_radius_pct_adj = glow_radius_pct
            if elem == self.hovered_element or elem == self.selected_element:
                glow_radius_pct_adj *= 1.5
                glow_intensity_adj *= 1.2
            glow_color = self.get_property_color(elem, self.glow_property, "glow")
            # Calculate glow size as percentage of wedge thickness
            wedge_thickness = outer_offset - inner_offset
            glow_size = wedge_thickness * glow_radius_pct_adj
            max_glow = wedge_thickness * 0.6
            constrained_glow = min(glow_size, max_glow)
            glow_grad = QRadialGradient(wedge_center_x, wedge_center_y, constrained_glow)
            glow_c = QColor(glow_color)
            glow_c.setAlpha(int(100 * glow_intensity_adj))
            glow_grad.setColorAt(0, glow_c)
            glow_c.setAlpha(0)
            glow_grad.setColorAt(1, glow_c)
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.save()
            painter.setClipPath(path)
            painter.drawEllipse(QPointF(wedge_center_x, wedge_center_y), constrained_glow, constrained_glow)
            painter.restore()

        # Border
        border_width = self.get_border_width(elem)
        border_width = max(1, min(4, border_width))
        if elem == self.selected_element:
            border_width += 2

        border_color = QColor(255, 255, 255, 180) if (elem == self.hovered_element or elem == self.selected_element) else QColor(255, 255, 255, 80)
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Isotope layers (stacked along outer edge)
        if self.show_isotopes and elem['isotopes']:
            sorted_isotopes = sorted(elem['isotopes'], key=lambda iso: iso[0])

            iso_offset = outer_offset + 8
            bar_length = half_span * 2

            for iso_idx, (mass, abundance) in enumerate(sorted_isotopes):
                # Calculate bar endpoints
                bar_x1 = x + iso_offset * math.cos(perp) - half_span * math.cos(tangent)
                bar_y1 = y + iso_offset * math.sin(perp) - half_span * math.sin(tangent)
                bar_x2 = x + iso_offset * math.cos(perp) + half_span * math.cos(tangent)
                bar_y2 = y + iso_offset * math.sin(perp) + half_span * math.sin(tangent)

                # Scale bar based on abundance
                abundance_factor = abundance / 100
                scaled_half_span = half_span * abundance_factor
                bar_x1_scaled = x + iso_offset * math.cos(perp) - scaled_half_span * math.cos(tangent)
                bar_y1_scaled = y + iso_offset * math.sin(perp) - scaled_half_span * math.sin(tangent)
                bar_x2_scaled = x + iso_offset * math.cos(perp) + scaled_half_span * math.cos(tangent)
                bar_y2_scaled = y + iso_offset * math.sin(perp) + scaled_half_span * math.sin(tangent)

                # Color based on neutron count
                neutron_count = mass - elem['z']
                iso_color = elem['block_color'].lighter(100 + neutron_count * 5)
                iso_color.setAlpha(140)

                painter.setPen(QPen(iso_color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(bar_x1_scaled, bar_y1_scaled), QPointF(bar_x2_scaled, bar_y2_scaled))

                iso_offset += 4  # Stack next isotope further out

        # Text with colored fills and white borders
        # Element Symbol
        symbol_text_color = self.get_property_color(elem, self.symbol_text_color_property, "symbol_text")
        font = QFont('Arial', 8, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = QRectF(wedge_center_x - 20, wedge_center_y - 8, 40, 16)

        # Draw symbol with white border
        symbol_path = QPainterPath()
        symbol_path.addText(text_rect.left() + text_rect.width()/2 - painter.fontMetrics().horizontalAdvance(elem['symbol'])/2,
                           text_rect.top() + text_rect.height()/2 + painter.fontMetrics().ascent()/2,
                           font, elem['symbol'])
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(symbol_path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(symbol_text_color))
        painter.drawPath(symbol_path)

        # Atomic Number
        atomic_num_text_color = self.get_property_color(elem, self.atomic_number_text_color_property, "atomic_number_text")
        font_tiny = QFont('Arial', 5)
        painter.setFont(font_tiny)
        num_rect = QRectF(wedge_center_x - 20, wedge_center_y + 6, 40, 10)

        # Draw atomic number with white border
        num_path = QPainterPath()
        num_str = str(elem['z'])
        num_path.addText(num_rect.left() + num_rect.width()/2 - painter.fontMetrics().horizontalAdvance(num_str)/2,
                        num_rect.top() + num_rect.height()/2 + painter.fontMetrics().ascent()/2,
                        font_tiny, num_str)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(num_path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(atomic_num_text_color))
        painter.drawPath(num_path)

    def get_available_orbitals(self, z):
        """
        Calculate available orbitals based on electron configuration.
        Returns list of (n, l, m, label) tuples for orbitals that contain electrons.

        Orbital filling order: 1s, 2s, 2p, 3s, 3p, 4s, 3d, 4p, 5s, 4d, 5p, 6s, 4f, 5d, 6p, 7s, 5f, 6d, 7p
        """
        orbitals = []

        # Filling order with (n, l, label, max_electrons)
        filling_order = [
            (1, 0, '1s', 2),
            (2, 0, '2s', 2),
            (2, 1, '2p', 6),
            (3, 0, '3s', 2),
            (3, 1, '3p', 6),
            (4, 0, '4s', 2),
            (3, 2, '3d', 10),
            (4, 1, '4p', 6),
            (5, 0, '5s', 2),
            (4, 2, '4d', 10),
            (5, 1, '5p', 6),
            (6, 0, '6s', 2),
            (4, 3, '4f', 14),
            (5, 2, '5d', 10),
            (6, 1, '6p', 6),
            (7, 0, '7s', 2),
            (5, 3, '5f', 14),
            (6, 2, '6d', 10),
            (7, 1, '7p', 6),
        ]

        electrons_remaining = z

        for n, l, label, max_electrons in filling_order:
            if electrons_remaining <= 0:
                break

            # Number of electrons in this orbital
            electrons_in_orbital = min(electrons_remaining, max_electrons)
            electrons_remaining -= electrons_in_orbital

            # Add all m values for this orbital (m ranges from -l to +l)
            for m in range(-l, l + 1):
                if l == 0:  # s orbital
                    m_label = ''
                elif l == 1:  # p orbital
                    m_names = ['px', 'py', 'pz']
                    m_label = f" ({m_names[m + 1]})"
                elif l == 2:  # d orbital
                    m_names = ['dxy', 'dyz', 'dz²', 'dxz', 'dx²-y²']
                    if -2 <= m <= 2:
                        m_label = f" ({m_names[m + 2]})"
                    else:
                        m_label = f" (m={m})"
                elif l == 3:  # f orbital
                    m_label = f" (m={m})"
                else:
                    m_label = f" (m={m})"

                full_label = f"{label}{m_label}"
                orbitals.append((n, l, m, full_label))

        return orbitals

    def draw_electron_probability_cloud(self, painter, center_x, center_y):
        """
        Draw electron probability cloud for selected element as background glow.
        The central graph/spiral represents the nucleus.
        """
        if not self.selected_element:
            return

        z = self.selected_element.get('z', 1)
        shells = get_electron_shell_distribution(z)

        if not shells:
            return

        # Get real shell radii in Angstroms
        real_radii_angstroms = get_real_shell_radii(z)
        num_shells = len(shells)

        # Nucleus size in pixels (element rings)
        if hasattr(self, 'outermost_radius'):
            nucleus_size_px = self.outermost_radius
        else:
            nucleus_size_px = 100

        # Scale factor to convert real distances (Angstroms) to pixels
        # The first shell radius determines the base scale
        if real_radii_angstroms:
            scale_factor = (nucleus_size_px * self.nucleus_to_shell_ratio) / real_radii_angstroms[0]
        else:
            scale_factor = nucleus_size_px

        # Get element color for the cloud
        fill_color = self.get_property_color(self.selected_element, self.fill_property)

        # Use selected orbital parameters to visualize specific orbital
        # Sample the orbital probability at multiple radial distances
        n, l, m = self.orbital_n, self.orbital_l, self.orbital_m

        # Determine maximum radius for this orbital (use the nth shell radius)
        # Cloud should encompass the shell, so use the actual shell radius
        if n <= len(real_radii_angstroms):
            shell_radius_angstroms = real_radii_angstroms[n - 1]
        else:
            shell_radius_angstroms = real_radii_angstroms[-1] if real_radii_angstroms else 10.0

        # Convert shell radius to pixels using same scaling as shells
        base_value_shell = shell_radius_angstroms * scale_factor
        if base_value_shell > 0 and self.nucleus_to_shell_ratio > 0:
            log_base_shell = math.log10(base_value_shell * self.nucleus_to_shell_ratio)
            t_shell = self.shell_power / 100.0
            log_result_shell = log_base_shell * (1 - t_shell) + 0 * t_shell
            shell_radius_px = nucleus_size_px + (10 ** log_result_shell)
        else:
            shell_radius_px = nucleus_size_px + shell_radius_angstroms * scale_factor

        # Cloud extends beyond the shell (use 2x for probability cloud extent)
        max_radius_angstroms = shell_radius_angstroms * 2.0
        max_radius_px = shell_radius_px  # Clouds draw out to this radius

        # Use SDF-based rendering for smooth probability cloud visualization
        # SDFRenderer provides better falloff, anti-aliasing, and orbital-specific shapes
        SDFRenderer.draw_orbital_cloud(
            painter=painter,
            cx=center_x,
            cy=center_y,
            n=n,
            l=l,
            m=m,
            shell_radius=shell_radius_px,
            rotation_x=self.rotation_x,
            rotation_y=self.rotation_y,
            opacity=self.cloud_opacity,
            Z=z,
            animation_phase=self.cloud_animation_phase
        )

    def draw_electron_shells(self, painter, center_x, center_y):
        """
        Draw concentric electron shells with electron dots for selected element.
        Wraps around the central graph representing the nucleus.
        Stores electron positions for click detection.
        """
        if not self.selected_element:
            return

        z = self.selected_element.get('z', 1)
        shells = get_electron_shell_distribution(z)

        # Get quantum numbers for each electron
        electron_quantum_numbers = get_electron_quantum_numbers(z)

        if not shells:
            return

        # Clear previous electron positions
        self.electron_positions = []

        # Get real shell radii in Angstroms
        real_radii_angstroms = get_real_shell_radii(z)

        # Nucleus size in pixels (element rings)
        if hasattr(self, 'outermost_radius'):
            nucleus_size_px = self.outermost_radius
        else:
            nucleus_size_px = 100  # Fallback

        # Scale factor: convert Angstroms to pixels
        # Nucleus represents ~few femtometers, shells are ~Angstroms (10^5 scale difference)
        # nucleus_to_shell_ratio controls how we visualize this scale
        # Real atomic radius for reference: ~1-3 Angstroms for most atoms
        # We want: first_shell_radius_px = nucleus_size_px * (1 + nucleus_to_shell_ratio)
        # So: scale_factor = (nucleus_size_px * nucleus_to_shell_ratio) / real_radii_angstroms[0]

        if real_radii_angstroms:
            # Scale factor to convert real distances (Angstroms) to pixels
            # Multiply ratio slider value to scale the shells relative to nucleus
            scale_factor = (nucleus_size_px * self.nucleus_to_shell_ratio) / real_radii_angstroms[0]
        else:
            scale_factor = nucleus_size_px

        # Get element color
        elem_color = self.get_property_color(self.selected_element, self.fill_property)

        # Track electron index for quantum number lookup
        electron_idx = 0

        # Draw each shell
        for shell_idx, electron_count in enumerate(shells):
            # Get real radius in Angstroms
            real_radius_angstroms = real_radii_angstroms[shell_idx]

            # Convert to pixels with logarithmic lerp scaling
            # Higher power = tighter logarithmic contraction (lerp toward 0)
            base_value_shell = real_radius_angstroms * scale_factor
            if base_value_shell > 0 and self.nucleus_to_shell_ratio > 0:
                log_base_shell = math.log10(base_value_shell * self.nucleus_to_shell_ratio)
                t_shell = self.shell_power / 100.0
                log_result_shell = log_base_shell * (1 - t_shell) + 0 * t_shell
                radius = nucleus_size_px + (10 ** log_result_shell)
            else:
                radius = nucleus_size_px + real_radius_angstroms * scale_factor

            # Draw shell circle
            shell_color = QColor(elem_color)
            shell_color.setAlpha(150)
            painter.setPen(QPen(shell_color, 2, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

            # Draw electrons as dots distributed around the shell
            electron_size = 4
            electron_color = QColor(200, 220, 255, 220)  # Light blue for electrons

            for i in range(electron_count):
                # Get quantum numbers for this electron
                if electron_idx < len(electron_quantum_numbers):
                    n, l, m = electron_quantum_numbers[electron_idx]
                else:
                    n, l, m = shell_idx + 1, 0, 0  # Fallback

                # Distribute electrons evenly around the shell
                angle = (2 * math.pi * i) / electron_count

                # Add slight randomness to make it look more natural
                angle_offset = math.sin(shell_idx * 0.5 + i * 0.3) * 0.1
                angle += angle_offset

                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)

                # Store electron position for click detection
                self.electron_positions.append((x, y, n, l, m, electron_size * 2))

                # Highlight if this is the selected orbital
                is_selected = (n == self.orbital_n and l == self.orbital_l and m == self.orbital_m)

                if is_selected:
                    selected_color = QColor(255, 255, 100, 255)  # Bright yellow
                    painter.setPen(QPen(selected_color, 2))
                    painter.setBrush(QBrush(selected_color))
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(electron_color))

                # Draw electron dot
                painter.drawEllipse(QPointF(x, y), electron_size, electron_size)

                # Add slight glow to electrons
                glow_gradient = QRadialGradient(x, y, electron_size * 2)
                if is_selected:
                    glow_color = QColor(255, 255, 100, 150)
                else:
                    glow_color = QColor(electron_color)
                    glow_color.setAlpha(100)
                glow_gradient.setColorAt(0, glow_color)
                glow_color.setAlpha(0)
                glow_gradient.setColorAt(1, glow_color)

                painter.setBrush(QBrush(glow_gradient))
                painter.drawEllipse(QPointF(x, y), electron_size * 2, electron_size * 2)

                electron_idx += 1  # Move to next electron

            # Draw shell label with radial offset to prevent overlap
            # Offset by 4 degrees per shell index
            angle_offset = math.radians(shell_idx * 4)
            label_distance = radius + 10
            label_x = center_x + label_distance * math.cos(angle_offset)
            label_y = center_y + label_distance * math.sin(angle_offset)
            painter.setPen(QPen(shell_color, 1))
            font = QFont('Arial', 9)
            painter.setFont(font)
            painter.drawText(int(label_x), int(label_y), f"Shell {shell_idx + 1}: {electron_count}e⁻")

    def draw_centered_element_display(self, painter, center_x, center_y):
        """
        Draw a centered circular display showing the selected element's symbol and atomic number.
        This appears in the center when an element is selected.
        """
        if not self.selected_element:
            return

        # Get element info
        symbol = self.selected_element['symbol']
        z = self.selected_element['z']

        # Get element color
        elem_color = self.get_property_color(self.selected_element, self.fill_property)

        # Circle size - should fit inside innermost radius
        circle_radius = 35

        # Draw outer glow
        glow_gradient = QRadialGradient(center_x, center_y, circle_radius * 1.8)
        glow_color = QColor(elem_color)
        glow_color.setAlpha(80)
        glow_gradient.setColorAt(0, glow_color)
        glow_color.setAlpha(0)
        glow_gradient.setColorAt(1, glow_color)
        painter.setBrush(QBrush(glow_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center_x, center_y), circle_radius * 1.8, circle_radius * 1.8)

        # Draw main circle with gradient
        gradient = QRadialGradient(center_x, center_y, circle_radius)
        bright_color = QColor(elem_color).lighter(120)
        bright_color.setAlpha(200)
        gradient.setColorAt(0, bright_color)
        elem_color.setAlpha(180)
        gradient.setColorAt(0.7, elem_color)
        elem_color.setAlpha(160)
        gradient.setColorAt(1, elem_color)

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.drawEllipse(QPointF(center_x, center_y), circle_radius, circle_radius)

        # Draw element symbol (large)
        painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
        symbol_font = QFont('Arial', 20, QFont.Weight.Bold)
        painter.setFont(symbol_font)

        # Center the text
        fm = painter.fontMetrics()
        symbol_width = fm.horizontalAdvance(symbol)
        symbol_height = fm.height()
        symbol_x = center_x - symbol_width / 2
        symbol_y = center_y + symbol_height / 4  # Slight offset for visual centering

        painter.drawText(int(symbol_x), int(symbol_y), symbol)

        # Draw atomic number (small, below symbol)
        number_font = QFont('Arial', 10)
        painter.setFont(number_font)
        number_text = str(z)
        fm_number = painter.fontMetrics()
        number_width = fm_number.horizontalAdvance(number_text)
        number_x = center_x - number_width / 2
        number_y = center_y + circle_radius * 0.6

        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
        painter.drawText(int(number_x), int(number_y), number_text)

    def draw_subatomic_particles(self, painter, center_x, center_y):
        """
        Draw subatomic particles as simple colored circles (like molecule atom visualization).
        Shows protons (red) and neutrons (gray) as circles arranged in a grid pattern.
        """
        if not self.selected_element or not self.show_subatomic_particles:
            return

        # Use the simple circle-based rendering (matching molecule visualization style)
        self.draw_subatomic_particles_simple(painter, center_x, center_y)

    def draw_subatomic_particles_simple(self, painter, center_x, center_y):
        """
        Draw subatomic particles as simple circles (matching molecule visualization style).
        Shows protons (red) and neutrons (blue/gray) as small circles.
        """
        z = self.selected_element.get('z', 1)

        # Get isotope information for neutron count
        isotopes = self.selected_element.get('isotopes', [])
        if isotopes:
            # Use most abundant isotope
            most_abundant = max(isotopes, key=lambda iso: iso[1] if isinstance(iso, tuple) else iso.get('abundance', 0))
            mass = most_abundant[0] if isinstance(most_abundant, tuple) else most_abundant.get('mass_number', z * 2)
        else:
            # Estimate mass number
            mass = z * 2

        neutrons = mass - z
        total_nucleons = z + neutrons

        # Calculate particle size - use consistent size like molecule atoms
        particle_radius = 8  # Fixed radius for consistency

        # Calculate grid layout for particles
        # Arrange in a roughly circular pattern
        particles_per_row = int(math.ceil(math.sqrt(total_nucleons)))

        # Calculate spacing
        spacing = particle_radius * 2.5

        # Calculate total grid size
        grid_width = particles_per_row * spacing
        grid_height = particles_per_row * spacing

        # Start position (top-left of grid, centered around center_x, center_y)
        start_x = center_x - grid_width / 2 + spacing / 2
        start_y = center_y - grid_height / 2 + spacing / 2

        # Draw protons first, then neutrons
        particle_index = 0

        # Draw all particles (protons first, then neutrons)
        for i in range(total_nucleons):
            is_proton = i < z

            # Calculate position in grid
            row = particle_index // particles_per_row
            col = particle_index % particles_per_row

            x = start_x + col * spacing
            y = start_y + row * spacing

            # Set color based on particle type
            if is_proton:
                # Proton - red
                base_color = QColor(255, 100, 100)
                label = "p+"
            else:
                # Neutron - blue/gray
                base_color = QColor(140, 140, 200)
                label = "n"

            # Draw glow effect (similar to molecule atoms)
            glow_gradient = QRadialGradient(x, y, particle_radius * 1.5)
            glow_color = QColor(base_color)
            glow_color.setAlpha(80)
            glow_gradient.setColorAt(0, glow_color)
            glow_color.setAlpha(0)
            glow_gradient.setColorAt(1, glow_color)
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), particle_radius * 1.5, particle_radius * 1.5)

            # Draw particle circle
            painter.setBrush(QBrush(base_color))
            painter.setPen(QPen(base_color.darker(120), 1))
            painter.drawEllipse(QPointF(x, y), particle_radius, particle_radius)

            # Draw label
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 6, QFont.Weight.Bold))
            text_rect = QRectF(x - particle_radius, y - particle_radius,
                             particle_radius * 2, particle_radius * 2)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

            particle_index += 1

        # Draw legend
        legend_x = center_x - grid_width / 2 - 60
        legend_y = center_y - grid_height / 2

        painter.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))

        # Title
        painter.drawText(int(legend_x), int(legend_y), "Subatomic Particles:")

        # Proton legend
        painter.setBrush(QBrush(QColor(255, 100, 100, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(legend_x + 10, legend_y + 15), 6, 6)
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
        painter.setFont(QFont('Arial', 8))
        painter.drawText(int(legend_x + 20), int(legend_y + 20), f"{z} Protons (p+)")

        # Neutron legend
        painter.setBrush(QBrush(QColor(140, 140, 200, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(legend_x + 10, legend_y + 35), 6, 6)
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
        painter.drawText(int(legend_x + 20), int(legend_y + 40), f"{neutrons} Neutrons (n)")

        # Total
        painter.setFont(QFont('Arial', 8, QFont.Weight.Bold))
        painter.drawText(int(legend_x), int(legend_y + 60), f"Total: {total_nucleons} nucleons")

    def draw_subatomic_particles_complex(self, painter, center_x, center_y):
        """
        Draw subatomic particles using realistic nuclear physics positioning.
        Uses liquid drop model with 3D spherical packing for nucleons.
        Shows protons (red) and neutrons (gray) packed in nucleus sphere.
        """
        if not self.selected_element or not self.show_subatomic_particles:
            return

        z = self.selected_element.get('z', 1)
        symbol = self.selected_element.get('symbol', '')

        # Get isotope information for neutron count
        isotopes = self.selected_element.get('isotopes', [])
        if isotopes:
            # Use most abundant isotope (isotopes are now in tuple format: (mass, abundance))
            most_abundant = max(isotopes, key=lambda iso: iso[1] if isinstance(iso, tuple) else iso.get('abundance', 0))
            mass = most_abundant[0] if isinstance(most_abundant, tuple) else most_abundant.get('mass_number', z * 2)
        else:
            # Estimate mass number
            mass = z * 2

        neutrons = mass - z
        total_nucleons = z + neutrons

        # Calculate realistic nucleus radius using liquid drop model
        # R = r0 * A^(1/3) where r0 ≈ 1.25 fm and A is mass number
        # Scale to pixels for visualization
        r0_fm = 1.25  # Nuclear radius constant in femtometers
        nucleus_radius_fm = r0_fm * (total_nucleons ** (1/3))

        # Scale to screen pixels (arbitrary scaling for visibility)
        # Use a base scale that makes the nucleus visible
        if hasattr(self, 'outermost_radius'):
            base_scale = self.outermost_radius / 3  # Use 1/3 of outermost electron shell
        else:
            base_scale = 50

        nucleus_radius_px = base_scale * (nucleus_radius_fm / 5.0)  # Normalize by typical medium nucleus

        # Draw nucleus boundary circle
        painter.setPen(QPen(QColor(100, 100, 150, 120), 2))
        painter.setBrush(QBrush(QColor(40, 40, 60, 40)))  # Dark semi-transparent fill
        painter.drawEllipse(QPointF(center_x, center_y), nucleus_radius_px, nucleus_radius_px)

        # Particle size based on nucleus radius
        # Nucleons are approximately 1 fm in diameter
        particle_radius = nucleus_radius_px / (total_nucleons ** (1/3)) * 0.8
        particle_radius = max(2, min(particle_radius, 8))  # Clamp for visibility

        # Use highly optimized SDF with proper space folding
        painter.setPen(Qt.PenStyle.NoPen)

        # Pre-calculate rotation matrices
        cos_x = math.cos(self.rotation_x)
        sin_x = math.sin(self.rotation_x)
        cos_y = math.cos(self.rotation_y)
        sin_y = math.sin(self.rotation_y)

        # Calculate nucleon spacing to fit all nucleons inside nucleus
        # Space should be divided into a cubic grid that fits inside the sphere
        # Number of nucleons per dimension: cube_root(total_nucleons)
        nucleons_per_dim = max(1, int(math.ceil(total_nucleons ** (1/3))))

        # Nucleon spacing to fit inside nucleus radius
        # We need (nucleons_per_dim * nucleon_diameter) to fit in (2 * nucleus_radius_px)
        # With some margin to avoid edge clipping
        nucleon_diameter = (2.0 * nucleus_radius_px * 0.85) / nucleons_per_dim
        nucleon_radius = nucleon_diameter * 0.42  # Slightly smaller for separation

        # Major performance optimization - much larger pixel step
        pixel_step = max(2, int(nucleus_radius_px / 30))

        # Pre-calculate light direction
        light_dir_x, light_dir_y, light_dir_z = 0.5, -0.3, 0.8
        light_mag = math.sqrt(light_dir_x**2 + light_dir_y**2 + light_dir_z**2)
        light_dir_x /= light_mag
        light_dir_y /= light_mag
        light_dir_z /= light_mag

        # Calculate proton/neutron ratio for color distribution
        proton_ratio = z / total_nucleons

        # Offset folding origin to center the nucleon grid
        fold_offset = nucleons_per_dim * nucleon_diameter / 2

        # Iterate over screen pixels with large steps for performance
        for screen_y in range(int(center_y - nucleus_radius_px), int(center_y + nucleus_radius_px), pixel_step):
            for screen_x in range(int(center_x - nucleus_radius_px), int(center_x + nucleus_radius_px), pixel_step):
                dx = screen_x - center_x
                dy = screen_y - center_y

                # Quick circle rejection
                dist_2d_sq = dx * dx + dy * dy
                if dist_2d_sq > nucleus_radius_px * nucleus_radius_px:
                    continue

                # Single Z-slice for maximum performance
                z_3d = 0

                # 3D position
                x_3d = dx
                y_3d = dy

                # Inverse Y rotation
                x_rot = x_3d * cos_y - z_3d * sin_y
                z_rot = x_3d * sin_y + z_3d * cos_y
                x_3d = x_rot
                z_3d = z_rot

                # Inverse X rotation
                y_rot = y_3d * cos_x + z_3d * sin_x
                z_rot2 = -y_3d * sin_x + z_3d * cos_x
                y_3d = y_rot
                z_3d = z_rot2

                # Calculate distance from center
                dist_3d = math.sqrt(x_3d**2 + y_3d**2 + z_3d**2)

                # Only process inside nucleus
                if dist_3d < nucleus_radius_px:
                    # OPTIMIZED SPACE FOLDING - centered grid
                    # Offset coordinates to center the folding grid
                    x_fold = x_3d + fold_offset
                    y_fold = y_3d + fold_offset
                    z_fold = z_3d + fold_offset

                    # Fold space with modulo
                    folded_x = (x_fold % nucleon_diameter) - nucleon_diameter / 2
                    folded_y = (y_fold % nucleon_diameter) - nucleon_diameter / 2
                    folded_z = (z_fold % nucleon_diameter) - nucleon_diameter / 2

                    # Distance to nearest nucleon center
                    folded_dist = math.sqrt(folded_x**2 + folded_y**2 + folded_z**2)

                    # Inside nucleon sphere?
                    if folded_dist < nucleon_radius:
                        # Determine cell for proton/neutron hash
                        cell_x = int((x_fold / nucleon_diameter))
                        cell_y = int((y_fold / nucleon_diameter))
                        cell_z = int((z_fold / nucleon_diameter))

                        # Hash to determine proton vs neutron
                        cell_hash = (cell_x * 73856093 + cell_y * 19349663 + cell_z * 83492791) % 1000
                        is_proton = (cell_hash / 1000.0) < proton_ratio

                        # Fast approximate lighting without normal rotation
                        # Use folded distance for simple shading
                        lighting = 0.6 + 0.4 * (1.0 - folded_dist / nucleon_radius)

                        # Soft edge
                        edge_softness = 1.0 - (folded_dist / nucleon_radius) ** 1.5
                        edge_softness = max(0, min(1, edge_softness))

                        # Colors
                        if is_proton:
                            base_r, base_g, base_b = 255, 100, 100
                        else:
                            base_r, base_g, base_b = 200, 200, 220

                        # Apply shading
                        brightness = 1.4
                        r = min(255, int(base_r * lighting * edge_softness * brightness))
                        g = min(255, int(base_g * lighting * edge_softness * brightness))
                        b = min(255, int(base_b * lighting * edge_softness * brightness))
                        a = int(240 * edge_softness)

                        color = QColor(r, g, b, a)
                        painter.setBrush(QBrush(color))
                        painter.drawRect(screen_x, screen_y, pixel_step, pixel_step)

        # Draw legend for particle colors
        legend_x = center_x - nucleus_radius_px * 1.3
        legend_y = center_y + nucleus_radius_px * 0.5
        legend_size = max(particle_radius * 1.5, 4)

        painter.setFont(QFont('Arial', 9))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))

        # Nucleus info
        painter.drawText(int(legend_x), int(legend_y - 25), f"Nucleus Radius: {nucleus_radius_fm:.2f} fm")

        # Proton legend
        painter.setBrush(QBrush(QColor(255, 80, 80, 150)))
        painter.drawEllipse(QPointF(legend_x, legend_y), legend_size, legend_size)
        painter.drawText(int(legend_x + legend_size + 5), int(legend_y + 4), f"{z} protons")

        # Neutron legend
        painter.setBrush(QBrush(QColor(140, 140, 140, 120)))
        painter.drawEllipse(QPointF(legend_x, legend_y + 20), legend_size, legend_size)
        painter.drawText(int(legend_x + legend_size + 5), int(legend_y + 24), f"{neutrons} neutrons")

        # Total nucleons
        painter.drawText(int(legend_x), int(legend_y + 45), f"Mass Number: A = {total_nucleons}")

    def draw_subatomic_particles_sdf(self, painter, center_x, center_y):
        """
        Draw subatomic particles (protons and neutrons) using SDF-based rendering.
        Provides smoother visualization with proper depth-based blending.
        Uses liquid drop model for nuclear radius scaling.
        """
        if not self.selected_element or not self.show_subatomic_particles:
            return

        z = self.selected_element.get('z', 1)
        symbol = self.selected_element.get('symbol', '')

        # Get isotope information for neutron count
        isotopes = self.selected_element.get('isotopes', [])
        if isotopes:
            # Use most abundant isotope (isotopes are now in tuple format: (mass, abundance))
            most_abundant = max(isotopes, key=lambda iso: iso[1] if isinstance(iso, tuple) else iso.get('abundance', 0))
            mass = most_abundant[0] if isinstance(most_abundant, tuple) else most_abundant.get('mass_number', z * 2)
        else:
            # Estimate mass number
            mass = z * 2

        neutrons = mass - z

        # Calculate base radius for visualization
        if hasattr(self, 'outermost_radius'):
            base_radius = self.outermost_radius / 2  # Use half of outermost electron shell
        else:
            base_radius = 60

        # Use SDF renderer for smooth nucleus visualization
        SDFRenderer.draw_nucleus(
            painter=painter,
            cx=center_x,
            cy=center_y,
            protons=z,
            neutrons=neutrons,
            base_radius=base_radius,
            rotation_x=self.rotation_x,
            rotation_y=self.rotation_y,
            show_legend=True
        )

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming in all layout modes"""
        # Get mouse position before zoom
        mouse_x = event.position().x()
        mouse_y = event.position().y()

        # Calculate zoom factor
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        old_zoom = self.zoom_level
        self.zoom_level *= zoom_factor
        self.zoom_level = max(0.05, min(10.0, self.zoom_level))  # Much wider zoom range

        # Adjust pan to keep mouse position fixed
        if old_zoom != self.zoom_level:
            zoom_change = self.zoom_level / old_zoom
            self.pan_x = mouse_x - (mouse_x - self.pan_x) * zoom_change
            self.pan_y = mouse_y - (mouse_y - self.pan_y) * zoom_change

        self.update()

    def mouseMoveEvent(self, event):
        mouse_x = event.position().x()
        mouse_y = event.position().y()

        # Handle rotation in subatomic mode
        if hasattr(self, 'is_rotating') and self.is_rotating:
            dx = mouse_x - self.rotate_start_x
            dy = mouse_y - self.rotate_start_y

            # Convert pixel movement to rotation (sensitivity factor)
            sensitivity = 0.01
            self.rotation_y = self.rotate_start_yaw + dx * sensitivity
            self.rotation_x = self.rotate_start_pitch + dy * sensitivity

            # Update sliders if control panel exists
            if hasattr(self, 'control_panel') and self.control_panel:
                self.control_panel.rotation_x_slider.blockSignals(True)
                self.control_panel.rotation_y_slider.blockSignals(True)
                self.control_panel.rotation_x_slider.setValue(int(math.degrees(self.rotation_x) % 360))
                self.control_panel.rotation_y_slider.setValue(int(math.degrees(self.rotation_y) % 360))
                self.control_panel.rotation_x_slider.blockSignals(False)
                self.control_panel.rotation_y_slider.blockSignals(False)

            self.update()
            return

        # Handle panning in all modes
        if self.is_panning:
            dx = mouse_x - self.pan_start_x
            dy = mouse_y - self.pan_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start_x = mouse_x
            self.pan_start_y = mouse_y
            self.update()
            return

        self.hovered_element = None

        if self.layout_mode == PTLayoutMode.CIRCULAR:
            # Circular layout - angular wedge detection with zoom/pan transform
            transformed_x = (mouse_x - self.pan_x) / self.zoom_level
            transformed_y = (mouse_y - self.pan_y) / self.zoom_level

            center_x = self.width() / 2
            center_y = self.height() / 2
            mx = transformed_x - center_x
            my = transformed_y - center_y
            mouse_r = math.sqrt(mx**2 + my**2)
            mouse_angle = math.atan2(my, mx)

            for elem in self.elements:
                if (elem['r_inner'] <= mouse_r <= elem['r_outer']):
                    angle_start = normalize_angle(elem['angle_start'])
                    angle_end = normalize_angle(elem['angle_end'])
                    test_angle = normalize_angle(mouse_angle)

                    if angle_start <= angle_end:
                        if angle_start <= test_angle <= angle_end:
                            self.hovered_element = elem
                            break
                    else:
                        if test_angle >= angle_start or test_angle <= angle_end:
                            self.hovered_element = elem
                            break

        elif self.layout_mode == PTLayoutMode.SPIRAL:
            # Spiral layout - circular marker detection
            # Transform mouse coordinates to match the zoomed/panned view
            transformed_x = (mouse_x - self.pan_x) / self.zoom_level
            transformed_y = (mouse_y - self.pan_y) / self.zoom_level

            # Hit detection radius scales inversely with zoom
            hit_radius = 15 / self.zoom_level

            for elem in self.elements:
                if not elem.get('has_element'):
                    continue

                x, y = elem['x'], elem['y']
                dx = transformed_x - x
                dy = transformed_y - y
                dist = math.sqrt(dx**2 + dy**2)

                # Circular marker detection
                if dist < hit_radius:
                    self.hovered_element = elem
                    break

        elif self.layout_mode == PTLayoutMode.TABLE:
            # Table layout - rectangular cell detection with zoom/pan transform
            transformed_x = (mouse_x - self.pan_x) / self.zoom_level
            transformed_y = (mouse_y - self.pan_y) / self.zoom_level

            for elem in self.elements:
                x = elem['x']
                y = elem['y']
                cell_size = elem.get('cell_size', 50)

                # Check if mouse is within cell rectangle
                # (x, y) is top-left corner of cell
                if (x <= transformed_x <= x + cell_size and
                    y <= transformed_y <= y + cell_size):
                    self.hovered_element = elem
                    break

        elif self.layout_mode == PTLayoutMode.SERPENTINE:
            # Linear layout - box rectangle detection
            # Transform mouse coordinates to match the zoomed/panned view
            transformed_x = (mouse_x - self.pan_x) / self.zoom_level
            transformed_y = (mouse_y - self.pan_y) / self.zoom_level

            for elem in self.elements:
                if not elem.get('has_element'):
                    continue

                x = elem['x']
                y = elem['y']
                box_width = elem.get('box_width', 50)
                box_height = elem.get('box_height', 100)

                # Check if mouse is within box rectangle (boxes are centered at x,y)
                half_width = box_width / 2
                half_height = box_height / 2
                if (x - half_width <= transformed_x <= x + half_width and
                    y - half_height <= transformed_y <= y + half_height):
                    self.hovered_element = elem
                    break

        if self.hovered_element:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            # Emit hover signal when element changes
            self.element_hovered.emit(self.hovered_element)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        self.update()

    def mousePressEvent(self, event):
        # Middle mouse button or Ctrl+Left for panning in all modes
        if event.button() == Qt.MouseButton.MiddleButton or \
           (event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.is_panning = True
            self.pan_start_x = event.position().x()
            self.pan_start_y = event.position().y()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        # In subatomic mode with Shift+Left-click, rotate the view
        elif event.button() == Qt.MouseButton.LeftButton and self.show_subatomic_particles and self.selected_element and \
             (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.is_rotating = True
            self.rotate_start_x = event.position().x()
            self.rotate_start_y = event.position().y()
            self.rotate_start_pitch = self.rotation_x
            self.rotate_start_yaw = self.rotation_y
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            # Check for electron click first
            click_x = event.position().x()
            click_y = event.position().y()

            clicked_electron = False
            for ex, ey, n, l, m, click_radius in self.electron_positions:
                dist = math.sqrt((click_x - ex)**2 + (click_y - ey)**2)
                if dist <= click_radius:
                    # Clicked on an electron - select its orbital
                    self.orbital_n = n
                    self.orbital_l = l
                    self.orbital_m = m
                    clicked_electron = True

                    # Update control panel orbital selector and label
                    if hasattr(self, 'control_panel') and self.control_panel:
                        # Update selector to match clicked electron
                        for i in range(self.control_panel.orbital_selector.count()):
                            orbital_data = self.control_panel.orbital_selector.itemData(i)
                            if orbital_data and orbital_data == (n, l, m):
                                self.control_panel.orbital_selector.blockSignals(True)
                                self.control_panel.orbital_selector.setCurrentIndex(i)
                                self.control_panel.orbital_selector.blockSignals(False)
                                break
                        self.control_panel.update_orbital_label()

                    self.update()
                    break

            # If no electron clicked, check for element click
            if not clicked_electron and self.hovered_element:
                self.selected_element = self.hovered_element
                # Emit element selected signal
                self.element_selected.emit(self.selected_element)

                # Copy element data to clipboard
                clipboard_text = json.dumps(self.selected_element, indent=2, default=str)
                QGuiApplication.clipboard().setText(clipboard_text)

                # Update orbital selector when element changes
                if hasattr(self, 'control_panel') and self.control_panel:
                    # Set to first orbital of new element
                    z = self.selected_element.get('z', 1)
                    orbitals = self.get_available_orbitals(z)
                    if orbitals:
                        self.orbital_n, self.orbital_l, self.orbital_m, _ = orbitals[0]
                    self.control_panel.update_orbital_selector()

                self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release for panning and rotation"""
        if hasattr(self, 'is_rotating') and self.is_rotating:
            self.is_rotating = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self.is_panning:
            self.is_panning = False
            if self.hovered_element:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Recreate layout on resize for proper scaling
        if self.layout_mode == PTLayoutMode.CIRCULAR:
            self.create_circular_layout()
        elif self.layout_mode == PTLayoutMode.SPIRAL or self.layout_mode == PTLayoutMode.SERPENTINE:
            self.create_serpentine_layout()
        elif self.layout_mode == PTLayoutMode.TABLE:
            self.create_table_layout()
        elif self.layout_mode == PTLayoutMode.LINEAR:
            self.create_linear_layout()

    def reload_data(self):
        """Reload element data from files and refresh the display"""
        self.create_element_data()
        # Recreate layout based on current mode
        if self.layout_mode == PTLayoutMode.CIRCULAR:
            self.create_circular_layout()
        elif self.layout_mode == PTLayoutMode.SPIRAL or self.layout_mode == PTLayoutMode.SERPENTINE:
            self.create_serpentine_layout()
        elif self.layout_mode == PTLayoutMode.TABLE:
            self.create_table_layout()
        elif self.layout_mode == PTLayoutMode.LINEAR:
            self.create_linear_layout()
        self.update()


# Alias for backward compatibility
UnifiedPeriodicTable = UnifiedTable
