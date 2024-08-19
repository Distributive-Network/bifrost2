import unittest
import pythonmonkey as pm
import dcp

class TestJob(unittest.TestCase):

    def test_Job(self):
        dcp.init()
        job = dcp.compute_for([], 'x=>{progress(); return x * 2}')
        #job.exec() # TODO can't reliably run this in CI until PythonMonkey corrupted string bug is fixed

    def test_presence_of_important_apis(self):
        """
        Smoke test for some expected Job properties...
        """
        job = dcp.compute_for([1,2,3], 'x=>{progress(); return x * 2}')

        self.assertTrue(hasattr(job, 'wait') and job.wait is not None)
        self.assertTrue(hasattr(job, 'exec') and job.exec is not None)
        self.assertTrue(hasattr(job, 'on') and job.on is not None)
        self.assertTrue(hasattr(job, 'computeGroups') and job.computeGroups is not None)
        self.assertTrue(hasattr(job, 'public') and job.public is not None)
        self.assertTrue(hasattr(job, 'requirements') and job.requirements is not None)
        self.assertTrue(hasattr(job, 'work') and job.work is not None)
        self.assertTrue(hasattr(job, 'status') and job.status is not None)
        self.assertTrue(hasattr(job, 'collateResults') and job.collateResults is not None)
        self.assertTrue(hasattr(job, 'cancel') and job.cancel is not None)
        self.assertTrue(hasattr(job, 'resume') and job.resume is not None)
        self.assertTrue(hasattr(job, 'localExec') and job.localExec is not None)
        self.assertTrue(hasattr(job, 'requires') and job.requires is not None)
        self.assertTrue(hasattr(job, 'setSlicePaymentOffer') and job.setSlicePaymentOffer is not None)
        self.assertTrue(hasattr(job, 'setPaymentAccountKeystore') and job.setPaymentAccountKeystore is not None)

    def test_setting_payment_ks(self):
        job = dcp.compute_for([1,2,3], 'x=>{progress(); return x * 2}')
        ks = dcp.wallet.get()

        # assume this works if it doesn't throw. No way to check if this was
        # successful without using unspec'd properties on the job...
        # If it doesn't throw, assume it worked!
        job.setPaymentAccountKeystore(ks)

    def test_default_compute_group(self):
        job = dcp.compute_for([1,2,3], 'x=>{progress(); return x * 2}')
        self.assertTrue(job.computeGroups[0]['joinKey'], 'public')


if __name__ == '__main__':
    unittest.main()

