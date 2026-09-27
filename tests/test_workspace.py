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


if __name__ == "__main__":
    unittest.main()
