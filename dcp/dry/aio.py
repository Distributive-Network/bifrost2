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

# LOCAL PATCH (Python 3.14 compatibility -- credit: Tom Tang's diagnosis):
# nest_asyncio.apply() was previously called unconditionally here. Its
# monkey-patch doesn't propagate asyncio's "current task" context correctly
# under 3.14's changed internals, which breaks any aiohttp call using
# timeout= (including pythonmonkey's XMLHttpRequest-internal.py, which
# backs DCP's socket.io polling transport) with "RuntimeError: Timeout
# should be used inside a task" *before* the request is even sent --
# dcp-client reports this up the stack as the much more confusing
# "DCPError: no transports defined" (DCPC-1014). Confirmed independent of
# dcp with a minimal pythonmonkey+XMLHttpRequest repro (works fine under
# asyncio.run(), breaks only via this reentrant-loop patch). nest_asyncio's
# last release (1.6.0, Jan 2024) only ever claimed testing through Python
# 3.12.
#
# Fix: only apply the patch when a loop is ALREADY running in the current
# thread at import time -- i.e. only when reentrant run_until_complete()
# support is actually needed (Jupyter, a web server, a GUI app already
# running its own loop). A plain script importing dcp normally has no loop
# running yet at this point, never needed the patch in the first place, and
# now skips the code path that's broken on 3.14. Verified both branches:
# plain scripts (patch skipped, fixes 3.14) and inside a real Jupyter
# kernel via nbclient (patch still applies, notebook usage unaffected).
try:
    asyncio.get_running_loop()
    import nest_asyncio
    nest_asyncio.apply()
except RuntimeError:
    pass  # no loop already running in this thread; nothing to patch

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

