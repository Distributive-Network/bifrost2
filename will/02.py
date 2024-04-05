#! /usr/bin/env python3
"""
Small chanages, pretty much looks the same
- dcp is loaded synchronously
- job.worktime is set to pyodide by default
- job.exec_sync so no async python required

Notes
- with job.exec_sync as the only option, it doesn't leave the python
  dev with the opportunity to just grab the job id does it? In NodeJS
  we can just ignore the promise, but it's not as clean here in Python
  - It would be nice if there was a way to synchronously deploy a job
    and just wait for it to be successfully deployed. If it's deployed
    properly, we'd then use the job id to do whatever stuff we need to
    do. This is similar to the Diana server workflow for non-hanging
    jobs.
"""

import dcp from distributive

job = dcp.compute_for([1,2,3], """
def my_func(datum):
    dcp.progress()
    return datum * 3
dcp.set_slice_handler(my_func)
""")

job.on("readystatechange", lambda state: print ("ready state change:", state))
job.on("accepted",         lambda x:     print ("job accepted, id", job.id))
job.on("result",           lambda res:   print ("got result for slice number", res.sliceNumber))

results = job.exec_sync()

print("job", job.id, "finished")
print("results:", results)

