"""
compute_for API

Author: Will Pringle <will@distributive.network>, Severn Lortie <severn@distributive.network>
Date: July 2024
"""

import pythonmonkey as pm
import dill
from .. import dry
from types import FunctionType

def compute_for_maker(Job):
    def compute_for(*args, **kwargs):
        args = list(args)
        for i in range(len(args)):
            arg = args[i]
            if isinstance(arg, FunctionType):
                args[i] = dill.source.getsource(arg)
        compute_for_js = pm.eval("globalThis.dcp.compute.for")
        job_js = dry.aio.blockify(compute_for_js)(*args, **kwargs)
        return Job(job_js)
    return compute_for
