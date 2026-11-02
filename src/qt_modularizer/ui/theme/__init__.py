"""Coral design system: palettes, stylesheet and theme manager.
"""

# region Imports & Config

# qt_modularizer/ui/theme/..
from .colors import DARK, LIGHT
from .stylesheet import apply_stylesheet, build_stylesheet
from .theme import ThemeManager

__all__ = [
    "DARK",
    "LIGHT",
    "ThemeManager",
    "apply_stylesheet",
    "build_stylesheet",
]

# endregion
