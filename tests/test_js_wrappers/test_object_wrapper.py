import unittest
import pythonmonkey as pm
from dcp.initialization import _wrap_js

JSCookieJar = pm.eval("""
class CookieJar
{
  constructor(...cookies)
  {
    this.cookies = []
    for (var cookie of cookies) {
      this.addCookie(cookie)
    }
  }
  addCookie(cookie)
  {
    this.cookies.push(cookie)
  }
  topCookie()
  {
    return this.cookies.at(-1)
  }
}
CookieJar;
""")

JSCookie = pm.eval("""
class Cookie
{
  constructor(flavor)
  {
    this.flavor = flavor
  }
}
Cookie;
""")

PyCookie = _wrap_js("Cookie", JSCookie)
PyCookieJar = _wrap_js("CookieJar", JSCookieJar)


class TestObjectUnwrapping(unittest.TestCase):

    def test_primitive_args_func(self):
      # ensure wrapped functions return correct primitives
      bf_fn = _wrap_js('test_fn', pm.eval('(x) => x'))
      self.assertEqual(bf_fn("Hello"), "Hello")
      self.assertEqual(type(bf_fn(7)), float)

    def test_bifrost_args_func(self):
      # object must be unwrapped before being passed to pm
      bf_fn = _wrap_js('test_fn', pm.eval('(cookie) => cookie instanceof Cookie'))
      cookie = PyCookie('chocolate chip')
      self.assertTrue(bf_fn(cookie))

      # returned object must be wrapped
      bf_fn = _wrap_js('test_fn', pm.eval('(cookie) => cookie'))
      cookie = PyCookie('chocolate chip')
      self.assertEqual(type(bf_fn(cookie)), PyCookie)

    def test_primitive_args_ctor(self):

      cookie = PyCookie('chocolate chip')

      # Verify object is wrapped properly
      self.assertEqual(type(cookie), PyCookie)
      self.assertTrue(hasattr(cookie, 'js_ref'))
      self.assertEqual(cookie.flavor, 'chocolate chip')

      # Verify underlying object is the right class
      self.assertTrue(pm.eval('(cookie) => cookie instanceof Cookie')(cookie.js_ref))

    def test_bifrost_args_ctor(self):

      cookie_one = PyCookie('chocolate chip')
      cookie_two = PyCookie('oatmeal')

      # Constructors that take bf2 objects must unwrap them
      py_jar = PyCookieJar(cookie_one, cookie_two)

      # Attributes and obj need to be the correct type when obtained in underlying js
      js_fn = pm.eval('(jar) => jar instanceof CookieJar && jar.topCookie() instanceof Cookie')
      self.assertTrue(js_fn(py_jar.js_ref))

    def test_bifrost_args_method(self):

      py_jar = PyCookieJar()

      # bf2 objects passed as function arguments must be unwrapped
      py_jar.addCookie( PyCookie('chocolate chip') )
      js_fn = pm.eval('(jar) => jar.topCookie() instanceof Cookie')

      self.assertTrue(js_fn(py_jar.js_ref))


if __name__ == '__main__':
    unittest.main()
