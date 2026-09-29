from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl, Signal
from PySide6.QtGui import (
    QDesktopServices,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ai_project_organizer.ui.document_list_panel import (
    DocumentListPanel,
)
from ai_project_organizer.workspace_structure import (
    discover_feature_packages,
    discover_project_features,
    feature_documents_path,
    is_project_feature_structure_initialized,
    is_project_package_structure_initialized,
    is_project_workspace_structure_initialized,
    package_documents_path,
    project_documents_path,
)


_ITEM_PATH_ROLE = int(Qt.ItemDataRole.UserRole)
_FEATURE_NAME_ROLE = _ITEM_PATH_ROLE + 1
_PACKAGE_ID_ROLE = _ITEM_PATH_ROLE + 2
_STRUCTURE_STATE_ROLE = _ITEM_PATH_ROLE + 3
_STRUCTURE_ERROR_ROLE = _ITEM_PATH_ROLE + 4

_STATE_COMPLETE = "complete"
_STATE_INCOMPLETE = "incomplete"
_STATE_ERROR = "error"


def _local_zip_candidate(
        mime_data,
) -> Path | None:
    urls = mime_data.urls()

    if len(urls) != 1:
        return None

    url = urls[0]

    if not url.isLocalFile():
        return None

    local_path = url.toLocalFile()

    if not local_path:
        return None

    path = Path(local_path)

    if (
            path.is_symlink()
            or not path.exists()
            or not path.is_file()
            or path.suffix.casefold() != ".zip"
    ):
        return None

    return path


class _ImplementationPackageDropListWidget(QListWidget):
    package_drop_requested = Signal(
        str,
        str,
    )

    def __init__(
            self,
            *,
            target_role: int,
            allow_background: bool,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._target_role = target_role
        self._allow_background = allow_background

        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.DropOnly
        )
        self.setDefaultDropAction(
            Qt.DropAction.CopyAction
        )

    def _drop_target_at(
            self,
            position: QPoint,
    ) -> str | None:
        item = self.itemAt(position)

        if item is None:
            return (
                ""
                if self._allow_background
                else None
            )

        value = item.data(
            self._target_role
        )

        if not value:
            return None

        return str(value)

    def dragEnterEvent(
            self,
            event: QDragEnterEvent,
    ) -> None:
        if _local_zip_candidate(
                event.mimeData()
        ) is None:
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.CopyAction
        )
        event.accept()

    def dragMoveEvent(
            self,
            event: QDragMoveEvent,
    ) -> None:
        if _local_zip_candidate(
                event.mimeData()
        ) is None:
            event.ignore()
            return

        target = self._drop_target_at(
            event.position().toPoint()
        )

        if target is None:
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.CopyAction
        )
        event.accept()

    def dragLeaveEvent(
            self,
            event: QDragLeaveEvent,
    ) -> None:
        super().dragLeaveEvent(event)

    def dropEvent(
            self,
            event: QDropEvent,
    ) -> None:
        source = _local_zip_candidate(
            event.mimeData()
        )
        target = self._drop_target_at(
            event.position().toPoint()
        )

        if (
                source is None
                or target is None
        ):
            event.ignore()
            return

        event.setDropAction(
            Qt.DropAction.CopyAction
        )
        event.accept()

        self.package_drop_requested.emit(
            str(source),
            target,
        )


class ProjectView(QWidget):
    file_open_requested = Signal(str)
    new_document_requested = Signal(str)
    add_feature_requested = Signal()
    add_package_requested = Signal(str)
    initialize_project_requested = Signal()
    initialize_feature_requested = Signal(str)
    initialize_package_requested = Signal(
        str,
        str,
    )
    implementation_package_import_requested = Signal(
        str,
        str,
        str,
    )
    extract_implementation_package_requested = Signal(
        str,
        str,
    )
    inspect_implementation_package_requested = Signal(
        str,
        str,
    )
    install_implementation_package_requested = Signal(
        str,
        str,
    )

    def __init__(
            self,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.workspace_path: Path | None = None
        self.project_display_name: str | None = None
        self.current_feature_name: str | None = None

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

        self.page_stack = QStackedWidget(self)

        self.project_page = self._build_project_page()
        self.feature_page = self._build_feature_page()

        self.page_stack.addWidget(
            self.project_page
        )
        self.page_stack.addWidget(
            self.feature_page
        )
        self.page_stack.setCurrentWidget(
            self.project_page
        )

        layout = QVBoxLayout(self)
        layout.addWidget(
            self.status_label
        )
        layout.addWidget(
            self.initialize_project_button
        )
        layout.addWidget(
            self.page_stack,
            1,
        )

        self._update_enabled_state()

    def _build_project_page(
            self,
    ) -> QWidget:
        page = QWidget(self)

        self.project_title_label = QLabel(page)
        self.project_refresh_button = QPushButton(
            "Refresh",
            page,
        )
        self.project_refresh_button.clicked.connect(
            self.refresh
        )

        header = QHBoxLayout()
        header.addWidget(
            self.project_title_label
        )
        header.addStretch(1)
        header.addWidget(
            self.project_refresh_button
        )

        self.project_documents_panel = DocumentListPanel(
            page
        )
        self.project_documents_panel.file_open_requested.connect(
            self.file_open_requested.emit
        )
        self.project_documents_panel.new_document_requested.connect(
            self.new_document_requested.emit
        )

        features_group = QGroupBox(
            "Features",
            page,
        )
        self.features_status_label = QLabel(
            features_group
        )
        self.features_status_label.setWordWrap(True)
        self.features_status_label.hide()

        self.feature_list = _ImplementationPackageDropListWidget(
            target_role=_FEATURE_NAME_ROLE,
            allow_background=False,
            parent=features_group,
        )
        self.feature_list.itemDoubleClicked.connect(
            self._feature_item_activated
        )
        self.feature_list.package_drop_requested.connect(
            self._feature_package_drop_requested
        )

        self.add_feature_button = QPushButton(
            "Add Feature",
            features_group,
        )
        self.add_feature_button.clicked.connect(
            lambda: self.add_feature_requested.emit()
        )

        features_layout = QVBoxLayout(
            features_group
        )
        features_layout.addWidget(
            self.features_status_label
        )
        features_layout.addWidget(
            self.feature_list,
            1,
        )
        features_layout.addWidget(
            self.add_feature_button
        )

        self.project_splitter = QSplitter(
            Qt.Orientation.Vertical,
            page,
        )
        self.project_splitter.setChildrenCollapsible(
            False
        )
        self.project_splitter.addWidget(
            self.project_documents_panel
        )
        self.project_splitter.addWidget(
            features_group
        )
        self.project_splitter.setStretchFactor(
            0,
            1,
        )
        self.project_splitter.setStretchFactor(
            1,
            1,
        )

        layout = QVBoxLayout(page)
        layout.addLayout(header)
        layout.addWidget(
            self.project_splitter,
            1,
        )

        return page

    def _build_feature_page(
            self,
    ) -> QWidget:
        page = QWidget(self)

        self.back_to_features_button = QPushButton(
            "Back to Features",
            page,
        )
        self.back_to_features_button.clicked.connect(
            self._return_to_project_page
        )

        self.feature_title_label = QLabel(page)
        self.feature_refresh_button = QPushButton(
            "Refresh",
            page,
        )
        self.feature_refresh_button.clicked.connect(
            self.refresh
        )

        header = QHBoxLayout()
        header.addWidget(
            self.back_to_features_button
        )
        header.addWidget(
            self.feature_title_label
        )
        header.addStretch(1)
        header.addWidget(
            self.feature_refresh_button
        )

        self.feature_status_label = QLabel(page)
        self.feature_status_label.setWordWrap(True)
        self.feature_status_label.hide()

        self.initialize_feature_button = QPushButton(
            "Initialize Feature Structure...",
            page,
        )
        self.initialize_feature_button.clicked.connect(
            self._request_feature_initialization
        )
        self.initialize_feature_button.hide()

        self.feature_documents_panel = DocumentListPanel(
            page
        )
        self.feature_documents_panel.file_open_requested.connect(
            self.file_open_requested.emit
        )
        self.feature_documents_panel.new_document_requested.connect(
            self.new_document_requested.emit
        )

        packages_group = QGroupBox(
            "Packages",
            page,
        )
        self.packages_status_label = QLabel(
            packages_group
        )
        self.packages_status_label.setWordWrap(True)
        self.packages_status_label.hide()

        self.package_list = _ImplementationPackageDropListWidget(
            target_role=_PACKAGE_ID_ROLE,
            allow_background=True,
            parent=packages_group,
        )
        self.package_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.package_list.customContextMenuRequested.connect(
            self._show_package_context_menu
        )
        self.package_list.package_drop_requested.connect(
            self._package_drop_requested
        )

        self.add_package_button = QPushButton(
            "Add Package",
            packages_group,
        )
        self.add_package_button.clicked.connect(
            self._request_add_package
        )

        packages_layout = QVBoxLayout(
            packages_group
        )
        packages_layout.addWidget(
            self.packages_status_label
        )
        packages_layout.addWidget(
            self.package_list,
            1,
        )
        packages_layout.addWidget(
            self.add_package_button
        )

        self.feature_splitter = QSplitter(
            Qt.Orientation.Vertical,
            page,
        )
        self.feature_splitter.setChildrenCollapsible(
            False
        )
        self.feature_splitter.addWidget(
            self.feature_documents_panel
        )
        self.feature_splitter.addWidget(
            packages_group
        )
        self.feature_splitter.setStretchFactor(
            0,
            1,
        )
        self.feature_splitter.setStretchFactor(
            1,
            1,
        )

        layout = QVBoxLayout(page)
        layout.addLayout(header)
        layout.addWidget(
            self.feature_status_label
        )
        layout.addWidget(
            self.initialize_feature_button
        )
        layout.addWidget(
            self.feature_splitter,
            1,
        )

        return page

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
        self.current_feature_name = None
        self.page_stack.setCurrentWidget(
            self.project_page
        )

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
        self.status_label.hide()
        self.initialize_project_button.hide()
        self.features_status_label.hide()

        workspace = self.workspace_path

        if workspace is None:
            self.current_feature_name = None
            self.project_title_label.clear()
            self.feature_title_label.clear()
            self.project_documents_panel.set_directory(
                None
            )
            self.feature_documents_panel.set_directory(
                None
            )
            self.feature_list.clear()
            self.package_list.clear()
            self.page_stack.setCurrentWidget(
                self.project_page
            )
            self.page_stack.hide()
            self._update_enabled_state()
            return

        try:
            initialized = (
                is_project_workspace_structure_initialized(
                    workspace
                )
            )
        except OSError as error:
            self._show_project_status(
                f"Project structure error: {error}"
            )
            self._update_enabled_state()
            return

        if not initialized:
            self._show_project_status(
                (
                    "This workspace does not contain the standard "
                    "Project structure."
                )
            )
            self.initialize_project_button.show()
            self._update_enabled_state()
            return

        self.page_stack.show()

        display_name = (
            self.project_display_name
            or workspace.name
            or str(workspace)
        )
        self.project_title_label.setText(
            display_name
        )
        self.project_documents_panel.set_directory(
            project_documents_path(
                workspace
            )
        )

        try:
            features = discover_project_features(
                workspace
            )
        except OSError as error:
            features = ()
            self.feature_list.clear()
            self._show_features_status(
                f"Unable to discover Features: {error}"
            )
        else:
            self._populate_features(
                features
            )

        current_feature = None

        if self.current_feature_name is not None:
            current_feature = next(
                (
                    feature
                    for feature in features
                    if (
                        feature.name
                        == self.current_feature_name
                    )
                ),
                None,
            )

        if current_feature is None:
            self.current_feature_name = None
            self.feature_documents_panel.set_directory(
                None
            )
            self.package_list.clear()
            self.page_stack.setCurrentWidget(
                self.project_page
            )
        else:
            self._refresh_feature_page(
                current_feature
            )
            self.page_stack.setCurrentWidget(
                self.feature_page
            )

        self._update_enabled_state()

    def _populate_features(
            self,
            features: tuple[Path, ...],
    ) -> None:
        self.feature_list.clear()
        self.features_status_label.hide()

        for feature in features:
            feature_name = feature.name
            state, error_text = self._feature_structure_state(
                feature_name
            )
            text = self._structured_item_text(
                feature_name,
                state,
            )

            item = QListWidgetItem(text)
            item.setData(
                _ITEM_PATH_ROLE,
                str(feature),
            )
            item.setData(
                _FEATURE_NAME_ROLE,
                feature_name,
            )
            item.setData(
                _STRUCTURE_STATE_ROLE,
                state,
            )

            if error_text is not None:
                item.setData(
                    _STRUCTURE_ERROR_ROLE,
                    error_text,
                )
                item.setToolTip(
                    error_text
                )

            self.feature_list.addItem(
                item
            )

    def _refresh_feature_page(
            self,
            feature_path: Path,
    ) -> None:
        feature_name = feature_path.name
        self.feature_title_label.setText(
            feature_name
        )
        self.feature_status_label.hide()
        self.initialize_feature_button.hide()
        self.packages_status_label.hide()

        state, error_text = self._feature_structure_state(
            feature_name
        )

        if state == _STATE_ERROR:
            self.feature_documents_panel.set_directory(
                None
            )
            self.package_list.clear()
            self.feature_splitter.hide()
            self._show_feature_status(
                (
                    "Feature structure error: "
                    f"{error_text}"
                )
            )
            self.add_package_button.setEnabled(
                False
            )
            return

        if state == _STATE_INCOMPLETE:
            self.feature_documents_panel.set_directory(
                None
            )
            self.package_list.clear()
            self.feature_splitter.hide()
            self._show_feature_status(
                (
                    "This Feature is missing its standard "
                    "workspace structure."
                )
            )
            self.initialize_feature_button.show()
            self.add_package_button.setEnabled(
                False
            )
            return

        self.feature_splitter.show()
        self.add_package_button.setEnabled(
            True
        )
        self.feature_documents_panel.set_directory(
            feature_documents_path(
                feature_path
            )
        )

        try:
            packages = discover_feature_packages(
                self.workspace_path,
                feature_name,
            )
        except OSError as error:
            self.package_list.clear()
            self._show_packages_status(
                f"Unable to discover Packages: {error}"
            )
            return

        self._populate_packages(
            feature_name,
            packages,
        )

    def _populate_packages(
            self,
            feature_name: str,
            packages: tuple[Path, ...],
    ) -> None:
        self.package_list.clear()
        self.packages_status_label.hide()

        for package in packages:
            package_id = package.name
            state, error_text = self._package_structure_state(
                feature_name,
                package_id,
            )
            text = self._structured_item_text(
                package_id,
                state,
            )

            item = QListWidgetItem(text)
            item.setData(
                _ITEM_PATH_ROLE,
                str(package),
            )
            item.setData(
                _PACKAGE_ID_ROLE,
                package_id,
            )
            item.setData(
                _STRUCTURE_STATE_ROLE,
                state,
            )

            if error_text is not None:
                item.setData(
                    _STRUCTURE_ERROR_ROLE,
                    error_text,
                )
                item.setToolTip(
                    error_text
                )

            self.package_list.addItem(
                item
            )

    def _feature_item_activated(
            self,
            item: QListWidgetItem,
    ) -> None:
        feature_name = item.data(
            _FEATURE_NAME_ROLE
        )

        if not feature_name:
            return

        self._open_feature(
            str(feature_name)
        )

    def _open_feature(
            self,
            feature_name: str,
    ) -> None:
        if self.workspace_path is None:
            return

        self.current_feature_name = feature_name
        self.refresh()

    def _return_to_project_page(
            self,
    ) -> None:
        self.current_feature_name = None
        self.page_stack.setCurrentWidget(
            self.project_page
        )
        self._update_enabled_state()

    def _request_feature_initialization(
            self,
    ) -> None:
        feature_name = self.current_feature_name

        if not feature_name:
            return

        self.initialize_feature_requested.emit(
            feature_name
        )

    def _request_add_package(
            self,
    ) -> None:
        feature_name = self.current_feature_name

        if not feature_name:
            return

        self.add_package_requested.emit(
            feature_name
        )

    def _feature_package_drop_requested(
            self,
            source_path: str,
            feature_name: str,
    ) -> None:
        if not feature_name:
            return

        self.implementation_package_import_requested.emit(
            source_path,
            feature_name,
            "",
        )

    def _package_drop_requested(
            self,
            source_path: str,
            package_id: str,
    ) -> None:
        feature_name = self.current_feature_name

        if not feature_name:
            return

        self.implementation_package_import_requested.emit(
            source_path,
            feature_name,
            package_id,
        )

    def _show_package_context_menu(
            self,
            position: QPoint,
    ) -> None:
        item = self.package_list.itemAt(
            position
        )

        if item is None:
            return

        feature_name = self.current_feature_name
        package_id = item.data(
            _PACKAGE_ID_ROLE
        )
        path_text = item.data(
            _ITEM_PATH_ROLE
        )
        state = item.data(
            _STRUCTURE_STATE_ROLE
        )

        if (
                not feature_name
                or not package_id
                or not path_text
        ):
            return

        package_id = str(package_id)
        package_path = Path(
            str(path_text)
        )

        menu = QMenu(self)
        new_document_action = None
        initialize_package_action = None
        extract_package_action = None
        inspect_package_action = None
        install_package_action = None

        if state == _STATE_COMPLETE:
            new_document_action = menu.addAction(
                "New Document..."
            )
            menu.addSeparator()
            extract_package_action = menu.addAction(
                "Extract Implementation Package..."
            )
            inspect_package_action = menu.addAction(
                "Inspect Implementation Package..."
            )
            install_package_action = menu.addAction(
                "Install Implementation Package..."
            )

        elif state == _STATE_INCOMPLETE:
            initialize_package_action = menu.addAction(
                "Initialize Package Structure..."
            )

        if menu.actions():
            menu.addSeparator()

        copy_path_action = menu.addAction(
            "Copy Path"
        )
        open_location_action = menu.addAction(
            "Open in File Manager"
        )

        selected = menu.exec(
            self.package_list.viewport().mapToGlobal(
                position
            )
        )

        if selected is new_document_action:
            self.new_document_requested.emit(
                str(
                    package_documents_path(
                        package_path
                    )
                )
            )

        elif selected is initialize_package_action:
            self.initialize_package_requested.emit(
                feature_name,
                package_id,
            )

        elif selected is extract_package_action:
            self.extract_implementation_package_requested.emit(
                feature_name,
                package_id,
            )

        elif selected is inspect_package_action:
            self.inspect_implementation_package_requested.emit(
                feature_name,
                package_id,
            )

        elif selected is install_package_action:
            self.install_implementation_package_requested.emit(
                feature_name,
                package_id,
            )

        elif selected is copy_path_action:
            QApplication.clipboard().setText(
                str(package_path)
            )

        elif selected is open_location_action:
            target = (
                package_path
                if package_path.is_dir()
                else package_path.parent
            )
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(target)
                )
            )

    def _feature_structure_state(
            self,
            feature_name: str,
    ) -> tuple[str, str | None]:
        workspace = self.workspace_path

        if workspace is None:
            return (
                _STATE_ERROR,
                "No Project workspace is active.",
            )

        try:
            initialized = (
                is_project_feature_structure_initialized(
                    workspace,
                    feature_name,
                )
            )
        except OSError as error:
            return (
                _STATE_ERROR,
                str(error),
            )

        return (
            _STATE_COMPLETE
            if initialized
            else _STATE_INCOMPLETE,
            None,
        )

    def _package_structure_state(
            self,
            feature_name: str,
            package_id: str,
    ) -> tuple[str, str | None]:
        workspace = self.workspace_path

        if workspace is None:
            return (
                _STATE_ERROR,
                "No Project workspace is active.",
            )

        try:
            initialized = (
                is_project_package_structure_initialized(
                    workspace,
                    feature_name,
                    package_id,
                )
            )
        except OSError as error:
            return (
                _STATE_ERROR,
                str(error),
            )

        return (
            _STATE_COMPLETE
            if initialized
            else _STATE_INCOMPLETE,
            None,
        )

    @staticmethod
    def _structured_item_text(
            name: str,
            state: str,
    ) -> str:
        if state == _STATE_INCOMPLETE:
            return (
                f"{name} — Structure incomplete"
            )

        if state == _STATE_ERROR:
            return (
                f"{name} — Structure error"
            )

        return name

    def _show_project_status(
            self,
            text: str,
    ) -> None:
        self.status_label.setText(text)
        self.status_label.show()
        self.page_stack.hide()

    def _show_features_status(
            self,
            text: str,
    ) -> None:
        self.features_status_label.setText(text)
        self.features_status_label.show()

    def _show_feature_status(
            self,
            text: str,
    ) -> None:
        self.feature_status_label.setText(text)
        self.feature_status_label.show()

    def _show_packages_status(
            self,
            text: str,
    ) -> None:
        self.packages_status_label.setText(text)
        self.packages_status_label.show()

    def _update_enabled_state(
            self,
    ) -> None:
        workspace_available = (
            self.workspace_path is not None
        )

        self.project_refresh_button.setEnabled(
            workspace_available
        )
        self.feature_refresh_button.setEnabled(
            workspace_available
        )
        self.add_feature_button.setEnabled(
            workspace_available
        )
        self.back_to_features_button.setEnabled(
            self.current_feature_name is not None
        )

        if self.current_feature_name is None:
            self.add_package_button.setEnabled(
                False
            )
