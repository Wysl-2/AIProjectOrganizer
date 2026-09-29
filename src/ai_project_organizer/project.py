import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


PROJECT_METADATA_FILENAME = ".aiproject.json"
PROJECT_METADATA_SCHEMA_VERSION = 1

_REQUIRED_METADATA_KEYS = {
    "schema_version",
    "name",
    "working_directory",
    "local_git_repository",
    "github_repository",
}


class ProjectMetadataError(ValueError):
    """Raised when project metadata is structurally invalid."""


@dataclass(frozen=True)
class ProjectMetadata:
    name: str
    working_directory: Path
    local_git_repository: Path
    github_repository: str

    def __post_init__(self) -> None:
        name = _validated_name(self.name)
        working_directory = _validated_absolute_path(
            self.working_directory,
            "working_directory",
        )
        local_git_repository = _validated_absolute_path(
            self.local_git_repository,
            "local_git_repository",
        )
        github_repository = _validated_github_repository(
            self.github_repository
        )

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "working_directory", working_directory)
        object.__setattr__(
            self,
            "local_git_repository",
            local_git_repository,
        )
        object.__setattr__(
            self,
            "github_repository",
            github_repository,
        )


def load_project_metadata(
    workspace_path: str | Path,
) -> ProjectMetadata | None:
    metadata_path = _metadata_path(workspace_path)

    if metadata_path.is_symlink():
        raise ProjectMetadataError(
            f"Project metadata file must not be a symbolic link: {metadata_path}"
        )

    if not metadata_path.exists():
        return None

    if not metadata_path.is_file():
        raise ProjectMetadataError(
            f"Project metadata path is not a file: {metadata_path}"
        )

    try:
        text = metadata_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ProjectMetadataError(
            "Project metadata is not valid UTF-8 text."
        ) from error

    try:
        raw_metadata = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProjectMetadataError(
            f"Project metadata contains invalid JSON: {error.msg}"
        ) from error

    return _metadata_from_mapping(raw_metadata)


def save_project_metadata(
    workspace_path: str | Path,
    metadata: ProjectMetadata,
) -> Path:
    if not isinstance(metadata, ProjectMetadata):
        raise TypeError("metadata must be a ProjectMetadata instance")

    workspace = Path(workspace_path).expanduser()

    if not workspace.exists():
        raise FileNotFoundError(
            f"Workspace directory does not exist: {workspace}"
        )

    if not workspace.is_dir():
        raise NotADirectoryError(
            f"Workspace path is not a directory: {workspace}"
        )

    metadata_path = workspace / PROJECT_METADATA_FILENAME

    _validate_metadata_destination(
        metadata_path
    )

    serialized = (
        json.dumps(
            _metadata_to_mapping(metadata),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=workspace,
            prefix=f".{metadata_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(
                temporary_file.name
            )
            temporary_file.write(
                serialized
            )
            temporary_file.flush()
            os.fsync(
                temporary_file.fileno()
            )

        _validate_metadata_destination(
            metadata_path
        )

        os.replace(
            temporary_path,
            metadata_path,
        )
        temporary_path = None

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    return metadata_path


def create_project_workspace(
    workspace_path: str | Path,
    metadata: ProjectMetadata,
) -> Path:
    if not isinstance(metadata, ProjectMetadata):
        raise TypeError("metadata must be a ProjectMetadata instance")

    if not isinstance(workspace_path, (str, Path)):
        raise ProjectMetadataError(
            "Project workspace path must be a filesystem path."
        )

    workspace = Path(
        workspace_path
    ).expanduser()

    if not workspace.is_absolute():
        raise ProjectMetadataError(
            "Project workspace path must be an absolute path."
        )

    if workspace.exists() or workspace.is_symlink():
        raise FileExistsError(
            f"Project workspace already exists: {workspace}"
        )

    parent = workspace.parent

    if not parent.exists():
        raise FileNotFoundError(
            f"Project workspace parent does not exist: {parent}"
        )

    if not parent.is_dir():
        raise NotADirectoryError(
            f"Project workspace parent is not a directory: {parent}"
        )

    workspace.mkdir()

    try:
        save_project_metadata(
            workspace,
            metadata,
        )
    except (ProjectMetadataError, OSError):
        try:
            workspace.rmdir()
        except OSError:
            pass
        raise

    return workspace


def _metadata_path(workspace_path: str | Path) -> Path:
    return Path(workspace_path).expanduser() / PROJECT_METADATA_FILENAME


def _validate_metadata_destination(
    metadata_path: Path,
) -> None:
    if metadata_path.is_symlink():
        raise ProjectMetadataError(
            f"Project metadata file must not be a symbolic link: {metadata_path}"
        )

    if metadata_path.exists() and not metadata_path.is_file():
        raise ProjectMetadataError(
            f"Project metadata path is not a file: {metadata_path}"
        )


def _metadata_from_mapping(raw_metadata: object) -> ProjectMetadata:
    if not isinstance(raw_metadata, dict):
        raise ProjectMetadataError(
            "Project metadata must contain a JSON object at the top level."
        )

    keys = set(raw_metadata)
    missing_keys = _REQUIRED_METADATA_KEYS - keys
    unexpected_keys = keys - _REQUIRED_METADATA_KEYS

    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ProjectMetadataError(
            f"Project metadata is missing required field(s): {missing}"
        )

    if unexpected_keys:
        unexpected = ", ".join(sorted(unexpected_keys))
        raise ProjectMetadataError(
            f"Project metadata contains unsupported field(s): {unexpected}"
        )

    schema_version = raw_metadata["schema_version"]

    if type(schema_version) is not int:
        raise ProjectMetadataError(
            "Project metadata schema_version must be an integer."
        )

    if schema_version != PROJECT_METADATA_SCHEMA_VERSION:
        raise ProjectMetadataError(
            "Unsupported project metadata schema version: "
            f"{schema_version}."
        )

    name = raw_metadata["name"]
    working_directory = raw_metadata["working_directory"]
    local_git_repository = raw_metadata["local_git_repository"]
    github_repository = raw_metadata["github_repository"]

    if not isinstance(name, str):
        raise ProjectMetadataError(
            "Project metadata field 'name' must be a string."
        )

    if not isinstance(working_directory, str):
        raise ProjectMetadataError(
            "Project metadata field 'working_directory' must be a string."
        )

    if not isinstance(local_git_repository, str):
        raise ProjectMetadataError(
            "Project metadata field 'local_git_repository' must be a string."
        )

    if not isinstance(github_repository, str):
        raise ProjectMetadataError(
            "Project metadata field 'github_repository' must be a string."
        )

    return ProjectMetadata(
        name=name,
        working_directory=Path(working_directory),
        local_git_repository=Path(local_git_repository),
        github_repository=github_repository,
    )


def _metadata_to_mapping(metadata: ProjectMetadata) -> dict[str, object]:
    return {
        "schema_version": PROJECT_METADATA_SCHEMA_VERSION,
        "name": metadata.name,
        "working_directory": str(metadata.working_directory),
        "local_git_repository": str(metadata.local_git_repository),
        "github_repository": metadata.github_repository,
    }


def _validated_name(value: object) -> str:
    if not isinstance(value, str):
        raise ProjectMetadataError("Project name must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ProjectMetadataError("Project name must not be empty.")

    return normalized


def _validated_absolute_path(
    value: object,
    field_name: str,
) -> Path:
    if not isinstance(value, (str, Path)):
        raise ProjectMetadataError(
            f"Project metadata field '{field_name}' must be a filesystem path."
        )

    path = Path(value).expanduser()

    if not path.is_absolute():
        raise ProjectMetadataError(
            f"Project metadata field '{field_name}' must be an absolute path."
        )

    return path


def _validated_github_repository(value: object) -> str:
    if not isinstance(value, str):
        raise ProjectMetadataError(
            "GitHub repository identifier must be a string."
        )

    normalized = value.strip()
    parts = normalized.split("/")

    if (
        len(parts) != 2
        or not parts[0].strip()
        or not parts[1].strip()
        or parts[0] != parts[0].strip()
        or parts[1] != parts[1].strip()
    ):
        raise ProjectMetadataError(
            "GitHub repository identifier must use the form 'owner/repository'."
        )

    return normalized
