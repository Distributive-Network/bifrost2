#! /usr/bin/env python3
"""
Another pythonic approach

But there's a problem - passing kwargs into the decorator like that just feels... ugly?

I think it's an intersting concept to apply the job properties like this in the decorator

but I'm not sure if kwargs is the way to go...
"""

import dcp from distributive

@dcp.job(compute_groups=[{ "joinKey": "will", "joinSecret": "bozo"}], public={ "name": "My Epic Job" })
def my_func(datum):
    dcp.progress()
    return datum * 3

job = my_func([1,2,3,4,5,6])
results = job.exec_sync()
print("results:", results) # 3,6,9,12,15,18

