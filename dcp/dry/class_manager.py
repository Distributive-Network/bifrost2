import pythonmonkey as pm
from .. import js
from .. import api


class ClassRegistry:
    def __init__(self):
        self._list = []

    def _find(self, cmp):
        return next((c for c in self._list if cmp(c)), None)

    # TODO: this feels wrong, it's doing too many things. it should just add
    # classes to the registry... instead it also does the inheritance stuff. ):
    def add(self, bfclass):
        if base_class := api.inheritance_hooks.get(bfclass.__name__):
            bfclass = type(bfclass.__name__, (bfclass,), dict(base_class.__dict__))
        self._list.append(bfclass)
        return bfclass

    def find_from_js_instance(self, js_inst):
        return self._find(lambda c: js.utils.instanceof(js_inst, c.get_js_class()))

    def find_from_name(self, name):
        return self._find(lambda c: c.__name__ == name)

    def find_from_js_ctor(self, js_ctor):
        return self._find(lambda c: js.utils.equals(c.get_js_class(), js_ctor))

    def find(self, value):
        if isinstance(value, pm.JSFunctionProxy):
            return self.find_from_js_ctor(value)
        elif isinstance(value, pm.JSObjectProxy):
            return self.find_from_js_instance(value)
        elif isinstance(value, str):
            return self.find_from_name(value)

    def __str__(self):
        return str(self._list)

    def __repr__(self):
        return self.__str__()


reg = ClassRegistry()

