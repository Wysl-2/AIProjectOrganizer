from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class ProjectBrowserEntry:
    display_name: str
    workspace_path: Path
    available: bool


class WelcomePage(QWidget):
    create_project_requested = Signal()
    open_existing_requested = Signal()
    project_open_requested = Signal(str)
    project_remove_requested = Signal(str)

    def __init__(
            self,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        title_label = QLabel(
            "AI Project Organizer"
        )
        title_font = title_label.font()
        title_font.setPointSize(
            title_font.pointSize() + 6
        )
        title_font.setBold(True)
        title_label.setFont(
            title_font
        )

        layout.addWidget(
            title_label
        )

        button_layout = QHBoxLayout()

        self.create_project_button = QPushButton(
            "Create New Project"
        )
        self.create_project_button.clicked.connect(
            self.create_project_requested.emit
        )

        self.open_existing_button = QPushButton(
            "Open Existing Project"
        )
        self.open_existing_button.clicked.connect(
            self.open_existing_requested.emit
        )

        button_layout.addWidget(
            self.create_project_button
        )
        button_layout.addWidget(
            self.open_existing_button
        )
        button_layout.addStretch()

        layout.addLayout(
            button_layout
        )

        projects_label = QLabel(
            "Projects"
        )
        projects_font = projects_label.font()
        projects_font.setBold(True)
        projects_label.setFont(
            projects_font
        )

        layout.addWidget(
            projects_label
        )

        self.empty_label = QLabel(
            "No Projects have been opened yet."
        )
        layout.addWidget(
            self.empty_label
        )

        self.project_list = QListWidget()
        self.project_list.itemActivated.connect(
            self._emit_project_open
        )
        self.project_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.project_list.customContextMenuRequested.connect(
            self._show_project_menu
        )
        layout.addWidget(
            self.project_list,
            1,
        )

        self.set_projects(
            ()
        )

    def set_projects(
            self,
            projects: Iterable[ProjectBrowserEntry],
    ) -> None:
        entries = tuple(projects)

        self.project_list.clear()

        for entry in entries:
            status = (
                "\nUnavailable"
                if not entry.available
                else ""
            )

            item = QListWidgetItem(
                (
                    f"{entry.display_name}"
                    f"\n{entry.workspace_path}"
                    f"{status}"
                )
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                str(entry.workspace_path),
            )

            self.project_list.addItem(
                item
            )

        has_projects = bool(entries)

        self.empty_label.setVisible(
            not has_projects
        )
        self.project_list.setVisible(
            has_projects
        )

    def _show_project_menu(
            self,
            position: QPoint,
    ) -> None:
        item = self.project_list.itemAt(
            position
        )

        if item is None:
            return

        self.project_list.setCurrentItem(
            item
        )

        menu = QMenu(self)
        open_action = menu.addAction(
            "Open Project"
        )
        remove_action = menu.addAction(
            "Remove from Projects"
        )

        selected_action = menu.exec(
            self.project_list.viewport().mapToGlobal(
                position
            )
        )

        if selected_action == open_action:
            self._emit_project_open(
                item
            )
        elif selected_action == remove_action:
            self._emit_project_remove(
                item
            )

    def _workspace_path_for_item(
            self,
            item: QListWidgetItem,
    ) -> str | None:
        workspace_path = item.data(
            Qt.ItemDataRole.UserRole
        )

        if not isinstance(workspace_path, str):
            return None

        return workspace_path

    def _emit_project_open(
            self,
            item: QListWidgetItem,
    ) -> None:
        workspace_path = self._workspace_path_for_item(
            item
        )

        if workspace_path is None:
            return

        self.project_open_requested.emit(
            workspace_path
        )

    def _emit_project_remove(
            self,
            item: QListWidgetItem,
    ) -> None:
        workspace_path = self._workspace_path_for_item(
            item
        )

        if workspace_path is None:
            return

        self.project_remove_requested.emit(
            workspace_path
        )
