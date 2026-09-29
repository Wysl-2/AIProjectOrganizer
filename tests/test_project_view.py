import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QApplication

from ai_project_organizer.ui.project_view import (
    ProjectView,
    _ProjectTreeWidget,
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

    def _initialized_workspace(self, root: Path) -> Path:
        workspace = root / "workspace"
        workspace.mkdir()
        initialize_project_workspace_structure(workspace)
        return workspace

    def _tree_texts(self, view: ProjectView) -> list[str]:
        texts: list[str] = []

        def visit(item) -> None:
            texts.append(item.text(0))
            for index in range(item.childCount()):
                visit(item.child(index))

        for index in range(view.tree.topLevelItemCount()):
            visit(view.tree.topLevelItem(index))

        return texts

    def test_complete_hierarchy_is_rendered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            (workspace / "Documents" / "Project Overview.txt").write_text(
                "overview",
                encoding="utf-8",
            )
            feature = create_project_feature(
                workspace,
                "Feature A",
            )
            (feature / "Documents" / "Feature Overview.txt").write_text(
                "feature",
                encoding="utf-8",
            )
            package = create_project_package(
                workspace,
                "Feature A",
                "PKG01",
            )
            (package / "Documents" / "Design.txt").write_text(
                "design",
                encoding="utf-8",
            )
            (package / "Contents" / "artifact.zip").write_text(
                "placeholder",
                encoding="utf-8",
            )

            view = ProjectView()
            view.set_workspace(
                workspace,
                "Example Project",
            )

            texts = self._tree_texts(view)

            for expected in (
                "Example Project",
                "Documents",
                "Features",
                "Feature A",
                "Packages",
                "PKG01",
                "Contents",
                "Project Overview.txt",
                "Feature Overview.txt",
                "Design.txt",
                "artifact.zip",
            ):
                self.assertIn(expected, texts)

    def test_arbitrary_top_level_file_is_not_shown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            (workspace / "scratch.txt").write_text(
                "scratch",
                encoding="utf-8",
            )
            view = ProjectView()
            view.set_workspace(workspace)
            self.assertNotIn(
                "scratch.txt",
                self._tree_texts(view),
            )

    def test_refresh_discovers_external_feature(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            view = ProjectView()
            view.set_workspace(workspace)
            (workspace / "Features" / "External Feature").mkdir()
            view.refresh()
            self.assertIn(
                "External Feature",
                self._tree_texts(view),
            )

    def test_incomplete_project_does_not_initialize(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            view = ProjectView()
            view.set_workspace(workspace)
            self.assertTrue(
                view.status_label.isVisible()
                or bool(view.status_label.text())
            )
            self.assertFalse(
                (workspace / "Documents").exists()
            )

    def test_file_activation_emits_real_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            document = workspace / "Documents" / "note.txt"
            document.write_text("text", encoding="utf-8")
            view = ProjectView()
            view.set_workspace(workspace)
            emitted: list[str] = []
            view.file_open_requested.connect(emitted.append)
            item = view.tree.topLevelItem(0).child(0).child(0)
            view._activate_item(item, 0)
            self.assertEqual(emitted, [str(document)])

    def test_incomplete_feature_remains_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            (workspace / "Features" / "Manual Feature").mkdir()
            view = ProjectView()
            view.set_workspace(workspace)
            texts = self._tree_texts(view)
            self.assertIn("Manual Feature", texts)
            self.assertIn("Structure incomplete", texts)

    def test_zip_candidate_filter_is_narrow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive = root / "package.zip"
            text_file = root / "notes.txt"
            archive.write_bytes(b"candidate")
            text_file.write_text("notes", encoding="utf-8")

            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(archive))])
            self.assertEqual(
                _ProjectTreeWidget._local_zip_candidate(mime),
                archive,
            )

            mime.setUrls([QUrl.fromLocalFile(str(text_file))])
            self.assertIsNone(
                _ProjectTreeWidget._local_zip_candidate(mime)
            )

            mime.setUrls([
                QUrl.fromLocalFile(str(archive)),
                QUrl.fromLocalFile(str(text_file)),
            ])
            self.assertIsNone(
                _ProjectTreeWidget._local_zip_candidate(mime)
            )

    def test_semantic_drop_targets_distinguish_feature_and_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            create_project_feature(workspace, "Feature")
            create_project_package(workspace, "Feature", "PKG01")
            view = ProjectView()
            view.set_workspace(workspace)

            project = view.tree.topLevelItem(0)
            feature = project.child(1).child(0)
            packages = feature.child(1)
            package = packages.child(0)
            documents = package.child(0)
            contents = package.child(1)

            self.assertEqual(
                view.tree._drop_target_for_item(feature),
                ("Feature", ""),
            )
            self.assertEqual(
                view.tree._drop_target_for_item(packages),
                ("Feature", ""),
            )
            self.assertEqual(
                view.tree._drop_target_for_item(package),
                ("Feature", "PKG01"),
            )
            self.assertEqual(
                view.tree._drop_target_for_item(contents),
                ("Feature", "PKG01"),
            )
            self.assertIsNone(
                view.tree._drop_target_for_item(documents)
            )

    def test_refresh_clears_drop_highlight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = self._initialized_workspace(root)
            create_project_feature(workspace, "Feature")
            view = ProjectView()
            view.set_workspace(workspace)
            feature = view.tree.topLevelItem(0).child(1).child(0)
            view.tree._set_drop_highlight(feature)
            view.refresh()
            self.assertIsNone(
                view.tree._drop_highlight_item
            )


if __name__ == "__main__":
    unittest.main()
