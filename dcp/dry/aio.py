"""
Manage asynchronous functions involving the PythonMonkey event loop.

Functions:
- asyncify(leaky_async_fn): make a leaky PM JS promise not leak.
- blockify(async_fn): make a leaky PM JS promise not leak and block.

Properties:
- loop: the single event loop used for all PythonMonkey ev loop interactions.

Author: Will Pringle <will@distributive.network>
Date: June 2024
"""
import asyncio
import inspect

# TODO: should we always do this? Is this user's responsibility?
import nest_asyncio
nest_asyncio.apply()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def asyncify(leaky_async_fn):
    # leaky_asyn_fn may not return a corotine but still require an event loop
    async def aio_fn(*args, **kwargs):
        return_value = leaky_async_fn(*args, **kwargs)
        if inspect.isawaitable(return_value):
            return await return_value

        return return_value
    return aio_fn


def blockify(async_fn):
    def blocking_fn(*args, **kwargs):
        return loop.run_until_complete(asyncify(async_fn)(*args, **kwargs))
    return blocking_fn

