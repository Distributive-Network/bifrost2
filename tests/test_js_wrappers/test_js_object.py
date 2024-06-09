import unittest
import asyncio
import inspect
import pythonmonkey as pm
from dcp.js_wrappers import create_js_class as make_class


class TestJSObjectFunction(unittest.TestCase):
    def test_simple_class(self):
        JSRect = pm.eval("""
class Rectangle
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
Rectangle;
        """)

        PyRect = make_class('PyRect', JSRect)
        my_rect = PyRect(2, 7)

        self.assertTrue(my_rect.area == 2 * 7)
        self.assertTrue(my_rect.calcArea() == 2 * 7)
        return True

    def test_aio_methods(self):
        MyClass = pm.eval("""
class Coffee
{
  // brews & returns how long it took to brew
  async brew(ms)
  {
    return new Promise((resolve) => {
        setTimeout(() => resolve(ms), ms);
    });
  }
}
Coffee;
        """)

        Coffee = make_class('Coffee', MyClass, aio_methods=["brew"])
        cup_of_joe = Coffee()

        # should be able to sleep synchronously
        resp = cup_of_joe.brew(11)
        self.assertTrue(resp, 11)

        # should be able to asynchronously await .brew as well
        resp = cup_of_joe.aio.brew(13)
        self.assertTrue(inspect.isawaitable(resp))
        self.assertTrue(asyncio.run(resp), 13)

    def test_aio_ctor(self):

        Human = pm.eval("""
class Human
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
Human;
        """)

        HumanPy = make_class('Human', Human, aio_ctor=True)

        # verify constructor promise has been resolved
        baby = HumanPy('Joe')
        self.assertTrue(not inspect.isawaitable(baby))
        self.assertTrue(baby.name == 'Joe')


if __name__ == '__main__':
    unittest.main()

