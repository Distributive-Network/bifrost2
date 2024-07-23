import pythonmonkey as pm
from .. import dry
from .. import js 

def compute_for_maker(Job):
    def compute_for(*args, **kwargs):
        return Job(*args, **kwargs)
    return compute_for

