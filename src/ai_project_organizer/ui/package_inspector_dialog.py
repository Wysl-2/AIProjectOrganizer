from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ai_project_organizer.implementation_package import (
    ExtractedImplementationPackage,
    ImplementationPackageReadme,
)


class PackageInspectorDialog(QDialog):
    open_readme_requested = Signal(str)
    open_contents_requested = Signal(str)
    install_requested = Signal(str)

    def __init__(
            self,
            package_id: str,
            extracted_package: ExtractedImplementationPackage,
            readme: ImplementationPackageReadme,
            contents_path: str | Path,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent
        )

        self.extracted_package = extracted_package
        self.readme = readme
        self.contents_path = Path(
            contents_path
        )

        self.setWindowTitle(
            f"Inspect Package - {package_id}"
        )
        self.resize(
            720,
            620,
        )

        package_label = QLabel(
            f"Package: {package_id}",
            self,
        )
        root_label = QLabel(
            (
                "Extracted Root: "
                f"{extracted_package.root_path.name}"
            ),
            self,
        )
        state_label = QLabel(
            "State: Extracted",
            self,
        )

        self.review_edit = QPlainTextEdit(
            self
        )
        self.review_edit.setReadOnly(
            True
        )
        self.review_edit.setPlainText(
            self._review_text()
        )

        self.open_readme_button = QPushButton(
            "Open README",
            self,
        )
        self.open_contents_button = QPushButton(
            "Open Contents",
            self,
        )
        self.copy_commit_button = QPushButton(
            "Copy Git Commit Message",
            self,
        )
        self.install_button = QPushButton(
            "Install Package",
            self,
        )
        self.copy_commit_button.setEnabled(
            bool(
                self.readme.git_commit_message
            )
        )

        self.open_readme_button.clicked.connect(
            self._request_open_readme
        )
        self.open_contents_button.clicked.connect(
            self._request_open_contents
        )
        self.copy_commit_button.clicked.connect(
            self._copy_git_commit_message
        )
        self.install_button.clicked.connect(
            self._request_install
        )

        action_layout = QHBoxLayout()
        action_layout.addWidget(
            self.open_readme_button
        )
        action_layout.addWidget(
            self.open_contents_button
        )
        action_layout.addWidget(
            self.copy_commit_button
        )
        action_layout.addWidget(
            self.install_button
        )
        action_layout.addStretch(
            1
        )

        close_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        close_buttons.rejected.connect(
            self.reject
        )

        layout = QVBoxLayout(
            self
        )
        layout.addWidget(
            package_label
        )
        layout.addWidget(
            root_label
        )
        layout.addWidget(
            state_label
        )
        layout.addWidget(
            self.review_edit,
            1,
        )
        layout.addLayout(
            action_layout
        )
        layout.addWidget(
            close_buttons
        )

    def _review_text(self) -> str:
        sections = (
            (
                "INSTALLATION",
                self.readme.installation,
            ),
            (
                "SUMMARY",
                self.readme.summary,
            ),
            (
                "IMPLEMENTATION DETAILS",
                self.readme.implementation_details,
            ),
            (
                "FILES CHANGED",
                self.readme.files_changed,
            ),
            (
                "MANUAL FOLLOW-UP",
                self.readme.manual_follow_up,
            ),
            (
                "TESTING / VALIDATION",
                self.readme.testing_validation,
            ),
        )

        rendered: list[str] = []

        for heading, content in sections:
            rendered.append(
                heading
            )
            rendered.append(
                ""
            )
            rendered.append(
                content
                if content
                else "Not provided."
            )
            rendered.append(
                ""
            )

        return "\n".join(
            rendered
        ).rstrip()

    def _request_install(
            self,
    ) -> None:
        root_name = self.extracted_package.root_path.name
        self.accept()
        self.install_requested.emit(
            root_name
        )

    def _request_open_readme(
            self,
    ) -> None:
        readme_path = str(
            self.extracted_package.readme_path
        )
        self.accept()
        self.open_readme_requested.emit(
            readme_path
        )

    def _request_open_contents(
            self,
    ) -> None:
        self.open_contents_requested.emit(
            str(
                self.contents_path
            )
        )

    def _copy_git_commit_message(
            self,
    ) -> None:
        if not self.readme.git_commit_message:
            return

        QApplication.clipboard().setText(
            self.readme.git_commit_message
        )
