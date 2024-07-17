import unittest
import asyncio
import pythonmonkey as pm
import dcp
dcp.init()

class TestJobFS(unittest.TestCase):

    def test_smoke_jobfs(self):
        self.assertTrue(dcp.JobFS is not None)
        new_fs = dcp.JobFS()
        self.assertTrue(dcp.JobFS.add is not None)
        self.assertTrue(dcp.JobFS.chdir is not None)

if __name__ == '__main__':
    unittest.main()

