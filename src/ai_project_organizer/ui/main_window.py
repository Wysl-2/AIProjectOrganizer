import shutil
from pathlib import Path

from PySide6.QtCore import QDir, QModelIndex, QStandardPaths, Qt, QUrl
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDesktopServices,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFileSystemModel,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
)

from ai_project_organizer.implementation_package import (
    ExtractedImplementationPackage,
    ImplementationPackageError,
    copy_implementation_package_archive,
    discover_extracted_implementation_packages,
    discover_implementation_package_archives,
    extract_implementation_package_archive,
    inspect_extracted_implementation_package,
    inspect_implementation_package_archive,
    parse_implementation_package_readme,
)
from ai_project_organizer.project import (
    PROJECT_METADATA_FILENAME,
    ProjectMetadata,
    ProjectMetadataError,
    create_project_workspace,
    load_project_metadata,
    save_project_metadata,
)
from ai_project_organizer.project_registry import (
    ProjectRegistry,
    ProjectRegistryError,
    load_project_registry,
    save_project_registry,
)
from ai_project_organizer.ui.add_package_dialog import (
    AddPackageDialog,
)
from ai_project_organizer.ui.file_tree import FileTreeView
from ai_project_organizer.ui.new_project_dialog import NewProjectDialog
from ai_project_organizer.ui.package_inspector_dialog import (
    PackageInspectorDialog,
)
from ai_project_organizer.ui.package_install_dialog import (
    PackageInstallDialog,
)
from ai_project_organizer.ui.project_settings_dialog import (
    ProjectSettingsDialog,
)
from ai_project_organizer.ui.project_view import ProjectView
from ai_project_organizer.ui.text_editor import TextEditor
from ai_project_organizer.ui.welcome_page import (
    ProjectBrowserEntry,
    WelcomePage,
)
from ai_project_organizer.workspace_paths import (
    filesystem_entry_exists,
    is_workspace_entry,
    is_workspace_target,
    same_path_entry,
)
from ai_project_organizer.workspace_structure import (
    create_project_feature,
    create_project_package,
    discover_project_features,
    initialize_project_feature_structure,
    initialize_project_package_structure,
    initialize_project_workspace_structure,
    is_project_feature_structure_initialized,
    is_project_package_structure_initialized,
    is_project_workspace_structure_initialized,
    package_contents_path,
    project_package_path,
)


class MainWindow(QMainWindow):
    def __init__(
            self,
            project_registry_path: str | Path | None = None,
    ) -> None:
        super().__init__()

        self.setWindowTitle("AI Project Organizer")
        self.resize(1000, 700)

        self.workspace_path: str | None = None
        self.current_file_path: str | None = None
        self.project_metadata: ProjectMetadata | None = None
        self.project_metadata_load_error: str | None = None

        self.project_registry_path = project_registry_path
        self.project_registry = ProjectRegistry()
        self.project_registry_load_error: str | None = None

        self._setup_ui()
        self._setup_menu()
        self._load_project_registry_state()
        self._update_action_states()

    def _setup_ui(self) -> None:
        self.central_stack = QStackedWidget()

        self.welcome_page = WelcomePage()
        self.welcome_page.create_project_requested.connect(
            self._create_project
        )
        self.welcome_page.open_existing_requested.connect(
            self._open_workspace
        )
        self.welcome_page.project_open_requested.connect(
            self._open_registered_project
        )
        self.welcome_page.project_remove_requested.connect(
            self._remove_registered_project
        )

        self.file_model = QFileSystemModel(self)
        self.file_model.setReadOnly(True)

        self.file_tree = FileTreeView()
        self.file_tree.setModel(self.file_model)

        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)

        self.file_tree.doubleClicked.connect(
            self._open_file_from_tree
        )

        self.file_tree.new_file_requested.connect(
            self._create_new_file
        )

        self.file_tree.new_folder_requested.connect(
            self._create_new_folder
        )

        self.file_tree.rename_requested.connect(
            self._rename_item
        )

        self.file_tree.delete_requested.connect(
            self._delete_item
        )

        self.file_tree.paths_moved.connect(
            self._handle_paths_moved
        )

        self.file_tree.move_failed.connect(
            self._show_move_error
        )

        self.file_tree.import_failed.connect(
            self._show_import_error
        )

        self.project_view = ProjectView()
        self.project_view.file_open_requested.connect(
            self._open_file_path
        )
        self.project_view.new_document_requested.connect(
            self._create_new_file
        )
        self.project_view.add_feature_requested.connect(
            self._add_feature
        )
        self.project_view.add_package_requested.connect(
            self._add_package
        )
        self.project_view.initialize_project_requested.connect(
            self._initialize_project_structure_from_view
        )
        self.project_view.initialize_feature_requested.connect(
            self._initialize_feature_structure_from_view
        )
        self.project_view.initialize_package_requested.connect(
            self._initialize_package_structure_from_view
        )
        self.project_view.implementation_package_import_requested.connect(
            self._import_implementation_package
        )
        self.project_view.extract_implementation_package_requested.connect(
            self._extract_implementation_package
        )
        self.project_view.inspect_implementation_package_requested.connect(
            self._inspect_implementation_package
        )
        self.project_view.install_implementation_package_requested.connect(
            self._install_implementation_package
        )

        self.workspace_navigation_tabs = QTabWidget()
        self.workspace_navigation_tabs.setProperty(
            "role",
            "workspaceNavigation",
        )
        self.workspace_navigation_tabs.addTab(
            self.project_view,
            "Project",
        )
        self.workspace_navigation_tabs.addTab(
            self.file_tree,
            "Files",
        )
        self.workspace_navigation_tabs.currentChanged.connect(
            self._workspace_navigation_changed
        )

        self.text_editor = TextEditor()

        self.text_editor.document().modificationChanged.connect(
            self._update_window_title
        )

        self.workspace_page = QSplitter(
            Qt.Orientation.Horizontal
        )
        self.workspace_page.addWidget(
            self.workspace_navigation_tabs
        )
        self.workspace_page.addWidget(
            self.text_editor
        )
        self.workspace_page.setSizes(
            [300, 700]
        )

        self.central_stack.addWidget(
            self.welcome_page
        )
        self.central_stack.addWidget(
            self.workspace_page
        )
        self.central_stack.setCurrentWidget(
            self.welcome_page
        )

        self.setCentralWidget(
            self.central_stack
        )

    def _setup_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self.new_file_action = QAction(
            "New File...",
            self,
        )
        self.new_file_action.setShortcut(
            QKeySequence.StandardKey.New
        )
        self.new_file_action.triggered.connect(
            lambda: self._create_new_file()
        )

        self.new_folder_action = QAction(
            "New Folder...",
            self,
        )
        self.new_folder_action.setShortcut(
            "Ctrl+Shift+N"
        )
        self.new_folder_action.triggered.connect(
            lambda: self._create_new_folder()
        )

        self.open_workspace_action = QAction(
            "Open Workspace Folder...",
            self,
        )
        self.open_workspace_action.setShortcut(
            "Ctrl+O"
        )
        self.open_workspace_action.triggered.connect(
            self._open_workspace
        )

        self.save_action = QAction(
            "Save",
            self,
        )
        self.save_action.setShortcut(
            QKeySequence.StandardKey.Save
        )
        self.save_action.triggered.connect(
            self._save_current_file
        )

        file_menu.addAction(
            self.new_file_action
        )
        file_menu.addAction(
            self.new_folder_action
        )
        file_menu.addSeparator()
        file_menu.addAction(
            self.open_workspace_action
        )
        file_menu.addSeparator()
        file_menu.addAction(
            self.save_action
        )

        project_menu = self.menuBar().addMenu(
            "&Project"
        )

        self.new_project_action = QAction(
            "New Project...",
            self,
        )
        self.new_project_action.triggered.connect(
            self._create_project
        )

        self.add_feature_action = QAction(
            "Add Feature...",
            self,
        )
        self.add_feature_action.triggered.connect(
            self._add_feature
        )

        self.add_package_action = QAction(
            "Add Package...",
            self,
        )
        self.add_package_action.triggered.connect(
            self._add_package
        )

        self.configure_project_action = QAction(
            "Configure Project...",
            self,
        )
        self.configure_project_action.triggered.connect(
            self._configure_project
        )

        self.close_project_action = QAction(
            "Close Project",
            self,
        )
        self.close_project_action.triggered.connect(
            self._close_project
        )

        project_menu.addAction(
            self.new_project_action
        )
        project_menu.addSeparator()
        project_menu.addAction(
            self.add_feature_action
        )
        project_menu.addAction(
            self.add_package_action
        )
        project_menu.addSeparator()
        project_menu.addAction(
            self.configure_project_action
        )
        project_menu.addAction(
            self.close_project_action
        )

    def _load_project_registry_state(self) -> None:
        try:
            self.project_registry = load_project_registry(
                self.project_registry_path
            )
        except (ProjectRegistryError, OSError) as error:
            self.project_registry = ProjectRegistry()
            self.project_registry_load_error = str(error)

            QMessageBox.warning(
                self,
                "Unable to Load Project Registry",
                (
                    "The Project Registry could not be loaded. "
                    "AI Project Organizer can still be used, but "
                    "previously known Projects cannot currently be "
                    "displayed or updated."
                    f"\n\n{error}"
                ),
            )
        else:
            self.project_registry_load_error = None

        self._refresh_welcome_projects()

    def _refresh_welcome_projects(self) -> None:
        entries: list[ProjectBrowserEntry] = []

        for registered_project in self.project_registry.projects:
            workspace_path = registered_project.workspace_path
            available = workspace_path.is_dir()
            display_name = (
                workspace_path.name
                or str(workspace_path)
            )

            if available:
                try:
                    metadata = load_project_metadata(
                        workspace_path
                    )
                except (ProjectMetadataError, OSError):
                    metadata = None

                if metadata is not None:
                    display_name = metadata.name

            entries.append(
                ProjectBrowserEntry(
                    display_name=display_name,
                    workspace_path=workspace_path,
                    available=available,
                )
            )

        self.welcome_page.set_projects(
            entries
        )

    def _open_workspace(self) -> None:
        if not self._confirm_discard_unsaved_changes():
            return

        start_path = (
                self.workspace_path
                or QDir.homePath()
        )

        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Open Workspace Folder",
            start_path,
        )

        if not selected_path:
            return

        self._activate_workspace(
            selected_path
        )

    def _open_registered_project(
            self,
            path: str,
    ) -> None:
        if not self._activate_workspace(path):
            self._refresh_welcome_projects()

    def _create_project(self) -> None:
        dialog = NewProjectDialog(
            parent=self,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            metadata = dialog.project_metadata()
            workspace_path = dialog.workspace_path()
        except (ProjectMetadataError, OSError, ValueError) as error:
            QMessageBox.warning(
                self,
                "Invalid Project Configuration",
                str(error),
            )
            return

        if not self._confirm_discard_unsaved_changes():
            return

        try:
            created_workspace = create_project_workspace(
                workspace_path,
                metadata,
            )
        except (ProjectMetadataError, OSError) as error:
            message = (
                "Could not create the Project:"
                f"\n\n{error}"
            )

            if workspace_path.exists() or workspace_path.is_symlink():
                message += (
                    "\n\nThe intended workspace path now exists. "
                    "Review it before trying again."
                )

            QMessageBox.critical(
                self,
                "Unable to Create Project",
                message,
            )
            return

        self._activate_workspace(
            created_workspace
        )

    def _add_feature(self) -> None:
        if self.workspace_path is None:
            return

        if not self._ensure_project_workspace_structure():
            return

        feature_name, accepted = QInputDialog.getText(
            self,
            "Add Feature",
            "Feature name:",
        )

        if not accepted:
            return

        try:
            create_project_feature(
                self.workspace_path,
                feature_name,
            )
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Invalid Feature Name",
                str(error),
            )
        except FileExistsError as error:
            QMessageBox.warning(
                self,
                "Feature Already Exists",
                str(error),
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Add Feature",
                (
                    "Could not create the Feature:"
                    f"\n\n{error}"
                ),
            )
            return

        self.project_view.refresh()

    def _add_package(
            self,
            selected_feature_name: str = "",
    ) -> None:
        if self.workspace_path is None:
            return

        if not self._ensure_project_workspace_structure():
            return

        try:
            features = discover_project_features(
                self.workspace_path
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Add Package",
                (
                    "Could not discover Project Features:"
                    f"\n\n{error}"
                ),
            )
            return

        if not features:
            QMessageBox.information(
                self,
                "No Features Available",
                "Create a Feature before adding a Package.",
            )
            return

        available_feature_names = tuple(
            feature.name
            for feature in features
        )

        if (
                selected_feature_name
                and selected_feature_name not in available_feature_names
        ):
            QMessageBox.warning(
                self,
                "Feature Unavailable",
                (
                    "The selected Feature no longer exists. "
                    "Refresh the Project view and try again."
                ),
            )
            return

        dialog = AddPackageDialog(
            available_feature_names,
            selected_feature_name=(
                selected_feature_name
                if selected_feature_name
                else None
            ),
            parent=self,
        )

        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            feature_name = dialog.feature_name()
            package_id = dialog.package_id()

            if not self._ensure_project_feature_structure(
                    feature_name
            ):
                return

            try:
                create_project_package(
                    self.workspace_path,
                    feature_name,
                    package_id,
                )
            except ValueError as error:
                QMessageBox.warning(
                    self,
                    "Invalid Package ID",
                    str(error),
                )
                continue
            except FileExistsError as error:
                QMessageBox.warning(
                    self,
                    "Package Already Exists",
                    str(error),
                )
                continue
            except OSError as error:
                QMessageBox.warning(
                    self,
                    "Unable to Add Package",
                    (
                        "Could not create the Package:"
                        f"\n\n{error}"
                    ),
                )
                return

            self.project_view.refresh()
            return

    def _ensure_project_feature_structure(
            self,
            feature_name: str,
    ) -> bool:
        if self.workspace_path is None:
            return False

        try:
            initialized = (
                is_project_feature_structure_initialized(
                    self.workspace_path,
                    feature_name,
                )
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Initialize Feature Structure",
                (
                    "The Feature structure could not be "
                    f"validated.\n\n{error}"
                ),
            )
            return False

        if initialized:
            return True

        message_box = QMessageBox(self)
        message_box.setWindowTitle(
            "Initialize Feature Structure"
        )
        message_box.setIcon(
            QMessageBox.Icon.Question
        )
        message_box.setText(
            f'Initialize the Feature "{feature_name}"?'
        )
        message_box.setInformativeText(
            (
                "This Feature does not contain the standard "
                "Documents and Packages folders.\n\n"
                "Create the missing standard folders now? "
                "Existing files and folders will not be moved "
                "or deleted."
            )
        )
        message_box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        message_box.setDefaultButton(
            QMessageBox.StandardButton.No
        )

        if (
                message_box.exec()
                != QMessageBox.StandardButton.Yes
        ):
            return False

        try:
            initialize_project_feature_structure(
                self.workspace_path,
                feature_name,
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Initialize Feature Structure",
                (
                    "Could not create the standard Feature "
                    f"structure.\n\n{error}"
                ),
            )
            return False

        return True

    def _ensure_project_workspace_structure(
            self,
    ) -> bool:
        if self.workspace_path is None:
            return False

        try:
            initialized = (
                is_project_workspace_structure_initialized(
                    self.workspace_path
                )
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Initialize Project Structure",
                (
                    "The Project workspace structure could not "
                    f"be validated.\n\n{error}"
                ),
            )
            return False

        if initialized:
            return True

        message_box = QMessageBox(self)
        message_box.setWindowTitle(
            "Initialize Project Structure"
        )
        message_box.setIcon(
            QMessageBox.Icon.Question
        )
        message_box.setText(
            "Initialize the standard Project structure?"
        )
        message_box.setInformativeText(
            (
                "This workspace does not contain the standard "
                "Documents and Features folders.\n\n"
                "Create the missing standard folders now? "
                "Existing files and folders will not be moved "
                "or deleted."
            )
        )
        message_box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        message_box.setDefaultButton(
            QMessageBox.StandardButton.No
        )

        if (
                message_box.exec()
                != QMessageBox.StandardButton.Yes
        ):
            return False

        try:
            initialize_project_workspace_structure(
                self.workspace_path
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Initialize Project Structure",
                (
                    "Could not create the standard Project "
                    f"structure.\n\n{error}"
                ),
            )
            return False

        return True

    def _workspace_navigation_changed(
            self,
            _index: int,
    ) -> None:
        if (
                self.workspace_navigation_tabs.currentWidget()
                is self.project_view
        ):
            self.project_view.refresh()

    def _initialize_project_structure_from_view(
            self,
    ) -> None:
        if self._ensure_project_workspace_structure():
            self.project_view.refresh()

    def _initialize_feature_structure_from_view(
            self,
            feature_name: str,
    ) -> None:
        if self._ensure_project_feature_structure(
                feature_name
        ):
            self.project_view.refresh()

    def _ensure_project_package_structure(
            self,
            feature_name: str,
            package_id: str,
    ) -> bool:
        if self.workspace_path is None:
            return False

        try:
            initialized = (
                is_project_package_structure_initialized(
                    self.workspace_path,
                    feature_name,
                    package_id,
                )
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Initialize Package Structure",
                (
                    "The Package structure could not be "
                    f"validated.\n\n{error}"
                ),
            )
            return False

        if initialized:
            return True

        message_box = QMessageBox(self)
        message_box.setWindowTitle(
            "Initialize Package Structure"
        )
        message_box.setIcon(
            QMessageBox.Icon.Question
        )
        message_box.setText(
            f'Initialize the Package "{package_id}"?'
        )
        message_box.setInformativeText(
            (
                "Create the missing standard Documents and "
                "Contents folders? Existing files and folders "
                "will not be moved or deleted."
            )
        )
        message_box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        message_box.setDefaultButton(
            QMessageBox.StandardButton.No
        )

        if (
                message_box.exec()
                != QMessageBox.StandardButton.Yes
        ):
            return False

        try:
            initialize_project_package_structure(
                self.workspace_path,
                feature_name,
                package_id,
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Initialize Package Structure",
                (
                    "Could not create the standard Package "
                    f"structure.\n\n{error}"
                ),
            )
            return False

        return True

    def _initialize_package_structure_from_view(
            self,
            feature_name: str,
            package_id: str,
    ) -> None:
        if self._ensure_project_package_structure(
                feature_name,
                package_id,
        ):
            self.project_view.refresh()

    def _import_implementation_package(
            self,
            source_path: str,
            feature_name: str,
            package_id: str,
    ) -> None:
        if self.workspace_path is None:
            return

        try:
            inspection = inspect_implementation_package_archive(
                source_path
            )
        except ImplementationPackageError as error:
            QMessageBox.warning(
                self,
                "Invalid Implementation Package",
                str(error),
            )
            return
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Import Implementation Package",
                (
                    "Could not read the implementation package:"
                    f"\n\n{error}"
                ),
            )
            return

        if not self._ensure_project_feature_structure(
                feature_name
        ):
            return

        resolved_package_id = package_id

        if resolved_package_id:
            try:
                package_path = project_package_path(
                    self.workspace_path,
                    feature_name,
                    resolved_package_id,
                )
            except ValueError as error:
                QMessageBox.warning(
                    self,
                    "Invalid Package ID",
                    str(error),
                )
                return

            if (
                    package_path.is_symlink()
                    or not package_path.exists()
                    or not package_path.is_dir()
            ):
                QMessageBox.warning(
                    self,
                    "Package Unavailable",
                    (
                        "The selected Package no longer exists "
                        "as an available Package directory."
                    ),
                )
                return

            inferred_id = inspection.inferred_package_id

            if (
                    inferred_id is not None
                    and inferred_id != resolved_package_id
            ):
                message_box = QMessageBox(self)
                message_box.setWindowTitle(
                    "Package ID Does Not Match"
                )
                message_box.setIcon(
                    QMessageBox.Icon.Warning
                )
                message_box.setText(
                    (
                        "This archive appears to belong to "
                        f'Package "{inferred_id}", but it was '
                        f'dropped on Package "{resolved_package_id}".'
                    )
                )
                message_box.setInformativeText(
                    (
                        f"Import it into "
                        f'"{resolved_package_id}" anyway?'
                    )
                )
                message_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                )
                message_box.setDefaultButton(
                    QMessageBox.StandardButton.No
                )

                if (
                        message_box.exec()
                        != QMessageBox.StandardButton.Yes
                ):
                    return

            if not self._ensure_project_package_structure(
                    feature_name,
                    resolved_package_id,
            ):
                return

        else:
            inferred_package_id = inspection.inferred_package_id

            while True:
                candidate_package_id = inferred_package_id

                if candidate_package_id is None:
                    candidate_package_id, accepted = (
                        QInputDialog.getText(
                            self,
                            "Import Implementation Package",
                            "Package ID:",
                        )
                    )

                    if not accepted:
                        return

                try:
                    package_path = project_package_path(
                        self.workspace_path,
                        feature_name,
                        candidate_package_id,
                    )
                except ValueError as error:
                    QMessageBox.warning(
                        self,
                        "Invalid Package ID",
                        str(error),
                    )

                    if inferred_package_id is not None:
                        return

                    continue

                resolved_package_id = package_path.name
                break

            if package_path.is_symlink():
                QMessageBox.warning(
                    self,
                    "Package Location Unavailable",
                    (
                        "The selected Package location is occupied "
                        "by a symbolic link."
                    ),
                )
                return

            if package_path.exists():
                if not package_path.is_dir():
                    QMessageBox.warning(
                        self,
                        "Package Location Unavailable",
                        (
                            "The selected Package location is occupied "
                            "by a non-directory filesystem entry."
                        ),
                    )
                    return

                if not self._ensure_project_package_structure(
                        feature_name,
                        resolved_package_id,
                ):
                    return
            else:
                try:
                    package_path = create_project_package(
                        self.workspace_path,
                        feature_name,
                        resolved_package_id,
                    )
                except ValueError as error:
                    QMessageBox.warning(
                        self,
                        "Invalid Package ID",
                        str(error),
                    )
                    return
                except FileExistsError as error:
                    QMessageBox.warning(
                        self,
                        "Package Already Exists",
                        str(error),
                    )
                    return
                except OSError as error:
                    QMessageBox.warning(
                        self,
                        "Unable to Import Implementation Package",
                        (
                            "Could not create the Package workspace:"
                            f"\n\n{error}"
                        ),
                    )
                    return

        contents_path = package_contents_path(
            package_path
        )

        try:
            copy_implementation_package_archive(
                source_path,
                contents_path,
            )
        except FileExistsError as error:
            QMessageBox.warning(
                self,
                "Implementation Package Already Exists",
                str(error),
            )
            return
        except ImplementationPackageError as error:
            QMessageBox.warning(
                self,
                "Invalid Implementation Package",
                str(error),
            )
            return
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Import Implementation Package",
                (
                    "Could not copy the implementation package:"
                    f"\n\n{error}"
                ),
            )
            return

        self.project_view.refresh()

    def _package_contents_for_artifact_action(
            self,
            feature_name: str,
            package_id: str,
    ) -> Path | None:
        if self.workspace_path is None:
            return None

        try:
            package_path = project_package_path(
                self.workspace_path,
                feature_name,
                package_id,
            )
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Package Unavailable",
                str(error),
            )
            return None

        if (
                package_path.is_symlink()
                or not package_path.exists()
                or not package_path.is_dir()
        ):
            QMessageBox.warning(
                self,
                "Package Unavailable",
                (
                    "The selected Package no longer exists "
                    "as an available Package directory."
                ),
            )
            return None

        if not self._ensure_project_package_structure(
                feature_name,
                package_id,
        ):
            return None

        return package_contents_path(
            package_path
        )

    def _extract_implementation_package(
            self,
            feature_name: str,
            package_id: str,
    ) -> None:
        contents_path = self._package_contents_for_artifact_action(
            feature_name,
            package_id,
        )

        if contents_path is None:
            return

        try:
            archives = discover_implementation_package_archives(
                contents_path
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Extract Implementation Package",
                (
                    "Could not inspect Package Contents:"
                    f"\n\n{error}"
                ),
            )
            return

        if not archives:
            QMessageBox.information(
                self,
                "No Implementation Package ZIP",
                (
                    "This Package does not contain a valid "
                    "implementation-package ZIP."
                ),
            )
            return

        selected_archive = archives[0]

        if len(archives) > 1:
            archive_names = tuple(
                archive.source_path.name
                for archive in archives
            )
            selected_name, accepted = QInputDialog.getItem(
                self,
                "Extract Implementation Package",
                "Archive:",
                archive_names,
                0,
                False,
            )

            if not accepted:
                return

            selected_archive = next(
                archive
                for archive in archives
                if archive.source_path.name == selected_name
            )

        try:
            extract_implementation_package_archive(
                selected_archive.source_path,
                contents_path,
            )
        except FileExistsError as error:
            QMessageBox.warning(
                self,
                "Implementation Package Already Extracted",
                str(error),
            )
            return
        except ImplementationPackageError as error:
            QMessageBox.warning(
                self,
                "Invalid Implementation Package",
                str(error),
            )
            return
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Extract Implementation Package",
                (
                    "Could not extract the implementation package:"
                    f"\n\n{error}"
                ),
            )
            return

        self.project_view.refresh()

    def _inspect_implementation_package(
            self,
            feature_name: str,
            package_id: str,
    ) -> None:
        contents_path = self._package_contents_for_artifact_action(
            feature_name,
            package_id,
        )

        if contents_path is None:
            return

        try:
            extracted_packages = (
                discover_extracted_implementation_packages(
                    contents_path
                )
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Inspect Implementation Package",
                (
                    "Could not inspect Package Contents:"
                    f"\n\n{error}"
                ),
            )
            return

        if not extracted_packages:
            try:
                archives = discover_implementation_package_archives(
                    contents_path
                )
            except OSError as error:
                QMessageBox.warning(
                    self,
                    "Unable to Inspect Implementation Package",
                    (
                        "Could not inspect Package Contents:"
                        f"\n\n{error}"
                    ),
                )
                return

            if archives:
                QMessageBox.information(
                    self,
                    "Implementation Package Not Extracted",
                    (
                        "A valid implementation-package ZIP is "
                        "available, but it has not been extracted."
                    ),
                )
            else:
                QMessageBox.information(
                    self,
                    "No Extracted Implementation Package",
                    (
                        "This Package does not contain a valid "
                        "extracted implementation package."
                    ),
                )

            return

        selected_package = extracted_packages[0]

        if len(extracted_packages) > 1:
            package_names = tuple(
                package.root_path.name
                for package in extracted_packages
            )
            selected_name, accepted = QInputDialog.getItem(
                self,
                "Inspect Implementation Package",
                "Extracted Package:",
                package_names,
                0,
                False,
            )

            if not accepted:
                return

            selected_package = next(
                package
                for package in extracted_packages
                if package.root_path.name == selected_name
            )

        try:
            readme = parse_implementation_package_readme(
                selected_package.readme_path
            )
        except ImplementationPackageError as error:
            QMessageBox.warning(
                self,
                "Unable to Inspect Package README",
                str(error),
            )
            return
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Inspect Package README",
                (
                    "Could not read README.txt:"
                    f"\n\n{error}"
                ),
            )
            return

        dialog = PackageInspectorDialog(
            package_id,
            selected_package,
            readme,
            contents_path,
            parent=self,
        )
        dialog.open_readme_requested.connect(
            self._open_file_path
        )
        dialog.open_contents_requested.connect(
            self._open_package_contents_from_inspector
        )
        dialog.install_requested.connect(
            lambda root_name: self._install_implementation_package(
                feature_name,
                package_id,
                preferred_root_name=root_name,
            )
        )
        dialog.exec()

    def _select_extracted_implementation_package(
            self,
            extracted_packages: tuple[
                ExtractedImplementationPackage,
                ...,
            ],
            *,
            dialog_title: str,
            preferred_root_name: str | None = None,
    ) -> ExtractedImplementationPackage | None:
        if preferred_root_name is not None:
            for extracted_package in extracted_packages:
                if (
                        extracted_package.root_path.name
                        == preferred_root_name
                ):
                    return extracted_package

            QMessageBox.warning(
                self,
                "Implementation Package Unavailable",
                (
                    "The extracted implementation package that "
                    "was selected is no longer available or is "
                    "no longer structurally valid."
                ),
            )
            return None

        if not extracted_packages:
            return None

        if len(extracted_packages) == 1:
            return extracted_packages[0]

        package_names = tuple(
            package.root_path.name
            for package in extracted_packages
        )
        selected_name, accepted = QInputDialog.getItem(
            self,
            dialog_title,
            "Extracted Package:",
            package_names,
            0,
            False,
        )

        if not accepted:
            return None

        return next(
            package
            for package in extracted_packages
            if package.root_path.name == selected_name
        )

    def _resolve_package_installation_target(
            self,
    ) -> Path | None:
        if self.workspace_path is None:
            return None

        if (
                self._is_project_metadata_document_open()
                and self.text_editor.document().isModified()
        ):
            QMessageBox.warning(
                self,
                "Project Metadata Has Unsaved Changes",
                (
                    "Save or discard the open Project metadata "
                    "changes before installing an implementation "
                    "package."
                ),
            )
            return None

        try:
            metadata = load_project_metadata(
                self.workspace_path
            )
        except (ProjectMetadataError, OSError) as error:
            QMessageBox.warning(
                self,
                "Unable to Load Project Configuration",
                (
                    "The Project configuration could not be "
                    f"loaded.\n\n{error}"
                ),
            )
            return None

        if metadata is None:
            QMessageBox.information(
                self,
                "Project Configuration Required",
                (
                    "Configure the Project before installing "
                    "implementation packages."
                ),
            )
            return None

        target_path = metadata.local_git_repository

        if (
                not target_path.exists()
                or not target_path.is_dir()
        ):
            QMessageBox.warning(
                self,
                "Configured Local Repository Unavailable",
                (
                    "The configured local Git repository does "
                    "not exist or is not a directory:"
                    f"\n\n{target_path}"
                ),
            )
            return None

        return target_path

    def _confirm_implementation_package_installation(
            self,
            package_id: str,
            extracted_package: ExtractedImplementationPackage,
            target_path: Path,
    ) -> bool:
        message_box = QMessageBox(
            self
        )
        message_box.setWindowTitle(
            "Install Implementation Package"
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )
        message_box.setText(
            (
                f'Install Package "{package_id}" into the '
                "configured local repository?"
            )
        )
        message_box.setInformativeText(
            (
                "Extracted Package:\n"
                f"{extracted_package.root_path.name}\n\n"
                "Installer:\n"
                f"{extracted_package.install_script_path}\n\n"
                "Target:\n"
                f"{target_path}\n\n"
                "The installer may modify files in the target "
                "Project."
            )
        )

        install_button = message_box.addButton(
            "Install",
            QMessageBox.ButtonRole.AcceptRole,
        )
        cancel_button = message_box.addButton(
            QMessageBox.StandardButton.Cancel
        )
        message_box.setDefaultButton(
            cancel_button
        )
        message_box.exec()

        return (
            message_box.clickedButton()
            is install_button
        )

    def _install_implementation_package(
            self,
            feature_name: str,
            package_id: str,
            preferred_root_name: str | None = None,
    ) -> None:
        contents_path = self._package_contents_for_artifact_action(
            feature_name,
            package_id,
        )

        if contents_path is None:
            return

        try:
            extracted_packages = (
                discover_extracted_implementation_packages(
                    contents_path
                )
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Unable to Install Implementation Package",
                (
                    "Could not inspect Package Contents:"
                    f"\n\n{error}"
                ),
            )
            return

        if not extracted_packages:
            try:
                archives = discover_implementation_package_archives(
                    contents_path
                )
            except OSError as error:
                QMessageBox.warning(
                    self,
                    "Unable to Install Implementation Package",
                    (
                        "Could not inspect Package Contents:"
                        f"\n\n{error}"
                    ),
                )
                return

            if archives:
                QMessageBox.information(
                    self,
                    "Implementation Package Not Extracted",
                    (
                        "A valid implementation-package ZIP is "
                        "available, but it must be extracted before "
                        "installation."
                    ),
                )
            else:
                QMessageBox.information(
                    self,
                    "No Installable Implementation Package",
                    (
                        "This Package does not contain a valid "
                        "extracted implementation package."
                    ),
                )

            return

        selected_package = (
            self._select_extracted_implementation_package(
                extracted_packages,
                dialog_title="Install Implementation Package",
                preferred_root_name=preferred_root_name,
            )
        )

        if selected_package is None:
            return

        try:
            selected_package = (
                inspect_extracted_implementation_package(
                    selected_package.root_path
                )
            )
        except (ImplementationPackageError, OSError) as error:
            QMessageBox.warning(
                self,
                "Implementation Package Changed",
                (
                    "The extracted implementation package is "
                    f"no longer valid.\n\n{error}"
                ),
            )
            return

        target_path = self._resolve_package_installation_target()

        if target_path is None:
            return

        python_program = QStandardPaths.findExecutable(
            "python3"
        )

        if not python_program:
            QMessageBox.warning(
                self,
                "Python 3 Unavailable",
                (
                    'The "python3" executable could not be found. '
                    "Install Python 3 or make it available on the "
                    "application PATH before installing packages."
                ),
            )
            return

        if not self._confirm_implementation_package_installation(
                package_id,
                selected_package,
                target_path,
        ):
            return

        try:
            selected_package = (
                inspect_extracted_implementation_package(
                    selected_package.root_path
                )
            )
        except (ImplementationPackageError, OSError) as error:
            QMessageBox.warning(
                self,
                "Implementation Package Changed",
                (
                    "The extracted implementation package changed "
                    "before installation could begin."
                    f"\n\n{error}"
                ),
            )
            return

        if (
                not target_path.exists()
                or not target_path.is_dir()
        ):
            QMessageBox.warning(
                self,
                "Configured Local Repository Unavailable",
                (
                    "The configured local Git repository is no "
                    "longer available:"
                    f"\n\n{target_path}"
                ),
            )
            return

        dialog = PackageInstallDialog(
            package_id,
            selected_package,
            target_path,
            python_program,
            parent=self,
        )
        dialog.start_installation()
        dialog.exec()

    def _open_package_contents_from_inspector(
            self,
            contents_path: str,
    ) -> None:
        path = Path(
            contents_path
        )

        if (
                path.is_symlink()
                or not path.exists()
                or not path.is_dir()
        ):
            QMessageBox.warning(
                self,
                "Package Contents Unavailable",
                (
                    "The Package Contents directory is no longer "
                    "available."
                ),
            )
            return

        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(
                    path
                )
            )
        )

        if not opened:
            QMessageBox.warning(
                self,
                "Unable to Open Package Contents",
                (
                    "The system file manager could not open "
                    "the Package Contents directory."
                ),
            )

    def _remove_registered_project(
            self,
            path: str,
    ) -> None:
        if self.project_registry_load_error is not None:
            QMessageBox.warning(
                self,
                "Unable to Update Project Registry",
                (
                    "Project Registry changes are unavailable for "
                    "this application session because the registry "
                    "could not be loaded safely."
                ),
            )
            return

        workspace_path = Path(
            path
        ).expanduser().absolute()

        if not self.project_registry.contains(
                workspace_path
        ):
            self._refresh_welcome_projects()
            return

        message_box = QMessageBox(self)
        message_box.setWindowTitle(
            "Remove Project"
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )
        message_box.setText(
            "Remove this Project from the Projects list?"
        )
        message_box.setInformativeText(
            (
                "The workspace directory and its files will not "
                "be deleted."
                f"\n\n{workspace_path}"
            )
        )
        message_box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        message_box.setDefaultButton(
            QMessageBox.StandardButton.No
        )

        if (
                message_box.exec()
                != QMessageBox.StandardButton.Yes
        ):
            return

        updated_registry = ProjectRegistry(
            self.project_registry.projects
        )

        if not updated_registry.remove(
                workspace_path
        ):
            self._refresh_welcome_projects()
            return

        try:
            save_project_registry(
                updated_registry,
                self.project_registry_path,
            )
        except (ProjectRegistryError, OSError) as error:
            QMessageBox.warning(
                self,
                "Unable to Update Project Registry",
                (
                    "The Project could not be removed from the "
                    "Projects list."
                    f"\n\n{error}"
                ),
            )
            return

        self.project_registry = updated_registry
        self._refresh_welcome_projects()

    def _activate_workspace(
            self,
            path: str | Path,
    ) -> bool:
        workspace = Path(
            path
        ).expanduser().absolute()

        if not workspace.exists():
            QMessageBox.warning(
                self,
                "Project Unavailable",
                (
                    "The selected Project workspace no longer exists:"
                    f"\n\n{workspace}"
                ),
            )
            return False

        if not workspace.is_dir():
            QMessageBox.warning(
                self,
                "Project Unavailable",
                (
                    "The selected Project workspace is not a directory:"
                    f"\n\n{workspace}"
                ),
            )
            return False

        self._set_workspace_root(
            str(workspace)
        )
        self._record_workspace_opened(
            workspace
        )

        return True

    def _record_workspace_opened(
            self,
            workspace_path: Path,
    ) -> None:
        if self.project_registry_load_error is not None:
            return

        try:
            self.project_registry.register(
                workspace_path
            )
            save_project_registry(
                self.project_registry,
                self.project_registry_path,
            )
        except (ProjectRegistryError, OSError) as error:
            QMessageBox.warning(
                self,
                "Unable to Save Project Registry",
                (
                    "The workspace was opened, but its recent Project "
                    "information could not be saved."
                    f"\n\n{error}"
                ),
            )

        self._refresh_welcome_projects()

    def _set_workspace_root(
            self,
            path: str,
    ) -> None:
        self.workspace_path = path
        self.current_file_path = None
        self.project_metadata = None
        self.project_metadata_load_error = None

        self.file_tree.set_workspace_path(
            path
        )

        self.file_model.setRootPath(
            path
        )
        self.file_tree.setRootIndex(
            self.file_model.index(path)
        )

        self.text_editor.clear()
        self.text_editor.document().setModified(
            False
        )

        self._load_workspace_project_metadata()

        project_display_name = (
            self.project_metadata.name
            if self.project_metadata is not None
            else Path(path).name
        )
        self.project_view.set_workspace(
            path,
            project_display_name,
        )
        self.workspace_navigation_tabs.setCurrentWidget(
            self.project_view
        )

        self.central_stack.setCurrentWidget(
            self.workspace_page
        )
        self._update_window_title()
        self._update_action_states()

    def _clear_workspace(self) -> None:
        self.workspace_path = None
        self.current_file_path = None
        self.project_metadata = None
        self.project_metadata_load_error = None

        self.file_tree.set_workspace_path(
            None
        )
        self.file_tree.clearSelection()
        self.file_tree.setCurrentIndex(
            QModelIndex()
        )
        self.file_tree.setRootIndex(
            QModelIndex()
        )
        self.project_view.set_workspace(
            None
        )

        self.text_editor.clear()
        self.text_editor.document().setModified(
            False
        )

        self._refresh_welcome_projects()
        self.central_stack.setCurrentWidget(
            self.welcome_page
        )
        self._update_window_title()
        self._update_action_states()

    def _close_project(self) -> None:
        if self.workspace_path is None:
            return

        if not self._confirm_discard_unsaved_changes():
            return

        self._clear_workspace()

    def _load_workspace_project_metadata(self) -> None:
        self.project_metadata = None
        self.project_metadata_load_error = None

        if self.workspace_path is None:
            return

        try:
            self.project_metadata = load_project_metadata(
                self.workspace_path
            )
        except (ProjectMetadataError, OSError) as error:
            self.project_metadata_load_error = str(error)

            QMessageBox.warning(
                self,
                "Unable to Load Project Metadata",
                (
                    "The workspace was opened, but its Project "
                    "metadata could not be loaded."
                    f"\n\n{error}"
                ),
            )

    def _configure_project(self) -> None:
        if self.workspace_path is None:
            return

        if not self._prepare_project_metadata_document_for_configuration():
            return

        dialog = ProjectSettingsDialog(
            workspace_path=self.workspace_path,
            metadata=self.project_metadata,
            parent=self,
        )

        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            metadata = dialog.project_metadata()

            if (
                    self.project_metadata_load_error is not None
                    and not self._confirm_replace_invalid_project_metadata()
            ):
                continue

            if self._save_project_configuration(metadata):
                return

    def _prepare_project_metadata_document_for_configuration(
            self,
    ) -> bool:
        if not self._is_project_metadata_document_open():
            return True

        if not self.text_editor.document().isModified():
            return True

        file_name = Path(
            self.current_file_path
        ).name

        message_box = QMessageBox(self)
        message_box.setWindowTitle(
            "Unsaved Changes"
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )
        message_box.setText(
            f"{file_name} has unsaved changes."
        )
        message_box.setInformativeText(
            "Do you want to save your changes?"
        )
        message_box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        message_box.setDefaultButton(
            QMessageBox.StandardButton.Save
        )

        result = message_box.exec()

        if result == QMessageBox.StandardButton.Save:
            metadata_path = self._project_metadata_path()

            if (
                    metadata_path is not None
                    and metadata_path.is_symlink()
            ):
                QMessageBox.warning(
                    self,
                    "Unable to Save Project Metadata",
                    (
                        "The Project metadata file is a symbolic link "
                        "and cannot be saved through Project "
                        "configuration."
                    ),
                )
                return False

            if not self._save_current_file():
                return False

            self._load_workspace_project_metadata()
            return True

        if result == QMessageBox.StandardButton.Discard:
            return self._reload_open_project_metadata_document(
                "Unable to Reload Project Metadata",
                (
                    "The on-disk Project metadata could not "
                    "be reloaded."
                ),
            )

        return False

    def _confirm_replace_invalid_project_metadata(
            self,
    ) -> bool:
        message_box = QMessageBox(self)
        message_box.setWindowTitle(
            "Replace Project Metadata"
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )
        message_box.setText(
            "The existing Project metadata could not be loaded."
        )
        message_box.setInformativeText(
            (
                "Saving this configuration will replace "
                f"{PROJECT_METADATA_FILENAME}. Any unsupported or "
                "invalid values in the existing file will not be "
                "preserved."
            )
        )
        message_box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        message_box.setDefaultButton(
            QMessageBox.StandardButton.No
        )

        return (
            message_box.exec()
            == QMessageBox.StandardButton.Yes
        )

    def _save_project_configuration(
            self,
            metadata: ProjectMetadata,
    ) -> bool:
        if self.workspace_path is None:
            return False

        try:
            save_project_metadata(
                self.workspace_path,
                metadata,
            )
        except (ProjectMetadataError, OSError) as error:
            QMessageBox.critical(
                self,
                "Unable to Save Project Configuration",
                (
                    "Could not save the Project configuration:"
                    f"\n\n{error}"
                ),
            )
            return False

        self.project_metadata = metadata
        self.project_metadata_load_error = None
        self.project_view.set_project_display_name(
            metadata.name
        )

        if self._is_project_metadata_document_open():
            self._reload_open_project_metadata_document(
                "Project Configuration Saved",
                (
                    "Project settings were saved, but the open "
                    "metadata document could not be refreshed."
                ),
            )

        return True

    def _project_metadata_path(self) -> Path | None:
        if self.workspace_path is None:
            return None

        return (
            Path(self.workspace_path)
            / PROJECT_METADATA_FILENAME
        )

    def _is_project_metadata_document_open(self) -> bool:
        if self.current_file_path is None:
            return False

        metadata_path = self._project_metadata_path()

        if metadata_path is None:
            return False

        return (
            Path(self.current_file_path)
            .expanduser()
            .absolute()
            == metadata_path
            .expanduser()
            .absolute()
        )

    def _reload_open_project_metadata_document(
            self,
            error_title: str,
            error_message: str,
    ) -> bool:
        if not self._is_project_metadata_document_open():
            return True

        metadata_path = self._project_metadata_path()

        if metadata_path is None:
            return False

        if (
                metadata_path.is_symlink()
                or self.workspace_path is None
                or not is_workspace_target(
                    metadata_path,
                    self.workspace_path,
                )
        ):
            QMessageBox.warning(
                self,
                error_title,
                (
                    f"{error_message}\n\n"
                    "The Project metadata file cannot be read "
                    "through a symbolic link or outside the "
                    "current workspace."
                ),
            )
            return False

        try:
            text = metadata_path.read_text(
                encoding="utf-8"
            )
        except (UnicodeDecodeError, OSError) as error:
            QMessageBox.warning(
                self,
                error_title,
                f"{error_message}\n\n{error}",
            )
            return False

        self.text_editor.setPlainText(
            text
        )
        self.text_editor.document().setModified(
            False
        )
        self._update_window_title()

        return True

    def _open_file_from_tree(
            self,
            index,
    ) -> None:
        if self.file_model.isDir(index):
            return

        self._open_file_path(
            self.file_model.filePath(
                index
            )
        )

    def _open_file_path(
            self,
            file_path: str | Path,
    ) -> bool:
        path = Path(
            file_path
        )

        if self.workspace_path is None:
            return False

        if (
                path.is_dir()
                or not is_workspace_target(
                    path,
                    self.workspace_path,
                )
        ):
            QMessageBox.warning(
                self,
                "Unable to Open File",
                (
                    "Files outside the current workspace "
                    "or directories cannot be opened "
                    "through the editor."
                ),
            )
            return False

        if str(path) == self.current_file_path:
            return True

        if not self._confirm_discard_unsaved_changes():
            return False

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            QMessageBox.warning(
                self,
                "Unable to Open File",
                (
                    "This file does not appear "
                    "to be a UTF-8 text file."
                ),
            )
            return False
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Open File",
                (
                    "Could not open the file:"
                    f"\n\n{error}"
                ),
            )
            return False

        self.current_file_path = str(
            path
        )

        self.text_editor.setPlainText(
            text
        )
        self.text_editor.document().setModified(
            False
        )

        self._update_window_title()
        self._update_action_states()

        return True

    def _save_current_file(self) -> bool:
        if self.current_file_path is None:
            return False

        if (
                self.workspace_path is None
                or not is_workspace_target(
                    self.current_file_path,
                    self.workspace_path,
                )
        ):
            QMessageBox.warning(
                self,
                "Unable to Save File",
                (
                    "The file no longer resolves inside the "
                    "current workspace and cannot be saved."
                ),
            )
            return False

        try:
            Path(
                self.current_file_path
            ).write_text(
                self.text_editor.toPlainText(),
                encoding="utf-8",
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Save File",
                (
                    "Could not save the file:"
                    f"\n\n{error}"
                ),
            )
            return False

        self.text_editor.document().setModified(
            False
        )

        self._update_window_title()

        return True

    def _create_new_file(
            self,
            target_path: str | None = None,
    ) -> None:
        if target_path is not None:
            target_directory = self._validated_creation_directory(
                Path(target_path)
            )
        else:
            target_directory = (
                self._get_creation_directory()
            )

        if target_directory is None:
            return

        file_name, accepted = QInputDialog.getText(
            self,
            "New File",
            "File name:",
        )

        if not accepted:
            return

        file_name = file_name.strip()

        if not self._is_valid_item_name(
                file_name
        ):
            QMessageBox.warning(
                self,
                "Invalid File Name",
                (
                    "Enter a valid file name "
                    "without path separators."
                ),
            )
            return

        new_file_path = (
                target_directory / file_name
        )

        if filesystem_entry_exists(
                new_file_path
        ):
            QMessageBox.warning(
                self,
                "File Already Exists",
                (
                    "A file or folder named "
                    f"'{file_name}' already exists."
                ),
            )
            return

        if (
                self.workspace_path is None
                or not is_workspace_target(
                    new_file_path,
                    self.workspace_path,
                )
        ):
            QMessageBox.warning(
                self,
                "Invalid File Location",
                (
                    "Files can only be created inside "
                    "the current workspace."
                ),
            )
            return

        if not self._confirm_discard_unsaved_changes():
            return

        try:
            new_file_path.write_text(
                "",
                encoding="utf-8",
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Create File",
                (
                    "Could not create the file:"
                    f"\n\n{error}"
                ),
            )
            return

        self.current_file_path = str(
            new_file_path
        )

        self.text_editor.clear()
        self.text_editor.document().setModified(
            False
        )
        self.text_editor.setFocus()

        self._update_window_title()
        self._update_action_states()
        self.project_view.refresh()

    def _create_new_folder(
            self,
            target_path: str | None = None,
    ) -> None:
        if target_path is not None:
            target_directory = self._validated_creation_directory(
                Path(target_path)
            )
        else:
            target_directory = (
                self._get_creation_directory()
            )

        if target_directory is None:
            return

        folder_name, accepted = QInputDialog.getText(
            self,
            "New Folder",
            "Folder name:",
        )

        if not accepted:
            return

        folder_name = folder_name.strip()

        if not self._is_valid_item_name(
                folder_name
        ):
            QMessageBox.warning(
                self,
                "Invalid Folder Name",
                (
                    "Enter a valid folder name "
                    "without path separators."
                ),
            )
            return

        new_folder_path = (
                target_directory / folder_name
        )

        if filesystem_entry_exists(
                new_folder_path
        ):
            QMessageBox.warning(
                self,
                "Folder Already Exists",
                (
                    "A file or folder named "
                    f"'{folder_name}' already exists."
                ),
            )
            return

        if (
                self.workspace_path is None
                or not is_workspace_target(
                    new_folder_path,
                    self.workspace_path,
                )
        ):
            QMessageBox.warning(
                self,
                "Invalid Folder Location",
                (
                    "Folders can only be created inside "
                    "the current workspace."
                ),
            )
            return

        try:
            new_folder_path.mkdir()
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Create Folder",
                (
                    "Could not create the folder:"
                    f"\n\n{error}"
                ),
            )

    def _rename_item(
            self,
            path_string: str,
    ) -> None:
        path = Path(path_string)

        if not self._can_modify_path(path):
            return

        new_name, accepted = QInputDialog.getText(
            self,
            "Rename",
            "New name:",
            QLineEdit.EchoMode.Normal,
            path.name,
        )

        if not accepted:
            return

        new_name = new_name.strip()

        if not self._is_valid_item_name(
                new_name
        ):
            QMessageBox.warning(
                self,
                "Invalid Name",
                (
                    "Enter a valid name "
                    "without path separators."
                ),
            )
            return

        new_path = path.with_name(
            new_name
        )

        if new_path == path:
            return

        if filesystem_entry_exists(
                new_path
        ):
            QMessageBox.warning(
                self,
                "Name Already Exists",
                (
                    "A file or folder named "
                    f"'{new_name}' already exists."
                ),
            )
            return

        if (
                self.workspace_path is None
                or not is_workspace_entry(
                    new_path,
                    self.workspace_path,
                )
        ):
            QMessageBox.warning(
                self,
                "Invalid Operation",
                (
                    "Files outside the current "
                    "workspace cannot be modified."
                ),
            )
            return

        try:
            path.rename(
                new_path
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Rename Item",
                (
                    "Could not rename the item:"
                    f"\n\n{error}"
                ),
            )
            return

        self._rebase_current_file_path(
            path,
            new_path,
        )

    def _delete_item(
            self,
            path_string: str,
    ) -> None:
        path = Path(path_string)

        if not self._can_modify_path(path):
            return

        if path.is_symlink():
            item_type = "symbolic link"
        elif path.is_dir():
            item_type = "folder"
        else:
            item_type = "file"

        message_box = QMessageBox(self)

        message_box.setWindowTitle(
            "Delete Item"
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )

        message_box.setText(
            f"Delete {item_type} '{path.name}'?"
        )

        if path.is_symlink():
            message_box.setInformativeText(
                (
                    "The symbolic link will be permanently deleted. "
                    "Its target will not be deleted."
                )
            )
        elif path.is_dir():
            message_box.setInformativeText(
                (
                    "The folder and everything "
                    "inside it will be permanently deleted. "
                    "This cannot be undone."
                )
            )
        else:
            message_box.setInformativeText(
                (
                    "The file will be permanently deleted. "
                    "This cannot be undone."
                )
            )

        message_box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        message_box.setDefaultButton(
            QMessageBox.StandardButton.No
        )

        result = message_box.exec()

        if result != QMessageBox.StandardButton.Yes:
            return

        contains_current_document = (
            self._path_contains_current_document(
                path
            )
        )

        if (
                contains_current_document
                and not self._confirm_discard_unsaved_changes()
        ):
            return

        try:
            if (
                    path.is_dir()
                    and not path.is_symlink()
            ):
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as error:
            QMessageBox.critical(
                self,
                "Unable to Delete Item",
                (
                    "Could not delete the item:"
                    f"\n\n{error}"
                ),
            )
            return

        if contains_current_document:
            self.current_file_path = None

            self.text_editor.clear()
            self.text_editor.document().setModified(
                False
            )

            self._update_window_title()
            self._update_action_states()

    def _get_creation_directory(
            self,
    ) -> Path | None:
        if self.workspace_path is None:
            QMessageBox.information(
                self,
                "No Workspace Open",
                (
                    "Open a workspace before "
                    "creating files or folders."
                ),
            )
            return None

        current_index = (
            self.file_tree.currentIndex()
        )

        if not current_index.isValid():
            candidate = Path(
                self.workspace_path
            )
        else:
            selected_path = Path(
                self.file_model.filePath(
                    current_index
                )
            )

            if selected_path.is_dir():
                candidate = selected_path
            else:
                candidate = selected_path.parent

        return self._validated_creation_directory(
            candidate
        )

    def _validated_creation_directory(
            self,
            path: Path,
    ) -> Path | None:
        if self.workspace_path is None:
            return None

        if (
                not filesystem_entry_exists(path)
                or not path.is_dir()
        ):
            QMessageBox.warning(
                self,
                "Invalid Folder Location",
                "The selected location is not an available folder.",
            )
            return None

        if not is_workspace_target(
                path,
                self.workspace_path,
        ):
            QMessageBox.warning(
                self,
                "Invalid Folder Location",
                (
                    "Files and folders can only be created inside "
                    "the current workspace."
                ),
            )
            return None

        return path

    def _is_valid_item_name(
            self,
            name: str,
    ) -> bool:
        if not name:
            return False

        if name in {".", ".."}:
            return False

        if "/" in name or "\\" in name:
            return False

        return True

    def _can_modify_path(
            self,
            path: Path,
    ) -> bool:
        if self.workspace_path is None:
            return False

        if not filesystem_entry_exists(path):
            QMessageBox.warning(
                self,
                "Item Not Found",
                (
                    "The selected file or folder "
                    "no longer exists."
                ),
            )
            return False

        if not is_workspace_entry(
                path,
                self.workspace_path,
        ):
            QMessageBox.warning(
                self,
                "Invalid Operation",
                (
                    "Files outside the current "
                    "workspace cannot be modified."
                ),
            )
            return False

        if same_path_entry(
                path,
                self.workspace_path,
        ):
            QMessageBox.warning(
                self,
                "Invalid Operation",
                (
                    "The workspace root cannot "
                    "be renamed or deleted."
                ),
            )
            return False

        return True

    def _path_contains_current_document(
            self,
            path: Path,
    ) -> bool:
        if self.current_file_path is None:
            return False

        current_path = Path(
            self.current_file_path
        )

        if current_path == path:
            return True

        try:
            current_path.relative_to(
                path
            )
        except ValueError:
            return False

        return True

    def _rebase_current_file_path(
            self,
            old_path: Path,
            new_path: Path,
    ) -> bool:
        if self.current_file_path is None:
            return False

        current_path = Path(
            self.current_file_path
        )

        try:
            relative_path = (
                current_path.relative_to(
                    old_path
                )
            )
        except ValueError:
            return False

        self.current_file_path = str(
            new_path / relative_path
        )

        self._update_window_title()

        return True

    def _handle_paths_moved(
            self,
            moved_paths: dict[str, str],
    ) -> None:
        for old_path, new_path in moved_paths.items():
            if self._rebase_current_file_path(
                    Path(old_path),
                    Path(new_path),
            ):
                break

    def _show_move_error(
            self,
            message: str,
    ) -> None:
        QMessageBox.warning(
            self,
            "Unable to Move Item",
            message,
        )

    def _show_import_error(
            self,
            message: str,
    ) -> None:
        QMessageBox.warning(
            self,
            "Unable to Import Item",
            message,
        )

    def _confirm_discard_unsaved_changes(
            self,
    ) -> bool:
        if not self.text_editor.document().isModified():
            return True

        file_name = (
            Path(
                self.current_file_path
            ).name
            if self.current_file_path
            else "Untitled"
        )

        message_box = QMessageBox(self)

        message_box.setWindowTitle(
            "Unsaved Changes"
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )

        message_box.setText(
            f"{file_name} has unsaved changes."
        )

        message_box.setInformativeText(
            "Do you want to save your changes?"
        )

        message_box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )

        message_box.setDefaultButton(
            QMessageBox.StandardButton.Save
        )

        result = message_box.exec()

        if result == QMessageBox.StandardButton.Save:
            return self._save_current_file()

        if result == QMessageBox.StandardButton.Discard:
            return True

        return False

    def _update_action_states(self) -> None:
        has_workspace = self.workspace_path is not None
        has_document = self.current_file_path is not None

        self.new_file_action.setEnabled(
            has_workspace
        )
        self.new_folder_action.setEnabled(
            has_workspace
        )
        self.open_workspace_action.setEnabled(
            True
        )
        self.new_project_action.setEnabled(
            True
        )
        self.save_action.setEnabled(
            has_document
        )
        self.add_feature_action.setEnabled(
            has_workspace
        )
        self.add_package_action.setEnabled(
            has_workspace
        )
        self.configure_project_action.setEnabled(
            has_workspace
        )
        self.close_project_action.setEnabled(
            has_workspace
        )

    def _update_window_title(
            self,
            *_args,
    ) -> None:
        if self.current_file_path is None:
            self.setWindowTitle(
                "AI Project Organizer"
            )
            return

        file_name = Path(
            self.current_file_path
        ).name

        modified_marker = (
            " *"
            if self.text_editor.document().isModified()
            else ""
        )

        self.setWindowTitle(
            (
                f"{file_name}{modified_marker} "
                f"- AI Project Organizer"
            )
        )

    def closeEvent(
            self,
            event: QCloseEvent,
    ) -> None:
        if self._confirm_discard_unsaved_changes():
            event.accept()
        else:
            event.ignore()
