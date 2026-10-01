from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
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
    patch_contents_path,
    patch_documents_path,
)


_ITEM_PATH_ROLE = int(
    Qt.ItemDataRole.UserRole
)
_PATCH_ID_ROLE = (
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


class PatchWorkspacePanel(SectionPanel):
    file_open_requested = Signal(str)
    new_document_requested = Signal(str)
    add_patch_requested = Signal()
    initialize_patch_requested = Signal(str)
    implementation_package_import_requested = Signal(
        str,
        str,
    )
    extract_implementation_package_requested = Signal(str)
    inspect_implementation_package_requested = Signal(str)
    install_implementation_package_requested = Signal(str)

    def __init__(
            self,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "PATCHES",
            parent,
        )

        self.context_key: object | None = None
        self.owner_label = "owner"
        self.current_patch_id: str | None = None
        self._discover_patches: (
            Callable[
                [],
                tuple[Path, ...],
            ]
            | None
        ) = None
        self._is_patch_structure_initialized: (
            Callable[
                [str],
                bool,
            ]
            | None
        ) = None

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

        self.patch_list = QListWidget(
            self
        )
        self.patch_list.currentItemChanged.connect(
            self._patch_selection_changed
        )

        self.add_patch_button = QPushButton(
            "Add",
            self,
        )
        self.add_patch_button.setProperty(
            "role",
            "toolbar",
        )
        self.add_patch_button.setIcon(
            load_icon(
                "add-rounded.svg"
            )
        )
        self.add_patch_button.clicked.connect(
            self._request_add_patch
        )
        self.add_header_widget(
            self.add_patch_button
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
            self.patch_list
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
            "No Patch Selected",
            page,
        )
        self.no_selection_title_label.setProperty(
            "role",
            "pageTitle",
        )

        self.no_selection_label = QLabel(
            (
                "Select a Patch to view its documents and "
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

        self.initialize_patch_button = QPushButton(
            "Initialize Patch Structure...",
            page,
        )
        self.initialize_patch_button.clicked.connect(
            self._request_patch_initialization
        )
        self.initialize_patch_button.hide()

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
            self.initialize_patch_button
        )
        layout.addStretch(
            1
        )

        return page

    def set_context(
            self,
            context_key: object,
            *,
            owner_label: str,
            discover_patches: Callable[
                [],
                tuple[Path, ...],
            ],
            is_patch_structure_initialized: Callable[
                [str],
                bool,
            ],
    ) -> None:
        if context_key != self.context_key:
            self.current_patch_id = None

        self.context_key = context_key
        self.owner_label = owner_label
        self._discover_patches = discover_patches
        self._is_patch_structure_initialized = (
            is_patch_structure_initialized
        )

        self.refresh()

    def clear_context(
            self,
    ) -> None:
        self.context_key = None
        self.owner_label = "owner"
        self.current_patch_id = None
        self._discover_patches = None
        self._is_patch_structure_initialized = None
        self.refresh()

    def refresh(self) -> None:
        self.status_label.clear()
        self.status_label.hide()

        discover_patches = self._discover_patches

        if (
                self.context_key is None
                or discover_patches is None
        ):
            self.current_patch_id = None
            self.patch_list.blockSignals(
                True
            )
            self.patch_list.clear()
            self.patch_list.blockSignals(
                False
            )
            self._show_no_selection()
            self._update_enabled_state()
            return

        selected_patch_id = self.current_patch_id

        try:
            patches = discover_patches()
        except OSError as error:
            self.current_patch_id = None
            self.patch_list.blockSignals(
                True
            )
            self.patch_list.clear()
            self.patch_list.blockSignals(
                False
            )
            self._show_status(
                f"Unable to discover Patches: {error}"
            )
            self._show_no_selection(
                (
                    "Patch details are unavailable while "
                    "Patches cannot be discovered."
                ),
                title="Patches Unavailable",
            )
            self._update_enabled_state()
            return

        self.patch_list.blockSignals(
            True
        )
        self.patch_list.clear()

        selected_item = None

        for patch_path in patches:
            patch_id = patch_path.name
            state, error_text = self._patch_structure_state(
                patch_id
            )

            item = QListWidgetItem(
                self._structured_item_text(
                    patch_id,
                    state,
                )
            )
            item.setData(
                _ITEM_PATH_ROLE,
                str(
                    patch_path
                ),
            )
            item.setData(
                _PATCH_ID_ROLE,
                patch_id,
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
                    "Patch structure is incomplete."
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

            self.patch_list.addItem(
                item
            )

            if patch_id == selected_patch_id:
                selected_item = item

        if not patches:
            self.current_patch_id = None
            self.patch_list.clearSelection()
            self.patch_list.blockSignals(
                False
            )
            self._show_status(
                (
                    "No Patches. Add a Patch to organize "
                    "corrective implementation work for this "
                    f"{self.owner_label}."
                )
            )
            self._show_no_selection(
                (
                    "Create a Patch to begin organizing "
                    "corrective implementation work for this "
                    f"{self.owner_label}."
                ),
                title="No Patches",
            )
            self._update_enabled_state()
            return

        if selected_item is not None:
            self.patch_list.setCurrentItem(
                selected_item
            )
        else:
            self.current_patch_id = None
            self.patch_list.clearSelection()

        self.patch_list.blockSignals(
            False
        )

        self._refresh_selected_patch()
        self._update_enabled_state()

    def _patch_selection_changed(
            self,
            current: QListWidgetItem | None,
            _previous: QListWidgetItem | None,
    ) -> None:
        self.current_patch_id = (
            str(
                current.data(
                    _PATCH_ID_ROLE
                )
            )
            if (
                current is not None
                and current.data(
                    _PATCH_ID_ROLE
                )
            )
            else None
        )

        self._refresh_selected_patch()

    def _refresh_selected_patch(
            self,
    ) -> None:
        patch_id = self.current_patch_id

        if patch_id is None:
            self._show_no_selection()
            return

        item = self._item_for_patch_id(
            patch_id
        )

        if item is None:
            self.current_patch_id = None
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
            self.current_patch_id = None
            self._show_no_selection()
            return

        selected_path = Path(
            str(
                path_text
            )
        )

        if state == _STATE_COMPLETE:
            self._show_complete_patch(
                patch_id,
                selected_path,
            )
            return

        self._clear_selected_patch_presentation()
        self.recovery_title_label.setText(
            patch_id
        )

        if state == _STATE_INCOMPLETE:
            self._set_label_role(
                self.recovery_status_label,
                "warning",
            )
            self.recovery_status_label.setText(
                "Patch structure incomplete."
            )
            self.initialize_patch_button.show()
        else:
            self._set_label_role(
                self.recovery_status_label,
                "error",
            )
            self.recovery_status_label.setText(
                (
                    "Unable to inspect Patch structure."
                    + (
                        f"\n\n{error_text}"
                        if error_text
                        else ""
                    )
                )
            )
            self.initialize_patch_button.hide()

        self.details_stack.setCurrentWidget(
            self.recovery_page
        )

    def _show_complete_patch(
            self,
            patch_id: str,
            selected_path: Path,
    ) -> None:
        self._clear_selected_patch_presentation()
        self.work_item_panel.set_work_item(
            patch_id,
            patch_documents_path(
                selected_path
            ),
            patch_contents_path(
                selected_path
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
        patch_id = self.current_patch_id

        if not patch_id:
            return

        self.implementation_package_import_requested.emit(
            source_path,
            patch_id,
        )

    def _work_item_extraction_requested(
            self,
            _contents_path: str,
    ) -> None:
        patch_id = self.current_patch_id

        if not patch_id:
            return

        self.extract_implementation_package_requested.emit(
            patch_id
        )

    def _work_item_inspection_requested(
            self,
            _contents_path: str,
    ) -> None:
        patch_id = self.current_patch_id

        if not patch_id:
            return

        self.inspect_implementation_package_requested.emit(
            patch_id
        )

    def _work_item_installation_requested(
            self,
            _contents_path: str,
    ) -> None:
        patch_id = self.current_patch_id

        if not patch_id:
            return

        self.install_implementation_package_requested.emit(
            patch_id
        )

    def _request_add_patch(
            self,
    ) -> None:
        if self.context_key is None:
            return

        self.add_patch_requested.emit()

    def _request_patch_initialization(
            self,
    ) -> None:
        patch_id = self.current_patch_id

        if not patch_id:
            return

        self.initialize_patch_requested.emit(
            patch_id
        )

    def _patch_structure_state(
            self,
            patch_id: str,
    ) -> tuple[str, str | None]:
        readiness = self._is_patch_structure_initialized

        if (
                self.context_key is None
                or readiness is None
        ):
            return (
                _STATE_ERROR,
                "No Patch owner context is active.",
            )

        try:
            initialized = readiness(
                patch_id
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

    def _item_for_patch_id(
            self,
            patch_id: str,
    ) -> QListWidgetItem | None:
        for index in range(
            self.patch_list.count()
        ):
            item = self.patch_list.item(
                index
            )

            if (
                    item.data(
                        _PATCH_ID_ROLE
                    )
                    == patch_id
            ):
                return item

        return None

    def _clear_selected_patch_presentation(
            self,
    ) -> None:
        self.work_item_panel.clear_work_item()
        self.recovery_title_label.clear()
        self.recovery_status_label.clear()
        self._set_label_role(
            self.recovery_status_label,
            "secondary",
        )
        self.initialize_patch_button.hide()

    def _show_no_selection(
            self,
            message: str | None = None,
            *,
            title: str = "No Patch Selected",
    ) -> None:
        self._clear_selected_patch_presentation()
        self.no_selection_title_label.setText(
            title
        )
        self.no_selection_label.setText(
            message
            or (
                "Select a Patch to view its documents and "
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
        self.add_patch_button.setEnabled(
            self.context_key is not None
        )
