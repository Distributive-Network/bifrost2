import pythonmonkey as pm
from .. import js

# TODO: rename to class manager
# TODO: add stuff for api inheritance setup

class ClassRegistry:
    def __init__(self):
        self._list = []

    def _find(self, cmp):
        return next((c for c in self._list if cmp(c)), None)

    def _replace_or_register(self, new_class, cmp):
        existing = self._find(cmp)
        if existing:
            self._list[self._list.index(existing)] = new_class
        else:
            self.register(new_class)

    def register(self, bfclass):
        # TODO: should probably check for api inheritance here?
        self._list.append(bfclass)

    def replace_from_name(self, name, new_class):
        self._replace_or_register(new_class, lambda c: c.__name__ == name)

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


registry = ClassRegistry()

