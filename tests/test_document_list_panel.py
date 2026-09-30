import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
)

from ai_project_organizer.ui.document_list_panel import (
    DocumentListPanel,
)


class DocumentListPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def _texts(
            panel: DocumentListPanel,
    ) -> list[str]:
        return [
            panel.list_widget.item(index).text()
            for index in range(
                panel.list_widget.count()
            )
        ]

    @staticmethod
    def _item_for_text(
            panel: DocumentListPanel,
            text: str,
    ):
        for index in range(
            panel.list_widget.count()
        ):
            item = panel.list_widget.item(
                index
            )

            if item.text() == text:
                return item

        return None

    @staticmethod
    def _create_symlink(
            link: Path,
            target: Path,
    ) -> None:
        try:
            link.symlink_to(
                target
            )
        except (OSError, NotImplementedError) as error:
            raise unittest.SkipTest(
                f"Symbolic links are unavailable: {error}"
            )

    def test_section_presentation_uses_compact_header_action(self) -> None:
        panel = DocumentListPanel()

        self.assertEqual(
            panel.title_label.text(),
            "DOCUMENTS",
        )
        self.assertEqual(
            panel.new_document_button.text(),
            "New",
        )
        self.assertEqual(
            panel.new_document_button.property(
                "role"
            ),
            "toolbar",
        )
        self.assertFalse(
            panel.new_document_button.icon().isNull()
        )
        self.assertEqual(
            panel.status_label.property(
                "role"
            ),
            "secondary",
        )

    def test_list_is_copy_only_drag_source(self) -> None:
        panel = DocumentListPanel()

        self.assertTrue(
            panel.list_widget.dragEnabled()
        )
        self.assertFalse(
            panel.list_widget.acceptDrops()
        )
        self.assertEqual(
            panel.list_widget.dragDropMode(),
            QAbstractItemView.DragDropMode.DragOnly,
        )
        self.assertEqual(
            panel.list_widget.defaultDropAction(),
            Qt.DropAction.CopyAction,
        )

    def test_directory_is_listed_without_recursive_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)
            folder = documents / "Folder"
            folder.mkdir()
            (folder / "nested.txt").write_text(
                "nested",
                encoding="utf-8",
            )
            (documents / "B.txt").write_text(
                "b",
                encoding="utf-8",
            )
            (documents / "A.txt").write_text(
                "a",
                encoding="utf-8",
            )

            panel = DocumentListPanel()
            panel.set_directory(documents)

            self.assertEqual(
                self._texts(panel),
                [
                    "Folder",
                    "A.txt",
                    "B.txt",
                ],
            )
            self.assertNotIn(
                "nested.txt",
                self._texts(panel),
            )
            self.assertTrue(
                panel.status_label.isHidden()
            )

    def test_regular_file_is_drag_enabled_and_directory_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)
            (documents / "Folder").mkdir()
            (documents / "note.txt").write_text(
                "text",
                encoding="utf-8",
            )

            panel = DocumentListPanel()
            panel.set_directory(documents)

            folder_item = self._item_for_text(
                panel,
                "Folder",
            )
            file_item = self._item_for_text(
                panel,
                "note.txt",
            )

            self.assertIsNotNone(folder_item)
            self.assertIsNotNone(file_item)
            self.assertFalse(
                bool(
                    folder_item.flags()
                    & Qt.ItemFlag.ItemIsDragEnabled
                )
            )
            self.assertTrue(
                bool(
                    file_item.flags()
                    & Qt.ItemFlag.ItemIsDragEnabled
                )
            )

    def test_symlink_is_not_drag_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)
            target = documents / "target.txt"
            target.write_text(
                "target",
                encoding="utf-8",
            )
            link = documents / "link.txt"
            self._create_symlink(
                link,
                target,
            )

            panel = DocumentListPanel()
            panel.set_directory(documents)

            link_item = self._item_for_text(
                panel,
                "link.txt",
            )

            self.assertIsNotNone(link_item)
            self.assertFalse(
                bool(
                    link_item.flags()
                    & Qt.ItemFlag.ItemIsDragEnabled
                )
            )

    def test_regular_file_mime_data_contains_local_file_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)
            file_path = documents / "note.txt"
            file_path.write_text(
                "text",
                encoding="utf-8",
            )

            panel = DocumentListPanel()
            panel.set_directory(documents)

            item = panel.list_widget.item(0)
            mime_data = panel.list_widget.mimeData(
                [item]
            )

            self.assertIsNotNone(mime_data)
            self.assertTrue(
                mime_data.hasUrls()
            )
            self.assertEqual(
                len(
                    mime_data.urls()
                ),
                1,
            )
            url = mime_data.urls()[0]
            self.assertTrue(
                url.isLocalFile()
            )
            self.assertEqual(
                Path(
                    url.toLocalFile()
                ),
                file_path.absolute(),
            )

    def test_stale_file_does_not_create_drag_mime_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)
            file_path = documents / "note.txt"
            file_path.write_text(
                "text",
                encoding="utf-8",
            )

            panel = DocumentListPanel()
            panel.set_directory(documents)
            item = panel.list_widget.item(0)

            file_path.unlink()

            self.assertIsNone(
                panel.list_widget.mimeData(
                    [item]
                )
            )

    def test_empty_directory_shows_empty_state_and_allows_new_document(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)

            panel = DocumentListPanel()
            panel.set_directory(documents)

            self.assertEqual(
                panel.list_widget.count(),
                0,
            )
            self.assertFalse(
                panel.status_label.isHidden()
            )
            self.assertEqual(
                panel.status_label.text(),
                "No Documents.",
            )
            self.assertTrue(
                panel.new_document_button.isEnabled()
            )

    def test_empty_state_clears_when_document_is_added(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)

            panel = DocumentListPanel()
            panel.set_directory(documents)

            self.assertEqual(
                panel.status_label.text(),
                "No Documents.",
            )

            document = documents / "note.txt"
            document.write_text(
                "text",
                encoding="utf-8",
            )
            panel.refresh()

            self.assertTrue(
                panel.status_label.isHidden()
            )
            self.assertEqual(
                panel.status_label.text(),
                "",
            )
            self.assertEqual(
                self._texts(panel),
                [
                    "note.txt"
                ],
            )

    def test_file_activation_emits_real_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)
            file_path = documents / "note.txt"
            file_path.write_text(
                "text",
                encoding="utf-8",
            )

            panel = DocumentListPanel()
            panel.set_directory(documents)

            emitted: list[str] = []
            panel.file_open_requested.connect(
                emitted.append
            )

            panel._activate_item(
                panel.list_widget.item(0)
            )

            self.assertEqual(
                emitted,
                [
                    str(file_path)
                ],
            )

    def test_directory_activation_does_not_emit_file_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)
            (documents / "Folder").mkdir()

            panel = DocumentListPanel()
            panel.set_directory(documents)

            emitted: list[str] = []
            panel.file_open_requested.connect(
                emitted.append
            )

            panel._activate_item(
                panel.list_widget.item(0)
            )

            self.assertEqual(
                emitted,
                [],
            )

    def test_new_document_emits_documents_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = Path(temporary_directory)

            panel = DocumentListPanel()
            panel.set_directory(documents)

            emitted: list[str] = []
            panel.new_document_requested.connect(
                emitted.append
            )

            panel._request_new_document()

            self.assertEqual(
                emitted,
                [
                    str(documents)
                ],
            )

    def test_unavailable_directory_clears_stale_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents = root / "Documents"
            documents.mkdir()
            (documents / "note.txt").write_text(
                "text",
                encoding="utf-8",
            )

            panel = DocumentListPanel()
            panel.set_directory(documents)
            self.assertEqual(
                panel.list_widget.count(),
                1,
            )

            missing = root / "Missing"
            panel.set_directory(missing)

            self.assertEqual(
                panel.list_widget.count(),
                0,
            )
            self.assertFalse(
                panel.new_document_button.isEnabled()
            )
            self.assertIn(
                "unavailable",
                panel.status_label.text().lower(),
            )


if __name__ == "__main__":
    unittest.main()
