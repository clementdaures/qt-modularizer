"""Entry point of the QtModularizer companion GUI.
"""

# region Imports & Config

# python modules
import sys

# daeria_log
import daeria_log

# qt_modularizer/ui/..
from .main_window import MainWindow
from .qt_compat import QtWidgets

# endregion

# ==========

# region Entry Point

def main(argv: list[str] | None = None) -> int:
    """Starts the companion GUI.

    Args:
        argv: Command line arguments. An optional ``.ui`` file path may
            follow the program name. Defaults to ``sys.argv``.

    Returns:
        int: Process exit code.
    """
    args = list(sys.argv if argv is None else argv)
    daeria_log.ensure_setup(app="qt_modularizer", product="qt_modularizer")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(args)

    window = MainWindow()
    window.show()
    if len(args) > 1:
        window.open_file(args[1])

    return app.exec()

# endregion


if __name__ == "__main__":
    sys.exit(main())
