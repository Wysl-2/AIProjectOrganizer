import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.project_view import (
    ProjectView,
    _local_zip_candidate,
)
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    create_project_package,
    initialize_project_workspace_structure,
)


class ProjectViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

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
            list_widget.item(index).text()
            for index in range(
                list_widget.count()
            )
        ]

    def test_project_page_lists_documents_and_features(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
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
            (workspace / "scratch.txt").write_text(
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
            self.assertNotIn(
                "scratch.txt",
                self._list_texts(
                    view.project_documents_panel.list_widget
                ),
            )

    def test_feature_navigation_and_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            create_project_feature(
                workspace,
                "Feature A",
            )

            view = ProjectView()
            view.set_workspace(workspace)

            view._feature_item_activated(
                view.feature_list.item(0)
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

    def test_feature_page_lists_documents_and_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
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
            view.set_workspace(workspace)
            view._open_feature("Feature")

            self.assertIn(
                "Feature Overview.txt",
                self._list_texts(
                    view.feature_documents_panel.list_widget
                ),
            )
            self.assertIn(
                "PKG01",
                self._list_texts(
                    view.package_list
                ),
            )

    def test_add_package_uses_current_feature(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            create_project_feature(
                workspace,
                "Feature",
            )

            view = ProjectView()
            view.set_workspace(workspace)
            view._open_feature("Feature")

            emitted: list[str] = []
            view.add_package_requested.connect(
                emitted.append
            )

            view._request_add_package()

            self.assertEqual(
                emitted,
                [
                    "Feature"
                ],
            )

    def test_incomplete_project_does_not_initialize_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            view = ProjectView()
            view.set_workspace(workspace)

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
                "standard Project structure",
                view.status_label.text(),
            )
            self.assertTrue(
                view.page_stack.isHidden()
            )

    def test_incomplete_feature_remains_visible_and_can_request_initialization(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            (
                workspace
                / "Features"
                / "Manual Feature"
            ).mkdir()

            view = ProjectView()
            view.set_workspace(workspace)

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
                "missing its standard",
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

    def test_incomplete_package_remains_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
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
            view.set_workspace(workspace)
            view._open_feature("Feature")

            self.assertIn(
                "PKG01 — Structure incomplete",
                self._list_texts(
                    view.package_list
                ),
            )

    def test_refresh_preserves_feature_or_falls_back_when_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            feature = create_project_feature(
                workspace,
                "Feature",
            )

            view = ProjectView()
            view.set_workspace(workspace)
            view._open_feature("Feature")
            view.refresh()

            self.assertEqual(
                view.current_feature_name,
                "Feature",
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.feature_page,
            )

            shutil.rmtree(feature)
            view.refresh()

            self.assertIsNone(
                view.current_feature_name
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.project_page,
            )

    def test_workspace_switch_resets_feature_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
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

            view = ProjectView()
            view.set_workspace(workspace_a)
            view._open_feature("Feature")

            view.set_workspace(workspace_b)

            self.assertIsNone(
                view.current_feature_name
            )
            self.assertIs(
                view.page_stack.currentWidget(),
                view.project_page,
            )

    def test_project_display_name_refresh_preserves_feature_navigation(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            create_project_feature(
                workspace,
                "Feature",
            )

            view = ProjectView()
            view.set_workspace(workspace)
            view._open_feature("Feature")

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
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
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
            view.set_workspace(workspace)

            emitted: list[str] = []
            view.file_open_requested.connect(
                emitted.append
            )

            view.project_documents_panel._activate_item(
                view.project_documents_panel.list_widget.item(0)
            )

            self.assertEqual(
                emitted,
                [
                    str(document)
                ],
            )

    def test_zip_candidate_filter_remains_narrow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive = root / "package.zip"
            text_file = root / "notes.txt"
            archive.write_bytes(
                b"candidate"
            )
            text_file.write_text(
                "notes",
                encoding="utf-8",
            )

            mime = QMimeData()
            mime.setUrls(
                [
                    QUrl.fromLocalFile(
                        str(archive)
                    )
                ]
            )
            self.assertEqual(
                _local_zip_candidate(mime),
                archive,
            )

            mime.setUrls(
                [
                    QUrl.fromLocalFile(
                        str(text_file)
                    )
                ]
            )
            self.assertIsNone(
                _local_zip_candidate(mime)
            )

            mime.setUrls(
                [
                    QUrl.fromLocalFile(
                        str(archive)
                    ),
                    QUrl.fromLocalFile(
                        str(text_file)
                    ),
                ]
            )
            self.assertIsNone(
                _local_zip_candidate(mime)
            )

    def test_feature_and_package_drop_intent_uses_semantic_context(
            self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
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
            view.set_workspace(workspace)

            emitted: list[
                tuple[str, str, str]
            ] = []
            view.implementation_package_import_requested.connect(
                lambda source, feature, package: emitted.append(
                    (
                        source,
                        feature,
                        package,
                    )
                )
            )

            view._feature_package_drop_requested(
                "/tmp/feature.zip",
                "Feature",
            )
            view._open_feature("Feature")
            view._package_drop_requested(
                "/tmp/package.zip",
                "PKG01",
            )
            view._package_drop_requested(
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
