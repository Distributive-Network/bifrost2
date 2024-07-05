# NOTE TO SELF - have to load class reg before classes that use it

from .dry import make_dcp_class, class_manager, wrap_js_obj, aio_run_wrapper, blocking_run_wrapper
from . import js
from .api import compute_for as api_compute_for #TODO - we should handle compute for and inheritance in same place /:
import sys
from types import ModuleType as Module

import pythonmonkey as pm

# state
init_memo = None


def init(**kwargs) -> Module:
    global init_memo

    # no-op on multiple initializations
    if init_memo is not None:
        return init_memo

    # initialize dcp
    js.dcp_client['init'](**kwargs)
    init_memo = True

    # build dcp modules
    for name in pm.globalThis.dcp.keys():
        init_dcp_module(sys.modules[__name__], pm.globalThis.dcp[name], name)

    init_memo = sys.modules[__name__]
    return init_memo


def init_dcp_module(py_parent, js_module, js_name):
    underscore_name = f"{js_name.replace('-', '_')}"
    module_name = f"{py_parent.__name__}.{underscore_name}"
    module = Module(module_name)
    module.__file__ = f"<dynamically created bifrost2 module: {module_name}>"
    module._js = js_module
    sys.modules[module_name] = module

    # add the new module as a submodule of the root module
    setattr(py_parent, underscore_name, module)

    # wrap js elements of the cjs module
    for prop_name, prop_ref in js_module.items():
        if isinstance(prop_ref, pm.JSFunctionProxy):
            if js.utils.isclass(prop_ref):
                new_bfclass = class_manager.reg.find(prop_ref)
                if new_bfclass is None:
                    new_bfclass = make_dcp_class(prop_ref, name=prop_name)
                    new_bfclass = class_manager.reg.add(new_bfclass)

                setattr(module, prop_name, new_bfclass)

            else:
                setattr(module, prop_name, blocking_run_wrapper(prop_ref))

        # js object
        elif prop_ref is js.utils.PMDict:
            setattr(module, prop_name, wrap_js_obj(prop_ref))

        # py dict
        else:
            setattr(module, prop_name, prop_ref)


__all__ = ["init"]

