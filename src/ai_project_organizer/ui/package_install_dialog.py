from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtGui import QCloseEvent, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai_project_organizer.implementation_package import (
    ExtractedImplementationPackage,
)


class PackageInstallDialog(QDialog):
    def __init__(
            self,
            package_id: str,
            extracted_package: ExtractedImplementationPackage,
            target_project_path: str | Path,
            python_program: str,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent
        )

        self.package_id = package_id
        self.extracted_package = extracted_package
        self.target_project_path = Path(
            target_project_path
        ).expanduser().absolute()
        self.python_program = python_program

        self._started = False
        self._running = False

        self.setWindowTitle(
            f"Install Package - {package_id}"
        )
        self.resize(
            760,
            560,
        )

        package_label = QLabel(
            f"Package: {package_id}",
            self,
        )
        installer_label = QLabel(
            (
                "Installer: "
                f"{extracted_package.install_script_path}"
            ),
            self,
        )
        installer_label.setWordWrap(
            True
        )
        target_label = QLabel(
            (
                "Target: "
                f"{self.target_project_path}"
            ),
            self,
        )
        target_label.setWordWrap(
            True
        )

        self.status_label = QLabel(
            "Status: Ready",
            self,
        )

        self.output_edit = QPlainTextEdit(
            self
        )
        self.output_edit.setReadOnly(
            True
        )

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        self.close_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Close
        )
        self.button_box.rejected.connect(
            self.reject
        )

        layout = QVBoxLayout(
            self
        )
        layout.addWidget(
            package_label
        )
        layout.addWidget(
            installer_label
        )
        layout.addWidget(
            target_label
        )
        layout.addWidget(
            self.status_label
        )
        layout.addWidget(
            self.output_edit,
            1,
        )
        layout.addWidget(
            self.button_box
        )

        self.process = QProcess(
            self
        )
        self.process.started.connect(
            self._process_started
        )
        self.process.readyReadStandardOutput.connect(
            self._read_standard_output
        )
        self.process.readyReadStandardError.connect(
            self._read_standard_error
        )
        self.process.errorOccurred.connect(
            self._process_error
        )
        self.process.finished.connect(
            self._process_finished
        )

    @property
    def is_running(self) -> bool:
        return self._running

    def start_installation(self) -> None:
        if self._started:
            return

        self._started = True
        self._running = True
        self.status_label.setText(
            "Status: Starting installer"
        )
        self.close_button.setEnabled(
            False
        )

        install_script = (
            self.extracted_package
            .install_script_path
            .expanduser()
            .absolute()
        )
        package_root = (
            self.extracted_package
            .root_path
            .expanduser()
            .absolute()
        )

        self.process.setProgram(
            self.python_program
        )
        self.process.setArguments(
            [
                str(
                    install_script
                ),
                str(
                    self.target_project_path
                ),
            ]
        )
        self.process.setWorkingDirectory(
            str(
                package_root
            )
        )
        self.process.start()

    def reject(self) -> None:
        if self._running:
            return

        super().reject()

    def closeEvent(
            self,
            event: QCloseEvent,
    ) -> None:
        if self._running:
            event.ignore()
            return

        super().closeEvent(
            event
        )

    def _process_started(self) -> None:
        self.status_label.setText(
            "Status: Running"
        )

    def _read_standard_output(self) -> None:
        data = bytes(
            self.process.readAllStandardOutput()
        )

        if not data:
            return

        self._append_output(
            data.decode(
                "utf-8",
                errors="replace",
            )
        )

    def _read_standard_error(self) -> None:
        data = bytes(
            self.process.readAllStandardError()
        )

        if not data:
            return

        self._append_output(
            "[stderr] "
            + data.decode(
                "utf-8",
                errors="replace",
            )
        )

    def _append_output(
            self,
            text: str,
    ) -> None:
        if not text:
            return

        scroll_bar = (
            self.output_edit
            .verticalScrollBar()
        )
        follow_output = (
            scroll_bar.value()
            >= scroll_bar.maximum() - 2
        )

        cursor = self.output_edit.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.End
        )
        cursor.insertText(
            text
        )
        self.output_edit.setTextCursor(
            cursor
        )

        if follow_output:
            self.output_edit.ensureCursorVisible()

    def _process_error(
            self,
            error: QProcess.ProcessError,
    ) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._running = False
            self.status_label.setText(
                "Status: Unable to start installer"
            )

            error_text = self.process.errorString()

            if error_text:
                self._append_output(
                    f"[process] {error_text}\n"
                )

            self.close_button.setEnabled(
                True
            )
            return

        error_text = self.process.errorString()

        if error_text:
            self._append_output(
                f"[process] {error_text}\n"
            )

    def _process_finished(
            self,
            exit_code: int,
            exit_status: QProcess.ExitStatus,
    ) -> None:
        self._read_standard_output()
        self._read_standard_error()

        self._running = False

        if exit_status == QProcess.ExitStatus.CrashExit:
            self.status_label.setText(
                "Status: Installer terminated unexpectedly"
            )
        elif exit_code == 0:
            self.status_label.setText(
                "Status: Installation completed successfully"
            )
        else:
            self.status_label.setText(
                (
                    "Status: Installation failed with "
                    f"exit code {exit_code}"
                )
            )

        self.close_button.setEnabled(
            True
        )
