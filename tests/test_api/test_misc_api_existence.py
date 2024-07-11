"""
Dumb smoke tests for api existence. This does not test functionality (;.
"""
import unittest
import inspect
import dcp
dcp.init()

class TestApiExistence(unittest.TestCase):
    def test_top_level_submodules(self):
        """protocol, compute, dcp_config are commonly used."""
        self.assertTrue(hasattr(dcp, 'protocol'), "dcp.protocol")
        self.assertTrue(hasattr(dcp, 'compute'), "dcp.compute")
        self.assertTrue(hasattr(dcp, 'dcp_config'), "dcp.dcp_config")
        self.assertTrue(hasattr(dcp, 'wallet'), "dcp.wallet")


    def test_fetch_results(self):
        """`fetchResults` chosen arbitrarily."""
        # Check if job.fetchResults is a function
        self.assertTrue(hasattr(dcp.job, 'fetchResults'), "dcp.job.fetchResults")
        self.assertTrue(inspect.isfunction(dcp.job.fetchResults), "dcp.job.fetchResults should be a function")

        # Check if job.aio.fetchResults is an async function
        self.assertTrue(hasattr(dcp.job, 'aio'), "dcp.job.aio")
        self.assertTrue(hasattr(dcp.job.aio, 'fetchResults'), "dcp.job.aio.fetchResults")
        self.assertTrue(inspect.iscoroutinefunction(dcp.job.aio.fetchResults), "dcp.job.aio.fetchResults should be an async function")


    def test_compute_api(self):
        """Valid API examples from https://docs.dcp.dev/api/compute/index.html"""
        self.assertTrue(hasattr(dcp.compute, 'do'), "do")
        self.assertTrue(inspect.isfunction(dcp.compute.do))

        self.assertTrue(hasattr(dcp.compute, 'getJobInfo'), "getJobInfo")
        self.assertTrue(inspect.isfunction(dcp.compute.getJobInfo))

        self.assertTrue(hasattr(dcp.compute, 'status'), "status")
        self.assertTrue(inspect.isfunction(dcp.compute.status))

        self.assertTrue(dcp.compute.marketValue)
        self.assertTrue(dcp.compute.ResultHandle)

        # aio variants
        self.assertTrue(hasattr(dcp.compute.aio, 'status'), "status")
        self.assertTrue(inspect.iscoroutinefunction(dcp.compute.aio.status))

        self.assertTrue(hasattr(dcp.compute.aio, 'getJobInfo'), "getJobInfo")
        self.assertTrue(inspect.iscoroutinefunction(dcp.compute.aio.getJobInfo))


    def test_wallet_api(self):
        self.assertTrue(dcp.wallet.get)
        self.assertTrue(inspect.isfunction(dcp.wallet.get))
        self.assertTrue(dcp.wallet.aio.get)
        self.assertTrue(inspect.iscoroutinefunction(dcp.wallet.aio.get))

if __name__ == '__main__':
    unittest.main()
