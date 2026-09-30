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
from ai_project_organizer.ui.project_settings_dialog import (
    ProjectSettingsDialog,
)


class ProjectSettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _metadata(self, root: Path) -> ProjectMetadata:
        working_directory = root / "development" / "WorldMeshes"

        return ProjectMetadata(
            name="WorldMeshes",
            working_directory=working_directory,
            local_git_repository=(
                working_directory / "Assets" / "WorldMeshes"
            ),
            github_repository="Wysl-2/WorldMeshes",
        )

    def test_save_button_uses_primary_presentation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            dialog = ProjectSettingsDialog(
                Path(temporary_directory)
            )
            button_box = dialog.findChild(
                QDialogButtonBox
            )
            self.assertIsNotNone(
                button_box
            )
            save_button = button_box.button(
                QDialogButtonBox.StandardButton.Save
            )

            self.assertIsNotNone(
                save_button
            )
            self.assertEqual(
                save_button.property(
                    "role"
                ),
                "primary",
            )

            dialog.close()

    def test_existing_metadata_populates_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            metadata = self._metadata(root)

            dialog = ProjectSettingsDialog(
                workspace,
                metadata,
            )

            self.assertEqual(
                dialog.name_edit.text(),
                metadata.name,
            )
            self.assertEqual(
                dialog.working_directory_edit.text(),
                str(metadata.working_directory),
            )
            self.assertEqual(
                dialog.local_git_repository_edit.text(),
                str(metadata.local_git_repository),
            )
            self.assertEqual(
                dialog.github_repository_edit.text(),
                metadata.github_repository,
            )

            dialog.close()

    def test_ordinary_workspace_uses_directory_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "WorldMeshes"
            workspace.mkdir()

            dialog = ProjectSettingsDialog(
                workspace
            )

            self.assertEqual(
                dialog.name_edit.text(),
                "WorldMeshes",
            )
            self.assertEqual(
                dialog.working_directory_edit.text(),
                "",
            )
            self.assertEqual(
                dialog.local_git_repository_edit.text(),
                "",
            )
            self.assertEqual(
                dialog.github_repository_edit.text(),
                "",
            )

            dialog.close()

    def test_valid_fields_build_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            working_directory = root / "development" / "WorldMeshes"
            git_repository = working_directory / "Assets" / "WorldMeshes"

            dialog = ProjectSettingsDialog(
                workspace
            )
            dialog.name_edit.setText(
                "WorldMeshes"
            )
            dialog.working_directory_edit.setText(
                str(working_directory)
            )
            dialog.local_git_repository_edit.setText(
                str(git_repository)
            )
            dialog.github_repository_edit.setText(
                "Wysl-2/WorldMeshes"
            )

            self.assertEqual(
                dialog.project_metadata(),
                ProjectMetadata(
                    name="WorldMeshes",
                    working_directory=working_directory,
                    local_git_repository=git_repository,
                    github_repository="Wysl-2/WorldMeshes",
                ),
            )

            dialog.close()

    def test_invalid_fields_raise_project_metadata_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            dialog = ProjectSettingsDialog(
                workspace
            )
            dialog.name_edit.setText(
                ""
            )
            dialog.working_directory_edit.setText(
                "relative/project"
            )
            dialog.local_git_repository_edit.setText(
                "relative/repository"
            )
            dialog.github_repository_edit.setText(
                "not-a-repository"
            )

            with self.assertRaises(ProjectMetadataError):
                dialog.project_metadata()

            dialog.close()


if __name__ == "__main__":
    unittest.main()
