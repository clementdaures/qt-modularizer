"""XML parsing and manipulation engine for Qt Designer ``.ui`` files.
"""

# region Imports & Config

# python modules
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# daeria_log
from daeria_log import get_logger

log = get_logger(__name__)

XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'

# Tags whose text holds a widget name and must follow a rename.
REFERENCE_TAGS = ("tabstop", "sender", "receiver", "zorder")

# Supported value types for dynamic properties.
VALUE_TYPES = ("string", "bool", "number", "double")

# Slots that would close or hide the form when wired to its top-level widget.
SHUTDOWN_SLOTS = frozenset({
    "close()", "hide()", "accept()", "reject()", "done(int)", "deleteLater()",
    "showMinimized()", "showMaximized()", "showFullScreen()",
})

# endregion

# ==========

# region Helpers

def strip_root_connections(xml: str) -> str:
    """Removes the connections that would close or hide the form itself.

    A preview shows the form inside another window, where a button wired
    to ``MainWindow.close()`` would make the preview disappear. Every other
    connection is kept, so the form keeps behaving like the real one.

    Args:
        xml: Content of a ``.ui`` file.

    Returns:
        str: The document without those connections, or ``xml`` itself when
        there is nothing to remove or it cannot be parsed.
    """
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError:
        return xml
    top = root.find("widget")
    connections = root.find("connections")
    if top is None or connections is None:
        return xml

    top_name = top.get("name", "")
    removed = False
    for connection in list(connections):
        receiver = (connection.findtext("receiver") or "").strip()
        slot = (connection.findtext("slot") or "").strip()
        if receiver == top_name and slot in SHUTDOWN_SLOTS:
            connections.remove(connection)
            removed = True
    if not removed:
        return xml
    return XML_DECLARATION + ET.tostring(root, encoding="unicode") + "\n"

# endregion

# ==========

# region Exceptions & Data Models

class UIParserError(Exception):
    """Raised when a ``.ui`` file cannot be loaded or manipulated."""


class WidgetNotFoundError(UIParserError):
    """Raised when no widget matches the requested object name."""


@dataclass
class WidgetInfo:
    """Read-only snapshot of a ``<widget>`` element.

    Attributes:
        class_name: Qt class of the widget, e.g. ``"QPushButton"``.
        name: Object name of the widget, e.g. ``"pushButton"``.
        parent: Object name of the parent widget, ``None`` for the root.
        properties: Dynamic properties (``stdset="0"``) as strings.
        children: Direct child widgets, layouts are traversed.
    """

    class_name: str
    name: str
    parent: str | None = None
    properties: dict[str, str] = field(default_factory=dict)
    children: list["WidgetInfo"] = field(default_factory=list)

    def walk(self) -> Iterator["WidgetInfo"]:
        """Iterates over this widget and all its descendants.

        Yields:
            WidgetInfo: The widget itself, then its descendants in
            document order.
        """
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass
class CustomWidgetInfo:
    """Promoted widget declared in the ``<customwidgets>`` section.

    Attributes:
        class_name: Class of the promoted widget, e.g. ``"ColorSwatch"``.
        extends: Qt base class it was promoted from.
        header: Header (module) declared for it in Qt Designer.
    """

    class_name: str
    extends: str
    header: str

# endregion

# ==========

# region UIParser

class UIParser:
    """Loads, inspects and edits a Qt Designer ``.ui`` file.

    Comments are preserved and the output follows Qt Designer's layout
    (one-space indentation) to keep version control diffs small.

    Example:
        >>> parser = UIParser()
        >>> parser.load("main.ui")
        >>> parser.set_property("saveButton", "role", "primaryButton")
        >>> parser.save("main_themed.ui")
    """

    def __init__(self) -> None:
        self._tree: ET.ElementTree | None = None
        self._path: Path | None = None
        self._source: str = ""

    # region Loading & Saving

    def load(self, path: str | Path) -> None:
        """Loads a ``.ui`` file, replacing any previously loaded one.

        Args:
            path: Path of the ``.ui`` file.

        Raises:
            UIParserError: If the file is unreadable, malformed or is not
                a Qt Designer file.
        """
        path = Path(path)
        try:
            builder = ET.TreeBuilder(insert_comments=True)
            tree = ET.parse(path, parser=ET.XMLParser(target=builder))
        except (OSError, ET.ParseError) as err:
            raise UIParserError(f"Unable to read '{path}': {err}") from err

        root = tree.getroot()
        if root.tag != "ui":
            raise UIParserError(
                f"'{path}' is not a Qt Designer file (root tag <{root.tag}>)."
            )

        self._tree = tree
        self._path = path
        self._source = path.read_bytes().decode("utf-8", errors="replace")
        log.info("Loaded ui file %s", path, widgets=len(self.list_widgets()))

    def save(self, path: str | Path | None = None) -> Path:
        """Writes the current tree to disk.

        Args:
            path: Destination file. When omitted, the loaded file is
                overwritten. Pass another path to export a derived file
                and leave the original untouched.

        Returns:
            Path: The file that was written.

        Raises:
            UIParserError: If nothing is loaded or the file is unwritable.
        """
        self._require_root()
        target = Path(path) if path is not None else self._path
        if target is None:
            raise UIParserError("No destination path available.")

        try:
            target.write_text(self.to_string(), encoding="utf-8")
        except OSError as err:
            raise UIParserError(f"Unable to write '{target}': {err}") from err

        log.info("Saved ui file %s", target)
        return target

    def to_string(self) -> str:
        """Serializes the current tree as Qt Designer formatted XML.

        Returns:
            str: The complete ``.ui`` document.

        Raises:
            UIParserError: If nothing is loaded.
        """
        root = self._require_root()
        ET.indent(root, space=" ")
        return XML_DECLARATION + ET.tostring(root, encoding="unicode") + "\n"

    # endregion

    # region Inspection

    @property
    def is_loaded(self) -> bool:
        """bool: Whether a ``.ui`` file is currently loaded."""
        return self._tree is not None

    @property
    def path(self) -> Path | None:
        """Path | None: Path of the loaded file."""
        return self._path

    @property
    def source_text(self) -> str:
        """str: The loaded file exactly as it was on disk.

        Unlike :meth:`to_string`, this ignores every later modification
        (roles, renames), so it is what Qt Designer would show.
        """
        return self._source

    @property
    def ui_class(self) -> str:
        """str: Name of the form class (the ``<class>`` tag)."""
        element = self._require_root().find("class")
        return (element.text or "").strip() if element is not None else ""

    def build_tree(self) -> WidgetInfo | None:
        """Builds the widget hierarchy.

        Returns:
            WidgetInfo | None: The top-level widget with its children
            populated, or ``None`` if the form has no widget.
        """
        top = self._require_root().find("widget")
        if top is None:
            return None
        return self._build_info(top, None)

    def list_widgets(self) -> list[WidgetInfo]:
        """Lists every widget in document order.

        Returns:
            list[WidgetInfo]: Flat list, parents before their children.
        """
        top = self.build_tree()
        return list(top.walk()) if top else []

    def custom_widgets(self) -> list[CustomWidgetInfo]:
        """Lists the promoted widgets declared by the form.

        Returns:
            list[CustomWidgetInfo]: One entry per ``<customwidget>``.
        """
        result: list[CustomWidgetInfo] = []
        for node in self._require_root().iter("customwidget"):
            result.append(
                CustomWidgetInfo(
                    class_name=(node.findtext("class") or "").strip(),
                    extends=(node.findtext("extends") or "QWidget").strip(),
                    header=(node.findtext("header") or "").strip(),
                )
            )
        return result

    def get_widget(self, name: str) -> WidgetInfo | None:
        """Finds a widget by object name.

        Args:
            name: Object name, e.g. ``"saveButton"``.

        Returns:
            WidgetInfo | None: The widget, or ``None`` if not found.
        """
        return next((w for w in self.list_widgets() if w.name == name), None)

    def widget_xml(self, name: str) -> str:
        """Returns the XML source of a single widget.

        Handy for a textual preview of the selected widget.

        Args:
            name: Object name of the widget.

        Returns:
            str: Indented XML of the ``<widget>`` element.

        Raises:
            WidgetNotFoundError: If no widget has this name.
        """
        element = self._get_element(name)
        ET.indent(element, space=" ")
        return ET.tostring(element, encoding="unicode")

    def get_property(self, name: str, prop: str) -> str | None:
        """Reads a dynamic property of a widget.

        Args:
            name: Object name of the widget.
            prop: Property name, e.g. ``"role"``.

        Returns:
            str | None: The value as a string, or ``None`` if unset.

        Raises:
            WidgetNotFoundError: If no widget has this name.
        """
        element = self._get_element(name)
        return self._read_dynamic_properties(element).get(prop)

    # endregion

    # region Modification

    def set_object_name(self, name: str, new_name: str) -> None:
        """Renames a widget and updates every reference to it.

        Tab stops, signal/slot connections and z-order entries are
        rewritten so the form stays consistent.

        Args:
            name: Current object name.
            new_name: New object name, must be a valid Python identifier.

        Raises:
            WidgetNotFoundError: If no widget has the current name.
            UIParserError: If the new name is invalid or already used.
        """
        element = self._get_element(name)
        if name == new_name:
            return
        if not new_name.isidentifier():
            raise UIParserError(f"'{new_name}' is not a valid object name.")
        if self._find_element(new_name) is not None:
            raise UIParserError(f"A widget named '{new_name}' already exists.")

        element.set("name", new_name)
        for tag in REFERENCE_TAGS:
            for ref in self._require_root().iter(tag):
                if (ref.text or "").strip() == name:
                    ref.text = new_name

        log.debug("Renamed widget %s", name, new_name=new_name)

    def set_property(
        self,
        name: str,
        prop: str,
        value: str | bool | int | float,
        value_type: str = "string",
    ) -> None:
        """Adds or updates a dynamic property on a widget.

        The property is written with ``stdset="0"``, exactly as Qt
        Designer does for properties added in its property editor.

        Args:
            name: Object name of the widget.
            prop: Property name, must be a valid identifier.
            value: Property value.
            value_type: One of ``"string"``, ``"bool"``, ``"number"``
                or ``"double"``.

        Raises:
            WidgetNotFoundError: If no widget has this name.
            UIParserError: If the property name, type or value is invalid.
        """
        if not prop.isidentifier():
            raise UIParserError(f"'{prop}' is not a valid property name.")
        text = self._format_value(value, value_type)
        element = self._get_element(name)

        node = self._find_dynamic_property(element, prop)
        if node is None:
            node = ET.Element("property", {"name": prop, "stdset": "0"})
            element.insert(self._property_insert_index(element), node)
        for child in list(node):
            node.remove(child)

        value_node = ET.SubElement(node, value_type)
        value_node.text = text
        if value_type == "string":
            value_node.set("notr", "true")

        log.debug("Set property %s.%s", name, prop, value=text)

    def remove_property(self, name: str, prop: str) -> bool:
        """Removes a dynamic property from a widget.

        Args:
            name: Object name of the widget.
            prop: Property name.

        Returns:
            bool: ``True`` if the property existed and was removed.

        Raises:
            WidgetNotFoundError: If no widget has this name.
        """
        element = self._get_element(name)
        node = self._find_dynamic_property(element, prop)
        if node is None:
            return False
        element.remove(node)
        log.debug("Removed property %s.%s", name, prop)
        return True

    # endregion

    # region Internal Helpers

    def _require_root(self) -> ET.Element:
        """Returns the root element of the loaded tree.

        Returns:
            ET.Element: The ``<ui>`` element.

        Raises:
            UIParserError: If nothing is loaded.
        """
        if self._tree is None:
            raise UIParserError("No .ui file loaded.")
        return self._tree.getroot()

    def _find_element(self, name: str) -> ET.Element | None:
        """Finds the ``<widget>`` element with the given object name.

        Args:
            name: Object name.

        Returns:
            ET.Element | None: The element, or ``None`` if not found.
        """
        for element in self._require_root().iter("widget"):
            if element.get("name") == name:
                return element
        return None

    def _get_element(self, name: str) -> ET.Element:
        """Finds a ``<widget>`` element or raises.

        Args:
            name: Object name.

        Returns:
            ET.Element: The matching element.

        Raises:
            WidgetNotFoundError: If no widget has this name.
        """
        element = self._find_element(name)
        if element is None:
            raise WidgetNotFoundError(f"No widget named '{name}'.")
        return element

    def _build_info(self, element: ET.Element, parent: str | None) -> WidgetInfo:
        """Builds the :class:`WidgetInfo` of an element and its children.

        Args:
            element: A ``<widget>`` element.
            parent: Object name of the parent widget.

        Returns:
            WidgetInfo: The populated snapshot.
        """
        info = WidgetInfo(
            class_name=element.get("class", ""),
            name=element.get("name", ""),
            parent=parent,
            properties=self._read_dynamic_properties(element),
        )
        for child in self._child_widgets(element):
            info.children.append(self._build_info(child, info.name))
        return info

    @staticmethod
    def _child_widgets(element: ET.Element) -> Iterator[ET.Element]:
        """Iterates over the direct child widgets of an element.

        Layouts and their ``<item>`` wrappers are traversed, but nested
        widgets are left to their own parent.

        Args:
            element: A ``<widget>`` or ``<layout>`` element.

        Yields:
            ET.Element: Each child ``<widget>`` element.
        """
        for child in element:
            if child.tag == "widget":
                yield child
            elif child.tag in ("layout", "item"):
                yield from UIParser._child_widgets(child)

    @staticmethod
    def _find_dynamic_property(
        element: ET.Element, prop: str
    ) -> ET.Element | None:
        """Finds a dynamic ``<property>`` node on a widget.

        Args:
            element: A ``<widget>`` element.
            prop: Property name.

        Returns:
            ET.Element | None: The node, or ``None`` if not found.
        """
        for node in element.findall("property"):
            if node.get("name") == prop and node.get("stdset") == "0":
                return node
        return None

    @staticmethod
    def _read_dynamic_properties(element: ET.Element) -> dict[str, str]:
        """Reads all dynamic properties of a widget.

        Args:
            element: A ``<widget>`` element.

        Returns:
            dict[str, str]: Property names mapped to their string value.
        """
        result: dict[str, str] = {}
        for node in element.findall("property"):
            if node.get("stdset") != "0" or len(node) == 0:
                continue
            result[node.get("name", "")] = (node[0].text or "").strip()
        return result

    @staticmethod
    def _property_insert_index(element: ET.Element) -> int:
        """Finds where a new ``<property>`` belongs in a widget.

        Args:
            element: A ``<widget>`` element.

        Returns:
            int: Index right after the last existing ``<property>``,
            or 0 if the widget has none.
        """
        indexes = [i for i, c in enumerate(element) if c.tag == "property"]
        return indexes[-1] + 1 if indexes else 0

    @staticmethod
    def _format_value(value: str | bool | int | float, value_type: str) -> str:
        """Converts a Python value to its ``.ui`` text form.

        Args:
            value: The value to convert.
            value_type: One of :data:`VALUE_TYPES`.

        Returns:
            str: Text to store in the value node.

        Raises:
            UIParserError: If the type is unknown or the value does not
                match it.
        """
        if value_type not in VALUE_TYPES:
            raise UIParserError(
                f"Unsupported value type '{value_type}', use one of {VALUE_TYPES}."
            )
        try:
            if value_type == "bool":
                if isinstance(value, str):
                    if value.lower() not in ("true", "false"):
                        raise ValueError(value)
                    return value.lower()
                return "true" if value else "false"
            if value_type == "number":
                return str(int(value))
            if value_type == "double":
                return str(float(value))
        except (TypeError, ValueError) as err:
            raise UIParserError(
                f"Value {value!r} is not a valid {value_type}."
            ) from err
        return str(value)

    # endregion

# endregion
