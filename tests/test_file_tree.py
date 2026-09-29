import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


class FileTreeMovePlanningTests(unittest.TestCase):
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
        self.destination = self.workspace / "destination"
        self.destination.mkdir()
        self.view = FileTreeView()
        self.view.set_workspace_path(
            str(self.workspace)
        )

    def tearDown(self) -> None:
        self.view.close()
        self.temporary_directory.cleanup()

    def test_duplicate_planned_destinations_are_rejected(self) -> None:
        first_directory = self.workspace / "first"
        second_directory = self.workspace / "second"
        first_directory.mkdir()
        second_directory.mkdir()
        first = first_directory / "report.txt"
        second = second_directory / "report.txt"
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")

        move_plan, error = self.view._build_move_plan(
            [first, second],
            self.destination,
        )

        self.assertEqual(
            move_plan,
            [],
        )
        self.assertIsNotNone(error)
        self.assertIn(
            "Multiple selected items",
            error,
        )
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())
        self.assertFalse(
            (self.destination / "report.txt").exists()
        )

    def test_distinct_sources_build_complete_move_plan(self) -> None:
        first = self.workspace / "first.txt"
        second = self.workspace / "second.txt"
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")

        move_plan, error = self.view._build_move_plan(
            [first, second],
            self.destination,
        )

        self.assertIsNone(error)
        self.assertEqual(
            move_plan,
            [
                (
                    first,
                    self.destination / "first.txt",
                ),
                (
                    second,
                    self.destination / "second.txt",
                ),
            ],
        )

    def test_no_op_source_is_omitted_from_move_plan(self) -> None:
        source = self.destination / "source.txt"
        source.write_text("text", encoding="utf-8")

        move_plan, error = self.view._build_move_plan(
            [source],
            self.destination,
        )

        self.assertIsNone(error)
        self.assertEqual(
            move_plan,
            [],
        )

    def test_nested_source_is_omitted_from_move_plan(self) -> None:
        folder = self.workspace / "folder"
        folder.mkdir()
        child = folder / "child.txt"
        child.write_text("text", encoding="utf-8")

        move_plan, error = self.view._build_move_plan(
            [child, folder],
            self.destination,
        )

        self.assertIsNone(error)
        self.assertEqual(
            move_plan,
            [
                (
                    folder,
                    self.destination / "folder",
                )
            ],
        )

    def test_successful_execution_emits_all_completed_moves_once(self) -> None:
        first = self.workspace / "first.txt"
        second = self.workspace / "second.txt"
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")
        move_plan = [
            (
                first,
                self.destination / "first.txt",
            ),
            (
                second,
                self.destination / "second.txt",
            ),
        ]
        moved_signals: list[dict[str, str]] = []
        failed_signals: list[str] = []

        self.view.paths_moved.connect(
            lambda mapping: moved_signals.append(
                dict(mapping)
            )
        )
        self.view.move_failed.connect(
            failed_signals.append
        )

        result = self.view._execute_move_plan(
            move_plan
        )

        self.assertTrue(result)
        self.assertEqual(
            len(moved_signals),
            1,
        )
        self.assertEqual(
            moved_signals[0],
            {
                str(first): str(
                    self.destination / "first.txt"
                ),
                str(second): str(
                    self.destination / "second.txt"
                ),
            },
        )
        self.assertEqual(
            failed_signals,
            [],
        )
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())
        self.assertTrue(
            (self.destination / "first.txt").is_file()
        )
        self.assertTrue(
            (self.destination / "second.txt").is_file()
        )

    def test_partial_failure_emits_completed_paths_before_failure(self) -> None:
        first = self.workspace / "first.txt"
        second = self.workspace / "second.txt"
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")
        move_plan = [
            (
                first,
                self.destination / "first.txt",
            ),
            (
                second,
                self.destination / "second.txt",
            ),
        ]
        real_move = shutil.move
        call_count = 0
        signal_order: list[str] = []
        moved_signals: list[dict[str, str]] = []
        failed_signals: list[str] = []

        def controlled_move(
                source: str,
                destination: str,
        ):
            nonlocal call_count
            call_count += 1

            if call_count == 2:
                raise PermissionError(
                    "permission denied"
                )

            return real_move(
                source,
                destination,
            )

        self.view.paths_moved.connect(
            lambda mapping: (
                signal_order.append("moved"),
                moved_signals.append(
                    dict(mapping)
                ),
            )
        )
        self.view.move_failed.connect(
            lambda message: (
                signal_order.append("failed"),
                failed_signals.append(message),
            )
        )

        with patch(
            "ai_project_organizer.ui.file_tree.shutil.move",
            side_effect=controlled_move,
        ):
            result = self.view._execute_move_plan(
                move_plan
            )

        self.assertFalse(result)
        self.assertEqual(
            signal_order,
            [
                "moved",
                "failed",
            ],
        )
        self.assertEqual(
            moved_signals,
            [
                {
                    str(first): str(
                        self.destination / "first.txt"
                    )
                }
            ],
        )
        self.assertEqual(
            len(failed_signals),
            1,
        )
        self.assertIn(
            "permission denied",
            failed_signals[0],
        )
        self.assertFalse(first.exists())
        self.assertTrue(
            (self.destination / "first.txt").is_file()
        )
        self.assertTrue(second.is_file())
        self.assertFalse(
            (self.destination / "second.txt").exists()
        )

    def test_first_move_failure_does_not_emit_empty_paths_mapping(self) -> None:
        source = self.workspace / "source.txt"
        source.write_text("text", encoding="utf-8")
        move_plan = [
            (
                source,
                self.destination / "source.txt",
            )
        ]
        moved_signals: list[dict[str, str]] = []
        failed_signals: list[str] = []

        self.view.paths_moved.connect(
            lambda mapping: moved_signals.append(
                dict(mapping)
            )
        )
        self.view.move_failed.connect(
            failed_signals.append
        )

        with patch(
            "ai_project_organizer.ui.file_tree.shutil.move",
            side_effect=PermissionError(
                "permission denied"
            ),
        ):
            result = self.view._execute_move_plan(
                move_plan
            )

        self.assertFalse(result)
        self.assertEqual(
            moved_signals,
            [],
        )
        self.assertEqual(
            len(failed_signals),
            1,
        )
        self.assertTrue(source.is_file())
        self.assertFalse(
            (self.destination / "source.txt").exists()
        )


if __name__ == "__main__":
    unittest.main()
