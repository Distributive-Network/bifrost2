"""
Store dynamically created classes in a registry for later use.

Classes:
- ClassRegistry().

Author: Will Pringle <will@distributive.network>
Date: June 2024
"""

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
        """Registers a new BF2 Wrapper class, replaces with api subclasses."""
        if sub_class_maker := api.sub_classes.get(bfclass.__name__):
            bfclass = sub_class_maker(bfclass)
        self._list.append(bfclass)
        return bfclass

    def find_from_js_instance(self, js_inst):
        def cmp(c):
            js_inst_is_instance = js.utils.instanceof(js_inst, c.get_js_class())

            instance_cname = js.utils.class_name(js.utils.obj_ctor(js_inst))
            class_cname = js.utils.class_name(c.get_js_class())

            return js_inst_is_instance and instance_cname == class_cname
        return self._find(cmp)

    def find_from_name(self, name):
        return self._find(lambda c: c.__name__ == name)

    def find_from_js_ctor(self, js_ctor):
        return self._find(lambda c: js.utils.equals(c.get_js_class(), js_ctor))

    def find(self, value):
        """Finds the corresponding BF2 Wrapper class from the registry."""
        if isinstance(value, pm.JSFunctionProxy):
            return self.find_from_js_ctor(value)
        if isinstance(value, pm.JSObjectProxy):
            return self.find_from_js_instance(value)
        if isinstance(value, str):
            return self.find_from_name(value)
        return None

    def __str__(self):
        return str(self._list)

    def __repr__(self):
        return self.__str__()

