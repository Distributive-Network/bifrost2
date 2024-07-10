import unittest
import pythonmonkey as pm
import dcp

class TestComputeFor(unittest.TestCase):

    def test_compute_for(self):
        dcp.init()
        job1 = dcp.compute_for('x=>{progress(); return x * 2}', [1,2,3])
        job2 = dcp.compute.do(5, 'x=>{progress(); return x * 2}')

        # check compute_for returns the same type as compute.do
        self.assertTrue(isinstance(job1, job2.__class__))

if __name__ == '__main__':
    unittest.main()

