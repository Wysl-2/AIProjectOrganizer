import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.implementation_package_drop_list import (
    ImplementationPackageDropListWidget,
)
import ai_project_organizer.ui.patch_workspace_panel as patch_workspace_module
from ai_project_organizer.ui.patch_workspace_panel import (
    PatchWorkspacePanel,
)


class _FakeAction:
    def __init__(
            self,
            text: str,
    ) -> None:
        self.text = text


class _FakeMenu:
    def __init__(
            self,
            selected_text: str | None,
    ) -> None:
        self.selected_text = selected_text
        self.action_labels: list[str] = []
        self._actions: list[_FakeAction] = []

    def addAction(
            self,
            text: str,
    ) -> _FakeAction:
        action = _FakeAction(
            text
        )
        self.action_labels.append(
            text
        )
        self._actions.append(
            action
        )
        return action

    def addSeparator(
            self,
    ) -> None:
        self.action_labels.append(
            "---"
        )

    def actions(
            self,
    ) -> list[_FakeAction]:
        return list(
            self._actions
        )

    def exec(
            self,
            _position,
    ) -> _FakeAction | None:
        for action in self._actions:
            if action.text == self.selected_text:
                return action

        return None


class PatchWorkspacePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def _create_patch(
            root: Path,
            patch_id: str,
            *,
            complete: bool = True,
    ) -> Path:
        patch_path = root / patch_id
        patch_path.mkdir()

        if complete:
            (
                patch_path
                / "Documents"
            ).mkdir()
            (
                patch_path
                / "Contents"
            ).mkdir()

        return patch_path

    def _panel(
            self,
            root: Path,
    ) -> PatchWorkspacePanel:
        panel = PatchWorkspacePanel()

        def discover():
            return tuple(
                sorted(
                    (
                        path
                        for path in root.iterdir()
                        if path.is_dir()
                    ),
                    key=lambda path: (
                        path.name.casefold(),
                        path.name,
                    ),
                )
            )

        def ready(
                patch_id: str,
        ) -> bool:
            patch_path = root / patch_id
            return (
                (
                    patch_path
                    / "Documents"
                ).is_dir()
                and (
                    patch_path
                    / "Contents"
                ).is_dir()
            )

        panel.set_context(
            (
                "test",
                root,
            ),
            owner_label="Project",
            discover_patches=discover,
            is_patch_structure_initialized=ready,
        )
        return panel

    def test_patch_list_reuses_drop_widget_and_rejects_background_target(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            self._create_patch(
                root,
                "Fix",
            )
            panel = self._panel(
                root
            )
            item = panel.patch_list.item(
                0
            )

            self.assertIsInstance(
                panel.patch_list,
                ImplementationPackageDropListWidget,
            )

            with patch.object(
                panel.patch_list,
                "itemAt",
                return_value=item,
            ):
                self.assertEqual(
                    panel.patch_list._drop_target_at(
                        QPoint(
                            0,
                            0,
                        )
                    ),
                    "Fix",
                )

            with patch.object(
                panel.patch_list,
                "itemAt",
                return_value=None,
            ):
                self.assertIsNone(
                    panel.patch_list._drop_target_at(
                        QPoint(
                            0,
                            0,
                        )
                    )
                )

    def test_patch_drop_emits_existing_import_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            self._create_patch(
                root,
                "Fix",
            )
            panel = self._panel(
                root
            )
            emitted = []

            panel.implementation_package_import_requested.connect(
                lambda source, patch_id: emitted.append(
                    (
                        source,
                        patch_id,
                    )
                )
            )

            panel._patch_drop_requested(
                "/tmp/fix.zip",
                "Fix",
            )

            self.assertEqual(
                emitted,
                [
                    (
                        "/tmp/fix.zip",
                        "Fix",
                    )
                ],
            )

    def test_patch_drop_without_context_emits_nothing(self) -> None:
        panel = PatchWorkspacePanel()
        emitted = []

        panel.implementation_package_import_requested.connect(
            lambda source, patch_id: emitted.append(
                (
                    source,
                    patch_id,
                )
            )
        )

        panel._patch_drop_requested(
            "/tmp/fix.zip",
            "Fix",
        )

        self.assertEqual(
            emitted,
            [],
        )

    def test_complete_patch_context_menu_has_utility_actions_only(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            patch_path = self._create_patch(
                root,
                "Fix",
            )
            panel = self._panel(
                root
            )
            item = panel.patch_list.item(
                0
            )
            fake_menu = _FakeMenu(
                "Copy Path"
            )

            with (
                patch.object(
                    panel.patch_list,
                    "itemAt",
                    return_value=item,
                ),
                patch.object(
                    patch_workspace_module,
                    "QMenu",
                    return_value=fake_menu,
                ),
            ):
                panel._show_patch_context_menu(
                    QPoint(
                        0,
                        0,
                    )
                )

            self.assertEqual(
                fake_menu.action_labels,
                [
                    "Copy Path",
                    "Open in File Manager",
                ],
            )
            self.assertEqual(
                QApplication.clipboard().text(),
                str(
                    patch_path
                ),
            )
            self.assertEqual(
                panel.current_patch_id,
                "Fix",
            )

    def test_incomplete_patch_context_menu_can_request_initialization(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            self._create_patch(
                root,
                "Broken",
                complete=False,
            )
            panel = self._panel(
                root
            )
            item = panel.patch_list.item(
                0
            )
            fake_menu = _FakeMenu(
                "Initialize Patch Structure..."
            )
            emitted = []

            panel.initialize_patch_requested.connect(
                emitted.append
            )

            with (
                patch.object(
                    panel.patch_list,
                    "itemAt",
                    return_value=item,
                ),
                patch.object(
                    patch_workspace_module,
                    "QMenu",
                    return_value=fake_menu,
                ),
            ):
                panel._show_patch_context_menu(
                    QPoint(
                        0,
                        0,
                    )
                )

            self.assertEqual(
                fake_menu.action_labels,
                [
                    "Initialize Patch Structure...",
                    "---",
                    "Copy Path",
                    "Open in File Manager",
                ],
            )
            self.assertEqual(
                emitted,
                [
                    "Broken"
                ],
            )

    def test_open_in_file_manager_uses_patch_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            patch_path = self._create_patch(
                root,
                "Fix",
            )
            panel = self._panel(
                root
            )
            item = panel.patch_list.item(
                0
            )
            fake_menu = _FakeMenu(
                "Open in File Manager"
            )

            with (
                patch.object(
                    panel.patch_list,
                    "itemAt",
                    return_value=item,
                ),
                patch.object(
                    patch_workspace_module,
                    "QMenu",
                    return_value=fake_menu,
                ),
                patch.object(
                    patch_workspace_module.QDesktopServices,
                    "openUrl",
                    return_value=True,
                ) as open_url,
            ):
                panel._show_patch_context_menu(
                    QPoint(
                        0,
                        0,
                    )
                )

            self.assertEqual(
                open_url.call_count,
                1,
            )
            opened_url = open_url.call_args.args[
                0
            ]
            self.assertEqual(
                Path(
                    opened_url.toLocalFile()
                ),
                patch_path,
            )


if __name__ == "__main__":
    unittest.main()
