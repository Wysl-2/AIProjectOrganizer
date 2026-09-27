import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from ai_project_organizer.project_registry import (
    PROJECT_REGISTRY_SCHEMA_VERSION,
    ProjectRegistry,
    ProjectRegistryError,
    RegisteredProject,
    load_project_registry,
    save_project_registry,
)


class ProjectRegistryTests(unittest.TestCase):
    def _timestamp(
        self,
        hour: int = 12,
    ) -> datetime:
        return datetime(
            2026,
            9,
            28,
            hour,
            0,
            0,
            tzinfo=timezone.utc,
        )

    def _absolute_path(
        self,
        root: Path,
        *parts: str,
    ) -> Path:
        return root.resolve().joinpath(*parts)

    def _write_registry(
        self,
        path: Path,
        data: object,
    ) -> None:
        path.write_text(
            json.dumps(data),
            encoding="utf-8",
        )

    def _valid_mapping(
        self,
        workspace_path: Path,
        timestamp: datetime | None = None,
    ) -> dict[str, object]:
        opened_at = timestamp or self._timestamp()

        return {
            "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
            "projects": [
                {
                    "workspace_path": str(workspace_path),
                    "last_opened": opened_at.isoformat(),
                },
            ],
        }

    def test_registered_project_normalizes_absolute_workspace_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "one" / ".." / "project"

            project = RegisteredProject(
                workspace_path=workspace,
                last_opened=self._timestamp(),
            )

            self.assertEqual(
                project.workspace_path,
                root / "project",
            )

    def test_relative_workspace_path_is_rejected(self) -> None:
        with self.assertRaises(ProjectRegistryError):
            RegisteredProject(
                workspace_path=Path("relative/project"),
                last_opened=self._timestamp(),
            )

    def test_timezone_aware_timestamp_is_normalized_to_utc(self) -> None:
        offset = timezone(timedelta(hours=12))
        timestamp = datetime(
            2026,
            9,
            29,
            1,
            30,
            tzinfo=offset,
        )

        project = RegisteredProject(
            workspace_path=Path(tempfile.gettempdir()).resolve(),
            last_opened=timestamp,
        )

        self.assertEqual(
            project.last_opened,
            timestamp.astimezone(timezone.utc),
        )
        self.assertIs(
            project.last_opened.tzinfo,
            timezone.utc,
        )

    def test_naive_timestamp_is_rejected(self) -> None:
        with self.assertRaises(ProjectRegistryError):
            RegisteredProject(
                workspace_path=Path(tempfile.gettempdir()).resolve(),
                last_opened=datetime(2026, 9, 28, 12, 0, 0),
            )

    def test_projects_are_ordered_most_recent_first(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            older = RegisteredProject(
                root / "older",
                self._timestamp(10),
            )
            newer = RegisteredProject(
                root / "newer",
                self._timestamp(14),
            )

            registry = ProjectRegistry(
                [older, newer]
            )

            self.assertEqual(
                registry.projects,
                (newer, older),
            )

    def test_equal_timestamps_use_deterministic_path_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            timestamp = self._timestamp()
            project_b = RegisteredProject(
                root / "b-project",
                timestamp,
            )
            project_a = RegisteredProject(
                root / "a-project",
                timestamp,
            )

            registry = ProjectRegistry(
                [project_b, project_a]
            )

            self.assertEqual(
                [project.workspace_path.name for project in registry.projects],
                ["a-project", "b-project"],
            )

    def test_register_adds_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"
            registry = ProjectRegistry()

            project = registry.register(
                workspace,
                self._timestamp(),
            )

            self.assertTrue(
                registry.contains(workspace)
            )
            self.assertEqual(
                registry.projects,
                (project,),
            )

    def test_register_does_not_require_existing_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = (
                Path(temporary_directory)
                / "missing"
                / "project"
            )
            registry = ProjectRegistry()

            registry.register(
                workspace,
                self._timestamp(),
            )

            self.assertTrue(
                registry.contains(workspace)
            )
            self.assertFalse(
                workspace.exists()
            )

    def test_register_updates_existing_project_without_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"
            registry = ProjectRegistry()

            registry.register(
                workspace,
                self._timestamp(10),
            )
            updated = registry.register(
                workspace,
                self._timestamp(15),
            )

            self.assertEqual(
                registry.projects,
                (updated,),
            )
            self.assertEqual(
                updated.last_opened,
                self._timestamp(15),
            )

    def test_normalized_paths_share_registry_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            canonical = root / "project"
            equivalent = root / "folder" / ".." / "project"
            registry = ProjectRegistry()

            registry.register(
                canonical,
                self._timestamp(),
            )

            self.assertTrue(
                registry.contains(equivalent)
            )

    def test_distinct_projects_remain_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry = ProjectRegistry()

            registry.register(
                root / "one",
                self._timestamp(10),
            )
            registry.register(
                root / "two",
                self._timestamp(11),
            )

            self.assertEqual(
                len(registry.projects),
                2,
            )

    def test_duplicate_projects_are_rejected_during_construction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            timestamp = self._timestamp()
            first = RegisteredProject(
                root / "project",
                timestamp,
            )
            duplicate = RegisteredProject(
                root / "folder" / ".." / "project",
                timestamp,
            )

            with self.assertRaises(ProjectRegistryError):
                ProjectRegistry(
                    [first, duplicate]
                )

    def test_remove_existing_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"
            registry = ProjectRegistry()
            registry.register(
                workspace,
                self._timestamp(),
            )

            removed = registry.remove(workspace)

            self.assertTrue(removed)
            self.assertFalse(
                registry.contains(workspace)
            )

    def test_remove_missing_project_reports_no_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"
            registry = ProjectRegistry()

            self.assertFalse(
                registry.remove(workspace)
            )

    def test_remove_does_not_modify_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "project"
            workspace.mkdir()
            marker = workspace / "marker.txt"
            marker.write_text(
                "unchanged",
                encoding="utf-8",
            )
            registry = ProjectRegistry()
            registry.register(
                workspace,
                self._timestamp(),
            )

            registry.remove(workspace)

            self.assertTrue(
                workspace.is_dir()
            )
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "unchanged",
            )

    def test_missing_registry_file_returns_empty_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = (
                Path(temporary_directory)
                / "projects.json"
            )

            registry = load_project_registry(
                registry_path
            )

            self.assertEqual(
                registry.projects,
                (),
            )
            self.assertFalse(
                registry_path.exists()
            )

    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "config" / "projects.json"
            registry = ProjectRegistry()
            registry.register(
                root / "older",
                self._timestamp(10),
            )
            registry.register(
                root / "newer",
                self._timestamp(14),
            )

            saved_path = save_project_registry(
                registry,
                registry_path,
            )
            loaded = load_project_registry(
                registry_path
            )

            self.assertEqual(
                saved_path,
                registry_path,
            )
            self.assertEqual(
                loaded.projects,
                registry.projects,
            )

    def test_saved_json_uses_expected_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            workspace = root / "workspace"
            registry = ProjectRegistry()
            registry.register(
                workspace,
                self._timestamp(),
            )

            save_project_registry(
                registry,
                registry_path,
            )

            raw = json.loads(
                registry_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                raw,
                {
                    "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
                    "projects": [
                        {
                            "workspace_path": str(workspace),
                            "last_opened": self._timestamp().isoformat(),
                        },
                    ],
                },
            )
            self.assertTrue(
                registry_path.read_text(
                    encoding="utf-8"
                ).endswith("\n")
            )

    def test_save_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = (
                Path(temporary_directory)
                / "nested"
                / "config"
                / "projects.json"
            )

            save_project_registry(
                ProjectRegistry(),
                registry_path,
            )

            self.assertTrue(
                registry_path.is_file()
            )

    def test_save_preserves_recent_first_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            registry = ProjectRegistry()
            registry.register(
                root / "older",
                self._timestamp(9),
            )
            registry.register(
                root / "newer",
                self._timestamp(16),
            )

            save_project_registry(
                registry,
                registry_path,
            )

            raw = json.loads(
                registry_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                [
                    Path(entry["workspace_path"]).name
                    for entry in raw["projects"]
                ],
                ["newer", "older"],
            )

    def test_failed_replace_preserves_existing_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            original_text = '{"existing": true}\n'
            registry_path.write_text(
                original_text,
                encoding="utf-8",
            )
            registry = ProjectRegistry()
            registry.register(
                root / "project",
                self._timestamp(),
            )

            with patch(
                "ai_project_organizer.project_registry.os.replace",
                side_effect=PermissionError("permission denied"),
            ):
                with self.assertRaises(PermissionError):
                    save_project_registry(
                        registry,
                        registry_path,
                    )

            self.assertEqual(
                registry_path.read_text(
                    encoding="utf-8"
                ),
                original_text,
            )

    def test_invalid_utf8_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = (
                Path(temporary_directory)
                / "projects.json"
            )
            registry_path.write_bytes(b"\xff")

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(
                    registry_path
                )

    def test_malformed_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = (
                Path(temporary_directory)
                / "projects.json"
            )
            registry_path.write_text(
                "{not valid json",
                encoding="utf-8",
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(
                    registry_path
                )

    def test_non_object_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "projects.json"
            self._write_registry(
                registry_path,
                [],
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_missing_root_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "projects.json"
            self._write_registry(
                registry_path,
                {
                    "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
                },
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_unexpected_root_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "projects.json"
            self._write_registry(
                registry_path,
                {
                    "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
                    "projects": [],
                    "unexpected": True,
                },
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_non_integer_schema_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "projects.json"
            self._write_registry(
                registry_path,
                {
                    "schema_version": "1",
                    "projects": [],
                },
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_unsupported_schema_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "projects.json"
            self._write_registry(
                registry_path,
                {
                    "schema_version": 2,
                    "projects": [],
                },
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_projects_must_be_a_list(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "projects.json"
            self._write_registry(
                registry_path,
                {
                    "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
                    "projects": {},
                },
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_project_entry_must_be_an_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "projects.json"
            self._write_registry(
                registry_path,
                {
                    "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
                    "projects": ["invalid"],
                },
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_project_entry_missing_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            self._write_registry(
                registry_path,
                {
                    "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
                    "projects": [
                        {
                            "workspace_path": str(root / "project"),
                        },
                    ],
                },
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_project_entry_unexpected_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            data = self._valid_mapping(root / "project")
            data["projects"][0]["unexpected"] = True
            self._write_registry(
                registry_path,
                data,
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_workspace_path_must_be_a_string(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            data = self._valid_mapping(root / "project")
            data["projects"][0]["workspace_path"] = 123
            self._write_registry(
                registry_path,
                data,
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_persisted_workspace_path_must_be_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            data = self._valid_mapping(root / "project")
            data["projects"][0]["workspace_path"] = "relative/project"
            self._write_registry(
                registry_path,
                data,
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_last_opened_must_be_a_string(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            data = self._valid_mapping(root / "project")
            data["projects"][0]["last_opened"] = 123
            self._write_registry(
                registry_path,
                data,
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_invalid_timestamp_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            data = self._valid_mapping(root / "project")
            data["projects"][0]["last_opened"] = "not-a-timestamp"
            self._write_registry(
                registry_path,
                data,
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_naive_persisted_timestamp_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            data = self._valid_mapping(root / "project")
            data["projects"][0]["last_opened"] = "2026-09-28T12:00:00"
            self._write_registry(
                registry_path,
                data,
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_duplicate_normalized_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            registry_path = root / "projects.json"
            timestamp = self._timestamp().isoformat()
            self._write_registry(
                registry_path,
                {
                    "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
                    "projects": [
                        {
                            "workspace_path": str(root / "project"),
                            "last_opened": timestamp,
                        },
                        {
                            "workspace_path": str(
                                root / "folder" / ".." / "project"
                            ),
                            "last_opened": timestamp,
                        },
                    ],
                },
            )

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_registry_file_symlink_is_rejected_for_loading(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target.json"
            target.write_text(
                json.dumps(
                    {
                        "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
                        "projects": [],
                    }
                ),
                encoding="utf-8",
            )
            registry_path = root / "projects.json"

            try:
                registry_path.symlink_to(target)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"Symbolic links are unavailable: {error}")

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

    def test_registry_file_symlink_is_rejected_for_saving(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target.json"
            target.write_text(
                "unchanged",
                encoding="utf-8",
            )
            registry_path = root / "projects.json"

            try:
                registry_path.symlink_to(target)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"Symbolic links are unavailable: {error}")

            with self.assertRaises(ProjectRegistryError):
                save_project_registry(
                    ProjectRegistry(),
                    registry_path,
                )

            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "unchanged",
            )

    def test_non_file_registry_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "projects.json"
            registry_path.mkdir()

            with self.assertRaises(ProjectRegistryError):
                load_project_registry(registry_path)

            with self.assertRaises(ProjectRegistryError):
                save_project_registry(
                    ProjectRegistry(),
                    registry_path,
                )


if __name__ == "__main__":
    unittest.main()
