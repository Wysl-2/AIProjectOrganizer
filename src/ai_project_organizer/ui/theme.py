from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


BACKGROUND_COLOR = "#1E1F22"
SECONDARY_BACKGROUND_COLOR = "#25262A"
CONTROL_BACKGROUND_COLOR = "#2B2D31"
INPUT_BACKGROUND_COLOR = "#191A1D"
BORDER_COLOR = "#34363B"

PRIMARY_TEXT_COLOR = "#D7DAE0"
SECONDARY_TEXT_COLOR = "#91969F"
DISABLED_TEXT_COLOR = "#62666D"
ICON_FOREGROUND_COLOR = "#C9CDD3"

ACCENT_COLOR = "#4EA1D3"
SELECTION_COLOR = "#264F78"
HOVER_COLOR = "#2A2D32"

ERROR_COLOR = "#D66C75"
WARNING_COLOR = "#D2A55B"


APPLICATION_STYLESHEET = f"""
QWidget {{
    color: {PRIMARY_TEXT_COLOR};
    selection-background-color: {SELECTION_COLOR};
    selection-color: {PRIMARY_TEXT_COLOR};
}}

QMainWindow,
QDialog,
QStackedWidget {{
    background-color: {BACKGROUND_COLOR};
}}

QMenuBar {{
    background-color: {SECONDARY_BACKGROUND_COLOR};
    color: {PRIMARY_TEXT_COLOR};
    border-bottom: 1px solid {BORDER_COLOR};
    spacing: 2px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 5px 8px;
}}

QMenuBar::item:selected {{
    background-color: {HOVER_COLOR};
}}

QMenu {{
    background-color: {SECONDARY_BACKGROUND_COLOR};
    color: {PRIMARY_TEXT_COLOR};
    border: 1px solid {BORDER_COLOR};
    padding: 4px;
}}

QMenu::item {{
    padding: 5px 24px 5px 8px;
    border-radius: 2px;
}}

QMenu::item:selected {{
    background-color: {SELECTION_COLOR};
}}

QMenu::item:disabled {{
    color: {DISABLED_TEXT_COLOR};
}}

QMenu::separator {{
    height: 1px;
    background-color: {BORDER_COLOR};
    margin: 4px 6px;
}}

QTabWidget::pane {{
    background-color: {BACKGROUND_COLOR};
    border: 1px solid {BORDER_COLOR};
}}

QTabBar::tab {{
    background-color: {SECONDARY_BACKGROUND_COLOR};
    color: {SECONDARY_TEXT_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-bottom: none;
    padding: 6px 12px;
    margin-right: 1px;
}}

QTabBar::tab:hover {{
    background-color: {HOVER_COLOR};
    color: {PRIMARY_TEXT_COLOR};
}}

QTabBar::tab:selected {{
    background-color: {BACKGROUND_COLOR};
    color: {PRIMARY_TEXT_COLOR};
    border-top: 2px solid {ACCENT_COLOR};
}}

QTabWidget[role="workspaceNavigation"]::pane {{
    background-color: {BACKGROUND_COLOR};
    border: none;
}}

QTabWidget[role="workspaceNavigation"] QTabBar::tab {{
    background: transparent;
    color: {SECONDARY_TEXT_COLOR};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 6px 10px;
    margin-right: 2px;
}}

QTabWidget[role="workspaceNavigation"] QTabBar::tab:hover {{
    background-color: {HOVER_COLOR};
    color: {PRIMARY_TEXT_COLOR};
}}

QTabWidget[role="workspaceNavigation"] QTabBar::tab:selected {{
    background: transparent;
    color: {PRIMARY_TEXT_COLOR};
    border-bottom: 2px solid {ACCENT_COLOR};
}}

QTabWidget[role="workspaceNavigation"] QTabBar::tab:disabled {{
    background: transparent;
    color: {DISABLED_TEXT_COLOR};
}}

QAbstractItemView {{
    background-color: {INPUT_BACKGROUND_COLOR};
    color: {PRIMARY_TEXT_COLOR};
    border: 1px solid {BORDER_COLOR};
    outline: none;
    selection-background-color: {SELECTION_COLOR};
    selection-color: {PRIMARY_TEXT_COLOR};
}}

QListView::item,
QListWidget::item,
QTreeView::item {{
    padding: 3px 6px;
}}

QListWidget[role="packageList"]::item {{
    padding: 6px 8px;
}}

QListView::item:hover,
QListWidget::item:hover,
QTreeView::item:hover {{
    background-color: {HOVER_COLOR};
}}

QListView::item:selected,
QListWidget::item:selected,
QTreeView::item:selected {{
    background-color: {SELECTION_COLOR};
    color: {PRIMARY_TEXT_COLOR};
}}

QLineEdit,
QPlainTextEdit {{
    background-color: {INPUT_BACKGROUND_COLOR};
    color: {PRIMARY_TEXT_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    padding: 4px;
    selection-background-color: {SELECTION_COLOR};
    selection-color: {PRIMARY_TEXT_COLOR};
}}

QLineEdit:focus,
QPlainTextEdit:focus {{
    border-color: {ACCENT_COLOR};
}}

QLineEdit:disabled,
QPlainTextEdit:disabled {{
    color: {DISABLED_TEXT_COLOR};
    background-color: {SECONDARY_BACKGROUND_COLOR};
}}

QPushButton,
QToolButton {{
    background-color: {CONTROL_BACKGROUND_COLOR};
    color: {PRIMARY_TEXT_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    padding: 5px 10px;
}}

QPushButton:hover,
QToolButton:hover {{
    background-color: {HOVER_COLOR};
    border-color: {ACCENT_COLOR};
}}

QPushButton:pressed,
QToolButton:pressed {{
    background-color: {SELECTION_COLOR};
}}

QPushButton:focus,
QToolButton:focus {{
    border-color: {ACCENT_COLOR};
}}

QPushButton:disabled,
QToolButton:disabled {{
    background-color: {SECONDARY_BACKGROUND_COLOR};
    color: {DISABLED_TEXT_COLOR};
    border-color: {BORDER_COLOR};
}}

QGroupBox {{
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    margin-top: 12px;
    padding-top: 6px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
    color: {SECONDARY_TEXT_COLOR};
}}

QSplitter::handle {{
    background-color: {BORDER_COLOR};
}}

QSplitter::handle:hover {{
    background-color: {ACCENT_COLOR};
}}

QSplitter::handle:horizontal {{
    width: 3px;
}}

QSplitter::handle:vertical {{
    height: 3px;
}}

QScrollBar:vertical {{
    background: {BACKGROUND_COLOR};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_COLOR};
    min-height: 24px;
    border-radius: 4px;
    margin: 1px;
}}

QScrollBar::handle:vertical:hover {{
    background: {SECONDARY_TEXT_COLOR};
}}

QScrollBar:horizontal {{
    background: {BACKGROUND_COLOR};
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER_COLOR};
    min-width: 24px;
    border-radius: 4px;
    margin: 1px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {SECONDARY_TEXT_COLOR};
}}

QScrollBar::add-line,
QScrollBar::sub-line {{
    width: 0;
    height: 0;
    background: transparent;
}}

QScrollBar::add-page,
QScrollBar::sub-page {{
    background: transparent;
}}

QToolTip {{
    background-color: {SECONDARY_BACKGROUND_COLOR};
    color: {PRIMARY_TEXT_COLOR};
    border: 1px solid {BORDER_COLOR};
    padding: 4px;
}}

QFrame[role="sectionDivider"] {{
    background-color: {BORDER_COLOR};
    border: none;
    min-height: 1px;
    max-height: 1px;
}}

QLabel[role="pageTitle"] {{
    color: {PRIMARY_TEXT_COLOR};
    font-size: 15px;
    font-weight: 600;
}}

QLabel[role="sectionTitle"] {{
    color: {SECONDARY_TEXT_COLOR};
    font-size: 12px;
    font-weight: 600;
}}

QLabel[role="secondary"] {{
    color: {SECONDARY_TEXT_COLOR};
}}

QLabel[role="error"] {{
    color: {ERROR_COLOR};
}}

QLabel[role="warning"] {{
    color: {WARNING_COLOR};
}}

QLabel[role="metadataLabel"] {{
    color: {SECONDARY_TEXT_COLOR};
    font-weight: 600;
}}

QPushButton[role="toolbar"],
QToolButton[role="toolbar"] {{
    background: transparent;
    border-color: transparent;
    padding: 4px 6px;
}}

QPushButton[role="toolbar"]:hover,
QToolButton[role="toolbar"]:hover {{
    background-color: {HOVER_COLOR};
    border-color: {BORDER_COLOR};
}}

QPushButton[role="primary"],
QToolButton[role="primary"] {{
    background-color: {SELECTION_COLOR};
    border-color: {ACCENT_COLOR};
    color: {PRIMARY_TEXT_COLOR};
}}
"""


def build_application_palette() -> QPalette:
    palette = QPalette()

    palette.setColor(
        QPalette.ColorRole.Window,
        QColor(BACKGROUND_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.WindowText,
        QColor(PRIMARY_TEXT_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.Base,
        QColor(INPUT_BACKGROUND_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.AlternateBase,
        QColor(SECONDARY_BACKGROUND_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.Text,
        QColor(PRIMARY_TEXT_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.Button,
        QColor(CONTROL_BACKGROUND_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.ButtonText,
        QColor(PRIMARY_TEXT_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.Highlight,
        QColor(SELECTION_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.HighlightedText,
        QColor(PRIMARY_TEXT_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.PlaceholderText,
        QColor(SECONDARY_TEXT_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.ToolTipBase,
        QColor(SECONDARY_BACKGROUND_COLOR),
    )
    palette.setColor(
        QPalette.ColorRole.ToolTipText,
        QColor(PRIMARY_TEXT_COLOR),
    )

    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            role,
            QColor(DISABLED_TEXT_COLOR),
        )

    return palette


def apply_application_theme(
        app: QApplication,
) -> None:
    app.setStyle("Fusion")
    app.setPalette(
        build_application_palette()
    )
    app.setStyleSheet(
        APPLICATION_STYLESHEET
    )
