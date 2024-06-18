# tests/test_sanity.py

import unittest
from dcp import sanity


class TestSanityFunction(unittest.TestCase):
    def test_sanity_returns_true(self):
        """Test if the sanity function returns True."""
        self.assertTrue(sanity())


if __name__ == '__main__':
    unittest.main()

