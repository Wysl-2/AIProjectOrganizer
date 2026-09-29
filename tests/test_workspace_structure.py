import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_project_organizer.workspace_structure import (
    PROJECT_DOCUMENTS_DIRECTORY_NAME,
    PROJECT_FEATURES_DIRECTORY_NAME,
    initialize_project_workspace_structure,
    project_documents_path,
    project_features_path,
)


class WorkspaceStructureTests(unittest.TestCase):
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

    def test_standard_paths_are_direct_workspace_children(self) -> None:
        workspace = Path(
            tempfile.gettempdir()
        ) / "workspace"

        self.assertEqual(
            project_documents_path(workspace),
            workspace / PROJECT_DOCUMENTS_DIRECTORY_NAME,
        )
        self.assertEqual(
            project_features_path(workspace),
            workspace / PROJECT_FEATURES_DIRECTORY_NAME,
        )

    def test_missing_standard_directories_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            initialize_project_workspace_structure(
                workspace
            )

            self.assertTrue(
                (workspace / "Documents").is_dir()
            )
            self.assertFalse(
                (workspace / "Documents").is_symlink()
            )
            self.assertTrue(
                (workspace / "Features").is_dir()
            )
            self.assertFalse(
                (workspace / "Features").is_symlink()
            )

    def test_existing_standard_directories_and_contents_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            documents = workspace / "Documents"
            features = workspace / "Features"
            documents.mkdir()
            features.mkdir()
            document_marker = documents / "overview.txt"
            feature_marker = features / "marker.txt"
            document_marker.write_text(
                "overview",
                encoding="utf-8",
            )
            feature_marker.write_text(
                "feature",
                encoding="utf-8",
            )

            initialize_project_workspace_structure(
                workspace
            )

            self.assertEqual(
                document_marker.read_text(encoding="utf-8"),
                "overview",
            )
            self.assertEqual(
                feature_marker.read_text(encoding="utf-8"),
                "feature",
            )

    def test_partially_initialized_workspace_creates_only_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            documents = workspace / "Documents"
            documents.mkdir()
            marker = documents / "existing.txt"
            marker.write_text(
                "preserve",
                encoding="utf-8",
            )

            initialize_project_workspace_structure(
                workspace
            )

            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "preserve",
            )
            self.assertTrue(
                (workspace / "Features").is_dir()
            )

    def test_regular_file_conflict_is_rejected_before_other_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            documents = workspace / "Documents"
            documents.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_workspace_structure(
                    workspace
                )

            self.assertEqual(
                documents.read_text(encoding="utf-8"),
                "preserve",
            )
            self.assertFalse(
                (workspace / "Features").exists()
            )

    def test_second_path_conflict_is_preflighted_before_first_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            features = workspace / "Features"
            features.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_workspace_structure(
                    workspace
                )

            self.assertFalse(
                (workspace / "Documents").exists()
            )
            self.assertEqual(
                features.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_symbolic_link_conflict_is_rejected_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            outside = root / "outside"
            outside.mkdir()
            marker = outside / "marker.txt"
            marker.write_text(
                "outside",
                encoding="utf-8",
            )
            documents = workspace / "Documents"
            self._symlink(
                documents,
                outside,
                target_is_directory=True,
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_workspace_structure(
                    workspace
                )

            self.assertTrue(
                documents.is_symlink()
            )
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "outside",
            )
            self.assertFalse(
                (workspace / "Features").exists()
            )

    def test_dangling_symbolic_link_conflict_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            missing_target = root / "missing"
            documents = workspace / "Documents"
            self._symlink(
                documents,
                missing_target,
                target_is_directory=True,
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_workspace_structure(
                    workspace
                )

            self.assertTrue(
                documents.is_symlink()
            )
            self.assertFalse(
                (workspace / "Features").exists()
            )

    def test_missing_workspace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = (
                Path(temporary_directory)
                / "missing"
            )

            with self.assertRaises(FileNotFoundError):
                initialize_project_workspace_structure(
                    workspace
                )

            self.assertFalse(
                workspace.exists()
            )

    def test_non_directory_workspace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = (
                Path(temporary_directory)
                / "workspace.txt"
            )
            workspace.write_text(
                "file",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_workspace_structure(
                    workspace
                )

    def test_initialization_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            initialize_project_workspace_structure(
                workspace
            )
            initialize_project_workspace_structure(
                workspace
            )

            self.assertTrue(
                (workspace / "Documents").is_dir()
            )
            self.assertTrue(
                (workspace / "Features").is_dir()
            )

    def test_partial_creation_failure_removes_only_directory_created_by_call(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            real_mkdir = Path.mkdir

            def controlled_mkdir(
                    path: Path,
                    *args,
                    **kwargs,
            ) -> None:
                if path.name == "Features":
                    raise PermissionError(
                        "permission denied"
                    )

                real_mkdir(
                    path,
                    *args,
                    **kwargs,
                )

            with patch(
                "ai_project_organizer.workspace_structure.Path.mkdir",
                new=controlled_mkdir,
            ):
                with self.assertRaises(PermissionError):
                    initialize_project_workspace_structure(
                        workspace
                    )

            self.assertFalse(
                (workspace / "Documents").exists()
            )
            self.assertFalse(
                (workspace / "Features").exists()
            )


if __name__ == "__main__":
    unittest.main()
