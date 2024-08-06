"""
Responsible for serializing Job arguments and input data.

Author: Severn Lortie <severn@distributive.network>
Date: July 2024
"""


import cloudpickle
import dill
import pythonmonkey as pm
from ..js import utils
from collections.abc import Iterator

class Serializers:
    def __init__(self):
        def numpy_save_interrogate(value):
            import numpy as np
            return isinstance(value, np.ndarray)
        def numpy_save_serialize(value):
            import numpy as np
            from io import BytesIO
            byte_buffer = BytesIO()
            np.save(byte_buffer, value)
            buffer.seek(0)
            return buffer.read()
        def numpy_save_deserialize(value):
            import numpy as np
            from io import BytesIO
            byte_buffer = BytesIO()
            buffer.seek(0)
            return np.load(value)
        
        def pickle_interrogate(value):
            return True
        def pickle_serialize(value):
            import cloudpickle
            return cloudpickle.dumps(value)
        def pickle_deserialize(value):
            import cloudpickle
            return cloudpickle.loads(value)

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

    # TODO: This code is duplicated across the job work function. See if possible to use this in both places
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
                serialized_value_bytes = serializer["serializer"](value)
                serialized_serializer_name_bytes = serializer["name"].encode('utf-8')
                serializer_name_length = len(serializer["name"])
                serializer_name_length_byte = bytearray(serializer_name_length.to_bytes(1, byteorder='big'))
                serialized_serializer_name_byte_array = bytearray(serialized_serializer_name_bytes)
                serialized_value_byte_array = bytearray(serialized_value_bytes)
                return serializer_name_length_byte + serialized_serializer_name_byte_array + serialized_value_byte_array

    # TODO: This code is duplicated across the job work function. See if possible to use this in both places
    def deserialize(self, value):
        if isinstance(value, memoryview):
            value = bytearray(value.tobytes())
        elif not isinstance(value, bytearray):
            return value
        serializer_name_length = value[0]
        if serializer_name_length > len(value):
            return value
        name_start_idx = 1
        name_end_idx = serializer_name_length + 1
        serializer_name_bytes = value[name_start_idx:name_end_idx]
        del value[0:name_end_idx]
        serializer_name = serializer_name_bytes.decode('utf-8')
        allowed_serializer_names = [serializer["name"] for serializer in self.serializers]
        if serializer_name not in allowed_serializer_names:
            return value

        serializer = next((serializer for serializer in self.serializers if serializer["name"] == serializer_name), None)
        return serializer["deserializer"](value)

    def convert_to_arguments(self):
        serialized_serializers = []
        for serializer in self.serializers:
            serialized_serializers.append({
                "name": serializer["name"],
                "interrogator": dill.source.getsource(serializer["interrogator"], lstrip=True),
                "serializer":   dill.source.getsource(serializer["serializer"], lstrip=True),
                "deserializer": dill.source.getsource(serializer["deserializer"], lstrip=True)
            })
        return bytearray(cloudpickle.dumps(serialized_serializers))

    def empty(self):
        return len(self.serializers) < 1



