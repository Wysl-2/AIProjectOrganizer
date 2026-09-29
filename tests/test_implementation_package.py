import stat
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch
import zipfile

from ai_project_organizer.implementation_package import (
    ImplementationPackageError,
    copy_implementation_package_archive,
    discover_extracted_implementation_packages,
    discover_implementation_package_archives,
    extract_implementation_package_archive,
    inspect_extracted_implementation_package,
    inspect_implementation_package_archive,
    parse_implementation_package_readme,
)


class ImplementationPackageTests(unittest.TestCase):
    def _write_valid_archive(
            self,
            path: Path,
            root_name: str = "Example_FI01_Package",
            *,
            empty_project: bool = False,
    ) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                f"{root_name}/Install.py",
                "install",
            )
            archive.writestr(
                f"{root_name}/README.txt",
                "readme",
            )
            if empty_project:
                archive.writestr(
                    f"{root_name}/Project/",
                    "",
                )
            else:
                archive.writestr(
                    f"{root_name}/Project/file.txt",
                    "file",
                )

    def test_valid_archive_is_inspected_without_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "package.zip"
            self._write_valid_archive(archive_path)

            inspection = inspect_implementation_package_archive(
                archive_path
            )

            self.assertEqual(
                inspection.package_root_name,
                "Example_FI01_Package",
            )
            self.assertEqual(
                inspection.inferred_package_id,
                "FI01",
            )
            self.assertEqual(
                set(root.iterdir()),
                {archive_path},
            )

    def test_empty_project_directory_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = Path(temporary_directory) / "package.zip"
            self._write_valid_archive(
                archive_path,
                empty_project=True,
            )
            inspect_implementation_package_archive(
                archive_path
            )

    def test_required_contract_entries_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            cases = {
                "missing-install.zip": [
                    ("Package/README.txt", "readme"),
                    ("Package/Project/file.txt", "file"),
                ],
                "missing-readme.zip": [
                    ("Package/Install.py", "install"),
                    ("Package/Project/file.txt", "file"),
                ],
                "missing-project.zip": [
                    ("Package/Install.py", "install"),
                    ("Package/README.txt", "readme"),
                ],
            }

            for filename, entries in cases.items():
                with self.subTest(filename=filename):
                    archive_path = root / filename
                    with zipfile.ZipFile(archive_path, "w") as archive:
                        for name, content in entries:
                            archive.writestr(name, content)

                    with self.assertRaises(ImplementationPackageError):
                        inspect_implementation_package_archive(
                            archive_path
                        )

    def test_multiple_roots_and_unexpected_root_content_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            multiple = root / "multiple.zip"
            with zipfile.ZipFile(multiple, "w") as archive:
                archive.writestr("A/Install.py", "install")
                archive.writestr("B/README.txt", "readme")
                archive.writestr("B/Project/file.txt", "file")

            with self.assertRaises(ImplementationPackageError):
                inspect_implementation_package_archive(
                    multiple
                )

            unexpected = root / "unexpected.zip"
            self._write_valid_archive(unexpected)
            with zipfile.ZipFile(unexpected, "a") as archive:
                archive.writestr(
                    "Example_FI01_Package/extra.txt",
                    "extra",
                )

            with self.assertRaises(ImplementationPackageError):
                inspect_implementation_package_archive(
                    unexpected
                )

    def test_unsafe_member_paths_are_rejected(self) -> None:
        unsafe_names = (
            "/Package/Install.py",
            "Package/Project/../../outside.txt",
            "Package\\Install.py",
            "C:/Package/Install.py",
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            for index, member_name in enumerate(unsafe_names):
                with self.subTest(member_name=member_name):
                    archive_path = root / f"unsafe-{index}.zip"
                    with zipfile.ZipFile(archive_path, "w") as archive:
                        archive.writestr(member_name, "unsafe")

                    with self.assertRaises(ImplementationPackageError):
                        inspect_implementation_package_archive(
                            archive_path
                        )

    def test_duplicate_and_symlink_members_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            duplicate = root / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with zipfile.ZipFile(duplicate, "w") as archive:
                    archive.writestr("Package/Install.py", "one")
                    archive.writestr("Package/Install.py", "two")

            with self.assertRaises(ImplementationPackageError):
                inspect_implementation_package_archive(
                    duplicate
                )

            symlink = root / "symlink.zip"
            link_info = zipfile.ZipInfo("Package/Project/link")
            link_info.create_system = 3
            link_info.external_attr = (
                (stat.S_IFLNK | 0o777)
                << 16
            )

            with zipfile.ZipFile(symlink, "w") as archive:
                archive.writestr("Package/Install.py", "install")
                archive.writestr("Package/README.txt", "readme")
                archive.writestr(link_info, "/outside")

            with self.assertRaises(ImplementationPackageError):
                inspect_implementation_package_archive(
                    symlink
                )

    def test_package_id_inference_is_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            ambiguous = root / "archive.zip"
            self._write_valid_archive(
                ambiguous,
                "Example_FI01_UI02_Package",
            )
            self.assertIsNone(
                inspect_implementation_package_archive(
                    ambiguous
                ).inferred_package_id
            )

            fallback = root / "Example_FI03_Archive.zip"
            self._write_valid_archive(
                fallback,
                "ExamplePackage",
            )
            self.assertEqual(
                inspect_implementation_package_archive(
                    fallback
                ).inferred_package_id,
                "FI03",
            )

            versioned = root / "versioned.zip"
            self._write_valid_archive(
                versioned,
                "Example_SPM04_Package_v2",
            )
            self.assertEqual(
                inspect_implementation_package_archive(
                    versioned
                ).inferred_package_id,
                "SPM04",
            )

    def test_copy_preserves_source_and_rejects_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "package.zip"
            contents = root / "Contents"
            contents.mkdir()
            self._write_valid_archive(source)
            original = source.read_bytes()

            destination = copy_implementation_package_archive(
                source,
                contents,
            )

            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(destination.read_bytes(), original)

            with self.assertRaises(FileExistsError):
                copy_implementation_package_archive(
                    source,
                    contents,
                )

            self.assertEqual(destination.read_bytes(), original)

    def test_copy_failure_removes_incomplete_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "package.zip"
            contents = root / "Contents"
            contents.mkdir()
            self._write_valid_archive(source)

            with patch(
                "ai_project_organizer.implementation_package.shutil.copyfileobj",
                side_effect=PermissionError("permission denied"),
            ):
                with self.assertRaises(PermissionError):
                    copy_implementation_package_archive(
                        source,
                        contents,
                    )

            self.assertTrue(source.is_file())
            self.assertFalse(
                (contents / source.name).exists()
            )


    def test_extracted_package_structure_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "Package"
            root.mkdir()
            (root / "Install.py").write_text(
                "install",
                encoding="utf-8",
            )
            (root / "README.txt").write_text(
                "readme",
                encoding="utf-8",
            )
            (root / "Project").mkdir()

            inspection = inspect_extracted_implementation_package(
                root
            )

            self.assertEqual(
                inspection.root_path,
                root,
            )
            self.assertEqual(
                inspection.install_script_path,
                root / "Install.py",
            )
            self.assertEqual(
                inspection.readme_path,
                root / "README.txt",
            )
            self.assertEqual(
                inspection.project_payload_path,
                root / "Project",
            )

    def test_extracted_package_rejects_missing_or_unexpected_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)

            missing = base / "Missing"
            missing.mkdir()
            (missing / "Install.py").write_text(
                "install",
                encoding="utf-8",
            )
            (missing / "README.txt").write_text(
                "readme",
                encoding="utf-8",
            )

            with self.assertRaises(ImplementationPackageError):
                inspect_extracted_implementation_package(
                    missing
                )

            unexpected = base / "Unexpected"
            unexpected.mkdir()
            (unexpected / "Install.py").write_text(
                "install",
                encoding="utf-8",
            )
            (unexpected / "README.txt").write_text(
                "readme",
                encoding="utf-8",
            )
            (unexpected / "Project").mkdir()
            (unexpected / "extra.txt").write_text(
                "extra",
                encoding="utf-8",
            )

            with self.assertRaises(ImplementationPackageError):
                inspect_extracted_implementation_package(
                    unexpected
                )

    def test_extracted_package_rejects_wrong_types(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)

            wrong_install = base / "WrongInstall"
            wrong_install.mkdir()
            (wrong_install / "Install.py").mkdir()
            (wrong_install / "README.txt").write_text(
                "readme",
                encoding="utf-8",
            )
            (wrong_install / "Project").mkdir()

            with self.assertRaises(ImplementationPackageError):
                inspect_extracted_implementation_package(
                    wrong_install
                )

            wrong_project = base / "WrongProject"
            wrong_project.mkdir()
            (wrong_project / "Install.py").write_text(
                "install",
                encoding="utf-8",
            )
            (wrong_project / "README.txt").write_text(
                "readme",
                encoding="utf-8",
            )
            (wrong_project / "Project").write_text(
                "not a directory",
                encoding="utf-8",
            )

            with self.assertRaises(ImplementationPackageError):
                inspect_extracted_implementation_package(
                    wrong_project
                )

    def test_extraction_publishes_valid_package_and_preserves_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "package.zip"
            contents = root / "Contents"
            contents.mkdir()
            self._write_valid_archive(
                archive_path,
                root_name="Example_FI01_Package",
            )
            original_bytes = archive_path.read_bytes()

            extracted = extract_implementation_package_archive(
                archive_path,
                contents,
            )

            self.assertEqual(
                extracted.root_path,
                contents / "Example_FI01_Package",
            )
            self.assertTrue(
                extracted.install_script_path.is_file()
            )
            self.assertTrue(
                extracted.readme_path.is_file()
            )
            self.assertTrue(
                extracted.project_payload_path.is_dir()
            )
            self.assertEqual(
                archive_path.read_bytes(),
                original_bytes,
            )
            self.assertFalse(
                any(
                    path.name.startswith(
                        ".package-extract-"
                    )
                    for path in contents.iterdir()
                )
            )

    def test_extraction_refuses_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "package.zip"
            contents = root / "Contents"
            contents.mkdir()
            self._write_valid_archive(
                archive_path,
                root_name="Example_FI01_Package",
            )
            destination = (
                contents
                / "Example_FI01_Package"
            )
            destination.mkdir()
            marker = destination / "existing.txt"
            marker.write_text(
                "existing",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                extract_implementation_package_archive(
                    archive_path,
                    contents,
                )

            self.assertEqual(
                marker.read_text(
                    encoding="utf-8"
                ),
                "existing",
            )
            self.assertTrue(
                archive_path.is_file()
            )

    def test_extraction_failure_cleans_temporary_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "package.zip"
            contents = root / "Contents"
            contents.mkdir()
            self._write_valid_archive(
                archive_path,
                root_name="Example_FI01_Package",
            )

            with patch(
                "ai_project_organizer.implementation_package.shutil.copyfileobj",
                side_effect=PermissionError(
                    "permission denied"
                ),
            ):
                with self.assertRaises(PermissionError):
                    extract_implementation_package_archive(
                        archive_path,
                        contents,
                    )

            self.assertFalse(
                (
                    contents
                    / "Example_FI01_Package"
                ).exists()
            )
            self.assertFalse(
                any(
                    path.name.startswith(
                        ".package-extract-"
                    )
                    for path in contents.iterdir()
                )
            )
            self.assertTrue(
                archive_path.is_file()
            )

    def test_archive_and_extracted_discovery_ignore_unrelated_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            contents = Path(temporary_directory)

            valid_archive = contents / "valid.zip"
            self._write_valid_archive(
                valid_archive,
                root_name="Archive_FI01",
            )
            (contents / "random.zip").write_bytes(
                b"not a zip"
            )
            (contents / "notes.txt").write_text(
                "notes",
                encoding="utf-8",
            )

            valid_root = contents / "ValidRoot"
            valid_root.mkdir()
            (valid_root / "Install.py").write_text(
                "install",
                encoding="utf-8",
            )
            (valid_root / "README.txt").write_text(
                "readme",
                encoding="utf-8",
            )
            (valid_root / "Project").mkdir()
            (contents / "RandomDirectory").mkdir()

            archives = discover_implementation_package_archives(
                contents
            )
            extracted = discover_extracted_implementation_packages(
                contents
            )

            self.assertEqual(
                tuple(
                    item.source_path.name
                    for item in archives
                ),
                ("valid.zip",),
            )
            self.assertEqual(
                tuple(
                    item.root_path.name
                    for item in extracted
                ),
                ("ValidRoot",),
            )

    def test_readme_parser_maps_standard_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            readme = Path(temporary_directory) / "README.txt"
            readme.write_text(
                (
                    "# INSTALLATION\n"
                    "\n"
                    "Install text\n"
                    "\n"
                    "# SUMMARY\n"
                    "\n"
                    "Summary line 1\n"
                    "Summary line 2\n"
                    "\n"
                    "# IMPLEMENTATION DETAILS\n"
                    "\n"
                    "Details\n"
                    "\n"
                    "# FILES CHANGED\n"
                    "\n"
                    "- file.py\n"
                    "\n"
                    "# MANUAL FOLLOW-UP\n"
                    "\n"
                    "None.\n"
                    "\n"
                    "# TESTING / VALIDATION\n"
                    "\n"
                    "python -m unittest discover -s tests\n"
                    "\n"
                    "# GIT COMMIT MESSAGE\n"
                    "\n"
                    "Add package inspection\n"
                    "\n"
                    "- inspect package\n"
                ),
                encoding="utf-8",
            )

            parsed = parse_implementation_package_readme(
                readme
            )

            self.assertEqual(
                parsed.installation,
                "Install text",
            )
            self.assertEqual(
                parsed.summary,
                "Summary line 1\nSummary line 2",
            )
            self.assertEqual(
                parsed.files_changed,
                "- file.py",
            )
            self.assertEqual(
                parsed.git_commit_message,
                "Add package inspection\n\n- inspect package",
            )

    def test_readme_parser_allows_missing_sections_and_rejects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            sparse = root / "sparse.txt"
            sparse.write_text(
                "# SUMMARY\n\nSummary only\n",
                encoding="utf-8",
            )

            parsed = parse_implementation_package_readme(
                sparse
            )

            self.assertEqual(
                parsed.summary,
                "Summary only",
            )
            self.assertEqual(
                parsed.git_commit_message,
                "",
            )

            duplicate = root / "duplicate.txt"
            duplicate.write_text(
                (
                    "# SUMMARY\n"
                    "One\n"
                    "# SUMMARY\n"
                    "Two\n"
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ImplementationPackageError):
                parse_implementation_package_readme(
                    duplicate
                )


if __name__ == "__main__":
    unittest.main()
