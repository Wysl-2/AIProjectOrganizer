import shutil
from pathlib import Path

from PySide6.QtCore import QDir, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFileSystemModel,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
)

from ai_project_organizer.ui.file_tree import FileTreeView
from ai_project_organizer.ui.text_editor import TextEditor


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("AI Project Organizer")
        self.resize(1000, 700)

        self.workspace_path: str | None = None
        self.current_file_path: str | None = None

        self._setup_ui()
        self._setup_menu()

    def _setup_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.file_model = QFileSystemModel(self)
        self.file_model.setReadOnly(True)

        root_path = QDir.homePath()
        self.file_model.setRootPath(root_path)

        self.file_tree = FileTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(
            self.file_model.index(root_path)
        )

        self.file_tree.doubleClicked.connect(
            self._open_file_from_tree
        )

        self.file_tree.new_file_requested.connect(
            self._create_new_file
        )

        self.file_tree.new_folder_requested.connect(
            self._create_new_folder
        )

        self.file_tree.rename_requested.connect(
            self._rename_item
        )

        self.file_tree.delete_requested.connect(
            self._delete_item
        )

        self.file_tree.paths_moved.connect(
            self._handle_paths_moved
        )

        self.file_tree.move_failed.connect(
            self._show_move_error
        )

        self.text_editor = TextEditor()

        self.text_editor.document().modificationChanged.connect(
            self._update_window_title
        )

        splitter.addWidget(self.file_tree)
        splitter.addWidget(self.text_editor)

        splitter.setSizes([300, 700])

        self.setCentralWidget(splitter)

    def _setup_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        new_file_action = QAction(
            "New File...",
            self,
        )
        new_file_action.setShortcut(
            QKeySequence.StandardKey.New
        )
        new_file_action.triggered.connect(
            lambda: self._create_new_file()
        )

        new_folder_action = QAction(
            "New Folder...",
            self,
        )
        new_folder_action.setShortcut(
            "Ctrl+Shift+N"
        )
        new_folder_action.triggered.connect(
            lambda: self._create_new_folder()
        )

        open_workspace_action = QAction(
            "Open Workspace Folder...",
            self,
        )
        open_workspace_action.setShortcut(
            "Ctrl+O"
        )
        open_workspace_action.triggered.connect(
            self._open_workspace
        )

        save_action = QAction(
            "Save",
            self,
        )
        save_action.setShortcut(
            QKeySequence.StandardKey.Save
        )
        save_action.triggered.connect(
            self._save_current_file
        )

        file_menu.addAction(
            new_file_action
        )
        file_menu.addAction(
            new_folder_action
        )
        file_menu.addSeparator()
        file_menu.addAction(
            open_workspace_action
        )
        file_menu.addSeparator()
        file_menu.addAction(
            save_action
        )

    def _open_workspace(self) -> None:
        if not self._confirm_discard_unsaved_changes():
            return

        start_path = (
                self.workspace_path
                or QDir.homePath()
        )

        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Open Workspace Folder",
            start_path,
        )

        if not selected_path:
            return

        self._set_workspace_root(
            selected_path
        )

    def _set_workspace_root(
            self,
            path: str,
    ) -> None:
        self.workspace_path = path
        self.current_file_path = None

        self.file_tree.set_workspace_path(
            path
        )

        self.file_model.setRootPath(
            path
        )
        self.file_tree.setRootIndex(
            self.file_model.index(path)
        )

        self.text_editor.clear()
        self.text_editor.document().setModified(
            False
        )

        self._update_window_title()

    def _open_file_from_tree(
            self,
            index,
    ) -> None:
        if self.file_model.isDir(index):
            return

        file_path = self.file_model.filePath(
            index
        )

        if file_path == self.current_file_path:
            return

        if not self._confirm_discard_unsaved_changes():
            return

        try:
            text = Path(file_path).read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            QMessageBox.warning(
                self,
                "Unable to Open File",
                (
                    "This file does not appear "
                    "to be a UTF-8 text file."
                ),
            )
            return
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Open File",
                (
                    "Could not open the file:"
                    f"\n\n{error}"
                ),
            )
            return

        self.current_file_path = file_path

        self.text_editor.setPlainText(
            text
        )
        self.text_editor.document().setModified(
            False
        )

        self._update_window_title()

    def _save_current_file(self) -> bool:
        if self.current_file_path is None:
            return False

        try:
            Path(
                self.current_file_path
            ).write_text(
                self.text_editor.toPlainText(),
                encoding="utf-8",
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Save File",
                (
                    "Could not save the file:"
                    f"\n\n{error}"
                ),
            )
            return False

        self.text_editor.document().setModified(
            False
        )

        self._update_window_title()

        return True

    def _create_new_file(
            self,
            target_path: str | None = None,
    ) -> None:
        if target_path is not None:
            target_directory = Path(
                target_path
            )
        else:
            target_directory = (
                self._get_creation_directory()
            )

        if target_directory is None:
            return

        file_name, accepted = QInputDialog.getText(
            self,
            "New File",
            "File name:",
        )

        if not accepted:
            return

        file_name = file_name.strip()

        if not self._is_valid_item_name(
                file_name
        ):
            QMessageBox.warning(
                self,
                "Invalid File Name",
                (
                    "Enter a valid file name "
                    "without path separators."
                ),
            )
            return

        new_file_path = (
                target_directory / file_name
        )

        if new_file_path.exists():
            QMessageBox.warning(
                self,
                "File Already Exists",
                (
                    "A file or folder named "
                    f"'{file_name}' already exists."
                ),
            )
            return

        if not self._confirm_discard_unsaved_changes():
            return

        try:
            new_file_path.write_text(
                "",
                encoding="utf-8",
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Create File",
                (
                    "Could not create the file:"
                    f"\n\n{error}"
                ),
            )
            return

        self.current_file_path = str(
            new_file_path
        )

        self.text_editor.clear()
        self.text_editor.document().setModified(
            False
        )
        self.text_editor.setFocus()

        self._update_window_title()

    def _create_new_folder(
            self,
            target_path: str | None = None,
    ) -> None:
        if target_path is not None:
            target_directory = Path(
                target_path
            )
        else:
            target_directory = (
                self._get_creation_directory()
            )

        if target_directory is None:
            return

        folder_name, accepted = QInputDialog.getText(
            self,
            "New Folder",
            "Folder name:",
        )

        if not accepted:
            return

        folder_name = folder_name.strip()

        if not self._is_valid_item_name(
                folder_name
        ):
            QMessageBox.warning(
                self,
                "Invalid Folder Name",
                (
                    "Enter a valid folder name "
                    "without path separators."
                ),
            )
            return

        new_folder_path = (
                target_directory / folder_name
        )

        if new_folder_path.exists():
            QMessageBox.warning(
                self,
                "Folder Already Exists",
                (
                    "A file or folder named "
                    f"'{folder_name}' already exists."
                ),
            )
            return

        try:
            new_folder_path.mkdir()
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Create Folder",
                (
                    "Could not create the folder:"
                    f"\n\n{error}"
                ),
            )

    def _rename_item(
            self,
            path_string: str,
    ) -> None:
        path = Path(path_string)

        if not self._can_modify_path(path):
            return

        new_name, accepted = QInputDialog.getText(
            self,
            "Rename",
            "New name:",
            QLineEdit.EchoMode.Normal,
            path.name,
        )

        if not accepted:
            return

        new_name = new_name.strip()

        if not self._is_valid_item_name(
                new_name
        ):
            QMessageBox.warning(
                self,
                "Invalid Name",
                (
                    "Enter a valid name "
                    "without path separators."
                ),
            )
            return

        new_path = path.with_name(
            new_name
        )

        if new_path == path:
            return

        if new_path.exists():
            QMessageBox.warning(
                self,
                "Name Already Exists",
                (
                    "A file or folder named "
                    f"'{new_name}' already exists."
                ),
            )
            return

        try:
            path.rename(
                new_path
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Rename Item",
                (
                    "Could not rename the item:"
                    f"\n\n{error}"
                ),
            )
            return

        self._rebase_current_file_path(
            path,
            new_path,
        )

    def _delete_item(
            self,
            path_string: str,
    ) -> None:
        path = Path(path_string)

        if not self._can_modify_path(path):
            return

        item_type = (
            "folder"
            if path.is_dir()
            else "file"
        )

        message_box = QMessageBox(self)

        message_box.setWindowTitle(
            "Delete Item"
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )

        message_box.setText(
            f"Delete {item_type} '{path.name}'?"
        )

        if path.is_dir():
            message_box.setInformativeText(
                (
                    "The folder and everything "
                    "inside it will be permanently deleted. "
                    "This cannot be undone."
                )
            )
        else:
            message_box.setInformativeText(
                (
                    "The file will be permanently deleted. "
                    "This cannot be undone."
                )
            )

        message_box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        message_box.setDefaultButton(
            QMessageBox.StandardButton.No
        )

        result = message_box.exec()

        if result != QMessageBox.StandardButton.Yes:
            return

        contains_current_document = (
            self._path_contains_current_document(
                path
            )
        )

        if (
                contains_current_document
                and not self._confirm_discard_unsaved_changes()
        ):
            return

        try:
            if (
                    path.is_dir()
                    and not path.is_symlink()
            ):
                shutil.rmtree(path)
            else:
                path.unlink()

        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Delete Item",
                (
                    "Could not delete the item:"
                    f"\n\n{error}"
                ),
            )
            return

        if contains_current_document:
            self.current_file_path = None

            self.text_editor.clear()
            self.text_editor.document().setModified(
                False
            )

            self._update_window_title()

    def _get_creation_directory(
            self,
    ) -> Path | None:
        if self.workspace_path is None:
            QMessageBox.information(
                self,
                "No Workspace Open",
                (
                    "Open a workspace before "
                    "creating files or folders."
                ),
            )
            return None

        current_index = (
            self.file_tree.currentIndex()
        )

        if not current_index.isValid():
            return Path(
                self.workspace_path
            )

        selected_path = Path(
            self.file_model.filePath(
                current_index
            )
        )

        if selected_path.is_dir():
            return selected_path

        return selected_path.parent

    def _is_valid_item_name(
            self,
            name: str,
    ) -> bool:
        if not name:
            return False

        if name in {".", ".."}:
            return False

        if "/" in name or "\\" in name:
            return False

        return True

    def _can_modify_path(
            self,
            path: Path,
    ) -> bool:
        if self.workspace_path is None:
            return False

        if not path.exists():
            QMessageBox.warning(
                self,
                "Item Not Found",
                (
                    "The selected file or folder "
                    "no longer exists."
                ),
            )
            return False

        try:
            resolved_path = path.resolve()
            workspace = Path(
                self.workspace_path
            ).resolve()

            resolved_path.relative_to(
                workspace
            )
        except (ValueError, OSError):
            QMessageBox.warning(
                self,
                "Invalid Operation",
                (
                    "Files outside the current "
                    "workspace cannot be modified."
                ),
            )
            return False

        if resolved_path == workspace:
            QMessageBox.warning(
                self,
                "Invalid Operation",
                (
                    "The workspace root cannot "
                    "be renamed or deleted."
                ),
            )
            return False

        return True

    def _path_contains_current_document(
            self,
            path: Path,
    ) -> bool:
        if self.current_file_path is None:
            return False

        current_path = Path(
            self.current_file_path
        )

        if current_path == path:
            return True

        try:
            current_path.relative_to(
                path
            )
        except ValueError:
            return False

        return True

    def _rebase_current_file_path(
            self,
            old_path: Path,
            new_path: Path,
    ) -> bool:
        if self.current_file_path is None:
            return False

        current_path = Path(
            self.current_file_path
        )

        try:
            relative_path = (
                current_path.relative_to(
                    old_path
                )
            )
        except ValueError:
            return False

        self.current_file_path = str(
            new_path / relative_path
        )

        self._update_window_title()

        return True

    def _handle_paths_moved(
            self,
            moved_paths: dict[str, str],
    ) -> None:
        for old_path, new_path in moved_paths.items():
            if self._rebase_current_file_path(
                    Path(old_path),
                    Path(new_path),
            ):
                break

    def _show_move_error(
            self,
            message: str,
    ) -> None:
        QMessageBox.warning(
            self,
            "Unable to Move Item",
            message,
        )

    def _confirm_discard_unsaved_changes(
            self,
    ) -> bool:
        if not self.text_editor.document().isModified():
            return True

        file_name = (
            Path(
                self.current_file_path
            ).name
            if self.current_file_path
            else "Untitled"
        )

        message_box = QMessageBox(self)

        message_box.setWindowTitle(
            "Unsaved Changes"
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )

        message_box.setText(
            f"{file_name} has unsaved changes."
        )

        message_box.setInformativeText(
            "Do you want to save your changes?"
        )

        message_box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )

        message_box.setDefaultButton(
            QMessageBox.StandardButton.Save
        )

        result = message_box.exec()

        if result == QMessageBox.StandardButton.Save:
            return self._save_current_file()

        if result == QMessageBox.StandardButton.Discard:
            return True

        return False

    def _update_window_title(
            self,
            *_args,
    ) -> None:
        if self.current_file_path is None:
            self.setWindowTitle(
                "AI Project Organizer"
            )
            return

        file_name = Path(
            self.current_file_path
        ).name

        modified_marker = (
            " *"
            if self.text_editor.document().isModified()
            else ""
        )

        self.setWindowTitle(
            (
                f"{file_name}{modified_marker} "
                f"- AI Project Organizer"
            )
        )

    def closeEvent(
            self,
            event: QCloseEvent,
    ) -> None:
        if self._confirm_discard_unsaved_changes():
            event.accept()
        else:
            event.ignore()