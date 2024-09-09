"""
addSlices API

Author: Will Pringle <will@distributive.network>
Date: September 2024
"""

import pythonmonkey as pm
from .. import dry
from .. import js
from .job_serializers import default_serializers, serialize

def add_slices_maker(add_slices_js):
    def is_iterable(maybe_iterable):
        try:
            iter(maybe_iterable)
            return True
        except TypeError:
            return False

    def add_slices(*args, serializers=default_serializers):
        new_args = []

        for arg in args:
            if not isinstance(arg, str) and is_iterable(arg):
                serialized_vals = []
                for val in arg:
                    serialized_vals.append(serialize(val, serializers))
                new_args.append(serialized_vals)
            else:
                new_args.append(arg)

        js_val = dry.aio.blockify(add_slices_js)(*new_args)
        
        return js_val 
    return add_slices
