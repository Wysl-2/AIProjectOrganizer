import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from ai_project_organizer.implementation_package import (
    ExtractedImplementationPackage,
    ImplementationPackageReadme,
)
from ai_project_organizer.ui.package_inspector_dialog import (
    PackageInspectorDialog,
)


class PackageInspectorDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _data(
            self,
            root: Path,
            commit_message: str = "Add inspection",
    ) -> tuple[
        ExtractedImplementationPackage,
        ImplementationPackageReadme,
        Path,
    ]:
        package_root = root / "PackageRoot"
        package_root.mkdir()
        install_script = package_root / "Install.py"
        readme_path = package_root / "README.txt"
        project_payload = package_root / "Project"
        install_script.write_text(
            "install",
            encoding="utf-8",
        )
        readme_path.write_text(
            "readme",
            encoding="utf-8",
        )
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
            installation="Install",
            summary="Summary",
            implementation_details="Details",
            files_changed="file.py",
            manual_follow_up="None.",
            testing_validation="Run tests",
            git_commit_message=commit_message,
        )

        return (
            extracted,
            readme,
            contents,
        )

    def test_dialog_presents_package_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            extracted, readme, contents = self._data(
                root
            )

            dialog = PackageInspectorDialog(
                "PKG01",
                extracted,
                readme,
                contents,
            )

            review = dialog.review_edit.toPlainText()

            self.assertIn(
                "SUMMARY",
                review,
            )
            self.assertIn(
                "Summary",
                review,
            )
            self.assertIn(
                "FILES CHANGED",
                review,
            )
            self.assertTrue(
                dialog.copy_commit_button.isEnabled()
            )
            self.assertEqual(
                dialog.package_title_label.text(),
                "PKG01",
            )
            self.assertEqual(
                dialog.package_title_label.property(
                    "role"
                ),
                "pageTitle",
            )
            self.assertEqual(
                dialog.root_metadata_label.property(
                    "role"
                ),
                "metadataLabel",
            )
            self.assertEqual(
                dialog.state_metadata_label.property(
                    "role"
                ),
                "metadataLabel",
            )
            self.assertEqual(
                dialog.review_panel.title_label.text(),
                "PACKAGE REVIEW",
            )
            self.assertEqual(
                dialog.open_readme_button.property(
                    "role"
                ),
                "toolbar",
            )
            self.assertEqual(
                dialog.open_contents_button.property(
                    "role"
                ),
                "toolbar",
            )
            self.assertFalse(
                dialog.open_contents_button.icon().isNull()
            )
            self.assertEqual(
                dialog.copy_commit_button.property(
                    "role"
                ),
                "toolbar",
            )
            self.assertEqual(
                dialog.install_button.property(
                    "role"
                ),
                "primary",
            )
            self.assertFalse(
                dialog.install_button.icon().isNull()
            )

    def test_copy_commit_message_uses_exact_parsed_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            commit_message = (
                "Add inspection\n\n"
                "- inspect package"
            )
            extracted, readme, contents = self._data(
                root,
                commit_message=commit_message,
            )

            dialog = PackageInspectorDialog(
                "PKG01",
                extracted,
                readme,
                contents,
            )
            dialog._copy_git_commit_message()

            self.assertEqual(
                QApplication.clipboard().text(),
                commit_message,
            )

    def test_missing_commit_message_disables_copy_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            extracted, readme, contents = self._data(
                root,
                commit_message="",
            )

            dialog = PackageInspectorDialog(
                "PKG01",
                extracted,
                readme,
                contents,
            )

            self.assertFalse(
                dialog.copy_commit_button.isEnabled()
            )

    def test_open_actions_emit_real_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            extracted, readme, contents = self._data(
                root
            )

            dialog = PackageInspectorDialog(
                "PKG01",
                extracted,
                readme,
                contents,
            )

            readme_requests: list[str] = []
            contents_requests: list[str] = []

            dialog.open_readme_requested.connect(
                readme_requests.append
            )
            dialog.open_contents_requested.connect(
                contents_requests.append
            )

            dialog._request_open_readme()

            self.assertEqual(
                readme_requests,
                [
                    str(
                        extracted.readme_path
                    )
                ],
            )

            dialog._request_open_contents()

            self.assertEqual(
                contents_requests,
                [
                    str(
                        contents
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()
