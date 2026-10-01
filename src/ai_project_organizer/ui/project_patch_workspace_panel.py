from pathlib import Path

from PySide6.QtWidgets import QWidget

from ai_project_organizer.ui.patch_workspace_panel import (
    PatchWorkspacePanel,
)
from ai_project_organizer.workspace_structure import (
    discover_project_patches,
    is_project_patch_structure_initialized,
)


class ProjectPatchWorkspacePanel(PatchWorkspacePanel):
    def __init__(
            self,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent
        )

        self.workspace_path: Path | None = None

    def set_workspace(
            self,
            workspace_path: str | Path | None,
    ) -> None:
        workspace = (
            Path(
                workspace_path
            ).expanduser()
            if workspace_path is not None
            else None
        )
        self.workspace_path = workspace

        if workspace is None:
            self.clear_context()
            return

        self.set_context(
            (
                "project",
                workspace,
            ),
            owner_label="Project",
            discover_patches=(
                lambda workspace=workspace:
                discover_project_patches(
                    workspace
                )
            ),
            is_patch_structure_initialized=(
                lambda patch_id, workspace=workspace:
                is_project_patch_structure_initialized(
                    workspace,
                    patch_id,
                )
            ),
        )
