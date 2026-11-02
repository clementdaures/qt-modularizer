"""Theme state management for the Coral design system.
"""

# region Imports & Config

# qt_modularizer/ui/..
from ..qt_compat import QtCore, QtSignal

# qt_modularizer/ui/theme/..
from .colors import DARK, LIGHT

# endregion

# ==========

# region ThemeManager

class ThemeManager(QtCore.QObject):
    """Holds the currently active Coral color theme.

    Widgets that need to react to a theme switch (e.g. to re-tint icons)
    should connect to ``themeChanged``.

    Attributes:
        themeChanged: Emitted with the new color palette when the theme
            switches.
    """

    themeChanged = QtSignal(dict)

    _instance: "ThemeManager | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._dark = False

    @classmethod
    def instance(cls) -> "ThemeManager":
        """Returns the shared ThemeManager instance.

        Returns:
            ThemeManager: The singleton, created on first access.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def colors(self) -> dict[str, str]:
        """dict[str, str]: The active color palette (LIGHT or DARK)."""
        return DARK if self._dark else LIGHT

    @property
    def is_dark(self) -> bool:
        """bool: Whether the dark theme is currently active."""
        return self._dark

    def set_dark(self, dark: bool) -> None:
        """Sets the active theme and notifies listeners if it changed.

        Args:
            dark: ``True`` to activate the dark theme, ``False`` for light.
        """
        dark = bool(dark)
        if dark == self._dark:
            return
        self._dark = dark
        self.themeChanged.emit(self.colors)

# endregion
