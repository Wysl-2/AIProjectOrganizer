import os
from pathlib import Path


def is_workspace_target(
    path: str | Path,
    workspace_path: str | Path,
) -> bool:
    try:
        target = _resolve_for_boundary(_absolute_path(path))
        workspace = _resolve_for_boundary(_absolute_path(workspace_path))
        target.relative_to(workspace)
    except (OSError, RuntimeError, ValueError):
        return False

    return True


def is_workspace_entry(
    path: str | Path,
    workspace_path: str | Path,
) -> bool:
    try:
        entry = _absolute_path(path)
        workspace_entry = _absolute_path(workspace_path)

        if same_path_entry(entry, workspace_entry):
            return True

        workspace = _resolve_for_boundary(workspace_entry)
        resolved_parent = _resolve_for_boundary(entry.parent)
        effective_entry = resolved_parent / entry.name
        effective_entry.relative_to(workspace)
    except (OSError, RuntimeError, ValueError):
        return False

    return True


def filesystem_entry_exists(
    path: str | Path,
) -> bool:
    entry = Path(path).expanduser()
    return entry.exists() or entry.is_symlink()


def same_path_entry(
    first: str | Path,
    second: str | Path,
) -> bool:
    first_identity = os.path.normcase(
        os.path.normpath(
            os.fspath(_absolute_path(first))
        )
    )
    second_identity = os.path.normcase(
        os.path.normpath(
            os.fspath(_absolute_path(second))
        )
    )

    return first_identity == second_identity


def _absolute_path(
    path: str | Path,
) -> Path:
    return Path(
        os.path.abspath(
            os.fspath(
                Path(path).expanduser()
            )
        )
    )


def _resolve_for_boundary(path: Path) -> Path:
    try:
        return path.resolve(strict=True)
    except FileNotFoundError:
        return path.resolve(strict=False)
