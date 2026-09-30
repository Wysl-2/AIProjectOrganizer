import shutil
from pathlib import Path

from PySide6.QtCore import QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QPainter,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileSystemModel,
    QMenu,
    QStyle,
    QStyleOptionViewItem,
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
    import_failed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.workspace_path: Path | None = None
        self._drop_highlight_path: Path | None = None

        self.setProperty(
            "role",
            "fileTree",
        )
        self.setHeaderHidden(
            True
        )
        self.setUniformRowHeights(
            True
        )
        self.setIndentation(
            16
        )

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
        self._set_drop_highlight(None)
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

    def _folder_path_at_position(
            self,
            position: QPoint,
    ) -> Path | None:
        if self.workspace_path is None:
            return None

        index = self.indexAt(position)

        if not index.isValid():
            return None

        model = self.model()

        if not isinstance(model, QFileSystemModel):
            return None

        path = Path(
            model.filePath(index)
        )

        if (
                not filesystem_entry_exists(path)
                or not path.is_dir()
                or not is_workspace_target(
                    path,
                    self.workspace_path,
                )
        ):
            return None

        return path

    def _set_drop_highlight(
            self,
            path: Path | None,
    ) -> None:
        if (
                self._drop_highlight_path is None
                and path is None
        ):
            return

        if (
                self._drop_highlight_path is not None
                and path is not None
                and same_path_entry(
                    self._drop_highlight_path,
                    path,
                )
        ):
            return

        self._drop_highlight_path = path
        self.viewport().update()

    def _update_drop_highlight(
            self,
            position: QPoint,
            target_directory: Path,
    ) -> None:
        folder_path = self._folder_path_at_position(
            position
        )

        if (
                folder_path is None
                or not same_path_entry(
                    folder_path,
                    target_directory,
                )
        ):
            self._set_drop_highlight(None)
            return

        self._set_drop_highlight(
            folder_path
        )

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
        self._set_drop_highlight(None)

        if not event.mimeData().hasUrls():
            event.ignore()
            return

        if event.source() is self:
            event.setDropAction(
                Qt.DropAction.MoveAction
            )
            event.accept()
            return

        sources = self._external_source_paths(
            event
        )

        if not sources:
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.CopyAction
        )
        event.accept()

    def dragMoveEvent(
            self,
            event: QDragMoveEvent,
    ) -> None:
        position = event.position().toPoint()
        target_directory = self._directory_at_position(
            position
        )

        if target_directory is None:
            self._set_drop_highlight(None)
            event.ignore()
            return

        if event.source() is self:
            sources = self._source_paths(event)

            if not sources:
                self._set_drop_highlight(None)
                event.ignore()
                return

            if not self._can_move_to(
                    sources,
                    target_directory,
            ):
                self._set_drop_highlight(None)
                event.ignore()
                return

            self._update_drop_highlight(
                position,
                target_directory,
            )
            event.setDropAction(
                Qt.DropAction.MoveAction
            )
            event.accept()
            return

        sources = self._external_source_paths(
            event
        )

        if not sources:
            self._set_drop_highlight(None)
            event.ignore()
            return

        if not self._can_import_to(
                sources,
                target_directory,
        ):
            self._set_drop_highlight(None)
            event.ignore()
            return

        self._update_drop_highlight(
            position,
            target_directory,
        )
        event.setDropAction(
            Qt.DropAction.CopyAction
        )
        event.accept()

    def dragLeaveEvent(
            self,
            event: QDragLeaveEvent,
    ) -> None:
        self._set_drop_highlight(None)
        super().dragLeaveEvent(event)

    def dropEvent(
            self,
            event: QDropEvent,
    ) -> None:
        self._set_drop_highlight(None)

        target_directory = self._directory_at_position(
            event.position().toPoint()
        )

        if target_directory is None:
            event.ignore()
            return

        if event.source() is self:
            self._drop_internal_move(
                event,
                target_directory,
            )
            return

        self._drop_external_import(
            event,
            target_directory,
        )

    def _drop_internal_move(
            self,
            event: QDropEvent,
            target_directory: Path,
    ) -> None:
        sources = self._source_paths(event)

        if not sources:
            event.ignore()
            return

        move_plan, error = self._build_move_plan(
            sources,
            target_directory,
        )

        if error is not None:
            self.move_failed.emit(error)
            event.ignore()
            return

        if not self._execute_move_plan(
                move_plan
        ):
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.MoveAction
        )
        event.accept()

    def _drop_external_import(
            self,
            event: QDropEvent,
            target_directory: Path,
    ) -> None:
        sources = self._external_source_paths(
            event
        )

        if not sources:
            event.ignore()
            return

        import_plan, error = self._build_import_plan(
            sources,
            target_directory,
        )

        if error is not None:
            self.import_failed.emit(error)
            event.ignore()
            return

        if not self._execute_import_plan(
                import_plan
        ):
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.CopyAction
        )
        event.accept()

    def drawRow(
            self,
            painter: QPainter,
            options: QStyleOptionViewItem,
            index: QModelIndex,
    ) -> None:
        model = self.model()

        if (
                self._drop_highlight_path is not None
                and isinstance(model, QFileSystemModel)
        ):
            path = Path(
                model.filePath(index)
            )

            if same_path_entry(
                    path,
                    self._drop_highlight_path,
            ):
                highlighted_options = QStyleOptionViewItem(
                    options
                )
                highlighted_options.state |= (
                    QStyle.StateFlag.State_Selected
                )
                highlighted_options.state &= ~(
                    QStyle.StateFlag.State_HasFocus
                )

                super().drawRow(
                    painter,
                    highlighted_options,
                    index,
                )
                return

        super().drawRow(
            painter,
            options,
            index,
        )

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

    def _external_source_paths(
            self,
            event,
    ) -> list[Path]:
        urls = event.mimeData().urls()

        if not urls:
            return []

        paths: list[Path] = []

        for url in urls:
            if not url.isLocalFile():
                return []

            local_file = url.toLocalFile()

            if not local_file:
                return []

            paths.append(
                Path(local_file)
            )

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
        _move_plan, error = self._build_move_plan(
            sources,
            target_directory,
        )
        return error

    def _can_import_to(
            self,
            sources: list[Path],
            target_directory: Path,
    ) -> bool:
        _import_plan, error = self._build_import_plan(
            sources,
            target_directory,
        )
        return error is None

    def _build_move_plan(
            self,
            sources: list[Path],
            target_directory: Path,
    ) -> tuple[list[tuple[Path, Path]], str | None]:
        if self.workspace_path is None:
            return [], "No workspace is open."

        if (
                not filesystem_entry_exists(
                    target_directory
                )
                or not target_directory.is_dir()
        ):
            return [], "The destination is not a folder."

        if not is_workspace_target(
                target_directory,
                self.workspace_path,
        ):
            return (
                [],
                (
                    "Files cannot be moved outside "
                    "the current workspace."
                ),
            )

        move_plan: list[tuple[Path, Path]] = []

        for source in self._remove_nested_sources(
                sources
        ):
            if not filesystem_entry_exists(source):
                return (
                    [],
                    f"'{source.name}' no longer exists.",
                )

            if not is_workspace_entry(
                    source,
                    self.workspace_path,
            ):
                return (
                    [],
                    (
                        "Files cannot be moved from outside "
                        "the current workspace."
                    ),
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
                    [],
                    (
                        f"'{destination.name}' already exists "
                        "in the destination folder."
                    ),
                )

            if any(
                    same_path_entry(
                        destination,
                        planned_destination,
                    )
                    for _planned_source, planned_destination in move_plan
            ):
                return (
                    [],
                    (
                        "Multiple selected items would be moved "
                        f"to '{destination.name}'."
                    ),
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
                        [],
                        (
                            "A folder cannot be moved "
                            "inside itself."
                        ),
                    )

            move_plan.append(
                (
                    source,
                    destination,
                )
            )

        return move_plan, None

    def _build_import_plan(
            self,
            sources: list[Path],
            target_directory: Path,
    ) -> tuple[list[tuple[Path, Path]], str | None]:
        if self.workspace_path is None:
            return [], "No workspace is open."

        if (
                not filesystem_entry_exists(
                    target_directory
                )
                or not target_directory.is_dir()
        ):
            return [], "The destination is not a folder."

        if not is_workspace_target(
                target_directory,
                self.workspace_path,
        ):
            return (
                [],
                (
                    "Files can only be imported into "
                    "the current workspace."
                ),
            )

        import_plan: list[tuple[Path, Path]] = []

        for source in self._remove_nested_sources(
                sources
        ):
            if not filesystem_entry_exists(source):
                return (
                    [],
                    f"'{source.name}' no longer exists.",
                )

            if (
                    not source.is_symlink()
                    and not source.is_file()
                    and not source.is_dir()
            ):
                return (
                    [],
                    (
                        f"'{source.name}' is not a supported "
                        "file, folder, or symbolic link."
                    ),
                )

            destination = (
                target_directory / source.name
            )

            if filesystem_entry_exists(
                    destination
            ):
                return (
                    [],
                    (
                        f"'{destination.name}' already exists "
                        "in the destination folder."
                    ),
                )

            if any(
                    same_path_entry(
                        destination,
                        planned_destination,
                    )
                    for _planned_source, planned_destination in import_plan
            ):
                return (
                    [],
                    (
                        "Multiple selected items would be imported "
                        f"to '{destination.name}'."
                    ),
                )

            if (
                    source.is_dir()
                    and not source.is_symlink()
            ):
                try:
                    target_directory.resolve().relative_to(
                        source.resolve()
                    )
                except ValueError:
                    pass
                except (OSError, RuntimeError):
                    return (
                        [],
                        (
                            f"Could not safely validate "
                            f"'{source.name}' for import."
                        ),
                    )
                else:
                    return (
                        [],
                        (
                            "A folder cannot be imported "
                            "inside itself."
                        ),
                    )

            import_plan.append(
                (
                    source,
                    destination,
                )
            )

        return import_plan, None

    def _execute_move_plan(
            self,
            move_plan: list[tuple[Path, Path]],
    ) -> bool:
        moved_paths: dict[str, str] = {}

        for source, destination in move_plan:
            try:
                shutil.move(
                    str(source),
                    str(destination),
                )
            except OSError as error:
                if moved_paths:
                    self.paths_moved.emit(
                        moved_paths
                    )

                self.move_failed.emit(
                    f"Could not move the item:\n\n{error}"
                )
                return False

            moved_paths[str(source)] = str(
                destination
            )

        if moved_paths:
            self.paths_moved.emit(
                moved_paths
            )

        return True

    def _execute_import_plan(
            self,
            import_plan: list[tuple[Path, Path]],
    ) -> bool:
        for source, destination in import_plan:
            try:
                self._copy_import_entry(
                    source,
                    destination,
                )
            except OSError as error:
                self.import_failed.emit(
                    f"Could not import the item:\n\n{error}"
                )
                return False

        return True

    def _copy_import_entry(
            self,
            source: Path,
            destination: Path,
    ) -> None:
        if source.is_symlink():
            shutil.copy2(
                source,
                destination,
                follow_symlinks=False,
            )
            return

        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                symlinks=True,
            )
            return

        if source.is_file():
            self._copy_regular_file_exclusive(
                source,
                destination,
            )
            return

        raise OSError(
            f"Unsupported filesystem entry: {source}"
        )

    def _copy_regular_file_exclusive(
            self,
            source: Path,
            destination: Path,
    ) -> None:
        destination_created = False

        try:
            with source.open("rb") as source_file:
                with destination.open("xb") as destination_file:
                    destination_created = True
                    shutil.copyfileobj(
                        source_file,
                        destination_file,
                    )

            shutil.copystat(
                source,
                destination,
                follow_symlinks=False,
            )
        except Exception:
            if destination_created:
                try:
                    destination.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass

            raise

    def _remove_nested_sources(
            self,
            sources: list[Path],
    ) -> list[Path]:
        ordered = sorted(
            set(sources),
            key=lambda path: (
                len(path.parts),
                str(path),
            ),
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
