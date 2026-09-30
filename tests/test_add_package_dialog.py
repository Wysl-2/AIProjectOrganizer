import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
)

from ai_project_organizer.ui.add_package_dialog import (
    AddPackageDialog,
)


class AddPackageDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_features_are_populated_in_supplied_order(self) -> None:
        dialog = AddPackageDialog(
            (
                "Alpha",
                "Beta",
            )
        )

        self.assertEqual(
            [
                dialog.feature_combo.itemText(index)
                for index in range(
                    dialog.feature_combo.count()
                )
            ],
            [
                "Alpha",
                "Beta",
            ],
        )

    def test_selected_feature_is_returned(self) -> None:
        dialog = AddPackageDialog(
            (
                "Alpha",
                "Beta",
            )
        )
        dialog.feature_combo.setCurrentText(
            "Beta"
        )

        self.assertEqual(
            dialog.feature_name(),
            "Beta",
        )

    def test_package_id_is_trimmed(self) -> None:
        dialog = AddPackageDialog(
            ("Alpha",)
        )
        dialog.package_id_edit.setText(
            "  FI03  "
        )

        self.assertEqual(
            dialog.package_id(),
            "FI03",
        )

    def test_ok_button_is_labelled_create(self) -> None:
        dialog = AddPackageDialog(
            ("Alpha",)
        )
        button_box = dialog.findChild(
            QDialogButtonBox
        )
        self.assertIsNotNone(
            button_box
        )
        create_button = button_box.button(
            QDialogButtonBox.StandardButton.Ok
        )

        self.assertIsNotNone(
            create_button
        )
        self.assertEqual(
            create_button.text(),
            "Create",
        )
        self.assertEqual(
            create_button.property(
                "role"
            ),
            "primary",
        )


    def test_selected_feature_name_is_preselected(self) -> None:
        dialog = AddPackageDialog(
            (
                "Alpha",
                "Beta",
            ),
            selected_feature_name="Beta",
        )

        self.assertEqual(
            dialog.feature_name(),
            "Beta",
        )

    def test_missing_selected_feature_keeps_normal_selection(self) -> None:
        dialog = AddPackageDialog(
            (
                "Alpha",
                "Beta",
            ),
            selected_feature_name="Missing",
        )

        self.assertEqual(
            dialog.feature_name(),
            "Alpha",
        )


if __name__ == "__main__":
    unittest.main()
