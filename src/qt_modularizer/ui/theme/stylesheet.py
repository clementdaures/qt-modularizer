"""Qt stylesheet definitions for the Coral design system.

Semantic roles are applied with the ``role`` dynamic property, e.g.
``button.setProperty("role", "primaryButton")``, and targeted by
``QPushButton[role="primaryButton"]`` selectors.
"""

# region Imports & Config

# qt_modularizer/ui/theme/..
from .colors import DARK, LIGHT

# endregion

# ==========

# region Stylesheet Logic

def build_stylesheet(colors: dict[str, str]) -> str:
    """Builds the Coral Qt stylesheet.

    Args:
        colors: Active theme colors, e.g. ``LIGHT`` or ``DARK``.

    Returns:
        str: Complete Qt stylesheet.
    """
    return f"""
    /* ------------------------------------------------------------------
       Global
       ------------------------------------------------------------------ */

    QWidget {{
        background: {colors["bg"]};
        color: {colors["text"]};
        font-family: "Inter", "Segoe UI", sans-serif;
        font-size: 13px;
    }}

    QMainWindow {{
        background: {colors["bg"]};
    }}

    QLabel {{
        background: transparent;
    }}

    QWidget[role="tabPage"] {{
        background: transparent;
    }}

    /* Plain containers (Designer layout widgets, tab pages, central widgets)
       stay transparent, as they are natively. Forms laid out with absolute
       geometry often overlap them, and an opaque background would hide the
       widgets of the one underneath. ".QWidget" matches the exact class only,
       so windows and every other widget keep the background set above. */

    .QWidget {{
        background: transparent;
    }}

    .QWidget:window,
    QAbstractScrollArea .QWidget {{
        background: {colors["bg"]};
    }}


    /* ------------------------------------------------------------------
       Buttons
       ------------------------------------------------------------------ */

    /* A push button without a role looks like a secondary button. Its height
       stays close to a native one (about 22px) so that it fits the tight rows
       of forms laid out in Qt Designer instead of being clipped. */

    QPushButton {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 2px 13px;
        min-height: 16px;
    }}

    QPushButton:hover {{
        background: {colors["surface_hover"]};
    }}

    QPushButton:pressed {{
        background: {colors["surface2"]};
    }}

    QPushButton:disabled {{
        color: {colors["faint"]};
    }}


    /* Primary button */

    QPushButton[role="primaryButton"] {{
        background: {colors["accent"]};
        color: #FFFFFF;
        border: 1px solid {colors["accent"]};
        font-weight: 600;
    }}

    QPushButton[role="primaryButton"]:hover {{
        background: {colors["accent_hover"]};
        border-color: {colors["accent_hover"]};
    }}

    QPushButton[role="primaryButton"]:pressed {{
        background: {colors["accent_hover"]};
    }}

    QPushButton[role="primaryButton"]:disabled {{
        background: {colors["surface2"]};
        color: {colors["faint"]};
        border-color: {colors["border"]};
    }}


    /* Secondary button */

    QPushButton[role="secondaryButton"] {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
    }}

    QPushButton[role="secondaryButton"]:hover {{
        background: {colors["surface_hover"]};
    }}

    QPushButton[role="secondaryButton"]:pressed {{
        background: {colors["surface2"]};
    }}


    /* Danger button */

    QPushButton[role="dangerButton"] {{
        background: {colors["error_soft"]};
        color: {colors["error"]};
        border: 1px solid transparent;
    }}

    QPushButton[role="dangerButton"]:hover {{
        border-color: {colors["error"]};
    }}

    QPushButton[role="dangerButton"]:pressed {{
        background: {colors["error_soft"]};
    }}


    /* Generic icon button */

    QToolButton[role="iconButton"] {{
        background: transparent;
        color: {colors["muted"]};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px;
    }}

    QToolButton[role="iconButton"]:hover {{
        background: {colors["surface_hover"]};
        color: {colors["text"]};
    }}

    QToolButton[role="iconButton"]:pressed {{
        background: {colors["accent_soft"]};
    }}


    /* ------------------------------------------------------------------
       Activity bar
       ------------------------------------------------------------------ */

    QWidget#activityBar {{
        background: {colors["surface"]};
        border-top: 1px solid {colors["border"]};
    }}

    QToolButton[role="activityButton"] {{
        background: transparent;
        color: {colors["muted"]};
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 8px;
        min-width: 28px;
        min-height: 28px;
    }}

    QToolButton[role="activityButton"]:hover {{
        background: {colors["surface_hover"]};
        color: {colors["text"]};
    }}

    QToolButton[role="activityButton"]:checked {{
        background: {colors["accent_soft"]};
        color: {colors["accent"]};
    }}

    QToolButton[role="activityButton"]:checked:hover {{
        background: {colors["accent_soft"]};
        color: {colors["accent"]};
    }}

    QToolButton[role="activityButton"]:pressed {{
        background: {colors["accent_soft"]};
    }}

    QToolButton[role="activityButton"]:disabled {{
        color: {colors["faint"]};
    }}


    /* ------------------------------------------------------------------
       Navigation
       ------------------------------------------------------------------ */

    QPushButton[role="navButton"] {{
        background: transparent;
        border: 1px solid transparent;
        color: {colors["muted"]};
        text-align: left;
        padding: 9px 10px;
        border-radius: 8px;
    }}

    QPushButton[role="navButton"]:hover {{
        background: {colors["surface_hover"]};
        color: {colors["text"]};
    }}

    QPushButton[role="navButton"]:checked {{
        background: {colors["accent_soft"]};
        color: {colors["accent"]};
        font-weight: 600;
    }}


    /* ------------------------------------------------------------------
       Toolbar
       ------------------------------------------------------------------ */

    QToolBar#mainToolbar {{
        background: {colors["surface"]};
        border: none;
        spacing: 4px;
        padding: 4px 6px;
    }}

    QToolBar#mainToolbar::separator {{
        background: {colors["border"]};
        width: 1px;
        margin: 6px 4px;
    }}

    QWidget#spacer {{
        background: {colors["surface"]};
        border: none;
    }}

    QToolButton[role="iconButton"]:checked {{
        background: {colors["accent_soft"]};
    }}


    /* ------------------------------------------------------------------
       Burger menu
       ------------------------------------------------------------------ */

    QWidget#burgerMenuBar,
    QWidget#burgerStrip {{
        background: transparent;
    }}

    QToolButton[role="menuBarButton"] {{
        background: transparent;
        color: {colors["muted"]};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px 10px;
    }}

    QToolButton[role="menuBarButton"]:hover,
    QToolButton[role="menuBarButton"][open="true"] {{
        background: {colors["surface_hover"]};
        color: {colors["text"]};
    }}

    QMenu {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 24px 6px 28px;
        border-radius: 6px;
        margin: 1px 2px;
    }}

    QMenu::item:selected {{
        background: {colors["accent_soft"]};
    }}

    QMenu::item:disabled {{
        color: {colors["faint"]};
    }}

    QMenu::separator {{
        height: 1px;
        background: {colors["border"]};
        margin: 4px 8px;
    }}

    QMenu::indicator {{
        width: 10px;
        height: 10px;
        left: 8px;
    }}

    QMenu::indicator:non-exclusive:checked {{
        background: {colors["accent"]};
        border-radius: 3px;
    }}

    QMenu::indicator:exclusive:checked {{
        background: {colors["accent"]};
        border-radius: 5px;
    }}


    /* ------------------------------------------------------------------
       Command bar
       ------------------------------------------------------------------ */

    QWidget#commandBar {{
        background: transparent;
    }}

    QLineEdit[role="commandInput"] {{
        background: {colors["surface2"]};
        border-radius: 8px;
        padding: 5px 10px;
    }}

    QFrame#commandPopup {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
    }}

    QListWidget#commandList {{
        background: transparent;
        border: none;
    }}


    /* ------------------------------------------------------------------
       Labels
       ------------------------------------------------------------------ */

    QLabel[role="pageTitle"] {{
        color: {colors["text"]};
        font-size: 27px;
        font-weight: 700;
    }}

    QLabel[role="pageSubtitle"] {{
        color: {colors["muted"]};
    }}

    QLabel[role="sectionTitle"] {{
        color: {colors["text"]};
        font-size: 14px;
        font-weight: 600;
    }}

    QLabel[role="muted"] {{
        color: {colors["muted"]};
    }}

    QLabel[role="faint"] {{
        color: {colors["faint"]};
    }}

    QLabel#coralLogo {{
        background: {colors["surface"]};
    }}

    QLabel#separator {{
        background: {colors["surface"]};
    }}


    /* ------------------------------------------------------------------
       Cards and panels
       ------------------------------------------------------------------ */

    QFrame[role="card"] {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 11px;
    }}

    QWidget[role="panel"] {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 10px;
    }}


    /* ------------------------------------------------------------------
       Inputs
       ------------------------------------------------------------------ */

    QLineEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 3px 10px;
    }}

    QLineEdit:hover,
    QComboBox:hover,
    QSpinBox:hover,
    QDoubleSpinBox:hover {{
        border-color: {colors["faint"]};
    }}

    QLineEdit:focus,
    QComboBox:focus,
    QSpinBox:focus,
    QDoubleSpinBox:focus {{
        border-color: {colors["accent"]};
    }}

    QLineEdit:disabled,
    QComboBox:disabled,
    QSpinBox:disabled,
    QDoubleSpinBox:disabled {{
        background: {colors["surface2"]};
        color: {colors["faint"]};
    }}


    /* ------------------------------------------------------------------
       Text editors
       ------------------------------------------------------------------ */

    QTextEdit,
    QPlainTextEdit {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 8px;
    }}

    QTextEdit:focus,
    QPlainTextEdit:focus {{
        border-color: {colors["accent"]};
    }}


    /* ------------------------------------------------------------------
       Checkboxes and radio buttons
       ------------------------------------------------------------------ */

    QCheckBox,
    QRadioButton {{
        spacing: 7px;
    }}

    QCheckBox:disabled,
    QRadioButton:disabled {{
        color: {colors["faint"]};
    }}


    /* ------------------------------------------------------------------
       Tables
       ------------------------------------------------------------------ */

    QTableWidget,
    QTableView {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: none;
        gridline-color: {colors["border"]};
        selection-background-color: {colors["accent_soft"]};
        selection-color: {colors["text"]};
    }}

    QHeaderView::section {{
        background: {colors["surface2"]};
        color: {colors["muted"]};
        border: none;
        border-bottom: 1px solid {colors["border"]};
        padding: 9px;
        font-weight: 600;
    }}

    QTableWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {colors["border"]};
    }}


    /* ------------------------------------------------------------------
       Lists and trees
       ------------------------------------------------------------------ */

    QListWidget,
    QTreeWidget {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        outline: none;
    }}

    QListWidget::item,
    QTreeWidget::item {{
        padding: 6px 8px;
        border-radius: 6px;
    }}

    QListWidget::item:hover,
    QTreeWidget::item:hover {{
        background: {colors["surface_hover"]};
    }}

    QListWidget::item:selected,
    QTreeWidget::item:selected {{
        background: {colors["accent_soft"]};
        color: {colors["text"]};
    }}


    /* ------------------------------------------------------------------
       Tabs
       ------------------------------------------------------------------ */

    QTabWidget::pane {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
    }}

    QTabBar::tab {{
        background: transparent;
        color: {colors["muted"]};
        border: none;
        padding: 8px 12px;
    }}

    QTabBar::tab:hover {{
        color: {colors["text"]};
    }}

    QTabBar::tab:selected {{
        color: {colors["accent"]};
        font-weight: 600;
    }}


    /* ------------------------------------------------------------------
       Scrollbars
       ------------------------------------------------------------------ */

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {colors["border"]};
        border-radius: 5px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {colors["faint"]};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal {{
        background: {colors["border"]};
        border-radius: 5px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {colors["faint"]};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}


    /* ------------------------------------------------------------------
       Splitters
       ------------------------------------------------------------------ */

    QSplitter::handle {{
        background: {colors["border"]};
    }}

    QSplitter::handle:hover {{
        background: {colors["accent"]};
    }}


    /* ------------------------------------------------------------------
       Semantic labels
       ------------------------------------------------------------------ */

    QLabel[role="success"],
    QLabel[role="warning"],
    QLabel[role="error"],
    QLabel[role="info"] {{
        border-radius: 12px;
        padding: 5px 10px;
        font-weight: 600;
    }}

    QLabel[role="success"] {{
        color: {colors["success"]};
        background: {colors["success_soft"]};
    }}

    QLabel[role="warning"] {{
        color: {colors["warning"]};
        background: {colors["warning_soft"]};
    }}

    QLabel[role="error"] {{
        color: {colors["error"]};
        background: {colors["error_soft"]};
    }}

    QLabel[role="info"] {{
        color: {colors["info"]};
        background: {colors["info_soft"]};
    }}


    /* ------------------------------------------------------------------
       Tooltips
       ------------------------------------------------------------------ */

    QToolTip {{
        background: {colors["surface2"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        padding: 5px 7px;
    }}


    /* ------------------------------------------------------------------
       Status bar
       ------------------------------------------------------------------ */

    QStatusBar {{
        background: {colors["surface"]};
        color: {colors["muted"]};
        border-top: 1px solid {colors["border"]};
    }}
    """


def apply_stylesheet(app, dark: bool = False) -> None:
    """Applies the Coral stylesheet to a Qt application.

    Args:
        app: Qt application instance.
        dark: Whether to use the dark color scheme.
    """
    colors = DARK if dark else LIGHT
    app.setStyleSheet(build_stylesheet(colors))

# endregion
