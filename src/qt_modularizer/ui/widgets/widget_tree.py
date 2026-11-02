"""Hierarchical view of the widgets found in a ``.ui`` file.
"""

# region Imports & Config

# qt_modularizer/core/..
from qt_modularizer.core.parser import WidgetInfo

# qt_modularizer/ui/..
from ..qt_compat import QtCore, QtSignal, QtWidgets

NAME_COLUMN = 0
CLASS_COLUMN = 1
ROLE_COLUMN = 2

# endregion

# ==========

# region WidgetTree

class WidgetTree(QtWidgets.QWidget):
    """Searchable tree listing widgets with their class and role.

    Attributes:
        widgetSelected: Emitted with the object name of the selected
            widget, or an empty string when the selection is cleared.
    """

    widgetSelected = QtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: dict[str, QtWidgets.QTreeWidgetItem] = {}

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Filter widgets...")
        self._search.setClearButtonEnabled(True)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels(["Name", "Class", "Role"])
        self._tree.setUniformRowHeights(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._search)
        layout.addWidget(self._tree)

        self._search.textChanged.connect(self._apply_filter)
        self._tree.currentItemChanged.connect(self._on_current_changed)

    # region Public API

    def set_tree(self, root: WidgetInfo | None, roles: dict[str, str]) -> None:
        """Fills the tree from a widget hierarchy.

        Args:
            root: Top-level widget, or ``None`` to empty the tree.
            roles: Role of each widget, by object name.
        """
        self._tree.blockSignals(True)
        self._tree.clear()
        self._items.clear()
        if root is not None:
            self._add_item(self._tree.invisibleRootItem(), root, roles)
            self._tree.expandAll()
        for column in (NAME_COLUMN, CLASS_COLUMN, ROLE_COLUMN):
            self._tree.resizeColumnToContents(column)
        self._tree.blockSignals(False)
        self._apply_filter(self._search.text())
        self.widgetSelected.emit("")

    def set_role(self, name: str, role: str) -> None:
        """Updates the role shown for a widget.

        Args:
            name: Object name of the widget.
            role: Role name, empty to clear.
        """
        item = self._items.get(name)
        if item is not None:
            item.setText(ROLE_COLUMN, role)
            self._tree.resizeColumnToContents(ROLE_COLUMN)

    def select(self, name: str) -> None:
        """Selects a widget by object name.

        Args:
            name: Object name of the widget.
        """
        item = self._items.get(name)
        if item is not None:
            self._tree.setCurrentItem(item)

    def current_name(self) -> str:
        """Returns the selected widget.

        Returns:
            str: Object name, or an empty string if nothing is selected.
        """
        item = self._tree.currentItem()
        return item.text(NAME_COLUMN) if item is not None else ""

    # endregion

    # region Internal Helpers

    def _add_item(
        self,
        parent_item: QtWidgets.QTreeWidgetItem,
        info: WidgetInfo,
        roles: dict[str, str],
    ) -> None:
        """Adds a widget and its descendants under an item.

        Args:
            parent_item: Item that receives the new widget.
            info: The widget to add.
            roles: Role of each widget, by object name.
        """
        item = QtWidgets.QTreeWidgetItem(
            [info.name, info.class_name, roles.get(info.name, "")]
        )
        parent_item.addChild(item)
        self._items[info.name] = item
        for child in info.children:
            self._add_item(item, child, roles)

    def _apply_filter(self, text: str) -> None:
        """Shows only the widgets matching the search text.

        Args:
            text: Text looked for in names, classes and roles.
        """
        needle = text.strip().lower()
        self._filter_item(self._tree.invisibleRootItem(), needle)

    def _filter_item(self, item: QtWidgets.QTreeWidgetItem, needle: str) -> bool:
        """Filters an item and its children.

        Args:
            item: Item to filter.
            needle: Lower-case search text, empty to show everything.

        Returns:
            bool: Whether the item or one of its descendants is visible.
        """
        visible_child = False
        for index in range(item.childCount()):
            if self._filter_item(item.child(index), needle):
                visible_child = True

        matches = not needle or any(
            needle in item.text(column).lower() for column in range(3)
        )
        visible = matches or visible_child
        if item is not self._tree.invisibleRootItem():
            item.setHidden(not visible)
        return visible

    def _on_current_changed(
        self,
        current: QtWidgets.QTreeWidgetItem | None,
        previous: QtWidgets.QTreeWidgetItem | None,
    ) -> None:
        """Forwards the selection change.

        Args:
            current: Newly selected item.
            previous: Previously selected item.
        """
        self.widgetSelected.emit(current.text(NAME_COLUMN) if current else "")

    # endregion

# endregion
