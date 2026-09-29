import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from ai_project_organizer.ui.main_window import MainWindow


class FileOperationBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(
            self.temporary_directory.name
        )
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.registry_path = self.root / "config" / "projects.json"
        self.window = MainWindow(
            project_registry_path=self.registry_path
        )
        self.window._set_workspace_root(
            str(self.workspace)
        )

    def tearDown(self) -> None:
        self.window.text_editor.document().setModified(
            False
        )
        self.window.close()
        self.temporary_directory.cleanup()

    def _symlink(
            self,
            link: Path,
            target: Path,
            *,
            target_is_directory: bool = False,
    ) -> None:
        try:
            link.symlink_to(
                target,
                target_is_directory=target_is_directory,
            )
        except (OSError, NotImplementedError) as error:
            self.skipTest(
                f"Symbolic links are unavailable: {error}"
            )

    def test_save_through_external_symlink_is_rejected(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.workspace / "link.txt"
        self._symlink(link, outside)

        self.window.current_file_path = str(link)
        self.window.text_editor.setPlainText(
            "changed"
        )
        self.window.text_editor.document().setModified(
            True
        )

        with patch.object(
            QMessageBox,
            "warning",
        ) as warning:
            result = self.window._save_current_file()

        self.assertFalse(result)
        self.assertEqual(
            outside.read_text(encoding="utf-8"),
            "outside",
        )
        self.assertTrue(
            self.window.text_editor.document().isModified()
        )
        warning.assert_called_once()

    def test_create_file_through_external_directory_symlink_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        link = self.workspace / "external"
        self._symlink(
            link,
            outside,
            target_is_directory=True,
        )

        with patch.object(
            QMessageBox,
            "warning",
        ) as warning:
            self.window._create_new_file(
                str(link)
            )

        self.assertFalse(
            (outside / "created.txt").exists()
        )
        warning.assert_called_once()

    def test_normal_file_creation_still_succeeds(self) -> None:
        with patch.object(
            QInputDialog,
            "getText",
            return_value=("created.txt", True),
        ):
            self.window._create_new_file(
                str(self.workspace)
            )

        created = self.workspace / "created.txt"

        self.assertTrue(
            created.is_file()
        )
        self.assertEqual(
            self.window.current_file_path,
            str(created),
        )

    def test_dangling_symlink_blocks_file_creation_collision(self) -> None:
        missing_target = self.root / "missing.txt"
        link = self.workspace / "dangling.txt"
        self._symlink(link, missing_target)

        with (
            patch.object(
                QInputDialog,
                "getText",
                return_value=("dangling.txt", True),
            ),
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
        ):
            self.window._create_new_file(
                str(self.workspace)
            )

        self.assertTrue(
            link.is_symlink()
        )
        self.assertFalse(
            missing_target.exists()
        )
        warning.assert_called_once()

    def test_external_target_symlink_entry_can_be_renamed(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.workspace / "link.txt"
        self._symlink(link, outside)
        renamed = self.workspace / "renamed.txt"

        with patch.object(
            QInputDialog,
            "getText",
            return_value=("renamed.txt", True),
        ):
            self.window._rename_item(
                str(link)
            )

        self.assertFalse(
            link.exists()
        )
        self.assertTrue(
            renamed.is_symlink()
        )
        self.assertEqual(
            outside.read_text(encoding="utf-8"),
            "outside",
        )

    def test_external_target_symlink_entry_can_be_deleted(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.workspace / "link.txt"
        self._symlink(link, outside)

        with patch.object(
            QMessageBox,
            "exec",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._delete_item(
                str(link)
            )

        self.assertFalse(
            link.is_symlink()
        )
        self.assertTrue(
            outside.is_file()
        )
        self.assertEqual(
            outside.read_text(encoding="utf-8"),
            "outside",
        )

    def test_partial_move_failure_rebases_current_document(self) -> None:
        folder = self.workspace / "folder"
        folder.mkdir()
        document = folder / "document.txt"
        document.write_text(
            "on disk",
            encoding="utf-8",
        )
        other = self.workspace / "other.txt"
        other.write_text(
            "other",
            encoding="utf-8",
        )
        destination = self.workspace / "destination"
        destination.mkdir()

        self.window.current_file_path = str(
            document
        )
        self.window.text_editor.setPlainText(
            "unsaved editor text"
        )
        self.window.text_editor.document().setModified(
            True
        )

        move_plan = [
            (
                folder,
                destination / "folder",
            ),
            (
                other,
                destination / "other.txt",
            ),
        ]
        real_move = shutil.move
        call_count = 0

        def controlled_move(
                source: str,
                target: str,
        ):
            nonlocal call_count
            call_count += 1

            if call_count == 2:
                raise PermissionError(
                    "permission denied"
                )

            return real_move(
                source,
                target,
            )

        with (
            patch(
                "ai_project_organizer.ui.file_tree.shutil.move",
                side_effect=controlled_move,
            ),
            patch.object(
                QMessageBox,
                "warning",
            ) as warning,
        ):
            result = self.window.file_tree._execute_move_plan(
                move_plan
            )

        moved_document = (
            destination
            / "folder"
            / "document.txt"
        )

        self.assertFalse(result)
        self.assertTrue(
            moved_document.is_file()
        )
        self.assertFalse(
            document.exists()
        )
        self.assertTrue(
            other.is_file()
        )
        self.assertEqual(
            self.window.current_file_path,
            str(moved_document),
        )
        self.assertEqual(
            self.window.text_editor.toPlainText(),
            "unsaved editor text",
        )
        self.assertTrue(
            self.window.text_editor.document().isModified()
        )
        warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
