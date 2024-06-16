import asyncio
import inspect

def aio_run_wrapper(leaky_async_fn):
    # leaky_asyn_fn may not return a corotine but still require an event loop
    async def aio_fn(*args, **kwargs):
        return_value = leaky_async_fn(*args, **kwargs)
        if inspect.isawaitable(return_value):
            return await return_value

        print("AIO_RUN_WRAPPER_CASE_HIT_WHERE_FN_NOT_RETURN_CORO") # TODO???
        return return_value
    return aio_fn

def blocking_run_wrapper(async_fn):
    def blocking_fn(*args, **kwargs):
        return asyncio.run(aio_run_wrapper(async_fn)(*args, **kwargs))
    return blocking_fn

