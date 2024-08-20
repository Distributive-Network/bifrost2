#!/usr/bin/env python3

import sys
import dcp; dcp.init()
from dcp import compute_for

def workfn(datum):
    import dcp
    dcp.progress()
    return datum * datum

def deploy_job():
    my_j = compute_for([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], workfn)

    my_j.on('readystatechange', print)
    my_j.on('result', print)
    @my_j.on('accepted')
    def accepted_handler(ev):
        print(f"jobid = {my_j.id}")

    my_j.autoClose = False;
    my_j.public.name = 'simple bifrost2 open job example'
    my_j.exec()

    print(my_j.id)

def add_slices(job_id):
    res = dcp.job.addSlices([1,2,3], job_id)
    print(res)

def get_slices(job_id):
    res = dcp.job.fetchResults(job_id)
    print(len(res))
    print(res)

if len(sys.argv) > 2:
    job_id = sys.argv[1]
    print(f"Job ID is {job_id}")
    if sys.argv[2] == 'add':
        add_slices(job_id)
    elif sys.argv[2] == 'get':
        get_slices(job_id)
    else:
        print(f"Invalid argv {sys.argv}")
        print("Please pass job id, then \"add\" or \"get\"")
else:
    deploy_job()


