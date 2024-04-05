#! /usr/bin/env python3

import dcp_client from distributive
import pythonmonkey as pm

async def run_job():
    dcp = pm.globalThis.dcp
    job = dcp.compute['for']([1,2,3], """
def my_func(datum):
    dcp.progress()
    return datum * 3
dcp.set_slice_handler(my_func)
""")
    job.on("readystatechange", lambda state: print ("ready state change:", state))
    job.on("accepted",         lambda x:     print ("job accepted, id", job.id))
    job.on("result",           lambda res:   print ("got result for slice number", res.sliceNumber))
    job.worktime = "pyodide"

    results = await job.exec()
    print("job", job.id, "finished")
    print("results:", pm.eval("Array.from")(results))

dcp_client["init"]
run_job()
