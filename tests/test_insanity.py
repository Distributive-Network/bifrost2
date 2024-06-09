# tests/test_sanity.py

import unittest
import dcp

class TestInSanityFunction(unittest.TestCase):
    def test_insanity_returns_true(self):
        """Test if the sanity function returns True."""
        dcp.init(['will', 'pringle'])
        self.assertTrue(dcp.will)
        self.assertTrue(dcp.pringle)

if __name__ == '__main__':
    unittest.main()
