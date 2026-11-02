"""Unit tests for the project configuration.
"""

# region Imports & Config

# python modules
import json
from pathlib import Path

import pytest

# qt_modularizer/core/..
from qt_modularizer.core.config import (
    ConfigError,
    ProjectConfig,
    normalize_hex,
    roles_for_class,
)
from qt_modularizer.core.parser import UIParser

# tests/..
from .test_parser import SAMPLE_UI

LIGHT = {"bg": "#FFFFFF", "accent": "#5FA37F"}
DARK = {"bg": "#000000", "accent": "#7FC49F"}

# endregion

# ==========

# region Helpers

def test_normalize_hex_uppercases() -> None:
    assert normalize_hex(" #5fa37f ") == "#5FA37F"


@pytest.mark.parametrize("value", ["", "5FA37F", "#FFF", "#GGGGGG", "#12345678"])
def test_normalize_hex_rejects_invalid(value: str) -> None:
    with pytest.raises(ConfigError):
        normalize_hex(value)


def test_roles_for_class() -> None:
    assert "primaryButton" in roles_for_class("QPushButton")
    assert roles_for_class("QCalendarWidget") == ()

# endregion

# ==========

# region Persistence

def test_load_missing_file_gives_defaults(tmp_path: Path) -> None:
    config = ProjectConfig.load(tmp_path / "ui_config.json", LIGHT, DARK)
    assert config.roles == {}
    assert config.palettes["light"] == LIGHT


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = ProjectConfig.path_for(tmp_path / "main.ui")
    config = ProjectConfig.default(LIGHT, DARK)
    config.set_role("saveButton", "primaryButton")
    config.set_color("dark", "accent", "#112233")
    config.save(path)

    loaded = ProjectConfig.load(path, LIGHT, DARK)
    assert path.name == "ui_config.json"
    assert loaded.get_role("saveButton") == "primaryButton"
    assert loaded.palettes["dark"]["accent"] == "#112233"
    assert loaded.palettes["light"] == LIGHT


def test_load_fills_missing_keys_and_ignores_bad_colors(tmp_path: Path) -> None:
    path = tmp_path / "ui_config.json"
    path.write_text(
        json.dumps({"palettes": {"light": {"accent": "oops", "bg": "#101010"}}}),
        encoding="utf-8",
    )
    config = ProjectConfig.load(path, LIGHT, DARK)
    assert config.palettes["light"] == {"bg": "#101010", "accent": "#5FA37F"}


def test_load_rejects_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "ui_config.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        ProjectConfig.load(path, LIGHT, DARK)

# endregion

# ==========

# region Editing

def test_set_role_empty_clears() -> None:
    config = ProjectConfig.default(LIGHT, DARK)
    config.set_role("a", "primaryButton")
    config.set_role("a", "")
    assert config.get_role("a") == ""


def test_set_color_validates() -> None:
    config = ProjectConfig.default(LIGHT, DARK)
    with pytest.raises(ConfigError):
        config.set_color("blue", "accent", "#123456")
    with pytest.raises(ConfigError):
        config.set_color("light", "nope", "#123456")
    with pytest.raises(ConfigError):
        config.set_color("light", "accent", "red")


def test_reset_palette() -> None:
    config = ProjectConfig.default(LIGHT, DARK)
    config.set_color("light", "accent", "#000000")
    config.reset_palette("light", LIGHT)
    assert config.palettes["light"] == LIGHT


def test_apply_to_parser_reports_orphans(tmp_path: Path) -> None:
    ui = tmp_path / "main.ui"
    ui.write_text(SAMPLE_UI, encoding="utf-8")
    parser = UIParser()
    parser.load(ui)

    config = ProjectConfig.default(LIGHT, DARK)
    config.set_role("saveButton", "primaryButton")
    config.set_role("deletedButton", "dangerButton")

    assert config.apply_to_parser(parser) == ["deletedButton"]
    assert parser.get_property("saveButton", "role") == "primaryButton"
    assert config.get_role("deletedButton") == "dangerButton"

# endregion
