from pathlib import Path


PROJECT_DOCUMENTS_DIRECTORY_NAME = "Documents"
PROJECT_FEATURES_DIRECTORY_NAME = "Features"


def project_documents_path(
    workspace_path: str | Path,
) -> Path:
    return (
        Path(workspace_path).expanduser()
        / PROJECT_DOCUMENTS_DIRECTORY_NAME
    )


def project_features_path(
    workspace_path: str | Path,
) -> Path:
    return (
        Path(workspace_path).expanduser()
        / PROJECT_FEATURES_DIRECTORY_NAME
    )


def initialize_project_workspace_structure(
    workspace_path: str | Path,
) -> None:
    workspace = Path(
        workspace_path
    ).expanduser()

    if not workspace.exists():
        raise FileNotFoundError(
            f"Workspace directory does not exist: {workspace}"
        )

    if not workspace.is_dir():
        raise NotADirectoryError(
            f"Workspace path is not a directory: {workspace}"
        )

    standard_paths = (
        project_documents_path(workspace),
        project_features_path(workspace),
    )

    missing_paths: list[Path] = []

    for path in standard_paths:
        if path.is_symlink():
            raise NotADirectoryError(
                "Standard workspace directory must not be "
                f"a symbolic link: {path}"
            )

        if path.exists():
            if not path.is_dir():
                raise NotADirectoryError(
                    "Standard workspace path is not a "
                    f"directory: {path}"
                )
            continue

        missing_paths.append(path)

    created_paths: list[Path] = []

    try:
        for path in missing_paths:
            path.mkdir()
            created_paths.append(path)
    except OSError:
        for created_path in reversed(
            created_paths
        ):
            try:
                created_path.rmdir()
            except OSError:
                pass
        raise
