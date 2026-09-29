import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtWidgets import QApplication, QListWidgetItem

from ai_project_organizer.ui.implementation_package_drop_list import (
    ImplementationPackageDropListWidget,
    local_zip_candidate,
)


class ImplementationPackageDropListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_local_zip_candidate_accepts_one_real_local_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive = Path(
                temporary_directory
            ) / "package.ZIP"
            archive.write_bytes(
                b"candidate"
            )

            mime = QMimeData()
            mime.setUrls(
                [
                    QUrl.fromLocalFile(
                        str(
                            archive
                        )
                    )
                ]
            )

            self.assertEqual(
                local_zip_candidate(
                    mime
                ),
                archive,
            )

    def test_local_zip_candidate_rejects_non_zip_and_multiple_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            archive = root / "package.zip"
            text_file = root / "notes.txt"
            archive.write_bytes(
                b"candidate"
            )
            text_file.write_text(
                "notes",
                encoding="utf-8",
            )

            mime = QMimeData()
            mime.setUrls(
                [
                    QUrl.fromLocalFile(
                        str(
                            text_file
                        )
                    )
                ]
            )
            self.assertIsNone(
                local_zip_candidate(
                    mime
                )
            )

            mime.setUrls(
                [
                    QUrl.fromLocalFile(
                        str(
                            archive
                        )
                    ),
                    QUrl.fromLocalFile(
                        str(
                            text_file
                        )
                    ),
                ]
            )
            self.assertIsNone(
                local_zip_candidate(
                    mime
                )
            )

    def test_local_zip_candidate_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(
                temporary_directory
            )
            target = root / "real.zip"
            target.write_bytes(
                b"candidate"
            )
            link = root / "link.zip"

            try:
                link.symlink_to(
                    target
                )
            except OSError:
                self.skipTest(
                    "Symbolic links are unavailable on this platform."
                )

            mime = QMimeData()
            mime.setUrls(
                [
                    QUrl.fromLocalFile(
                        str(
                            link
                        )
                    )
                ]
            )

            self.assertIsNone(
                local_zip_candidate(
                    mime
                )
            )

    def test_drop_target_uses_row_role(self) -> None:
        role = int(
            Qt.ItemDataRole.UserRole
        ) + 7
        widget = ImplementationPackageDropListWidget(
            target_role=role,
            allow_background=True,
        )
        item = QListWidgetItem(
            "Package"
        )
        item.setData(
            role,
            "PKG01",
        )

        with patch.object(
            widget,
            "itemAt",
            return_value=item,
        ):
            self.assertEqual(
                widget._drop_target_at(
                    QPoint(
                        0,
                        0,
                    )
                ),
                "PKG01",
            )

    def test_background_target_respects_configuration(self) -> None:
        role = int(
            Qt.ItemDataRole.UserRole
        ) + 7
        allowed = ImplementationPackageDropListWidget(
            target_role=role,
            allow_background=True,
        )
        rejected = ImplementationPackageDropListWidget(
            target_role=role,
            allow_background=False,
        )

        with patch.object(
            allowed,
            "itemAt",
            return_value=None,
        ):
            self.assertEqual(
                allowed._drop_target_at(
                    QPoint(
                        0,
                        0,
                    )
                ),
                "",
            )

        with patch.object(
            rejected,
            "itemAt",
            return_value=None,
        ):
            self.assertIsNone(
                rejected._drop_target_at(
                    QPoint(
                        0,
                        0,
                    )
                )
            )


if __name__ == "__main__":
    unittest.main()
