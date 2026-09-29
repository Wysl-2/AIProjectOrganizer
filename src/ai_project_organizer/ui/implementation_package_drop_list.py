from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QWidget,
)


def local_zip_candidate(
        mime_data,
) -> Path | None:
    urls = mime_data.urls()

    if len(urls) != 1:
        return None

    url = urls[0]

    if not url.isLocalFile():
        return None

    local_path = url.toLocalFile()

    if not local_path:
        return None

    path = Path(
        local_path
    )

    if (
            path.is_symlink()
            or not path.exists()
            or not path.is_file()
            or path.suffix.casefold() != ".zip"
    ):
        return None

    return path


class ImplementationPackageDropListWidget(QListWidget):
    package_drop_requested = Signal(
        str,
        str,
    )

    def __init__(
            self,
            *,
            target_role: int,
            allow_background: bool,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent
        )

        self._target_role = target_role
        self._allow_background = allow_background

        self.setAcceptDrops(
            True
        )
        self.setDropIndicatorShown(
            True
        )
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.DropOnly
        )
        self.setDefaultDropAction(
            Qt.DropAction.CopyAction
        )

    def _drop_target_at(
            self,
            position: QPoint,
    ) -> str | None:
        item = self.itemAt(
            position
        )

        if item is None:
            return (
                ""
                if self._allow_background
                else None
            )

        value = item.data(
            self._target_role
        )

        if not value:
            return None

        return str(
            value
        )

    def dragEnterEvent(
            self,
            event: QDragEnterEvent,
    ) -> None:
        if local_zip_candidate(
                event.mimeData()
        ) is None:
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
        if local_zip_candidate(
                event.mimeData()
        ) is None:
            event.ignore()
            return

        target = self._drop_target_at(
            event.position().toPoint()
        )

        if target is None:
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.CopyAction
        )
        event.accept()

    def dragLeaveEvent(
            self,
            event: QDragLeaveEvent,
    ) -> None:
        super().dragLeaveEvent(
            event
        )

    def dropEvent(
            self,
            event: QDropEvent,
    ) -> None:
        source = local_zip_candidate(
            event.mimeData()
        )
        target = self._drop_target_at(
            event.position().toPoint()
        )

        if (
                source is None
                or target is None
        ):
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.CopyAction
        )
        event.accept()

        self.package_drop_requested.emit(
            str(
                source
            ),
            target,
        )
