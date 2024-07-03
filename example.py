#!/usr/bin/env python3

import pythonmonkey as pm

import dcp
dcp.init()

from dcp import job


my_j = job.Job('x=>{progress();return x+x;}', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

my_j.on('readystatechange', print)
my_j.on('result', print)
@my_j.on('accepted')
def accepted_handler(ev):
    print(my_j.id)

my_j.computeGroups = [{'joinKey': 'joseph', 'joinSecret': 'pringle'}]
my_j.public.name = 'simple bifrost2 example'

res = my_j.exec()

my_j.wait()
# my_j.exec()
# res = my_j.wait()

print(">>>>>>>>>>>>>>>>>>>>>>>>>> RESULTS ARE IN")
print(pm.eval('Array.from')(res))

