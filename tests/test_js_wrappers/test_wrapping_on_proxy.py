import unittest
import pythonmonkey as pm
from dcp import dry

class TestWrapperOnProxy(unittest.TestCase):
    def test_setting_self(self):
        JSClass = pm.eval("class SomeClass { constructor(a,b) { this.sev = a + b}}; SomeClass")
        PyClass = dry.class_manager.wrap_class(JSClass)

        class SubClass(PyClass):
            def __init__(self):
                super().__init__()
                self._wrapper_set_attribute('some_attr', 3)

        instance = SubClass()
        self.assertEqual(instance.some_attr, 3)
        self.assertTrue(instance.js_ref['some_attr'] is None)

if __name__ == '__main__':
    unittest.main()

