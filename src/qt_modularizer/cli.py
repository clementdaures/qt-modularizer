"""Command line interface: code generation for build scripts and CI, and GUI launcher.
"""

# region Imports & Config

# python modules
import sys
from pathlib import Path
from typing import Annotated, Optional

# typer
import typer

# daeria_log
import daeria_log

# qt_modularizer/..
from qt_modularizer.core.config import ConfigError, ProjectConfig
from qt_modularizer.core.generator import CodeGenerator, GeneratorError
from qt_modularizer.core.parser import UIParser, UIParserError
from qt_modularizer.templates.colors import DARK, LIGHT

EXIT_OK = 0
EXIT_WARNINGS = 1
EXIT_ERROR = 2

PROG_NAME = "python -m qt_modularizer"

app = typer.Typer(
    help="Companion tool for Qt Designer. Without a command, "
    "the GUI starts (optionally with a .ui file to open).",
    add_completion=False,
    no_args_is_help=True,
)

# endregion

# ==========

# region Commands

def run_build(
    ui: str,
    output: str,
    config: str | None,
    force: bool,
    strict: bool,
    verbose: bool,
) -> int:
    """Generates the ``ui`` package of a form.

    Args:
        ui: Path of the .ui file.
        output: Folder of the generated package.
        config: Settings file, or ``None`` for the default one.
        force: Also overwrite the files owned by the user.
        strict: Return ``1`` if warnings were raised.
        verbose: List files and show logs.

    Returns:
        int: ``0`` on success, ``1`` if warnings were raised with
        ``strict``, ``2`` on error.
    """
    daeria_log.ensure_setup(
        app="cli",
        product="qt_modularizer",
        console=verbose,
        capture_hooks=False,
    )

    ui_path = Path(ui)
    config_path = Path(config) if config else ProjectConfig.path_for(ui_path)

    parser = UIParser()
    try:
        parser.load(ui_path)
        project_config = ProjectConfig.load(config_path, LIGHT, DARK)
        result = CodeGenerator(parser, project_config).generate(output, force=force)
    except (UIParserError, ConfigError, GeneratorError) as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_ERROR

    if not config_path.exists():
        result.warnings.append(
            f"No settings file at '{config_path}': default roles and palettes used."
        )

    print(
        f"Generated {len(result.written)} file(s) in {result.output}"
        f" ({len(result.kept)} existing file(s) kept)."
    )
    if verbose:
        for path in result.written:
            print(f"  wrote {path}")
        for path in result.kept:
            print(f"  kept  {path}")
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if result.warnings and strict:
        return EXIT_WARNINGS
    return EXIT_OK


def run_gui(args: list[str]) -> int:
    """Starts the companion GUI.

    Args:
        args: Arguments passed to the GUI (optionally a .ui file).

    Returns:
        int: Process exit code.
    """
    from qt_modularizer.ui.main import main as gui_main

    return gui_main(["qt_modularizer"] + list(args))

# endregion

# ==========

# region Entry Point

@app.command("build", help="generate the ui package from a .ui file")
def build_command(
    ui: Annotated[str, typer.Option("--ui", help="path of the .ui file")],
    output: Annotated[
        str,
        typer.Option(
            "--output", help="folder of the generated package, e.g. src/ui"
        ),
    ],
    config: Annotated[
        Optional[str],
        typer.Option(
            "--config",
            help="settings file (default: ui_config.json next to the .ui file)",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="also overwrite the files you own (window class, main.py, widgets/)",
        ),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict", help="exit with code 1 if the generation raised warnings"
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="list files and show logs"),
    ] = False,
) -> None:
    """Typer wrapper of :func:`run_build`."""
    raise typer.Exit(run_build(ui, output, config, force, strict, verbose))


@app.command("gui", help="start the companion GUI")
def gui_command(
    ui: Annotated[Optional[str], typer.Argument(help="a .ui file to open")] = None,
) -> None:
    """Typer wrapper of :func:`run_gui`."""
    raise typer.Exit(run_gui([ui] if ui else []))


def main(argv: list[str] | None = None) -> int:
    """Runs the command line.

    Args:
        argv: Arguments without the program name, defaults to
            ``sys.argv[1:]``.

    Returns:
        int: Process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0].lower().endswith(".ui"):
        return run_gui(args)

    try:
        app(args=args, prog_name=PROG_NAME)
    except SystemExit as err:
        return err.code if isinstance(err.code, int) else EXIT_OK
    return EXIT_OK

# endregion