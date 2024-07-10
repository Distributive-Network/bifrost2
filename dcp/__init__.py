from .initialization import make_init_fn 
import sys

init = make_init_fn(sys.modules[__name__])

# clean up namespace
del sys
del js
del dry
del api
del initialization
del make_init_fn

__all__ = ['init']

