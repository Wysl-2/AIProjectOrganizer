from pathlib import Path


PROJECT_DOCUMENTS_DIRECTORY_NAME = "Documents"
PROJECT_FEATURES_DIRECTORY_NAME = "Features"
FEATURE_DOCUMENTS_DIRECTORY_NAME = "Documents"
FEATURE_PACKAGES_DIRECTORY_NAME = "Packages"


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


def project_feature_path(
    workspace_path: str | Path,
    feature_name: str,
) -> Path:
    return (
        project_features_path(workspace_path)
        / _validated_feature_name(feature_name)
    )


def feature_documents_path(
    feature_path: str | Path,
) -> Path:
    return (
        Path(feature_path).expanduser()
        / FEATURE_DOCUMENTS_DIRECTORY_NAME
    )


def feature_packages_path(
    feature_path: str | Path,
) -> Path:
    return (
        Path(feature_path).expanduser()
        / FEATURE_PACKAGES_DIRECTORY_NAME
    )


def is_project_workspace_structure_initialized(
    workspace_path: str | Path,
) -> bool:
    workspace = _validated_workspace(
        workspace_path
    )

    missing_standard_path = False

    for path in (
        project_documents_path(workspace),
        project_features_path(workspace),
    ):
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
        else:
            missing_standard_path = True

    return not missing_standard_path


def initialize_project_workspace_structure(
    workspace_path: str | Path,
) -> None:
    workspace = _validated_workspace(
        workspace_path
    )

    _initialize_standard_directories(
        (
            project_documents_path(workspace),
            project_features_path(workspace),
        )
    )


def initialize_project_feature_structure(
    workspace_path: str | Path,
    feature_name: str,
) -> None:
    workspace = _validated_workspace(
        workspace_path
    )
    features_root = _validated_features_root(
        workspace
    )
    feature = (
        features_root
        / _validated_feature_name(feature_name)
    )

    _require_real_directory(
        feature,
        "Feature directory",
    )

    _initialize_standard_directories(
        (
            feature_documents_path(feature),
            feature_packages_path(feature),
        )
    )


def create_project_feature(
    workspace_path: str | Path,
    feature_name: str,
) -> Path:
    workspace = _validated_workspace(
        workspace_path
    )
    features_root = _validated_features_root(
        workspace
    )
    normalized_name = _validated_feature_name(
        feature_name
    )
    feature = features_root / normalized_name

    if feature.exists() or feature.is_symlink():
        raise FileExistsError(
            f"Feature already exists: {feature}"
        )

    feature.mkdir()

    try:
        _initialize_standard_directories(
            (
                feature_documents_path(feature),
                feature_packages_path(feature),
            )
        )
    except OSError:
        try:
            feature.rmdir()
        except OSError:
            pass
        raise

    return feature


def discover_project_features(
    workspace_path: str | Path,
) -> tuple[Path, ...]:
    workspace = _validated_workspace(
        workspace_path
    )
    features_root = _validated_features_root(
        workspace
    )

    features = [
        entry
        for entry in features_root.iterdir()
        if (
            not entry.is_symlink()
            and entry.is_dir()
        )
    ]

    features.sort(
        key=lambda path: (
            path.name.casefold(),
            path.name,
        )
    )

    return tuple(features)


def _validated_workspace(
    workspace_path: str | Path,
) -> Path:
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

    return workspace


def _validated_features_root(
    workspace: Path,
) -> Path:
    features_root = project_features_path(
        workspace
    )

    _require_real_directory(
        features_root,
        "Project Features directory",
    )

    return features_root


def _require_real_directory(
    path: Path,
    description: str,
) -> None:
    if path.is_symlink():
        raise NotADirectoryError(
            f"{description} must not be a symbolic link: {path}"
        )

    if not path.exists():
        raise FileNotFoundError(
            f"{description} does not exist: {path}"
        )

    if not path.is_dir():
        raise NotADirectoryError(
            f"{description} is not a directory: {path}"
        )


def _validated_feature_name(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise ValueError(
            "Feature name must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            "Feature name must not be empty."
        )

    if normalized in {".", ".."}:
        raise ValueError(
            "Feature name must not be '.' or '..'."
        )

    if "/" in normalized or "\\" in normalized:
        raise ValueError(
            "Feature name must not contain path separators."
        )

    return normalized


def _initialize_standard_directories(
    paths: tuple[Path, ...],
) -> None:
    missing_paths: list[Path] = []

    for path in paths:
        if path.is_symlink():
            raise NotADirectoryError(
                "Standard directory must not be "
                f"a symbolic link: {path}"
            )

        if path.exists():
            if not path.is_dir():
                raise NotADirectoryError(
                    "Standard path is not a "
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
