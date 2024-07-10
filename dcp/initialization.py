"""
Dynamically initialize the dcp mode.

Traverses through the dcp-client CJS modules to generate the dcp Python module
and build a registry of classes along the way which are automatically wrapped.

Author: Will Pringle <will@distributive.network>
Date: June 2024
"""

import sys
from types import ModuleType as Module
from typing import Callable
import pythonmonkey as pm
from .dry import class_manager, aio
from . import js
from . import api

# state
INIT_MEMO = None


def init_dcp_module(py_parent, js_module, js_name):
    """builds the dcp module and class registry"""
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
                    new_bfclass = class_manager.wrap_class(prop_ref, name=prop_name)
                    new_bfclass = class_manager.reg.add(new_bfclass)

                setattr(module, prop_name, new_bfclass)

            else:
                setattr(module, prop_name, aio.blockify(prop_ref))

        # js object
        elif prop_ref is js.utils.PMDict:
            setattr(module, prop_name, class_manager.wrap_obj(prop_ref))

        # py dict
        else:
            setattr(module, prop_name, prop_ref)


def make_init_fn(dcp_module) -> Callable:
    """Creates the init function to return."""
    def init(**kwargs) -> Module:
        global INIT_MEMO

        # no-op on multiple initializations
        if INIT_MEMO is not None:
            return INIT_MEMO

        # initialize dcp
        js.dcp_client['init'](**kwargs)
        INIT_MEMO = True

        # build dcp modules
        for name in pm.globalThis.dcp.keys():
            init_dcp_module(dcp_module, pm.globalThis.dcp[name], name)

        # add some api top level imports
        setattr(dcp_module, "compute_for", api.compute_for_maker(), )

        INIT_MEMO = dcp_module
        return INIT_MEMO

    return init

