"""
Calculations Module
Contains color conversion functions and property-based color gradient calculations.
"""

import math
from PySide6.QtGui import QColor

# Physical constants
C = 299792458  # m/s (speed of light)


def get_block_color(block):
    """Base colors for orbital blocks"""
    colors = {
        's': QColor(255, 80, 100),    # Neon red
        'p': QColor(80, 150, 255),    # Electric blue
        'd': QColor(255, 200, 80),    # Golden
        'f': QColor(120, 255, 150)    # Neon green
    }
    return colors.get(block, QColor(200, 200, 200))


def ev_to_frequency(ev):
    """Convert eV to PetaHertz"""
    h = 4.135667696e-15  # eV·s
    return ev / h / 1e15  # PHz


def ev_to_wavelength(ev):
    """Convert eV to wavelength in nanometers"""
    h = 6.62607015e-34  # J·s
    e = 1.602176634e-19  # J/eV
    return (h * C) / (ev * e) * 1e9  # nm


# Spectrum cache: {(z, ie, max_n): spectrum_lines}
_spectrum_cache = {}

def calculate_emission_spectrum(z, ionization_energy_ev, max_n=20):
    """
    Calculate approximate emission spectrum lines for an element.
    Uses simplified Rydberg-like formula adjusted for actual ionization energy.
    Results are cached for performance.

    Args:
        z: Atomic number
        ionization_energy_ev: First ionization energy in eV
        max_n: Maximum principal quantum number to calculate (default 20)
               Higher values generate more spectral lines but take longer
               Typical values: 10 (fast), 20 (default), 50 (detailed)

    Returns:
        List of (wavelength_nm, relative_intensity) tuples for visible/near-visible lines
    """
    # Check cache first
    cache_key = (z, ionization_energy_ev, max_n)
    if cache_key in _spectrum_cache:
        return _spectrum_cache[cache_key]

    # Rydberg constant
    R_inf = 10973731.6  # m^-1

    # Approximate effective charge (simplified screening model)
    # For outer electrons, effective charge is reduced by inner electron screening
    Z_eff = max(1.0, z ** 0.5)  # Very simplified

    lines = []

    # Calculate spectral lines for transitions to lower energy levels
    # Use configurable max_n for richer spectra
    # This generates many spectral lines for a more realistic appearance
    for n_upper in range(2, max_n + 1):
        for n_lower in range(1, n_upper):
            # Energy difference in eV (scaled by actual ionization energy)
            # E = -13.6 * Z_eff^2 / n^2 (hydrogen-like approximation)
            # Scale by ratio of actual IE to hydrogen IE
            scale_factor = ionization_energy_ev / 13.6
            E_upper = -13.6 * scale_factor / (n_upper ** 2)
            E_lower = -13.6 * scale_factor / (n_lower ** 2)
            delta_E = E_upper - E_lower  # Positive value (upper is less negative)

            if delta_E <= 0:
                continue

            # Convert energy to wavelength
            wavelength = ev_to_wavelength(delta_E)

            # Only keep lines in extended visible range (200-1000nm)
            # UV to near-IR
            if 200 <= wavelength <= 1000:
                # Approximate relative intensity based on transition probability
                # Lower transitions (to n=1,2) are generally stronger
                # Also, transitions with small Δn are generally stronger
                delta_n = n_upper - n_lower

                # Intensity model: stronger for lower n_lower and smaller delta_n
                # Add exponential decay for higher quantum numbers
                intensity = 1.0 / (delta_n * n_lower)
                intensity *= (1.0 / n_upper ** 0.5)  # Decay with upper level

                # Series-specific intensity factors
                # Lyman series (n→1) is strongest but mostly UV
                if n_lower == 1:
                    intensity *= 2.0
                # Balmer series (n→2) is strong and in visible range
                elif n_lower == 2:
                    intensity *= 1.5
                # Paschen series (n→3) weaker, mostly IR
                elif n_lower == 3:
                    intensity *= 0.8
                # Higher series progressively weaker
                else:
                    intensity *= 0.5

                lines.append((wavelength, intensity))

    # Normalize intensities
    if lines:
        max_intensity = max(i for _, i in lines)
        lines = [(wl, intensity / max_intensity) for wl, intensity in lines]
        # Sort by wavelength
        lines.sort(key=lambda x: x[0])

    # Cache result before returning
    _spectrum_cache[cache_key] = lines

    return lines


def draw_spectrum_bar(painter, rect, spectrum_lines, show_prominent_only=False):
    """
    Draw a spectrum bar showing emission lines.

    Args:
        painter: QPainter object
        rect: QRectF defining the bar area
        spectrum_lines: List of (wavelength_nm, intensity) tuples
        show_prominent_only: If True, only show lines with intensity > 0.3
    """
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QPen, QBrush

    if not spectrum_lines:
        return

    # Filter lines if showing prominent only
    if show_prominent_only:
        filtered_lines = [(wl, intensity) for wl, intensity in spectrum_lines if intensity > 0.3]
    else:
        filtered_lines = spectrum_lines

    if not filtered_lines:
        return

    # Find wavelength range
    min_wl = min(wl for wl, _ in filtered_lines)
    max_wl = max(wl for wl, _ in filtered_lines)
    wl_range = max_wl - min_wl
    if wl_range == 0:
        wl_range = 1

    # Draw each spectral line as a vertical bar
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)

    for wavelength, intensity in filtered_lines:
        # Position along the bar (0 to 1)
        t = (wavelength - min_wl) / wl_range

        # Get color for this wavelength
        color = wavelength_to_rgb(wavelength)

        # Adjust alpha based on intensity
        color.setAlpha(int(255 * intensity * 0.7))  # Max 70% opacity for background

        # Calculate bar position and width
        x = rect.left() + t * rect.width()
        width = max(2, rect.width() / 20)  # Line width, at least 2px

        # Draw the spectral line
        painter.setBrush(QBrush(color))
        line_rect = QRectF(x - width/2, rect.top(), width, rect.height())
        painter.drawRect(line_rect)

    painter.restore()


def wavelength_to_rgb(wavelength_nm, range_min=380, range_max=780, fade=0.0):
    """
    Convert wavelength to visible RGB color using rainbow spectrum.
    Small wavelengths lerp toward white, large wavelengths lerp toward black.

    Args:
        wavelength_nm: Wavelength value to map
        range_min: Minimum wavelength to map to violet (default 380nm)
        range_max: Maximum wavelength to map to red (default 780nm)
        fade: Fade towards transparent (0.0 = no fade, 1.0 = fully transparent)

    Returns:
        QColor representing the wavelength in the visible spectrum with alpha
    """
    # Map input wavelength to visible spectrum range (380-780nm)
    # This allows shifting the color mapping
    if range_min >= range_max:
        range_max = range_min + 1

    normalized = (wavelength_nm - range_min) / (range_max - range_min)
    w = 380 + normalized * (780 - 380)  # Map to visible spectrum

    # Clamp to visible range
    w = max(380, min(780, w))

    # Rainbow spectrum mapping (violet -> blue -> cyan -> green -> yellow -> orange -> red)
    if w < 380 or w > 780:
        return QColor(120, 120, 150)  # UV/IR gray-blue

    if 380 <= w < 440:  # Violet to Blue
        r, g, b = -(w - 440) / 60, 0.0, 1.0
    elif 440 <= w < 490:  # Blue to Cyan
        r, g, b = 0.0, (w - 440) / 50, 1.0
    elif 490 <= w < 510:  # Cyan to Green
        r, g, b = 0.0, 1.0, -(w - 510) / 20
    elif 510 <= w < 580:  # Green to Yellow
        r, g, b = (w - 510) / 70, 1.0, 0.0
    elif 580 <= w < 645:  # Yellow to Red
        r, g, b = 1.0, -(w - 645) / 65, 0.0
    else:  # Red
        r, g, b = 1.0, 0.0, 0.0

    # Edge intensity falloff for natural appearance
    if 380 <= w < 420:
        factor = 0.3 + 0.7 * (w - 380) / 40
    elif 645 < w <= 780:
        factor = 0.3 + 0.7 * (780 - w) / 135
    else:
        factor = 1.0

    # Apply factor
    r, g, b = r * factor, g * factor, b * factor

    # Lerp toward white for small wavelengths (normalized < 0.2)
    # Lerp toward black for large wavelengths (normalized > 0.8)
    if normalized < 0.2:
        # Lerp toward white (1.0, 1.0, 1.0)
        white_factor = 1.0 - (normalized / 0.2)  # 1.0 at min, 0.0 at 20%
        r = r * (1 - white_factor) + white_factor
        g = g * (1 - white_factor) + white_factor
        b = b * (1 - white_factor) + white_factor
    elif normalized > 0.8:
        # Lerp toward black (0.0, 0.0, 0.0)
        black_factor = (normalized - 0.8) / 0.2  # 0.0 at 80%, 1.0 at max
        r = r * (1 - black_factor)
        g = g * (1 - black_factor)
        b = b * (1 - black_factor)

    # Apply fade parameter to alpha channel
    # fade = 0.0: alpha = 255 (fully opaque)
    # fade = 1.0: alpha = 0 (fully transparent)
    alpha = int(255 * (1.0 - fade))

    return QColor(int(r * 255), int(g * 255), int(b * 255), alpha)


def get_ie_color(ie, fade=0.0):
    """Color gradient for ionization energy (cool to warm)"""
    normalized = (ie - 3.5) / (25.0 - 3.5)
    normalized = max(0, min(1, normalized))

    if normalized < 0.2:
        t = normalized / 0.2
        color = QColor(int(100 * (1-t) + 0 * t), int(100 * (1-t) + 200 * t), 255)
    elif normalized < 0.4:
        t = (normalized - 0.2) / 0.2
        color = QColor(0, int(200 * (1-t) + 255 * t), int(255 * (1-t) + 100 * t))
    elif normalized < 0.6:
        t = (normalized - 0.4) / 0.2
        color = QColor(int(0 * (1-t) + 255 * t), 255, int(100 * (1-t) + 50 * t))
    elif normalized < 0.8:
        t = (normalized - 0.6) / 0.2
        color = QColor(255, int(255 * (1-t) + 150 * t), int(50 * (1-t) + 0 * t))
    else:
        t = (normalized - 0.8) / 0.2
        color = QColor(255, int(150 * (1-t) + 50 * t), 0)

    color.setAlpha(int(255 * (1.0 - fade)))
    return color


def get_electroneg_color(electroneg, fade=0.0):
    """Color gradient for electronegativity"""
    if electroneg == 0:
        color = QColor(100, 100, 100)
    else:
        normalized = electroneg / 4.0
        color = QColor(int(100 + 155 * normalized), int(150 - 50 * normalized),
                     int(255 - 155 * normalized))
    color.setAlpha(int(255 * (1.0 - fade)))
    return color


def get_melting_color(melting, fade=0.0):
    """Color gradient for melting point"""
    normalized = min(melting / 4000.0, 1.0)

    if normalized < 0.33:
        t = normalized / 0.33
        color = QColor(int(100 + 55 * t), int(100 + 100 * t), 255)
    elif normalized < 0.67:
        t = (normalized - 0.33) / 0.34
        color = QColor(int(155 + 100 * t), int(200 - 50 * t), int(255 - 155 * t))
    else:
        t = (normalized - 0.67) / 0.33
        color = QColor(255, int(150 + 50 * t), int(100 - 100 * t))

    color.setAlpha(int(255 * (1.0 - fade)))
    return color


def get_radius_color(radius, fade=0.0):
    """Color gradient for atomic radius"""
    normalized = (radius - 30) / 320
    normalized = max(0, min(1, normalized))

    if normalized < 0.5:
        t = normalized / 0.5
        color = QColor(int(150 + 105 * t), int(100 + 100 * t), 255)
    else:
        t = (normalized - 0.5) / 0.5
        color = QColor(255, int(200 - 50 * t), int(255 - 155 * t))

    color.setAlpha(int(255 * (1.0 - fade)))
    return color


def get_density_color(density, fade=0.0):
    """Color gradient for density"""
    # Log scale for density (ranges from ~0.0001 to ~20)
    log_density = math.log10(max(density, 0.0001))
    normalized = (log_density + 4) / 5.3  # -4 to 1.3
    normalized = max(0, min(1, normalized))

    if normalized < 0.33:
        t = normalized / 0.33
        color = QColor(int(50 + 100 * t), int(50 + 150 * t), 255)
    elif normalized < 0.67:
        t = (normalized - 0.33) / 0.34
        color = QColor(int(150 + 105 * t), int(200 - 50 * t), int(255 - 100 * t))
    else:
        t = (normalized - 0.67) / 0.33
        color = QColor(255, int(150 + 50 * t), int(155 - 155 * t))

    color.setAlpha(int(255 * (1.0 - fade)))
    return color


def get_electron_affinity_color(affinity, fade=0.0):
    """Color gradient for electron affinity"""
    normalized = (affinity + 10) / 360
    normalized = max(0, min(1, normalized))

    if normalized < 0.5:
        t = normalized / 0.5
        color = QColor(int(100 + 100 * t), int(100 + 100 * t), 255)
    else:
        t = (normalized - 0.5) / 0.5
        color = QColor(int(200 + 55 * t), int(200 - 100 * t), int(255 - 155 * t))

    color.setAlpha(int(255 * (1.0 - fade)))
    return color


def get_boiling_color(boiling, fade=0.0):
    """Color gradient for boiling point"""
    normalized = min(boiling / 4000.0, 1.0)

    if normalized < 0.33:
        t = normalized / 0.33
        color = QColor(int(100 + 55 * t), int(150 + 50 * t), 255)
    elif normalized < 0.67:
        t = (normalized - 0.33) / 0.34
        color = QColor(int(155 + 100 * t), int(200 - 50 * t), int(255 - 155 * t))
    else:
        t = (normalized - 0.67) / 0.33
        color = QColor(255, int(150 + 50 * t), int(100 - 100 * t))

    color.setAlpha(int(255 * (1.0 - fade)))
    return color
