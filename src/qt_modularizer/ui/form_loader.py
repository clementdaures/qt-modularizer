"""Loads a Qt Designer ``.ui`` form as live widgets, ready to be embedded.
"""

# region Imports & Config

# python modules
from dataclasses import dataclass, field

# qt_modularizer/core/..
from ..core.parser import strip_root_connections

# qt_modularizer/ui/..
from .qt_compat import Qt, QtCore, QtWidgets

# Forms smaller than this carry no usable size, so the size hint is used.
MIN_FORM_SIDE = 50

# Object name of the container holding a form, so style sheets can target it.
HOST_NAME = "formHost"

# endregion

# ==========

# region Data Models

@dataclass
class LoadedForm:
    """A form loaded as live widgets.

    Attributes:
        host: Fixed-size container holding the form, ``None`` on failure.
        form: Top-level widget of the form, ``None`` on failure.
        widgets: Widgets of the form by object name, root included.
        error: Why the form could not be loaded, empty on success.
    """

    host: QtWidgets.QWidget | None = None
    form: QtWidgets.QWidget | None = None
    widgets: dict[str, QtWidgets.QWidget] = field(default_factory=dict)
    error: str = ""

    def dispose(self) -> None:
        """Releases the widgets."""
        self.widgets.clear()
        if self.host is not None:
            self.host.hide()
            self.host.setParent(None)
            self.host.deleteLater()
        self.host = self.form = None

# endregion

# ==========

# region Loader

_loader_class: type | None = None


def _get_loader_class() -> type | None:
    """Builds, once, the ``QUiLoader`` subclass used to load forms.

    ``QUiLoader`` cannot create promoted widgets, because their class
    lives in the user's own code. The subclass creates their Qt base
    class instead, which is enough to show the form.

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

# region Loading

def load_form(
    xml: str,
    working_dir: str | None = None,
    custom_bases: dict[str, str] | None = None,
    stylesheet: str = "",
) -> LoadedForm:
    """Loads a ``.ui`` document into live, interactive widgets.

    Nothing is shown: the caller places ``LoadedForm.host`` in a layout.
    The form keeps the size stored in the file.

    Args:
        xml: Content of the ``.ui`` file.
        working_dir: Folder used to resolve relative resources such as
            icons, normally the folder of the ``.ui`` file.
        custom_bases: Qt base class of each promoted widget, by class
            name, e.g. ``{"ColorSwatch": "QWidget"}``.
        stylesheet: Style sheet applied to the host and so to the whole
            form. Without one the form keeps the platform's native look.

    Returns:
        LoadedForm: The widgets, or the reason they could not be created.
    """
    loader_class = _get_loader_class()
    if loader_class is None:
        return LoadedForm(error="QtUiTools is not available in this Qt binding.")

    host = QtWidgets.QWidget()
    host.setObjectName(HOST_NAME)
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    if stylesheet:
        host.setStyleSheet(stylesheet)
    else:
        host.setAutoFillBackground(True)  # native window color

    loader = loader_class(custom_bases or {})
    if working_dir:
        loader.setWorkingDirectory(QtCore.QDir(str(working_dir)))

    buffer = QtCore.QBuffer()
    buffer.setData(QtCore.QByteArray(strip_root_connections(xml).encode("utf-8")))
    buffer.open(QtCore.QIODevice.OpenModeFlag.ReadOnly)
    try:
        form = loader.load(buffer, host)
    except Exception as err:  # QUiLoader raises on some malformed forms
        form, load_error = None, str(err)
    else:
        load_error = loader.errorString()
    finally:
        buffer.close()

    if form is None:
        host.deleteLater()
        return LoadedForm(error=load_error or "The form could not be loaded.")

    # The root is a child of the host: let it behave as a plain widget
    # instead of opening as a separate window (QMainWindow, QDialog).
    if form.isWindow():
        form.setWindowFlags(QtCore.Qt.WindowType.Widget)
        form.setVisible(True)  # setWindowFlags hides the widget
    if not stylesheet:
        form.setAutoFillBackground(True)
    for bar in form.findChildren(QtWidgets.QMenuBar):
        bar.setNativeMenuBar(False)  # a native bar would leave the form

    size = form.size()
    if size.width() < MIN_FORM_SIDE or size.height() < MIN_FORM_SIDE:
        size = form.sizeHint()
    size = size.expandedTo(form.minimumSize()).expandedTo(form.minimumSizeHint())
    layout.addWidget(form)
    host.setFixedSize(size)

    widgets: dict[str, QtWidgets.QWidget] = {}
    for widget in [form, *form.findChildren(QtWidgets.QWidget)]:
        name = widget.objectName()
        if name and not name.startswith("qt_") and name not in widgets:
            widgets[name] = widget
    return LoadedForm(host=host, form=form, widgets=widgets)

# endregion
