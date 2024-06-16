import sys
from types import ModuleType as Module

import pythonmonkey as pm

from .sanity import sanity
from .js import dcp_client as dcp_js

# state
init_memo = None


def init(**kwargs):
    global init_memo

    # no-op on multiple initializations
    if init_memo is not None:
        return init_memo

    # initialize dcp
    dcp_js['init'](**kwargs)
    init_memo = True

    # build dcp modules
    for name in pm.globalThis.dcp.keys():
        module_tree(sys.modules[__name__], pm.globalThis.dcp[name], name)

    print(dir(sys.modules[__name__]))


def module_tree(py_parent, js_child, js_name):
    underscore_name = f"{js_name.replace('-', '_')}"
    module_name = f"{py_parent.__name__}.{underscore_name}"
    module = Module(module_name)
    module.__file__ = f"<dynamically created {module_name}>"
    module._js = js_child
    sys.modules[module_name] = module
    setattr(py_parent, underscore_name, module)


__all__ = ["init", "sanity"]

