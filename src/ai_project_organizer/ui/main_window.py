from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("AI Project Organizer")
        self.resize(1000, 700)