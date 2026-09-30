from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QPainter, QPaintEvent, QPalette, QResizeEvent
from PySide6.QtWidgets import QPlainTextEdit, QWidget


class LineNumberArea(QWidget):
    def __init__(self, editor: "TextEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self.editor.paint_line_number_area(event)


class TextEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setProperty(
            "role",
            "documentEditor",
        )

        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(
            self._update_line_number_area_width
        )
        self.updateRequest.connect(
            self._update_line_number_area
        )

        self._update_line_number_area_width()

        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

    def line_number_area_width(self) -> int:
        digits = 1
        block_count = max(1, self.blockCount())

        while block_count >= 10:
            block_count //= 10
            digits += 1

        digit_width = self.fontMetrics().horizontalAdvance("9")

        return 10 + digit_width * digits

    def _update_line_number_area_width(
            self,
            _block_count: int = 0,
    ) -> None:
        self.setViewportMargins(
            self.line_number_area_width(),
            0,
            0,
            0,
        )

    def _update_line_number_area(
            self,
            rect: QRect,
            dy: int,
    ) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0,
                rect.y(),
                self.line_number_area.width(),
                rect.height(),
            )

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

        contents = self.contentsRect()

        self.line_number_area.setGeometry(
            QRect(
                contents.left(),
                contents.top(),
                self.line_number_area_width(),
                contents.height(),
            )
        )

    def paint_line_number_area(
            self,
            event: QPaintEvent,
    ) -> None:
        painter = QPainter(self.line_number_area)

        painter.fillRect(
            event.rect(),
            self.palette().color(
                QPalette.ColorRole.AlternateBase
            ),
        )

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()

        top = round(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )

        bottom = top + round(
            self.blockBoundingRect(block).height()
        )

        while block.isValid() and top <= event.rect().bottom():
            if (
                    block.isVisible()
                    and bottom >= event.rect().top()
            ):
                line_number = str(block_number + 1)

                painter.setPen(
                    self.palette().color(
                        QPalette.ColorRole.PlaceholderText
                    )
                )

                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    line_number,
                    )

            block = block.next()
            top = bottom

            if block.isValid():
                bottom = top + round(
                    self.blockBoundingRect(block).height()
                )

            block_number += 1
