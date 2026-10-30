"""Renders a Qt Designer ``.ui`` form to an image, without showing a window.
"""

# region Imports & Config

# python modules
from dataclasses import dataclass, field

# qt_modularizer/ui/..
from .qt_compat import Qt, QtCore, QtGui, QtWidgets

# Outline drawn around the widget selected in the tree.
HIGHLIGHT_COLOR = "#E8603C"

# Forms smaller than this carry no usable size, so the size hint is used.
MIN_FORM_SIDE = 50

# endregion

# ==========

# region Data Models

@dataclass
class FormSnapshot:
    """Picture of a rendered form.

    Attributes:
        pixmap: The rendered form, ``None`` if it could not be loaded.
        rects: Visible widgets by object name, in pixmap coordinates.
        error: Why the form could not be rendered, empty on success.
    """

    pixmap: QtGui.QPixmap | None = None
    rects: dict[str, QtCore.QRect] = field(default_factory=dict)
    error: str = ""

    def with_highlight(self, name: str) -> QtGui.QPixmap | None:
        """Returns the picture with one widget outlined.

        Args:
            name: Object name of the widget to outline. Nothing is drawn
                when it is empty or not visible in the picture.

        Returns:
            QtGui.QPixmap | None: A copy of the picture, or ``None`` if
            there is no picture.
        """
        if self.pixmap is None:
            return None
        rect = self.rects.get(name)
        if rect is None:
            return self.pixmap

        result = QtGui.QPixmap(self.pixmap)
        painter = QtGui.QPainter(result)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        color = QtGui.QColor(HIGHLIGHT_COLOR)
        pen = QtGui.QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        color.setAlpha(40)
        painter.setBrush(color)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.end()
        return result

# endregion

# ==========

# region Loader

_loader_class: type | None = None


def _get_loader_class() -> type | None:
    """Builds, once, the ``QUiLoader`` subclass used to load forms.

    ``QUiLoader`` cannot create promoted widgets, because their class
    lives in the user's own code. The subclass creates their Qt base
    class instead, which is enough to draw the form.

    Returns:
        type | None: The loader class, ``None`` if QtUiTools is missing.
    """
    global _loader_class
    if _loader_class is not None:
        return _loader_class

    base = getattr(getattr(Qt, "_QtUiTools", None), "QUiLoader", None)
    if base is None:
        return None

    class FormLoader(base):
        """Loader that falls back to the base class of promoted widgets."""

        def __init__(self, bases: dict[str, str]) -> None:
            super().__init__()
            self._bases = bases

        def createWidget(self, class_name, parent=None, name=""):
            """Creates a widget, substituting promoted classes.

            Args:
                class_name: Class requested by the form.
                parent: Parent of the new widget.
                name: Object name of the new widget.

            Returns:
                The widget, or ``None`` if no class could be created.
            """
            widget = None
            if class_name in self._bases:
                widget = super().createWidget(self._bases[class_name], parent, name)
                if widget is None:
                    widget = super().createWidget("QWidget", parent, name)
            if widget is None:
                widget = super().createWidget(class_name, parent, name)
            return widget

    _loader_class = FormLoader
    return _loader_class

# endregion

# ==========

# region Rendering

def render_form(
    xml: str,
    working_dir: str | None = None,
    custom_bases: dict[str, str] | None = None,
    stylesheet: str = "",
    isolate: bool = False,
) -> FormSnapshot:
    """Renders a ``.ui`` document the way Qt Designer's preview does.

    The form is built from its real widgets, laid out at the size stored
    in the file, and captured offscreen. Nothing is shown on screen.

    Args:
        xml: Content of the ``.ui`` file.
        working_dir: Folder used to resolve relative resources such as
            icons, normally the folder of the ``.ui`` file.
        custom_bases: Qt base class of each promoted widget, by class
            name, e.g. ``{"ColorSwatch": "QWidget"}``.
        stylesheet: Style sheet applied to the form, empty for none.
        isolate: Render without the style sheet of the running
            application, so the form keeps the platform's native look
            instead of the companion's own theme. The application
            style sheet is restored before returning.

    Returns:
        FormSnapshot: The picture, or the reason it could not be made.
    """
    loader_class = _get_loader_class()
    if loader_class is None:
        return FormSnapshot(error="QtUiTools is not available in this Qt binding.")

    app = QtWidgets.QApplication.instance()
    saved_sheet = app.styleSheet() if app is not None else ""
    clear_app_sheet = bool(isolate and saved_sheet)

    if clear_app_sheet:
        app.setStyleSheet("")
    try:
        return _render(loader_class, xml, working_dir, custom_bases or {}, stylesheet)
    finally:
        if clear_app_sheet:
            app.setStyleSheet(saved_sheet)


def _render(
    loader_class: type,
    xml: str,
    working_dir: str | None,
    custom_bases: dict[str, str],
    stylesheet: str,
) -> FormSnapshot:
    """Loads the form into an offscreen host and captures it.

    Args:
        loader_class: Loader class from :func:`_get_loader_class`.
        xml: Content of the ``.ui`` file.
        working_dir: Folder used to resolve relative resources.
        custom_bases: Qt base class of each promoted widget.
        stylesheet: Style sheet applied to the form, empty for none.

    Returns:
        FormSnapshot: The picture, or the reason it could not be made.
    """
    host = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    if stylesheet:
        host.setStyleSheet(stylesheet)

    loader = loader_class(custom_bases)
    if working_dir:
        loader.setWorkingDirectory(QtCore.QDir(str(working_dir)))

    buffer = QtCore.QBuffer()
    buffer.setData(QtCore.QByteArray(xml.encode("utf-8")))
    buffer.open(QtCore.QIODevice.OpenModeFlag.ReadOnly)
    try:
        form = loader.load(buffer, host)
    except Exception as err:  # QUiLoader raises on some malformed forms
        form, load_error = None, str(err)
    else:
        load_error = loader.errorString()
    finally:
        buffer.close()

    try:
        if form is None:
            return FormSnapshot(error=load_error or "The form could not be loaded.")

        # The root is a child of the host: let it behave as a plain widget
        # instead of opening as a separate window (QMainWindow, QDialog).
        if form.isWindow():
            form.setWindowFlags(QtCore.Qt.WindowType.Widget)
            form.setVisible(True)  # setWindowFlags hides the widget
        for bar in form.findChildren(QtWidgets.QMenuBar):
            bar.setNativeMenuBar(False)  # a native bar would be left out

        size = form.size()
        if size.width() < MIN_FORM_SIDE or size.height() < MIN_FORM_SIDE:
            size = form.sizeHint()
        layout.addWidget(form)
        host.resize(size)

        pixmap = host.grab()
        if pixmap.isNull():
            return FormSnapshot(error="Rendering produced an empty image.")

        rects: dict[str, QtCore.QRect] = {}
        for widget in [form, *form.findChildren(QtWidgets.QWidget)]:
            name = widget.objectName()
            if name and name not in rects and widget.isVisibleTo(host):
                rects[name] = QtCore.QRect(
                    widget.mapTo(host, QtCore.QPoint(0, 0)), widget.size()
                )
        return FormSnapshot(pixmap=pixmap, rects=rects)
    finally:
        host.deleteLater()

# endregion
