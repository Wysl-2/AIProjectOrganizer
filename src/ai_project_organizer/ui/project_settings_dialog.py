from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMessageBox,
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


class ProjectSettingsDialog(QDialog):
    def __init__(
            self,
            workspace_path: str | Path,
            metadata: ProjectMetadata | None = None,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.workspace_path = Path(
            workspace_path
        ).expanduser()

        self.setWindowTitle(
            "Project Configuration"
        )
        self.setMinimumWidth(620)

        self.metadata_form = ProjectMetadataForm(
            browse_start_path=self.workspace_path,
            metadata=metadata,
            default_name=self.workspace_path.name,
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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(
            self._accept_configuration
        )
        buttons.rejected.connect(
            self.reject
        )

        layout = QVBoxLayout(self)
        layout.addWidget(
            self.metadata_form
        )
        layout.addWidget(buttons)

    def project_metadata(self) -> ProjectMetadata:
        return self.metadata_form.project_metadata()

    def _accept_configuration(self) -> None:
        try:
            self.project_metadata()
        except ProjectMetadataError as error:
            QMessageBox.warning(
                self,
                "Invalid Project Configuration",
                str(error),
            )
            return

        self.accept()
