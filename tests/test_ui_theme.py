import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.theme import (
    ACCENT_COLOR,
    APPLICATION_STYLESHEET,
    BACKGROUND_COLOR,
    PRIMARY_TEXT_COLOR,
    apply_application_theme,
)


class UiThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = (
            QApplication.instance()
            or QApplication([])
        )

    def test_application_theme_is_applied(self) -> None:
        apply_application_theme(
            self.application
        )

        self.assertEqual(
            self.application.style().objectName().casefold(),
            "fusion",
        )
        self.assertTrue(
            self.application.styleSheet()
        )
        self.assertEqual(
            (
                self.application
                .palette()
                .color(
                    QPalette.ColorRole.Window
                )
                .name()
                .upper()
            ),
            BACKGROUND_COLOR,
        )
        self.assertEqual(
            (
                self.application
                .palette()
                .color(
                    QPalette.ColorRole.WindowText
                )
                .name()
                .upper()
            ),
            PRIMARY_TEXT_COLOR,
        )

    def test_stylesheet_contains_semantic_roles(self) -> None:
        for role in (
            'role="applicationTitle"',
            'role="pageTitle"',
            'role="sectionTitle"',
            'role="sectionDivider"',
            'role="workspaceNavigation"',
            'role="packageList"',
            'role="fileTree"',
            'role="projectList"',
            'role="documentEditor"',
            'role="consoleOutput"',
            'role="secondary"',
            'role="error"',
            'role="warning"',
            'role="metadataLabel"',
            'role="toolbar"',
            'role="primary"',
        ):
            with self.subTest(
                    role=role
            ):
                self.assertIn(
                    role,
                    APPLICATION_STYLESHEET,
                )

    def test_stylesheet_styles_combo_boxes(self) -> None:
        self.assertIn(
            "QComboBox",
            APPLICATION_STYLESHEET,
        )

    def test_stylesheet_contains_accent_color(self) -> None:
        self.assertIn(
            ACCENT_COLOR,
            APPLICATION_STYLESHEET,
        )


if __name__ == "__main__":
    unittest.main()
