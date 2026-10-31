"""Unit tests for the command line interface.
"""

# region Imports & Config

# python modules
import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

# qt_modularizer/..
from qt_modularizer import cli

# tests/..
from .test_parser import SAMPLE_UI

# endregion

# ==========

# region Fixtures

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

# endregion

# ==========

# region Build Command

def test_build_generates_package(ui_path: Path, tmp_path: Path, capsys) -> None:
    out = tmp_path / "src" / "ui"
    code = cli.main(["build", "--ui", str(ui_path), "--output", str(out)])

    assert code == 0
    assert (out / "main_window.py").is_file()
    assert "Generated" in capsys.readouterr().out


def test_build_uses_settings_next_to_ui(ui_path: Path, tmp_path: Path) -> None:
    (tmp_path / "ui_config.json").write_text(
        json.dumps({"roles": {"saveButton": "dangerButton"}}), encoding="utf-8"
    )
    out = tmp_path / "ui"
    assert cli.main(["build", "--ui", str(ui_path), "--output", str(out)]) == 0
    assert 'u"dangerButton"' in (out / "ui_main_window.py").read_text(encoding="utf-8")


def test_build_with_explicit_config(ui_path: Path, tmp_path: Path) -> None:
    config = tmp_path / "other.json"
    config.write_text(json.dumps({"roles": {"saveButton": "primaryButton"}}), encoding="utf-8")
    out = tmp_path / "ui"
    args = ["build", "--ui", str(ui_path), "--output", str(out), "--config", str(config)]

    assert cli.main(args) == 0
    assert 'u"primaryButton"' in (out / "ui_main_window.py").read_text(encoding="utf-8")


def test_build_missing_ui_is_an_error(tmp_path: Path, capsys) -> None:
    code = cli.main(["build", "--ui", str(tmp_path / "no.ui"), "--output", str(tmp_path / "ui")])
    assert code == 2
    assert "error:" in capsys.readouterr().err


def test_build_invalid_config_is_an_error(ui_path: Path, tmp_path: Path) -> None:
    (tmp_path / "ui_config.json").write_text("{bad", encoding="utf-8")
    assert cli.main(["build", "--ui", str(ui_path), "--output", str(tmp_path / "ui")]) == 2


def test_warnings_fail_only_in_strict_mode(ui_path: Path, tmp_path: Path, capsys) -> None:
    (tmp_path / "ui_config.json").write_text(
        json.dumps({"roles": {"ghost": "dangerButton"}}), encoding="utf-8"
    )
    base = ["build", "--ui", str(ui_path), "--output", str(tmp_path / "ui")]

    assert cli.main(base) == 0
    assert "ghost" in capsys.readouterr().err
    assert cli.main(base + ["--strict"]) == 1


def test_missing_settings_file_is_a_warning(ui_path: Path, tmp_path: Path) -> None:
    base = ["build", "--ui", str(ui_path), "--output", str(tmp_path / "ui")]
    assert cli.main(base + ["--strict"]) == 1


def test_force_overwrites_owned_files(ui_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "ui"
    base = ["build", "--ui", str(ui_path), "--output", str(out)]
    cli.main(base)
    (out / "main.py").write_text("# mine\n", encoding="utf-8")

    cli.main(base)
    assert (out / "main.py").read_text(encoding="utf-8") == "# mine\n"
    cli.main(base + ["--force"])
    assert "def main" in (out / "main.py").read_text(encoding="utf-8")


def test_build_requires_ui_and_output(capsys) -> None:
    with pytest.raises(SystemExit) as info:
        cli.main(["build"])
    assert info.value.code == 2

# endregion

# ==========

# region Dispatch

def test_no_arguments_starts_gui(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []
    monkeypatch.setattr(cli, "run_gui", lambda args: calls.append(args) or 0)
    assert cli.main([]) == 0
    assert calls == [[]]


def test_ui_path_alone_opens_it_in_gui(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []
    monkeypatch.setattr(cli, "run_gui", lambda args: calls.append(args) or 0)
    cli.main(["form.ui"])
    assert calls == [["form.ui"]]


def test_gui_subcommand_forwards_file(monkeypatch: pytest.MonkeyPatch) -> None:
    import qt_modularizer.ui.main as gui

    seen: list = []
    monkeypatch.setattr(gui, "main", lambda argv: seen.append(argv) or 0)
    assert cli.main(["gui", "form.ui"]) == 0
    assert seen == [["qt_modularizer", "form.ui"]]

# endregion
