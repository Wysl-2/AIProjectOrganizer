import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication, QMessageBox

from ai_project_organizer.implementation_package import (
    ImplementationPackageError,
    inspect_extracted_implementation_package,
)
from ai_project_organizer.project import (
    PROJECT_METADATA_FILENAME,
    ProjectMetadata,
    save_project_metadata,
)
from ai_project_organizer.ui.main_window import MainWindow
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    create_project_package,
    initialize_project_workspace_structure,
)


class PackageInstallWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(
            self.temporary_directory.name
        )
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        initialize_project_workspace_structure(
            self.workspace
        )

        self.working_directory = self.root / "working"
        self.working_directory.mkdir()
        self.target_a = self.root / "target-a"
        self.target_a.mkdir()
        self.target_b = self.root / "target-b"
        self.target_b.mkdir()

        self._save_metadata(
            self.target_a
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
        self.contents = self.package / "Contents"
        self.extracted = self._create_extracted_package(
            "PackageRoot"
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

    def _save_metadata(
            self,
            target: Path,
    ) -> None:
        save_project_metadata(
            self.workspace,
            ProjectMetadata(
                name="Example Project",
                working_directory=self.working_directory,
                local_git_repository=target,
                github_repository="owner/repository",
            ),
        )

    def _create_extracted_package(
            self,
            root_name: str,
    ):
        package_root = self.contents / root_name
        package_root.mkdir()
        install_script = package_root / "Install.py"
        install_script.write_text(
            "print('install')\n",
            encoding="utf-8",
        )
        readme_path = package_root / "README.txt"
        readme_path.write_text(
            "# SUMMARY\n\nExample\n",
            encoding="utf-8",
        )
        project_payload = package_root / "Project"
        project_payload.mkdir()

        return inspect_extracted_implementation_package(
            package_root
        )

    def _run_with_dialog_mock(
            self,
            *,
            preferred_root_name: str | None = None,
    ):
        with (
            patch.object(
                self.window,
                "_confirm_implementation_package_installation",
                return_value=True,
            ),
            patch(
                "ai_project_organizer.ui.main_window.QStandardPaths.findExecutable",
                return_value=sys.executable,
            ),
            patch(
                "ai_project_organizer.ui.main_window.PackageInstallDialog"
            ) as dialog_class,
        ):
            self.window._install_implementation_package(
                "Feature",
                "PKG01",
                preferred_root_name=preferred_root_name,
            )

        return dialog_class

    def test_install_uses_validated_package_and_configured_target(self) -> None:
        dialog_class = self._run_with_dialog_mock()

        dialog_class.assert_called_once()
        call = dialog_class.call_args
        self.assertEqual(
            call.args[0],
            "PKG01",
        )
        self.assertEqual(
            call.args[1].root_path,
            self.extracted.root_path,
        )
        self.assertEqual(
            call.args[2],
            self.target_a,
        )
        self.assertEqual(
            call.args[3],
            sys.executable,
        )

        dialog = dialog_class.return_value
        dialog.start_installation.assert_called_once()
        dialog.exec.assert_called_once()

    def test_fresh_metadata_is_used_instead_of_cached_target(self) -> None:
        self._save_metadata(
            self.target_b
        )

        dialog_class = self._run_with_dialog_mock()

        self.assertEqual(
            dialog_class.call_args.args[2],
            self.target_b,
        )

    def test_unsaved_metadata_document_blocks_installation(self) -> None:
        metadata_path = (
            self.workspace
            / PROJECT_METADATA_FILENAME
        )
        self.window.current_file_path = str(
            metadata_path
        )
        self.window.text_editor.setPlainText(
            "unsaved metadata"
        )
        self.window.text_editor.document().setModified(
            True
        )

        with (
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
            patch(
                "ai_project_organizer.ui.main_window.PackageInstallDialog"
            ) as dialog_class,
        ):
            self.window._install_implementation_package(
                "Feature",
                "PKG01",
            )

        dialog_class.assert_not_called()
        self.assertTrue(
            self.window.text_editor.document().isModified()
        )
        self.assertEqual(
            warning.call_args.args[1],
            "Project Metadata Has Unsaved Changes",
        )

    def test_no_extracted_package_requires_extraction(self) -> None:
        for child in list(
            self.contents.iterdir()
        ):
            if child.is_dir():
                import shutil
                shutil.rmtree(
                    child
                )

        archive_path = self.contents / "package.zip"

        with zipfile.ZipFile(
            archive_path,
            "w",
        ) as archive:
            archive.writestr(
                "PackageRoot/Install.py",
                "install",
            )
            archive.writestr(
                "PackageRoot/README.txt",
                "readme",
            )
            archive.writestr(
                "PackageRoot/Project/file.txt",
                "payload",
            )

        with patch.object(
            QMessageBox,
            "information",
        ) as information:
            self.window._install_implementation_package(
                "Feature",
                "PKG01",
            )

        self.assertEqual(
            information.call_args.args[1],
            "Implementation Package Not Extracted",
        )

    def test_multiple_packages_allow_explicit_selection(self) -> None:
        second = self._create_extracted_package(
            "SecondRoot"
        )

        with (
            patch(
                "ai_project_organizer.ui.main_window.QInputDialog.getItem",
                return_value=(
                    second.root_path.name,
                    True,
                ),
            ),
            patch.object(
                self.window,
                "_confirm_implementation_package_installation",
                return_value=True,
            ),
            patch(
                "ai_project_organizer.ui.main_window.QStandardPaths.findExecutable",
                return_value=sys.executable,
            ),
            patch(
                "ai_project_organizer.ui.main_window.PackageInstallDialog"
            ) as dialog_class,
        ):
            self.window._install_implementation_package(
                "Feature",
                "PKG01",
            )

        self.assertEqual(
            dialog_class.call_args.args[1].root_path,
            second.root_path,
        )

    def test_missing_preferred_root_does_not_fall_back(self) -> None:
        with (
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
            patch(
                "ai_project_organizer.ui.main_window.PackageInstallDialog"
            ) as dialog_class,
        ):
            self.window._install_implementation_package(
                "Feature",
                "PKG01",
                preferred_root_name="MissingRoot",
            )

        dialog_class.assert_not_called()
        self.assertEqual(
            warning.call_args.args[1],
            "Implementation Package Unavailable",
        )

    def test_python_unavailable_blocks_process_launch(self) -> None:
        with (
            patch.object(
                self.window,
                "_confirm_implementation_package_installation",
                return_value=True,
            ),
            patch(
                "ai_project_organizer.ui.main_window.QStandardPaths.findExecutable",
                return_value="",
            ),
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
            patch(
                "ai_project_organizer.ui.main_window.PackageInstallDialog"
            ) as dialog_class,
        ):
            self.window._install_implementation_package(
                "Feature",
                "PKG01",
            )

        dialog_class.assert_not_called()
        self.assertEqual(
            warning.call_args.args[1],
            "Python 3 Unavailable",
        )

    def test_target_disappearing_after_confirmation_blocks_launch(self) -> None:
        def confirm_and_remove(
                _package_id,
                _extracted_package,
                target_path,
        ) -> bool:
            target_path.rmdir()
            return True

        with (
            patch.object(
                self.window,
                "_confirm_implementation_package_installation",
                side_effect=confirm_and_remove,
            ),
            patch(
                "ai_project_organizer.ui.main_window.QStandardPaths.findExecutable",
                return_value=sys.executable,
            ),
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
            patch(
                "ai_project_organizer.ui.main_window.PackageInstallDialog"
            ) as dialog_class,
        ):
            self.window._install_implementation_package(
                "Feature",
                "PKG01",
            )

        dialog_class.assert_not_called()
        self.assertEqual(
            warning.call_args.args[1],
            "Configured Local Repository Unavailable",
        )

    def test_package_change_after_confirmation_blocks_launch(self) -> None:
        valid_package = self.extracted

        with (
            patch.object(
                self.window,
                "_confirm_implementation_package_installation",
                return_value=True,
            ),
            patch(
                "ai_project_organizer.ui.main_window.QStandardPaths.findExecutable",
                return_value=sys.executable,
            ),
            patch(
                "ai_project_organizer.ui.main_window.inspect_extracted_implementation_package",
                side_effect=(
                    valid_package,
                    ImplementationPackageError(
                        "changed"
                    ),
                ),
            ),
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
            patch(
                "ai_project_organizer.ui.main_window.PackageInstallDialog"
            ) as dialog_class,
        ):
            self.window._install_implementation_package(
                "Feature",
                "PKG01",
            )

        dialog_class.assert_not_called()
        self.assertEqual(
            warning.call_args.args[1],
            "Implementation Package Changed",
        )

    def test_ordinary_modified_document_is_not_changed_by_install_coordination(
            self,
    ) -> None:
        document = self.workspace / "Documents" / "note.txt"
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

        self._run_with_dialog_mock()

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
