"""Qt compatibility layer, resolving the available binding through ``Qt.py``.
"""

# region Imports & Config

# python modules
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
VENDOR_DIR = CURRENT_DIR / "vendor"

vendor_str = str(VENDOR_DIR)

if vendor_str not in sys.path:
    sys.path.insert(0, vendor_str)

try:
    import Qt
    from Qt import QtCore, QtGui, QtWidgets, QtSvg

    QtSlot = QtCore.Slot
    QtSignal = QtCore.Signal

except ImportError as err:
    raise ImportError(
        f"Unable to load the Qt.py wrapper from '{vendor_str}'. "
        "Please make sure vendor/Qt.py is installed correctly."
    ) from err

__all__ = [
    "Qt",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "QtSvg",
    "QtSlot",
    "QtSignal",
]

# endregion
