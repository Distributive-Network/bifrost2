"""
compute_for API

Author: Will Pringle <will@distributive.network>, Severn Lortie <severn@distributive.network>
Date: July 2024
"""

import pythonmonkey as pm
import dill
from .. import dry
from .. import js
from types import FunctionType

def compute_for_maker(Job):
    def compute_for(*args, **kwargs):
        args = list(args)

        for i, arg in enumerate(args):
            if isinstance(arg, FunctionType):
                args[i] = dill.source.getsource(arg)


        # Hide values from PythonMonkey which aren't supported
        # TODO: This is bad for a number of reasons:
        ####################################################
        # - Not comprehensively guarding every call to JS
        # - Only applies to compute_for and not compute_do
        # - Bizarre that it only applies to some types.....
        # - Only transforming values that are one level deep

        job_input_idx = None
        job_args_idx = None

        # compute.for(start, end, step, work, args)
        if len(args) == 5:
            job_args_idx = 4

        # compute.for(iterableObject, work, args)
        elif len(args) <= 3:
            job_input_idx = 0

            if len(args) == 3:
                job_args_idx = 2

        # clean up job input for PythonMonkey
        if job_input_idx != None:
            for i, val in enumerate(args[job_input_idx]):
                if js.utils.throws_in_pm(val):
                    args[job_input_idx][i] = { '__pythonmonkey_guard': val }

        # clean up job args for PythonMonkey
        if job_args_idx != None:
            for i, val in enumerate(args[job_args_idx]):
                if js.utils.throws_in_pm(val):
                    args[job_args_idx][i] = { '__pythonmonkey_guard': val }

        ####################################################

        compute_for_js = pm.eval("globalThis.dcp.compute.for")
        job_js = dry.aio.blockify(compute_for_js)(*args, **kwargs)
        return Job(job_js)
    return compute_for
