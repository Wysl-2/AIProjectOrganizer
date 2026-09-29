import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
)

from ai_project_organizer.ui.main_window import MainWindow
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    initialize_project_workspace_structure,
)


class PackageWorkflowTests(unittest.TestCase):
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

    def _initialized_workspace(self) -> Path:
        workspace = self.root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(
            workspace
        )
        return workspace

    def test_add_package_creates_complete_package_structure(self) -> None:
        workspace = self._initialized_workspace()
        create_project_feature(
            workspace,
            "Filesystem Drag Drop",
        )
        self.window._set_workspace_root(
            str(workspace)
        )

        with patch(
            "ai_project_organizer.ui.main_window.AddPackageDialog"
        ) as dialog_class:
            dialog = dialog_class.return_value
            dialog.exec.return_value = QDialog.DialogCode.Accepted
            dialog.feature_name.return_value = "Filesystem Drag Drop"
            dialog.package_id.return_value = "FI03"

            self.window._add_package()

        package = (
            workspace
            / "Features"
            / "Filesystem Drag Drop"
            / "Packages"
            / "FI03"
        )

        self.assertTrue(
            (package / "Documents").is_dir()
        )
        self.assertTrue(
            (package / "Contents").is_dir()
        )

    def test_add_package_without_features_does_not_open_dialog(self) -> None:
        workspace = self._initialized_workspace()
        self.window._set_workspace_root(
            str(workspace)
        )

        with (
            patch(
                "ai_project_organizer.ui.main_window.AddPackageDialog"
            ) as dialog_class,
            patch.object(
                QMessageBox,
                "information",
            ) as information,
        ):
            self.window._add_package()

        dialog_class.assert_not_called()
        information.assert_called_once()
        self.assertEqual(
            list(
                (workspace / "Features").iterdir()
            ),
            [],
        )

    def test_add_package_can_initialize_incomplete_feature(self) -> None:
        workspace = self._initialized_workspace()
        feature = (
            workspace
            / "Features"
            / "Existing Feature"
        )
        feature.mkdir()
        marker = feature / "notes.txt"
        marker.write_text(
            "preserve",
            encoding="utf-8",
        )
        self.window._set_workspace_root(
            str(workspace)
        )

        with (
            patch(
                "ai_project_organizer.ui.main_window.AddPackageDialog"
            ) as dialog_class,
            patch.object(
                QMessageBox,
                "exec",
                return_value=QMessageBox.StandardButton.Yes,
            ),
        ):
            dialog = dialog_class.return_value
            dialog.exec.return_value = QDialog.DialogCode.Accepted
            dialog.feature_name.return_value = "Existing Feature"
            dialog.package_id.return_value = "PKG01"

            self.window._add_package()

        package = (
            feature
            / "Packages"
            / "PKG01"
        )

        self.assertTrue(
            (feature / "Documents").is_dir()
        )
        self.assertTrue(
            (package / "Documents").is_dir()
        )
        self.assertTrue(
            (package / "Contents").is_dir()
        )
        self.assertEqual(
            marker.read_text(encoding="utf-8"),
            "preserve",
        )

    def test_declined_feature_initialization_creates_no_package(self) -> None:
        workspace = self._initialized_workspace()
        feature = (
            workspace
            / "Features"
            / "Existing Feature"
        )
        feature.mkdir()
        marker = feature / "notes.txt"
        marker.write_text(
            "preserve",
            encoding="utf-8",
        )
        self.window._set_workspace_root(
            str(workspace)
        )

        with (
            patch(
                "ai_project_organizer.ui.main_window.AddPackageDialog"
            ) as dialog_class,
            patch.object(
                QMessageBox,
                "exec",
                return_value=QMessageBox.StandardButton.No,
            ),
        ):
            dialog = dialog_class.return_value
            dialog.exec.return_value = QDialog.DialogCode.Accepted
            dialog.feature_name.return_value = "Existing Feature"
            dialog.package_id.return_value = "PKG01"

            self.window._add_package()

        self.assertFalse(
            (feature / "Documents").exists()
        )
        self.assertFalse(
            (feature / "Packages").exists()
        )
        self.assertEqual(
            marker.read_text(encoding="utf-8"),
            "preserve",
        )

    def test_cancelled_add_package_dialog_creates_nothing(self) -> None:
        workspace = self._initialized_workspace()
        feature = create_project_feature(
            workspace,
            "Filesystem Drag Drop",
        )
        self.window._set_workspace_root(
            str(workspace)
        )

        with patch(
            "ai_project_organizer.ui.main_window.AddPackageDialog"
        ) as dialog_class:
            dialog = dialog_class.return_value
            dialog.exec.return_value = QDialog.DialogCode.Rejected

            self.window._add_package()

        self.assertEqual(
            list(
                (feature / "Packages").iterdir()
            ),
            [],
        )

    def test_add_package_preserves_modified_current_document(self) -> None:
        workspace = self._initialized_workspace()
        create_project_feature(
            workspace,
            "Filesystem Drag Drop",
        )
        document = workspace / "notes.txt"
        document.write_text(
            "original",
            encoding="utf-8",
        )
        self.window._set_workspace_root(
            str(workspace)
        )

        self.window.current_file_path = str(
            document
        )
        self.window.text_editor.setPlainText(
            "modified"
        )
        self.window.text_editor.document().setModified(
            True
        )

        with patch(
            "ai_project_organizer.ui.main_window.AddPackageDialog"
        ) as dialog_class:
            dialog = dialog_class.return_value
            dialog.exec.return_value = QDialog.DialogCode.Accepted
            dialog.feature_name.return_value = "Filesystem Drag Drop"
            dialog.package_id.return_value = "FI03"

            self.window._add_package()

        self.assertEqual(
            self.window.current_file_path,
            str(document),
        )
        self.assertEqual(
            self.window.text_editor.toPlainText(),
            "modified",
        )
        self.assertTrue(
            self.window.text_editor.document().isModified()
        )


if __name__ == "__main__":
    unittest.main()
