from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ai_project_organizer.implementation_package import (
    discover_extracted_implementation_packages,
    discover_implementation_package_archives,
)
from ai_project_organizer.ui.document_list_panel import (
    DocumentListPanel,
)
from ai_project_organizer.ui.resources import (
    load_icon,
)
from ai_project_organizer.ui.section_panel import (
    SectionPanel,
)


class ImplementationWorkItemPanel(QWidget):
    file_open_requested = Signal(str)
    new_document_requested = Signal(str)
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
            parent
        )

        self.display_name: str | None = None
        self.documents_path: Path | None = None
        self.contents_path: Path | None = None

        self.title_label = QLabel(
            self
        )
        self.title_label.setProperty(
            "role",
            "pageTitle",
        )

        self.documents_panel = DocumentListPanel(
            self
        )
        self.documents_panel.file_open_requested.connect(
            self.file_open_requested.emit
        )
        self.documents_panel.new_document_requested.connect(
            self.new_document_requested.emit
        )

        self.artifact_panel = SectionPanel(
            "IMPLEMENTATION PACKAGE",
            self,
        )

        self.archive_metadata_label = QLabel(
            "ZIP",
            self.artifact_panel,
        )
        self.archive_metadata_label.setProperty(
            "role",
            "metadataLabel",
        )

        self.archive_status_label = QLabel(
            self.artifact_panel
        )
        self.archive_status_label.setWordWrap(
            True
        )

        self.extracted_metadata_label = QLabel(
            "Extracted",
            self.artifact_panel,
        )
        self.extracted_metadata_label.setProperty(
            "role",
            "metadataLabel",
        )

        self.extracted_status_label = QLabel(
            self.artifact_panel
        )
        self.extracted_status_label.setWordWrap(
            True
        )

        metadata_layout = QGridLayout()
        metadata_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        metadata_layout.setHorizontalSpacing(
            12
        )
        metadata_layout.setVerticalSpacing(
            4
        )
        metadata_layout.addWidget(
            self.archive_metadata_label,
            0,
            0,
        )
        metadata_layout.addWidget(
            self.archive_status_label,
            0,
            1,
        )
        metadata_layout.addWidget(
            self.extracted_metadata_label,
            1,
            0,
        )
        metadata_layout.addWidget(
            self.extracted_status_label,
            1,
            1,
        )
        metadata_layout.setColumnStretch(
            1,
            1,
        )

        self.artifact_error_label = QLabel(
            self.artifact_panel
        )
        self.artifact_error_label.setWordWrap(
            True
        )
        self.artifact_error_label.setProperty(
            "role",
            "error",
        )
        self.artifact_error_label.hide()

        self.import_package_button = QPushButton(
            "Import ZIP",
            self.artifact_panel,
        )
        self.import_package_button.setIcon(
            load_icon(
                "import.svg"
            )
        )
        self.import_package_button.clicked.connect(
            self._request_import
        )

        self.extract_package_button = QPushButton(
            "Extract",
            self.artifact_panel,
        )
        self.extract_package_button.clicked.connect(
            self._request_extraction
        )

        self.inspect_package_button = QPushButton(
            "Inspect",
            self.artifact_panel,
        )
        self.inspect_package_button.setIcon(
            load_icon(
                "inspect.svg"
            )
        )
        self.inspect_package_button.clicked.connect(
            self._request_inspection
        )

        self.install_package_button = QPushButton(
            "Install",
            self.artifact_panel,
        )
        self.install_package_button.setIcon(
            load_icon(
                "install-line.svg"
            )
        )
        self.install_package_button.clicked.connect(
            self._request_installation
        )

        self.open_contents_button = QPushButton(
            "Open Contents",
            self.artifact_panel,
        )
        self.open_contents_button.setProperty(
            "role",
            "toolbar",
        )
        self.open_contents_button.setIcon(
            load_icon(
                "folder.svg"
            )
        )
        self.open_contents_button.clicked.connect(
            self._open_contents
        )

        primary_actions = QGridLayout()
        primary_actions.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        primary_actions.setHorizontalSpacing(
            4
        )
        primary_actions.setVerticalSpacing(
            4
        )
        primary_actions.addWidget(
            self.import_package_button,
            0,
            0,
        )
        primary_actions.addWidget(
            self.extract_package_button,
            0,
            1,
        )
        primary_actions.addWidget(
            self.inspect_package_button,
            1,
            0,
        )
        primary_actions.addWidget(
            self.install_package_button,
            1,
            1,
        )
        primary_actions.setColumnStretch(
            0,
            1,
        )
        primary_actions.setColumnStretch(
            1,
            1,
        )

        secondary_actions = QHBoxLayout()
        secondary_actions.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        secondary_actions.addWidget(
            self.open_contents_button
        )
        secondary_actions.addStretch(
            1
        )

        self.artifact_panel.content_layout.addLayout(
            metadata_layout
        )
        self.artifact_panel.content_layout.addWidget(
            self.artifact_error_label
        )
        self.artifact_panel.content_layout.addLayout(
            primary_actions
        )
        self.artifact_panel.content_layout.addLayout(
            secondary_actions
        )

        layout = QVBoxLayout(
            self
        )
        layout.setContentsMargins(
            8,
            4,
            8,
            8,
        )
        layout.setSpacing(
            10
        )
        layout.addWidget(
            self.title_label
        )
        layout.addWidget(
            self.documents_panel,
            1,
        )
        layout.addWidget(
            self.artifact_panel
        )

        self.clear_work_item()

    def set_work_item(
            self,
            display_name: str,
            documents_path: str | Path,
            contents_path: str | Path,
    ) -> None:
        self.display_name = display_name
        self.documents_path = Path(
            documents_path
        ).expanduser()
        self.contents_path = Path(
            contents_path
        ).expanduser()

        self.title_label.setText(
            display_name
        )
        self.documents_panel.set_directory(
            self.documents_path
        )
        self.refresh()

    def clear_work_item(
            self,
    ) -> None:
        self.display_name = None
        self.documents_path = None
        self.contents_path = None
        self.title_label.clear()
        self.documents_panel.set_directory(
            None
        )
        self.archive_status_label.clear()
        self.extracted_status_label.clear()
        self._set_artifact_metadata_visible(
            False
        )
        self.artifact_error_label.clear()
        self.artifact_error_label.hide()
        self._set_artifact_action_state(
            can_import=False,
            can_extract=False,
            can_inspect=False,
            can_install=False,
            can_open_contents=False,
        )

    def refresh(
            self,
    ) -> None:
        contents_path = self.contents_path

        if contents_path is None:
            self.archive_status_label.clear()
            self.extracted_status_label.clear()
            self._set_artifact_metadata_visible(
                False
            )
            self.artifact_error_label.clear()
            self.artifact_error_label.hide()
            self._set_artifact_action_state(
                can_import=False,
                can_extract=False,
                can_inspect=False,
                can_install=False,
                can_open_contents=False,
            )
            return

        contents_available = (
            not contents_path.is_symlink()
            and contents_path.exists()
            and contents_path.is_dir()
        )

        self.archive_status_label.clear()
        self.extracted_status_label.clear()
        self.artifact_error_label.clear()
        self.artifact_error_label.hide()
        self._set_artifact_metadata_visible(
            True
        )

        self._set_artifact_action_state(
            can_import=True,
            can_extract=False,
            can_inspect=False,
            can_install=False,
            can_open_contents=contents_available,
        )

        try:
            archives = discover_implementation_package_archives(
                contents_path
            )
            extracted_packages = (
                discover_extracted_implementation_packages(
                    contents_path
                )
            )
        except OSError as error:
            self.archive_status_label.clear()
            self.extracted_status_label.clear()
            self._set_artifact_metadata_visible(
                False
            )
            self.artifact_error_label.setText(
                (
                    "Unable to inspect Contents:"
                    f"\n{error}"
                )
            )
            self.artifact_error_label.show()
            return

        if not archives:
            archive_text = "None"
        elif len(archives) == 1:
            archive_text = archives[0].source_path.name
        else:
            archive_text = (
                f"{len(archives)} archives"
            )

        if not extracted_packages:
            extracted_text = "None"
        elif len(extracted_packages) == 1:
            extracted_text = extracted_packages[0].root_path.name
        else:
            extracted_text = (
                f"{len(extracted_packages)} packages"
            )

        self.archive_status_label.setText(
            archive_text
        )
        self.extracted_status_label.setText(
            extracted_text
        )
        self._set_artifact_action_state(
            can_import=True,
            can_extract=bool(
                archives
            ),
            can_inspect=bool(
                extracted_packages
            ),
            can_install=bool(
                extracted_packages
            ),
            can_open_contents=contents_available,
        )

    def _set_artifact_metadata_visible(
            self,
            visible: bool,
    ) -> None:
        for label in (
                self.archive_metadata_label,
                self.archive_status_label,
                self.extracted_metadata_label,
                self.extracted_status_label,
        ):
            label.setVisible(
                visible
            )

    def _set_artifact_action_state(
            self,
            *,
            can_import: bool,
            can_extract: bool,
            can_inspect: bool,
            can_install: bool,
            can_open_contents: bool,
    ) -> None:
        self.import_package_button.setEnabled(
            can_import
        )
        self.extract_package_button.setEnabled(
            can_extract
        )
        self.inspect_package_button.setEnabled(
            can_inspect
        )
        self.install_package_button.setEnabled(
            can_install
        )
        self.open_contents_button.setEnabled(
            can_open_contents
        )

    def _request_import(
            self,
    ) -> None:
        contents_path = self.contents_path

        if contents_path is None:
            return

        selected_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Import Implementation Package",
            "",
            "ZIP Archives (*.zip)",
        )

        if not selected_path:
            return

        self.implementation_package_import_requested.emit(
            selected_path,
            str(
                contents_path
            ),
        )

    def _request_extraction(
            self,
    ) -> None:
        if self.contents_path is None:
            return

        self.extract_implementation_package_requested.emit(
            str(
                self.contents_path
            )
        )

    def _request_inspection(
            self,
    ) -> None:
        if self.contents_path is None:
            return

        self.inspect_implementation_package_requested.emit(
            str(
                self.contents_path
            )
        )

    def _request_installation(
            self,
    ) -> None:
        if self.contents_path is None:
            return

        self.install_implementation_package_requested.emit(
            str(
                self.contents_path
            )
        )

    def _open_contents(
            self,
    ) -> None:
        contents_path = self.contents_path

        if contents_path is None:
            return

        if (
                contents_path.is_symlink()
                or not contents_path.exists()
                or not contents_path.is_dir()
        ):
            self._show_artifact_error(
                "Contents is no longer available."
            )
            self.open_contents_button.setEnabled(
                False
            )
            return

        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(
                    contents_path
                )
            )
        )

        if not opened:
            self._show_artifact_error(
                "Unable to open Contents."
            )

    def _show_artifact_error(
            self,
            text: str,
    ) -> None:
        self.artifact_error_label.setText(
            text
        )
        self.artifact_error_label.show()
