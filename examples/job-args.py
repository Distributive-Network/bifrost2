#!/usr/bin/env python3

import dcp
dcp.init()

from dcp import compute_for

def workfn(datum,a,b,c):
    import dcp
    dcp.progress()
    return datum + a + b + c

job = compute_for([1], workfn, [100,1000,10000])

job.on('readystatechange', print)
job.on('result', print)
@job.on('accepted')
def accepted_handler(ev):
    print(f"jobid = {job.id}")

job.public.name = 'bf2: job args example'

job.exec()
res = job.wait()

print(">>>>>>>>>>>>>>>>>>>>>>>>>> RESULTS ARE IN")
print(res)

