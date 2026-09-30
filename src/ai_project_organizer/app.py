import sys

from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.main_window import MainWindow
from ai_project_organizer.ui.theme import apply_application_theme


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("AI Project Organizer")

    apply_application_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()