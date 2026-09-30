from pathlib import Path

from PySide6.QtGui import QIcon


_ICONS_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "icons"
)


def icon_path(
        name: str,
) -> Path | None:
    if not isinstance(name, str):
        return None

    if (
            not name
            or name in {".", ".."}
            or "/" in name
            or "\\" in name
    ):
        return None

    path = Path(name)

    if (
            path.name != name
            or path.suffix.casefold() != ".svg"
    ):
        return None

    candidate = _ICONS_DIRECTORY / name

    if (
            candidate.is_symlink()
            or not candidate.is_file()
    ):
        return None

    return candidate


def load_icon(
        name: str,
) -> QIcon:
    path = icon_path(
        name
    )

    if path is None:
        return QIcon()

    return QIcon(
        str(path)
    )
