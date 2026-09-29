from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile


_PACKAGE_ID_PATTERN = re.compile(
    r"(?=.*\d)[A-Z][A-Z0-9-]*"
)


class ImplementationPackageError(ValueError):
    pass


@dataclass(frozen=True)
class ImplementationPackageArchive:
    source_path: Path
    package_root_name: str
    inferred_package_id: str | None


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
            infos = archive.infolist()
    except zipfile.BadZipFile as error:
        raise ImplementationPackageError(
            "The selected file is not a valid ZIP archive."
        ) from error

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


def copy_implementation_package_archive(
    archive_path: str | Path,
    contents_directory: str | Path,
) -> Path:
    inspection = inspect_implementation_package_archive(
        archive_path
    )
    source = inspection.source_path
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
