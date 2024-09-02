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
        js_attr = object.__getattribute__(self, 'js_ref')[name]

        if isinstance(js_attr, pm.null.__class__):
            return None

        if not callable(js_attr):
            return wrap_obj(js_attr)

        def method(*args, **kwargs):
            args = tuple([arg.js_ref if hasattr(arg, 'js_ref') else arg for arg in args])
            if True in (js.utils.throws_in_pm(arg) for arg in args):
                raise Exception(f'Attempted to pass unsupported value to PythonMonkey')
            ret_val = blockify(js_attr)(*args, **kwargs)
            return wrap_obj(ret_val)
        return method

    def __setattr__(self, name, value):
        if name == 'js_ref':
            object.__setattr__(self, name, value)
        else:
            if js.utils.throws_in_pm(value):
                raise Exception(f'{type(value)} is not supported in PythonMonkey')
            self.js_ref[name] = value

    def _wrapper_set_attribute(self, name, value):
        """Allows for attributes to be set on the proxy itself, not the js_ref."""
        object.__setattr__(self, name, value)

    def _wrapper_get_attribute(self, name):
        """Allows for attributes to be get on the proxy itself, not the js_ref."""
        return object.__getattribute__(self, name)

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
        '_wrapper_set_attribute': _wrapper_set_attribute, #TODO this is doing too much, should just be a proxy, not also have its own api...
        '_wrapper_get_attribute': _wrapper_get_attribute, #TODO same as above
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

    # Result Handle is very hard to check directly, so we duck type
    # check if it's a result handle
    result_handle_props = ['toJSON', 'newResult', 'getLength', 'slice', 'fetch']
    if js_val is not None and js.utils.class_name(js.utils.obj_ctor(js_val)) == 'Function':
        if next((x for x in result_handle_props if js_val[x] is None), None) is None:
            return reg.find('ResultHandle')

    # TODO: job.constructor.name is empty string in PythonMonkey but not NodeJS
    # TODO: Open question: can we even trust x.constructor.name???
    # TODO: Are there better attrs to duck test for Job???
    if hasattr(js_val, 'debugLabel') and js_val.debugLabel == 'Job':
        return reg.find('Job')

