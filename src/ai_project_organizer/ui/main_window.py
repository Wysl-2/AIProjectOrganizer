from pathlib import Path

from PySide6.QtCore import QDir, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFileSystemModel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTreeView,
)

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

        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(
            self.file_model.index(root_path)
        )

        self.file_tree.doubleClicked.connect(
            self._open_file_from_tree
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

        open_workspace_action = QAction(
            "Open Workspace Folder...",
            self,
        )
        open_workspace_action.setShortcut("Ctrl+O")
        open_workspace_action.triggered.connect(
            self._open_workspace
        )

        save_action = QAction(
            "Save",
            self,
        )
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(
            self._save_current_file
        )

        file_menu.addAction(open_workspace_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)

    def _open_workspace(self) -> None:
        if not self._confirm_discard_unsaved_changes():
            return

        start_path = self.workspace_path or QDir.homePath()

        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Open Workspace Folder",
            start_path,
        )

        if not selected_path:
            return

        self._set_workspace_root(selected_path)

    def _set_workspace_root(self, path: str) -> None:
        self.workspace_path = path
        self.current_file_path = None

        self.file_model.setRootPath(path)
        self.file_tree.setRootIndex(
            self.file_model.index(path)
        )

        self.text_editor.clear()
        self.text_editor.document().setModified(False)

        self._update_window_title()

    def _open_file_from_tree(self, index) -> None:
        if self.file_model.isDir(index):
            return

        file_path = self.file_model.filePath(index)

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
                "This file does not appear to be a UTF-8 text file.",
            )
            return
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Open File",
                f"Could not open the file:\n\n{error}",
            )
            return

        self.current_file_path = file_path

        self.text_editor.setPlainText(text)
        self.text_editor.document().setModified(False)

        self._update_window_title()

    def _save_current_file(self) -> bool:
        if self.current_file_path is None:
            return False

        try:
            Path(self.current_file_path).write_text(
                self.text_editor.toPlainText(),
                encoding="utf-8",
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Save File",
                f"Could not save the file:\n\n{error}",
            )
            return False

        self.text_editor.document().setModified(False)

        self._update_window_title()

        return True

    def _confirm_discard_unsaved_changes(self) -> bool:
        if not self.text_editor.document().isModified():
            return True

        file_name = (
            Path(self.current_file_path).name
            if self.current_file_path
            else "Untitled"
        )

        message_box = QMessageBox(self)

        message_box.setWindowTitle("Unsaved Changes")
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

    def _update_window_title(self, *_args) -> None:
        if self.current_file_path is None:
            self.setWindowTitle("AI Project Organizer")
            return

        file_name = Path(self.current_file_path).name

        modified_marker = (
            " *"
            if self.text_editor.document().isModified()
            else ""
        )

        self.setWindowTitle(
            f"{file_name}{modified_marker} - AI Project Organizer"
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard_unsaved_changes():
            event.accept()
        else:
            event.ignore()