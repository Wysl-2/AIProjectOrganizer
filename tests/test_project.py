import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_project_organizer.project import (
    PROJECT_METADATA_FILENAME,
    PROJECT_METADATA_SCHEMA_VERSION,
    ProjectMetadata,
    ProjectMetadataError,
    create_project_workspace,
    load_project_metadata,
    save_project_metadata,
)


class ProjectMetadataTests(unittest.TestCase):
    def _absolute_path(self, *parts: str) -> Path:
        return Path(tempfile.gettempdir()).resolve().joinpath(*parts)

    def _metadata(self) -> ProjectMetadata:
        working_directory = self._absolute_path(
            "development",
            "WorldMeshes",
        )
        local_git_repository = working_directory / "Assets" / "WorldMeshes"

        return ProjectMetadata(
            name="WorldMeshes",
            working_directory=working_directory,
            local_git_repository=local_git_repository,
            github_repository="Wysl-2/WorldMeshes",
        )

    def _updated_metadata(self) -> ProjectMetadata:
        metadata = self._metadata()

        return ProjectMetadata(
            name="Updated WorldMeshes",
            working_directory=metadata.working_directory,
            local_git_repository=metadata.local_git_repository,
            github_repository=metadata.github_repository,
        )

    def _write_metadata(self, workspace: Path, data: object) -> Path:
        metadata_path = workspace / PROJECT_METADATA_FILENAME
        metadata_path.write_text(
            json.dumps(data),
            encoding="utf-8",
        )
        return metadata_path

    def _temporary_metadata_paths(
            self,
            workspace: Path,
    ) -> list[Path]:
        return list(
            workspace.glob(
                f".{PROJECT_METADATA_FILENAME}.*.tmp"
            )
        )

    def test_valid_metadata_is_normalized(self) -> None:
        metadata = ProjectMetadata(
            name="  WorldMeshes  ",
            working_directory=self._absolute_path("development", "WorldMeshes"),
            local_git_repository=self._absolute_path(
                "development",
                "WorldMeshes",
                "Assets",
                "WorldMeshes",
            ),
            github_repository="  Wysl-2/WorldMeshes  ",
        )

        self.assertEqual(metadata.name, "WorldMeshes")
        self.assertEqual(metadata.github_repository, "Wysl-2/WorldMeshes")
        self.assertIsInstance(metadata.working_directory, Path)
        self.assertIsInstance(metadata.local_git_repository, Path)

    def test_blank_project_name_is_rejected(self) -> None:
        with self.assertRaises(ProjectMetadataError):
            ProjectMetadata(
                name="   ",
                working_directory=self._absolute_path("project"),
                local_git_repository=self._absolute_path("repository"),
                github_repository="Wysl-2/WorldMeshes",
            )

    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            metadata = self._metadata()

            saved_path = save_project_metadata(workspace, metadata)
            loaded = load_project_metadata(workspace)

            self.assertEqual(
                saved_path,
                workspace / PROJECT_METADATA_FILENAME,
            )
            self.assertEqual(loaded, metadata)

    def test_saved_json_uses_expected_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            metadata = self._metadata()

            metadata_path = save_project_metadata(workspace, metadata)
            raw = json.loads(metadata_path.read_text(encoding="utf-8"))

            self.assertEqual(
                raw,
                {
                    "schema_version": PROJECT_METADATA_SCHEMA_VERSION,
                    "name": "WorldMeshes",
                    "working_directory": str(metadata.working_directory),
                    "local_git_repository": str(metadata.local_git_repository),
                    "github_repository": "Wysl-2/WorldMeshes",
                },
            )
            self.assertTrue(
                metadata_path.read_text(encoding="utf-8").endswith("\n")
            )

    def test_successful_save_replaces_existing_metadata_without_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            initial = self._metadata()
            updated = self._updated_metadata()

            save_project_metadata(
                workspace,
                initial,
            )
            save_project_metadata(
                workspace,
                updated,
            )

            self.assertEqual(
                load_project_metadata(workspace),
                updated,
            )
            self.assertEqual(
                self._temporary_metadata_paths(
                    workspace
                ),
                [],
            )

    def test_failed_replace_preserves_existing_metadata_and_cleans_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            initial = self._metadata()
            updated = self._updated_metadata()
            metadata_path = save_project_metadata(
                workspace,
                initial,
            )
            original_text = metadata_path.read_text(
                encoding="utf-8"
            )

            with patch(
                "ai_project_organizer.project.os.replace",
                side_effect=PermissionError(
                    "permission denied"
                ),
            ):
                with self.assertRaises(
                    PermissionError
                ):
                    save_project_metadata(
                        workspace,
                        updated,
                    )

            self.assertEqual(
                metadata_path.read_text(
                    encoding="utf-8"
                ),
                original_text,
            )
            self.assertEqual(
                load_project_metadata(workspace),
                initial,
            )
            self.assertEqual(
                self._temporary_metadata_paths(
                    workspace
                ),
                [],
            )

    def test_failed_fsync_preserves_existing_metadata_and_cleans_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            initial = self._metadata()
            updated = self._updated_metadata()
            metadata_path = save_project_metadata(
                workspace,
                initial,
            )
            original_text = metadata_path.read_text(
                encoding="utf-8"
            )

            with patch(
                "ai_project_organizer.project.os.fsync",
                side_effect=OSError(
                    "sync failed"
                ),
            ):
                with self.assertRaises(OSError):
                    save_project_metadata(
                        workspace,
                        updated,
                    )

            self.assertEqual(
                metadata_path.read_text(
                    encoding="utf-8"
                ),
                original_text,
            )
            self.assertEqual(
                self._temporary_metadata_paths(
                    workspace
                ),
                [],
            )

    def test_failed_initial_replace_leaves_no_metadata_or_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            with patch(
                "ai_project_organizer.project.os.replace",
                side_effect=PermissionError(
                    "permission denied"
                ),
            ):
                with self.assertRaises(
                    PermissionError
                ):
                    save_project_metadata(
                        workspace,
                        self._metadata(),
                    )

            self.assertFalse(
                (
                    workspace
                    / PROJECT_METADATA_FILENAME
                ).exists()
            )
            self.assertEqual(
                self._temporary_metadata_paths(
                    workspace
                ),
                [],
            )

    def test_missing_metadata_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            self.assertIsNone(load_project_metadata(workspace))

    def test_malformed_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            metadata_path = workspace / PROJECT_METADATA_FILENAME
            metadata_path.write_text("{not valid json", encoding="utf-8")

            with self.assertRaises(ProjectMetadataError):
                load_project_metadata(workspace)

    def test_invalid_utf8_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            metadata_path = workspace / PROJECT_METADATA_FILENAME
            metadata_path.write_bytes(b"\xff")

            with self.assertRaises(ProjectMetadataError):
                load_project_metadata(workspace)

    def test_non_object_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            self._write_metadata(workspace, ["not", "an", "object"])

            with self.assertRaises(ProjectMetadataError):
                load_project_metadata(workspace)

    def test_missing_required_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            self._write_metadata(
                workspace,
                {
                    "schema_version": 1,
                    "name": "WorldMeshes",
                    "working_directory": str(
                        self._absolute_path("development", "WorldMeshes")
                    ),
                    "local_git_repository": str(
                        self._absolute_path("repository", "WorldMeshes")
                    ),
                },
            )

            with self.assertRaises(ProjectMetadataError):
                load_project_metadata(workspace)

    def test_unexpected_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            self._write_metadata(
                workspace,
                {
                    "schema_version": 1,
                    "name": "WorldMeshes",
                    "working_directory": str(
                        self._absolute_path("development", "WorldMeshes")
                    ),
                    "local_git_repository": str(
                        self._absolute_path("repository", "WorldMeshes")
                    ),
                    "github_repository": "Wysl-2/WorldMeshes",
                    "unexpected": True,
                },
            )

            with self.assertRaises(ProjectMetadataError):
                load_project_metadata(workspace)

    def test_unsupported_schema_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            self._write_metadata(
                workspace,
                {
                    "schema_version": 2,
                    "name": "WorldMeshes",
                    "working_directory": str(
                        self._absolute_path("development", "WorldMeshes")
                    ),
                    "local_git_repository": str(
                        self._absolute_path("repository", "WorldMeshes")
                    ),
                    "github_repository": "Wysl-2/WorldMeshes",
                },
            )

            with self.assertRaises(ProjectMetadataError):
                load_project_metadata(workspace)

    def test_relative_working_directory_is_rejected(self) -> None:
        with self.assertRaises(ProjectMetadataError):
            ProjectMetadata(
                name="WorldMeshes",
                working_directory=Path("relative/project"),
                local_git_repository=self._absolute_path("repository"),
                github_repository="Wysl-2/WorldMeshes",
            )

    def test_relative_git_repository_is_rejected(self) -> None:
        with self.assertRaises(ProjectMetadataError):
            ProjectMetadata(
                name="WorldMeshes",
                working_directory=self._absolute_path("project"),
                local_git_repository=Path("relative/repository"),
                github_repository="Wysl-2/WorldMeshes",
            )

    def test_invalid_github_repository_is_rejected(self) -> None:
        invalid_values = [
            "",
            "WorldMeshes",
            "Wysl-2/WorldMeshes/Extra",
            "/WorldMeshes",
            "Wysl-2/",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ProjectMetadataError):
                    ProjectMetadata(
                        name="WorldMeshes",
                        working_directory=self._absolute_path("project"),
                        local_git_repository=self._absolute_path("repository"),
                        github_repository=value,
                    )

    def test_wrong_field_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            self._write_metadata(
                workspace,
                {
                    "schema_version": 1,
                    "name": "WorldMeshes",
                    "working_directory": 123,
                    "local_git_repository": "/repository",
                    "github_repository": "Wysl-2/WorldMeshes",
                },
            )

            with self.assertRaises(ProjectMetadataError):
                load_project_metadata(workspace)

    def test_save_requires_existing_workspace_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_workspace = Path(temporary_directory) / "missing"

            with self.assertRaises(FileNotFoundError):
                save_project_metadata(
                    missing_workspace,
                    self._metadata(),
                )

    def test_metadata_symlink_is_rejected_for_loading(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            target = root / "outside.json"
            target.write_text("{}", encoding="utf-8")
            metadata_path = workspace / PROJECT_METADATA_FILENAME

            try:
                metadata_path.symlink_to(target)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"Symbolic links are unavailable: {error}")

            with self.assertRaises(ProjectMetadataError):
                load_project_metadata(workspace)

    def test_metadata_symlink_is_rejected_for_saving(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "workspace"
            workspace.mkdir()
            target = root / "outside.json"
            target.write_text("unchanged", encoding="utf-8")
            metadata_path = workspace / PROJECT_METADATA_FILENAME

            try:
                metadata_path.symlink_to(target)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"Symbolic links are unavailable: {error}")

            with self.assertRaises(ProjectMetadataError):
                save_project_metadata(
                    workspace,
                    self._metadata(),
                )

            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "unchanged",
            )

    def test_create_project_workspace_creates_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "CreatedProject"
            metadata = self._metadata()

            created = create_project_workspace(
                workspace,
                metadata,
            )

            self.assertEqual(
                created,
                workspace,
            )
            self.assertTrue(
                workspace.is_dir()
            )
            self.assertEqual(
                load_project_metadata(workspace),
                metadata,
            )
            self.assertTrue(
                (workspace / "Documents").is_dir()
            )
            self.assertTrue(
                (workspace / "Features").is_dir()
            )

    def test_create_project_workspace_rejects_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "existing"
            workspace.mkdir()

            with self.assertRaises(FileExistsError):
                create_project_workspace(
                    workspace,
                    self._metadata(),
                )

    def test_create_project_workspace_requires_existing_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = (
                Path(temporary_directory)
                / "missing"
                / "project"
            )

            with self.assertRaises(FileNotFoundError):
                create_project_workspace(
                    workspace,
                    self._metadata(),
                )

    def test_create_project_workspace_requires_directory_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            parent = root / "parent"
            parent.write_text(
                "file",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                create_project_workspace(
                    parent / "project",
                    self._metadata(),
                )

    def test_create_project_workspace_rejects_relative_path(self) -> None:
        with self.assertRaises(ProjectMetadataError):
            create_project_workspace(
                Path("relative/project"),
                self._metadata(),
            )

    def test_failed_initial_metadata_save_removes_empty_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"

            with patch(
                "ai_project_organizer.project.save_project_metadata",
                side_effect=PermissionError("permission denied"),
            ):
                with self.assertRaises(PermissionError):
                    create_project_workspace(
                        workspace,
                        self._metadata(),
                    )

            self.assertFalse(
                workspace.exists()
            )

    def test_failed_atomic_metadata_replace_removes_empty_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"

            with patch(
                "ai_project_organizer.project.os.replace",
                side_effect=PermissionError(
                    "permission denied"
                ),
            ):
                with self.assertRaises(
                    PermissionError
                ):
                    create_project_workspace(
                        workspace,
                        self._metadata(),
                    )

            self.assertFalse(
                workspace.exists()
            )

    def test_failed_initial_metadata_save_never_recursively_deletes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"

            def fail_after_writing(
                    created_workspace: Path,
                    _metadata: ProjectMetadata,
            ) -> None:
                (created_workspace / "marker.txt").write_text(
                    "preserve",
                    encoding="utf-8",
                )
                raise PermissionError("permission denied")

            with patch(
                "ai_project_organizer.project.save_project_metadata",
                side_effect=fail_after_writing,
            ):
                with self.assertRaises(PermissionError):
                    create_project_workspace(
                        workspace,
                        self._metadata(),
                    )

            self.assertTrue(
                workspace.is_dir()
            )
            self.assertEqual(
                (workspace / "marker.txt").read_text(encoding="utf-8"),
                "preserve",
            )

    def test_failed_workspace_structure_initialization_cleans_created_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"

            with patch(
                "ai_project_organizer.project.initialize_project_workspace_structure",
                side_effect=PermissionError(
                    "permission denied"
                ),
            ):
                with self.assertRaises(PermissionError):
                    create_project_workspace(
                        workspace,
                        self._metadata(),
                    )

            self.assertFalse(
                workspace.exists()
            )


if __name__ == "__main__":
    unittest.main()
