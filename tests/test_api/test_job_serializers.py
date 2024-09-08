import unittest
import numpy as np
import types
import dcp

dcp.init()
from dcp.api import job_serializers as js

def helper_shallow_cmp(self, left, right):
    """Best effort to compare two values shallowly."""
    self.assertIsInstance(left, type(right))

    if isinstance(left, (list, tuple)):
        self.assertEqual(list(left), list(right))

    elif isinstance(left, set):
        self.assertEqual(left, right)

    elif isinstance(left, dict):
        self.assertEqual(set(left.keys()), set(right.keys()))
        self.assertEqual(set(left.values()), set(right.values()))

    elif isinstance(left, (bytes, bytearray)):
        self.assertEqual(bytes(left), bytes(right))

    elif isinstance(left, types.LambdaType):
        self.assertEqual(left.__code__.co_code, right.__code__.co_code)

    elif isinstance(left, np.ndarray):
        # Compare numpy arrays: check shape, dtype, and content
        self.assertEqual(left.shape, right.shape)
        self.assertEqual(left.dtype, right.dtype)
        self.assertTrue(np.array_equal(left, right), "Numpy arrays are not equal")

    else:
        self.assertEqual(left, right)


class TestJobSerializers(unittest.TestCase):
    def test_default_serialize_and_deserialize_basic(self):
        job = dcp.compute_for([], '')

        values = [
            123,
            3.14,
            'some string',
            True,
            False,
            1 + 2j,
            [1,2,3],
            (1,2,3),
            {1,2,3 },
            { 'key': 'value' },
            b'some bytes',
            bytearray('some bytes in a bytearray', 'utf-8'),
            lambda x: x,
            None,
        ]

        serialized_vals = []
        for val in values:
            serialized_vals.append(js.serialize(val, job.serializers))

        des_vals = []
        for val in serialized_vals:
            des_vals.append(js.deserialize(val, job.serializers))

        for i in range(len(values)):
            helper_shallow_cmp(self, values[i], des_vals[i])

    def test_default_serialize_and_deserialize_numpy_array(self):
        job = dcp.compute_for([], '')

        values = [
            np.array([]),
            np.array([1, 2, 3, 4]),
            np.array([[1, 2], [3, 4]]),
            np.array([[[1], [2]], [[3], [4]]]),
            np.array([1.1, 2.2, 3.3], dtype=np.float64),
            np.array([True, False, True], dtype=np.bool_),
            np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')]),
            np.ma.array([1, 2, 3], mask=[False, True, False]),
            np.array([1, 2, 3, 4])[1:3],
            np.random.rand(2, 3, 4),
            np.array([1 + 1j, 2 + 2j], dtype=np.complex128),

            np.arange(10),
            np.linspace(0, 1, 5),
            np.random.randint(0, 10, (2, 2)),
            np.random.normal(size=(2, 2)),
            np.zeros((2, 2)),
            np.ones((3, 3)),
            np.eye(3),
            np.recarray((2,), dtype=[('col1', 'int32'), ('col2', 'float32')]),
        ]

        serialized_vals = []
        for val in values:
            serialized_vals.append(js.serialize(val, job.serializers))

        des_vals = []
        for val in serialized_vals:
            des_vals.append(js.deserialize(val, job.serializers))


        for i in range(len(values)):
            helper_shallow_cmp(self, values[i], des_vals[i])

if __name__ == '__main__':
    unittest.main()

