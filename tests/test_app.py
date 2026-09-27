import unittest

from ai_project_organizer.app import main


class ApplicationTests(unittest.TestCase):
    def test_main_is_callable(self) -> None:
        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()