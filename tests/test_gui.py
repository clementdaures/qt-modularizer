"""Smoke tests for the companion GUI, run headless.
"""

# region Imports & Config

# python modules
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

# qt_modularizer/ui/..
from qt_modularizer.ui.form_loader import load_form
from qt_modularizer.ui.main_window import MainWindow
from qt_modularizer.ui.qt_compat import QtCore, QtGui, QtWidgets
from qt_modularizer.ui.theme import LIGHT, ThemeManager, build_stylesheet

# tests/..
from .test_parser import SAMPLE_UI

# endregion

# ==========

# region Fixtures

@pytest.fixture(scope="session")
def qapp() -> QtWidgets.QApplication:
    """Provides the shared QApplication.

    Returns:
        QtWidgets.QApplication: The application instance.
    """
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def ui_path(tmp_path: Path) -> Path:
    """Writes the sample form to a temporary folder.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        Path: Path of the ``.ui`` file.
    """
    path = tmp_path / "main.ui"
    path.write_text(SAMPLE_UI, encoding="utf-8")
    return path


@pytest.fixture
def window(qapp: QtWidgets.QApplication) -> MainWindow:
    """Provides a fresh main window.

    Args:
        qapp: The shared application.

    Returns:
        MainWindow: A window with nothing loaded.
    """
    win = MainWindow()
    yield win
    win._dirty = False
    win.close()

# endregion

# ==========

# region Tests

def test_open_file_fills_tree(window: MainWindow, ui_path: Path) -> None:
    assert window.open_file(ui_path)
    assert set(window._tree._items) == {
        "MainWindow", "centralwidget", "saveButton", "groupBox", "nameEdit",
    }


def test_open_invalid_file_is_refused(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.ui"
    bad.write_text("<html/>", encoding="utf-8")
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *a, **k: None)
    assert window.open_file(bad) is False


def test_selection_populates_role_and_preview(window: MainWindow, ui_path: Path) -> None:
    window.open_file(ui_path)
    window._tree.select("saveButton")

    assert window._roles._combo.isEnabled()
    items = [window._roles._combo.itemText(i) for i in range(window._roles._combo.count())]
    assert "primaryButton" in items
    assert "saveButton" in window._preview._xml.toPlainText()


def test_role_assignment_roundtrip(window: MainWindow, ui_path: Path, qapp) -> None:
    window.open_file(ui_path)
    window._tree.select("saveButton")
    window._on_role_changed("saveButton", "primaryButton")

    assert window._dirty
    assert window._parser.get_property("saveButton", "role") == "primaryButton"
    assert window.save_config()

    stored = json.loads((ui_path.parent / "ui_config.json").read_text(encoding="utf-8"))
    assert stored["roles"] == {"saveButton": "primaryButton"}

    other = MainWindow()
    other.open_file(ui_path)
    assert other._config.get_role("saveButton") == "primaryButton"
    assert other._parser.get_property("saveButton", "role") == "primaryButton"
    other.close()


def test_stored_role_without_widget_is_reported(
    window: MainWindow, ui_path: Path
) -> None:
    (ui_path.parent / "ui_config.json").write_text(
        json.dumps({"roles": {"ghost": "dangerButton"}}), encoding="utf-8"
    )
    window.open_file(ui_path)
    assert "without a matching widget" in window.statusBar().currentMessage()


def test_color_editing(window: MainWindow, ui_path: Path) -> None:
    window.open_file(ui_path)
    row = window._palettes._rows["light"]["accent"]

    row._edit.setText("#112233")
    row._on_edited()
    assert window._config.palettes["light"]["accent"] == "#112233"

    row._edit.setText("not a color")
    row._on_edited()
    assert window._config.palettes["light"]["accent"] == "#112233"
    assert row._edit.text() == "#112233"


def test_palette_reset(window: MainWindow, ui_path: Path) -> None:
    window.open_file(ui_path)
    window._palettes._rows["light"]["accent"]._commit("#112233")
    window._on_palette_reset("light")
    assert window._config.palettes["light"]["accent"] == "#5FA37F"


def test_export_does_not_touch_original(
    window: MainWindow, ui_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.open_file(ui_path)
    window._on_role_changed("saveButton", "primaryButton")
    target = tmp_path / "out.ui"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), "")
    )

    assert window.export_ui()
    assert "primaryButton" in target.read_text(encoding="utf-8")
    assert "primaryButton" not in ui_path.read_text(encoding="utf-8")


def test_generate_code(window: MainWindow, ui_path: Path, tmp_path: Path) -> None:
    window.open_file(ui_path)
    window._on_role_changed("saveButton", "primaryButton")
    out = tmp_path / "out" / "ui"

    assert window.generate_code(out)
    assert (out / "main_window.py").is_file()
    assert (out / "theme" / "colors.py").is_file()
    assert not window._dirty  # settings were saved first


def test_generate_requires_loaded_file(window: MainWindow, tmp_path: Path) -> None:
    assert window.generate_code(tmp_path / "ui") is False


def test_theme_toggle_restyles_the_companion(window: MainWindow, qapp) -> None:
    manager = ThemeManager.instance()
    window._toggle_theme()
    assert manager.is_dark
    assert all("#111110" in w.styleSheet() for w in window._themed)
    assert qapp.styleSheet() == ""  # never application-wide, see below
    window._toggle_theme()
    assert not manager.is_dark


# region Preview

FORM_UI = """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <layout class="QVBoxLayout" name="verticalLayout">
   <item>
    <widget class="QTabWidget" name="tabs">
     <widget class="QWidget" name="pageA">
      <attribute name="title"><string>A</string></attribute>
     </widget>
     <widget class="QWidget" name="pageB">
      <attribute name="title"><string>B</string></attribute>
     </widget>
    </widget>
   </item>
   <item><widget class="QCheckBox" name="check"/></item>
   <item><widget class="QLineEdit" name="edit"/></item>
   <item><widget class="QPushButton" name="button"/></item>
  </layout>
 </widget>
</ui>
"""


@pytest.fixture
def preview(window: MainWindow, tmp_path: Path):
    """Opens FORM_UI and returns the preview panel with both forms loaded.

    Args:
        window: Main window under test.
        tmp_path: Pytest temporary directory.

    Returns:
        PreviewPanel: The panel of ``window``.
    """
    path = tmp_path / "form.ui"
    path.write_text(FORM_UI, encoding="utf-8")
    assert window.open_file(path)
    return window._preview


def test_preview_loads_live_original_and_modified_form(
    window: MainWindow, ui_path: Path
) -> None:
    window.open_file(ui_path)
    original, modified = window._preview._original, window._preview._modified

    assert original.form is not None and not original.error
    assert modified.form is not None and not modified.error
    assert "saveButton" in original.widgets and "saveButton" in modified.widgets
    assert original.host.isVisibleTo(window._preview)


def test_preview_does_not_close_itself(window: MainWindow, ui_path: Path) -> None:
    window.open_file(ui_path)
    button = window._preview._original.widgets["saveButton"]

    button.click()  # wired to MainWindow.close() in the file

    assert not window._preview._original.form.isHidden()


def test_original_form_is_never_styled_by_the_companion(
    window: MainWindow, ui_path: Path, qapp
) -> None:
    window.open_file(ui_path)
    original = window._preview._original

    widget = original.host
    while widget is not None:
        assert widget.styleSheet() == ""
        widget = widget.parentWidget()
    assert qapp.styleSheet() == ""


def test_modified_form_carries_the_palette(window: MainWindow, ui_path: Path) -> None:
    window.open_file(ui_path)

    assert "#5FA37F" in window._preview._modified.host.styleSheet()  # light accent
    assert "#formHost" in window._preview._modified.host.styleSheet()
    window._on_palette_tab_changed("dark")
    assert "#5FA37F" not in window._preview._modified.host.styleSheet()


def test_role_change_updates_the_live_widget_in_place(
    window: MainWindow, ui_path: Path
) -> None:
    window.open_file(ui_path)
    original = window._preview._original.widgets["saveButton"]
    modified = window._preview._modified.widgets["saveButton"]
    window._preview._modified.widgets["nameEdit"].setText("typed")  # state to keep

    window._on_role_changed("saveButton", "primaryButton")

    assert modified.property("role") == "primaryButton"
    assert original.property("role") is None
    assert window._preview._modified.widgets["nameEdit"].text() == "typed"


def test_selection_is_outlined_in_both_forms(window: MainWindow, ui_path: Path) -> None:
    window.open_file(ui_path)
    window._tree.select("saveButton")

    assert len(window._preview._outlines) == 2
    for loaded, outline in window._preview._outlines:
        assert outline._target is loaded.widgets["saveButton"]
        assert not outline.isHidden()  # a child added to a shown host starts hidden
        assert outline.isVisibleTo(loaded.host)


def test_tab_switch_is_mirrored_both_ways(preview) -> None:
    original, modified = preview._original.widgets, preview._modified.widgets

    original["tabs"].setCurrentIndex(1)
    assert modified["tabs"].currentIndex() == 1

    modified["tabs"].setCurrentIndex(0)
    assert original["tabs"].currentIndex() == 0


def test_inputs_are_mirrored(preview) -> None:
    original, modified = preview._original.widgets, preview._modified.widgets

    original["check"].setChecked(True)
    modified["edit"].setText("hello")

    assert modified["check"].isChecked()
    assert original["edit"].text() == "hello"


def test_hover_and_press_are_mirrored(preview) -> None:
    original, modified = preview._original.widgets, preview._modified.widgets
    point = QtCore.QPointF(3, 3)

    enter = QtGui.QEnterEvent(point, point, point)
    QtCore.QCoreApplication.sendEvent(original["button"], enter)
    assert modified["button"].testAttribute(QtCore.Qt.WidgetAttribute.WA_UnderMouse)

    QtCore.QCoreApplication.sendEvent(original["button"], QtCore.QEvent(QtCore.QEvent.Type.Leave))
    assert not modified["button"].testAttribute(QtCore.Qt.WidgetAttribute.WA_UnderMouse)

    original["button"].pressed.emit()
    assert modified["button"].isDown()
    original["button"].released.emit()
    assert not modified["button"].isDown()


def test_push_button_without_role_looks_secondary() -> None:
    sheet = build_stylesheet(LIGHT)
    base = sheet.split("QPushButton {", 1)[1].split("}", 1)[0]
    secondary = sheet.split('QPushButton[role="secondaryButton"] {', 1)[1].split("}", 1)[0]

    for color in (LIGHT["surface"], LIGHT["border"]):
        assert color in base and color in secondary


def _pixel(widget: QtWidgets.QWidget, x: int, y: int) -> str:
    """Returns the color of one pixel of a widget as ``#RRGGBB``.

    Args:
        widget: Widget to render.
        x: Horizontal position.
        y: Vertical position.

    Returns:
        str: Upper-case hexadecimal color.
    """
    return QtGui.QColor(widget.grab().toImage().pixel(x, y)).name().upper()


def test_plain_container_does_not_hide_what_is_under_it(qapp: QtWidgets.QApplication) -> None:
    # Designer forms overlap layout widgets; an opaque one covered the line below it
    root = QtWidgets.QWidget()
    root.setStyleSheet(build_stylesheet(LIGHT))
    root.resize(100, 100)
    QtWidgets.QPushButton("x", root).setGeometry(0, 0, 100, 100)
    cover = QtWidgets.QWidget(root)
    cover.setGeometry(0, 0, 100, 100)
    cover.raise_()

    assert _pixel(root, 10, 50) == LIGHT["surface"].upper()  # the button, not the cover


def test_top_level_plain_widget_keeps_the_background(qapp: QtWidgets.QApplication) -> None:
    root = QtWidgets.QWidget()
    root.setStyleSheet(build_stylesheet(LIGHT))
    root.resize(50, 50)

    assert _pixel(root, 5, 5) == LIGHT["bg"].upper()


def test_companion_panels_stay_opaque(window: MainWindow) -> None:
    panel = window._themed[0]
    panel.resize(200, 200)

    assert _pixel(panel, 2, 2) == ThemeManager.instance().colors["bg"].upper()


def test_styled_push_button_fits_a_native_row(qapp: QtWidgets.QApplication) -> None:
    button = QtWidgets.QPushButton("Go")
    button.setStyleSheet(build_stylesheet(LIGHT))
    button.ensurePolished()

    # 8px of vertical padding made it ~34px and clipped rows of buttons in
    # forms whose containers have a fixed geometry
    assert button.sizeHint().height() <= 26


def test_styled_line_edit_fits_a_native_row(qapp: QtWidgets.QApplication) -> None:
    edit = QtWidgets.QLineEdit()
    edit.setStyleSheet(build_stylesheet(LIGHT))
    edit.ensurePolished()

    # 7px of vertical padding made it ~31px and clipped its text in tight rows
    assert edit.sizeHint().height() <= 28


def test_promoted_widget_falls_back_to_its_base_class(qapp: QtWidgets.QApplication) -> None:
    xml = SAMPLE_UI.replace(
        '<widget class="QLineEdit" name="nameEdit"/>',
        '<widget class="ColorSwatch" name="nameEdit"/>',
    ).replace(
        "</ui>",
        "<customwidgets><customwidget><class>ColorSwatch</class>"
        "<extends>QWidget</extends><header>widgets.h</header></customwidget>"
        "</customwidgets></ui>",
    )
    loaded = load_form(xml, custom_bases={"ColorSwatch": "QWidget"})
    assert not loaded.error
    assert "nameEdit" in loaded.widgets
    loaded.dispose()


def test_unloadable_form_reports_an_error(qapp: QtWidgets.QApplication) -> None:
    loaded = load_form("<ui/>")
    assert loaded.host is None
    assert loaded.error

# endregion

# endregion
