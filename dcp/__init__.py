# NOTE TO SELF - have to load class registry before classes that use it

from .dry import make_dcp_class, class_registry, wrap_js_obj, aio_run_wrapper, blocking_run_wrapper
from .js import dcp_client as dcp_js
from .api import compute_for as api_compute_for
from .api import Job as api_Job
from .sanity import sanity
import sys
from types import ModuleType as Module

import pythonmonkey as pm
PMDict = pm.eval('x={};x').__class__
proto_own_prop_names = pm.eval(
    'x=>(x?.prototype ? Object.getOwnPropertyNames(x?.prototype) : [])')


# state
init_memo = None


def init(**kwargs) -> Module:
    global init_memo

    # no-op on multiple initializations
    if init_memo is not None:
        return init_memo

    # initialize dcp
    dcp_js['init'](**kwargs)
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
            # TODO: come up with better way to determine if class...
            if len(proto_own_prop_names(prop_ref)) > 1:
                new_bfclass = make_dcp_class(prop_ref, name=prop_name)

                # TODO - need to make this more prorgramatic and dry - maybe this belongs in a class manager..? TODO XXX TODO XXX
                if prop_name == 'Job':
                    new_bfclass = type('Job', (new_bfclass,), dict(api_Job.__dict__))

                class_registry.register(new_bfclass)
                setattr(module, prop_name, new_bfclass)

            # TODO: check if the function is known to return a promise...
            else:
                setattr(module, prop_name, blocking_run_wrapper(prop_ref))

        # js object
        elif prop_ref is PMDict:
            setattr(module, prop_name, wrap_js_obj(prop_ref))

        # py dict
        else:
            setattr(module, prop_name, prop_ref)


__all__ = ["init", "sanity"]

