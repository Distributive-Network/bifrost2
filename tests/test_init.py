import unittest
import dcp


class TestDcpInitFunction(unittest.TestCase):
    def test_init_exists(self):
        self.assertTrue(hasattr(dcp, 'init'))

    def test_init(self):
        dcp.init()

    def test_init_twice(self):
        dcp.init()
        dcp.init()


if __name__ == '__main__':
    unittest.main()

