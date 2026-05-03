"""
Color utility functions for Kivy Canvas rendering.
All functions return RGBA tuples in 0-1 range.
"""

import math


def hex_to_rgba(hex_color, alpha=1.0):
    """Convert hex color string to RGBA tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return (r, g, b, alpha)


def rgb_to_rgba(r, g, b, a=255):
    """Convert RGB 0-255 to RGBA 0-1 tuple."""
    return (r / 255, g / 255, b / 255, a / 255)


def lerp_color(color_a, color_b, t):
    """Linearly interpolate between two RGBA colors."""
    t = max(0.0, min(1.0, t))
    return tuple(a + (b - a) * t for a, b in zip(color_a, color_b))


def value_to_gradient_color(value, min_val, max_val, start_color, end_color):
    """Map a numeric value to a color along a gradient."""
    if max_val == min_val:
        return start_color
    t = (value - min_val) / (max_val - min_val)
    t = max(0.0, min(1.0, t))
    return lerp_color(start_color, end_color, t)


def get_property_color(item, property_name, min_val=None, max_val=None,
                       start_color=(0.2, 0.2, 0.8, 1.0),
                       end_color=(0.8, 0.2, 0.2, 1.0)):
    """
    Get a color for an item based on a property value.
    Handles both numeric (gradient) and categorical (hash-based) properties.
    """
    value = item.get(property_name)
    if value is None:
        return (0.5, 0.5, 0.5, 1.0)

    if isinstance(value, (int, float)):
        if min_val is None:
            min_val = 0
        if max_val is None:
            max_val = 1
        return value_to_gradient_color(value, min_val, max_val, start_color, end_color)

    # Categorical value: use hash for consistent color
    return categorical_color(str(value))


def categorical_color(category_str):
    """Generate a consistent color from a string category."""
    h = hash(category_str)
    r = ((h & 0xFF0000) >> 16) / 255
    g = ((h & 0x00FF00) >> 8) / 255
    b = (h & 0x0000FF) / 255
    # Ensure colors are vibrant enough
    max_c = max(r, g, b)
    if max_c < 0.3:
        r, g, b = r + 0.3, g + 0.3, b + 0.3
    return (r, g, b, 1.0)


def wavelength_to_rgba(wavelength_nm):
    """Convert visible light wavelength (380-780nm) to RGBA color."""
    if wavelength_nm < 380 or wavelength_nm > 780:
        return (0.5, 0.5, 0.5, 1.0)

    if wavelength_nm < 440:
        r = -(wavelength_nm - 440) / (440 - 380)
        g = 0.0
        b = 1.0
    elif wavelength_nm < 490:
        r = 0.0
        g = (wavelength_nm - 440) / (490 - 440)
        b = 1.0
    elif wavelength_nm < 510:
        r = 0.0
        g = 1.0
        b = -(wavelength_nm - 510) / (510 - 490)
    elif wavelength_nm < 580:
        r = (wavelength_nm - 510) / (580 - 510)
        g = 1.0
        b = 0.0
    elif wavelength_nm < 645:
        r = 1.0
        g = -(wavelength_nm - 645) / (645 - 580)
        b = 0.0
    else:
        r = 1.0
        g = 0.0
        b = 0.0

    # Intensity falloff at edges
    if wavelength_nm < 420:
        factor = 0.3 + 0.7 * (wavelength_nm - 380) / (420 - 380)
    elif wavelength_nm > 700:
        factor = 0.3 + 0.7 * (780 - wavelength_nm) / (780 - 700)
    else:
        factor = 1.0

    return (r * factor, g * factor, b * factor, 1.0)
