"""
Responsible for serializing Job arguments and input data.

Author: Severn Lortie <severn@distributive.network>
Date: July 2024
"""

import cloudpickle
import dill
from collections.abc import Iterator

def numpy_save_interrogate(value):
    import numpy as np
    return isinstance(value, np.ndarray)
def numpy_save_serialize(value) -> bytes:
    import numpy as np
    from io import BytesIO
    byte_buffer = BytesIO()
    np.save(byte_buffer, value)
    byte_buffer.seek(0)
    return byte_buffer.read()
def numpy_save_deserialize(value: bytes):
    import numpy as np
    from io import BytesIO
    byte_buffer = BytesIO(value)
    byte_buffer.seek(0)  # Reset the buffer position
    return np.load(byte_buffer)

def pickle_interrogate(value):
    return True
def pickle_serialize(value):
    import cloudpickle
    return cloudpickle.dumps(value)
def pickle_deserialize(value):
    import cloudpickle
    return cloudpickle.loads(value)

default_serializers = [
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

def validate_serializers(serializers):
    required_keys = ['name', 'interrogator', 'serializer', 'deserializer']
    for i in range(len(serializers)):
        serializer = serializers[i]
        missing_keys = [key for key in required_keys if key not in serializer]
        if len(missing_keys) > 0:
            raise TypeError(f"Serializer at index {i} is missing keys: {missing_keys}")
        if len(serializer["name"]) > 256:
            raise TypeError(f"Serializer at index {i} has name '{serializer.name}' which exceeds 256 characters")

def serialize(value, serializers):
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
    if isinstance(value, Iterator):
        return IteratorWrapper(value)

    for serializer in serializers:
        if serializer["interrogator"](value):
            serialized_value_bytes = serializer["serializer"](value)
            serialized_serializer_name_bytes = serializer["name"].encode('utf-8')
            serializer_name_length = len(serializer["name"])
            serializer_name_length_byte = bytearray(serializer_name_length.to_bytes(1, byteorder='big'))
            serialized_serializer_name_byte_array = bytearray(serialized_serializer_name_bytes)
            serialized_value_byte_array = bytearray(serialized_value_bytes)
            return serializer_name_length_byte + serialized_serializer_name_byte_array + serialized_value_byte_array

def deserialize(serialized_value, serializers):
    if isinstance(serialized_value, memoryview):
        value = bytearray(serialized_value.tobytes())
    elif not isinstance(serialized_value, bytearray):
        return serialized_value
    else:
        value = serialized_value.copy()
    serializer_name_length = value[0]
    if serializer_name_length > len(value):
        return serialized_value
    name_start_idx = 1
    name_end_idx = serializer_name_length + 1
    serializer_name_bytes = value[name_start_idx:name_end_idx]
    del value[0:name_end_idx]
    serializer_name = serializer_name_bytes.decode('utf-8')
    allowed_serializer_names = [serializer["name"] for serializer in serializers]
    if serializer_name not in allowed_serializer_names:
        return serialized_value

    serializer = next((serializer for serializer in serializers if serializer["name"] == serializer_name), None)
    return serializer["deserializer"](value)

def convert_serializers_to_arguments(serializers):
    stringified_serializers = []
    for serializer in serializers:
        stringified_serializers.append({
            "name": serializer["name"],
            "interrogator": dill.source.getsource(serializer["interrogator"], lstrip=True),
            "serializer":   dill.source.getsource(serializer["serializer"], lstrip=True),
            "deserializer": dill.source.getsource(serializer["deserializer"], lstrip=True)
        })
    serialized_serializers = bytearray(cloudpickle.dumps(stringified_serializers))
    return serialized_serializers

