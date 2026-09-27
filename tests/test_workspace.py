import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from ai_project_organizer.project import (
    PROJECT_METADATA_FILENAME,
    ProjectMetadata,
    load_project_metadata,
    save_project_metadata,
)
from ai_project_organizer.ui.main_window import MainWindow


class WorkspaceProjectIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()

    def _metadata(self, root: Path) -> ProjectMetadata:
        working_directory = root / "development" / "WorldMeshes"

        return ProjectMetadata(
            name="WorldMeshes",
            working_directory=working_directory,
            local_git_repository=working_directory / "Assets" / "WorldMeshes",
            github_repository="Wysl-2/WorldMeshes",
        )

    def test_configured_project_metadata_loads_with_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            metadata = self._metadata(workspace)

            save_project_metadata(workspace, metadata)
            self.window._set_workspace_root(str(workspace))

            self.assertEqual(self.window.workspace_path, str(workspace))
            self.assertEqual(self.window.project_metadata, metadata)
            self.assertIsNone(self.window.project_metadata_load_error)

    def test_workspace_without_metadata_remains_unconfigured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            self.window._set_workspace_root(str(workspace))

            self.assertEqual(self.window.workspace_path, str(workspace))
            self.assertIsNone(self.window.project_metadata)
            self.assertIsNone(self.window.project_metadata_load_error)

    def test_switching_workspace_clears_previous_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            configured_workspace = root / "configured"
            ordinary_workspace = root / "ordinary"
            configured_workspace.mkdir()
            ordinary_workspace.mkdir()

            metadata = self._metadata(root)
            save_project_metadata(configured_workspace, metadata)

            self.window._set_workspace_root(str(configured_workspace))
            self.assertEqual(self.window.project_metadata, metadata)

            self.window._set_workspace_root(str(ordinary_workspace))

            self.assertEqual(
                self.window.workspace_path,
                str(ordinary_workspace),
            )
            self.assertIsNone(self.window.project_metadata)
            self.assertIsNone(self.window.project_metadata_load_error)

    def test_invalid_metadata_does_not_prevent_workspace_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            metadata_path = workspace / PROJECT_METADATA_FILENAME
            metadata_path.write_text("{not valid json", encoding="utf-8")

            with patch.object(QMessageBox, "warning") as warning:
                self.window._set_workspace_root(str(workspace))

            self.assertEqual(self.window.workspace_path, str(workspace))
            self.assertIsNone(self.window.project_metadata)
            self.assertIsNotNone(self.window.project_metadata_load_error)
            self.assertIn(
                "invalid JSON",
                self.window.project_metadata_load_error,
            )
            warning.assert_called_once()

    def test_metadata_filesystem_error_keeps_workspace_active(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            with (
                patch(
                    "ai_project_organizer.ui.main_window.load_project_metadata",
                    side_effect=PermissionError("permission denied"),
                ),
                patch.object(QMessageBox, "warning") as warning,
            ):
                self.window._set_workspace_root(str(workspace))

            self.assertEqual(self.window.workspace_path, str(workspace))
            self.assertIsNone(self.window.project_metadata)
            self.assertEqual(
                self.window.project_metadata_load_error,
                "permission denied",
            )
            warning.assert_called_once()

    def test_configure_project_action_requires_workspace(self) -> None:
        self.assertFalse(
            self.window.configure_project_action.isEnabled()
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            self.window._set_workspace_root(str(workspace))

            self.assertTrue(
                self.window.configure_project_action.isEnabled()
            )

    def test_save_project_configuration_updates_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            metadata = self._metadata(workspace)

            self.window._set_workspace_root(str(workspace))

            result = self.window._save_project_configuration(
                metadata
            )

            self.assertTrue(result)
            self.assertEqual(
                self.window.project_metadata,
                metadata,
            )
            self.assertIsNone(
                self.window.project_metadata_load_error
            )
            self.assertEqual(
                load_project_metadata(workspace),
                metadata,
            )

    def test_save_project_configuration_failure_preserves_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            existing_metadata = self._metadata(root)
            updated_metadata = ProjectMetadata(
                name="Updated Project",
                working_directory=existing_metadata.working_directory,
                local_git_repository=existing_metadata.local_git_repository,
                github_repository=existing_metadata.github_repository,
            )

            self.window._set_workspace_root(str(workspace))
            self.window.project_metadata = existing_metadata
            self.window.project_metadata_load_error = None

            with (
                patch(
                    "ai_project_organizer.ui.main_window.save_project_metadata",
                    side_effect=PermissionError("permission denied"),
                ),
                patch.object(QMessageBox, "critical") as critical,
            ):
                result = self.window._save_project_configuration(
                    updated_metadata
                )

            self.assertFalse(result)
            self.assertEqual(
                self.window.project_metadata,
                existing_metadata,
            )
            self.assertIsNone(
                self.window.project_metadata_load_error
            )
            critical.assert_called_once()

    def test_project_configuration_refreshes_open_metadata_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            metadata = self._metadata(root)
            save_project_metadata(workspace, metadata)
            self.window._set_workspace_root(str(workspace))

            metadata_path = workspace / PROJECT_METADATA_FILENAME
            self.window.current_file_path = str(metadata_path)
            self.window.text_editor.setPlainText(
                metadata_path.read_text(encoding="utf-8")
            )
            self.window.text_editor.document().setModified(
                False
            )

            updated_metadata = ProjectMetadata(
                name="Updated Project",
                working_directory=metadata.working_directory,
                local_git_repository=metadata.local_git_repository,
                github_repository=metadata.github_repository,
            )

            result = self.window._save_project_configuration(
                updated_metadata
            )

            self.assertTrue(result)
            self.assertEqual(
                self.window.text_editor.toPlainText(),
                metadata_path.read_text(encoding="utf-8"),
            )
            self.assertFalse(
                self.window.text_editor.document().isModified()
            )
            self.assertEqual(
                self.window.project_metadata,
                updated_metadata,
            )


if __name__ == "__main__":
    unittest.main()
