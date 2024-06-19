import pythonmonkey as pm


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
        self._list.append(bfclass)

    def replace_from_name(self, name, new_class):
        self._replace_or_register(new_class, lambda c: c.__name__ == name)

    def find_from_js_instance(self, js_inst):
        js_instanceof = pm.eval('(i,c) => i instanceof c')
        return self._find(lambda c: js_instanceof(js_inst, c.get_js_class()))

    def find_from_name(self, name):
        return self._find(lambda c: c.__name__ == name)

    def __str__(self):
        return str(self._list)

    def __repr__(self):
        return self.__str__()


registry = ClassRegistry()

