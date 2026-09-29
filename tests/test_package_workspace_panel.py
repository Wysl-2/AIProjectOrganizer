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

from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.package_workspace_panel import (
    PackageWorkspacePanel,
)
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    create_project_package,
    initialize_project_workspace_structure,
)


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

    def test_valid_archive_and_extraction_are_presented(self) -> None:
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
            contents = package / "Contents"

            archive = contents / "package.zip"
            self._write_valid_archive(
                archive,
                "PackageArchive",
            )
            self._write_extracted_package(
                contents,
                "PackageExtracted",
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
                panel.archive_status_label.text(),
                "ZIP: package.zip",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "Extracted: PackageExtracted",
            )

    def test_multiple_artifacts_are_presented_as_counts(self) -> None:
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

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )
            panel.package_list.setCurrentRow(
                0
            )

            self.assertEqual(
                panel.archive_status_label.text(),
                "ZIPs: 2",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "Extracted packages: 2",
            )

    def test_invalid_contents_entries_do_not_change_valid_artifact_state(
            self,
    ) -> None:
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
            contents = package / "Contents"

            self._write_valid_archive(
                contents / "valid.zip",
                "ValidPackage",
            )
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

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )
            panel.package_list.setCurrentRow(
                0
            )

            self.assertEqual(
                panel.archive_status_label.text(),
                "ZIP: valid.zip",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "Extracted: None",
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

            emitted: list[
                tuple[str, str]
            ] = []
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

    def test_refresh_preserves_existing_selection_and_clears_removed_package(
            self,
    ) -> None:
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

            panel = PackageWorkspacePanel()
            panel.set_feature(
                workspace,
                "Feature",
            )
            panel.package_list.setCurrentRow(
                0
            )

            panel.refresh()

            self.assertEqual(
                panel.current_package_id,
                "PKG01",
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

    def test_contents_discovery_error_keeps_package_documents_available(
            self,
    ) -> None:
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
                / "design.txt"
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
            self.assertIs(
                panel.details_stack.currentWidget(),
                panel.package_details_page,
            )
            self.assertEqual(
                panel.package_documents_panel.directory_path,
                package / "Documents",
            )
            self.assertIn(
                "permission denied",
                panel.artifact_error_label.text(),
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

            added: list[str] = []
            imported: list[
                tuple[str, str, str]
            ] = []

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
