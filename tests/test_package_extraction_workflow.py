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

from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMessageBox,
)

from ai_project_organizer.ui.main_window import MainWindow
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    create_project_package,
    initialize_project_workspace_structure,
)


class PackageExtractionWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(
            self.temporary_directory.name
        )
        self.workspace = (
            self.root
            / "workspace"
        )
        self.workspace.mkdir()
        initialize_project_workspace_structure(
            self.workspace
        )
        create_project_feature(
            self.workspace,
            "Feature",
        )
        self.package = create_project_package(
            self.workspace,
            "Feature",
            "PKG01",
        )
        self.contents = (
            self.package
            / "Contents"
        )
        self.window = MainWindow(
            project_registry_path=(
                self.root
                / "projects.json"
            )
        )
        self.window._set_workspace_root(
            str(
                self.workspace
            )
        )

    def tearDown(self) -> None:
        self.window.text_editor.document().setModified(
            False
        )
        self.window.close()
        self.temporary_directory.cleanup()

    def _archive(
            self,
            filename: str,
            package_root: str,
    ) -> Path:
        archive_path = (
            self.contents
            / filename
        )

        with zipfile.ZipFile(
            archive_path,
            "w",
        ) as archive:
            archive.writestr(
                f"{package_root}/Install.py",
                "print('install')",
            )
            archive.writestr(
                f"{package_root}/README.txt",
                (
                    "# SUMMARY\n\n"
                    "Package summary\n\n"
                    "# GIT COMMIT MESSAGE\n\n"
                    "Add package behavior\n"
                ),
            )
            archive.writestr(
                f"{package_root}/Project/file.txt",
                "payload",
            )

        return archive_path

    def test_single_archive_extracts_and_refreshes(self) -> None:
        archive = self._archive(
            "package.zip",
            "PackageRoot",
        )

        with patch.object(
            self.window.project_view,
            "refresh",
        ) as refresh:
            self.window._extract_implementation_package(
                "Feature",
                "PKG01",
            )

        self.assertTrue(
            archive.is_file()
        )
        self.assertTrue(
            (
                self.contents
                / "PackageRoot"
                / "Install.py"
            ).is_file()
        )
        refresh.assert_called_once()

    def test_no_valid_archive_reports_without_mutation(self) -> None:
        (self.contents / "random.zip").write_bytes(
            b"not a package"
        )

        with patch.object(
            QMessageBox,
            "information",
        ) as information:
            self.window._extract_implementation_package(
                "Feature",
                "PKG01",
            )

        information.assert_called_once()
        self.assertEqual(
            [
                path.name
                for path in self.contents.iterdir()
            ],
            [
                "random.zip"
            ],
        )

    def test_multiple_archives_require_selection(self) -> None:
        first = self._archive(
            "first.zip",
            "FirstRoot",
        )
        second = self._archive(
            "second.zip",
            "SecondRoot",
        )

        with patch.object(
            QInputDialog,
            "getItem",
            return_value=(
                second.name,
                True,
            ),
        ):
            self.window._extract_implementation_package(
                "Feature",
                "PKG01",
            )

        self.assertFalse(
            (
                self.contents
                / "FirstRoot"
            ).exists()
        )
        self.assertTrue(
            (
                self.contents
                / "SecondRoot"
            ).is_dir()
        )
        self.assertTrue(
            first.is_file()
        )
        self.assertTrue(
            second.is_file()
        )

    def test_inspection_requires_extraction(self) -> None:
        self._archive(
            "package.zip",
            "PackageRoot",
        )

        with patch.object(
            QMessageBox,
            "information",
        ) as information:
            self.window._inspect_implementation_package(
                "Feature",
                "PKG01",
            )

        information.assert_called_once()
        self.assertIn(
            "has not been extracted",
            information.call_args.args[2].lower(),
        )

    def test_extraction_does_not_change_modified_editor(self) -> None:
        document = (
            self.workspace
            / "Documents"
            / "note.txt"
        )
        document.write_text(
            "original",
            encoding="utf-8",
        )
        self.window._open_file_path(
            document
        )
        self.window.text_editor.setPlainText(
            "modified"
        )
        self.window.text_editor.document().setModified(
            True
        )
        self._archive(
            "package.zip",
            "PackageRoot",
        )

        self.window._extract_implementation_package(
            "Feature",
            "PKG01",
        )

        self.assertEqual(
            self.window.current_file_path,
            str(
                document
            ),
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
