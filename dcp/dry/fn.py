import asyncio
import inspect
from . import classes

# this CAN'T LIVE HERE!!! TODO XXX but temporarily putting it here
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def aio_run_wrapper(leaky_async_fn):
    # leaky_asyn_fn may not return a corotine but still require an event loop
    async def aio_fn(*args, **kwargs):
        return_value = leaky_async_fn(*args, **kwargs)
        if inspect.isawaitable(return_value):
            return await return_value

        # TODO: check class registry if it should be wrapped instance
        # if obj is py obj
            # find from ref
            # if not found
                # register it as new class
            # return the new instance of that class with the ref

        return return_value
    return aio_fn


def blocking_run_wrapper(async_fn):
    def blocking_fn(*args, **kwargs):
        return loop.run_until_complete(aio_run_wrapper(async_fn)(*args, **kwargs))
    return blocking_fn

