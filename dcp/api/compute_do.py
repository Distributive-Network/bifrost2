"""
compute_do API

Author: Severn Lortie <severn@distributive.network>
Date: Aug 2024
"""

import pythonmonkey as pm
import dill
from types import FunctionType

def compute_do_maker(Job):
    def compute_do(*args, **kwargs):
        args = list(args)
        for i in range(len(args)):
            arg = args[i]
            if isinstance(arg, FunctionType):
                args[i] = dill.source.getsource(arg)
        compute_do_js = pm.eval("globalThis.dcp.compute.do")
        job_js = dry.aio.blockify(computedo_js)(*args, **kwargs)
        return Job(job_js)
    return compute_do
