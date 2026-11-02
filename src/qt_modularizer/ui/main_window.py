"""Main window of the QtModularizer companion.
"""

# region Imports & Config

# python modules
from pathlib import Path

# qt_modularizer/core/..
from qt_modularizer.core.config import ConfigError, ProjectConfig
from qt_modularizer.core.generator import CodeGenerator, GeneratorError
from qt_modularizer.core.parser import UIParser, UIParserError

# qt_modularizer/ui/..
from .qt_compat import QtCore, QtGui, QtWidgets
from .theme import DARK, LIGHT, ThemeManager, build_stylesheet
from .widgets import PaletteEditor, PreviewPanel, RolePanel, WidgetTree


APP_TITLE = "QtModularizer"

# endregion

# ==========

# region MainWindow

# The shared stylesheet keeps text inputs and push buttons compact so they fit the
# tight rows of forms laid out in Qt Designer. The companion's own widgets can
# afford more room, and its panels are plain containers that must stay opaque.
def companion_extra(colors: dict[str, str]) -> str:
    """Returns the rules that only apply to the companion's own panels.

    Args:
        colors: Palette of the companion's theme.

    Returns:
        str: Style sheet to append to the shared one.
    """
    return f"""
    .QWidget {{
        background: {colors["bg"]};
    }}

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        padding: 7px 10px;
    }}

    QPushButton {{
        padding: 8px 13px;
    }}
    """


class ColorPanel(QtWidgets.QWidget):
    """Panel whose background is painted rather than styled.

    It holds the preview, which contains the original form, so it cannot
    receive a style sheet. Painting avoids the palette too, since a palette
    would be inherited by the form.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QtGui.QColor()

    def set_color(self, color: QtGui.QColor) -> None:
        """Sets the background color.

        Args:
            color: New color.
        """
        self._color = color
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Fills the background.

        Args:
            event: The paint event.
        """
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._color)
        painter.end()


class MainWindow(QtWidgets.QMainWindow):
    """Three-panel companion: widget tree, preview, roles and palettes.

    The left panel lists the widgets of the loaded ``.ui`` file, the center
    panel previews the whole form (as designed, then with roles and theme
    applied) and the right panel assigns the role of the selected widget
    and edits the color palettes. Settings are saved in ``ui_config.json``
    next to the ``.ui`` file, so they are restored the next time the form
    is opened, even after it was edited in Qt Designer.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._parser = UIParser()
        self._config = ProjectConfig.default(LIGHT, DARK)
        self._config_path: Path | None = None
        self._dirty = False
        # Widgets carrying the companion's own theme. The theme is set on
        # each of them rather than on the application, because an
        # application style sheet would also restyle the original form of
        # the preview, which must keep the native look of Qt Designer.
        self._themed: list[QtWidgets.QWidget] = []

        self._tree = WidgetTree()
        self._preview = PreviewPanel()
        self._roles = RolePanel()
        self._palettes = PaletteEditor()

        self._build_ui()
        self._build_toolbar()
        self._connect_signals()

        self._restyle(ThemeManager.instance().colors)
        self._palettes.set_palettes(self._config.palettes)
        self._preview.set_palette(self._config.palettes["light"])
        self._preview.clear()
        self._update_title()
        self.statusBar().showMessage("Open a .ui file to get started.")

    # region UI Construction

    def _build_ui(self) -> None:
        """Lays out the three panels."""
        left = self._panel("Widgets", self._tree)
        self._center = self._panel("Preview", self._preview, ColorPanel)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(20)
        right_layout.addWidget(self._roles)
        right_layout.addWidget(self._palettes, 1)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self._themed += [left, right]
        for panel in (left, self._center, right):
            panel.setContentsMargins(12, 12, 12, 12)
            splitter.addWidget(panel)
        splitter.setSizes([380, 440, 360])
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)
        self.resize(1200, 760)

    @staticmethod
    def _panel(
        title: str,
        content: QtWidgets.QWidget,
        panel_class: type[QtWidgets.QWidget] = QtWidgets.QWidget,
    ) -> QtWidgets.QWidget:
        """Wraps a widget under a section title.

        Args:
            title: Section title.
            content: Widget shown below the title.
            panel_class: Class of the panel.

        Returns:
            QtWidgets.QWidget: The titled panel, its label in ``title_label``.
        """
        panel = panel_class()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        label = QtWidgets.QLabel(title)
        label.setProperty("role", "sectionTitle")
        layout.addWidget(label)
        layout.addWidget(content, 1)
        panel.title_label = label
        return panel

    def _build_toolbar(self) -> None:
        """Creates the toolbar and its shortcuts."""
        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        self._themed.append(toolbar)

        self._add_button(toolbar, "Open .ui", self.open_file, "Ctrl+O", "secondaryButton")
        self._add_button(toolbar, "Save config", self.save_config, "Ctrl+S", "primaryButton")
        self._add_button(toolbar, "Export .ui", self.export_ui, "Ctrl+Shift+S", "secondaryButton")
        self._add_button(toolbar, "Generate code", self.generate_code, "Ctrl+G", "secondaryButton")

        spacer = QtWidgets.QWidget()
        spacer.setObjectName("spacer")
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        toolbar.addWidget(spacer)

        self._theme_button = self._add_button(
            toolbar, "Dark mode", self._toggle_theme, "Ctrl+T", "secondaryButton"
        )

    def _add_button(
        self,
        toolbar: QtWidgets.QToolBar,
        text: str,
        slot,
        shortcut: str,
        role: str,
    ) -> QtWidgets.QPushButton:
        """Adds a button, and a window-wide shortcut, to the toolbar.

        Args:
            toolbar: Toolbar receiving the button.
            text: Button label.
            slot: Callable run when the button is clicked.
            shortcut: Key sequence triggering the same action.
            role: Semantic role of the button.

        Returns:
            QtWidgets.QPushButton: The created button.
        """
        button = QtWidgets.QPushButton(text)
        button.setProperty("role", role)
        button.clicked.connect(lambda _checked=False: slot())
        toolbar.addWidget(button)

        action = QtGui.QAction(text, self)
        action.setShortcut(QtGui.QKeySequence(shortcut))
        action.triggered.connect(lambda _checked=False: slot())
        self.addAction(action)
        return button

    def _connect_signals(self) -> None:
        """Wires the panels together."""
        self._tree.widgetSelected.connect(self._on_widget_selected)
        self._roles.roleChanged.connect(self._on_role_changed)
        self._palettes.colorChanged.connect(self._on_color_changed)
        self._palettes.resetRequested.connect(self._on_palette_reset)
        self._palettes.themeChanged.connect(self._on_palette_tab_changed)
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

    # endregion

    # region File Actions

    def open_file(self, path: str | Path | None = None) -> bool:
        """Loads a ``.ui`` file and the settings stored next to it.

        Args:
            path: File to open. A file dialog is shown when omitted.

        Returns:
            bool: Whether a file was loaded.
        """
        if not self._confirm_discard():
            return False
        if not path:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open .ui file", "", "Qt Designer files (*.ui)"
            )
            if not path:
                return False

        parser = UIParser()
        try:
            parser.load(path)
        except UIParserError as err:
            QtWidgets.QMessageBox.critical(self, APP_TITLE, str(err))
            return False

        config_path = ProjectConfig.path_for(path)
        try:
            config = ProjectConfig.load(config_path, LIGHT, DARK)
        except ConfigError as err:
            QtWidgets.QMessageBox.warning(
                self, APP_TITLE, f"{err}\n\nDefault settings will be used."
            )
            config = ProjectConfig.default(LIGHT, DARK)

        orphans = config.apply_to_parser(parser)
        self._parser, self._config, self._config_path = parser, config, config_path
        self._dirty = False

        self._preview.clear()
        self._tree.set_tree(parser.build_tree(), config.roles)
        self._palettes.set_palettes(config.palettes)
        self._on_palette_tab_changed(self._palettes.current_theme())
        self._preview.load_form(
            parser.source_text,
            parser.to_string(),
            working_dir=parser.path.parent if parser.path else None,
            custom_bases={c.class_name: c.extends for c in parser.custom_widgets()},
        )
        self._update_title()

        message = f"Loaded {Path(path).name}: {len(parser.list_widgets())} widgets"
        if orphans:
            message += f", {len(orphans)} stored role(s) without a matching widget"
        self.statusBar().showMessage(message)
        return True

    def save_config(self) -> bool:
        """Writes the roles and palettes to ``ui_config.json``.

        Returns:
            bool: Whether the file was written.
        """
        if self._config_path is None:
            self.statusBar().showMessage("Open a .ui file first.")
            return False
        try:
            self._config.save(self._config_path)
        except ConfigError as err:
            QtWidgets.QMessageBox.critical(self, APP_TITLE, str(err))
            return False
        self._dirty = False
        self._update_title()
        self.statusBar().showMessage(f"Saved {self._config_path}")
        return True

    def export_ui(self) -> bool:
        """Exports a copy of the form that contains the assigned roles.

        The original file is never modified.

        Returns:
            bool: Whether the file was written.
        """
        if not self._parser.is_loaded:
            self.statusBar().showMessage("Open a .ui file first.")
            return False
        source = self._parser.path
        suggestion = str(source.with_name(f"{source.stem}_themed.ui")) if source else ""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export .ui file", suggestion, "Qt Designer files (*.ui)"
        )
        if not path:
            return False
        if source and Path(path).resolve() == source.resolve():
            QtWidgets.QMessageBox.warning(
                self, APP_TITLE, "Choose a different file: the original is not overwritten."
            )
            return False
        try:
            self._parser.save(path)
        except UIParserError as err:
            QtWidgets.QMessageBox.critical(self, APP_TITLE, str(err))
            return False
        self.statusBar().showMessage(f"Exported {path}")
        return True

    def generate_code(self, output: str | Path | None = None) -> bool:
        """Generates the modular ``ui`` package of the loaded form.

        Settings are saved first, so the generated colors and roles match
        what is on screen. Files you already own (the window class,
        ``main.py``, ``widgets/``) are kept.

        Args:
            output: Folder of the package. A folder dialog is shown when
                omitted, and a ``ui`` package is created inside it.

        Returns:
            bool: Whether the code was generated.
        """
        if not self._parser.is_loaded or self._config_path is None:
            self.statusBar().showMessage("Open a .ui file first.")
            return False
        if output is None:
            folder = QtWidgets.QFileDialog.getExistingDirectory(
                self, "Generate into folder (a 'ui' package is created inside)"
            )
            if not folder:
                return False
            output = Path(folder) / "ui"
        if not self.save_config():
            return False

        try:
            result = CodeGenerator(self._parser, self._config).generate(output)
        except GeneratorError as err:
            QtWidgets.QMessageBox.critical(self, APP_TITLE, str(err))
            return False

        message = (
            f"Generated {len(result.written)} file(s) in {result.output}"
            f", kept {len(result.kept)} of yours"
        )
        self.statusBar().showMessage(message)
        if result.warnings:
            QtWidgets.QMessageBox.warning(
                self, APP_TITLE, "\n".join(f"- {w}" for w in result.warnings)
            )
        return True

    # endregion

    # region Slots

    def _on_widget_selected(self, name: str) -> None:
        """Shows the selected widget in the preview and role panels.

        Args:
            name: Object name of the widget, empty if none.
        """
        info = self._parser.get_widget(name) if name and self._parser.is_loaded else None
        if info is None:
            self._roles.set_widget(None, "")
            self._preview.clear_selection()
            return
        role = self._config.get_role(name)
        self._roles.set_widget(info, role)
        self._preview.show_widget(name, self._parser.widget_xml(name))

    def _on_role_changed(self, name: str, role: str) -> None:
        """Stores a role chosen by the user.

        Args:
            name: Object name of the widget.
            role: Chosen role, empty for none.
        """
        self._config.set_role(name, role)
        if role:
            self._parser.set_property(name, "role", role)
        else:
            self._parser.remove_property(name, "role")
        self._tree.set_role(name, role)
        self._preview.set_role(name, role)
        self._on_widget_selected(name)
        self._mark_dirty()

    def _on_color_changed(self, theme: str, key: str, value: str) -> None:
        """Stores a color edited by the user.

        Args:
            theme: ``"light"`` or ``"dark"``.
            key: Color name.
            value: New hexadecimal color.
        """
        self._config.set_color(theme, key, value)
        if theme == self._palettes.current_theme():
            self._preview.set_palette(self._config.palettes[theme])
        self._mark_dirty()

    def _on_palette_reset(self, theme: str) -> None:
        """Restores the default palette of a theme.

        Args:
            theme: ``"light"`` or ``"dark"``.
        """
        defaults = LIGHT if theme == "light" else DARK
        self._config.reset_palette(theme, defaults)
        self._palettes.set_palettes(self._config.palettes)
        self._preview.set_palette(self._config.palettes[theme])
        self._mark_dirty()

    def _on_palette_tab_changed(self, theme: str) -> None:
        """Previews the palette of the tab the user opened.

        Args:
            theme: ``"light"`` or ``"dark"``.
        """
        self._preview.set_palette(self._config.palettes[theme])

    def _toggle_theme(self) -> None:
        """Switches the companion between light and dark."""
        manager = ThemeManager.instance()
        manager.set_dark(not manager.is_dark)

    def _apply_theme(self, colors: dict) -> None:
        """Restyles the companion after a theme switch.

        Args:
            colors: Palette of the new theme.
        """
        self._restyle(colors)
        dark = ThemeManager.instance().is_dark
        self._theme_button.setText("Light mode" if dark else "Dark mode")

    def _restyle(self, colors: dict) -> None:
        """Applies the companion's theme to its own panels.

        The splitter, the center panel and the preview's containers are
        left unstyled on purpose: they are ancestors of the original form.

        Args:
            colors: Palette of the theme.
        """
        sheet = build_stylesheet(colors) + companion_extra(colors)
        for widget in (*self._themed, self.statusBar(), self._center.title_label):
            widget.setStyleSheet(sheet)
        self._center.set_color(QtGui.QColor(colors["bg"]))
        self._preview.set_theme(colors)

    # endregion

    # region Internal Helpers

    def _mark_dirty(self) -> None:
        """Flags unsaved changes."""
        self._dirty = True
        self._update_title()

    def _update_title(self) -> None:
        """Refreshes the window title."""
        name = self._parser.path.name if self._parser.path else "no file"
        self.setWindowTitle(f"{APP_TITLE} - {name}{' *' if self._dirty else ''}")

    def _confirm_discard(self) -> bool:
        """Asks what to do with unsaved changes.

        Returns:
            bool: ``True`` if it is safe to continue.
        """
        if not self._dirty:
            return True
        Button = QtWidgets.QMessageBox.StandardButton
        answer = QtWidgets.QMessageBox.question(
            self,
            APP_TITLE,
            "Save the changes to ui_config.json?",
            Button.Save | Button.Discard | Button.Cancel,
        )
        if answer == Button.Save:
            return self.save_config()
        return answer == Button.Discard

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Offers to save unsaved changes before closing.

        Args:
            event: The close event.
        """
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    # endregion

# endregion
