import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication

from ai_project_organizer.implementation_package import (
    ExtractedImplementationPackage,
)
from ai_project_organizer.ui.package_install_dialog import (
    PackageInstallDialog,
)


class PackageInstallDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _package(
            self,
            root: Path,
            source: str,
    ) -> ExtractedImplementationPackage:
        package_root = root / "PackageRoot"
        package_root.mkdir()
        install_script = package_root / "Install.py"
        install_script.write_text(
            source,
            encoding="utf-8",
        )
        readme = package_root / "README.txt"
        readme.write_text(
            "readme",
            encoding="utf-8",
        )
        project_payload = package_root / "Project"
        project_payload.mkdir()

        return ExtractedImplementationPackage(
            root_path=package_root,
            install_script_path=install_script,
            readme_path=readme,
            project_payload_path=project_payload,
        )

    def _wait_for_process(
            self,
            dialog: PackageInstallDialog,
            timeout: float = 4.0,
    ) -> None:
        deadline = time.monotonic() + timeout

        while (
                dialog.is_running
                and time.monotonic() < deadline
        ):
            QApplication.processEvents()
            time.sleep(
                0.01
            )

        QApplication.processEvents()
        self.assertFalse(
            dialog.is_running
        )

    def test_dialog_uses_structured_install_presentation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            extracted = self._package(
                root,
                "print('unused')\n",
            )

            dialog = PackageInstallDialog(
                "PKG01",
                extracted,
                target,
                sys.executable,
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
                dialog.installer_metadata_label.property(
                    "role"
                ),
                "metadataLabel",
            )
            self.assertEqual(
                dialog.target_metadata_label.property(
                    "role"
                ),
                "metadataLabel",
            )
            self.assertEqual(
                dialog.status_metadata_label.property(
                    "role"
                ),
                "metadataLabel",
            )
            self.assertEqual(
                dialog.status_label.text(),
                "Ready",
            )
            self.assertEqual(
                dialog.status_label.property(
                    "role"
                ),
                "secondary",
            )
            self.assertEqual(
                dialog.output_panel.title_label.text(),
                "INSTALLER OUTPUT",
            )
            self.assertEqual(
                dialog.output_edit.property(
                    "role"
                ),
                "consoleOutput",
            )

            dialog.close()

    def test_success_streams_output_and_uses_separate_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            extracted = self._package(
                root,
                (
                    "import sys\n"
                    "print('stdout text', flush=True)\n"
                    "print('stderr text', file=sys.stderr, flush=True)\n"
                ),
            )

            dialog = PackageInstallDialog(
                "PKG01",
                extracted,
                target,
                sys.executable,
            )
            dialog.start_installation()

            self.assertEqual(
                dialog.process.program(),
                sys.executable,
            )
            self.assertEqual(
                dialog.process.arguments(),
                [
                    str(
                        extracted.install_script_path.absolute()
                    ),
                    str(
                        target.absolute()
                    ),
                ],
            )

            self._wait_for_process(
                dialog
            )

            output = dialog.output_edit.toPlainText()

            self.assertIn(
                "stdout text",
                output,
            )
            self.assertIn(
                "[stderr] stderr text",
                output,
            )
            self.assertIn(
                "completed successfully",
                dialog.status_label.text().lower(),
            )
            self.assertEqual(
                dialog.status_label.property(
                    "role"
                ),
                "secondary",
            )
            self.assertTrue(
                dialog.close_button.isEnabled()
            )

    def test_nonzero_exit_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            extracted = self._package(
                root,
                "raise SystemExit(3)\n",
            )

            dialog = PackageInstallDialog(
                "PKG01",
                extracted,
                target,
                sys.executable,
            )
            dialog.start_installation()
            self._wait_for_process(
                dialog
            )

            self.assertIn(
                "exit code 3",
                dialog.status_label.text().lower(),
            )
            self.assertEqual(
                dialog.status_label.property(
                    "role"
                ),
                "error",
            )

    def test_failed_start_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            extracted = self._package(
                root,
                "print('unused')\n",
            )

            dialog = PackageInstallDialog(
                "PKG01",
                extracted,
                target,
                "/definitely/not/a/python/executable",
            )
            dialog.start_installation()
            self._wait_for_process(
                dialog
            )

            self.assertIn(
                "unable to start",
                dialog.status_label.text().lower(),
            )
            self.assertEqual(
                dialog.status_label.property(
                    "role"
                ),
                "error",
            )
            self.assertTrue(
                dialog.close_button.isEnabled()
            )

    def test_crash_exit_uses_error_presentation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            extracted = self._package(
                root,
                "print('unused')\n",
            )

            dialog = PackageInstallDialog(
                "PKG01",
                extracted,
                target,
                sys.executable,
            )
            dialog._process_finished(
                1,
                QProcess.ExitStatus.CrashExit,
            )

            self.assertIn(
                "terminated unexpectedly",
                dialog.status_label.text().lower(),
            )
            self.assertEqual(
                dialog.status_label.property(
                    "role"
                ),
                "error",
            )

            dialog.close()

    def test_close_is_disabled_while_running(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            extracted = self._package(
                root,
                (
                    "import time\n"
                    "time.sleep(0.2)\n"
                ),
            )

            dialog = PackageInstallDialog(
                "PKG01",
                extracted,
                target,
                sys.executable,
            )
            dialog.start_installation()

            self.assertFalse(
                dialog.close_button.isEnabled()
            )

            self._wait_for_process(
                dialog
            )

            self.assertTrue(
                dialog.close_button.isEnabled()
            )

    def test_duplicate_start_runs_installer_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            marker = target / "marker.txt"
            extracted = self._package(
                root,
                (
                    "from pathlib import Path\n"
                    "import sys\n"
                    "marker = Path(sys.argv[1]) / 'marker.txt'\n"
                    "with marker.open('a', encoding='utf-8') as stream:\n"
                    "    stream.write('x')\n"
                ),
            )

            dialog = PackageInstallDialog(
                "PKG01",
                extracted,
                target,
                sys.executable,
            )
            dialog.start_installation()
            dialog.start_installation()
            self._wait_for_process(
                dialog
            )

            self.assertEqual(
                marker.read_text(
                    encoding="utf-8"
                ),
                "x",
            )

    def test_invalid_utf8_output_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            extracted = self._package(
                root,
                (
                    "import sys\n"
                    "sys.stdout.buffer.write(b'\\xff')\n"
                    "sys.stdout.buffer.flush()\n"
                ),
            )

            dialog = PackageInstallDialog(
                "PKG01",
                extracted,
                target,
                sys.executable,
            )
            dialog.start_installation()
            self._wait_for_process(
                dialog
            )

            self.assertIn(
                "\ufffd",
                dialog.output_edit.toPlainText(),
            )


if __name__ == "__main__":
    unittest.main()
