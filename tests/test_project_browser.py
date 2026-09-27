import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from ai_project_organizer.project import (
    ProjectMetadata,
    save_project_metadata,
)
from ai_project_organizer.project_registry import (
    ProjectRegistry,
    load_project_registry,
    save_project_registry,
)
from ai_project_organizer.ui.main_window import MainWindow


class ProjectBrowserIntegrationTests(unittest.TestCase):
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

    def test_window_starts_on_welcome_page_without_workspace(self) -> None:
        self.assertIsNone(
            self.window.workspace_path
        )
        self.assertIs(
            self.window.central_stack.currentWidget(),
            self.window.welcome_page,
        )

    def test_set_workspace_root_changes_session_without_registry_write(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()

        self.window._set_workspace_root(
            str(workspace)
        )

        self.assertEqual(
            self.window.workspace_path,
            str(workspace),
        )
        self.assertIs(
            self.window.central_stack.currentWidget(),
            self.window.workspace_page,
        )
        self.assertFalse(
            self.registry_path.exists()
        )

    def test_activation_registers_workspace(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()

        result = self.window._activate_workspace(
            workspace
        )

        self.assertTrue(result)
        registry = load_project_registry(
            self.registry_path
        )
        self.assertTrue(
            registry.contains(workspace)
        )

    def test_reopening_workspace_does_not_duplicate_registry_entry(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()

        self.window._activate_workspace(
            workspace
        )
        self.window._activate_workspace(
            workspace
        )

        registry = load_project_registry(
            self.registry_path
        )
        self.assertEqual(
            len(registry.projects),
            1,
        )

    def test_ordinary_workspace_can_be_registered(self) -> None:
        workspace = self.root / "ordinary"
        workspace.mkdir()

        self.window._activate_workspace(
            workspace
        )

        self.assertIsNone(
            self.window.project_metadata
        )
        self.assertTrue(
            load_project_registry(
                self.registry_path
            ).contains(workspace)
        )

    def test_close_project_returns_to_welcome_and_clears_state(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        self.window._activate_workspace(
            workspace
        )

        self.window._close_project()

        self.assertIsNone(
            self.window.workspace_path
        )
        self.assertIsNone(
            self.window.current_file_path
        )
        self.assertIsNone(
            self.window.project_metadata
        )
        self.assertIsNone(
            self.window.project_metadata_load_error
        )
        self.assertIsNone(
            self.window.file_tree.workspace_path
        )
        self.assertIs(
            self.window.central_stack.currentWidget(),
            self.window.welcome_page,
        )

    def test_close_project_respects_unsaved_change_cancellation(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        self.window._activate_workspace(
            workspace
        )

        with patch.object(
            self.window,
            "_confirm_discard_unsaved_changes",
            return_value=False,
        ):
            self.window._close_project()

        self.assertEqual(
            self.window.workspace_path,
            str(workspace),
        )
        self.assertIs(
            self.window.central_stack.currentWidget(),
            self.window.workspace_page,
        )

    def test_missing_registered_project_does_not_activate(self) -> None:
        missing = self.root / "missing"
        self.window.project_registry.register(
            missing
        )
        self.window._refresh_welcome_projects()

        with patch.object(
            QMessageBox,
            "warning",
        ) as warning:
            result = self.window._activate_workspace(
                missing
            )

        self.assertFalse(result)
        self.assertIsNone(
            self.window.workspace_path
        )
        warning.assert_called_once()

    def test_registry_load_failure_does_not_overwrite_registry(self) -> None:
        self.window.close()

        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        original_text = "{not valid json"
        self.registry_path.write_text(
            original_text,
            encoding="utf-8",
        )

        with patch.object(
            QMessageBox,
            "warning",
        ) as warning:
            self.window = MainWindow(
                project_registry_path=self.registry_path
            )

        self.assertIsNotNone(
            self.window.project_registry_load_error
        )
        warning.assert_called_once()

        workspace = self.root / "workspace"
        workspace.mkdir()

        self.window._activate_workspace(
            workspace
        )

        self.assertEqual(
            self.registry_path.read_text(
                encoding="utf-8"
            ),
            original_text,
        )

    def test_registry_save_failure_does_not_prevent_workspace_activation(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()

        with (
            patch(
                "ai_project_organizer.ui.main_window.save_project_registry",
                side_effect=PermissionError("permission denied"),
            ),
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
        ):
            result = self.window._activate_workspace(
                workspace
            )

        self.assertTrue(result)
        self.assertEqual(
            self.window.workspace_path,
            str(workspace),
        )
        self.assertIs(
            self.window.central_stack.currentWidget(),
            self.window.workspace_page,
        )
        warning.assert_called_once()

    def test_action_states_follow_workspace_and_document_state(self) -> None:
        self.assertFalse(
            self.window.new_file_action.isEnabled()
        )
        self.assertFalse(
            self.window.new_folder_action.isEnabled()
        )
        self.assertTrue(
            self.window.open_workspace_action.isEnabled()
        )
        self.assertTrue(
            self.window.new_project_action.isEnabled()
        )
        self.assertFalse(
            self.window.save_action.isEnabled()
        )
        self.assertFalse(
            self.window.configure_project_action.isEnabled()
        )
        self.assertFalse(
            self.window.close_project_action.isEnabled()
        )

        workspace = self.root / "workspace"
        workspace.mkdir()
        self.window._set_workspace_root(
            str(workspace)
        )

        self.assertTrue(
            self.window.new_file_action.isEnabled()
        )
        self.assertTrue(
            self.window.new_folder_action.isEnabled()
        )
        self.assertTrue(
            self.window.new_project_action.isEnabled()
        )
        self.assertFalse(
            self.window.save_action.isEnabled()
        )
        self.assertTrue(
            self.window.configure_project_action.isEnabled()
        )
        self.assertTrue(
            self.window.close_project_action.isEnabled()
        )

        document = workspace / "document.txt"
        document.write_text(
            "text",
            encoding="utf-8",
        )
        self.window.current_file_path = str(
            document
        )
        self.window._update_action_states()

        self.assertTrue(
            self.window.save_action.isEnabled()
        )

    def test_welcome_uses_metadata_name_when_available(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        development = self.root / "development"
        metadata = ProjectMetadata(
            name="Configured Project",
            working_directory=development,
            local_git_repository=development,
            github_repository="Wysl-2/ConfiguredProject",
        )
        save_project_metadata(
            workspace,
            metadata,
        )
        self.window.project_registry.register(
            workspace
        )

        self.window._refresh_welcome_projects()

        self.assertTrue(
            self.window.welcome_page.project_list.item(0).text().startswith(
                "Configured Project\n"
            )
        )

    def test_welcome_falls_back_to_folder_name_for_invalid_metadata(self) -> None:
        workspace = self.root / "FallbackProject"
        workspace.mkdir()
        (workspace / ".aiproject.json").write_text(
            "{not valid json",
            encoding="utf-8",
        )
        self.window.project_registry.register(
            workspace
        )

        with patch.object(
            QMessageBox,
            "warning",
        ) as warning:
            self.window._refresh_welcome_projects()

        self.assertTrue(
            self.window.welcome_page.project_list.item(0).text().startswith(
                "FallbackProject\n"
            )
        )
        warning.assert_not_called()

    def test_unavailable_registered_project_is_shown_without_removal(self) -> None:
        missing = self.root / "MissingProject"
        registry = ProjectRegistry()
        registry.register(
            missing
        )
        save_project_registry(
            registry,
            self.registry_path,
        )

        self.window.close()
        self.window = MainWindow(
            project_registry_path=self.registry_path
        )

        item_text = (
            self.window.welcome_page.project_list.item(0).text()
        )

        self.assertIn(
            "Unavailable",
            item_text,
        )
        self.assertTrue(
            self.window.project_registry.contains(
                missing
            )
        )

    def test_create_project_uses_normal_activation_and_registry_flow(self) -> None:
        workspace = self.root / "CreatedProject"
        metadata = ProjectMetadata(
            name="CreatedProject",
            working_directory=self.root / "development" / "CreatedProject",
            local_git_repository=self.root / "repositories" / "CreatedProject",
            github_repository="Wysl-2/CreatedProject",
        )

        with patch(
            "ai_project_organizer.ui.main_window.NewProjectDialog"
        ) as dialog_class:
            dialog = dialog_class.return_value
            dialog.exec.return_value = QDialog.DialogCode.Accepted
            dialog.project_metadata.return_value = metadata
            dialog.workspace_path.return_value = workspace

            self.window._create_project()

        self.assertEqual(
            self.window.workspace_path,
            str(workspace),
        )
        self.assertEqual(
            self.window.project_metadata,
            metadata,
        )
        self.assertTrue(
            load_project_registry(
                self.registry_path
            ).contains(workspace)
        )

    def test_failed_project_creation_does_not_activate_or_register(self) -> None:
        workspace = self.root / "FailedProject"
        metadata = ProjectMetadata(
            name="FailedProject",
            working_directory=self.root / "development" / "FailedProject",
            local_git_repository=self.root / "repositories" / "FailedProject",
            github_repository="Wysl-2/FailedProject",
        )

        with (
            patch(
                "ai_project_organizer.ui.main_window.NewProjectDialog"
            ) as dialog_class,
            patch(
                "ai_project_organizer.ui.main_window.create_project_workspace",
                side_effect=PermissionError("permission denied"),
            ),
            patch.object(
                QMessageBox,
                "critical",
            ) as critical,
        ):
            dialog = dialog_class.return_value
            dialog.exec.return_value = QDialog.DialogCode.Accepted
            dialog.project_metadata.return_value = metadata
            dialog.workspace_path.return_value = workspace

            self.window._create_project()

        self.assertIsNone(
            self.window.workspace_path
        )
        self.assertFalse(
            self.window.project_registry.contains(
                workspace
            )
        )
        critical.assert_called_once()

    def test_remove_registered_project_preserves_workspace(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        marker = workspace / "marker.txt"
        marker.write_text(
            "unchanged",
            encoding="utf-8",
        )
        self.window._activate_workspace(
            workspace
        )
        self.window._close_project()

        with patch.object(
            QMessageBox,
            "exec",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._remove_registered_project(
                str(workspace)
            )

        self.assertFalse(
            self.window.project_registry.contains(
                workspace
            )
        )
        self.assertFalse(
            load_project_registry(
                self.registry_path
            ).contains(workspace)
        )
        self.assertEqual(
            marker.read_text(encoding="utf-8"),
            "unchanged",
        )

    def test_unavailable_project_can_be_removed(self) -> None:
        missing = self.root / "missing"
        self.window.project_registry.register(
            missing
        )
        save_project_registry(
            self.window.project_registry,
            self.registry_path,
        )

        with patch.object(
            QMessageBox,
            "exec",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._remove_registered_project(
                str(missing)
            )

        self.assertFalse(
            self.window.project_registry.contains(
                missing
            )
        )

    def test_registry_save_failure_preserves_removed_entry(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        self.window.project_registry.register(
            workspace
        )
        save_project_registry(
            self.window.project_registry,
            self.registry_path,
        )

        with (
            patch.object(
                QMessageBox,
                "exec",
                return_value=QMessageBox.StandardButton.Yes,
            ),
            patch(
                "ai_project_organizer.ui.main_window.save_project_registry",
                side_effect=PermissionError("permission denied"),
            ),
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
        ):
            self.window._remove_registered_project(
                str(workspace)
            )

        self.assertTrue(
            self.window.project_registry.contains(
                workspace
            )
        )
        self.assertTrue(
            load_project_registry(
                self.registry_path
            ).contains(workspace)
        )
        warning.assert_called_once()

    def test_registry_removal_can_be_cancelled(self) -> None:
        workspace = self.root / "workspace"
        workspace.mkdir()
        self.window.project_registry.register(
            workspace
        )
        save_project_registry(
            self.window.project_registry,
            self.registry_path,
        )

        with patch.object(
            QMessageBox,
            "exec",
            return_value=QMessageBox.StandardButton.No,
        ):
            self.window._remove_registered_project(
                str(workspace)
            )

        self.assertTrue(
            self.window.project_registry.contains(
                workspace
            )
        )


if __name__ == "__main__":
    unittest.main()
