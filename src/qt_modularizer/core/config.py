"""Project configuration: semantic roles and palettes stored in ``ui_config.json``.
"""

# region Imports & Config

# python modules
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# daeria_log
from daeria_log import get_logger

# qt_modularizer/core/..
from .parser import UIParser, WidgetNotFoundError

log = get_logger(__name__)

CONFIG_FILENAME = "ui_config.json"
CONFIG_VERSION = 1
THEMES = ("light", "dark")

HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Semantic roles offered for each Qt class (cf. stylesheet).
ROLES_BY_CLASS: dict[str, tuple[str, ...]] = {
    "QPushButton": ("primaryButton", "secondaryButton", "dangerButton", "navButton"),
    "QToolButton": ("iconButton", "activityButton", "menuBarButton"),
    "QLabel": (
        "pageTitle",
        "pageSubtitle",
        "sectionTitle",
        "muted",
        "faint",
        "success",
        "warning",
        "error",
        "info",
    ),
    "QLineEdit": ("commandInput",),
    "QFrame": ("card", "panel"),
    "QGroupBox": ("panel",),
    "QWidget": ("panel",),
}

# endregion

# ==========

# region Exceptions

class ConfigError(Exception):
    """Raised when a configuration file or value is invalid."""

# endregion

# ==========

# region Helpers

def roles_for_class(class_name: str) -> tuple[str, ...]:
    """Lists the semantic roles available for a Qt class.

    Args:
        class_name: Qt class name, e.g. ``"QPushButton"``.

    Returns:
        tuple[str, ...]: Role names, empty if the class has none.
    """
    return ROLES_BY_CLASS.get(class_name, ())


def normalize_hex(value: str) -> str:
    """Validates and normalizes a hexadecimal color.

    Args:
        value: Color such as ``"#5fa37f"``.

    Returns:
        str: Upper-case color, e.g. ``"#5FA37F"``.

    Raises:
        ConfigError: If the value is not a ``#RRGGBB`` color.
    """
    value = value.strip()
    if not HEX_COLOR.match(value):
        raise ConfigError(f"'{value}' is not a valid #RRGGBB color.")
    return value.upper()

# endregion

# ==========

# region ProjectConfig

@dataclass
class ProjectConfig:
    """User settings kept next to a ``.ui`` file.

    Roles are keyed by object name, so they survive layout changes made in
    Qt Designer as long as the widgets keep their names.

    Attributes:
        roles: Semantic role of each widget, by object name.
        palettes: Color palettes by theme (``"light"`` and ``"dark"``).
        version: Format version of the file.
    """

    roles: dict[str, str] = field(default_factory=dict)
    palettes: dict[str, dict[str, str]] = field(default_factory=dict)
    version: int = CONFIG_VERSION

    # region Construction

    @classmethod
    def default(
        cls, light: dict[str, str], dark: dict[str, str]
    ) -> "ProjectConfig":
        """Creates a configuration holding the default palettes.

        Args:
            light: Default light palette.
            dark: Default dark palette.

        Returns:
            ProjectConfig: A configuration without roles.
        """
        return cls(palettes={"light": dict(light), "dark": dict(dark)})

    @classmethod
    def load(
        cls, path: str | Path, light: dict[str, str], dark: dict[str, str]
    ) -> "ProjectConfig":
        """Loads a configuration file, falling back to defaults.

        Missing palette keys are filled from the defaults, so files written
        by an older version keep working.

        Args:
            path: Path of the ``ui_config.json`` file.
            light: Default light palette.
            dark: Default dark palette.

        Returns:
            ProjectConfig: The loaded configuration, or the defaults if the
            file does not exist.

        Raises:
            ConfigError: If the file exists but cannot be read.
        """
        config = cls.default(light, dark)
        path = Path(path)
        if not path.exists():
            return config

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            raise ConfigError(f"Unable to read '{path}': {err}") from err
        if not isinstance(data, dict):
            raise ConfigError(f"'{path}' does not contain a JSON object.")

        roles = data.get("roles", {})
        if isinstance(roles, dict):
            config.roles = {str(k): str(v) for k, v in roles.items() if v}

        for theme in THEMES:
            stored = data.get("palettes", {}).get(theme, {})
            for key, value in stored.items():
                try:
                    config.palettes[theme][key] = normalize_hex(str(value))
                except ConfigError:
                    log.warning("Ignored invalid color %s", key, theme=theme)

        log.info("Loaded config %s", path, roles=len(config.roles))
        return config

    # endregion

    # region Persistence

    def save(self, path: str | Path) -> Path:
        """Writes the configuration as JSON.

        Args:
            path: Destination file.

        Returns:
            Path: The file that was written.

        Raises:
            ConfigError: If the file cannot be written.
        """
        path = Path(path)
        data = {
            "version": self.version,
            "roles": dict(sorted(self.roles.items())),
            "palettes": self.palettes,
        }
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as err:
            raise ConfigError(f"Unable to write '{path}': {err}") from err

        log.info("Saved config %s", path)
        return path

    @staticmethod
    def path_for(ui_path: str | Path) -> Path:
        """Gives the configuration path that goes with a ``.ui`` file.

        Args:
            ui_path: Path of the ``.ui`` file.

        Returns:
            Path: ``ui_config.json`` in the same folder.
        """
        return Path(ui_path).parent / CONFIG_FILENAME

    # endregion

    # region Editing

    def get_role(self, name: str) -> str:
        """Returns the role assigned to a widget.

        Args:
            name: Object name of the widget.

        Returns:
            str: The role, or an empty string if none is assigned.
        """
        return self.roles.get(name, "")

    def set_role(self, name: str, role: str) -> None:
        """Assigns or clears the role of a widget.

        Args:
            name: Object name of the widget.
            role: Role name, or an empty string to clear it.
        """
        if role:
            self.roles[name] = role
        else:
            self.roles.pop(name, None)

    def set_color(self, theme: str, key: str, value: str) -> str:
        """Sets one color of a palette.

        Args:
            theme: ``"light"`` or ``"dark"``.
            key: Color name, e.g. ``"accent"``.
            value: Hexadecimal color, ``#RRGGBB``.

        Returns:
            str: The normalized color that was stored.

        Raises:
            ConfigError: If the theme, key or color is invalid.
        """
        if theme not in THEMES:
            raise ConfigError(f"Unknown theme '{theme}'.")
        if key not in self.palettes[theme]:
            raise ConfigError(f"Unknown color '{key}'.")
        color = normalize_hex(value)
        self.palettes[theme][key] = color
        return color

    def reset_palette(
        self, theme: str, defaults: dict[str, str]
    ) -> None:
        """Restores a palette to its defaults.

        Args:
            theme: ``"light"`` or ``"dark"``.
            defaults: The default palette of that theme.

        Raises:
            ConfigError: If the theme is unknown.
        """
        if theme not in THEMES:
            raise ConfigError(f"Unknown theme '{theme}'.")
        self.palettes[theme] = dict(defaults)

    def apply_to_parser(self, parser: UIParser) -> list[str]:
        """Writes the stored roles into the loaded form.

        Args:
            parser: A parser with a ``.ui`` file loaded.

        Returns:
            list[str]: Names of the configured widgets that no longer
            exist in the form. Their roles are kept in the configuration
            in case the widgets come back.
        """
        orphans: list[str] = []
        for name, role in self.roles.items():
            try:
                parser.set_property(name, "role", role)
            except WidgetNotFoundError:
                orphans.append(name)
        return orphans

    # endregion

# endregion
