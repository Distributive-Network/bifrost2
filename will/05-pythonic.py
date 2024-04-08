#! /usr/bin/env python3
"""
Another pythonic approach similar to 04 but using an options object

I think I like it a little more, this one returns a job from compute
dot for with the properties set from the job_options arg passed to the
decorator.
"""

import dcp from distributive

job_options = {
    "computeGroups": [{
        "joinKey": "will",
        "joinSecret": "bozo"
    }],
    "public": { "name": "my epic job" },
    "autoClose": False,
}

@dcp.job(job_options)
def my_func(datum):
    dcp.progress()
    return datum * 3

job = my_func([1,2,3,4,5,6])
results = job.exec_sync()
print("results:", results) # 3,6,9,12,15,18

