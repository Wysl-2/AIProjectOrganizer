import os
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

from ai_project_organizer.ui.implementation_work_item_panel import (
    ImplementationWorkItemPanel,
)


class ImplementationWorkItemPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def _write_valid_archive(
            path: Path,
            root_name: str = "ExamplePackage",
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
            root_name: str = "ExtractedPackage",
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

    @staticmethod
    def _work_item(
            root: Path,
    ) -> tuple[Path, Path]:
        documents = root / "Documents"
        contents = root / "Contents"
        documents.mkdir()
        contents.mkdir()
        return documents, contents

    def test_initial_state_is_clear_and_actions_are_disabled(self) -> None:
        panel = ImplementationWorkItemPanel()

        self.assertEqual(
            panel.title_label.text(),
            "",
        )
        self.assertIsNone(
            panel.documents_panel.directory_path
        )
        self.assertIsNone(
            panel.contents_path
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

    def test_set_work_item_configures_documents_and_empty_artifact_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )

            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "PKG01",
                documents,
                contents,
            )

            self.assertEqual(
                panel.title_label.text(),
                "PKG01",
            )
            self.assertEqual(
                panel.documents_panel.directory_path,
                documents,
            )
            self.assertEqual(
                panel.contents_path,
                contents,
            )
            self.assertEqual(
                panel.archive_status_label.text(),
                "None",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "None",
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

    def test_archive_and_extracted_state_controls_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            self._write_valid_archive(
                contents / "package.zip",
                "ArchivePackage",
            )
            self._write_extracted_package(
                contents,
                "ExtractedPackage",
            )

            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "Work Item",
                documents,
                contents,
            )

            self.assertEqual(
                panel.archive_status_label.text(),
                "package.zip",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "ExtractedPackage",
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

    def test_multiple_artifacts_use_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            self._write_valid_archive(
                contents / "a.zip",
                "ArchiveA",
            )
            self._write_valid_archive(
                contents / "b.zip",
                "ArchiveB",
            )
            self._write_extracted_package(
                contents,
                "ExtractedA",
            )
            self._write_extracted_package(
                contents,
                "ExtractedB",
            )

            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "Work Item",
                documents,
                contents,
            )

            self.assertEqual(
                panel.archive_status_label.text(),
                "2 archives",
            )
            self.assertEqual(
                panel.extracted_status_label.text(),
                "2 packages",
            )

    def test_discovery_error_hides_metadata_and_recovers_on_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            panel = ImplementationWorkItemPanel()

            with patch(
                "ai_project_organizer.ui.implementation_work_item_panel."
                "discover_implementation_package_archives",
                side_effect=OSError(
                    "permission denied"
                ),
            ):
                panel.set_work_item(
                    "Work Item",
                    documents,
                    contents,
                )

            self.assertIn(
                "permission denied",
                panel.artifact_error_label.text(),
            )
            self.assertTrue(
                panel.archive_metadata_label.isHidden()
            )
            self.assertTrue(
                panel.import_package_button.isEnabled()
            )
            self.assertFalse(
                panel.extract_package_button.isEnabled()
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
                "None",
            )

    def test_clear_work_item_removes_paths_and_stale_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            self._write_valid_archive(
                contents / "package.zip"
            )

            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "Work Item",
                documents,
                contents,
            )
            panel.clear_work_item()

            self.assertIsNone(
                panel.documents_panel.directory_path
            )
            self.assertIsNone(
                panel.contents_path
            )
            self.assertEqual(
                panel.archive_status_label.text(),
                "",
            )
            self.assertFalse(
                panel.import_package_button.isEnabled()
            )
            self.assertFalse(
                panel.extract_package_button.isEnabled()
            )
            self.assertFalse(
                panel.open_contents_button.isEnabled()
            )

    def test_import_dialog_emits_source_and_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "Work Item",
                documents,
                contents,
            )
            emitted = []
            panel.implementation_package_import_requested.connect(
                lambda source, target: emitted.append(
                    (
                        source,
                        target,
                    )
                )
            )

            with patch(
                "ai_project_organizer.ui.implementation_work_item_panel."
                "QFileDialog.getOpenFileName",
                return_value=(
                    "/tmp/package.zip",
                    "ZIP Archives (*.zip)",
                ),
            ):
                panel._request_import()

            self.assertEqual(
                emitted,
                [
                    (
                        "/tmp/package.zip",
                        str(
                            contents
                        ),
                    )
                ],
            )

    def test_import_cancel_emits_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "Work Item",
                documents,
                contents,
            )
            emitted = []
            panel.implementation_package_import_requested.connect(
                lambda *args: emitted.append(
                    args
                )
            )

            with patch(
                "ai_project_organizer.ui.implementation_work_item_panel."
                "QFileDialog.getOpenFileName",
                return_value=(
                    "",
                    "",
                ),
            ):
                panel._request_import()

            self.assertEqual(
                emitted,
                [],
            )

    def test_generic_actions_emit_configured_contents_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "Work Item",
                documents,
                contents,
            )
            extracted = []
            inspected = []
            installed = []
            panel.extract_implementation_package_requested.connect(
                extracted.append
            )
            panel.inspect_implementation_package_requested.connect(
                inspected.append
            )
            panel.install_implementation_package_requested.connect(
                installed.append
            )

            panel._request_extraction()
            panel._request_inspection()
            panel._request_installation()

            expected = [
                str(
                    contents
                )
            ]
            self.assertEqual(
                extracted,
                expected,
            )
            self.assertEqual(
                inspected,
                expected,
            )
            self.assertEqual(
                installed,
                expected,
            )

    def test_open_contents_uses_configured_contents_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "Work Item",
                documents,
                contents,
            )

            with patch(
                "ai_project_organizer.ui.implementation_work_item_panel."
                "QDesktopServices.openUrl",
                return_value=True,
            ) as open_url:
                panel._open_contents()

            open_url.assert_called_once()
            url = open_url.call_args.args[0]
            self.assertEqual(
                Path(
                    url.toLocalFile()
                ),
                contents,
            )

    def test_document_request_is_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents, contents = self._work_item(
                root
            )
            panel = ImplementationWorkItemPanel()
            panel.set_work_item(
                "Work Item",
                documents,
                contents,
            )
            emitted: list[str] = []
            panel.new_document_requested.connect(
                emitted.append
            )

            panel.documents_panel._request_new_document()

            self.assertEqual(
                emitted,
                [
                    str(
                        documents
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()
