from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ai_project_organizer.project import (
    ProjectMetadata,
    ProjectMetadataError,
)
from ai_project_organizer.ui.project_metadata_form import (
    ProjectMetadataForm,
)


class NewProjectDialog(QDialog):
    def __init__(
            self,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(
            "Create New Project"
        )
        self.setMinimumWidth(620)

        self.project_location_edit = QLineEdit(self)
        self.project_location_edit.setText(
            str(Path.home())
        )

        self.metadata_form = ProjectMetadataForm(
            browse_start_path=Path.home(),
            default_name="",
            parent=self,
        )

        self.name_edit = self.metadata_form.name_edit
        self.working_directory_edit = (
            self.metadata_form.working_directory_edit
        )
        self.local_git_repository_edit = (
            self.metadata_form.local_git_repository_edit
        )
        self.github_repository_edit = (
            self.metadata_form.github_repository_edit
        )

        location_layout = QFormLayout()
        location_layout.addRow(
            "Project Location",
            self._project_location_row(),
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        create_button = buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        if create_button is not None:
            create_button.setText(
                "Create"
            )
            create_button.setProperty(
                "role",
                "primary",
            )
        buttons.accepted.connect(
            self._accept_project
        )
        buttons.rejected.connect(
            self.reject
        )

        layout = QVBoxLayout(self)
        layout.addLayout(
            location_layout
        )
        layout.addWidget(
            self.metadata_form
        )
        layout.addWidget(buttons)

    def _project_location_row(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        browse_button = QPushButton(
            "Browse...",
            container,
        )
        browse_button.clicked.connect(
            self._browse_project_location
        )

        layout.addWidget(
            self.project_location_edit
        )
        layout.addWidget(
            browse_button
        )

        return container

    def project_metadata(self) -> ProjectMetadata:
        return self.metadata_form.project_metadata()

    def project_location(self) -> Path:
        entered_text = self.project_location_edit.text().strip()

        if not entered_text:
            raise ValueError(
                "Project location must not be empty."
            )

        location = Path(
            entered_text
        ).expanduser()

        if not location.is_absolute():
            raise ValueError(
                "Project location must be an absolute path."
            )

        if not location.exists():
            raise FileNotFoundError(
                f"Project location does not exist: {location}"
            )

        if not location.is_dir():
            raise NotADirectoryError(
                f"Project location is not a directory: {location}"
            )

        return location

    def workspace_path(self) -> Path:
        metadata = self.project_metadata()
        project_name = metadata.name

        if (
                project_name in {".", ".."}
                or "/" in project_name
                or "\\" in project_name
        ):
            raise ValueError(
                "Project name must be a valid folder name without "
                "path separators."
            )

        workspace = (
            self.project_location()
            / project_name
        )

        if workspace.exists() or workspace.is_symlink():
            raise FileExistsError(
                f"Project workspace already exists: {workspace}"
            )

        return workspace

    def _accept_project(self) -> None:
        try:
            self.workspace_path()
        except (ProjectMetadataError, OSError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Invalid Project Configuration",
                str(error),
            )
            return

        self.accept()

    def _browse_project_location(self) -> None:
        entered_text = self.project_location_edit.text().strip()
        entered_path = (
            Path(entered_text).expanduser()
            if entered_text
            else None
        )

        start_path = (
            entered_path
            if entered_path is not None and entered_path.is_dir()
            else Path.home()
        )

        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Select Project Location",
            str(start_path),
        )

        if selected_path:
            self.project_location_edit.setText(
                selected_path
            )
