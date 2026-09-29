import tempfile
import unittest
from pathlib import Path

from ai_project_organizer.workspace_paths import (
    filesystem_entry_exists,
    is_workspace_entry,
    is_workspace_target,
    same_path_entry,
)


class WorkspacePathTests(unittest.TestCase):
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

    def test_normal_internal_target_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "workspace"
            workspace.mkdir()
            file_path = workspace / "document.txt"
            file_path.write_text("text", encoding="utf-8")

            self.assertTrue(
                is_workspace_target(
                    file_path,
                    workspace,
                )
            )
            self.assertTrue(
                is_workspace_entry(
                    file_path,
                    workspace,
                )
            )

    def test_outside_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")

            self.assertFalse(
                is_workspace_target(
                    outside,
                    workspace,
                )
            )
            self.assertFalse(
                is_workspace_entry(
                    outside,
                    workspace,
                )
            )

    def test_internal_file_symlink_target_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "workspace"
            workspace.mkdir()
            target = workspace / "target.txt"
            target.write_text("text", encoding="utf-8")
            link = workspace / "link.txt"
            self._symlink(link, target)

            self.assertTrue(
                is_workspace_target(
                    link,
                    workspace,
                )
            )

    def test_external_file_symlink_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            target = root / "outside.txt"
            target.write_text("outside", encoding="utf-8")
            link = workspace / "link.txt"
            self._symlink(link, target)

            self.assertFalse(
                is_workspace_target(
                    link,
                    workspace,
                )
            )
            self.assertTrue(
                is_workspace_entry(
                    link,
                    workspace,
                )
            )

    def test_internal_directory_symlink_target_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "workspace"
            workspace.mkdir()
            target = workspace / "target"
            target.mkdir()
            link = workspace / "link"
            self._symlink(
                link,
                target,
                target_is_directory=True,
            )

            self.assertTrue(
                is_workspace_target(
                    link,
                    workspace,
                )
            )

    def test_external_directory_symlink_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            target = root / "outside"
            target.mkdir()
            link = workspace / "external"
            self._symlink(
                link,
                target,
                target_is_directory=True,
            )

            self.assertFalse(
                is_workspace_target(
                    link,
                    workspace,
                )
            )
            self.assertTrue(
                is_workspace_entry(
                    link,
                    workspace,
                )
            )

    def test_child_reached_through_external_directory_is_not_workspace_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            outside = root / "outside"
            outside.mkdir()
            child = outside / "child.txt"
            child.write_text("outside", encoding="utf-8")
            link = workspace / "external"
            self._symlink(
                link,
                outside,
                target_is_directory=True,
            )

            self.assertFalse(
                is_workspace_entry(
                    link / "child.txt",
                    workspace,
                )
            )

    def test_dangling_symlink_counts_as_existing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            missing_target = root / "missing.txt"
            link = workspace / "dangling.txt"
            self._symlink(link, missing_target)

            self.assertTrue(
                filesystem_entry_exists(link)
            )
            self.assertFalse(
                is_workspace_target(
                    link,
                    workspace,
                )
            )
            self.assertTrue(
                is_workspace_entry(
                    link,
                    workspace,
                )
            )

    def test_workspace_selected_through_symlink_uses_resolved_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            real_workspace = root / "real-workspace"
            real_workspace.mkdir()
            workspace_link = root / "workspace-link"
            self._symlink(
                workspace_link,
                real_workspace,
                target_is_directory=True,
            )
            document = real_workspace / "document.txt"
            document.write_text("text", encoding="utf-8")

            self.assertTrue(
                is_workspace_target(
                    workspace_link / "document.txt",
                    workspace_link,
                )
            )
            self.assertTrue(
                is_workspace_entry(
                    workspace_link / "document.txt",
                    workspace_link,
                )
            )

    def test_symlink_to_workspace_root_is_not_same_directory_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "workspace"
            workspace.mkdir()
            alias = workspace / "workspace-alias"
            self._symlink(
                alias,
                workspace,
                target_is_directory=True,
            )

            self.assertFalse(
                same_path_entry(
                    alias,
                    workspace,
                )
            )

    def test_symlink_loop_is_rejected_for_target_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "workspace"
            workspace.mkdir()
            first = workspace / "first"
            second = workspace / "second"
            self._symlink(first, second)
            self._symlink(second, first)

            self.assertFalse(
                is_workspace_target(
                    first,
                    workspace,
                )
            )


if __name__ == "__main__":
    unittest.main()
