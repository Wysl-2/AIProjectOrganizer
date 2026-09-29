import os
import tempfile
import unittest
from pathlib import Path
os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication, QDialog

from ai_project_organizer.implementation_package import (
    ExtractedImplementationPackage,
    ImplementationPackageReadme,
)
from ai_project_organizer.ui.package_inspector_dialog import (
    PackageInspectorDialog,
)
from ai_project_organizer.ui.project_view import ProjectView
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    create_project_package,
    initialize_project_workspace_structure,
)


class PackageInstallUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def _write_extracted_package(
            contents: Path,
            root_name: str,
    ) -> None:
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

    def test_project_view_install_button_emits_package_context(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = root / "workspace"
            workspace.mkdir()
            initialize_project_workspace_structure(
                workspace
            )
            create_project_feature(
                workspace,
                "Feature",
            )
            package = create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )
            self._write_extracted_package(
                package / "Contents",
                "PackageRoot",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            view._open_feature(
                "Feature"
            )

            panel = view.package_workspace_panel
            panel.package_list.setCurrentRow(
                0
            )
            QApplication.processEvents()

            self.assertTrue(
                panel.install_package_button.isEnabled()
            )

            emitted = []
            view.install_implementation_package_requested.connect(
                lambda feature_name, package_id: emitted.append(
                    (
                        feature_name,
                        package_id,
                    )
                )
            )

            panel.install_package_button.click()

            self.assertEqual(
                emitted,
                [
                    (
                        "Feature",
                        "PKG01",
                    )
                ],
            )

    def test_inspector_install_request_emits_root_name_and_closes(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            package_root = root / "PackageRoot"
            package_root.mkdir()
            install_script = package_root / "Install.py"
            install_script.write_text(
                "install",
                encoding="utf-8",
            )
            readme_path = package_root / "README.txt"
            readme_path.write_text(
                "readme",
                encoding="utf-8",
            )
            project_payload = package_root / "Project"
            project_payload.mkdir()
            contents = root / "Contents"
            contents.mkdir()

            extracted = ExtractedImplementationPackage(
                root_path=package_root,
                install_script_path=install_script,
                readme_path=readme_path,
                project_payload_path=project_payload,
            )
            readme = ImplementationPackageReadme(
                installation="",
                summary="Summary",
                implementation_details="",
                files_changed="",
                manual_follow_up="",
                testing_validation="",
                git_commit_message="",
            )

            dialog = PackageInspectorDialog(
                "PKG01",
                extracted,
                readme,
                contents,
            )
            emitted: list[str] = []
            dialog.install_requested.connect(
                emitted.append
            )

            dialog._request_install()

            self.assertEqual(
                emitted,
                [
                    "PackageRoot"
                ],
            )
            self.assertEqual(
                dialog.result(),
                QDialog.DialogCode.Accepted,
            )


if __name__ == "__main__":
    unittest.main()
