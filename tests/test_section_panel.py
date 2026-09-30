import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
)

from ai_project_organizer.ui.section_panel import (
    SectionPanel,
)


class SectionPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = (
            QApplication.instance()
            or QApplication([])
        )

    def test_section_exposes_title_and_semantic_roles(self) -> None:
        panel = SectionPanel(
            "DOCUMENTS"
        )

        self.assertEqual(
            panel.title_label.text(),
            "DOCUMENTS",
        )
        self.assertEqual(
            panel.title_label.property(
                "role"
            ),
            "sectionTitle",
        )
        self.assertEqual(
            panel.divider.property(
                "role"
            ),
            "sectionDivider",
        )

    def test_header_widget_is_added_to_action_area(self) -> None:
        panel = SectionPanel(
            "FEATURES"
        )
        button = QPushButton(
            "Add"
        )

        panel.add_header_widget(
            button
        )

        self.assertEqual(
            panel.header_actions_layout.count(),
            1,
        )
        self.assertIs(
            panel.header_actions_layout.itemAt(
                0
            ).widget(),
            button,
        )

    def test_content_layout_accepts_widgets(self) -> None:
        panel = SectionPanel(
            "PACKAGES"
        )
        label = QLabel(
            "Content"
        )

        panel.content_layout.addWidget(
            label
        )

        self.assertEqual(
            panel.content_layout.count(),
            1,
        )
        self.assertIs(
            panel.content_layout.itemAt(
                0
            ).widget(),
            label,
        )


if __name__ == "__main__":
    unittest.main()
