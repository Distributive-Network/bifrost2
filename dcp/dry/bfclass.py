# @file         js_object.py - Wrapper Class for DCP JS Classes
#               PythonMonkey's async functions leak, by design, meaning calling
#               a function which returns a promise will immediately require
#               usage of an event loop or will otherwise error. Therefore, not
#               only are async functions block waited, but are also wrapped for
#               use with the aio subcomponent.
#
#               For example: job.aio.exec will return an awaitable but job.exec
#               will block until the true value is returned which the awaitable
#               awaits to.
#
# @TODO         Should be more modular - also, needs to account for dcp object
#               instances returned from methods better.
#
# @author       Will Pringle <will@distributive.network>
# @date         June 2024

import asyncio
import inspect
import types
import pythonmonkey as pm

from .fn import aio_run_wrapper, blocking_run_wrapper


def make_dcp_class(js_class, **kwargs):
    """
    Factory of Classes function for generating pleasant proxies to JS Classes.

    Parameters:
    js_class (function): The JavaScript class to wrap.
    name (string: optional): The name of the new class to make.
    props  (dict, optional): Properties to add to the class.
    js_instance (JSObjectProxy, optional): set a specific JS ref for the class.

    Returns:
    type: A new Python class which wraps the given JavaScript class.
    """

    optional_defaults = {
        'name': js_class_name(js_class),
        'props': {},
        'js_instance': None,
    }
    opts = types.SimpleNamespace(**{**optional_defaults, **kwargs})

    def __init__(self, *args, **kwargs):
        if opts.js_instance is not None:
            self.js_ref = opts.js_instance
        else:
            async_wrapped_ctor = blocking_run_wrapper(pm.new(js_class))
            self.js_ref = async_wrapped_ctor(*args, **kwargs)

        self.aio = AsyncIOMethods(self)

    def __getattr__(self, name):
        js_attr = self.js_ref[name]

        if (not callable(js_attr)):
            # If it returns a js type, wrap it...
            if isinstance(js_attr, pm.JSObjectProxy):
                return wrap_js_obj(js_attr)
            return js_attr

        def method(*args, **kwargs):
            return blocking_run_wrapper(js_attr)(*args, **kwargs)

        return method

    def __setattr__(self, name, value):
        if name == 'js_ref':
            object.__setattr__(self, name, value)
        else:
            self.js_ref[name] = value

    def __str__(self):
        return str(self.js_ref)

    opts.props['__init__'] = __init__
    opts.props['__getattr__'] = __getattr__
    opts.props['__setattr__'] = __setattr__
    opts.props['__str__'] = __str__
    opts.props['get_js_class'] = staticmethod(lambda: js_class)
    new_class = type(opts.name, (object,), opts.props)

    return new_class


class AsyncIOMethods:
    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, name):
        js_attr = self.parent.js_ref[name]
        return aio_run_wrapper(js_attr)


def wrap_js_obj(js_obj, **kwargs):
    if not isinstance(js_obj, pm.JSObjectProxy):
        return js_obj

    JSClass = pm.eval('x=>x.constructor')(js_obj, **kwargs)
    DCPClass = make_dcp_class(JSClass, js_instance=js_obj)

    generic_obj = DCPClass()

    return generic_obj


def js_class_name(JSClass):
    return pm.eval('x=>x.name')(JSClass)

