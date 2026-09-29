import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.file_tree import FileTreeView


class FileTreeBoundaryTests(unittest.TestCase):
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
        self.view = FileTreeView()
        self.view.set_workspace_path(
            str(self.workspace)
        )

    def tearDown(self) -> None:
        self.view.close()
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

    def test_external_directory_symlink_cannot_be_move_destination(self) -> None:
        source = self.workspace / "source.txt"
        source.write_text("text", encoding="utf-8")
        outside = self.root / "outside"
        outside.mkdir()
        destination = self.workspace / "external"
        self._symlink(
            destination,
            outside,
            target_is_directory=True,
        )

        error = self.view._validate_move(
            [source],
            destination,
        )

        self.assertIsNotNone(error)
        self.assertIn(
            "outside",
            error,
        )

    def test_internal_directory_symlink_can_be_move_destination(self) -> None:
        source = self.workspace / "source.txt"
        source.write_text("text", encoding="utf-8")
        target = self.workspace / "target"
        target.mkdir()
        destination = self.workspace / "target-link"
        self._symlink(
            destination,
            target,
            target_is_directory=True,
        )

        self.assertIsNone(
            self.view._validate_move(
                [source],
                destination,
            )
        )

    def test_external_target_symlink_entry_can_be_move_source(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        source = self.workspace / "link.txt"
        self._symlink(source, outside)
        destination = self.workspace / "destination"
        destination.mkdir()

        self.assertIsNone(
            self.view._validate_move(
                [source],
                destination,
            )
        )

    def test_child_reached_through_external_directory_cannot_be_move_source(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        child = outside / "child.txt"
        child.write_text("outside", encoding="utf-8")
        link = self.workspace / "external"
        self._symlink(
            link,
            outside,
            target_is_directory=True,
        )
        destination = self.workspace / "destination"
        destination.mkdir()

        error = self.view._validate_move(
            [link / "child.txt"],
            destination,
        )

        self.assertIsNotNone(error)
        self.assertIn(
            "outside",
            error,
        )

    def test_dangling_symlink_destination_counts_as_occupied(self) -> None:
        source = self.workspace / "source.txt"
        source.write_text("text", encoding="utf-8")
        destination = self.workspace / "destination"
        destination.mkdir()
        missing_target = self.root / "missing.txt"
        collision = destination / "source.txt"
        self._symlink(collision, missing_target)

        error = self.view._validate_move(
            [source],
            destination,
        )

        self.assertIsNotNone(error)
        self.assertIn(
            "already exists",
            error,
        )

    def test_workspace_root_and_symlink_alias_have_distinct_entry_identity(self) -> None:
        alias = self.workspace / "alias"
        self._symlink(
            alias,
            self.workspace,
            target_is_directory=True,
        )

        self.assertTrue(
            self.view._is_workspace_root(
                self.workspace
            )
        )
        self.assertFalse(
            self.view._is_workspace_root(
                alias
            )
        )
        self.assertTrue(
            self.view._can_modify_entry(
                alias
            )
        )


if __name__ == "__main__":
    unittest.main()
