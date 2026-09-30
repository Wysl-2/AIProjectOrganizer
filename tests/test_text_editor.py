import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication, QPlainTextEdit

from ai_project_organizer.ui.text_editor import TextEditor


class TextEditorPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = (
            QApplication.instance()
            or QApplication([])
        )

    def test_editor_uses_document_presentation(self) -> None:
        editor = TextEditor()

        self.assertEqual(
            editor.property(
                "role"
            ),
            "documentEditor",
        )
        self.assertIsNotNone(
            editor.line_number_area
        )
        self.assertEqual(
            editor.lineWrapMode(),
            QPlainTextEdit.LineWrapMode.NoWrap,
        )

        editor.close()


if __name__ == "__main__":
    unittest.main()
