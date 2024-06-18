import unittest
import pythonmonkey as pm
from dcp import dry
from dcp.dry import make_dcp_class as make_class
from dcp.dry import wrap_js_obj

JSRectangle = pm.eval("""
class JSRectangle
{
  constructor(height, width)
  {
    this.height = height;
    this.width = width;
  }
  get area()
  {
    return this.calcArea();
  }
  calcArea()
  {
    return this.height * this.width;
  }
}
JSRectangle;
""")

JSCoffee = pm.eval("""
class JSCoffee
{
  // brews & returns how long it took to brew
  async brew(ms)
  {
    return new Promise((resolve) => {
        setTimeout(() => resolve(ms), ms);
    });
  }
}
JSCoffee;
""")

JSHuman = pm.eval("""
class JSHuman
{
    // births a baby, has to be awaited until born
    constructor(name)
    {
        this.name = name;
        const that = this;
        return new Promise((resolve) => {
            setTimeout(() => resolve(that), 9);
        });
    }
}
JSHuman;
""")

PyRect = make_class(JSRectangle)
PyCoff = make_class(JSCoffee)
PyHuma = make_class(JSHuman)
                                    
class TestClassRegistry(unittest.TestCase):
    def test_adding_and_retrieval(self):
        dry.class_registry.register(PyRect)
        dry.class_registry.register(PyCoff)
        dry.class_registry.register(PyHuma)

        # retrieval by JS Class name
        Class = dry.class_registry.find_from_name('JSHuman')
        self.assertTrue(Class.__name__, 'JSHuman')

        # retrieval by JS Class instance
        js_inst = pm.new(JSRectangle)(7,11)
        Class = dry.class_registry.find_from_js_instance(js_inst)
        self.assertTrue(Class.__name__, 'JSRectangle')
        return True

    def test_baseclassing_from_retrieval(self):
        pass

    def test_replacement(self):
        pass

if __name__ == '__main__':
    unittest.main()

