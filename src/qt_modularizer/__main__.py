"""Allows ``python -m qt_modularizer`` to run the command line or the GUI.
"""

# region Imports & Config

# python modules
import sys

# qt_modularizer/..
from qt_modularizer.cli import main

# endregion

if __name__ == "__main__":
    sys.exit(main())
