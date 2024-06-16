import pythonmonkey as pm

class ClassRegistry:
    def __init__(self):
        self._list = []

    def register(self, bfclass):
        self._list.append(bfclass)

    def find(self, needle, cmp):
        for bfclass in self._list:
            if cmp(needle, bfclass):
                return bfclass
        return None

    def find_class_from_js_instance(self, js_instance):
        js_instanceof = pm.eval('(i,c) => i instanceof c')
        return self.find(js_instance, lambda i,c : js_instanceof(i, c.js_ref))

    def find_class_from_name(self, name):
        return self.find(name, lambda name,c : name == c.__name__)

    def __str__(self):
        return str(self._list)

    def __repr__(self):
        return self.__str__()

registry = ClassRegistry()

import pdb; pdb.set_trace() # need to test with real js class / bfclass

