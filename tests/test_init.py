import unittest
import dcp


class TestDcpInitFunction(unittest.TestCase):
    def test_init_exists(self):
        self.assertTrue(hasattr(dcp, 'init'))

    def test_init(self):
        ret_module = dcp.init()
        from dcp import wallet
        from dcp import job

        self.assertEqual(ret_module, dcp)

        job = job.Job('x=>{progress();return x+1', [1, 2, 3])

        # TODO - maybe I should just smoke test if a few functions exist?
        #        How do I test this?

    def test_init_twice(self):
        dcp.init()
        dcp.init()


if __name__ == '__main__':
    unittest.main()

