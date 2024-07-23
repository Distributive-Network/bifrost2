"""
Responsible for serializing Job arguments and input data.

Author: Severn Lortie <severn@distributive.network>
Date: July 2024
"""

import numpy as np
import pickle
from io import BytesIO

class Serializers:
    def __init__(self):
        def numpy_save_interrogate(value):
            return isinstance(value, np.ndarray)
        def numpy_save_serialize(value):
            byte_buffer = BytesIO()
            np.save(byte_buffer, value)
            buffer.seek(0)
            return buffer.read()
        def numpy_save_deserialize(value):
            byte_buffer = BytesIO()
            buffer.seek(0)
            return numpy.load(value)
        
        def pickle_interrogate(value):
            return True
        def pickle_serialize(value):
            return pickle.dumps(value)
        def pickle_deserialize(value):
            return pickle.loads(value)

        self.serializers = [
            {
                "name": "numpy-save",
                "interrogator": numpy_save_interrogate,
                "serializer": numpy_save_serialize,
                "deserializer": numpy_save_deserialize,
            },
            {
                "name": "pickle",
                "interrogator": pickle_interrogate,
                "serializer": pickle_serialize,
                "deserializer": pickle_deserialize,
            },
        ]

    def validate_serializers(self):
        required_keys = ['name', 'interrogator', 'serializer', 'deserializer']
        for i in range(len(self.serializers)):
            serializer = self.serializers[i]
            missing_keys = [key for key in required_keys if key not in serializer]
            if len(missing_keys) > 0:
                raise TypeError(f"Serializer at index {i} is missing keys: {missing_keys}")
            if len(serializer["name"]) > 256:
                raise TypeError(f"Serializer at index {i} has name '{serializer.name}' which exceeds 256 characters")

    def serialize(self, value):
        class IteratorWrapper:
            def __init__(self, iterator):
                self.iterator = iterator

            def __iter__(self):
                return self

            def __next__(self):
                value = next(self.iterator)
                return serialize(value)

        primitive_types = (int, float, bool, str, bytes)
        if isinstance(value, primitive_types):
            return value
        super_range_object = pm.eval("globalThis.dcp['range-object'].SuperRangeObject")
        if utils.instanceof(value, super_range_object):
            return value
        if isinstance(value, Iterator):
            return IteratorWrapper(value)

        for serializer in self.serializers:
            if serializer["interrogator"](value):
                serialized_value_bytes = serializer["serialize"](value)
                serialized_serializer_name_bytes = serializer["name"].encode('utf-8')
                serialized_serializer_name_byte_array = bytearray(serialized_serializer_name_bytes)
                serialized_value_byte_array = bytearray(serialized_value_bytes)
                return serialized_serializer_name_byte_array + serialized_value_byte_array





