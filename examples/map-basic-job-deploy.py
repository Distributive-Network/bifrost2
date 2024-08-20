#!/usr/bin/env python3

import dcp
dcp.init()

from dcp import compute_for

workfn = """
function workFunction(datum, arg1, arg2) {
  progress();
  return [ datum * datum, arg1, arg2 ];
}
"""

my_j = compute_for([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], workfn, ['hello', 'world'])

my_j.on('readystatechange', print)
my_j.on('result', print)
@my_j.on('accepted')
def accepted_handler(ev):
    print(f"jobid = {my_j.id}")

my_j.public.name = 'simple bifrost2 map-basic example'
my_j.worktime = 'map-basic'

my_j.exec()
res = my_j.wait()

print(">>>>>>>>>>>>>>>>>>>>>>>>>> RESULTS ARE IN")
print(res)

