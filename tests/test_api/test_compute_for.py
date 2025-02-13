import unittest
import pythonmonkey as pm
import dcp
dcp.init()

class TestComputeFor(unittest.TestCase):

    def test_compute_for(self):
        job1 = dcp.compute_for([1,2,3], 'x=>{progress(); return x * 2}')
        job2 = dcp.compute.do(5, 'x=>{progress(); return x * 2}')

        # check compute_for returns the same type as compute.do
        self.assertTrue(isinstance(job1, job2.__class__))

    def test_smoke_bf2_attrs(self):
        job = dcp.compute_for([1,2,3], 'x=>{progress(); return x * 2}')
        self.assertTrue(hasattr(job, 'wait'))

    def test_range_and_iterables(self):
        dcp.compute_for(range(1,4), '')
        pass

    def test_numpy_array(self):
        import numpy as np
        dcp.compute_for([np.array([1]), np.array([2])], '', [np.array([3]), np.array([[1]])])

if __name__ == '__main__':
    unittest.main()

