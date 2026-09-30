from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
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
from ai_project_organizer.ui.implementation_package_drop_list import (
    ImplementationPackageDropListWidget,
)
from ai_project_organizer.ui.package_workspace_panel import (
    PackageWorkspacePanel,
)
from ai_project_organizer.ui.resources import (
    load_icon,
)
from ai_project_organizer.ui.section_panel import (
    SectionPanel,
)
from ai_project_organizer.workspace_structure import (
    discover_project_features,
    feature_documents_path,
    is_project_feature_structure_initialized,
    is_project_workspace_structure_initialized,
    project_documents_path,
)


_ITEM_PATH_ROLE = int(
    Qt.ItemDataRole.UserRole
)
_FEATURE_NAME_ROLE = (
    _ITEM_PATH_ROLE
    + 1
)
_STRUCTURE_STATE_ROLE = (
    _ITEM_PATH_ROLE
    + 2
)
_STRUCTURE_ERROR_ROLE = (
    _ITEM_PATH_ROLE
    + 3
)

_STATE_COMPLETE = "complete"
_STATE_INCOMPLETE = "incomplete"
_STATE_ERROR = "error"


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
        super().__init__(
            parent
        )

        self.workspace_path: Path | None = None
        self.project_display_name: str | None = None
        self.current_feature_name: str | None = None

        self.status_label = QLabel(
            self
        )
        self.status_label.setWordWrap(
            True
        )
        self.status_label.setProperty(
            "role",
            "secondary",
        )
        self.status_label.hide()

        self.initialize_project_button = QPushButton(
            "Initialize Project Structure...",
            self,
        )
        self.initialize_project_button.clicked.connect(
            lambda: self.initialize_project_requested.emit()
        )
        self.initialize_project_button.hide()

        self.page_stack = QStackedWidget(
            self
        )

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

        layout = QVBoxLayout(
            self
        )
        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        layout.setSpacing(
            6
        )
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
        page = QWidget(
            self
        )

        self.project_title_label = QLabel(
            page
        )
        self.project_title_label.setProperty(
            "role",
            "pageTitle",
        )

        self.project_refresh_button = QPushButton(
            "Refresh",
            page,
        )
        self.project_refresh_button.setProperty(
            "role",
            "toolbar",
        )
        self.project_refresh_button.setIcon(
            load_icon(
                "refresh-rounded.svg"
            )
        )
        self.project_refresh_button.clicked.connect(
            self.refresh
        )

        header = QHBoxLayout()
        header.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        header.setSpacing(
            6
        )
        header.addWidget(
            self.project_title_label
        )
        header.addStretch(
            1
        )
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

        self.features_panel = SectionPanel(
            "FEATURES",
            page,
        )

        self.features_status_label = QLabel(
            self.features_panel
        )
        self.features_status_label.setWordWrap(
            True
        )
        self.features_status_label.setProperty(
            "role",
            "secondary",
        )
        self.features_status_label.hide()

        self.feature_list = ImplementationPackageDropListWidget(
            target_role=_FEATURE_NAME_ROLE,
            allow_background=False,
            parent=self.features_panel,
        )
        self.feature_list.itemDoubleClicked.connect(
            self._feature_item_activated
        )
        self.feature_list.package_drop_requested.connect(
            self._feature_package_drop_requested
        )
        self.feature_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.feature_list.customContextMenuRequested.connect(
            self._show_feature_context_menu
        )

        self.add_feature_button = QPushButton(
            "Add",
            self.features_panel,
        )
        self.add_feature_button.setProperty(
            "role",
            "toolbar",
        )
        self.add_feature_button.setIcon(
            load_icon(
                "add-rounded.svg"
            )
        )
        self.add_feature_button.clicked.connect(
            lambda: self.add_feature_requested.emit()
        )
        self.features_panel.add_header_widget(
            self.add_feature_button
        )

        self.features_panel.content_layout.addWidget(
            self.features_status_label
        )
        self.features_panel.content_layout.addWidget(
            self.feature_list,
            1,
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
            self.features_panel
        )
        self.project_splitter.setStretchFactor(
            0,
            1,
        )
        self.project_splitter.setStretchFactor(
            1,
            1,
        )

        layout = QVBoxLayout(
            page
        )
        layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )
        layout.setSpacing(
            8
        )
        layout.addLayout(
            header
        )
        layout.addWidget(
            self.project_splitter,
            1,
        )

        return page

    def _build_feature_page(
            self,
    ) -> QWidget:
        page = QWidget(
            self
        )

        self.back_to_features_button = QPushButton(
            "Back to Features",
            page,
        )
        self.back_to_features_button.setProperty(
            "role",
            "toolbar",
        )
        self.back_to_features_button.setIcon(
            load_icon(
                "go-back.svg"
            )
        )
        self.back_to_features_button.clicked.connect(
            self._return_to_project_page
        )

        self.feature_title_label = QLabel(
            page
        )
        self.feature_title_label.setProperty(
            "role",
            "pageTitle",
        )

        self.feature_refresh_button = QPushButton(
            "Refresh",
            page,
        )
        self.feature_refresh_button.setProperty(
            "role",
            "toolbar",
        )
        self.feature_refresh_button.setIcon(
            load_icon(
                "refresh-rounded.svg"
            )
        )
        self.feature_refresh_button.clicked.connect(
            self.refresh
        )

        header = QHBoxLayout()
        header.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        header.setSpacing(
            6
        )
        header.addWidget(
            self.back_to_features_button
        )
        header.addWidget(
            self.feature_title_label
        )
        header.addStretch(
            1
        )
        header.addWidget(
            self.feature_refresh_button
        )

        self.feature_status_label = QLabel(
            page
        )
        self.feature_status_label.setWordWrap(
            True
        )
        self.feature_status_label.setProperty(
            "role",
            "secondary",
        )
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

        self.package_workspace_panel = PackageWorkspacePanel(
            page
        )
        self.package_workspace_panel.file_open_requested.connect(
            self.file_open_requested.emit
        )
        self.package_workspace_panel.new_document_requested.connect(
            self.new_document_requested.emit
        )
        self.package_workspace_panel.add_package_requested.connect(
            self.add_package_requested.emit
        )
        self.package_workspace_panel.initialize_package_requested.connect(
            self.initialize_package_requested.emit
        )
        self.package_workspace_panel.implementation_package_import_requested.connect(
            self.implementation_package_import_requested.emit
        )
        self.package_workspace_panel.extract_implementation_package_requested.connect(
            self.extract_implementation_package_requested.emit
        )
        self.package_workspace_panel.inspect_implementation_package_requested.connect(
            self.inspect_implementation_package_requested.emit
        )
        self.package_workspace_panel.install_implementation_package_requested.connect(
            self.install_implementation_package_requested.emit
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
            self.package_workspace_panel
        )
        self.feature_splitter.setStretchFactor(
            0,
            1,
        )
        self.feature_splitter.setStretchFactor(
            1,
            1,
        )

        layout = QVBoxLayout(
            page
        )
        layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )
        layout.setSpacing(
            8
        )
        layout.addLayout(
            header
        )
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
            Path(
                workspace_path
            ).expanduser()
            if workspace_path is not None
            else None
        )
        self.project_display_name = display_name
        self.current_feature_name = None
        self.package_workspace_panel.set_feature(
            None,
            None,
        )
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
        self.status_label.clear()
        self.status_label.hide()
        self.initialize_project_button.hide()
        self.features_status_label.clear()
        self.features_status_label.hide()
        self.feature_status_label.clear()
        self.feature_status_label.hide()

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
            self.package_workspace_panel.set_feature(
                None,
                None,
            )
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
            self.package_workspace_panel.set_feature(
                None,
                None,
            )
            self._show_project_status(
                f"Project structure error: {error}"
            )
            self._update_enabled_state()
            return

        if not initialized:
            self.package_workspace_panel.set_feature(
                None,
                None,
            )
            self._show_project_status(
                (
                    "Project structure incomplete.\n\n"
                    "The standard Documents and Features folders "
                    "are not available."
                )
            )
            self.initialize_project_button.show()
            self._update_enabled_state()
            return

        self.page_stack.show()

        display_name = (
            self.project_display_name
            or workspace.name
            or str(
                workspace
            )
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

        requested_feature_name = self.current_feature_name
        current_feature = None

        if requested_feature_name is not None:
            current_feature = next(
                (
                    feature
                    for feature in features
                    if (
                        feature.name
                        == requested_feature_name
                    )
                ),
                None,
            )

        if current_feature is None:
            self.current_feature_name = None
            self.feature_documents_panel.set_directory(
                None
            )

            if requested_feature_name is not None:
                self.package_workspace_panel.set_feature(
                    None,
                    None,
                )

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
        self.features_status_label.clear()
        self.features_status_label.hide()

        if not features:
            self._show_features_status(
                (
                    "No Features. Add a Feature to organize "
                    "implementation work."
                )
            )
            return

        for feature in features:
            feature_name = feature.name
            state, error_text = self._feature_structure_state(
                feature_name
            )
            text = self._structured_item_text(
                feature_name,
                state,
            )

            item = QListWidgetItem(
                text
            )
            item.setData(
                _ITEM_PATH_ROLE,
                str(
                    feature
                ),
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
        self.feature_status_label.clear()
        self.feature_status_label.hide()
        self.initialize_feature_button.hide()

        state, error_text = self._feature_structure_state(
            feature_name
        )

        if state == _STATE_ERROR:
            self.feature_documents_panel.set_directory(
                None
            )
            self.package_workspace_panel.set_feature(
                None,
                None,
            )
            self.feature_splitter.hide()
            self._show_feature_status(
                (
                    "Feature structure error:"
                    f"\n\n{error_text}"
                )
            )
            return

        if state == _STATE_INCOMPLETE:
            self.feature_documents_panel.set_directory(
                None
            )
            self.package_workspace_panel.set_feature(
                None,
                None,
            )
            self.feature_splitter.hide()
            self._show_feature_status(
                (
                    "Feature structure incomplete.\n\n"
                    "The standard Documents and Packages folders "
                    "are not available."
                )
            )
            self.initialize_feature_button.show()
            return

        self.feature_splitter.show()
        self.feature_documents_panel.set_directory(
            feature_documents_path(
                feature_path
            )
        )
        self.package_workspace_panel.set_feature(
            self.workspace_path,
            feature_name,
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
            str(
                feature_name
            )
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

    def _show_feature_context_menu(
            self,
            position: QPoint,
    ) -> None:
        item = self.feature_list.itemAt(
            position
        )

        if item is None:
            return

        feature_name = item.data(
            _FEATURE_NAME_ROLE
        )
        path_text = item.data(
            _ITEM_PATH_ROLE
        )
        state = item.data(
            _STRUCTURE_STATE_ROLE
        )

        if (
                not feature_name
                or not path_text
        ):
            return

        feature_name = str(
            feature_name
        )
        feature_path = Path(
            str(
                path_text
            )
        )

        self.feature_list.setCurrentItem(
            item
        )

        menu = QMenu(
            self
        )
        initialize_feature_action = None

        if state == _STATE_INCOMPLETE:
            initialize_feature_action = menu.addAction(
                "Initialize Feature Structure..."
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
            self.feature_list.viewport().mapToGlobal(
                position
            )
        )

        if selected is initialize_feature_action:
            self.initialize_feature_requested.emit(
                feature_name
            )

        elif selected is copy_path_action:
            QApplication.clipboard().setText(
                str(
                    feature_path
                )
            )

        elif selected is open_location_action:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(
                        feature_path
                    )
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
                str(
                    error
                ),
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
        self.status_label.setText(
            text
        )
        self.status_label.show()
        self.page_stack.hide()

    def _show_features_status(
            self,
            text: str,
    ) -> None:
        self.features_status_label.setText(
            text
        )
        self.features_status_label.show()

    def _show_feature_status(
            self,
            text: str,
    ) -> None:
        self.feature_status_label.setText(
            text
        )
        self.feature_status_label.show()

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
