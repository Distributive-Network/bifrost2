"""
Manage Bifrost 2 Class wrappers.

Decorate the raw PythonMonkey JS Proxies with Pythonic Bifrost 2 API classes.

Author: Will Pringle <will@distributive.network>
Date: June 2024
"""

import pythonmonkey as pm
from .aio import asyncify, blockify
from .class_registry import ClassRegistry
from .. import js

reg = ClassRegistry()


def make_new_class(ctor_js_ref_init, name, js_class=None, mutate_js=True):
    def __init__(self, *args, **kwargs):
        self.js_ref = ctor_js_ref_init(self, *args, **kwargs)

        class AsyncAttrs:
            """For instance.aio.*"""
            def __init__(self, parent):
                self.parent = parent

            def __getattr__(self, name):
                async def wrapper(*args, **kwargs):
                    ret_val = await asyncify(self.parent.js_ref[name])(*args, **kwargs)
                    return wrap_obj(ret_val)
                return wrapper

        object.__setattr__(self, 'aio', AsyncAttrs(self))

    def __getattr__(self, name):
        js_attr = self.js_ref[name]

        if isinstance(js_attr, pm.null.__class__):
            return None

        if not callable(js_attr):
            return wrap_obj(js_attr)

        def method(*args, **kwargs):
            ret_val = blockify(js_attr)(*args, **kwargs)
            return wrap_obj(ret_val)
        return method

    def __setattr__(self, name, value):
        if name == 'js_ref':
            object.__setattr__(self, name, value)
        else:
            self.js_ref[name] = value

    def __str__(self):
        # Workaround required since PythonMonkey will encounter errors while str values
        try:
            return str(self.js_ref)
        except:
            return name

    props = {
        '__init__': __init__,
        '__getattr__': __getattr__,
        '__setattr__': __setattr__,
        '__str__': __str__,
        'get_js_class': staticmethod(lambda: js_class),
    }

    if not mutate_js:
        del props['__setattr__']

    new_class = type(name, (object,), props)

    return new_class


def wrap_class(js_class, name=None):
    """Wraps a PythonMonkey JS Proxy Class Function as a Pythonic Class"""
    name = name or js.utils.class_name(js_class)

    def js_ref_generator(self, *args, **kwargs):
        # if the sole argument to the ctor is a js instance, use it as the ref
        if len(args) == 1 and js.utils.instanceof(args[0], js_class):
            self.js_ref = args[0]
        # otherwise, instantiate a new underlying js ref using the ctor args
        else:
            async_wrapped_ctor = blockify(pm.new(js_class))
            self.js_ref = async_wrapped_ctor(*args, **kwargs)
        return self.js_ref

    return make_new_class(js_ref_generator, name, js_class=js_class)


def wrap_obj(js_val):
    """Wraps a PythonMonkey JS Proxy instance as a Pythonic Class instance"""
    if bfclass := ugly_duck_type_check(js_val):
        return bfclass(js_val)

    if isinstance(js_val, pm.JSObjectProxy):
        bfclass = reg.find(js_val)

        if bfclass is None:
            bfclass = wrap_class(js.utils.obj_ctor(js_val))
            bfclass = reg.add(bfclass)

        return bfclass(js_val)
    return js_val

# TODO: there must be a better way to check for this...
def ugly_duck_type_check(js_val):
    """Check via duck typing what the js_val is."""

    # check if it's a result handle
    result_handle_props = ['toJSON', 'newResult', 'getLength', 'slice', 'fetch']
    if js.utils.class_name(js.utils.obj_ctor(js_val)) == 'Function':
        if next((x for x in result_handle_props if js_val[x] is None), None) is None:
            return reg.find('ResultHandle')

