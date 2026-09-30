from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QWidget,
)

from ai_project_organizer.ui.resources import (
    load_icon,
)
from ai_project_organizer.ui.section_panel import (
    SectionPanel,
)


_ENTRY_PATH_ROLE = int(Qt.ItemDataRole.UserRole)
_ENTRY_REAL_DIRECTORY_ROLE = _ENTRY_PATH_ROLE + 1


class DocumentListPanel(SectionPanel):
    file_open_requested = Signal(str)
    new_document_requested = Signal(str)

    def __init__(
            self,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "DOCUMENTS",
            parent,
        )

        self.directory_path: Path | None = None

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        self.status_label.setProperty(
            "role",
            "secondary",
        )
        self.status_label.hide()

        self.list_widget = QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(
            self._activate_item
        )

        self.new_document_button = QPushButton(
            "New",
            self,
        )
        self.new_document_button.setProperty(
            "role",
            "toolbar",
        )
        self.new_document_button.setIcon(
            load_icon(
                "add-rounded.svg"
            )
        )
        self.new_document_button.clicked.connect(
            self._request_new_document
        )
        self.add_header_widget(
            self.new_document_button
        )

        self.content_layout.addWidget(
            self.status_label
        )
        self.content_layout.addWidget(
            self.list_widget,
            1,
        )

        self._update_enabled_state()

    def set_directory(
            self,
            directory_path: str | Path | None,
    ) -> None:
        self.directory_path = (
            Path(directory_path).expanduser()
            if directory_path is not None
            else None
        )
        self.refresh()

    def refresh(self) -> None:
        self.list_widget.clear()
        self.status_label.clear()
        self.status_label.hide()

        directory = self.directory_path

        if directory is None:
            self._update_enabled_state()
            return

        if (
                directory.is_symlink()
                or not directory.exists()
                or not directory.is_dir()
        ):
            self._show_status(
                "Documents directory unavailable."
            )
            self._update_enabled_state()
            return

        try:
            entries = list(directory.iterdir())
        except OSError as error:
            self._show_status(
                f"Unable to read Documents: {error}"
            )
            self._update_enabled_state()
            return

        entries.sort(
            key=lambda entry: (
                0
                if (
                    entry.is_dir()
                    and not entry.is_symlink()
                )
                else 1,
                entry.name.casefold(),
                entry.name,
            )
        )

        if not entries:
            self._show_status(
                "No Documents."
            )
            self._update_enabled_state()
            return

        for entry in entries:
            real_directory = (
                entry.is_dir()
                and not entry.is_symlink()
            )
            item = QListWidgetItem(entry.name)
            item.setData(
                _ENTRY_PATH_ROLE,
                str(entry),
            )
            item.setData(
                _ENTRY_REAL_DIRECTORY_ROLE,
                real_directory,
            )
            self.list_widget.addItem(item)

        self._update_enabled_state()

    def _activate_item(
            self,
            item: QListWidgetItem,
    ) -> None:
        if bool(
            item.data(
                _ENTRY_REAL_DIRECTORY_ROLE
            )
        ):
            return

        path_text = item.data(
            _ENTRY_PATH_ROLE
        )

        if not path_text:
            return

        self.file_open_requested.emit(
            str(path_text)
        )

    def _request_new_document(
            self,
    ) -> None:
        directory = self.directory_path

        if (
                directory is None
                or directory.is_symlink()
                or not directory.exists()
                or not directory.is_dir()
        ):
            return

        self.new_document_requested.emit(
            str(directory)
        )

    def _show_status(
            self,
            text: str,
    ) -> None:
        self.status_label.setText(text)
        self.status_label.show()

    def _update_enabled_state(
            self,
    ) -> None:
        directory = self.directory_path
        available = (
            directory is not None
            and not directory.is_symlink()
            and directory.exists()
            and directory.is_dir()
        )

        self.new_document_button.setEnabled(
            available
        )
