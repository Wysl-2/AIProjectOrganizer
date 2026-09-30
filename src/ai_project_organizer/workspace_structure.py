from pathlib import Path


PROJECT_DOCUMENTS_DIRECTORY_NAME = "Documents"
PROJECT_FEATURES_DIRECTORY_NAME = "Features"
PROJECT_PATCHES_DIRECTORY_NAME = "Patches"
FEATURE_DOCUMENTS_DIRECTORY_NAME = "Documents"
FEATURE_PACKAGES_DIRECTORY_NAME = "Packages"
PACKAGE_DOCUMENTS_DIRECTORY_NAME = "Documents"
PACKAGE_CONTENTS_DIRECTORY_NAME = "Contents"
PACKAGE_PATCHES_DIRECTORY_NAME = "Patches"
PATCH_DOCUMENTS_DIRECTORY_NAME = "Documents"
PATCH_CONTENTS_DIRECTORY_NAME = "Contents"


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


def project_patches_path(
    workspace_path: str | Path,
) -> Path:
    return (
        Path(workspace_path).expanduser()
        / PROJECT_PATCHES_DIRECTORY_NAME
    )


def project_feature_path(
    workspace_path: str | Path,
    feature_name: str,
) -> Path:
    return (
        project_features_path(workspace_path)
        / _validated_feature_name(feature_name)
    )


def project_patch_path(
    workspace_path: str | Path,
    patch_id: str,
) -> Path:
    return (
        project_patches_path(workspace_path)
        / _validated_patch_id(patch_id)
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


def project_package_path(
    workspace_path: str | Path,
    feature_name: str,
    package_id: str,
) -> Path:
    feature = project_feature_path(
        workspace_path,
        feature_name,
    )

    return (
        feature_packages_path(feature)
        / _validated_package_id(package_id)
    )


def package_documents_path(
    package_path: str | Path,
) -> Path:
    return (
        Path(package_path).expanduser()
        / PACKAGE_DOCUMENTS_DIRECTORY_NAME
    )


def package_contents_path(
    package_path: str | Path,
) -> Path:
    return (
        Path(package_path).expanduser()
        / PACKAGE_CONTENTS_DIRECTORY_NAME
    )


def package_patches_path(
    package_path: str | Path,
) -> Path:
    return (
        Path(package_path).expanduser()
        / PACKAGE_PATCHES_DIRECTORY_NAME
    )


def package_patch_path(
    package_path: str | Path,
    patch_id: str,
) -> Path:
    return (
        package_patches_path(package_path)
        / _validated_patch_id(patch_id)
    )


def patch_documents_path(
    patch_path: str | Path,
) -> Path:
    return (
        Path(patch_path).expanduser()
        / PATCH_DOCUMENTS_DIRECTORY_NAME
    )


def patch_contents_path(
    patch_path: str | Path,
) -> Path:
    return (
        Path(patch_path).expanduser()
        / PATCH_CONTENTS_DIRECTORY_NAME
    )


def is_project_workspace_structure_initialized(
    workspace_path: str | Path,
) -> bool:
    workspace = _validated_workspace(
        workspace_path
    )

    return _are_standard_directories_initialized(
        (
            project_documents_path(workspace),
            project_features_path(workspace),
        )
    )


def is_project_feature_structure_initialized(
    workspace_path: str | Path,
    feature_name: str,
) -> bool:
    workspace = _validated_workspace(
        workspace_path
    )
    feature = _validated_feature(
        workspace,
        feature_name,
    )

    return _are_standard_directories_initialized(
        (
            feature_documents_path(feature),
            feature_packages_path(feature),
        )
    )


def is_project_package_structure_initialized(
    workspace_path: str | Path,
    feature_name: str,
    package_id: str,
) -> bool:
    workspace = _validated_workspace(
        workspace_path
    )
    packages_root = _validated_feature_packages_root(
        workspace,
        feature_name,
    )
    package = (
        packages_root
        / _validated_package_id(package_id)
    )

    _require_real_directory(
        package,
        "Package directory",
    )

    return _are_standard_directories_initialized(
        (
            package_documents_path(package),
            package_contents_path(package),
        )
    )


def is_project_patch_structure_initialized(
    workspace_path: str | Path,
    patch_id: str,
) -> bool:
    workspace = _validated_workspace(
        workspace_path
    )
    patches_root = project_patches_path(
        workspace
    )

    _require_real_directory(
        patches_root,
        "Project Patches directory",
    )

    patch = (
        patches_root
        / _validated_patch_id(patch_id)
    )

    _require_real_directory(
        patch,
        "Patch directory",
    )

    return _are_standard_directories_initialized(
        (
            patch_documents_path(patch),
            patch_contents_path(patch),
        )
    )


def is_package_patch_structure_initialized(
    workspace_path: str | Path,
    feature_name: str,
    package_id: str,
    patch_id: str,
) -> bool:
    workspace = _validated_workspace(
        workspace_path
    )
    package = _validated_project_package(
        workspace,
        feature_name,
        package_id,
    )
    patches_root = package_patches_path(
        package
    )

    _require_real_directory(
        patches_root,
        "Package Patches directory",
    )

    patch = (
        patches_root
        / _validated_patch_id(patch_id)
    )

    _require_real_directory(
        patch,
        "Patch directory",
    )

    return _are_standard_directories_initialized(
        (
            patch_documents_path(patch),
            patch_contents_path(patch),
        )
    )


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
    feature = _validated_feature(
        workspace,
        feature_name,
    )

    _initialize_standard_directories(
        (
            feature_documents_path(feature),
            feature_packages_path(feature),
        )
    )


def initialize_project_package_structure(
    workspace_path: str | Path,
    feature_name: str,
    package_id: str,
) -> None:
    workspace = _validated_workspace(
        workspace_path
    )
    packages_root = _validated_feature_packages_root(
        workspace,
        feature_name,
    )
    package = (
        packages_root
        / _validated_package_id(package_id)
    )

    _require_real_directory(
        package,
        "Package directory",
    )

    _initialize_standard_directories(
        (
            package_documents_path(package),
            package_contents_path(package),
        )
    )


def initialize_project_patch_structure(
    workspace_path: str | Path,
    patch_id: str,
) -> None:
    workspace = _validated_workspace(
        workspace_path
    )
    patches_root = project_patches_path(
        workspace
    )

    _require_real_directory(
        patches_root,
        "Project Patches directory",
    )

    patch = (
        patches_root
        / _validated_patch_id(patch_id)
    )

    _require_real_directory(
        patch,
        "Patch directory",
    )

    _initialize_standard_directories(
        (
            patch_documents_path(patch),
            patch_contents_path(patch),
        )
    )


def initialize_package_patch_structure(
    workspace_path: str | Path,
    feature_name: str,
    package_id: str,
    patch_id: str,
) -> None:
    workspace = _validated_workspace(
        workspace_path
    )
    package = _validated_project_package(
        workspace,
        feature_name,
        package_id,
    )
    patches_root = package_patches_path(
        package
    )

    _require_real_directory(
        patches_root,
        "Package Patches directory",
    )

    patch = (
        patches_root
        / _validated_patch_id(patch_id)
    )

    _require_real_directory(
        patch,
        "Patch directory",
    )

    _initialize_standard_directories(
        (
            patch_documents_path(patch),
            patch_contents_path(patch),
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


def create_project_package(
    workspace_path: str | Path,
    feature_name: str,
    package_id: str,
) -> Path:
    workspace = _validated_workspace(
        workspace_path
    )
    packages_root = _validated_feature_packages_root(
        workspace,
        feature_name,
    )
    normalized_package_id = _validated_package_id(
        package_id
    )
    package = packages_root / normalized_package_id

    if package.exists() or package.is_symlink():
        raise FileExistsError(
            f"Package already exists: {package}"
        )

    package.mkdir()

    try:
        _initialize_standard_directories(
            (
                package_documents_path(package),
                package_contents_path(package),
            )
        )
    except OSError:
        try:
            package.rmdir()
        except OSError:
            pass
        raise

    return package


def create_project_patch(
    workspace_path: str | Path,
    patch_id: str,
) -> Path:
    workspace = _validated_workspace(
        workspace_path
    )
    normalized_patch_id = _validated_patch_id(
        patch_id
    )
    patches_root = project_patches_path(
        workspace
    )

    return _create_patch(
        patches_root,
        normalized_patch_id,
        root_description="Project Patches directory",
    )


def create_package_patch(
    workspace_path: str | Path,
    feature_name: str,
    package_id: str,
    patch_id: str,
) -> Path:
    workspace = _validated_workspace(
        workspace_path
    )
    package = _validated_project_package(
        workspace,
        feature_name,
        package_id,
    )
    normalized_patch_id = _validated_patch_id(
        patch_id
    )
    patches_root = package_patches_path(
        package
    )

    return _create_patch(
        patches_root,
        normalized_patch_id,
        root_description="Package Patches directory",
    )


def discover_project_features(
    workspace_path: str | Path,
) -> tuple[Path, ...]:
    workspace = _validated_workspace(
        workspace_path
    )
    features_root = _validated_features_root(
        workspace
    )

    return _discover_real_directories(
        features_root
    )


def discover_feature_packages(
    workspace_path: str | Path,
    feature_name: str,
) -> tuple[Path, ...]:
    workspace = _validated_workspace(
        workspace_path
    )
    packages_root = _validated_feature_packages_root(
        workspace,
        feature_name,
    )

    return _discover_real_directories(
        packages_root
    )


def discover_project_patches(
    workspace_path: str | Path,
) -> tuple[Path, ...]:
    workspace = _validated_workspace(
        workspace_path
    )
    patches_root = project_patches_path(
        workspace
    )

    if not _optional_real_directory_available(
        patches_root,
        "Project Patches directory",
    ):
        return ()

    return _discover_real_directories(
        patches_root
    )


def discover_package_patches(
    workspace_path: str | Path,
    feature_name: str,
    package_id: str,
) -> tuple[Path, ...]:
    workspace = _validated_workspace(
        workspace_path
    )
    package = _validated_project_package(
        workspace,
        feature_name,
        package_id,
    )
    patches_root = package_patches_path(
        package
    )

    if not _optional_real_directory_available(
        patches_root,
        "Package Patches directory",
    ):
        return ()

    return _discover_real_directories(
        patches_root
    )


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


def _validated_feature(
    workspace: Path,
    feature_name: str,
) -> Path:
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

    return feature


def _validated_feature_packages_root(
    workspace: Path,
    feature_name: str,
) -> Path:
    feature = _validated_feature(
        workspace,
        feature_name,
    )
    packages_root = feature_packages_path(
        feature
    )

    _require_real_directory(
        packages_root,
        "Feature Packages directory",
    )

    return packages_root


def _validated_project_package(
    workspace: Path,
    feature_name: str,
    package_id: str,
) -> Path:
    packages_root = _validated_feature_packages_root(
        workspace,
        feature_name,
    )
    package = (
        packages_root
        / _validated_package_id(package_id)
    )

    _require_real_directory(
        package,
        "Package directory",
    )

    return package


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


def _optional_real_directory_available(
    path: Path,
    description: str,
) -> bool:
    if path.is_symlink():
        raise NotADirectoryError(
            f"{description} must not be a symbolic link: {path}"
        )

    if not path.exists():
        return False

    if not path.is_dir():
        raise NotADirectoryError(
            f"{description} is not a directory: {path}"
        )

    return True


def _validated_feature_name(
    value: object,
) -> str:
    return _validated_structured_directory_name(
        value,
        label="Feature name",
    )


def _validated_package_id(
    value: object,
) -> str:
    return _validated_structured_directory_name(
        value,
        label="Package ID",
    )


def _validated_patch_id(
    value: object,
) -> str:
    return _validated_structured_directory_name(
        value,
        label="Patch ID",
    )


def _validated_structured_directory_name(
    value: object,
    *,
    label: str,
) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"{label} must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{label} must not be empty."
        )

    if normalized in {".", ".."}:
        raise ValueError(
            f"{label} must not be '.' or '..'."
        )

    if "/" in normalized or "\\" in normalized:
        raise ValueError(
            f"{label} must not contain path separators."
        )

    return normalized


def _create_patch(
    patches_root: Path,
    patch_id: str,
    *,
    root_description: str,
) -> Path:
    root_created = False
    patch_created = False
    patch = patches_root / patch_id

    if patches_root.is_symlink():
        raise NotADirectoryError(
            f"{root_description} must not be a symbolic link: "
            f"{patches_root}"
        )

    if patches_root.exists():
        if not patches_root.is_dir():
            raise NotADirectoryError(
                f"{root_description} is not a directory: "
                f"{patches_root}"
            )

        if patch.exists() or patch.is_symlink():
            raise FileExistsError(
                f"Patch already exists: {patch}"
            )

    try:
        if not patches_root.exists():
            patches_root.mkdir()
            root_created = True

        if patch.exists() or patch.is_symlink():
            raise FileExistsError(
                f"Patch already exists: {patch}"
            )

        patch.mkdir()
        patch_created = True

        _initialize_standard_directories(
            (
                patch_documents_path(patch),
                patch_contents_path(patch),
            )
        )
    except OSError:
        if patch_created:
            try:
                patch.rmdir()
            except OSError:
                pass

        if root_created:
            try:
                patches_root.rmdir()
            except OSError:
                pass

        raise

    return patch


def _are_standard_directories_initialized(
    paths: tuple[Path, ...],
) -> bool:
    missing_standard_path = False

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
        else:
            missing_standard_path = True

    return not missing_standard_path


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


def _discover_real_directories(
    parent: Path,
) -> tuple[Path, ...]:
    directories = [
        entry
        for entry in parent.iterdir()
        if (
            not entry.is_symlink()
            and entry.is_dir()
        )
    ]

    directories.sort(
        key=lambda path: (
            path.name.casefold(),
            path.name,
        )
    )

    return tuple(directories)
