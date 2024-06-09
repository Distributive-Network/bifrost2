# @file         js_object.py - Wrapper Class for DCP JS Classes
#
# @author       Will Pringle <will@distributive.network>
# @date         June 2024

import asyncio
import pythonmonkey as pm


def create_js_class(name, js_class, props={}, aio_methods=[], aio_ctor=False):
    class AsyncIOMethods:
        def __init__(self, parent):
            self.parent = parent

        def __getattr__(self, name):
            js_attr = self.parent.js_ref[name]

            if name in aio_methods:
                return aio_run_wrapper(js_attr)

    def __init__(self, *args, **kwargs):
        if (aio_ctor):
            async_wrapped_ctor = aio_run_wrapper(pm.new(js_class))
            self.js_ref = asyncio.run(async_wrapped_ctor(*args, **kwargs))
        else:
            self.js_ref = pm.new(js_class)(*args, **kwargs)

        self.aio = AsyncIOMethods(self)

    def __getattr__(self, name):
        js_attr = self.js_ref[name]

        if (not callable(js_attr)):
            return js_attr

        def method(*args, **kwargs):
            if (name in aio_methods):
                aio_attr = getattr(self.aio, name)
                return asyncio.run(aio_attr(*args, **kwargs))

            return js_attr(*args, **kwargs)

        return method

    def __setattr__(self, name, value):
        if name == 'js_ref':
            object.__setattr__(self, name, value)
        else:
            self.js_ref[name] = value

    def __str__(self):
        return str(self.js_ref)

    props['__init__'] = __init__
    props['__getattr__'] = __getattr__
    props['__setattr__'] = __setattr__
    props['__str__'] = __str__
    new_class = type(name, (object,), props)

    return new_class


def aio_run_wrapper(leaky_async_fn):
    async def aio_fn(*args, **kwargs):
        return await leaky_async_fn(*args, **kwargs)
    return aio_fn

