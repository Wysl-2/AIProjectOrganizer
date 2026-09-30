from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtGui import QCloseEvent, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai_project_organizer.implementation_package import (
    ExtractedImplementationPackage,
)
from ai_project_organizer.ui.section_panel import (
    SectionPanel,
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

        self.package_title_label = QLabel(
            package_id,
            self,
        )
        self.package_title_label.setProperty(
            "role",
            "pageTitle",
        )

        self.installer_metadata_label = QLabel(
            "Installer",
            self,
        )
        self.installer_metadata_label.setProperty(
            "role",
            "metadataLabel",
        )
        self.installer_value_label = QLabel(
            str(extracted_package.install_script_path),
            self,
        )
        self.installer_value_label.setWordWrap(
            True
        )

        self.target_metadata_label = QLabel(
            "Target",
            self,
        )
        self.target_metadata_label.setProperty(
            "role",
            "metadataLabel",
        )
        self.target_value_label = QLabel(
            str(self.target_project_path),
            self,
        )
        self.target_value_label.setWordWrap(
            True
        )

        self.status_metadata_label = QLabel(
            "Status",
            self,
        )
        self.status_metadata_label.setProperty(
            "role",
            "metadataLabel",
        )
        self.status_label = QLabel(
            "Ready",
            self,
        )
        self.status_label.setProperty(
            "role",
            "secondary",
        )

        metadata_layout = QGridLayout()
        metadata_layout.setColumnStretch(
            1,
            1,
        )
        metadata_layout.addWidget(
            self.installer_metadata_label,
            0,
            0,
        )
        metadata_layout.addWidget(
            self.installer_value_label,
            0,
            1,
        )
        metadata_layout.addWidget(
            self.target_metadata_label,
            1,
            0,
        )
        metadata_layout.addWidget(
            self.target_value_label,
            1,
            1,
        )
        metadata_layout.addWidget(
            self.status_metadata_label,
            2,
            0,
        )
        metadata_layout.addWidget(
            self.status_label,
            2,
            1,
        )

        self.output_panel = SectionPanel(
            "INSTALLER OUTPUT",
            self,
        )
        self.output_edit = QPlainTextEdit(
            self.output_panel
        )
        self.output_edit.setProperty(
            "role",
            "consoleOutput",
        )
        self.output_edit.setReadOnly(
            True
        )
        self.output_panel.content_layout.addWidget(
            self.output_edit,
            1,
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
            self.package_title_label
        )
        layout.addLayout(
            metadata_layout
        )
        layout.addWidget(
            self.output_panel,
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

    def _set_status(
            self,
            text: str,
            role: str = "secondary",
    ) -> None:
        self.status_label.setText(
            text
        )
        self.status_label.setProperty(
            "role",
            role,
        )

        style = self.status_label.style()
        style.unpolish(
            self.status_label
        )
        style.polish(
            self.status_label
        )
        self.status_label.update()

    def start_installation(self) -> None:
        if self._started:
            return

        self._started = True
        self._running = True
        self._set_status(
            "Starting installer"
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
        self._set_status(
            "Running"
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
            self._set_status(
                "Unable to start installer",
                "error",
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
            self._set_status(
                "Installer terminated unexpectedly",
                "error",
            )
        elif exit_code == 0:
            self._set_status(
                "Installation completed successfully"
            )
        else:
            self._set_status(
                (
                    "Installation failed with "
                    f"exit code {exit_code}"
                ),
                "error",
            )

        self.close_button.setEnabled(
            True
        )
