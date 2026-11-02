"""Panel assigning a semantic role to the selected widget.
"""

# region Imports & Config

# qt_modularizer/core/..
from qt_modularizer.core.config import roles_for_class
from qt_modularizer.core.parser import WidgetInfo

# qt_modularizer/ui/..
from ..qt_compat import QtSignal, QtWidgets

NO_ROLE_LABEL = "(none)"

# endregion

# ==========

# region RolePanel

class RolePanel(QtWidgets.QWidget):
    """Dropdown of the semantic roles available for the selected widget.

    Attributes:
        roleChanged: Emitted with the object name and the new role
            (empty string for no role) when the user picks a role.
    """

    roleChanged = QtSignal(str, str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = ""

        title = QtWidgets.QLabel("Semantic role")
        title.setProperty("role", "sectionTitle")

        self._summary = QtWidgets.QLabel("No widget selected")
        self._summary.setProperty("role", "muted")

        self._combo = QtWidgets.QComboBox()
        self._combo.setEnabled(False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(self._summary)
        layout.addWidget(self._combo)

        self._combo.activated.connect(self._on_activated)

    def set_widget(self, info: WidgetInfo | None, role: str) -> None:
        """Shows the roles available for a widget.

        Args:
            info: The selected widget, or ``None`` if nothing is selected.
            role: Role currently assigned to it, empty for none.
        """
        self._combo.clear()
        self._name = info.name if info else ""

        if info is None:
            self._summary.setText("No widget selected")
            self._combo.setEnabled(False)
            return

        self._summary.setText(f"{info.name}  ·  {info.class_name}")
        roles = list(roles_for_class(info.class_name))
        if role and role not in roles:
            roles.append(role)

        self._combo.addItem(NO_ROLE_LABEL, "")
        for entry in roles:
            self._combo.addItem(entry, entry)
        self._combo.setCurrentIndex(max(0, self._combo.findData(role)))
        self._combo.setEnabled(bool(roles))

    def _on_activated(self, index: int) -> None:
        """Emits the role picked by the user.

        Args:
            index: Index of the chosen entry.
        """
        if self._name:
            self.roleChanged.emit(self._name, self._combo.itemData(index) or "")

# endregion
