"""Interactive preview of the loaded form, as designed and with the theme.
"""

# region Imports & Config

# python modules
from pathlib import Path

# qt_modularizer/ui/..
from ..form_loader import HOST_NAME, LoadedForm, load_form
from ..form_sync import FormSync
from ..qt_compat import QtCore, QtGui, QtWidgets

# qt_modularizer/ui/theme/..
from ..theme.stylesheet import build_stylesheet

# Outline drawn around the widget selected in the tree.
HIGHLIGHT_COLOR = "#E8603C"

ALIGN_TOP_LEFT = QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop

# endregion

# ==========

# region Helper Widgets

class _Canvas(QtWidgets.QWidget):
    """Background of the form tab, painted instead of styled.

    It is an ancestor of the original form, so it must not receive a
    style sheet or a palette: both would leak into that form and spoil its
    native look.
    """

    def __init__(self) -> None:
        super().__init__()
        self._color = QtGui.QColor("#FAFAF9")

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


class _Outline(QtWidgets.QWidget):
    """Transparent layer on top of a form, outlining one of its widgets.

    Mouse events go through it, so the form stays fully interactive.
    """

    def __init__(self, host: QtWidgets.QWidget) -> None:
        super().__init__(host)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(host.rect())
        self._target: QtWidgets.QWidget | None = None
        self.raise_()
        self.show()  # created under a visible host, so it is hidden until shown

    def set_target(self, widget: QtWidgets.QWidget | None) -> None:
        """Sets the outlined widget.

        Args:
            widget: Widget of the form, ``None`` for no outline.
        """
        self._target = widget
        self.raise_()
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Draws the outline, unless the widget is hidden (other tab).

        Args:
            event: The paint event.
        """
        host = self.parentWidget()
        target = self._target
        if target is None or not target.isVisibleTo(host):
            return
        rect = QtCore.QRect(target.mapTo(host, QtCore.QPoint(0, 0)), target.size())

        painter = QtGui.QPainter(self)
        color = QtGui.QColor(HIGHLIGHT_COLOR)
        pen = QtGui.QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        color.setAlpha(40)
        painter.setBrush(color)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.end()

# endregion

# ==========

# region PreviewPanel

class PreviewPanel(QtWidgets.QWidget):
    """Tabs showing the live form and the XML of the selected widget.

    The *Form* tab stacks two copies of the same ``.ui``: the form exactly
    as saved (what Qt Designer shows), then the same form with the
    assigned roles and the Coral stylesheet applied. Both are fully
    interactive and mirror each other: switching a tab, ticking a box or
    hovering a button in one does the same in the other. The widget
    selected in the tree is outlined in both.

    The panel and everything between it and the original form carry no
    style sheet (see :meth:`set_theme`), otherwise the companion's theme
    would also restyle the original.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._colors: dict[str, str] | None = None
        self._working_dir: Path | None = None
        self._custom_bases: dict[str, str] = {}
        self._selected = ""
        self._original: LoadedForm | None = None
        self._modified: LoadedForm | None = None
        self._sync: FormSync | None = None
        self._outlines: list[tuple[LoadedForm, _Outline]] = []

        self._tabs = QtWidgets.QTabBar()
        self._tabs.addTab("Form")
        self._tabs.addTab("XML")
        self._tabs.setExpanding(False)
        self._stack = QtWidgets.QStackedWidget()

        self._canvas = _Canvas()
        self._original_msg = self._make_message()
        self._modified_msg = self._make_message()
        self._original_box = QtWidgets.QVBoxLayout()
        self._modified_box = QtWidgets.QVBoxLayout()
        self._original_box.addWidget(self._original_msg)
        self._modified_box.addWidget(self._modified_msg)

        self._captions = [
            self._make_caption("Original, as in Qt Designer"),
            self._make_caption("With roles and theme"),
        ]
        layout = QtWidgets.QVBoxLayout(self._canvas)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.addWidget(self._captions[0])
        layout.addLayout(self._original_box)
        layout.addSpacing(20)
        layout.addWidget(self._captions[1])
        layout.addLayout(self._modified_box)
        layout.addStretch(1)

        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._scroll.setWidget(self._canvas)

        self._xml = QtWidgets.QPlainTextEdit()
        self._xml.setReadOnly(True)
        self._xml.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont))

        self._stack.addWidget(self._scroll)
        self._stack.addWidget(self._xml)
        self._tabs.currentChanged.connect(self._stack.setCurrentIndex)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._tabs)
        outer.addWidget(self._stack, 1)

        self._show_empty()

    # region Construction Helpers

    @staticmethod
    def _make_caption(text: str) -> QtWidgets.QLabel:
        """Creates the caption shown above a form.

        Args:
            text: Caption text.

        Returns:
            QtWidgets.QLabel: The label, themed by :meth:`set_theme`.
        """
        label = QtWidgets.QLabel(text)
        label.setProperty("role", "muted")
        return label

    @staticmethod
    def _make_message() -> QtWidgets.QLabel:
        """Creates the label shown where there is no form.

        Returns:
            QtWidgets.QLabel: The label, themed by :meth:`set_theme`.
        """
        label = QtWidgets.QLabel()
        label.setWordWrap(True)
        return label

    # endregion

    # region Public API

    def set_theme(self, colors: dict[str, str]) -> None:
        """Themes the panel's own chrome: tabs, captions, XML, scrollbars.

        The style sheet is set on each of these widgets, never on the panel
        or its containers, so that it cannot reach the original form.

        Args:
            colors: Palette of the companion app itself.
        """
        sheet = build_stylesheet(colors)
        chrome = [
            self._tabs, self._xml, self._original_msg, self._modified_msg,
            self._scroll.verticalScrollBar(), self._scroll.horizontalScrollBar(),
            *self._captions,
        ]
        for widget in chrome:
            widget.setStyleSheet(sheet)
        self._canvas.set_color(QtGui.QColor(colors["bg"]))

    def set_palette(self, colors: dict[str, str]) -> None:
        """Sets the palette applied to the modified form.

        Args:
            colors: Color palette, e.g. the light or dark one.
        """
        self._colors = colors
        if self._modified is not None and self._modified.host is not None:
            self._modified.host.setStyleSheet(self._modified_sheet())

    def load_form(
        self,
        original_xml: str,
        modified_xml: str,
        working_dir: str | Path | None = None,
        custom_bases: dict[str, str] | None = None,
    ) -> None:
        """Loads a form twice: as saved, and with roles and theme.

        Args:
            original_xml: The ``.ui`` file exactly as it is on disk.
            modified_xml: The same form with the roles added.
            working_dir: Folder used to resolve relative resources.
            custom_bases: Qt base class of each promoted widget.
        """
        self._dispose_forms()
        self._working_dir = Path(working_dir) if working_dir else None
        self._custom_bases = dict(custom_bases or {})

        self._original = load_form(original_xml, self._working_dir, self._custom_bases)
        sheet = self._modified_sheet()
        self._modified = load_form(
            modified_xml, self._working_dir, self._custom_bases, stylesheet=sheet
        )
        self._place(self._original_box, self._original_msg, self._original)
        self._place(self._modified_box, self._modified_msg, self._modified)

        if self._original.form is not None and self._modified.form is not None:
            self._sync = FormSync(self._original, self._modified)
            self._sync.changed.connect(self._schedule_outline_refresh)
        self._refresh_outlines()

    def set_role(self, name: str, role: str) -> None:
        """Applies a role to a widget of the modified form, in place.

        The form is not reloaded, so the tab, text and other state the user
        set up in the preview is kept.

        Args:
            name: Object name of the widget.
            role: Role to apply, empty to remove it.
        """
        if self._modified is None:
            return
        widget = self._modified.widgets.get(name)
        if widget is None:
            return
        widget.setProperty("role", role)
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        # A role can change the size of a widget (bold text, padding): tell
        # the layout it sits in, so that its neighbours adapt.
        widget.updateGeometry()
        widget.update()

    def show_widget(self, name: str, xml: str) -> None:
        """Outlines a widget in both forms and shows its XML.

        Args:
            name: Object name of the widget.
            xml: Source of the widget element.
        """
        self._selected = name
        self._xml.setPlainText(xml)
        self._refresh_outlines()

    def clear_selection(self) -> None:
        """Removes the outline and empties the XML tab."""
        self.show_widget("", "")

    def clear(self) -> None:
        """Forgets the form and the selection."""
        self._dispose_forms()
        self._selected = ""
        self._xml.clear()
        self._show_empty()

    # endregion

    # region Internal Helpers

    def _modified_sheet(self) -> str:
        """Builds the style sheet of the modified form.

        The host is a plain container, which the theme makes transparent, so
        it gets the palette's background explicitly (the form may be a plain
        widget that is only transparent here because it is not a window).

        Returns:
            str: The style sheet, empty while no palette is set.
        """
        if not self._colors:
            return ""
        host_rule = f'QWidget#{HOST_NAME} {{ background: {self._colors["bg"]}; }}'
        return build_stylesheet(self._colors) + host_rule

    def _dispose_forms(self) -> None:
        """Deletes the loaded forms and everything attached to them."""
        if self._sync is not None:
            self._sync.dispose()
            self._sync.deleteLater()
            self._sync = None
        self._outlines.clear()
        for loaded in (self._original, self._modified):
            if loaded is not None:
                loaded.dispose()
        self._original = self._modified = None

    def _show_empty(self) -> None:
        """Shows the hint displayed while no form is loaded."""
        for message in (self._original_msg, self._modified_msg):
            message.setText("Open a .ui file to preview it.")
            message.show()

    def _place(
        self,
        box: QtWidgets.QVBoxLayout,
        message: QtWidgets.QLabel,
        loaded: LoadedForm,
    ) -> None:
        """Puts a loaded form in its slot, or the reason it failed.

        Args:
            box: Layout of the slot.
            message: Label shown when there is no form.
            loaded: The loaded form.
        """
        if loaded.host is None:
            message.setText(f"The form could not be loaded: {loaded.error}")
            message.show()
            return
        message.hide()
        box.addWidget(loaded.host, 0, ALIGN_TOP_LEFT)
        loaded.host.show()
        self._outlines.append((loaded, _Outline(loaded.host)))

    def _schedule_outline_refresh(self) -> None:
        """Refreshes the outlines once Qt finished the current change."""
        QtCore.QTimer.singleShot(0, self._refresh_outlines)

    def _refresh_outlines(self) -> None:
        """Points each outline at the selected widget of its form."""
        for loaded, outline in self._outlines:
            outline.set_target(loaded.widgets.get(self._selected))

    # endregion

# endregion
