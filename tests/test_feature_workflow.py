import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMessageBox,
)

from ai_project_organizer.ui.main_window import MainWindow
from ai_project_organizer.workspace_structure import (
    initialize_project_workspace_structure,
)


class FeatureWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(
            self.temporary_directory.name
        )
        self.registry_path = (
            self.root
            / "config"
            / "projects.json"
        )
        self.window = MainWindow(
            project_registry_path=self.registry_path
        )

    def tearDown(self) -> None:
        self.window.text_editor.document().setModified(
            False
        )
        self.window.close()
        self.temporary_directory.cleanup()

    def test_add_feature_creates_complete_feature_structure(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(
            workspace
        )
        self.window._set_workspace_root(
            str(workspace)
        )

        with patch.object(
            QInputDialog,
            "getText",
            return_value=(
                "Filesystem Drag Drop",
                True,
            ),
        ):
            self.window._add_feature()

        feature = (
            workspace
            / "Features"
            / "Filesystem Drag Drop"
        )

        self.assertTrue(
            (feature / "Documents").is_dir()
        )
        self.assertTrue(
            (feature / "Packages").is_dir()
        )

    def test_add_feature_can_initialize_older_workspace_after_confirmation(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        self.window._set_workspace_root(
            str(workspace)
        )

        with (
            patch.object(
                QMessageBox,
                "exec",
                return_value=QMessageBox.StandardButton.Yes,
            ),
            patch.object(
                QInputDialog,
                "getText",
                return_value=(
                    "Filesystem Safety",
                    True,
                ),
            ),
        ):
            self.window._add_feature()

        feature = (
            workspace
            / "Features"
            / "Filesystem Safety"
        )

        self.assertTrue(
            (workspace / "Documents").is_dir()
        )
        self.assertTrue(
            (workspace / "Features").is_dir()
        )
        self.assertTrue(
            (feature / "Documents").is_dir()
        )
        self.assertTrue(
            (feature / "Packages").is_dir()
        )

    def test_declined_workspace_initialization_leaves_workspace_unchanged(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        self.window._set_workspace_root(
            str(workspace)
        )

        with (
            patch.object(
                QMessageBox,
                "exec",
                return_value=QMessageBox.StandardButton.No,
            ),
            patch.object(
                QInputDialog,
                "getText",
            ) as get_text,
        ):
            self.window._add_feature()

        self.assertFalse(
            (workspace / "Documents").exists()
        )
        self.assertFalse(
            (workspace / "Features").exists()
        )
        get_text.assert_not_called()

    def test_cancelled_feature_name_input_creates_nothing(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(
            workspace
        )
        self.window._set_workspace_root(
            str(workspace)
        )

        with patch.object(
            QInputDialog,
            "getText",
            return_value=(
                "",
                False,
            ),
        ):
            self.window._add_feature()

        self.assertEqual(
            list(
                (workspace / "Features").iterdir()
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
