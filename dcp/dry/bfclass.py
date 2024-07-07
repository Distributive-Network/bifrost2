# @file         bfclass.py - Wrapper Class factory for DCP JS Classes
#
# @author       Will Pringle <will@distributive.network>
# @date         June 2024

import asyncio
import types
import pythonmonkey as pm
from .aio import asyncify, blockify
from . import class_manager 
from .. import js


def make_dcp_class(js_class, name=None):
    name = name or js.utils.class_name(js_class)

    def __init__(self, *args, **kwargs):
        # if the sole argument to the ctor is a js instance, use it as the ref
        if len(args) == 1 and js.utils.instanceof(args[0], js_class):
            self.js_ref = args[0]
        # otherwise, instantiate a new underlying js ref using the ctor args
        else:
            async_wrapped_ctor = blockify(pm.new(js_class))
            self.js_ref = async_wrapped_ctor(*args, **kwargs)

        class AsyncAttrs:
            def __init__(self, parent):
                self.parent = parent

            def __getattr__(self, name):
                return asyncify(self.parent.js_ref[name])

        self.aio = AsyncAttrs(self)

    def __getattr__(self, name):
        js_attr = self.js_ref[name]
        if not callable(js_attr):
            if isinstance(js_attr, pm.JSObjectProxy):
                return wrap_js_obj(js_attr)
            else:
                return js_attr

        def method(*args, **kwargs):
            return blockify(js_attr)(*args, **kwargs)
        return method

    def __setattr__(self, name, value):
        if name == 'js_ref':
            object.__setattr__(self, name, value)
        else:
            self.js_ref[name] = value

    def __str__(self):
        return str(self.js_ref)

    props = {
        '__init__': __init__,
        '__getattr__': __getattr__,
        '__setattr__': __setattr__,
        '__str__': __str__,
        'get_js_class': staticmethod(lambda: js_class),
    }

    new_class = type(name, (object,), props)

    return new_class

# TODO: ew. The bfclass uses the class manager? Shouldn't the class manager
# use bfclass? REFACTOR LATER
def wrap_js_obj(js_val):
    if isinstance(js_val, pm.JSObjectProxy):
        bfclass = class_manager.reg.find(js_val)

        if bfclass is None:
            bfclass = make_dcp_class(js.utils.obj_ctor(js_val))
            bfclass = class_manager.reg.add(bfclass)

        return bfclass(js_val)
    return js_val

