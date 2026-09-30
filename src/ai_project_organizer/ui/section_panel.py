from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class SectionPanel(QWidget):
    def __init__(
            self,
            title: str,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent
        )

        self.title_label = QLabel(
            title,
            self,
        )
        self.title_label.setProperty(
            "role",
            "sectionTitle",
        )

        self.header_actions_layout = QHBoxLayout()
        self.header_actions_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.header_actions_layout.setSpacing(
            4
        )

        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.header_layout.setSpacing(
            6
        )
        self.header_layout.addWidget(
            self.title_label
        )
        self.header_layout.addStretch(
            1
        )
        self.header_layout.addLayout(
            self.header_actions_layout
        )

        self.divider = QFrame(
            self
        )
        self.divider.setFrameShape(
            QFrame.Shape.NoFrame
        )
        self.divider.setProperty(
            "role",
            "sectionDivider",
        )
        self.divider.setFixedHeight(
            1
        )

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.content_layout.setSpacing(
            6
        )

        layout = QVBoxLayout(
            self
        )
        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        layout.setSpacing(
            6
        )
        layout.addLayout(
            self.header_layout
        )
        layout.addWidget(
            self.divider
        )
        layout.addLayout(
            self.content_layout,
            1,
        )

    def add_header_widget(
            self,
            widget: QWidget,
    ) -> None:
        self.header_actions_layout.addWidget(
            widget
        )
