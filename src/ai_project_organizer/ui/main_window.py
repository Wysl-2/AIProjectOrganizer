from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

        self._setup_ui()

    def _setup_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.file_tree = QTreeView()
        self.text_editor = QPlainTextEdit()

        splitter.addWidget(self.file_tree)
        splitter.addWidget(self.text_editor)

        splitter.setSizes([300, 700])

        self.setCentralWidget(splitter)