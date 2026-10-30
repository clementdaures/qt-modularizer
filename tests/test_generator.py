"""Unit tests for the code generation engine.
"""

# region Imports & Config

# python modules
import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

# qt_modularizer/core/..
from qt_modularizer.core.config import ProjectConfig
from qt_modularizer.core.generator import (
    CodeGenerator,
    GeneratorError,
    patch_uic_imports,
    render_colors,
    snake_name,
)
from qt_modularizer.core.parser import UIParser

# qt_modularizer/ui/theme/..
from qt_modularizer.ui.theme.colors import DARK, LIGHT

# tests/..
from .test_parser import SAMPLE_UI

pytest.importorskip("PySide6")

PROMOTED_UI = SAMPLE_UI.replace(
    '<widget class="QLineEdit" name="nameEdit"/>',
    '<widget class="FancyEdit" name="nameEdit"/>',
).replace(
    " <tabstops>",
    " <customwidgets>\n  <customwidget>\n   <class>FancyEdit</class>\n"
    "   <extends>QLineEdit</extends>\n   <header>fancy_edit.h</header>\n"
    "  </customwidget>\n </customwidgets>\n <tabstops>",
)

# endregion

# ==========

# region Fixtures

def make_generator(tmp_path: Path, xml: str = SAMPLE_UI) -> CodeGenerator:
    """Builds a generator for a form written in a temporary folder.

    Args:
        tmp_path: Pytest temporary directory.
        xml: Content of the form.

    Returns:
        CodeGenerator: A generator with one role assigned.
    """
    ui = tmp_path / "main.ui"
    ui.write_text(xml, encoding="utf-8")
    parser = UIParser()
    parser.load(ui)
    config = ProjectConfig.default(LIGHT, DARK)
    config.set_role("saveButton", "primaryButton")
    return CodeGenerator(parser, config)

# endregion

# ==========

# region Helpers

@pytest.mark.parametrize(
    ("name", "expected"),
    [("MainWindow", "main_window"), ("Form", "form"), ("HTTPClient", "http_client")],
)
def test_snake_name(name: str, expected: str) -> None:
    assert snake_name(name) == expected


def test_render_colors_is_valid_python_and_keeps_values() -> None:
    palettes = {"light": dict(LIGHT), "dark": dict(DARK)}
    palettes["light"]["accent"] = "#112233"
    namespace: dict = {}
    exec(render_colors(palettes), namespace)
    assert namespace["LIGHT"]["accent"] == "#112233"
    assert namespace["DARK"] == DARK


def test_patch_uic_imports() -> None:
    code = (
        "from PySide6.QtCore import (QSize)\n"
        "from fancy_edit import FancyEdit\n"
        "import res_rc\n"
    )
    patched, warnings = patch_uic_imports(code, ["FancyEdit"])
    assert "from Qt.QtCore import" in patched
    assert "from .widgets.custom_widgets import FancyEdit" in patched
    assert patched.index("qt_compat") < patched.index("from Qt.QtCore")
    assert "res_rc" in warnings[0]

# endregion

# ==========

# region Generation

def test_generate_creates_expected_files(tmp_path: Path) -> None:
    out = tmp_path / "src" / "ui"
    make_generator(tmp_path).generate(out)

    expected = [
        "__init__.py", "main.py", "main_window.py", "ui_main_window.py",
        "qt_compat.py", "vendor/Qt.py", "theme/__init__.py", "theme/colors.py",
        "theme/stylesheet.py", "theme/theme.py", "widgets/__init__.py",
        "widgets/custom_widgets.py",
    ]
    for name in expected:
        assert (out / name).is_file(), name
        if name.endswith(".py"):
            ast.parse((out / name).read_text(encoding="utf-8"))


def test_generated_form_carries_role_and_qt_py_imports(tmp_path: Path) -> None:
    out = tmp_path / "ui"
    make_generator(tmp_path).generate(out)
    form = (out / "ui_main_window.py").read_text(encoding="utf-8")

    assert "PySide6" not in form
    assert "from Qt.QtWidgets import" in form
    assert '"role", u"primaryButton"' in form


def test_user_owned_files_survive_regeneration(tmp_path: Path) -> None:
    out = tmp_path / "ui"
    generator = make_generator(tmp_path)
    generator.generate(out)
    (out / "main_window.py").write_text("# my code\n", encoding="utf-8")
    (out / "ui_main_window.py").write_text("# stale\n", encoding="utf-8")

    result = generator.generate(out)

    assert (out / "main_window.py").read_text(encoding="utf-8") == "# my code\n"
    assert out / "main_window.py" in result.kept
    assert "Ui_MainWindow" in (out / "ui_main_window.py").read_text(encoding="utf-8")

    generator.generate(out, force=True)
    assert "class MainWindow" in (out / "main_window.py").read_text(encoding="utf-8")


def test_promoted_widgets_get_stubs_once(tmp_path: Path) -> None:
    out = tmp_path / "ui"
    generator = make_generator(tmp_path, PROMOTED_UI)
    generator.generate(out)
    stubs = out / "widgets" / "custom_widgets.py"

    assert "class FancyEdit(QtWidgets.QLineEdit):" in stubs.read_text(encoding="utf-8")
    assert "from .widgets.custom_widgets import FancyEdit" in (
        out / "ui_main_window.py"
    ).read_text(encoding="utf-8")

    stubs.write_text(
        stubs.read_text(encoding="utf-8").replace('"""Promoted widget', '"""Mine'),
        encoding="utf-8",
    )
    generator.generate(out)
    text = stubs.read_text(encoding="utf-8")
    assert text.count("class FancyEdit") == 1
    assert '"""Mine' in text


def test_orphan_roles_become_warnings(tmp_path: Path) -> None:
    generator = make_generator(tmp_path)
    generator._config.set_role("ghost", "dangerButton")
    result = generator.generate(tmp_path / "ui")
    assert any("ghost" in w for w in result.warnings)


def test_invalid_palette_is_rejected(tmp_path: Path) -> None:
    generator = make_generator(tmp_path)
    del generator._config.palettes["dark"]["accent"]
    with pytest.raises(GeneratorError):
        generator.generate(tmp_path / "ui")


def test_invalid_package_name_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(GeneratorError):
        make_generator(tmp_path).generate(tmp_path / "my-ui")


def test_generated_package_runs(tmp_path: Path) -> None:
    out = tmp_path / "src" / "ui"
    make_generator(tmp_path, PROMOTED_UI).generate(out)
    script = (
        "from ui.main_window import MainWindow\n"
        "from ui.qt_compat import QtWidgets\n"
        "from ui.theme import ThemeManager, apply_stylesheet\n"
        "app = QtWidgets.QApplication([])\n"
        "apply_stylesheet(app)\n"
        "w = MainWindow()\n"
        "assert w.ui.saveButton.property('role') == 'primaryButton'\n"
        "w.toggle_theme()\n"
        "assert '#111110' in app.styleSheet()\n"
        "print('OK')\n"
    )
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    run = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path / "src",
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    assert "OK" in run.stdout


def test_templates_match_companion_theme() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "qt_modularizer"
    pairs = {
        "Qt.py": "ui/vendor/Qt.py",
        "qt_compat.py": "ui/qt_compat.py",
        "colors.py": "ui/theme/colors.py",
        "stylesheet.py": "ui/theme/stylesheet.py",
        "theme.py": "ui/theme/theme.py",
    }
    for template, companion in pairs.items():
        assert (root / "templates" / template).read_bytes() == (
            root / companion
        ).read_bytes(), template

# endregion
