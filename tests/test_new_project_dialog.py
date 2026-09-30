import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
)

from ai_project_organizer.project import (
    ProjectMetadata,
    ProjectMetadataError,
)
from ai_project_organizer.ui.new_project_dialog import NewProjectDialog


class NewProjectDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _populate_valid_fields(
            self,
            dialog: NewProjectDialog,
            root: Path,
            name: str = "NewProject",
    ) -> None:
        dialog.project_location_edit.setText(
            str(root)
        )
        dialog.name_edit.setText(
            name
        )
        dialog.working_directory_edit.setText(
            str(root / "development" / name)
        )
        dialog.local_git_repository_edit.setText(
            str(root / "repositories" / name)
        )
        dialog.github_repository_edit.setText(
            f"Wysl-2/{name}"
        )

    def test_create_button_uses_primary_presentation(self) -> None:
        dialog = NewProjectDialog()
        button_box = dialog.findChild(
            QDialogButtonBox
        )
        self.assertIsNotNone(
            button_box
        )
        create_button = button_box.button(
            QDialogButtonBox.StandardButton.Ok
        )

        self.assertIsNotNone(
            create_button
        )
        self.assertEqual(
            create_button.property(
                "role"
            ),
            "primary",
        )

        dialog.close()

    def test_valid_fields_produce_workspace_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dialog = NewProjectDialog()
            self._populate_valid_fields(
                dialog,
                root,
            )

            self.assertEqual(
                dialog.workspace_path(),
                root / "NewProject",
            )
            self.assertEqual(
                dialog.project_metadata(),
                ProjectMetadata(
                    name="NewProject",
                    working_directory=root / "development" / "NewProject",
                    local_git_repository=root / "repositories" / "NewProject",
                    github_repository="Wysl-2/NewProject",
                ),
            )

            dialog.close()

    def test_project_location_expands_home(self) -> None:
        dialog = NewProjectDialog()
        dialog.project_location_edit.setText(
            "~"
        )

        self.assertEqual(
            dialog.project_location(),
            Path.home(),
        )

        dialog.close()

    def test_relative_project_location_is_rejected(self) -> None:
        dialog = NewProjectDialog()
        self._populate_valid_fields(
            dialog,
            Path.home(),
        )
        dialog.project_location_edit.setText(
            "relative/location"
        )

        with self.assertRaises(ValueError):
            dialog.workspace_path()

        dialog.close()

    def test_missing_project_location_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dialog = NewProjectDialog()
            self._populate_valid_fields(
                dialog,
                root,
            )
            dialog.project_location_edit.setText(
                str(root / "missing")
            )

            with self.assertRaises(FileNotFoundError):
                dialog.workspace_path()

            dialog.close()

    def test_non_directory_project_location_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            location = root / "location.txt"
            location.write_text(
                "file",
                encoding="utf-8",
            )
            dialog = NewProjectDialog()
            self._populate_valid_fields(
                dialog,
                root,
            )
            dialog.project_location_edit.setText(
                str(location)
            )

            with self.assertRaises(NotADirectoryError):
                dialog.workspace_path()

            dialog.close()

    def test_existing_workspace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "NewProject").mkdir()
            dialog = NewProjectDialog()
            self._populate_valid_fields(
                dialog,
                root,
            )

            with self.assertRaises(FileExistsError):
                dialog.workspace_path()

            dialog.close()

    def test_empty_project_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dialog = NewProjectDialog()
            self._populate_valid_fields(
                dialog,
                root,
            )
            dialog.name_edit.setText(
                ""
            )

            with self.assertRaises(ProjectMetadataError):
                dialog.workspace_path()

            dialog.close()

    def test_special_directory_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            for name in (".", "..", "folder/name", "folder\\name"):
                with self.subTest(name=name):
                    dialog = NewProjectDialog()
                    self._populate_valid_fields(
                        dialog,
                        root,
                    )
                    dialog.name_edit.setText(
                        name
                    )

                    with self.assertRaises(ValueError):
                        dialog.workspace_path()

                    dialog.close()


if __name__ == "__main__":
    unittest.main()
