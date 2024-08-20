#!/usr/bin/env python3

import pythonmonkey as pm

import dcp
dcp.init()

from dcp import compute_for
from dcp import JobFS

jfs = JobFS()
jfs.add('./example.py', '/code0.py')
jfs.add('./example.py', 'code1.py')
jfs.add('./example.py', '/home/code2.py')
jfs.add('./example.py', '/home/pyodide/code3.py')

tar_bytes = jfs.to_gzip_tar()
tar_bytearray = bytearray(tar_bytes)

py_workfn = """
import dcp
import os

def ls_safe(dirname):
    try:
        return os.listdir(dirname)
    except:
        return 'failed'

def slice_handler(datum):
    dcp.progress()
    #return datum * datum
    return [ ls_safe('/'), ls_safe('/home'), ls_safe('/home/pyodide') ]

dcp.set_slice_handler(slice_handler)
"""

my_j = compute_for([1], py_workfn, [3, 'gzImage', tar_bytearray])

my_j.worktime = 'pyodide'

my_j.on('readystatechange', print)
my_j.on('result', print)
@my_j.on('accepted')
def accepted_handler(ev):
    print(my_j.id)

my_j.public.name = 'simple bifrost2 example'

res = my_j.exec()

my_j.wait()
# my_j.exec()
# res = my_j.wait()

print(">>>>>>>>>>>>>>>>>>>>>>>>>> RESULTS ARE IN")
print(res)

