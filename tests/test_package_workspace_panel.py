import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.package_workspace_panel import (
    PackageWorkspacePanel,
)
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    create_project_package,
    initialize_project_package_structure,
    initialize_project_workspace_structure,
)


class _RecordingMenu:
    latest_actions: list[str] = []

    def __init__(
            self,
            _parent=None,
    ) -> None:
        self._actions = []
        type(self).latest_actions = []

    def addAction(
            self,
            text: str,
    ):
        action = object()
        self._actions.append(
            action
        )
        type(self).latest_actions.append(
            text
        )
        return action

    def addSeparator(self) -> None:
        pass

    def actions(self):
        return self._actions

    def exec(
            self,
            _position,
    ):
        return None


class PackageWorkspacePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _workspace(
            self,
            root: Path,
    ) -> Path:
        workspace = root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(
            workspace
        )
        create_project_feature(
            workspace,
            "Feature",
        )
        return workspace

    @staticmethod
    def _list_texts(
            panel: PackageWorkspacePanel,
    ) -> list[str]:
        return [
            panel.package_list.item(
                index
            ).text()
            for index in range(
                panel.package_list.count()
            )
        ]

    @staticmethod
    def _write_valid_archive(
            path: Path,
            root_name: str,
    ) -> None:
        with zipfile.ZipFile(
            path,
            "w",
        ) as archive:
            archive.writestr(
                f"{root_name}/Install.py",
                "print('install')\n",
            )
            archive.writestr(
                f"{root_name}/README.txt",
                "# SUMMARY\n\nSummary\n",
            )
            archive.writestr(
                f"{root_name}/Project/file.txt",
                "payload",
            )

    @staticmethod
    def _write_extracted_package(
            contents: Path,
            root_name: str,
    ) -> Path:
        package_root = contents / root_name
        package_root.mkdir()
        (
            package_root
            / "Install.py"
        ).write_text(
            "print('install')\n",
            encoding="utf-8",
        )
        (
            package_root
            / "README.txt"
        ).write_text(
            "# SUMMARY\n\nSummary\n",
            encoding="utf-8",
        )
        (
            package_root
            / "Project"
        ).mkdir()

        return package_root

    def _panel_with_package(
            self,
            root: Path,
    ) -> tuple[
        PackageWorkspacePanel,
        Path,
        Path,
    ]:
        workspace = self._workspace(
            root
        )
        package = create_project_package(
            workspace,
            "Feature",
            "PKG01",
        )

        panel = PackageWorkspacePanel()
        panel.set_feature(
            workspace,
            "Feature",
        )
        panel.package_list.setCurrentRow(
            0
        )
        QApplication.processEvents()

        return (
            panel,
            workspace,
            package,
        )

    def test_packages_are_discovered_without_automatic_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )
            create_project_package(
                workspace,
                "Feature",
                "PKG02",
            )
            create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )

            self.assertEqual(
                self._list_texts(
                    panel
                ),
                [
                    "PKG01",
                    "PKG02",
                ],
            )
            self.assertIsNone(
                panel.current_package_id
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.no_selection_page,
            )
            self.assertIn(
                "Select a Package",
                panel.no_selection_label.text(),
            )

    def test_empty_feature_shows_no_packages_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )

            self.assertEqual(
                panel.package_list.count(),
                0,
            )
            self.assertFalse(
                panel.status_label.isHidden()
            )
            self.assertIn(
                "No Packages",
                panel.status_label.text(),
            )
            self.assertIn(
                "Create a Package",
                panel.no_selection_label.text(),
            )
            self.assertTrue(
                panel.add_package_button.isEnabled()
            )

    def test_no_packages_state_clears_after_package_is_created(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )

            create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )
            panel.refresh()

            self.assertTrue(
                panel.status_label.isHidden()
            )
            self.assertEqual(
                panel.status_label.text(),
                "",
            )
            self.assertIn(
                "PKG01",
                self._list_texts(
                    panel
                ),
            )
            self.assertIsNone(
                panel.current_package_id
            )
            self.assertIn(
                "Select a Package",
                panel.no_selection_label.text(),
            )

    def test_selection_displays_package_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )
            package = create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )
            document = (
                package
                / "Documents"
                / "Code Implementation Design.txt"
            )
            document.write_text(
                "design",
                encoding="utf-8",
            )

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )
            panel.package_list.setCurrentRow(
                0
            )
            QApplication.processEvents()

            self.assertEqual(
                panel.current_package_id,
                "PKG01",
            )
            self.assertEqual(
                panel.package_title_label.text(),
                "PKG01",
            )
            self.assertIn(
                "Code Implementation Design.txt",
                [
                    panel.package_documents_panel.list_widget.item(
                        index
                    ).text()
                    for index in range(
                        panel.package_documents_panel.list_widget.count()
                    )
                ],
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.package_details_page,
            )

    def test_package_document_creation_emits_canonical_documents_path(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )

            emitted: list[str] = []
            panel.new_document_requested.connect(
                emitted.append
            )

            panel.package_documents_panel._request_new_document()

            self.assertEqual(
                emitted,
                [
                    str(
                        package
                        / "Documents"
                    )
                ],
            )

    def test_empty_complete_package_action_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, _package = self._panel_with_package(
                root
            )

            self.assertTrue(
                panel.import_package_button.isEnabled()
            )
            self.assertFalse(
                panel.extract_package_button.isEnabled()
            )
            self.assertFalse(
                panel.inspect_package_button.isEnabled()
            )
            self.assertFalse(
                panel.install_package_button.isEnabled()
            )
            self.assertTrue(
                panel.open_contents_button.isEnabled()
            )

    def test_valid_archive_enables_extract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )
            self._write_valid_archive(
                package / "Contents" / "package.zip",
                "PackageArchive",
            )

            panel.refresh()

            self.assertEqual(
                panel.archive_status_label.text(),
                "ZIP: package.zip",
            )
            self.assertTrue(
                panel.extract_package_button.isEnabled()
            )
            self.assertFalse(
                panel.inspect_package_button.isEnabled()
            )
            self.assertFalse(
                panel.install_package_button.isEnabled()
            )

    def test_valid_extraction_enables_inspect_and_install(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )
            self._write_extracted_package(
                package / "Contents",
                "PackageExtracted",
            )

            panel.refresh()

            self.assertEqual(
                panel.extracted_status_label.text(),
                "Extracted: PackageExtracted",
            )
            self.assertTrue(
                panel.inspect_package_button.isEnabled()
            )
            self.assertTrue(
                panel.install_package_button.isEnabled()
            )

    def test_valid_archive_and_extraction_enable_all_artifact_actions(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )
            contents = package / "Contents"
            self._write_valid_archive(
                contents / "package.zip",
                "PackageArchive",
            )
            self._write_extracted_package(
                contents,
                "PackageExtracted",
            )

            panel.refresh()

            self.assertTrue(
                panel.import_package_button.isEnabled()
            )
            self.assertTrue(
                panel.extract_package_button.isEnabled()
            )
            self.assertTrue(
                panel.inspect_package_button.isEnabled()
            )
            self.assertTrue(
                panel.install_package_button.isEnabled()
            )
            self.assertTrue(
                panel.open_contents_button.isEnabled()
            )

    def test_multiple_artifacts_are_counts_without_disabling_actions(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )
            contents = package / "Contents"
            self._write_valid_archive(
                contents / "a.zip",
                "PackageA",
            )
            self._write_valid_archive(
                contents / "b.zip",
                "PackageB",
            )
            self._write_extracted_package(
                contents,
                "ExtractedA",
            )
            self._write_extracted_package(
                contents,
                "ExtractedB",
            )

            panel.refresh()

            self.assertEqual(
                panel.archive_status_label.text(),
                "ZIPs: 2",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "Extracted packages: 2",
            )
            self.assertTrue(
                panel.extract_package_button.isEnabled()
            )
            self.assertTrue(
                panel.inspect_package_button.isEnabled()
            )
            self.assertTrue(
                panel.install_package_button.isEnabled()
            )

    def test_invalid_contents_entries_do_not_enable_artifact_actions(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )
            contents = package / "Contents"

            (
                contents
                / "invalid.zip"
            ).write_text(
                "not a zip",
                encoding="utf-8",
            )
            invalid_directory = contents / "InvalidDirectory"
            invalid_directory.mkdir()
            (
                invalid_directory
                / "file.txt"
            ).write_text(
                "invalid",
                encoding="utf-8",
            )

            panel.refresh()

            self.assertEqual(
                panel.archive_status_label.text(),
                "ZIP: None",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "Extracted: None",
            )
            self.assertFalse(
                panel.extract_package_button.isEnabled()
            )
            self.assertFalse(
                panel.inspect_package_button.isEnabled()
            )
            self.assertFalse(
                panel.install_package_button.isEnabled()
            )

    def test_artifact_discovery_error_disables_state_dependent_actions(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )
            document = (
                package
                / "Documents"
                / "design.txt"
            )
            document.write_text(
                "design",
                encoding="utf-8",
            )

            with patch(
                "ai_project_organizer.ui.package_workspace_panel.discover_implementation_package_archives",
                side_effect=OSError(
                    "permission denied"
                ),
            ):
                panel._refresh_selected_package()

            self.assertEqual(
                panel.current_package_id,
                "PKG01",
            )
            self.assertEqual(
                panel.package_documents_panel.directory_path,
                package / "Documents",
            )
            self.assertIn(
                "permission denied",
                panel.artifact_error_label.text(),
            )
            self.assertEqual(
                panel.archive_status_label.text(),
                "",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "",
            )
            self.assertTrue(
                panel.import_package_button.isEnabled()
            )
            self.assertFalse(
                panel.extract_package_button.isEnabled()
            )
            self.assertFalse(
                panel.inspect_package_button.isEnabled()
            )
            self.assertFalse(
                panel.install_package_button.isEnabled()
            )

    def test_artifact_error_clears_after_successful_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, _package = self._panel_with_package(
                root
            )

            with patch(
                "ai_project_organizer.ui.package_workspace_panel.discover_implementation_package_archives",
                side_effect=OSError(
                    "temporary failure"
                ),
            ):
                panel._refresh_selected_package()

            self.assertFalse(
                panel.artifact_error_label.isHidden()
            )
            self.assertIn(
                "temporary failure",
                panel.artifact_error_label.text(),
            )

            panel.refresh()

            self.assertTrue(
                panel.artifact_error_label.isHidden()
            )
            self.assertEqual(
                panel.artifact_error_label.text(),
                "",
            )
            self.assertEqual(
                panel.archive_status_label.text(),
                "ZIP: None",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "Extracted: None",
            )

    def test_import_cancel_emits_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, _package = self._panel_with_package(
                root
            )

            emitted = []
            panel.implementation_package_import_requested.connect(
                lambda *args: emitted.append(
                    args
                )
            )

            with patch(
                "ai_project_organizer.ui.package_workspace_panel.QFileDialog.getOpenFileName",
                return_value=(
                    "",
                    "",
                ),
            ):
                panel._request_package_import()

            self.assertEqual(
                emitted,
                [],
            )

    def test_import_selection_emits_existing_semantic_request(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, _package = self._panel_with_package(
                root
            )

            emitted = []
            panel.implementation_package_import_requested.connect(
                lambda source, feature, package_id: emitted.append(
                    (
                        source,
                        feature,
                        package_id,
                    )
                )
            )

            with patch(
                "ai_project_organizer.ui.package_workspace_panel.QFileDialog.getOpenFileName",
                return_value=(
                    "/tmp/package.zip",
                    "ZIP Archives (*.zip)",
                ),
            ):
                panel._request_package_import()

            self.assertEqual(
                emitted,
                [
                    (
                        "/tmp/package.zip",
                        "Feature",
                        "PKG01",
                    )
                ],
            )

    def test_visible_artifact_actions_emit_semantic_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, _package = self._panel_with_package(
                root
            )

            extracted = []
            inspected = []
            installed = []

            panel.extract_implementation_package_requested.connect(
                lambda feature, package_id: extracted.append(
                    (
                        feature,
                        package_id,
                    )
                )
            )
            panel.inspect_implementation_package_requested.connect(
                lambda feature, package_id: inspected.append(
                    (
                        feature,
                        package_id,
                    )
                )
            )
            panel.install_implementation_package_requested.connect(
                lambda feature, package_id: installed.append(
                    (
                        feature,
                        package_id,
                    )
                )
            )

            panel._request_package_extraction()
            panel._request_package_inspection()
            panel._request_package_installation()

            self.assertEqual(
                extracted,
                [
                    (
                        "Feature",
                        "PKG01",
                    )
                ],
            )
            self.assertEqual(
                inspected,
                [
                    (
                        "Feature",
                        "PKG01",
                    )
                ],
            )
            self.assertEqual(
                installed,
                [
                    (
                        "Feature",
                        "PKG01",
                    )
                ],
            )

    def test_open_contents_uses_canonical_package_contents_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )

            with patch(
                "ai_project_organizer.ui.package_workspace_panel.QDesktopServices.openUrl",
                return_value=True,
            ) as open_url:
                panel._open_selected_package_contents()

            open_url.assert_called_once()
            url = open_url.call_args.args[0]

            self.assertEqual(
                Path(
                    url.toLocalFile()
                ),
                package / "Contents",
            )

    def test_incomplete_package_shows_recovery_and_emits_initialization(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )
            package = (
                workspace
                / "Features"
                / "Feature"
                / "Packages"
                / "PKG01"
            )
            package.mkdir()

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )
            panel.package_list.setCurrentRow(
                0
            )

            self.assertEqual(
                panel.current_package_id,
                "PKG01",
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.recovery_page,
            )
            self.assertIn(
                "incomplete",
                panel.recovery_status_label.text().lower(),
            )

            emitted = []
            panel.initialize_package_requested.connect(
                lambda feature, package_id: emitted.append(
                    (
                        feature,
                        package_id,
                    )
                )
            )

            panel._request_package_initialization()

            self.assertEqual(
                emitted,
                [
                    (
                        "Feature",
                        "PKG01",
                    )
                ],
            )

    def test_incomplete_package_transitions_to_complete_without_losing_selection(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )
            package = (
                workspace
                / "Features"
                / "Feature"
                / "Packages"
                / "PKG01"
            )
            package.mkdir()

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )
            panel.package_list.setCurrentRow(
                0
            )

            initialize_project_package_structure(
                workspace,
                "Feature",
                "PKG01",
            )
            panel.refresh()

            self.assertEqual(
                panel.current_package_id,
                "PKG01",
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.package_details_page,
            )
            self.assertEqual(
                panel.package_documents_panel.directory_path,
                package / "Documents",
            )
            self.assertTrue(
                panel.import_package_button.isEnabled()
            )

    def test_refresh_preserves_existing_selection_and_clears_removed_package(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, package = self._panel_with_package(
                root
            )
            contents = package / "Contents"
            self._write_valid_archive(
                contents / "package.zip",
                "PackageArchive",
            )
            panel.refresh()

            self.assertEqual(
                panel.current_package_id,
                "PKG01",
            )
            self.assertEqual(
                panel.archive_status_label.text(),
                "ZIP: package.zip",
            )

            shutil.rmtree(
                package
            )
            panel.refresh()

            self.assertIsNone(
                panel.current_package_id
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.no_selection_page,
            )
            self.assertEqual(
                panel.package_title_label.text(),
                "",
            )
            self.assertIsNone(
                panel.package_documents_panel.directory_path
            )
            self.assertEqual(
                panel.archive_status_label.text(),
                "",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "",
            )
            self.assertTrue(
                panel.artifact_error_label.isHidden()
            )
            self.assertEqual(
                panel.artifact_error_label.text(),
                "",
            )
            self.assertFalse(
                panel.import_package_button.isEnabled()
            )
            self.assertFalse(
                panel.extract_package_button.isEnabled()
            )
            self.assertFalse(
                panel.inspect_package_button.isEnabled()
            )
            self.assertFalse(
                panel.install_package_button.isEnabled()
            )
            self.assertFalse(
                panel.open_contents_button.isEnabled()
            )
            self.assertIn(
                "Create a Package",
                panel.no_selection_label.text(),
            )

    def test_feature_change_clears_package_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )
            create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )
            create_project_feature(
                workspace,
                "Feature B",
            )
            create_project_package(
                workspace,
                "Feature B",
                "PKG02",
            )

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )
            panel.package_list.setCurrentRow(
                0
            )

            self.assertEqual(
                panel.current_package_id,
                "PKG01",
            )

            panel.set_feature(
                workspace,
                "Feature B",
            )

            self.assertIsNone(
                panel.current_package_id
            )
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.no_selection_page,
            )

    def test_package_discovery_error_clears_selection_and_details(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, _package = self._panel_with_package(
                root
            )

            with patch(
                "ai_project_organizer.ui.package_workspace_panel.discover_feature_packages",
                side_effect=OSError(
                    "permission denied"
                ),
            ):
                panel.refresh()

            self.assertIsNone(
                panel.current_package_id
            )
            self.assertEqual(
                panel.package_list.count(),
                0,
            )
            self.assertIn(
                "Unable to discover Packages",
                panel.status_label.text(),
            )
            self.assertIn(
                "unavailable",
                panel.no_selection_label.text(),
            )
            self.assertEqual(
                panel.package_title_label.text(),
                "",
            )
            self.assertFalse(
                panel.import_package_button.isEnabled()
            )
            self.assertFalse(
                panel.extract_package_button.isEnabled()
            )
            self.assertFalse(
                panel.inspect_package_button.isEnabled()
            )
            self.assertFalse(
                panel.install_package_button.isEnabled()
            )
            self.assertFalse(
                panel.open_contents_button.isEnabled()
            )

    def test_context_menu_no_longer_contains_primary_workflow_actions(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            panel, _workspace, _package = self._panel_with_package(
                root
            )
            item = panel.package_list.item(
                0
            )

            with (
                patch(
                    "ai_project_organizer.ui.package_workspace_panel.QMenu",
                    _RecordingMenu,
                ),
                patch.object(
                    panel.package_list,
                    "itemAt",
                    return_value=item,
                ),
            ):
                panel._show_package_context_menu(
                    QPoint(
                        0,
                        0,
                    )
                )

            self.assertIn(
                "Copy Path",
                _RecordingMenu.latest_actions,
            )
            self.assertIn(
                "Open in File Manager",
                _RecordingMenu.latest_actions,
            )
            self.assertNotIn(
                "Extract Implementation Package...",
                _RecordingMenu.latest_actions,
            )
            self.assertNotIn(
                "Inspect Implementation Package...",
                _RecordingMenu.latest_actions,
            )
            self.assertNotIn(
                "Install Implementation Package...",
                _RecordingMenu.latest_actions,
            )

    def test_drop_and_add_package_intent_include_current_feature(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._workspace(
                root
            )

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )

            added = []
            imported = []

            panel.add_package_requested.connect(
                added.append
            )
            panel.implementation_package_import_requested.connect(
                lambda source, feature, package_id: imported.append(
                    (
                        source,
                        feature,
                        package_id,
                    )
                )
            )

            panel._request_add_package()
            panel._package_drop_requested(
                "/tmp/package.zip",
                "PKG01",
            )
            panel._package_drop_requested(
                "/tmp/background.zip",
                "",
            )

            self.assertEqual(
                added,
                [
                    "Feature"
                ],
            )
            self.assertEqual(
                imported,
                [
                    (
                        "/tmp/package.zip",
                        "Feature",
                        "PKG01",
                    ),
                    (
                        "/tmp/background.zip",
                        "Feature",
                        "",
                    ),
                ],
            )


if __name__ == "__main__":
    unittest.main()
