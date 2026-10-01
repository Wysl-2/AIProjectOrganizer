import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.project_patch_workspace_panel import (
    ProjectPatchWorkspacePanel,
)
from ai_project_organizer.workspace_structure import (
    create_project_patch,
    initialize_project_patch_structure,
    initialize_project_workspace_structure,
)


class ProjectPatchWorkspacePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def _workspace(
            root: Path,
            name: str = "workspace",
    ) -> Path:
        workspace = root / name
        workspace.mkdir()
        initialize_project_workspace_structure(
            workspace
        )
        return workspace

    @staticmethod
    def _list_texts(
            panel: ProjectPatchWorkspacePanel,
    ) -> list[str]:
        return [
            panel.patch_list.item(
                index
            ).text()
            for index in range(
                panel.patch_list.count()
            )
        ]

    def _panel_with_patch(
            self,
            root: Path,
            patch_id: str = "Fix",
    ) -> tuple[
        ProjectPatchWorkspacePanel,
        Path,
        Path,
    ]:
        workspace = self._workspace(
            root
        )
        patch_path = create_project_patch(
            workspace,
            patch_id,
        )
        panel = ProjectPatchWorkspacePanel()
        panel.set_workspace(
            workspace
        )
        panel.patch_list.setCurrentRow(
            0
        )
        QApplication.processEvents()
        return panel, workspace, patch_path

    def test_initial_state_is_disabled_and_clear(self) -> None:
        panel = ProjectPatchWorkspacePanel()

        self.assertEqual(
            panel.title_label.text(),
            "PATCHES",
        )
        self.assertFalse(
            panel.add_patch_button.isEnabled()
        )
        self.assertIsNone(
            panel.current_patch_id
        )
        self.assertEqual(
            panel.patch_list.count(),
            0,
        )

    def test_empty_workspace_does_not_create_patches_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )

            panel = ProjectPatchWorkspacePanel()
            panel.set_workspace(
                workspace
            )

            self.assertFalse(
                (
                    workspace
                    / "Patches"
                ).exists()
            )
            self.assertEqual(
                panel.patch_list.count(),
                0,
            )
            self.assertEqual(
                panel.no_selection_title_label.text(),
                "No Patches",
            )
            self.assertTrue(
                panel.add_patch_button.isEnabled()
            )

    def test_discovery_lists_patches_without_auto_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )
            create_project_patch(
                workspace,
                "Beta",
            )
            create_project_patch(
                workspace,
                "Alpha",
            )

            panel = ProjectPatchWorkspacePanel()
            panel.set_workspace(
                workspace
            )

            self.assertEqual(
                self._list_texts(
                    panel
                ),
                [
                    "Alpha",
                    "Beta",
                ],
            )
            self.assertIsNone(
                panel.current_patch_id
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.no_selection_page,
            )

    def test_complete_patch_configures_reusable_work_item(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, patch_path = (
                self._panel_with_patch(
                    root
                )
            )

            self.assertEqual(
                panel.current_patch_id,
                "Fix",
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.work_item_panel,
            )
            self.assertEqual(
                panel.work_item_panel.title_label.text(),
                "Fix",
            )
            self.assertEqual(
                panel.work_item_panel.documents_panel.directory_path,
                patch_path / "Documents",
            )
            self.assertEqual(
                panel.work_item_panel.contents_path,
                patch_path / "Contents",
            )

    def test_patch_document_request_is_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, patch_path = (
                self._panel_with_patch(
                    root
                )
            )
            emitted: list[str] = []
            panel.new_document_requested.connect(
                emitted.append
            )

            panel.work_item_panel.documents_panel._request_new_document()

            self.assertEqual(
                emitted,
                [
                    str(
                        patch_path / "Documents"
                    )
                ],
            )

    def test_work_item_actions_are_adapted_to_patch_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, patch_path = (
                self._panel_with_patch(
                    root
                )
            )
            imported = []
            extracted = []
            inspected = []
            installed = []

            panel.implementation_package_import_requested.connect(
                lambda source, patch_id: imported.append(
                    (
                        source,
                        patch_id,
                    )
                )
            )
            panel.extract_implementation_package_requested.connect(
                extracted.append
            )
            panel.inspect_implementation_package_requested.connect(
                inspected.append
            )
            panel.install_implementation_package_requested.connect(
                installed.append
            )

            stale_contents = str(
                patch_path.parent
                / "Other"
                / "Contents"
            )
            panel.work_item_panel.implementation_package_import_requested.emit(
                "/tmp/package.zip",
                stale_contents,
            )
            panel.work_item_panel.extract_implementation_package_requested.emit(
                stale_contents
            )
            panel.work_item_panel.inspect_implementation_package_requested.emit(
                stale_contents
            )
            panel.work_item_panel.install_implementation_package_requested.emit(
                stale_contents
            )

            self.assertEqual(
                imported,
                [
                    (
                        "/tmp/package.zip",
                        "Fix",
                    )
                ],
            )
            self.assertEqual(
                extracted,
                [
                    "Fix"
                ],
            )
            self.assertEqual(
                inspected,
                [
                    "Fix"
                ],
            )
            self.assertEqual(
                installed,
                [
                    "Fix"
                ],
            )

    def test_incomplete_patch_shows_recovery_and_requests_initialization(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )
            patches_root = workspace / "Patches"
            patches_root.mkdir()
            patch_path = patches_root / "Manual"
            patch_path.mkdir()

            panel = ProjectPatchWorkspacePanel()
            panel.set_workspace(
                workspace
            )
            panel.patch_list.setCurrentRow(
                0
            )

            emitted: list[str] = []
            panel.initialize_patch_requested.connect(
                emitted.append
            )

            self.assertIn(
                "Structure incomplete",
                panel.patch_list.item(
                    0
                ).text(),
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.recovery_page,
            )
            self.assertFalse(
                panel.initialize_patch_button.isHidden()
            )

            panel._request_patch_initialization()

            self.assertEqual(
                emitted,
                [
                    "Manual"
                ],
            )

    def test_incomplete_patch_transitions_to_complete_with_selection(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )
            patches_root = workspace / "Patches"
            patches_root.mkdir()
            patch_path = patches_root / "Manual"
            patch_path.mkdir()

            panel = ProjectPatchWorkspacePanel()
            panel.set_workspace(
                workspace
            )
            panel.patch_list.setCurrentRow(
                0
            )

            initialize_project_patch_structure(
                workspace,
                "Manual",
            )
            panel.refresh()

            self.assertEqual(
                panel.current_patch_id,
                "Manual",
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.work_item_panel,
            )
            self.assertEqual(
                panel.work_item_panel.documents_panel.directory_path,
                patch_path / "Documents",
            )

    def test_refresh_preserves_selection_and_clears_removed_patch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, patch_path = (
                self._panel_with_patch(
                    root
                )
            )

            panel.refresh()

            self.assertEqual(
                panel.current_patch_id,
                "Fix",
            )

            shutil.rmtree(
                patch_path
            )
            panel.refresh()

            self.assertIsNone(
                panel.current_patch_id
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.no_selection_page,
            )
            self.assertIsNone(
                panel.work_item_panel.contents_path
            )

    def test_workspace_change_clears_previous_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            first = self._workspace(
                root,
                "first",
            )
            second = self._workspace(
                root,
                "second",
            )
            create_project_patch(
                first,
                "FirstPatch",
            )
            create_project_patch(
                second,
                "SecondPatch",
            )

            panel = ProjectPatchWorkspacePanel()
            panel.set_workspace(
                first
            )
            panel.patch_list.setCurrentRow(
                0
            )
            self.assertEqual(
                panel.current_patch_id,
                "FirstPatch",
            )

            panel.set_workspace(
                second
            )

            self.assertIsNone(
                panel.current_patch_id
            )
            self.assertEqual(
                self._list_texts(
                    panel
                ),
                [
                    "SecondPatch"
                ],
            )

    def test_discovery_error_clears_stale_patch_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, _patch_path = (
                self._panel_with_patch(
                    root
                )
            )

            with patch(
                "ai_project_organizer.ui.project_patch_workspace_panel."
                "discover_project_patches",
                side_effect=OSError(
                    "permission denied"
                ),
            ):
                panel.refresh()

            self.assertIsNone(
                panel.current_patch_id
            )
            self.assertEqual(
                panel.patch_list.count(),
                0,
            )
            self.assertEqual(
                panel.no_selection_title_label.text(),
                "Patches Unavailable",
            )
            self.assertIn(
                "permission denied",
                panel.status_label.text(),
            )
            self.assertIsNone(
                panel.work_item_panel.contents_path
            )


if __name__ == "__main__":
    unittest.main()
