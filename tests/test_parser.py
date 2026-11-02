"""Unit tests for the ``.ui`` XML parser.
"""

# region Imports & Config

# python modules
from pathlib import Path

import pytest

# qt_modularizer/core/..
from qt_modularizer.core.parser import (
    UIParser,
    UIParserError,
    WidgetNotFoundError,
    strip_root_connections,
)

SAMPLE_UI = """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <property name="windowTitle">
   <string>Demo</string>
  </property>
  <widget class="QWidget" name="centralwidget">
   <layout class="QVBoxLayout" name="verticalLayout">
    <item>
     <widget class="QPushButton" name="saveButton">
      <property name="text">
       <string>Save</string>
      </property>
     </widget>
    </item>
    <item>
     <!-- grouped inputs -->
     <widget class="QGroupBox" name="groupBox">
      <layout class="QHBoxLayout" name="horizontalLayout">
       <item>
        <widget class="QLineEdit" name="nameEdit"/>
       </item>
      </layout>
     </widget>
    </item>
   </layout>
  </widget>
 </widget>
 <tabstops>
  <tabstop>saveButton</tabstop>
  <tabstop>nameEdit</tabstop>
 </tabstops>
 <connections>
  <connection>
   <sender>saveButton</sender>
   <signal>clicked()</signal>
   <receiver>MainWindow</receiver>
   <slot>close()</slot>
  </connection>
 </connections>
</ui>
"""

# endregion

# ==========

# region Fixtures

@pytest.fixture
def ui_path(tmp_path: Path) -> Path:
    """Writes the sample form to a temporary file.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        Path: Path of the written ``.ui`` file.
    """
    path = tmp_path / "sample.ui"
    path.write_text(SAMPLE_UI, encoding="utf-8")
    return path


@pytest.fixture
def parser(ui_path: Path) -> UIParser:
    """Provides a parser with the sample form loaded.

    Args:
        ui_path: Path of the sample form.

    Returns:
        UIParser: A loaded parser.
    """
    instance = UIParser()
    instance.load(ui_path)
    return instance

# endregion

# ==========

# region Loading

def test_load_reports_form_class(parser: UIParser) -> None:
    assert parser.is_loaded
    assert parser.ui_class == "MainWindow"


def test_source_text_ignores_later_edits(parser: UIParser, ui_path: Path) -> None:
    parser.set_property("saveButton", "role", "primaryButton")

    assert parser.source_text == ui_path.read_bytes().decode("utf-8")
    assert "primaryButton" not in parser.source_text
    assert "primaryButton" in parser.to_string()


def test_strip_root_connections_keeps_the_rest() -> None:
    stripped = strip_root_connections(SAMPLE_UI)
    assert "close()" not in stripped
    assert "saveButton" in stripped

    elsewhere = SAMPLE_UI.replace(
        "<receiver>MainWindow</receiver>", "<receiver>nameEdit</receiver>"
    )
    assert strip_root_connections(elsewhere) == elsewhere
    assert strip_root_connections("<broken") == "<broken"


def test_load_rejects_non_designer_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.ui"
    bad.write_text("<html/>", encoding="utf-8")
    with pytest.raises(UIParserError):
        UIParser().load(bad)


def test_load_rejects_malformed_xml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.ui"
    bad.write_text("<ui><widget></ui>", encoding="utf-8")
    with pytest.raises(UIParserError):
        UIParser().load(bad)


def test_load_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(UIParserError):
        UIParser().load(tmp_path / "nope.ui")


def test_methods_require_loaded_file() -> None:
    with pytest.raises(UIParserError):
        UIParser().list_widgets()

# endregion

# ==========

# region Inspection

def test_list_widgets_in_document_order(parser: UIParser) -> None:
    widgets = [(w.class_name, w.name) for w in parser.list_widgets()]
    assert widgets == [
        ("QMainWindow", "MainWindow"),
        ("QWidget", "centralwidget"),
        ("QPushButton", "saveButton"),
        ("QGroupBox", "groupBox"),
        ("QLineEdit", "nameEdit"),
    ]


def test_tree_traverses_layouts(parser: UIParser) -> None:
    tree = parser.build_tree()
    assert tree is not None
    assert tree.parent is None
    assert parser.get_widget("saveButton").parent == "centralwidget"
    assert parser.get_widget("nameEdit").parent == "groupBox"
    central = parser.get_widget("centralwidget")
    assert [c.name for c in central.children] == ["saveButton", "groupBox"]


def test_get_widget_returns_none_when_missing(parser: UIParser) -> None:
    assert parser.get_widget("ghost") is None


def test_widget_xml_returns_widget_source(parser: UIParser) -> None:
    xml = parser.widget_xml("saveButton")
    assert xml.startswith('<widget class="QPushButton"')
    assert "Save" in xml

def test_custom_widgets_are_listed(tmp_path: Path) -> None:
    xml = SAMPLE_UI.replace(
        " <tabstops>",
        " <customwidgets>\n  <customwidget>\n   <class>FancyEdit</class>\n"
        "   <extends>QLineEdit</extends>\n   <header>fancy_edit.h</header>\n"
        "  </customwidget>\n </customwidgets>\n <tabstops>",
    )
    path = tmp_path / "custom.ui"
    path.write_text(xml, encoding="utf-8")
    parser = UIParser()
    parser.load(path)

    [widget] = parser.custom_widgets()
    assert (widget.class_name, widget.extends, widget.header) == (
        "FancyEdit", "QLineEdit", "fancy_edit.h",
    )


def test_no_custom_widgets_by_default(parser: UIParser) -> None:
    assert parser.custom_widgets() == []

# endregion

# ==========

# region Renaming

def test_rename_updates_references(parser: UIParser) -> None:
    parser.set_object_name("saveButton", "submitButton")
    xml = parser.to_string()

    assert parser.get_widget("saveButton") is None
    assert parser.get_widget("submitButton") is not None
    assert "<tabstop>submitButton</tabstop>" in xml
    assert "<sender>submitButton</sender>" in xml
    assert "saveButton" not in xml


def test_rename_to_same_name_is_noop(parser: UIParser) -> None:
    parser.set_object_name("saveButton", "saveButton")
    assert parser.get_widget("saveButton") is not None


def test_rename_rejects_duplicates(parser: UIParser) -> None:
    with pytest.raises(UIParserError):
        parser.set_object_name("saveButton", "nameEdit")


def test_rename_rejects_invalid_identifier(parser: UIParser) -> None:
    with pytest.raises(UIParserError):
        parser.set_object_name("saveButton", "not valid")


def test_rename_unknown_widget(parser: UIParser) -> None:
    with pytest.raises(WidgetNotFoundError):
        parser.set_object_name("ghost", "other")

# endregion

# ==========

# region Dynamic Properties

def test_set_property_adds_dynamic_property(parser: UIParser) -> None:
    parser.set_property("saveButton", "role", "primaryButton")

    assert parser.get_property("saveButton", "role") == "primaryButton"
    assert parser.get_widget("saveButton").properties == {"role": "primaryButton"}
    assert '<property name="role" stdset="0">' in parser.to_string()


def test_set_property_updates_without_duplicating(parser: UIParser) -> None:
    parser.set_property("saveButton", "role", "primaryButton")
    parser.set_property("saveButton", "role", "dangerButton")

    assert parser.get_property("saveButton", "role") == "dangerButton"
    assert parser.to_string().count('name="role"') == 1


def test_set_property_keeps_standard_properties_first(parser: UIParser) -> None:
    parser.set_property("saveButton", "role", "primaryButton")
    xml = parser.widget_xml("saveButton")
    assert xml.index('name="text"') < xml.index('name="role"')


@pytest.mark.parametrize(
    ("value", "value_type", "expected"),
    [
        (True, "bool", "true"),
        ("False", "bool", "false"),
        (3, "number", "3"),
        (1.5, "double", "1.5"),
    ],
)
def test_set_property_value_types(
    parser: UIParser, value: object, value_type: str, expected: str
) -> None:
    parser.set_property("saveButton", "flag", value, value_type)
    assert parser.get_property("saveButton", "flag") == expected


def test_set_property_rejects_bad_input(parser: UIParser) -> None:
    with pytest.raises(UIParserError):
        parser.set_property("saveButton", "bad name", "x")
    with pytest.raises(UIParserError):
        parser.set_property("saveButton", "role", "x", "color")
    with pytest.raises(UIParserError):
        parser.set_property("saveButton", "count", "abc", "number")


def test_standard_properties_are_not_dynamic(parser: UIParser) -> None:
    assert parser.get_property("saveButton", "text") is None


def test_remove_property(parser: UIParser) -> None:
    parser.set_property("saveButton", "role", "primaryButton")

    assert parser.remove_property("saveButton", "role") is True
    assert parser.remove_property("saveButton", "role") is False
    assert parser.get_property("saveButton", "role") is None

# endregion

# ==========

# region Saving

def test_save_overwrites_loaded_file(parser: UIParser, ui_path: Path) -> None:
    parser.set_property("saveButton", "role", "primaryButton")
    parser.save()

    reloaded = UIParser()
    reloaded.load(ui_path)
    assert reloaded.get_property("saveButton", "role") == "primaryButton"


def test_save_to_new_path_leaves_original_untouched(
    parser: UIParser, ui_path: Path, tmp_path: Path
) -> None:
    parser.set_property("saveButton", "role", "primaryButton")
    derived = parser.save(tmp_path / "derived.ui")

    assert derived.exists()
    assert "role" not in ui_path.read_text(encoding="utf-8")


def test_roundtrip_preserves_structure_and_comments(
    parser: UIParser, tmp_path: Path
) -> None:
    out = parser.save(tmp_path / "out.ui")
    text = out.read_text(encoding="utf-8")

    assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<!-- grouped inputs -->" in text

    reloaded = UIParser()
    reloaded.load(out)
    assert [w.name for w in reloaded.list_widgets()] == [
        w.name for w in parser.list_widgets()
    ]

# endregion
