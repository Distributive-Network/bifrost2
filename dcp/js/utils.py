import pythonmonkey as pm

PMDict = pm.eval('x = {}; x').__class__


def isclass(ref):
    # TODO: come up with better way to determine if class..
    # if a js object prototype has more than one own property, it is a class
    proto_own_prop_names = pm.eval(
        'x=>(x?.prototype ? Object.getOwnPropertyNames(x?.prototype) : [])')
    return len(proto_own_prop_names(ref)) > 1


def class_name(JSClass):
    return pm.eval('x => x.name')(JSClass)


def instanceof(js_instance, JSClass):
    return pm.eval('(i,c) => i instanceof c')(js_instance, JSClass)


def obj_ctor(js_instance):
    return pm.eval('x => x.constructor')(js_instance)


def equals(a, b):
    return pm.eval('(a,b) => a === b')(a, b)

def throws_in_pm(value):
    """
    Some values such as multi dimensional numpy arrays aren't supported in PM.
    """
    try:
        pm.eval('()=>{}')(value)
    except:
        return True
    return False

