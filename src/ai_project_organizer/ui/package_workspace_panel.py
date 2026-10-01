from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QBrush, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ai_project_organizer.ui.implementation_package_drop_list import (
    ImplementationPackageDropListWidget,
)
from ai_project_organizer.ui.implementation_work_item_panel import (
    ImplementationWorkItemPanel,
)
from ai_project_organizer.ui.resources import (
    load_icon,
)
from ai_project_organizer.ui.section_panel import (
    SectionPanel,
)
from ai_project_organizer.ui.theme import (
    ERROR_COLOR,
    WARNING_COLOR,
)
from ai_project_organizer.workspace_structure import (
    discover_feature_packages,
    is_project_package_structure_initialized,
    package_contents_path,
    package_documents_path,
)


_ITEM_PATH_ROLE = int(
    Qt.ItemDataRole.UserRole
)
_PACKAGE_ID_ROLE = (
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


class PackageWorkspacePanel(SectionPanel):
    file_open_requested = Signal(str)
    new_document_requested = Signal(str)
    add_package_requested = Signal(str)
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
            "PACKAGES",
            parent,
        )

        self.workspace_path: Path | None = None
        self.feature_name: str | None = None
        self.current_package_id: str | None = None

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

        self.package_list = ImplementationPackageDropListWidget(
            target_role=_PACKAGE_ID_ROLE,
            allow_background=True,
            parent=self,
        )
        self.package_list.setProperty(
            "role",
            "packageList",
        )
        self.package_list.currentItemChanged.connect(
            self._package_selection_changed
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
            "Add",
            self,
        )
        self.add_package_button.setProperty(
            "role",
            "toolbar",
        )
        self.add_package_button.setIcon(
            load_icon(
                "add-rounded.svg"
            )
        )
        self.add_package_button.clicked.connect(
            self._request_add_package
        )
        self.add_header_widget(
            self.add_package_button
        )

        self.details_stack = QStackedWidget(
            self
        )
        self.no_selection_page = self._build_no_selection_page()
        self.work_item_panel = ImplementationWorkItemPanel(
            self
        )
        self.work_item_panel.file_open_requested.connect(
            self.file_open_requested.emit
        )
        self.work_item_panel.new_document_requested.connect(
            self.new_document_requested.emit
        )
        self.work_item_panel.implementation_package_import_requested.connect(
            self._work_item_import_requested
        )
        self.work_item_panel.extract_implementation_package_requested.connect(
            self._work_item_extraction_requested
        )
        self.work_item_panel.inspect_implementation_package_requested.connect(
            self._work_item_inspection_requested
        )
        self.work_item_panel.install_implementation_package_requested.connect(
            self._work_item_installation_requested
        )
        self.recovery_page = self._build_recovery_page()

        self.details_stack.addWidget(
            self.no_selection_page
        )
        self.details_stack.addWidget(
            self.work_item_panel
        )
        self.details_stack.addWidget(
            self.recovery_page
        )
        self.details_stack.setCurrentWidget(
            self.no_selection_page
        )
        self.splitter = QSplitter(
            Qt.Orientation.Horizontal,
            self,
        )
        self.splitter.setChildrenCollapsible(
            False
        )
        self.splitter.addWidget(
            self.package_list
        )
        self.splitter.addWidget(
            self.details_stack
        )
        self.splitter.setStretchFactor(
            0,
            1,
        )
        self.splitter.setStretchFactor(
            1,
            3,
        )
        self.splitter.setSizes(
            [
                220,
                660,
            ]
        )

        self.content_layout.addWidget(
            self.status_label
        )
        self.content_layout.addWidget(
            self.splitter,
            1,
        )

        self._update_enabled_state()
    def _build_no_selection_page(
            self,
    ) -> QWidget:
        page = QWidget(
            self
        )

        self.no_selection_title_label = QLabel(
            "No Package Selected",
            page,
        )
        self.no_selection_title_label.setProperty(
            "role",
            "pageTitle",
        )

        self.no_selection_label = QLabel(
            (
                "Select a Package to view its documents and "
                "implementation package information."
            ),
            page,
        )
        self.no_selection_label.setWordWrap(
            True
        )
        self.no_selection_label.setProperty(
            "role",
            "secondary",
        )

        layout = QVBoxLayout(
            page
        )
        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )
        layout.setSpacing(
            6
        )
        layout.addWidget(
            self.no_selection_title_label
        )
        layout.addWidget(
            self.no_selection_label
        )
        layout.addStretch(
            1
        )

        return page

    def _build_recovery_page(
            self,
    ) -> QWidget:
        page = QWidget(
            self
        )

        self.recovery_title_label = QLabel(
            page
        )
        self.recovery_title_label.setProperty(
            "role",
            "pageTitle",
        )

        self.recovery_status_label = QLabel(
            page
        )
        self.recovery_status_label.setWordWrap(
            True
        )
        self.recovery_status_label.setProperty(
            "role",
            "secondary",
        )

        self.initialize_package_button = QPushButton(
            "Initialize Package Structure...",
            page,
        )
        self.initialize_package_button.clicked.connect(
            self._request_package_initialization
        )
        self.initialize_package_button.hide()

        layout = QVBoxLayout(
            page
        )
        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )
        layout.setSpacing(
            6
        )
        layout.addWidget(
            self.recovery_title_label
        )
        layout.addWidget(
            self.recovery_status_label
        )
        layout.addWidget(
            self.initialize_package_button
        )
        layout.addStretch(
            1
        )

        return page

    def set_feature(
            self,
            workspace_path: str | Path | None,
            feature_name: str | None,
    ) -> None:
        workspace = (
            Path(
                workspace_path
            ).expanduser()
            if workspace_path is not None
            else None
        )

        context_changed = (
            workspace != self.workspace_path
            or feature_name != self.feature_name
        )

        self.workspace_path = workspace
        self.feature_name = feature_name

        if context_changed:
            self.current_package_id = None

        self.refresh()

    def refresh(self) -> None:
        self.status_label.clear()
        self.status_label.hide()

        workspace = self.workspace_path
        feature_name = self.feature_name

        if (
                workspace is None
                or not feature_name
        ):
            self.current_package_id = None
            self.package_list.blockSignals(
                True
            )
            self.package_list.clear()
            self.package_list.blockSignals(
                False
            )
            self._show_no_selection()
            self._update_enabled_state()
            return

        selected_package_id = self.current_package_id

        try:
            packages = discover_feature_packages(
                workspace,
                feature_name,
            )
        except OSError as error:
            self.current_package_id = None
            self.package_list.blockSignals(
                True
            )
            self.package_list.clear()
            self.package_list.blockSignals(
                False
            )
            self._show_status(
                f"Unable to discover Packages: {error}"
            )
            self._show_no_selection(
                (
                    "Package details are unavailable while "
                    "Packages cannot be discovered."
                ),
                title="Packages Unavailable",
            )
            self._update_enabled_state()
            return

        self.package_list.blockSignals(
            True
        )
        self.package_list.clear()

        selected_item = None

        for package in packages:
            package_id = package.name
            state, error_text = self._package_structure_state(
                package_id
            )
            item = QListWidgetItem(
                self._structured_item_text(
                    package_id,
                    state,
                )
            )
            item.setData(
                _ITEM_PATH_ROLE,
                str(
                    package
                ),
            )
            item.setData(
                _PACKAGE_ID_ROLE,
                package_id,
            )
            item.setData(
                _STRUCTURE_STATE_ROLE,
                state,
            )

            if state == _STATE_INCOMPLETE:
                item.setForeground(
                    QBrush(
                        QColor(
                            WARNING_COLOR
                        )
                    )
                )
                item.setToolTip(
                    "Package structure is incomplete."
                )

            elif state == _STATE_ERROR:
                item.setForeground(
                    QBrush(
                        QColor(
                            ERROR_COLOR
                        )
                    )
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

            if package_id == selected_package_id:
                selected_item = item

        if not packages:
            self.current_package_id = None
            self.package_list.clearSelection()
            self.package_list.blockSignals(
                False
            )
            self._show_status(
                (
                    "No Packages. Add a Package to organize "
                    "implementation work for this Feature."
                )
            )
            self._show_no_selection(
                (
                    "Create a Package to begin organizing "
                    "implementation work for this Feature."
                ),
                title="No Packages",
            )
            self._update_enabled_state()
            return

        if selected_item is not None:
            self.package_list.setCurrentItem(
                selected_item
            )
        else:
            self.current_package_id = None
            self.package_list.clearSelection()

        self.package_list.blockSignals(
            False
        )

        self._refresh_selected_package()
        self._update_enabled_state()

    def _package_selection_changed(
            self,
            current: QListWidgetItem | None,
            _previous: QListWidgetItem | None,
    ) -> None:
        self.current_package_id = (
            str(
                current.data(
                    _PACKAGE_ID_ROLE
                )
            )
            if (
                current is not None
                and current.data(
                    _PACKAGE_ID_ROLE
                )
            )
            else None
        )

        self._refresh_selected_package()

    def _refresh_selected_package(
            self,
    ) -> None:
        package_id = self.current_package_id

        if package_id is None:
            self._show_no_selection()
            return

        item = self._item_for_package_id(
            package_id
        )

        if item is None:
            self.current_package_id = None
            self._show_no_selection()
            return

        path_text = item.data(
            _ITEM_PATH_ROLE
        )
        state = item.data(
            _STRUCTURE_STATE_ROLE
        )
        error_text = item.data(
            _STRUCTURE_ERROR_ROLE
        )

        if not path_text:
            self.current_package_id = None
            self._show_no_selection()
            return

        package_path = Path(
            str(
                path_text
            )
        )

        if state == _STATE_COMPLETE:
            self._show_complete_package(
                package_id,
                package_path,
            )
            return

        self._clear_selected_package_presentation()
        self.recovery_title_label.setText(
            package_id
        )

        if state == _STATE_INCOMPLETE:
            self._set_label_role(
                self.recovery_status_label,
                "warning",
            )
            self.recovery_status_label.setText(
                "Package structure incomplete."
            )
            self.initialize_package_button.show()
        else:
            self._set_label_role(
                self.recovery_status_label,
                "error",
            )
            self.recovery_status_label.setText(
                (
                    "Unable to inspect Package structure."
                    + (
                        f"\n\n{error_text}"
                        if error_text
                        else ""
                    )
                )
            )
            self.initialize_package_button.hide()

        self.details_stack.setCurrentWidget(
            self.recovery_page
        )

    def _show_complete_package(
            self,
            package_id: str,
            package_path: Path,
    ) -> None:
        self._clear_selected_package_presentation()
        self.work_item_panel.set_work_item(
            package_id,
            package_documents_path(
                package_path
            ),
            package_contents_path(
                package_path
            ),
        )
        self.details_stack.setCurrentWidget(
            self.work_item_panel
        )

    @staticmethod
    def _set_label_role(
            label: QLabel,
            role: str,
    ) -> None:
        if label.property(
                "role"
        ) == role:
            return

        label.setProperty(
            "role",
            role,
        )
        style = label.style()
        style.unpolish(
            label
        )
        style.polish(
            label
        )
        label.update()

    def _work_item_import_requested(
            self,
            source_path: str,
            _contents_path: str,
    ) -> None:
        feature_name = self.feature_name
        package_id = self.current_package_id

        if (
                not feature_name
                or not package_id
        ):
            return

        self.implementation_package_import_requested.emit(
            source_path,
            feature_name,
            package_id,
        )

    def _work_item_extraction_requested(
            self,
            _contents_path: str,
    ) -> None:
        feature_name = self.feature_name
        package_id = self.current_package_id

        if (
                not feature_name
                or not package_id
        ):
            return

        self.extract_implementation_package_requested.emit(
            feature_name,
            package_id,
        )

    def _work_item_inspection_requested(
            self,
            _contents_path: str,
    ) -> None:
        feature_name = self.feature_name
        package_id = self.current_package_id

        if (
                not feature_name
                or not package_id
        ):
            return

        self.inspect_implementation_package_requested.emit(
            feature_name,
            package_id,
        )

    def _work_item_installation_requested(
            self,
            _contents_path: str,
    ) -> None:
        feature_name = self.feature_name
        package_id = self.current_package_id

        if (
                not feature_name
                or not package_id
        ):
            return

        self.install_implementation_package_requested.emit(
            feature_name,
            package_id,
        )

    def _request_add_package(
            self,
    ) -> None:
        feature_name = self.feature_name

        if not feature_name:
            return

        self.add_package_requested.emit(
            feature_name
        )

    def _request_package_initialization(
            self,
    ) -> None:
        feature_name = self.feature_name
        package_id = self.current_package_id

        if (
                not feature_name
                or not package_id
        ):
            return

        self.initialize_package_requested.emit(
            feature_name,
            package_id,
        )

    def _package_drop_requested(
            self,
            source_path: str,
            package_id: str,
    ) -> None:
        feature_name = self.feature_name

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

        feature_name = self.feature_name
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

        package_id = str(
            package_id
        )
        package_path = Path(
            str(
                path_text
            )
        )

        self.package_list.setCurrentItem(
            item
        )

        menu = QMenu(
            self
        )
        initialize_package_action = None

        if state == _STATE_INCOMPLETE:
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

        if selected is initialize_package_action:
            self.initialize_package_requested.emit(
                feature_name,
                package_id,
            )

        elif selected is copy_path_action:
            QApplication.clipboard().setText(
                str(
                    package_path
                )
            )

        elif selected is open_location_action:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(
                        package_path
                    )
                )
            )

    def _package_structure_state(
            self,
            package_id: str,
    ) -> tuple[str, str | None]:
        workspace = self.workspace_path
        feature_name = self.feature_name

        if (
                workspace is None
                or not feature_name
        ):
            return (
                _STATE_ERROR,
                "No Feature workspace is active.",
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

    def _item_for_package_id(
            self,
            package_id: str,
    ) -> QListWidgetItem | None:
        for index in range(
            self.package_list.count()
        ):
            item = self.package_list.item(
                index
            )

            if (
                    item.data(
                        _PACKAGE_ID_ROLE
                    )
                    == package_id
            ):
                return item

        return None

    def _clear_selected_package_presentation(
            self,
    ) -> None:
        self.work_item_panel.clear_work_item()
        self.recovery_title_label.clear()
        self.recovery_status_label.clear()
        self._set_label_role(
            self.recovery_status_label,
            "secondary",
        )
        self.initialize_package_button.hide()

    def _show_no_selection(
            self,
            message: str | None = None,
            *,
            title: str = "No Package Selected",
    ) -> None:
        self._clear_selected_package_presentation()
        self.no_selection_title_label.setText(
            title
        )
        self.no_selection_label.setText(
            message
            or (
                "Select a Package to view its documents and "
                "implementation package information."
            )
        )
        self.details_stack.setCurrentWidget(
            self.no_selection_page
        )

    def _show_status(
            self,
            text: str,
    ) -> None:
        self.status_label.setText(
            text
        )
        self.status_label.show()

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

    def _update_enabled_state(
            self,
    ) -> None:
        self.add_package_button.setEnabled(
            (
                self.workspace_path is not None
                and bool(
                    self.feature_name
                )
            )
        )
