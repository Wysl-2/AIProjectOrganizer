import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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


class PackageImportWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        initialize_project_workspace_structure(self.workspace)
        self.feature = create_project_feature(
            self.workspace,
            "Feature",
        )
        self.window = MainWindow(
            project_registry_path=self.root / "projects.json"
        )
        self.window._set_workspace_root(str(self.workspace))

    def tearDown(self) -> None:
        self.window.text_editor.document().setModified(False)
        self.window.close()
        self.temporary_directory.cleanup()

    def _archive(
            self,
            filename: str,
            root_name: str,
    ) -> Path:
        archive_path = self.root / filename
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(
                f"{root_name}/Install.py",
                "install",
            )
            archive.writestr(
                f"{root_name}/README.txt",
                "readme",
            )
            archive.writestr(
                f"{root_name}/Project/file.txt",
                "file",
            )
        return archive_path

    def test_feature_import_creates_inferred_package(self) -> None:
        source = self._archive(
            "archive.zip",
            "Example_FI03_Package",
        )
        self.window._import_implementation_package(
            str(source),
            "Feature",
            "",
        )
        package = self.feature / "Packages" / "FI03"
        self.assertTrue((package / "Documents").is_dir())
        self.assertTrue(
            (package / "Contents" / source.name).is_file()
        )
        self.assertTrue(source.is_file())

    def test_feature_import_reuses_existing_package(self) -> None:
        package = create_project_package(
            self.workspace,
            "Feature",
            "FI03",
        )
        source = self._archive(
            "archive.zip",
            "Example_FI03_Package",
        )
        self.window._import_implementation_package(
            str(source),
            "Feature",
            "",
        )
        self.assertTrue(
            (package / "Contents" / source.name).is_file()
        )

    def test_ambiguous_id_prompts_and_cancel_is_safe(self) -> None:
        source = self._archive(
            "archive.zip",
            "ExamplePackage",
        )
        with patch.object(
            QInputDialog,
            "getText",
            return_value=("FI03", True),
        ):
            self.window._import_implementation_package(
                str(source),
                "Feature",
                "",
            )
        self.assertTrue(
            (
                self.feature
                / "Packages"
                / "FI03"
                / "Contents"
                / source.name
            ).is_file()
        )

        other = self._archive(
            "other.zip",
            "AnotherPackage",
        )
        with patch.object(
            QInputDialog,
            "getText",
            return_value=("", False),
        ):
            self.window._import_implementation_package(
                str(other),
                "Feature",
                "",
            )
        self.assertFalse(
            (
                self.feature
                / "Packages"
                / "other"
            ).exists()
        )

    def test_invalid_archive_creates_no_package(self) -> None:
        source = self.root / "invalid.zip"
        source.write_bytes(b"not a zip")
        with patch.object(QMessageBox, "warning") as warning:
            self.window._import_implementation_package(
                str(source),
                "Feature",
                "",
            )
        self.assertEqual(
            [
                path.name
                for path in (self.feature / "Packages").iterdir()
            ],
            [],
        )
        warning.assert_called_once()

    def test_direct_package_import_and_mismatch_confirmation(self) -> None:
        package = create_project_package(
            self.workspace,
            "Feature",
            "FI03",
        )
        source = self._archive(
            "archive.zip",
            "ExamplePackage",
        )
        with patch.object(QInputDialog, "getText") as get_text:
            self.window._import_implementation_package(
                str(source),
                "Feature",
                "FI03",
            )
        get_text.assert_not_called()
        self.assertTrue(
            (package / "Contents" / source.name).is_file()
        )

        mismatch = self._archive(
            "mismatch.zip",
            "Example_FI04_Package",
        )
        with patch.object(
            QMessageBox,
            "exec",
            return_value=QMessageBox.StandardButton.No,
        ):
            self.window._import_implementation_package(
                str(mismatch),
                "Feature",
                "FI03",
            )
        self.assertFalse(
            (package / "Contents" / mismatch.name).exists()
        )

    def test_collision_and_editor_state_are_preserved(self) -> None:
        package = create_project_package(
            self.workspace,
            "Feature",
            "FI03",
        )
        source = self._archive(
            "archive.zip",
            "Example_FI03_Package",
        )
        destination = package / "Contents" / source.name
        destination.write_bytes(b"existing")

        document = self.workspace / "Documents" / "note.txt"
        document.write_text("original", encoding="utf-8")
        self.window._open_file_path(document)
        self.window.text_editor.setPlainText("modified")
        self.window.text_editor.document().setModified(True)

        with patch.object(QMessageBox, "warning") as warning:
            self.window._import_implementation_package(
                str(source),
                "Feature",
                "FI03",
            )

        self.assertEqual(destination.read_bytes(), b"existing")
        self.assertTrue(source.is_file())
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
        warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
