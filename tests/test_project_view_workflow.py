import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from ai_project_organizer.ui.main_window import MainWindow
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    initialize_project_workspace_structure,
)


class ProjectViewWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.window = MainWindow(
            project_registry_path=self.root / "projects.json"
        )

    def tearDown(self) -> None:
        self.window.text_editor.document().setModified(False)
        self.window.close()
        self.temporary_directory.cleanup()

    def test_project_view_file_uses_shared_editor(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(workspace)
        document = workspace / "Documents" / "note.txt"
        document.write_text(
            "hello",
            encoding="utf-8",
        )
        self.window._set_workspace_root(str(workspace))

        self.window.project_view.file_open_requested.emit(
            str(document)
        )

        self.assertEqual(
            self.window.current_file_path,
            str(document),
        )
        self.assertEqual(
            self.window.text_editor.toPlainText(),
            "hello",
        )

    def test_unsaved_change_cancellation_is_shared(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(workspace)
        first = workspace / "Documents" / "first.txt"
        second = workspace / "Documents" / "second.txt"
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")
        self.window._set_workspace_root(str(workspace))
        self.window._open_file_path(first)
        self.window.text_editor.setPlainText("modified")
        self.window.text_editor.document().setModified(True)

        with patch.object(
            QMessageBox,
            "exec",
            return_value=QMessageBox.StandardButton.Cancel,
        ):
            self.window.project_view.file_open_requested.emit(
                str(second)
            )

        self.assertEqual(
            self.window.current_file_path,
            str(first),
        )
        self.assertEqual(
            self.window.text_editor.toPlainText(),
            "modified",
        )

    def test_project_and_files_tabs_share_editor_state(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(workspace)
        self.window._set_workspace_root(str(workspace))
        self.window.text_editor.setPlainText("modified")
        self.window.text_editor.document().setModified(True)

        self.window.workspace_navigation_tabs.setCurrentWidget(
            self.window.file_tree
        )
        self.window.workspace_navigation_tabs.setCurrentWidget(
            self.window.project_view
        )

        self.assertEqual(
            self.window.text_editor.toPlainText(),
            "modified",
        )
        self.assertTrue(
            self.window.text_editor.document().isModified()
        )

    def test_project_initialization_request_uses_existing_confirmation(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        self.window._set_workspace_root(str(workspace))

        with patch.object(
            QMessageBox,
            "exec",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._initialize_project_structure_from_view()

        self.assertTrue(
            (workspace / "Documents").is_dir()
        )
        self.assertTrue(
            (workspace / "Features").is_dir()
        )

    def test_package_initialization_from_view(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(workspace)
        feature = create_project_feature(
            workspace,
            "Feature",
        )
        package = feature / "Packages" / "PKG01"
        package.mkdir()
        self.window._set_workspace_root(str(workspace))

        with patch.object(
            QMessageBox,
            "exec",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._initialize_package_structure_from_view(
                "Feature",
                "PKG01",
            )

        self.assertTrue(
            (package / "Documents").is_dir()
        )
        self.assertTrue(
            (package / "Contents").is_dir()
        )


if __name__ == "__main__":
    unittest.main()
