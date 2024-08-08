from .initialization import make_init_fn 
import sys

# TODO: remove once patched in DCP (TODO: link MR)
# This is required since dcp-client looks for a __file__ attribute
if not hasattr(__import__("__main__"), '__file__'):
    setattr(__import__("__main__"), '__file__', 'severn::repl|ipython')

init = make_init_fn(sys.modules[__name__])

# clean up namespace
del sys
del js
del dry
del api
del initialization
del make_init_fn

__all__ = ['init']

