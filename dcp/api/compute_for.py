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
from collections.abc import Iterable

def compute_for_maker(Job):
    def compute_for(*args, **kwargs):
        args = list(args)

        # Hide values from PythonMonkey which aren't supported
        # TODO: This is bad for a number of reasons:
        ####################################################
        # - Not comprehensively guarding every call to JS
        # - Only applies to compute_for and not compute_do
        # - Bizarre that it only applies to some types.....
        # - Only transforming values that are one level deep

        job_input_idx = None
        job_args_idx = None

        for i, arg in enumerate(args):
            if isinstance(arg, FunctionType):
                # work function arg separates input from arguments, find indices to hide based on it
                if i == 1: # compute.for(iterableObject, work, args), need to wrap iterable
                    job_input_idx = 0
                if i < len(args) - 1: # work function isn't last argument, so last value is args in compute.for
                    job_args_idx = len(args) - 1
                args[i] = dill.source.getsource(arg)

        # Process for ensuring symbols aren't mutated in the python -> js layer:
        #  1. Check if symbol is coming from a dcp module/class. If so, set it as the js_ref. Skip next steps.
        #  2. Determine if input array can be mutated, or create new array for input set
        #  3. For each input element, dereference js_ref if from dcp-client, add a guard if pythonmonkey will mutate it, else as it as-is.
        if job_input_idx != None:
            if hasattr(args[job_input_idx], 'js_ref') and dry.class_manager.reg.find_from_js_instance(args[job_input_idx].js_ref):
                args[job_input_idx] = args[job_input_idx]
            else:
                try:
                    tmp = args[job_input_idx][0]
                    args[job_input_idx][0] = { 'arbitrary-input-test': True }
                    args[job_input_idx][0] = tmp

                    newArr = args[job_input_idx]
                except (ValueError, TypeError):
                    newArr = [ 'placeholder' for i in range(len(args[job_input_idx]))]

                for i, val in enumerate(args[job_input_idx]):
                    if hasattr(val, 'js_ref') and dry.class_manager.reg.find_from_js_instance(val.js_ref):
                        newArr[i] = val
                    elif js.utils.throws_or_coerced_in_pm(val):
                        newArr[i] = { '__pythonmonkey_guard': val }
                    else:
                        newArr[i] = val
                args[job_input_idx] = newArr

        if job_args_idx != None:
            if hasattr(args[job_args_idx], 'js_ref') and dry.class_manager.reg.find_from_js_instance(args[job_args_idx].js_ref):
                args[job_args_idx] = args[job_args_idx]
            else:
                try:
                    tmp = args[job_args_idx][0]
                    args[job_args_idx][0] = { 'arbitrary-input-test': True }
                    args[job_args_idx][0] = tmp

                    newArr = args[job_args_idx]
                except ValueError as e:
                    newArr = [ 'placeholder' for i in range(len(args[job_args_idx]))]

                for i, val in enumerate(args[job_args_idx]):
                    if hasattr(val, 'js_ref') and dry.class_manager.reg.find_from_js_instance(val.js_ref):
                        newArr[i] = val
                    elif js.utils.throws_or_coerced_in_pm(val):
                        newArr[i] = { '__pythonmonkey_guard': val }
                    else:
                        newArr[i] = val
                args[job_args_idx] = newArr

        ####################################################

        JSIterator = pm.eval("""
        (class JSIterator {
            constructor(pyit)
            {
                this.pyit = pyit;
            }

            next()
            {
                return this.pyit.next();
            }

            [Symbol.iterator]()
            {
                return this;
            }
        })
        """)

        compute_for_js = pm.eval("globalThis.dcp.compute.for")
        job_js = dry.aio.blockify(compute_for_js)(*args, **kwargs)
        return Job(job_js)
    return compute_for
