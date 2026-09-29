from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ai_project_organizer.workspace_structure import (
    discover_feature_packages,
    discover_project_features,
    feature_documents_path,
    feature_packages_path,
    is_project_feature_structure_initialized,
    is_project_package_structure_initialized,
    is_project_workspace_structure_initialized,
    package_contents_path,
    package_documents_path,
    project_documents_path,
    project_features_path,
)


PATH_ROLE = int(Qt.ItemDataRole.UserRole)
KIND_ROLE = PATH_ROLE + 1
FEATURE_ROLE = PATH_ROLE + 2
PACKAGE_ROLE = PATH_ROLE + 3

KIND_PROJECT = "project"
KIND_FEATURES = "features"
KIND_FEATURE = "feature"
KIND_PACKAGES = "packages"
KIND_PACKAGE = "package"
KIND_DOCUMENTS = "documents"
KIND_CONTENTS = "contents"
KIND_DIRECTORY = "directory"
KIND_FILE = "file"
KIND_STATUS = "status"


class ProjectView(QWidget):
    file_open_requested = Signal(str)
    new_document_requested = Signal(str)
    add_feature_requested = Signal()
    add_package_requested = Signal(str)
    initialize_project_requested = Signal()
    initialize_feature_requested = Signal(str)
    initialize_package_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.workspace_path: Path | None = None
        self.project_display_name: str | None = None

        self.add_feature_button = QPushButton(
            "Add Feature",
            self,
        )
        self.add_package_button = QPushButton(
            "Add Package",
            self,
        )
        self.refresh_button = QPushButton(
            "Refresh",
            self,
        )

        self.add_feature_button.clicked.connect(
            lambda: self.add_feature_requested.emit()
        )
        self.add_package_button.clicked.connect(
            lambda: self.add_package_requested.emit("")
        )
        self.refresh_button.clicked.connect(
            lambda: self.refresh()
        )

        controls = QHBoxLayout()
        controls.addWidget(
            self.add_feature_button
        )
        controls.addWidget(
            self.add_package_button
        )
        controls.addStretch(1)
        controls.addWidget(
            self.refresh_button
        )

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        self.status_label.hide()

        self.initialize_project_button = QPushButton(
            "Initialize Project Structure...",
            self,
        )
        self.initialize_project_button.clicked.connect(
            lambda: self.initialize_project_requested.emit()
        )
        self.initialize_project_button.hide()

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.tree.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self.tree.itemDoubleClicked.connect(
            self._activate_item
        )

        layout = QVBoxLayout(self)
        layout.addLayout(
            controls
        )
        layout.addWidget(
            self.status_label
        )
        layout.addWidget(
            self.initialize_project_button
        )
        layout.addWidget(
            self.tree,
            1,
        )

        self._update_enabled_state()

    def set_workspace(
            self,
            workspace_path: str | Path | None,
            display_name: str | None = None,
    ) -> None:
        self.workspace_path = (
            Path(workspace_path).expanduser()
            if workspace_path is not None
            else None
        )
        self.project_display_name = display_name

        self._update_enabled_state()
        self.refresh()

    def set_project_display_name(
            self,
            display_name: str | None,
    ) -> None:
        self.project_display_name = display_name

        if self.workspace_path is not None:
            self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        self.status_label.hide()
        self.initialize_project_button.hide()

        if self.workspace_path is None:
            return

        workspace = self.workspace_path
        display_name = (
            self.project_display_name
            or workspace.name
            or str(workspace)
        )

        try:
            initialized = (
                is_project_workspace_structure_initialized(
                    workspace
                )
            )
        except OSError as error:
            self._show_status(
                f"Project structure error: {error}"
            )
            return

        if not initialized:
            self._show_status(
                "This workspace does not contain the standard "
                "Project structure."
            )
            self.initialize_project_button.show()
            return

        root = self._item(
            display_name,
            workspace,
            KIND_PROJECT,
        )
        self.tree.addTopLevelItem(
            root
        )

        documents_path = project_documents_path(
            workspace
        )
        documents_item = self._item(
            "Documents",
            documents_path,
            KIND_DOCUMENTS,
        )
        root.addChild(
            documents_item
        )
        self._populate_directory(
            documents_item,
            documents_path,
        )

        features_path = project_features_path(
            workspace
        )
        features_item = self._item(
            "Features",
            features_path,
            KIND_FEATURES,
        )
        root.addChild(
            features_item
        )

        try:
            features = discover_project_features(
                workspace
            )
        except OSError as error:
            features_item.addChild(
                self._status_item(
                    f"Structure error: {error}"
                )
            )
        else:
            for feature in features:
                self._populate_feature(
                    features_item,
                    feature,
                )

        root.setExpanded(True)
        documents_item.setExpanded(True)
        features_item.setExpanded(True)

    def _populate_feature(
            self,
            parent: QTreeWidgetItem,
            feature: Path,
    ) -> None:
        feature_name = feature.name
        feature_item = self._item(
            feature_name,
            feature,
            KIND_FEATURE,
            feature_name=feature_name,
        )
        parent.addChild(
            feature_item
        )

        try:
            initialized = (
                is_project_feature_structure_initialized(
                    self.workspace_path,
                    feature_name,
                )
            )
        except OSError as error:
            feature_item.addChild(
                self._status_item(
                    f"Structure error: {error}"
                )
            )
            return

        if not initialized:
            feature_item.addChild(
                self._status_item(
                    "Structure incomplete"
                )
            )
            return

        documents_path = feature_documents_path(
            feature
        )
        documents_item = self._item(
            "Documents",
            documents_path,
            KIND_DOCUMENTS,
            feature_name=feature_name,
        )
        feature_item.addChild(
            documents_item
        )
        self._populate_directory(
            documents_item,
            documents_path,
        )

        packages_path = feature_packages_path(
            feature
        )
        packages_item = self._item(
            "Packages",
            packages_path,
            KIND_PACKAGES,
            feature_name=feature_name,
        )
        feature_item.addChild(
            packages_item
        )

        try:
            packages = discover_feature_packages(
                self.workspace_path,
                feature_name,
            )
        except OSError as error:
            packages_item.addChild(
                self._status_item(
                    f"Structure error: {error}"
                )
            )
            return

        for package in packages:
            self._populate_package(
                packages_item,
                feature_name,
                package,
            )

    def _populate_package(
            self,
            parent: QTreeWidgetItem,
            feature_name: str,
            package: Path,
    ) -> None:
        package_id = package.name
        package_item = self._item(
            package_id,
            package,
            KIND_PACKAGE,
            feature_name=feature_name,
            package_id=package_id,
        )
        parent.addChild(
            package_item
        )

        try:
            initialized = (
                is_project_package_structure_initialized(
                    self.workspace_path,
                    feature_name,
                    package_id,
                )
            )
        except OSError as error:
            package_item.addChild(
                self._status_item(
                    f"Structure error: {error}"
                )
            )
            return

        if not initialized:
            package_item.addChild(
                self._status_item(
                    "Structure incomplete"
                )
            )
            return

        documents_path = package_documents_path(
            package
        )
        documents_item = self._item(
            "Documents",
            documents_path,
            KIND_DOCUMENTS,
            feature_name=feature_name,
            package_id=package_id,
        )
        package_item.addChild(
            documents_item
        )
        self._populate_directory(
            documents_item,
            documents_path,
        )

        contents_path = package_contents_path(
            package
        )
        contents_item = self._item(
            "Contents",
            contents_path,
            KIND_CONTENTS,
            feature_name=feature_name,
            package_id=package_id,
        )
        package_item.addChild(
            contents_item
        )
        self._populate_directory(
            contents_item,
            contents_path,
        )

    def _populate_directory(
            self,
            parent: QTreeWidgetItem,
            directory: Path,
    ) -> None:
        try:
            entries = list(
                directory.iterdir()
            )
        except OSError as error:
            parent.addChild(
                self._status_item(
                    f"Unable to read: {error}"
                )
            )
            return

        entries.sort(
            key=lambda entry: (
                0
                if entry.is_dir() and not entry.is_symlink()
                else 1,
                entry.name.casefold(),
                entry.name,
            )
        )

        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                item = self._item(
                    entry.name,
                    entry,
                    KIND_DIRECTORY,
                )
                parent.addChild(
                    item
                )
                self._populate_directory(
                    item,
                    entry,
                )
                continue

            parent.addChild(
                self._item(
                    entry.name,
                    entry,
                    KIND_FILE,
                )
            )

    def _item(
            self,
            text: str,
            path: Path,
            kind: str,
            *,
            feature_name: str | None = None,
            package_id: str | None = None,
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem(
            [text]
        )
        item.setData(
            0,
            PATH_ROLE,
            str(path),
        )
        item.setData(
            0,
            KIND_ROLE,
            kind,
        )

        if feature_name is not None:
            item.setData(
                0,
                FEATURE_ROLE,
                feature_name,
            )

        if package_id is not None:
            item.setData(
                0,
                PACKAGE_ROLE,
                package_id,
            )

        return item

    def _status_item(
            self,
            text: str,
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem(
            [text]
        )
        item.setData(
            0,
            KIND_ROLE,
            KIND_STATUS,
        )
        return item

    def _activate_item(
            self,
            item: QTreeWidgetItem,
            _column: int,
    ) -> None:
        if item.data(
                0,
                KIND_ROLE,
        ) != KIND_FILE:
            return

        path = item.data(
            0,
            PATH_ROLE,
        )

        if path:
            self.file_open_requested.emit(
                path
            )

    def _show_context_menu(
            self,
            position: QPoint,
    ) -> None:
        item = self.tree.itemAt(
            position
        )

        if item is None:
            return

        kind = item.data(
            0,
            KIND_ROLE,
        )
        path_text = item.data(
            0,
            PATH_ROLE,
        )
        feature_name = item.data(
            0,
            FEATURE_ROLE,
        )
        package_id = item.data(
            0,
            PACKAGE_ROLE,
        )

        menu = QMenu(self)

        new_document_action = None
        add_package_action = None
        initialize_feature_action = None
        initialize_package_action = None
        copy_path_action = None
        open_location_action = None

        if kind in {
            KIND_PROJECT,
            KIND_FEATURE,
            KIND_PACKAGE,
            KIND_DOCUMENTS,
        }:
            documents_path = self._documents_target_for_item(
                item
            )
            if documents_path is not None and documents_path.is_dir():
                new_document_action = menu.addAction(
                    "New Document..."
                )

        if kind in {
            KIND_FEATURE,
            KIND_PACKAGES,
        } and feature_name:
            add_package_action = menu.addAction(
                "Add Package..."
            )

        if (
                kind == KIND_FEATURE
                and feature_name
                and self._feature_needs_initialization(
                    feature_name
                )
        ):
            initialize_feature_action = menu.addAction(
                "Initialize Feature Structure..."
            )

        if (
                kind == KIND_PACKAGE
                and feature_name
                and package_id
                and self._package_needs_initialization(
                    feature_name,
                    package_id,
                )
        ):
            initialize_package_action = menu.addAction(
                "Initialize Package Structure..."
            )

        if path_text:
            if menu.actions():
                menu.addSeparator()

            copy_path_action = menu.addAction(
                "Copy Path"
            )
            open_location_action = menu.addAction(
                "Open in File Manager"
            )

        if not menu.actions():
            return

        selected = menu.exec(
            self.tree.viewport().mapToGlobal(
                position
            )
        )

        if selected is new_document_action:
            documents_path = self._documents_target_for_item(
                item
            )
            if documents_path is not None:
                self.new_document_requested.emit(
                    str(documents_path)
                )

        elif selected is add_package_action and feature_name:
            self.add_package_requested.emit(
                feature_name
            )

        elif (
                selected is initialize_feature_action
                and feature_name
        ):
            self.initialize_feature_requested.emit(
                feature_name
            )

        elif (
                selected is initialize_package_action
                and feature_name
                and package_id
        ):
            self.initialize_package_requested.emit(
                feature_name,
                package_id,
            )

        elif selected is copy_path_action and path_text:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(
                path_text
            )

        elif selected is open_location_action and path_text:
            path = Path(
                path_text
            )
            target = (
                path
                if path.is_dir()
                else path.parent
            )
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(target)
                )
            )

    def _documents_target_for_item(
            self,
            item: QTreeWidgetItem,
    ) -> Path | None:
        kind = item.data(
            0,
            KIND_ROLE,
        )
        path_text = item.data(
            0,
            PATH_ROLE,
        )

        if not path_text:
            return None

        path = Path(
            path_text
        )

        if kind == KIND_DOCUMENTS:
            return path

        if kind == KIND_PROJECT:
            return project_documents_path(
                path
            )

        if kind == KIND_FEATURE:
            return feature_documents_path(
                path
            )

        if kind == KIND_PACKAGE:
            return package_documents_path(
                path
            )

        return None

    def _feature_needs_initialization(
            self,
            feature_name: str,
    ) -> bool:
        if self.workspace_path is None:
            return False

        try:
            return not is_project_feature_structure_initialized(
                self.workspace_path,
                feature_name,
            )
        except OSError:
            return False

    def _package_needs_initialization(
            self,
            feature_name: str,
            package_id: str,
    ) -> bool:
        if self.workspace_path is None:
            return False

        try:
            return not is_project_package_structure_initialized(
                self.workspace_path,
                feature_name,
                package_id,
            )
        except OSError:
            return False

    def _show_status(
            self,
            text: str,
    ) -> None:
        self.status_label.setText(
            text
        )
        self.status_label.show()

    def _update_enabled_state(self) -> None:
        enabled = self.workspace_path is not None

        self.add_feature_button.setEnabled(
            enabled
        )
        self.add_package_button.setEnabled(
            enabled
        )
        self.refresh_button.setEnabled(
            enabled
        )
