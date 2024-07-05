import unittest
import pythonmonkey as pm
from dcp import dry
from dcp.dry import make_dcp_class as make_class

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
    def test_monolithic_add_retrieve(self):
        def test_adding_and_retrieval():
            dry.class_manager.reg.add(PyRect)
            dry.class_manager.reg.add(PyCoff)
            dry.class_manager.reg.add(PyHuma)

            # retrieval by JS Class name
            Class = dry.class_manager.reg.find_from_name('JSHuman')
            self.assertTrue(Class.__name__, 'JSHuman')

            # retrieval by JS Class instance
            js_inst = pm.new(JSRectangle)(7, 11)
            Class = dry.class_manager.reg.find_from_js_instance(js_inst)
            self.assertTrue(Class.__name__, 'JSRectangle')

        def test_baseclassing_from_retrieval():
            class PyRect2(dry.class_manager.reg.find_from_name('JSRectangle')):
                def __str__(self):
                    return "changed"

                def area(self):
                    return self.calcArea() * 100

            my_inst = PyRect2(3, 13)

            self.assertEqual(str(my_inst), "changed")       # new
            self.assertEqual(my_inst.calcArea(), 3 * 13)    # existing
            self.assertEqual(my_inst.area(), 3 * 13 * 100)  # overwritten

        test_adding_and_retrieval()
        test_baseclassing_from_retrieval()


if __name__ == '__main__':
    unittest.main()

