import pythonmonkey as pm
from .. import dry
from .. import js 

def compute_for_maker():
    def compute_for(*args, **kwargs):
        compute_for_js = pm.eval("globalThis.dcp.compute.for")
        ret_val = dry.aio.blockify(compute_for_js)(*args, **kwargs)
        return dry.class_manager.wrap_obj(ret_val)
    return compute_for

