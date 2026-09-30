import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_project_organizer.workspace_structure import (
    FEATURE_DOCUMENTS_DIRECTORY_NAME,
    FEATURE_PACKAGES_DIRECTORY_NAME,
    PACKAGE_CONTENTS_DIRECTORY_NAME,
    PACKAGE_DOCUMENTS_DIRECTORY_NAME,
    PACKAGE_PATCHES_DIRECTORY_NAME,
    PATCH_CONTENTS_DIRECTORY_NAME,
    PATCH_DOCUMENTS_DIRECTORY_NAME,
    PROJECT_DOCUMENTS_DIRECTORY_NAME,
    PROJECT_FEATURES_DIRECTORY_NAME,
    PROJECT_PATCHES_DIRECTORY_NAME,
    create_package_patch,
    create_project_feature,
    create_project_package,
    create_project_patch,
    discover_feature_packages,
    discover_package_patches,
    discover_project_features,
    discover_project_patches,
    feature_documents_path,
    feature_packages_path,
    initialize_package_patch_structure,
    initialize_project_feature_structure,
    initialize_project_package_structure,
    initialize_project_patch_structure,
    initialize_project_workspace_structure,
    is_package_patch_structure_initialized,
    is_project_package_structure_initialized,
    is_project_patch_structure_initialized,
    is_project_feature_structure_initialized,
    is_project_workspace_structure_initialized,
    package_contents_path,
    package_documents_path,
    package_patch_path,
    package_patches_path,
    patch_contents_path,
    patch_documents_path,
    project_documents_path,
    project_feature_path,
    project_features_path,
    project_package_path,
    project_patch_path,
    project_patches_path,
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

    def _initialized_workspace(
            self,
            root: Path,
    ) -> Path:
        workspace = root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(
            workspace
        )
        return workspace

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

    def test_feature_paths_use_standard_feature_children(self) -> None:
        workspace = (
            Path(tempfile.gettempdir())
            / "workspace"
        )
        feature = project_feature_path(
            workspace,
            "Filesystem Safety",
        )

        self.assertEqual(
            feature,
            workspace / "Features" / "Filesystem Safety",
        )
        self.assertEqual(
            feature_documents_path(feature),
            feature / FEATURE_DOCUMENTS_DIRECTORY_NAME,
        )
        self.assertEqual(
            feature_packages_path(feature),
            feature / FEATURE_PACKAGES_DIRECTORY_NAME,
        )

    def test_package_paths_use_standard_package_children(self) -> None:
        workspace = (
            Path(tempfile.gettempdir())
            / "workspace"
        )
        package = project_package_path(
            workspace,
            "Filesystem Drag Drop",
            "FI03",
        )

        self.assertEqual(
            package,
            (
                workspace
                / "Features"
                / "Filesystem Drag Drop"
                / "Packages"
                / "FI03"
            ),
        )
        self.assertEqual(
            package_documents_path(package),
            package / PACKAGE_DOCUMENTS_DIRECTORY_NAME,
        )
        self.assertEqual(
            package_contents_path(package),
            package / PACKAGE_CONTENTS_DIRECTORY_NAME,
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

    def test_project_structure_readiness_reports_missing_and_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            self.assertFalse(
                is_project_workspace_structure_initialized(
                    workspace
                )
            )

            initialize_project_workspace_structure(
                workspace
            )

            self.assertTrue(
                is_project_workspace_structure_initialized(
                    workspace
                )
            )

    def test_project_structure_readiness_rejects_conflicting_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            (workspace / "Features").write_text(
                "conflict",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                is_project_workspace_structure_initialized(
                    workspace
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

    def test_create_feature_builds_complete_standard_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )

            feature = create_project_feature(
                workspace,
                "Filesystem Safety",
            )

            self.assertEqual(
                feature,
                workspace / "Features" / "Filesystem Safety",
            )
            self.assertTrue(
                (feature / "Documents").is_dir()
            )
            self.assertTrue(
                (feature / "Packages").is_dir()
            )

    def test_create_feature_normalizes_surrounding_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )

            feature = create_project_feature(
                workspace,
                "  Filesystem Safety  ",
            )

            self.assertEqual(
                feature.name,
                "Filesystem Safety",
            )

    def test_invalid_feature_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )

            for name in (
                "",
                "   ",
                ".",
                "..",
                "Feature/Subfeature",
                "Feature\\Subfeature",
            ):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        create_project_feature(
                            workspace,
                            name,
                        )

    def test_existing_feature_directory_is_not_merged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Existing Feature"
            )
            feature.mkdir()
            marker = feature / "notes.txt"
            marker.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                create_project_feature(
                    workspace,
                    "Existing Feature",
                )

            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "preserve",
            )
            self.assertFalse(
                (feature / "Documents").exists()
            )

    def test_existing_feature_file_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Occupied"
            )
            feature.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                create_project_feature(
                    workspace,
                    "Occupied",
                )

            self.assertEqual(
                feature.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_dangling_feature_symlink_prevents_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Linked Feature"
            )
            self._symlink(
                feature,
                root / "missing",
                target_is_directory=True,
            )

            with self.assertRaises(FileExistsError):
                create_project_feature(
                    workspace,
                    "Linked Feature",
                )

            self.assertTrue(
                feature.is_symlink()
            )

    def test_feature_initialization_preserves_existing_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Existing Feature"
            )
            feature.mkdir()
            marker = feature / "notes.txt"
            marker.write_text(
                "preserve",
                encoding="utf-8",
            )

            initialize_project_feature_structure(
                workspace,
                "Existing Feature",
            )

            self.assertTrue(
                (feature / "Documents").is_dir()
            )
            self.assertTrue(
                (feature / "Packages").is_dir()
            )
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_feature_initialization_preflights_children_before_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Existing Feature"
            )
            feature.mkdir()
            packages = feature / "Packages"
            packages.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_feature_structure(
                    workspace,
                    "Existing Feature",
                )

            self.assertFalse(
                (feature / "Documents").exists()
            )
            self.assertEqual(
                packages.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_feature_symlink_root_cannot_be_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            outside = root / "outside"
            outside.mkdir()
            feature = (
                workspace
                / "Features"
                / "Linked Feature"
            )
            self._symlink(
                feature,
                outside,
                target_is_directory=True,
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_feature_structure(
                    workspace,
                    "Linked Feature",
                )

            self.assertEqual(
                list(outside.iterdir()),
                [],
            )

    def test_feature_readiness_reports_missing_and_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Existing Feature"
            )
            feature.mkdir()

            self.assertFalse(
                is_project_feature_structure_initialized(
                    workspace,
                    "Existing Feature",
                )
            )

            initialize_project_feature_structure(
                workspace,
                "Existing Feature",
            )

            self.assertTrue(
                is_project_feature_structure_initialized(
                    workspace,
                    "Existing Feature",
                )
            )

    def test_feature_readiness_rejects_conflicting_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Existing Feature"
            )
            feature.mkdir()
            (feature / "Packages").write_text(
                "conflict",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                is_project_feature_structure_initialized(
                    workspace,
                    "Existing Feature",
                )

    def test_discovery_returns_real_immediate_feature_directories_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            features_root = workspace / "Features"
            alpha = features_root / "Alpha"
            beta = features_root / "beta"
            alpha.mkdir()
            beta.mkdir()
            (features_root / "notes.txt").write_text(
                "not a feature",
                encoding="utf-8",
            )
            outside = root / "outside"
            outside.mkdir()
            linked = features_root / "External"
            self._symlink(
                linked,
                outside,
                target_is_directory=True,
            )

            discovered = discover_project_features(
                workspace
            )

            self.assertEqual(
                discovered,
                (
                    alpha,
                    beta,
                ),
            )

    def test_discovery_includes_incomplete_real_feature(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Manual Feature"
            )
            feature.mkdir()
            (feature / "notes.txt").write_text(
                "existing",
                encoding="utf-8",
            )

            self.assertEqual(
                discover_project_features(
                    workspace
                ),
                (feature,),
            )

    def test_discovery_order_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            features_root = workspace / "Features"

            for name in (
                "gamma",
                "beta",
                "Alpha",
            ):
                (features_root / name).mkdir()

            self.assertEqual(
                [
                    path.name
                    for path in discover_project_features(
                        workspace
                    )
                ],
                [
                    "Alpha",
                    "beta",
                    "gamma",
                ],
            )

    def test_discovery_requires_features_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            with self.assertRaises(FileNotFoundError):
                discover_project_features(
                    workspace
                )

    def test_failed_feature_creation_removes_empty_created_feature(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            real_mkdir = Path.mkdir

            def controlled_mkdir(
                    path: Path,
                    *args,
                    **kwargs,
            ) -> None:
                if path.name == "Packages":
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
                    create_project_feature(
                        workspace,
                        "Broken Feature",
                    )

            self.assertFalse(
                (
                    workspace
                    / "Features"
                    / "Broken Feature"
                ).exists()
            )

    def test_create_package_builds_complete_standard_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Filesystem Drag Drop",
            )

            package = create_project_package(
                workspace,
                "Filesystem Drag Drop",
                "FI03",
            )

            self.assertEqual(
                package,
                (
                    workspace
                    / "Features"
                    / "Filesystem Drag Drop"
                    / "Packages"
                    / "FI03"
                ),
            )
            self.assertTrue(
                (package / "Documents").is_dir()
            )
            self.assertTrue(
                (package / "Contents").is_dir()
            )

    def test_create_package_normalizes_surrounding_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )

            package = create_project_package(
                workspace,
                "Feature",
                "  FI03  ",
            )

            self.assertEqual(
                package.name,
                "FI03",
            )

    def test_invalid_package_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )

            for package_id in (
                "",
                "   ",
                ".",
                "..",
                "FI/03",
                "FI\\03",
            ):
                with self.subTest(package_id=package_id):
                    with self.assertRaises(ValueError):
                        create_project_package(
                            workspace,
                            "Feature",
                            package_id,
                        )

    def test_existing_package_directory_is_not_merged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            package = (
                feature
                / "Packages"
                / "FI03"
            )
            package.mkdir()
            marker = package / "notes.txt"
            marker.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                create_project_package(
                    workspace,
                    "Feature",
                    "FI03",
                )

            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "preserve",
            )
            self.assertFalse(
                (package / "Documents").exists()
            )

    def test_existing_package_file_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            package = (
                feature
                / "Packages"
                / "FI03"
            )
            package.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                create_project_package(
                    workspace,
                    "Feature",
                    "FI03",
                )

            self.assertEqual(
                package.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_dangling_package_symlink_prevents_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            package = (
                feature
                / "Packages"
                / "FI03"
            )
            self._symlink(
                package,
                root / "missing",
                target_is_directory=True,
            )

            with self.assertRaises(FileExistsError):
                create_project_package(
                    workspace,
                    "Feature",
                    "FI03",
                )

            self.assertTrue(
                package.is_symlink()
            )

    def test_package_initialization_preserves_existing_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            package = (
                feature
                / "Packages"
                / "FI03"
            )
            package.mkdir()
            marker = package / "old-notes.txt"
            marker.write_text(
                "preserve",
                encoding="utf-8",
            )

            initialize_project_package_structure(
                workspace,
                "Feature",
                "FI03",
            )

            self.assertTrue(
                (package / "Documents").is_dir()
            )
            self.assertTrue(
                (package / "Contents").is_dir()
            )
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_package_initialization_preflights_children_before_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            package = (
                feature
                / "Packages"
                / "FI03"
            )
            package.mkdir()
            contents = package / "Contents"
            contents.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_package_structure(
                    workspace,
                    "Feature",
                    "FI03",
                )

            self.assertFalse(
                (package / "Documents").exists()
            )
            self.assertEqual(
                contents.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_package_symlink_root_cannot_be_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            outside = root / "outside"
            outside.mkdir()
            package = (
                feature
                / "Packages"
                / "FI03"
            )
            self._symlink(
                package,
                outside,
                target_is_directory=True,
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_package_structure(
                    workspace,
                    "Feature",
                    "FI03",
                )

            self.assertEqual(
                list(outside.iterdir()),
                [],
            )

    def test_package_discovery_returns_real_immediate_directories_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            packages_root = feature / "Packages"
            first = packages_root / "FI01"
            second = packages_root / "FI02"
            first.mkdir()
            second.mkdir()
            (packages_root / "notes.txt").write_text(
                "not a package",
                encoding="utf-8",
            )
            outside = root / "outside"
            outside.mkdir()
            linked = packages_root / "External"
            self._symlink(
                linked,
                outside,
                target_is_directory=True,
            )

            self.assertEqual(
                discover_feature_packages(
                    workspace,
                    "Feature",
                ),
                (
                    first,
                    second,
                ),
            )

    def test_package_discovery_includes_incomplete_real_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            package = (
                feature
                / "Packages"
                / "FI03"
            )
            package.mkdir()
            (package / "old-design.txt").write_text(
                "existing",
                encoding="utf-8",
            )

            self.assertEqual(
                discover_feature_packages(
                    workspace,
                    "Feature",
                ),
                (package,),
            )

    def test_package_discovery_order_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            packages_root = feature / "Packages"

            for name in (
                "pkg03",
                "PKG01",
                "pkg02",
            ):
                (packages_root / name).mkdir()

            self.assertEqual(
                [
                    path.name
                    for path in discover_feature_packages(
                        workspace,
                        "Feature",
                    )
                ],
                [
                    "PKG01",
                    "pkg02",
                    "pkg03",
                ],
            )

    def test_package_discovery_requires_packages_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            feature = (
                workspace
                / "Features"
                / "Feature"
            )
            feature.mkdir()

            with self.assertRaises(FileNotFoundError):
                discover_feature_packages(
                    workspace,
                    "Feature",
                )

    def test_failed_package_creation_removes_empty_created_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )
            real_mkdir = Path.mkdir

            def controlled_mkdir(
                    path: Path,
                    *args,
                    **kwargs,
            ) -> None:
                if path.name == "Contents":
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
                    create_project_package(
                        workspace,
                        "Feature",
                        "Broken Package",
                    )

            self.assertFalse(
                (
                    workspace
                    / "Features"
                    / "Feature"
                    / "Packages"
                    / "Broken Package"
                ).exists()
            )


    def test_package_structure_readiness_reports_missing_and_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            package = feature / "Packages" / "PKG01"
            package.mkdir()

            self.assertFalse(
                is_project_package_structure_initialized(
                    workspace,
                    "Feature",
                    "PKG01",
                )
            )

            initialize_project_package_structure(
                workspace,
                "Feature",
                "PKG01",
            )

            self.assertTrue(
                is_project_package_structure_initialized(
                    workspace,
                    "Feature",
                    "PKG01",
                )
            )

    def test_package_structure_readiness_rejects_conflicting_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            package = feature / "Packages" / "PKG01"
            package.mkdir()
            (package / "Contents").write_text(
                "conflict",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                is_project_package_structure_initialized(
                    workspace,
                    "Feature",
                    "PKG01",
                )

    def test_patch_paths_use_standard_patch_children(self) -> None:
        workspace = (
            Path(tempfile.gettempdir())
            / "workspace"
        )
        package = project_package_path(
            workspace,
            "Feature",
            "PKG01",
        )
        project_patch = project_patch_path(
            workspace,
            "General Fix",
        )
        package_patch = package_patch_path(
            package,
            "PKG01-1",
        )

        self.assertEqual(
            project_patches_path(workspace),
            workspace / PROJECT_PATCHES_DIRECTORY_NAME,
        )
        self.assertEqual(
            project_patch,
            workspace / "Patches" / "General Fix",
        )
        self.assertEqual(
            package_patches_path(package),
            package / PACKAGE_PATCHES_DIRECTORY_NAME,
        )
        self.assertEqual(
            package_patch,
            package / "Patches" / "PKG01-1",
        )
        self.assertEqual(
            patch_documents_path(project_patch),
            project_patch / PATCH_DOCUMENTS_DIRECTORY_NAME,
        )
        self.assertEqual(
            patch_contents_path(project_patch),
            project_patch / PATCH_CONTENTS_DIRECTORY_NAME,
        )

    def test_missing_patch_containers_do_not_change_existing_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )
            create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )

            self.assertTrue(
                is_project_workspace_structure_initialized(
                    workspace
                )
            )
            self.assertTrue(
                is_project_package_structure_initialized(
                    workspace,
                    "Feature",
                    "PKG01",
                )
            )
            self.assertFalse(
                project_patches_path(
                    workspace
                ).exists()
            )
            self.assertFalse(
                package_patches_path(
                    project_package_path(
                        workspace,
                        "Feature",
                        "PKG01",
                    )
                ).exists()
            )

    def test_missing_patch_containers_discover_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )
            create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )

            self.assertEqual(
                discover_project_patches(
                    workspace
                ),
                (),
            )
            self.assertEqual(
                discover_package_patches(
                    workspace,
                    "Feature",
                    "PKG01",
                ),
                (),
            )

    def test_create_project_patch_builds_complete_standard_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )

            patch_path = create_project_patch(
                workspace,
                "  Theme Fix  ",
            )

            self.assertEqual(
                patch_path,
                workspace / "Patches" / "Theme Fix",
            )
            self.assertTrue(
                (patch_path / "Documents").is_dir()
            )
            self.assertTrue(
                (patch_path / "Contents").is_dir()
            )
            self.assertTrue(
                is_project_patch_structure_initialized(
                    workspace,
                    "Theme Fix",
                )
            )

    def test_create_package_patch_builds_complete_standard_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )
            package = create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )

            patch_path = create_package_patch(
                workspace,
                "Feature",
                "PKG01",
                "PKG01-1",
            )

            self.assertEqual(
                patch_path,
                package / "Patches" / "PKG01-1",
            )
            self.assertTrue(
                (patch_path / "Documents").is_dir()
            )
            self.assertTrue(
                (patch_path / "Contents").is_dir()
            )
            self.assertTrue(
                (package / "Documents").is_dir()
            )
            self.assertTrue(
                (package / "Contents").is_dir()
            )
            self.assertTrue(
                is_package_patch_structure_initialized(
                    workspace,
                    "Feature",
                    "PKG01",
                    "PKG01-1",
                )
            )

    def test_patch_identifiers_reuse_structured_name_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )

            for patch_id in (
                "",
                "   ",
                ".",
                "..",
                "Patch/01",
                "Patch\\01",
            ):
                with self.subTest(patch_id=patch_id):
                    with self.assertRaises(ValueError):
                        create_project_patch(
                            workspace,
                            patch_id,
                        )

            with self.assertRaises(ValueError):
                create_project_patch(
                    workspace,
                    123,  # type: ignore[arg-type]
                )

    def test_existing_project_patch_is_not_merged_or_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            patches_root = workspace / "Patches"
            patches_root.mkdir()
            patch_path = patches_root / "Existing"
            patch_path.mkdir()
            marker = patch_path / "marker.txt"
            marker.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                create_project_patch(
                    workspace,
                    "Existing",
                )

            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "preserve",
            )
            self.assertFalse(
                (patch_path / "Documents").exists()
            )

    def test_project_patch_container_conflicts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            patches_root = workspace / "Patches"
            patches_root.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                discover_project_patches(
                    workspace
                )

            with self.assertRaises(NotADirectoryError):
                create_project_patch(
                    workspace,
                    "Fix",
                )

            self.assertEqual(
                patches_root.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_package_patch_container_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )
            package = create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )
            outside = root / "outside"
            outside.mkdir()
            patches_root = package / "Patches"
            self._symlink(
                patches_root,
                outside,
                target_is_directory=True,
            )

            with self.assertRaises(NotADirectoryError):
                discover_package_patches(
                    workspace,
                    "Feature",
                    "PKG01",
                )

            with self.assertRaises(NotADirectoryError):
                create_package_patch(
                    workspace,
                    "Feature",
                    "PKG01",
                    "PKG01-1",
                )

            self.assertEqual(
                list(outside.iterdir()),
                [],
            )

    def test_patch_discovery_returns_real_directories_in_deterministic_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            patches_root = workspace / "Patches"
            patches_root.mkdir()
            alpha = patches_root / "Alpha"
            beta = patches_root / "beta"
            gamma = patches_root / "gamma"
            for path in (
                gamma,
                beta,
                alpha,
            ):
                path.mkdir()

            (patches_root / "notes.txt").write_text(
                "not a patch",
                encoding="utf-8",
            )
            outside = root / "outside"
            outside.mkdir()
            linked = patches_root / "External"
            self._symlink(
                linked,
                outside,
                target_is_directory=True,
            )

            self.assertEqual(
                discover_project_patches(
                    workspace
                ),
                (
                    alpha,
                    beta,
                    gamma,
                ),
            )

    def test_incomplete_patch_can_be_initialized_without_losing_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            patches_root = workspace / "Patches"
            patches_root.mkdir()
            patch_path = patches_root / "Fix"
            patch_path.mkdir()
            documents = patch_path / "Documents"
            documents.mkdir()
            marker = documents / "notes.txt"
            marker.write_text(
                "preserve",
                encoding="utf-8",
            )

            self.assertFalse(
                is_project_patch_structure_initialized(
                    workspace,
                    "Fix",
                )
            )

            initialize_project_patch_structure(
                workspace,
                "Fix",
            )

            self.assertTrue(
                is_project_patch_structure_initialized(
                    workspace,
                    "Fix",
                )
            )
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_patch_initialization_preflights_children_before_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            patches_root = workspace / "Patches"
            patches_root.mkdir()
            patch_path = patches_root / "Fix"
            patch_path.mkdir()
            contents = patch_path / "Contents"
            contents.write_text(
                "preserve",
                encoding="utf-8",
            )

            with self.assertRaises(NotADirectoryError):
                initialize_project_patch_structure(
                    workspace,
                    "Fix",
                )

            self.assertFalse(
                (patch_path / "Documents").exists()
            )
            self.assertEqual(
                contents.read_text(encoding="utf-8"),
                "preserve",
            )

    def test_same_patch_id_can_exist_under_different_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )
            first = create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )
            second = create_project_package(
                workspace,
                "Feature",
                "PKG02",
            )

            first_patch = create_package_patch(
                workspace,
                "Feature",
                "PKG01",
                "FollowUp",
            )
            second_patch = create_package_patch(
                workspace,
                "Feature",
                "PKG02",
                "FollowUp",
            )

            self.assertEqual(
                first_patch,
                first / "Patches" / "FollowUp",
            )
            self.assertEqual(
                second_patch,
                second / "Patches" / "FollowUp",
            )

    def test_failed_first_patch_creation_removes_new_optional_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            real_mkdir = Path.mkdir

            def controlled_mkdir(
                    path: Path,
                    *args,
                    **kwargs,
            ) -> None:
                if path.name == "Contents":
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
                    create_project_patch(
                        workspace,
                        "Broken",
                    )

            self.assertFalse(
                (workspace / "Patches").exists()
            )

    def test_failed_patch_creation_preserves_existing_optional_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(
                root
            )
            patches_root = workspace / "Patches"
            patches_root.mkdir()
            marker = patches_root / "marker.txt"
            marker.write_text(
                "preserve",
                encoding="utf-8",
            )
            real_mkdir = Path.mkdir

            def controlled_mkdir(
                    path: Path,
                    *args,
                    **kwargs,
            ) -> None:
                if path.name == "Contents":
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
                    create_project_patch(
                        workspace,
                        "Broken",
                    )

            self.assertTrue(
                patches_root.is_dir()
            )
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "preserve",
            )
            self.assertFalse(
                (patches_root / "Broken").exists()
            )


if __name__ == "__main__":
    unittest.main()
