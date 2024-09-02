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


def _wrap_js(prop_name, prop_ref):
    """Determines what the js ref is, if class add to class registry."""
    if isinstance(prop_ref, pm.JSFunctionProxy):
        # class
        if js.utils.isclass(prop_ref):
            new_bfclass = class_manager.reg.find(prop_ref)
            if new_bfclass is None:
                new_bfclass = class_manager.wrap_class(prop_ref, name=prop_name)
                new_bfclass = class_manager.reg.add(new_bfclass)
            return new_bfclass

        # function
        else:
            def fn_wrapper(*args, **kwargs):
                for arg in args:
                    if js.utils.throws_in_pm(arg):
                        raise Exception(f'{type(arg)} is not supported in PythonMonkey')
                ret_val = aio.blockify(prop_ref)(*args, **kwargs)
                return _wrap_js('dynamically_accessed_property', ret_val)
            return fn_wrapper

    elif isinstance(prop_ref, pm.JSObjectProxy):
        return class_manager.wrap_obj(prop_ref)

    elif isinstance(prop_ref, pm.null.__class__):
        return None

    return prop_ref


def init_dcp_module(py_parent, js_module, js_name):
    """Builds the dcp module and sub modules"""
    underscore_name = f"{js_name.replace('-', '_')}"
    module_name = f"{py_parent.__name__}.{underscore_name}"

    # TODO this is quite ugly
    # TODO why don't we pass the js module to it so we can use it as a proxy?
    BfDyn = class_manager.make_new_class(lambda *args, **kwargs: js_module, 'Module', mutate_js=False)
    BfDyn = type(Module.__name__, (Module,), dict(BfDyn.__dict__))
    module = BfDyn()

    module.__file__ = f"<dynamically created bifrost2 module: {module_name}>"
    module._js = js_module
    sys.modules[module_name] = module

    # add the new module as a submodule of the root module
    setattr(py_parent, underscore_name, module)

    for prop_name, prop_ref in js_module.items():
        setattr(module, prop_name, _wrap_js(prop_name, prop_ref))


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

        # XXX apply dcp-client hacks XXX
        # Hacks should be removed as quickly as possible
        # You must include a dcp-client MR which fixes the hack

        # dcp-client getProcessPath hack
        # TODO remove once https://gitlab.com/Distributed-Compute-Protocol/dcp/-/merge_requests/2866 lands in prod
        pm.eval("""
        globalThis.dcp['dcp-env'].getProcessPath = function bf2_hack_dcpEnv$$getProcessPath()
        {
          return globalThis.python.eval('__import__("__main__")')['__file__'];
        }
        """)

        # build dcp modules
        for name in pm.globalThis.dcp.keys():
            init_dcp_module(dcp_module, pm.globalThis.dcp[name], name)

        # add some api top level imports
        setattr(dcp_module, "compute_for", api.compute_for_maker(class_manager.reg.find('Job')), )
        setattr(dcp_module, "compute_do", api.compute_do_maker(class_manager.reg.find('Job')), )
        setattr(dcp_module, "JobFS", api.JobFS, )


        INIT_MEMO = dcp_module
        return INIT_MEMO

    return init

