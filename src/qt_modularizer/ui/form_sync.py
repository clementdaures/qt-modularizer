"""Keeps two loaded copies of the same form in step.
"""

# region Imports & Config

# python modules
from collections.abc import Callable

# daeria
from daeria_log import get_logger

# qt_modularizer/ui/..
from .form_loader import LoadedForm
from .qt_compat import QtCore, QtGui, QtSignal, QtWidgets

log = get_logger(__name__)

# endregion

# ==========

# region FormSync

class FormSync(QtCore.QObject):
    """Mirrors what the user does in one form onto the other.

    Widgets are paired by object name. Two kinds of things are mirrored:

    * State: current tab, checked, selected item, text, value, scroll
      position and so on, through the widgets' own signals.
    * Look: hover and pressed visuals, through the events the widgets
      receive, so a button lights up in both forms at once.

    Signals:
        changed: Emitted after the state of a form changed.
    """

    changed = QtSignal()

    def __init__(
        self,
        first: LoadedForm,
        second: LoadedForm,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._busy = False
        self._twins: dict[QtWidgets.QWidget, QtWidgets.QWidget] = {}

        for name, one in first.widgets.items():
            other = second.widgets.get(name)
            if other is None:
                continue
            self._twins[one] = other
            self._twins[other] = one
            for widget in (one, other):
                widget.installEventFilter(self)
                self._wire(widget)

    def dispose(self) -> None:
        """Stops mirroring, before the forms are deleted."""
        self._twins.clear()

    # region State

    def _link(self, widget: QtWidgets.QWidget, signal, apply: Callable) -> None:
        """Calls ``apply`` on the twin whenever ``signal`` is emitted.

        Args:
            widget: Widget emitting the signal.
            signal: Signal of ``widget``.
            apply: Called as ``apply(widget, twin, *signal_args)``.
        """
        def handler(*args) -> None:
            if self._busy:
                return  # echo of a change we just made on the other side
            twin = self._twins.get(widget)
            if twin is None:
                return
            self._busy = True
            try:
                apply(widget, twin, *args)
            except RuntimeError:
                pass  # a widget is being deleted
            finally:
                self._busy = False
            self.changed.emit()

        signal.connect(handler)

    def _wire(self, w: QtWidgets.QWidget) -> None:
        """Connects every state worth mirroring on one widget.

        Args:
            w: Widget of either form.
        """
        W = QtWidgets
        link = self._link

        if isinstance(w, (W.QTabWidget, W.QStackedWidget, W.QToolBox)):
            link(w, w.currentChanged, lambda s, t, i: t.setCurrentIndex(i))
        if isinstance(w, W.QAbstractButton):
            link(w, w.toggled, lambda s, t, c: t.setChecked(c))
            link(w, w.pressed, lambda s, t: t.setDown(True))
            link(w, w.released, lambda s, t: t.setDown(False))
        if isinstance(w, W.QGroupBox):
            link(w, w.toggled, lambda s, t, c: t.setChecked(c))
        if isinstance(w, W.QComboBox):
            link(w, w.currentIndexChanged, lambda s, t, i: t.setCurrentIndex(i))
            link(w, w.editTextChanged, self._set_edit_text)
        if isinstance(w, W.QLineEdit):
            link(w, w.textChanged, self._set_line_text)
        if isinstance(w, W.QPlainTextEdit):
            link(w, w.textChanged, self._set_plain_text)
        if isinstance(w, W.QTextEdit):
            link(w, w.textChanged, self._set_html)
        if isinstance(w, (W.QSpinBox, W.QDoubleSpinBox, W.QAbstractSlider, W.QProgressBar)):
            link(w, w.valueChanged, lambda s, t, v: t.setValue(v))
        if isinstance(w, W.QListWidget):
            link(w, w.currentRowChanged, lambda s, t, r: t.setCurrentRow(r))
        if isinstance(w, W.QAbstractScrollArea):
            link(w, w.verticalScrollBar().valueChanged,
                 lambda s, t, v: t.verticalScrollBar().setValue(v))
            link(w, w.horizontalScrollBar().valueChanged,
                 lambda s, t, v: t.horizontalScrollBar().setValue(v))

    @staticmethod
    def _set_edit_text(source, twin, text: str) -> None:
        """Copies the text of an editable combo box."""
        if twin.currentText() != text:
            twin.setEditText(text)

    @staticmethod
    def _set_line_text(source, twin, text: str) -> None:
        """Copies the text of a line edit."""
        if twin.text() != text:
            twin.setText(text)

    @staticmethod
    def _set_plain_text(source, twin) -> None:
        """Copies the text of a plain text edit."""
        text = source.toPlainText()
        if twin.toPlainText() != text:
            twin.setPlainText(text)

    @staticmethod
    def _set_html(source, twin) -> None:
        """Copies the content of a rich text edit."""
        html = source.toHtml()
        if twin.toHtml() != html:
            twin.setHtml(html)

    # endregion

    # region Look

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Mirrors hover events onto the twin of the widget receiving them.

        Args:
            obj: Widget receiving the event.
            event: The event, always left to be handled normally.

        Returns:
            bool: Always ``False``.
        """
        if self._busy:
            return False
        twin = self._twins.get(obj)
        if twin is None:
            return False

        kind = event.type()
        Type = QtCore.QEvent.Type
        try:
            if kind == Type.Enter:
                self._set_under_mouse(twin, True)
            elif kind == Type.Leave:
                self._set_under_mouse(twin, False)
            elif kind in (Type.HoverEnter, Type.HoverMove, Type.HoverLeave):
                self._forward_hover(twin, event)
        except RuntimeError:
            pass  # a widget is being deleted
        except Exception:
            log.exception("Could not mirror an event")
        return False

    @staticmethod
    def _set_under_mouse(widget: QtWidgets.QWidget, under: bool) -> None:
        """Gives a widget the hovered (or not) look.

        Args:
            widget: Widget to update.
            under: Whether the mouse is over it.
        """
        widget.setAttribute(QtCore.Qt.WidgetAttribute.WA_UnderMouse, under)
        widget.update()

    def _forward_hover(self, twin: QtWidgets.QWidget, event: QtGui.QHoverEvent) -> None:
        """Sends the same hover event to the twin.

        This is what makes the tabs of a tab bar light up under the mouse.
        Both forms have the same geometry, so the position is unchanged.

        Args:
            twin: Widget receiving the copy.
            event: Hover event received by the other widget.
        """
        copy = QtGui.QHoverEvent(
            event.type(),
            event.position(),
            event.globalPosition(),
            event.oldPosF(),
            event.modifiers(),
        )
        self._busy = True
        try:
            QtCore.QCoreApplication.sendEvent(twin, copy)
        finally:
            self._busy = False

    # endregion

# endregion
