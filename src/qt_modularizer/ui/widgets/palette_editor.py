"""Editor of the Coral color palettes, with one tab per theme.
"""

# region Imports & Config

# qt_modularizer/core/..
from qt_modularizer.core.config import THEMES, ConfigError, normalize_hex

# qt_modularizer/ui/..
from ..qt_compat import QtCore, QtGui, QtSignal, QtWidgets

# endregion

# ==========

# region ColorRow

class ColorRow(QtWidgets.QWidget):
    """One palette entry: name, color swatch and hexadecimal field.

    Attributes:
        colorChanged: Emitted with the color name and its new value.
    """

    colorChanged = QtSignal(str, str)

    def __init__(
        self, key: str, value: str, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._key = key
        self._value = value

        label = QtWidgets.QLabel(key)
        label.setProperty("role", "muted")
        label.setMinimumWidth(100)

        self._swatch = QtWidgets.QPushButton()
        self._swatch.setFixedSize(28, 28)
        self._swatch.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        self._edit = QtWidgets.QLineEdit()
        self._edit.setMaxLength(7)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(label)
        layout.addWidget(self._swatch)
        layout.addWidget(self._edit, 1)

        self.set_color(value)
        self._swatch.clicked.connect(self._pick_color)
        self._edit.editingFinished.connect(self._on_edited)

    def set_color(self, value: str) -> None:
        """Displays a color without emitting ``colorChanged``.

        Args:
            value: Hexadecimal color, ``#RRGGBB``.
        """
        self._value = value
        self._edit.setText(value)
        self._swatch.setStyleSheet(
            f"background: {value}; border: 1px solid rgba(0, 0, 0, 40);"
            "border-radius: 6px; padding: 0px; min-height: 0px;"
        )

    def _pick_color(self) -> None:
        """Opens the color dialog and applies the chosen color."""
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self._value), self)
        if color.isValid():
            self._commit(color.name())

    def _on_edited(self) -> None:
        """Applies the typed color, or restores the last valid one."""
        try:
            self._commit(self._edit.text())
        except ConfigError:
            self._edit.setText(self._value)

    def _commit(self, text: str) -> None:
        """Validates a color and notifies listeners if it changed.

        Args:
            text: Candidate hexadecimal color.

        Raises:
            ConfigError: If the text is not a ``#RRGGBB`` color.
        """
        value = normalize_hex(text)
        self.set_color(value)
        self.colorChanged.emit(self._key, value)

# endregion

# ==========

# region PaletteEditor

class PaletteEditor(QtWidgets.QWidget):
    """Light and dark palette editor.

    Attributes:
        colorChanged: Emitted with the theme, color name and new value.
        resetRequested: Emitted with the theme whose reset was requested.
        themeChanged: Emitted with the theme of the tab the user opened.
    """

    colorChanged = QtSignal(str, str, str)
    resetRequested = QtSignal(str)
    themeChanged = QtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: dict[str, dict[str, ColorRow]] = {theme: {} for theme in THEMES}
        self._layouts: dict[str, QtWidgets.QVBoxLayout] = {}

        title = QtWidgets.QLabel("Color palette")
        title.setProperty("role", "sectionTitle")

        self._tabs = QtWidgets.QTabWidget()
        for theme in THEMES:
            self._tabs.addTab(self._build_tab(theme), theme.capitalize())

        self._reset = QtWidgets.QPushButton("Reset palette")
        self._reset.setProperty("role", "secondaryButton")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(self._tabs, 1)
        layout.addWidget(self._reset)

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._reset.clicked.connect(lambda: self.resetRequested.emit(self.current_theme()))

    def current_theme(self) -> str:
        """Returns the theme of the visible tab.

        Returns:
            str: ``"light"`` or ``"dark"``.
        """
        return THEMES[self._tabs.currentIndex()]

    def set_palettes(self, palettes: dict[str, dict[str, str]]) -> None:
        """Fills both tabs from the given palettes.

        Args:
            palettes: Colors by theme.
        """
        for theme in THEMES:
            self._fill_tab(theme, palettes[theme])

    def _build_tab(self, theme: str) -> QtWidgets.QWidget:
        """Builds the scrollable page of a theme.

        Args:
            theme: ``"light"`` or ``"dark"``.

        Returns:
            QtWidgets.QWidget: The tab page.
        """
        content = QtWidgets.QWidget()
        content.setProperty("role", "tabPage")
        inner = QtWidgets.QVBoxLayout(content)
        inner.setContentsMargins(10, 10, 10, 10)
        inner.setSpacing(6)
        inner.addStretch(1)
        self._layouts[theme] = inner

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidget(content)
        scroll.viewport().setProperty("role", "tabPage")
        return scroll

    def _fill_tab(self, theme: str, palette: dict[str, str]) -> None:
        """Updates the rows of a theme, creating them on first use.

        Args:
            theme: ``"light"`` or ``"dark"``.
            palette: Colors to display.
        """
        rows = self._rows[theme]
        for key, value in palette.items():
            row = rows.get(key)
            if row is None:
                row = ColorRow(key, value)
                row.colorChanged.connect(
                    lambda k, v, t=theme: self.colorChanged.emit(t, k, v)
                )
                rows[key] = row
                layout = self._layouts[theme]
                layout.insertWidget(layout.count() - 1, row)
            else:
                row.set_color(value)

    def _on_tab_changed(self, index: int) -> None:
        """Forwards the tab change.

        Args:
            index: Index of the new tab.
        """
        self.themeChanged.emit(THEMES[index])

# endregion
