from collections.abc import Sequence

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class AddPackageDialog(QDialog):
    def __init__(
            self,
            feature_names: Sequence[str],
            selected_feature_name: str | None = None,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(
            "Add Package"
        )
        self.setMinimumWidth(
            420
        )

        self.feature_combo = QComboBox(self)
        self.feature_combo.addItems(
            list(feature_names)
        )

        if (
                selected_feature_name is not None
                and self.feature_combo.findText(
                    selected_feature_name
                ) >= 0
        ):
            self.feature_combo.setCurrentText(
                selected_feature_name
            )

        self.package_id_edit = QLineEdit(self)

        form_layout = QFormLayout()
        form_layout.addRow(
            "Feature",
            self.feature_combo,
        )
        form_layout.addRow(
            "Package ID",
            self.package_id_edit,
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        create_button = buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        if create_button is not None:
            create_button.setText(
                "Create"
            )

        buttons.accepted.connect(
            self.accept
        )
        buttons.rejected.connect(
            self.reject
        )

        layout = QVBoxLayout(self)
        layout.addLayout(
            form_layout
        )
        layout.addWidget(
            buttons
        )

    def feature_name(self) -> str:
        return self.feature_combo.currentText()

    def package_id(self) -> str:
        return self.package_id_edit.text().strip()
