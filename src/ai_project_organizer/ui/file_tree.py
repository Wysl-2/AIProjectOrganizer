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
        target_directory = self._directory_at_position(
            position
        )

        if target_directory is None:
            return

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

        menu = QMenu(self)

        new_file_action = menu.addAction(
            "New File..."
        )
        new_folder_action = menu.addAction(
            "New Folder..."
        )

        rename_action = None
        delete_action = None

        if (
                selected_path is not None
                and not self._is_workspace_root(
            selected_path
        )
        ):
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

        if selected_action == new_file_action:
            self.new_file_requested.emit(
                str(target_directory)
            )

        elif selected_action == new_folder_action:
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
            return self.workspace_path

        model = self.model()

        if not isinstance(model, QFileSystemModel):
            return None

        path = Path(model.filePath(index))

        if path.is_dir():
            return path

        return path.parent

    def _is_workspace_root(
            self,
            path: Path,
    ) -> bool:
        if self.workspace_path is None:
            return False

        try:
            return (
                    path.resolve()
                    == self.workspace_path.resolve()
            )
        except OSError:
            return False

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

                if destination == source:
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

            if self._is_inside_workspace(path):
                paths.append(path)

        return paths

    def _is_inside_workspace(
            self,
            path: Path,
    ) -> bool:
        if self.workspace_path is None:
            return False

        try:
            path.resolve().relative_to(
                self.workspace_path.resolve()
            )
        except (ValueError, OSError):
            return False

        return True

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

        if not target_directory.is_dir():
            return (
                "The destination is not a folder."
            )

        if not self._is_inside_workspace(
                target_directory
        ):
            return (
                "Files cannot be moved outside "
                "the current workspace."
            )

        for source in sources:
            if not source.exists():
                return (
                    f"'{source.name}' no longer exists."
                )

            destination = (
                    target_directory / source.name
            )

            if destination == source:
                continue

            if destination.exists():
                return (
                    f"'{destination.name}' already exists "
                    "in the destination folder."
                )

            if source.is_dir():
                try:
                    target_directory.resolve().relative_to(
                        source.resolve()
                    )
                except ValueError:
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