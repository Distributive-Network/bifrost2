from .initialization import make_init_fn 
import sys

init = make_init_fn(sys.modules[__name__])

__all__ = ['init']

