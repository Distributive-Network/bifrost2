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

        job = dcp.compute_for([], 'x=>{progress();return x+1')
        job.on('readystatechange', print)


    def test_init_twice(self):
        dcp.init()
        dcp.init()


if __name__ == '__main__':
    unittest.main()

