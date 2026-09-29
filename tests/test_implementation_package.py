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
    inspect_implementation_package_archive,
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


if __name__ == "__main__":
    unittest.main()
