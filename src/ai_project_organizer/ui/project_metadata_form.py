from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ai_project_organizer.project import ProjectMetadata


class ProjectMetadataForm(QWidget):
    def __init__(
            self,
            browse_start_path: str | Path,
            metadata: ProjectMetadata | None = None,
            default_name: str = "",
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.browse_start_path = Path(
            browse_start_path
        ).expanduser()

        self.name_edit = QLineEdit(self)
        self.working_directory_edit = QLineEdit(self)
        self.local_git_repository_edit = QLineEdit(self)
        self.github_repository_edit = QLineEdit(self)
        self.github_repository_edit.setPlaceholderText(
            "owner/repository"
        )

        self._populate_fields(
            metadata,
            default_name,
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        form_layout = QFormLayout(self)

        form_layout.addRow(
            "Project Name",
            self.name_edit,
        )
        form_layout.addRow(
            "Development Working Directory",
            self._directory_row(
                self.working_directory_edit,
                self._browse_working_directory,
            ),
        )
        form_layout.addRow(
            "Local Git Repository",
            self._directory_row(
                self.local_git_repository_edit,
                self._browse_local_git_repository,
            ),
        )
        form_layout.addRow(
            "GitHub Repository",
            self.github_repository_edit,
        )

    def _directory_row(
            self,
            line_edit: QLineEdit,
            browse_callback,
    ) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        browse_button = QPushButton(
            "Browse...",
            container,
        )
        browse_button.clicked.connect(
            browse_callback
        )

        layout.addWidget(line_edit)
        layout.addWidget(browse_button)

        return container

    def _populate_fields(
            self,
            metadata: ProjectMetadata | None,
            default_name: str,
    ) -> None:
        if metadata is None:
            self.name_edit.setText(
                default_name
            )
            return

        self.name_edit.setText(
            metadata.name
        )
        self.working_directory_edit.setText(
            str(metadata.working_directory)
        )
        self.local_git_repository_edit.setText(
            str(metadata.local_git_repository)
        )
        self.github_repository_edit.setText(
            metadata.github_repository
        )

    def project_metadata(self) -> ProjectMetadata:
        return ProjectMetadata(
            name=self.name_edit.text(),
            working_directory=Path(
                self.working_directory_edit.text().strip()
            ).expanduser(),
            local_git_repository=Path(
                self.local_git_repository_edit.text().strip()
            ).expanduser(),
            github_repository=self.github_repository_edit.text(),
        )

    def _browse_working_directory(self) -> None:
        self._browse_directory(
            self.working_directory_edit,
            "Select Development Working Directory",
        )

    def _browse_local_git_repository(self) -> None:
        self._browse_directory(
            self.local_git_repository_edit,
            "Select Local Git Repository",
        )

    def _browse_directory(
            self,
            line_edit: QLineEdit,
            title: str,
    ) -> None:
        entered_text = line_edit.text().strip()
        entered_path = (
            Path(entered_text).expanduser()
            if entered_text
            else None
        )

        start_path = (
            entered_path
            if entered_path is not None and entered_path.is_dir()
            else self.browse_start_path
        )

        if not start_path.is_dir():
            start_path = Path.home()

        selected_path = QFileDialog.getExistingDirectory(
            self,
            title,
            str(start_path),
        )

        if selected_path:
            line_edit.setText(
                selected_path
            )
