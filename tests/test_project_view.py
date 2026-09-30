import os
import shutil
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

from ai_project_organizer.ui.project_view import ProjectView
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    create_project_package,
    initialize_project_feature_structure,
    initialize_project_workspace_structure,
)


class _FakeAction:
    def __init__(
            self,
            text: str,
    ) -> None:
        self.text = text


class _RecordingMenu:
    latest_actions: list[str] = []
    selected_text: str | None = None

    def __init__(
            self,
            _parent=None,
    ) -> None:
        self._actions: list[_FakeAction] = []
        type(self).latest_actions = []

    def addAction(
            self,
            text: str,
    ) -> _FakeAction:
        action = _FakeAction(
            text
        )
        self._actions.append(
            action
        )
        type(self).latest_actions.append(
            text
        )
        return action

    def addSeparator(self) -> None:
        pass

    def actions(self) -> list[_FakeAction]:
        return self._actions

    def exec(
            self,
            _position,
    ) -> _FakeAction | None:
        for action in self._actions:
            if action.text == type(self).selected_text:
                return action

        return None


class ProjectViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        _RecordingMenu.selected_text = None

    def _initialized_workspace(
            self,
            root: Path,
            name: str = "workspace",
    ) -> Path:
        workspace = root / name
        workspace.mkdir()
        initialize_project_workspace_structure(
            workspace
        )
        return workspace

    @staticmethod
    def _list_texts(
            list_widget,
    ) -> list[str]:
        return [
            list_widget.item(
                index
            ).text()
            for index in range(
                list_widget.count()
            )
        ]

    def test_structured_pages_use_semantic_section_presentation(self) -> None:
        view = ProjectView()

        self.assertEqual(
            view.project_title_label.property(
                "role"
            ),
            "pageTitle",
        )
        self.assertEqual(
            view.project_refresh_button.property(
                "role"
            ),
            "toolbar",
        )
        self.assertEqual(
            view.features_panel.title_label.text(),
            "FEATURES",
        )
        self.assertEqual(
            view.add_feature_button.text(),
            "Add",
        )
        self.assertEqual(
            view.add_feature_button.property(
                "role"
            ),
            "toolbar",
        )
        self.assertEqual(
            view.feature_title_label.property(
                "role"
            ),
            "pageTitle",
        )
        self.assertEqual(
            view.back_to_features_button.property(
                "role"
            ),
            "toolbar",
        )
        self.assertEqual(
            view.feature_refresh_button.property(
                "role"
            ),
            "toolbar",
        )

    def test_project_page_lists_documents_and_features(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            (
                workspace
                / "Documents"
                / "Project Overview.txt"
            ).write_text(
                "overview",
                encoding="utf-8",
            )
            create_project_feature(
                workspace,
                "Feature A",
            )
            (
                workspace
                / "scratch.txt"
            ).write_text(
                "scratch",
                encoding="utf-8",
            )

            view = ProjectView()
            view.set_workspace(
                workspace,
                "Example Project",
            )

            self.assertIs(
                view.page_stack.currentWidget(),
                view.project_page,
            )
            self.assertEqual(
                view.project_title_label.text(),
                "Example Project",
            )
            self.assertIn(
                "Project Overview.txt",
                self._list_texts(
                    view.project_documents_panel.list_widget
                ),
            )
            self.assertIn(
                "Feature A",
                self._list_texts(
                    view.feature_list
                ),
            )

    def test_empty_project_shows_no_features_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )

            self.assertEqual(
                view.feature_list.count(),
                0,
            )
            self.assertFalse(
                view.features_status_label.isHidden()
            )
            self.assertIn(
                "No Features",
                view.features_status_label.text(),
            )
            self.assertTrue(
                view.add_feature_button.isEnabled()
            )

    def test_features_empty_state_clears_after_feature_is_created(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )

            create_project_feature(
                workspace,
                "Feature A",
            )
            view.refresh()

            self.assertTrue(
                view.features_status_label.isHidden()
            )
            self.assertEqual(
                view.features_status_label.text(),
                "",
            )
            self.assertIn(
                "Feature A",
                self._list_texts(
                    view.feature_list
                ),
            )

    def test_feature_navigation_and_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature A",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )

            view._feature_item_activated(
                view.feature_list.item(
                    0
                )
            )

            self.assertEqual(
                view.current_feature_name,
                "Feature A",
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.feature_page,
            )

            view._return_to_project_page()

            self.assertIsNone(
                view.current_feature_name
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.project_page,
            )

    def test_feature_page_configures_documents_and_package_workspace(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            (
                feature
                / "Documents"
                / "Feature Overview.txt"
            ).write_text(
                "feature",
                encoding="utf-8",
            )
            create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            view._open_feature(
                "Feature"
            )

            self.assertIn(
                "Feature Overview.txt",
                self._list_texts(
                    view.feature_documents_panel.list_widget
                ),
            )
            self.assertEqual(
                view.package_workspace_panel.workspace_path,
                workspace,
            )
            self.assertEqual(
                view.package_workspace_panel.feature_name,
                "Feature",
            )
            self.assertIn(
                "PKG01",
                self._list_texts(
                    view.package_workspace_panel.package_list
                ),
            )

    def test_package_workspace_signals_are_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            view._open_feature(
                "Feature"
            )

            added: list[str] = []
            imported: list[
                tuple[str, str, str]
            ] = []

            view.add_package_requested.connect(
                added.append
            )
            view.implementation_package_import_requested.connect(
                lambda source, feature, package_id: imported.append(
                    (
                        source,
                        feature,
                        package_id,
                    )
                )
            )

            view.package_workspace_panel._request_add_package()
            view.package_workspace_panel._package_drop_requested(
                "/tmp/package.zip",
                "PKG01",
            )

            self.assertEqual(
                added,
                [
                    "Feature"
                ],
            )
            self.assertEqual(
                imported,
                [
                    (
                        "/tmp/package.zip",
                        "Feature",
                        "PKG01",
                    )
                ],
            )

    def test_incomplete_project_does_not_initialize_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(
                temporary_directory
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )

            self.assertFalse(
                (
                    workspace
                    / "Documents"
                ).exists()
            )
            self.assertFalse(
                (
                    workspace
                    / "Features"
                ).exists()
            )
            self.assertIn(
                "Project structure incomplete",
                view.status_label.text(),
            )
            self.assertTrue(
                view.page_stack.isHidden()
            )

    def test_incomplete_feature_remains_visible_and_can_request_initialization(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            (
                workspace
                / "Features"
                / "Manual Feature"
            ).mkdir()

            view = ProjectView()
            view.set_workspace(
                workspace
            )

            self.assertIn(
                "Manual Feature — Structure incomplete",
                self._list_texts(
                    view.feature_list
                ),
            )

            emitted: list[str] = []
            view.initialize_feature_requested.connect(
                emitted.append
            )

            view._open_feature(
                "Manual Feature"
            )
            view._request_feature_initialization()

            self.assertIn(
                "Feature structure incomplete",
                view.feature_status_label.text(),
            )
            self.assertTrue(
                view.feature_splitter.isHidden()
            )
            self.assertEqual(
                emitted,
                [
                    "Manual Feature"
                ],
            )

    def test_incomplete_feature_transitions_to_normal_workspace_after_initialization(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            (
                workspace
                / "Features"
                / "Manual Feature"
            ).mkdir()

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            view._open_feature(
                "Manual Feature"
            )

            self.assertTrue(
                view.feature_splitter.isHidden()
            )

            initialize_project_feature_structure(
                workspace,
                "Manual Feature",
            )
            view.refresh()

            self.assertEqual(
                view.current_feature_name,
                "Manual Feature",
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.feature_page,
            )
            self.assertFalse(
                view.feature_splitter.isHidden()
            )
            self.assertTrue(
                view.feature_status_label.isHidden()
            )
            self.assertEqual(
                view.package_workspace_panel.feature_name,
                "Manual Feature",
            )

    def test_incomplete_package_remains_visible_through_package_workspace(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            (
                feature
                / "Packages"
                / "PKG01"
            ).mkdir()

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            view._open_feature(
                "Feature"
            )

            self.assertIn(
                "PKG01 — Structure incomplete",
                self._list_texts(
                    view.package_workspace_panel.package_list
                ),
            )

    def test_refresh_preserves_feature_and_selected_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )
            create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            view._open_feature(
                "Feature"
            )
            view.package_workspace_panel.package_list.setCurrentRow(
                0
            )

            view.refresh()

            self.assertEqual(
                view.current_feature_name,
                "Feature",
            )
            self.assertEqual(
                view.package_workspace_panel.current_package_id,
                "PKG01",
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.feature_page,
            )

    def test_refresh_returns_to_project_page_when_feature_is_removed(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            feature = create_project_feature(
                workspace,
                "Feature",
            )
            create_project_package(
                workspace,
                "Feature",
                "PKG01",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            view._open_feature(
                "Feature"
            )
            view.package_workspace_panel.package_list.setCurrentRow(
                0
            )

            shutil.rmtree(
                feature
            )
            view.refresh()

            self.assertIsNone(
                view.current_feature_name
            )
            self.assertIsNone(
                view.package_workspace_panel.current_package_id
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.project_page,
            )

    def test_workspace_switch_resets_feature_and_package_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace_a = self._initialized_workspace(
                root,
                "workspace-a",
            )
            workspace_b = self._initialized_workspace(
                root,
                "workspace-b",
            )
            create_project_feature(
                workspace_a,
                "Feature",
            )
            create_project_package(
                workspace_a,
                "Feature",
                "PKG01",
            )

            view = ProjectView()
            view.set_workspace(
                workspace_a
            )
            view._open_feature(
                "Feature"
            )
            view.package_workspace_panel.package_list.setCurrentRow(
                0
            )

            view.set_workspace(
                workspace_b
            )

            self.assertIsNone(
                view.current_feature_name
            )
            self.assertIsNone(
                view.package_workspace_panel.feature_name
            )
            self.assertIsNone(
                view.package_workspace_panel.current_package_id
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.project_page,
            )

    def test_project_display_name_refresh_preserves_feature_navigation(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            view._open_feature(
                "Feature"
            )

            view.set_project_display_name(
                "Renamed Project"
            )

            self.assertEqual(
                view.current_feature_name,
                "Feature",
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.feature_page,
            )
            self.assertEqual(
                view.project_title_label.text(),
                "Renamed Project",
            )

    def test_project_document_activation_emits_real_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            document = (
                workspace
                / "Documents"
                / "note.txt"
            )
            document.write_text(
                "text",
                encoding="utf-8",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )

            emitted: list[str] = []
            view.file_open_requested.connect(
                emitted.append
            )

            view.project_documents_panel._activate_item(
                view.project_documents_panel.list_widget.item(
                    0
                )
            )

            self.assertEqual(
                emitted,
                [
                    str(
                        document
                    )
                ],
            )

    def test_feature_context_menu_has_utility_actions_for_complete_feature(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            item = view.feature_list.item(
                0
            )

            with (
                patch(
                    "ai_project_organizer.ui.project_view.QMenu",
                    _RecordingMenu,
                ),
                patch.object(
                    view.feature_list,
                    "itemAt",
                    return_value=item,
                ),
            ):
                view._show_feature_context_menu(
                    QPoint(
                        0,
                        0,
                    )
                )

            self.assertIn(
                "Copy Path",
                _RecordingMenu.latest_actions,
            )
            self.assertIn(
                "Open in File Manager",
                _RecordingMenu.latest_actions,
            )
            self.assertNotIn(
                "Initialize Feature Structure...",
                _RecordingMenu.latest_actions,
            )

    def test_incomplete_feature_context_menu_can_request_initialization(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            (
                workspace
                / "Features"
                / "Manual Feature"
            ).mkdir()

            view = ProjectView()
            view.set_workspace(
                workspace
            )
            item = view.feature_list.item(
                0
            )

            emitted: list[str] = []
            view.initialize_feature_requested.connect(
                emitted.append
            )
            _RecordingMenu.selected_text = (
                "Initialize Feature Structure..."
            )

            with (
                patch(
                    "ai_project_organizer.ui.project_view.QMenu",
                    _RecordingMenu,
                ),
                patch.object(
                    view.feature_list,
                    "itemAt",
                    return_value=item,
                ),
            ):
                view._show_feature_context_menu(
                    QPoint(
                        0,
                        0,
                    )
                )

            self.assertIn(
                "Initialize Feature Structure...",
                _RecordingMenu.latest_actions,
            )
            self.assertEqual(
                emitted,
                [
                    "Manual Feature"
                ],
            )

    def test_feature_and_package_drop_intent_use_semantic_context(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            workspace = self._initialized_workspace(
                root
            )
            create_project_feature(
                workspace,
                "Feature",
            )

            view = ProjectView()
            view.set_workspace(
                workspace
            )

            emitted: list[
                tuple[str, str, str]
            ] = []
            view.implementation_package_import_requested.connect(
                lambda source, feature, package_id: emitted.append(
                    (
                        source,
                        feature,
                        package_id,
                    )
                )
            )

            view._feature_package_drop_requested(
                "/tmp/feature.zip",
                "Feature",
            )
            view._open_feature(
                "Feature"
            )
            view.package_workspace_panel._package_drop_requested(
                "/tmp/package.zip",
                "PKG01",
            )
            view.package_workspace_panel._package_drop_requested(
                "/tmp/background.zip",
                "",
            )

            self.assertEqual(
                emitted,
                [
                    (
                        "/tmp/feature.zip",
                        "Feature",
                        "",
                    ),
                    (
                        "/tmp/package.zip",
                        "Feature",
                        "PKG01",
                    ),
                    (
                        "/tmp/background.zip",
                        "Feature",
                        "",
                    ),
                ],
            )


if __name__ == "__main__":
    unittest.main()
