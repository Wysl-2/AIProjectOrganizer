from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile


_PACKAGE_ID_PATTERN = re.compile(
    r"(?=.*\d)[A-Z][A-Z0-9-]*"
)

_README_SECTION_FIELDS = {
    "# INSTALLATION": "installation",
    "# SUMMARY": "summary",
    "# IMPLEMENTATION DETAILS": "implementation_details",
    "# FILES CHANGED": "files_changed",
    "# MANUAL FOLLOW-UP": "manual_follow_up",
    "# TESTING / VALIDATION": "testing_validation",
    "# GIT COMMIT MESSAGE": "git_commit_message",
}


class ImplementationPackageError(ValueError):
    pass


@dataclass(frozen=True)
class ImplementationPackageArchive:
    source_path: Path
    package_root_name: str
    inferred_package_id: str | None


@dataclass(frozen=True)
class ExtractedImplementationPackage:
    root_path: Path
    install_script_path: Path
    readme_path: Path
    project_payload_path: Path


@dataclass(frozen=True)
class ImplementationPackageReadme:
    installation: str
    summary: str
    implementation_details: str
    files_changed: str
    manual_follow_up: str
    testing_validation: str
    git_commit_message: str


def inspect_implementation_package_archive(
    archive_path: str | Path,
) -> ImplementationPackageArchive:
    source = _validated_archive_source(
        archive_path
    )

    try:
        with zipfile.ZipFile(
            source,
            "r",
        ) as archive:
            return _inspect_open_archive(
                source,
                archive,
            )
    except zipfile.BadZipFile as error:
        raise ImplementationPackageError(
            "The selected file is not a valid ZIP archive."
        ) from error


def copy_implementation_package_archive(
    archive_path: str | Path,
    contents_directory: str | Path,
) -> Path:
    inspection = inspect_implementation_package_archive(
        archive_path
    )
    source = inspection.source_path
    contents = _validated_contents_directory(
        contents_directory
    )
    destination = (
        contents
        / source.name
    )

    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            "An implementation package with this file name "
            f"already exists: {destination}"
        )

    created_destination = False

    try:
        with source.open(
            "rb"
        ) as source_stream:
            with destination.open(
                "xb"
            ) as destination_stream:
                created_destination = True
                shutil.copyfileobj(
                    source_stream,
                    destination_stream,
                )
    except OSError:
        if created_destination:
            try:
                destination.unlink()
            except OSError:
                pass
        raise

    return destination


def extract_implementation_package_archive(
    archive_path: str | Path,
    contents_directory: str | Path,
) -> ExtractedImplementationPackage:
    source = _validated_archive_source(
        archive_path
    )
    contents = _validated_contents_directory(
        contents_directory
    )

    try:
        with zipfile.ZipFile(
            source,
            "r",
        ) as archive:
            inspection = _inspect_open_archive(
                source,
                archive,
            )
            destination = (
                contents
                / inspection.package_root_name
            )

            if destination.exists() or destination.is_symlink():
                raise FileExistsError(
                    "An extracted implementation package already "
                    f"exists at: {destination}"
                )

            with tempfile.TemporaryDirectory(
                prefix=".package-extract-",
                dir=contents,
            ) as temporary_directory:
                temporary_root = Path(
                    temporary_directory
                )

                for info in archive.infolist():
                    parts = _validated_member_parts(
                        info.filename
                    )
                    target = temporary_root.joinpath(
                        *parts
                    )

                    if info.is_dir():
                        target.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                        continue

                    target.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    with archive.open(
                        info,
                        "r",
                    ) as source_stream:
                        with target.open(
                            "xb"
                        ) as destination_stream:
                            shutil.copyfileobj(
                                source_stream,
                                destination_stream,
                            )

                temporary_package_root = (
                    temporary_root
                    / inspection.package_root_name
                )
                inspect_extracted_implementation_package(
                    temporary_package_root
                )

                if destination.exists() or destination.is_symlink():
                    raise FileExistsError(
                        "An extracted implementation package already "
                        f"exists at: {destination}"
                    )

                temporary_package_root.rename(
                    destination
                )
    except zipfile.BadZipFile as error:
        raise ImplementationPackageError(
            "The selected file is not a valid ZIP archive."
        ) from error

    return inspect_extracted_implementation_package(
        destination
    )


def inspect_extracted_implementation_package(
    package_root: str | Path,
) -> ExtractedImplementationPackage:
    root = Path(
        package_root
    ).expanduser()

    if root.is_symlink():
        raise ImplementationPackageError(
            "Extracted implementation package roots must not "
            "be symbolic links."
        )

    if not root.exists():
        raise FileNotFoundError(
            f"Extracted implementation package does not exist: {root}"
        )

    if not root.is_dir():
        raise ImplementationPackageError(
            "The extracted implementation package root is not "
            "a directory."
        )

    entries = {
        entry.name: entry
        for entry in root.iterdir()
    }
    expected_names = {
        "Install.py",
        "README.txt",
        "Project",
    }

    missing_names = (
        expected_names
        - entries.keys()
    )

    if missing_names:
        missing_text = ", ".join(
            sorted(
                missing_names
            )
        )
        raise ImplementationPackageError(
            "The extracted implementation package is missing "
            f"required content: {missing_text}"
        )

    unexpected_names = (
        entries.keys()
        - expected_names
    )

    if unexpected_names:
        unexpected_text = ", ".join(
            sorted(
                unexpected_names
            )
        )
        raise ImplementationPackageError(
            "The extracted implementation package contains "
            f"unexpected root content: {unexpected_text}"
        )

    install_script = entries[
        "Install.py"
    ]
    readme = entries[
        "README.txt"
    ]
    project_payload = entries[
        "Project"
    ]

    _require_real_file(
        install_script,
        "Install.py",
    )
    _require_real_file(
        readme,
        "README.txt",
    )
    _require_real_directory(
        project_payload,
        "Project",
    )

    return ExtractedImplementationPackage(
        root_path=root,
        install_script_path=install_script,
        readme_path=readme,
        project_payload_path=project_payload,
    )


def discover_implementation_package_archives(
    contents_directory: str | Path,
) -> tuple[ImplementationPackageArchive, ...]:
    contents = _validated_contents_directory(
        contents_directory
    )
    entries = sorted(
        contents.iterdir(),
        key=lambda path: (
            path.name.casefold(),
            path.name,
        ),
    )
    discovered: list[
        ImplementationPackageArchive
    ] = []

    for entry in entries:
        if (
                entry.is_symlink()
                or not entry.is_file()
                or entry.suffix.casefold() != ".zip"
        ):
            continue

        try:
            discovered.append(
                inspect_implementation_package_archive(
                    entry
                )
            )
        except ImplementationPackageError:
            continue

    return tuple(
        discovered
    )


def discover_extracted_implementation_packages(
    contents_directory: str | Path,
) -> tuple[ExtractedImplementationPackage, ...]:
    contents = _validated_contents_directory(
        contents_directory
    )
    entries = sorted(
        contents.iterdir(),
        key=lambda path: (
            path.name.casefold(),
            path.name,
        ),
    )
    discovered: list[
        ExtractedImplementationPackage
    ] = []

    for entry in entries:
        if (
                entry.is_symlink()
                or not entry.is_dir()
        ):
            continue

        try:
            discovered.append(
                inspect_extracted_implementation_package(
                    entry
                )
            )
        except ImplementationPackageError:
            continue

    return tuple(
        discovered
    )


def parse_implementation_package_readme(
    readme_path: str | Path,
) -> ImplementationPackageReadme:
    path = Path(
        readme_path
    ).expanduser()

    _require_real_file(
        path,
        "README.txt",
    )

    try:
        text = path.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError as error:
        raise ImplementationPackageError(
            "README.txt is not valid UTF-8 text."
        ) from error

    section_lines = {
        field_name: []
        for field_name
        in _README_SECTION_FIELDS.values()
    }
    seen_headings: set[str] = set()
    current_field: str | None = None

    for line in text.splitlines():
        stripped_line = line.strip()

        if stripped_line in _README_SECTION_FIELDS:
            if stripped_line in seen_headings:
                raise ImplementationPackageError(
                    "README.txt contains a duplicate standardized "
                    f"section: {stripped_line}"
                )

            seen_headings.add(
                stripped_line
            )
            current_field = (
                _README_SECTION_FIELDS[
                    stripped_line
                ]
            )
            continue

        if current_field is not None:
            section_lines[
                current_field
            ].append(
                line
            )

    values = {
        field_name: "\n".join(
            lines
        ).strip()
        for field_name, lines
        in section_lines.items()
    }

    return ImplementationPackageReadme(
        installation=values[
            "installation"
        ],
        summary=values[
            "summary"
        ],
        implementation_details=values[
            "implementation_details"
        ],
        files_changed=values[
            "files_changed"
        ],
        manual_follow_up=values[
            "manual_follow_up"
        ],
        testing_validation=values[
            "testing_validation"
        ],
        git_commit_message=values[
            "git_commit_message"
        ],
    )


def _inspect_open_archive(
    source: Path,
    archive: zipfile.ZipFile,
) -> ImplementationPackageArchive:
    infos = archive.infolist()

    if not infos:
        raise ImplementationPackageError(
            "The implementation package archive is empty."
        )

    members: list[
        tuple[zipfile.ZipInfo, tuple[str, ...]]
    ] = []
    seen_paths: set[str] = set()

    for info in infos:
        parts = _validated_member_parts(
            info.filename
        )
        normalized_path = "/".join(
            parts
        )

        if normalized_path in seen_paths:
            raise ImplementationPackageError(
                "The implementation package contains "
                f"a duplicate archive member: {normalized_path}"
            )

        seen_paths.add(
            normalized_path
        )
        _validate_member_type(
            info
        )
        members.append(
            (
                info,
                parts,
            )
        )

    roots = {
        parts[0]
        for _info, parts in members
    }

    if len(roots) != 1:
        raise ImplementationPackageError(
            "The implementation package must contain exactly "
            "one top-level package directory."
        )

    package_root_name = next(
        iter(roots)
    )

    install_info: zipfile.ZipInfo | None = None
    readme_info: zipfile.ZipInfo | None = None
    project_present = False

    for info, parts in members:
        if len(parts) == 1:
            if not info.is_dir():
                raise ImplementationPackageError(
                    "The top-level package entry must be a directory."
                )
            continue

        root_child = parts[1]

        if root_child not in {
            "Install.py",
            "README.txt",
            "Project",
        }:
            raise ImplementationPackageError(
                "Unexpected item at implementation package root: "
                f"{root_child}"
            )

        if len(parts) >= 3:
            if root_child != "Project":
                raise ImplementationPackageError(
                    "Only the Project directory may contain "
                    "nested package-root content."
                )

            project_present = True
            continue

        if root_child == "Install.py":
            if info.is_dir():
                raise ImplementationPackageError(
                    "Install.py must be a file."
                )
            install_info = info

        elif root_child == "README.txt":
            if info.is_dir():
                raise ImplementationPackageError(
                    "README.txt must be a file."
                )
            readme_info = info

        elif root_child == "Project":
            if not info.is_dir():
                raise ImplementationPackageError(
                    "Project must be a directory."
                )
            project_present = True

    if install_info is None:
        raise ImplementationPackageError(
            "The implementation package is missing Install.py."
        )

    if readme_info is None:
        raise ImplementationPackageError(
            "The implementation package is missing README.txt."
        )

    if not project_present:
        raise ImplementationPackageError(
            "The implementation package is missing Project/."
        )

    return ImplementationPackageArchive(
        source_path=source,
        package_root_name=package_root_name,
        inferred_package_id=_infer_package_id(
            package_root_name,
            source.stem,
        ),
    )


def _validated_archive_source(
    archive_path: str | Path,
) -> Path:
    source = Path(
        archive_path
    ).expanduser()

    if source.is_symlink():
        raise ImplementationPackageError(
            "Implementation package ZIP files must not "
            "be symbolic links."
        )

    if not source.exists():
        raise FileNotFoundError(
            f"Implementation package does not exist: {source}"
        )

    if not source.is_file():
        raise ImplementationPackageError(
            "The selected implementation package is not a file."
        )

    if source.suffix.casefold() != ".zip":
        raise ImplementationPackageError(
            "Implementation packages must be ZIP files."
        )

    return source


def _validated_contents_directory(
    contents_directory: str | Path,
) -> Path:
    contents = Path(
        contents_directory
    ).expanduser()

    if contents.is_symlink():
        raise NotADirectoryError(
            "Package Contents directory must not be "
            f"a symbolic link: {contents}"
        )

    if not contents.exists():
        raise FileNotFoundError(
            "Package Contents directory does not exist: "
            f"{contents}"
        )

    if not contents.is_dir():
        raise NotADirectoryError(
            "Package Contents path is not a directory: "
            f"{contents}"
        )

    return contents


def _require_real_file(
    path: Path,
    description: str,
) -> None:
    if path.is_symlink():
        raise ImplementationPackageError(
            f"{description} must not be a symbolic link."
        )

    if not path.exists():
        raise FileNotFoundError(
            f"{description} does not exist: {path}"
        )

    if not path.is_file():
        raise ImplementationPackageError(
            f"{description} must be a regular file."
        )


def _require_real_directory(
    path: Path,
    description: str,
) -> None:
    if path.is_symlink():
        raise ImplementationPackageError(
            f"{description} must not be a symbolic link."
        )

    if not path.exists():
        raise FileNotFoundError(
            f"{description} does not exist: {path}"
        )

    if not path.is_dir():
        raise ImplementationPackageError(
            f"{description} must be a directory."
        )


def _validated_member_parts(
    member_name: str,
) -> tuple[str, ...]:
    if not member_name:
        raise ImplementationPackageError(
            "The implementation package contains "
            "an unnamed archive member."
        )

    if "\x00" in member_name:
        raise ImplementationPackageError(
            "The implementation package contains "
            "an invalid archive member name."
        )

    if "\\" in member_name:
        raise ImplementationPackageError(
            "Implementation package member paths must "
            "use forward slashes."
        )

    if member_name.startswith("/"):
        raise ImplementationPackageError(
            "The implementation package contains "
            "an absolute archive path."
        )

    if re.match(
            r"^[A-Za-z]:",
            member_name,
    ):
        raise ImplementationPackageError(
            "The implementation package contains "
            "a drive-qualified archive path."
        )

    trimmed_name = (
        member_name[:-1]
        if member_name.endswith("/")
        else member_name
    )

    if not trimmed_name:
        raise ImplementationPackageError(
            "The implementation package contains "
            "an invalid archive root entry."
        )

    raw_parts = trimmed_name.split(
        "/"
    )

    if any(
        part in {
            "",
            ".",
            "..",
        }
        for part in raw_parts
    ):
        raise ImplementationPackageError(
            "The implementation package contains "
            "an unsafe archive member path."
        )

    path = PurePosixPath(
        trimmed_name
    )

    if path.is_absolute():
        raise ImplementationPackageError(
            "The implementation package contains "
            "an absolute archive path."
        )

    return tuple(
        path.parts
    )


def _validate_member_type(
    info: zipfile.ZipInfo,
) -> None:
    unix_mode = (
        info.external_attr
        >> 16
    ) & 0xFFFF

    if stat.S_ISLNK(
        unix_mode
    ):
        raise ImplementationPackageError(
            "Implementation package archives must not "
            "contain symbolic links."
        )

    file_type = stat.S_IFMT(
        unix_mode
    )

    if file_type not in {
        0,
        stat.S_IFREG,
        stat.S_IFDIR,
    }:
        raise ImplementationPackageError(
            "Implementation package archives contain "
            "an unsupported special filesystem entry."
        )


def _infer_package_id(
    package_root_name: str,
    archive_stem: str,
) -> str | None:
    root_candidates = _identifier_candidates(
        package_root_name
    )

    if len(root_candidates) == 1:
        return next(
            iter(root_candidates)
        )

    if len(root_candidates) > 1:
        return None

    filename_candidates = _identifier_candidates(
        archive_stem
    )

    if len(filename_candidates) == 1:
        return next(
            iter(filename_candidates)
        )

    return None


def _identifier_candidates(
    value: str,
) -> set[str]:
    candidates: set[str] = set()

    for token in re.split(
        r"[_\s]+",
        value,
    ):
        if _PACKAGE_ID_PATTERN.fullmatch(
            token
        ):
            candidates.add(
                token
            )

    return candidates
