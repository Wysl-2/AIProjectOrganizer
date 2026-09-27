import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.welcome_page import (
    ProjectBrowserEntry,
    WelcomePage,
)


class WelcomePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.page = WelcomePage()

    def tearDown(self) -> None:
        self.page.close()

    def test_empty_state_is_shown_without_projects(self) -> None:
        self.page.set_projects(())

        self.assertFalse(
            self.page.empty_label.isHidden()
        )
        self.assertTrue(
            self.page.project_list.isHidden()
        )

    def test_projects_are_displayed_in_supplied_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            entries = (
                ProjectBrowserEntry(
                    "Recent",
                    root / "recent",
                    True,
                ),
                ProjectBrowserEntry(
                    "Older",
                    root / "older",
                    True,
                ),
            )

            self.page.set_projects(
                entries
            )

            self.assertEqual(
                self.page.project_list.count(),
                2,
            )
            self.assertTrue(
                self.page.project_list.item(0).text().startswith(
                    "Recent\n"
                )
            )
            self.assertTrue(
                self.page.project_list.item(1).text().startswith(
                    "Older\n"
                )
            )

    def test_workspace_path_is_stored_with_project_item(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = (
                Path(temporary_directory)
                / "workspace"
            )

            self.page.set_projects(
                (
                    ProjectBrowserEntry(
                        "Project",
                        workspace,
                        True,
                    ),
                )
            )

            item = self.page.project_list.item(0)

            self.assertEqual(
                item.data(
                    Qt.ItemDataRole.UserRole
                ),
                str(workspace),
            )

    def test_unavailable_project_is_visibly_marked(self) -> None:
        workspace = (
            Path(tempfile.gettempdir())
            / "missing-project"
        )

        self.page.set_projects(
            (
                ProjectBrowserEntry(
                    "Missing",
                    workspace,
                    False,
                ),
            )
        )

        self.assertIn(
            "Unavailable",
            self.page.project_list.item(0).text(),
        )

    def test_open_existing_button_emits_signal(self) -> None:
        emissions: list[bool] = []
        self.page.open_existing_requested.connect(
            lambda: emissions.append(True)
        )

        self.page.open_existing_button.click()

        self.assertEqual(
            emissions,
            [True],
        )

    def test_project_activation_emits_workspace_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = (
                Path(temporary_directory)
                / "workspace"
            )
            self.page.set_projects(
                (
                    ProjectBrowserEntry(
                        "Project",
                        workspace,
                        True,
                    ),
                )
            )
            emissions: list[str] = []
            self.page.project_open_requested.connect(
                emissions.append
            )

            item = self.page.project_list.item(0)
            self.page.project_list.itemActivated.emit(
                item
            )

            self.assertEqual(
                emissions,
                [str(workspace)],
            )

    def test_create_project_is_reserved_for_later_workflow(self) -> None:
        self.assertFalse(
            self.page.create_project_button.isEnabled()
        )


if __name__ == "__main__":
    unittest.main()
