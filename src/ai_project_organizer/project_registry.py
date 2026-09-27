import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QStandardPaths


PROJECT_REGISTRY_FILENAME = "projects.json"
PROJECT_REGISTRY_SCHEMA_VERSION = 1

_REQUIRED_REGISTRY_KEYS = {
    "schema_version",
    "projects",
}

_REQUIRED_PROJECT_KEYS = {
    "workspace_path",
    "last_opened",
}


class ProjectRegistryError(ValueError):
    """Raised when project registry data is structurally invalid."""


@dataclass(frozen=True)
class RegisteredProject:
    workspace_path: Path
    last_opened: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "workspace_path",
            _normalized_workspace_path(self.workspace_path),
        )
        object.__setattr__(
            self,
            "last_opened",
            _normalized_timestamp(self.last_opened),
        )


class ProjectRegistry:
    def __init__(
        self,
        projects: Iterable[RegisteredProject] = (),
    ) -> None:
        self._projects: dict[str, RegisteredProject] = {}

        for project in projects:
            if not isinstance(project, RegisteredProject):
                raise TypeError(
                    "projects must contain RegisteredProject instances"
                )

            key = _workspace_identity(project.workspace_path)

            if key in self._projects:
                raise ProjectRegistryError(
                    "Project registry contains duplicate workspace paths."
                )

            self._projects[key] = project

    @property
    def projects(self) -> tuple[RegisteredProject, ...]:
        projects = sorted(
            self._projects.values(),
            key=lambda project: _workspace_identity(
                project.workspace_path
            ),
        )
        projects.sort(
            key=lambda project: project.last_opened,
            reverse=True,
        )
        return tuple(projects)

    def contains(
        self,
        workspace_path: str | Path,
    ) -> bool:
        path = _normalized_workspace_path(workspace_path)
        return _workspace_identity(path) in self._projects

    def register(
        self,
        workspace_path: str | Path,
        opened_at: datetime | None = None,
    ) -> RegisteredProject:
        project = RegisteredProject(
            workspace_path=_normalized_workspace_path(workspace_path),
            last_opened=(
                datetime.now(timezone.utc)
                if opened_at is None
                else opened_at
            ),
        )

        self._projects[
            _workspace_identity(project.workspace_path)
        ] = project

        return project

    def remove(
        self,
        workspace_path: str | Path,
    ) -> bool:
        path = _normalized_workspace_path(workspace_path)
        key = _workspace_identity(path)

        if key not in self._projects:
            return False

        del self._projects[key]
        return True


def default_project_registry_path() -> Path:
    config_location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )

    if not config_location:
        raise ProjectRegistryError(
            "Unable to determine the application configuration directory."
        )

    return Path(config_location) / PROJECT_REGISTRY_FILENAME


def load_project_registry(
    registry_path: str | Path | None = None,
) -> ProjectRegistry:
    path = _registry_path(registry_path)

    if path.is_symlink():
        raise ProjectRegistryError(
            f"Project registry file must not be a symbolic link: {path}"
        )

    if not path.exists():
        return ProjectRegistry()

    if not path.is_file():
        raise ProjectRegistryError(
            f"Project registry path is not a file: {path}"
        )

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ProjectRegistryError(
            "Project registry is not valid UTF-8 text."
        ) from error

    try:
        raw_registry = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProjectRegistryError(
            f"Project registry contains invalid JSON: {error.msg}"
        ) from error

    return _registry_from_mapping(raw_registry)


def save_project_registry(
    registry: ProjectRegistry,
    registry_path: str | Path | None = None,
) -> Path:
    if not isinstance(registry, ProjectRegistry):
        raise TypeError("registry must be a ProjectRegistry instance")

    path = _registry_path(registry_path)

    if path.is_symlink():
        raise ProjectRegistryError(
            f"Project registry file must not be a symbolic link: {path}"
        )

    if path.exists() and not path.is_file():
        raise ProjectRegistryError(
            f"Project registry path is not a file: {path}"
        )

    serialized = json.dumps(
        _registry_to_mapping(registry),
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if path.is_symlink():
        raise ProjectRegistryError(
            f"Project registry file must not be a symbolic link: {path}"
        )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)

        os.replace(
            temporary_path,
            path,
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

    return path


def _registry_path(
    registry_path: str | Path | None,
) -> Path:
    if registry_path is None:
        return default_project_registry_path()

    if not isinstance(registry_path, (str, Path)):
        raise TypeError(
            "registry_path must be a filesystem path or None"
        )

    return Path(registry_path).expanduser()


def _registry_from_mapping(
    raw_registry: object,
) -> ProjectRegistry:
    if not isinstance(raw_registry, dict):
        raise ProjectRegistryError(
            "Project registry must contain a JSON object at the top level."
        )

    keys = set(raw_registry)
    missing_keys = _REQUIRED_REGISTRY_KEYS - keys
    unexpected_keys = keys - _REQUIRED_REGISTRY_KEYS

    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ProjectRegistryError(
            f"Project registry is missing required field(s): {missing}"
        )

    if unexpected_keys:
        unexpected = ", ".join(sorted(unexpected_keys))
        raise ProjectRegistryError(
            f"Project registry contains unsupported field(s): {unexpected}"
        )

    schema_version = raw_registry["schema_version"]

    if type(schema_version) is not int:
        raise ProjectRegistryError(
            "Project registry schema_version must be an integer."
        )

    if schema_version != PROJECT_REGISTRY_SCHEMA_VERSION:
        raise ProjectRegistryError(
            "Unsupported project registry schema version: "
            f"{schema_version}."
        )

    raw_projects = raw_registry["projects"]

    if not isinstance(raw_projects, list):
        raise ProjectRegistryError(
            "Project registry field 'projects' must be a list."
        )

    projects = [
        _registered_project_from_mapping(raw_project)
        for raw_project in raw_projects
    ]

    return ProjectRegistry(projects)


def _registered_project_from_mapping(
    raw_project: object,
) -> RegisteredProject:
    if not isinstance(raw_project, dict):
        raise ProjectRegistryError(
            "Each project registry entry must contain a JSON object."
        )

    keys = set(raw_project)
    missing_keys = _REQUIRED_PROJECT_KEYS - keys
    unexpected_keys = keys - _REQUIRED_PROJECT_KEYS

    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ProjectRegistryError(
            "Project registry entry is missing required field(s): "
            f"{missing}"
        )

    if unexpected_keys:
        unexpected = ", ".join(sorted(unexpected_keys))
        raise ProjectRegistryError(
            "Project registry entry contains unsupported field(s): "
            f"{unexpected}"
        )

    workspace_path = raw_project["workspace_path"]
    last_opened = raw_project["last_opened"]

    if not isinstance(workspace_path, str):
        raise ProjectRegistryError(
            "Project registry field 'workspace_path' must be a string."
        )

    if not isinstance(last_opened, str):
        raise ProjectRegistryError(
            "Project registry field 'last_opened' must be a string."
        )

    try:
        timestamp = datetime.fromisoformat(last_opened)
    except ValueError as error:
        raise ProjectRegistryError(
            "Project registry field 'last_opened' "
            "must be a valid ISO-8601 timestamp."
        ) from error

    return RegisteredProject(
        workspace_path=Path(workspace_path),
        last_opened=timestamp,
    )


def _registry_to_mapping(
    registry: ProjectRegistry,
) -> dict[str, object]:
    return {
        "schema_version": PROJECT_REGISTRY_SCHEMA_VERSION,
        "projects": [
            {
                "workspace_path": str(project.workspace_path),
                "last_opened": project.last_opened.isoformat(),
            }
            for project in registry.projects
        ],
    }


def _normalized_workspace_path(
    value: object,
) -> Path:
    if not isinstance(value, (str, Path)):
        raise ProjectRegistryError(
            "Project workspace path must be a filesystem path."
        )

    try:
        path = Path(value).expanduser()
    except RuntimeError as error:
        raise ProjectRegistryError(
            "Project workspace path could not be expanded."
        ) from error

    if not path.is_absolute():
        raise ProjectRegistryError(
            "Project workspace path must be an absolute path."
        )

    return Path(
        os.path.normpath(
            os.fspath(path)
        )
    )


def _workspace_identity(
    path: Path,
) -> str:
    return os.path.normcase(
        os.path.normpath(
            os.fspath(path)
        )
    )


def _normalized_timestamp(
    value: object,
) -> datetime:
    if not isinstance(value, datetime):
        raise ProjectRegistryError(
            "Project last-opened value must be a datetime."
        )

    if value.utcoffset() is None:
        raise ProjectRegistryError(
            "Project last-opened timestamp must include timezone information."
        )

    return value.astimezone(timezone.utc)
