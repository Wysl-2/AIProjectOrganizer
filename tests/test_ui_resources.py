import os
import tomllib
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.resources import (
    icon_path,
    load_icon,
)
from ai_project_organizer.ui.theme import (
    ICON_FOREGROUND_COLOR,
)


_ICON_NAMES = (
    "add-rounded.svg",
    "folder.svg",
    "go-back.svg",
    "import.svg",
    "inspect.svg",
    "install-line.svg",
    "refresh-rounded.svg",
)


class UiResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = (
            QApplication.instance()
            or QApplication([])
        )

    def test_known_icons_resolve(self) -> None:
        for name in _ICON_NAMES:
            with self.subTest(
                    name=name
            ):
                path = icon_path(
                    name
                )

                self.assertIsNotNone(
                    path
                )
                self.assertEqual(
                    path.name,
                    name,
                )
                self.assertTrue(
                    path.is_file()
                )

    def test_known_icons_load(self) -> None:
        for name in _ICON_NAMES:
            with self.subTest(
                    name=name
            ):
                self.assertFalse(
                    load_icon(
                        name
                    ).isNull()
                )

    def test_missing_icon_returns_empty_icon(self) -> None:
        self.assertTrue(
            load_icon(
                "does-not-exist.svg"
            ).isNull()
        )

    def test_path_components_are_rejected(self) -> None:
        for name in (
            "../refresh-rounded.svg",
            "icons/refresh-rounded.svg",
            "icons\\refresh-rounded.svg",
            "/tmp/refresh-rounded.svg",
            "refresh-rounded.png",
        ):
            with self.subTest(
                    name=name
            ):
                self.assertIsNone(
                    icon_path(
                        name
                    )
                )

    def test_icons_use_theme_foreground_paint(self) -> None:
        expected = (
            ICON_FOREGROUND_COLOR
            .casefold()
        )

        for name in _ICON_NAMES:
            with self.subTest(
                    name=name
            ):
                path = icon_path(
                    name
                )
                self.assertIsNotNone(
                    path
                )

                source = path.read_text(
                    encoding="utf-8"
                ).casefold()

                self.assertNotIn(
                    "currentcolor",
                    source,
                )
                self.assertIn(
                    expected,
                    source,
                )

    def test_package_data_includes_svg_icons(self) -> None:
        project_root = (
            Path(__file__).resolve().parents[1]
        )
        configuration = tomllib.loads(
            (
                project_root
                / "pyproject.toml"
            ).read_text(
                encoding="utf-8"
            )
        )

        package_data = (
            configuration
            .get("tool", {})
            .get("setuptools", {})
            .get("package-data", {})
        )

        self.assertIn(
            "resources/icons/*.svg",
            package_data.get(
                "ai_project_organizer",
                [],
            ),
        )


if __name__ == "__main__":
    unittest.main()
