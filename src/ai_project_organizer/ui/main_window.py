from PySide6.QtCore import QDir, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFileSystemModel,
    QMainWindow,
    QPlainTextEdit,
    QSplitter,
    QTreeView,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("AI Project Organizer")
        self.resize(1000, 700)

        self.workspace_path: str | None = None

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
        self.file_tree.setRootIndex(self.file_model.index(root_path))

        self.text_editor = QPlainTextEdit()

        splitter.addWidget(self.file_tree)
        splitter.addWidget(self.text_editor)

        splitter.setSizes([300, 700])

        self.setCentralWidget(splitter)

    def _setup_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_workspace_action = QAction("Open Workspace Folder...", self)
        open_workspace_action.setShortcut("Ctrl+O")
        open_workspace_action.triggered.connect(self._open_workspace)

        file_menu.addAction(open_workspace_action)

    def _open_workspace(self) -> None:
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

        self.file_model.setRootPath(path)
        self.file_tree.setRootIndex(self.file_model.index(path))