import shutil
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileSystemModel,
    QMenu,
    QTreeView,
)

from ai_project_organizer.workspace_paths import (
    filesystem_entry_exists,
    is_workspace_entry,
    is_workspace_target,
    same_path_entry,
)


class FileTreeView(QTreeView):
    new_file_requested = Signal(str)
    new_folder_requested = Signal(str)

    rename_requested = Signal(str)
    delete_requested = Signal(str)

    paths_moved = Signal(object)
    move_failed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.workspace_path: Path | None = None

        self.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.customContextMenuRequested.connect(
            self._show_context_menu
        )

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        self.setDragDropMode(
            QAbstractItemView.DragDropMode.DragDrop
        )
        self.setDefaultDropAction(
            Qt.DropAction.MoveAction
        )

    def set_workspace_path(self, path: str | None) -> None:
        self.workspace_path = (
            Path(path)
            if path is not None
            else None
        )

    def _show_context_menu(self, position: QPoint) -> None:
        index = self.indexAt(position)
        selected_path: Path | None = None

        if index.isValid():
            self.setCurrentIndex(index)

            model = self.model()

            if isinstance(model, QFileSystemModel):
                selected_path = Path(
                    model.filePath(index)
                )
        else:
            self.clearSelection()

        target_directory = self._directory_at_position(
            position
        )

        can_modify_entry = (
            selected_path is not None
            and self._can_modify_entry(
                selected_path
            )
            and not self._is_workspace_root(
                selected_path
            )
        )

        if target_directory is None and not can_modify_entry:
            return

        menu = QMenu(self)

        new_file_action = None
        new_folder_action = None

        if target_directory is not None:
            new_file_action = menu.addAction(
                "New File..."
            )
            new_folder_action = menu.addAction(
                "New Folder..."
            )

        rename_action = None
        delete_action = None

        if can_modify_entry:
            if target_directory is not None:
                menu.addSeparator()

            rename_action = menu.addAction(
                "Rename..."
            )
            delete_action = menu.addAction(
                "Delete"
            )

        selected_action = menu.exec(
            self.viewport().mapToGlobal(position)
        )

        if (
                new_file_action is not None
                and selected_action == new_file_action
                and target_directory is not None
        ):
            self.new_file_requested.emit(
                str(target_directory)
            )

        elif (
                new_folder_action is not None
                and selected_action == new_folder_action
                and target_directory is not None
        ):
            self.new_folder_requested.emit(
                str(target_directory)
            )

        elif (
                rename_action is not None
                and selected_action == rename_action
                and selected_path is not None
        ):
            self.rename_requested.emit(
                str(selected_path)
            )

        elif (
                delete_action is not None
                and selected_action == delete_action
                and selected_path is not None
        ):
            self.delete_requested.emit(
                str(selected_path)
            )

    def _directory_at_position(
            self,
            position: QPoint,
    ) -> Path | None:
        if self.workspace_path is None:
            return None

        index = self.indexAt(position)

        if not index.isValid():
            candidate = self.workspace_path
        else:
            model = self.model()

            if not isinstance(model, QFileSystemModel):
                return None

            path = Path(
                model.filePath(index)
            )

            if path.is_dir():
                candidate = path
            else:
                candidate = path.parent

        if (
                not filesystem_entry_exists(candidate)
                or not candidate.is_dir()
                or not is_workspace_target(
                    candidate,
                    self.workspace_path,
                )
        ):
            return None

        return candidate

    def _can_modify_entry(
            self,
            path: Path,
    ) -> bool:
        if self.workspace_path is None:
            return False

        return (
            filesystem_entry_exists(path)
            and is_workspace_entry(
                path,
                self.workspace_path,
            )
        )

    def _is_workspace_root(
            self,
            path: Path,
    ) -> bool:
        if self.workspace_path is None:
            return False

        return same_path_entry(
            path,
            self.workspace_path,
        )

    def dragEnterEvent(
            self,
            event: QDragEnterEvent,
    ) -> None:
        if (
                event.source() is self
                and event.mimeData().hasUrls()
        ):
            event.setDropAction(
                Qt.DropAction.MoveAction
            )
            event.accept()
            return

        event.ignore()

    def dragMoveEvent(
            self,
            event: QDragMoveEvent,
    ) -> None:
        target_directory = self._directory_at_position(
            event.position().toPoint()
        )

        if target_directory is None:
            event.ignore()
            return

        sources = self._source_paths(event)

        if not sources:
            event.ignore()
            return

        if not self._can_move_to(
                sources,
                target_directory,
        ):
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.MoveAction
        )
        event.accept()

    def dropEvent(
            self,
            event: QDropEvent,
    ) -> None:
        target_directory = self._directory_at_position(
            event.position().toPoint()
        )

        if target_directory is None:
            event.ignore()
            return

        sources = self._source_paths(event)

        if not sources:
            event.ignore()
            return

        sources = self._remove_nested_sources(
            sources
        )

        error = self._validate_move(
            sources,
            target_directory,
        )

        if error is not None:
            self.move_failed.emit(error)
            event.ignore()
            return

        moved_paths: dict[str, str] = {}

        try:
            for source in sources:
                destination = (
                        target_directory / source.name
                )

                if same_path_entry(
                        destination,
                        source,
                ):
                    continue

                shutil.move(
                    str(source),
                    str(destination),
                )

                moved_paths[str(source)] = str(
                    destination
                )

        except OSError as error:
            self.move_failed.emit(
                f"Could not move the item:\n\n{error}"
            )
            event.ignore()
            return

        if moved_paths:
            self.paths_moved.emit(
                moved_paths
            )

        event.setDropAction(
            Qt.DropAction.MoveAction
        )
        event.accept()

    def _source_paths(
            self,
            event,
    ) -> list[Path]:
        if self.workspace_path is None:
            return []

        paths: list[Path] = []

        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue

            path = Path(
                url.toLocalFile()
            )

            if (
                    filesystem_entry_exists(path)
                    and is_workspace_entry(
                        path,
                        self.workspace_path,
                    )
            ):
                paths.append(path)

        return paths

    def _can_move_to(
            self,
            sources: list[Path],
            target_directory: Path,
    ) -> bool:
        return (
                self._validate_move(
                    sources,
                    target_directory,
                )
                is None
        )

    def _validate_move(
            self,
            sources: list[Path],
            target_directory: Path,
    ) -> str | None:
        if self.workspace_path is None:
            return "No workspace is open."

        if (
                not filesystem_entry_exists(
                    target_directory
                )
                or not target_directory.is_dir()
        ):
            return (
                "The destination is not a folder."
            )

        if not is_workspace_target(
                target_directory,
                self.workspace_path,
        ):
            return (
                "Files cannot be moved outside "
                "the current workspace."
            )

        for source in sources:
            if not filesystem_entry_exists(source):
                return (
                    f"'{source.name}' no longer exists."
                )

            if not is_workspace_entry(
                    source,
                    self.workspace_path,
            ):
                return (
                    "Files cannot be moved from outside "
                    "the current workspace."
                )

            destination = (
                    target_directory / source.name
            )

            if same_path_entry(
                    destination,
                    source,
            ):
                continue

            if filesystem_entry_exists(
                    destination
            ):
                return (
                    f"'{destination.name}' already exists "
                    "in the destination folder."
                )

            if (
                    source.is_dir()
                    and not source.is_symlink()
            ):
                try:
                    target_directory.resolve().relative_to(
                        source.resolve()
                    )
                except (ValueError, OSError, RuntimeError):
                    pass
                else:
                    return (
                        "A folder cannot be moved "
                        "inside itself."
                    )

        return None

    def _remove_nested_sources(
            self,
            sources: list[Path],
    ) -> list[Path]:
        ordered = sorted(
            set(sources),
            key=lambda path: len(path.parts),
        )

        filtered: list[Path] = []

        for source in ordered:
            if any(
                    parent == source
                    or parent in source.parents
                    for parent in filtered
            ):
                continue

            filtered.append(source)

        return filtered
