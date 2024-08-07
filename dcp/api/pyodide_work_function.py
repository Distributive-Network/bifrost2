"""
The BiFrost2 work function. Handles deserializing/serializing job data and running
the real (user provided) work function.

Author: Severn Lortie <severn@distributive.network>
Date: Aug 2024
"""

work_function_string = """
import numpy
import cloudpickle
import sys
from collections.abc import Iterator

def eval_function(function_string):
    def user_code_namespace():
        locals = {}
        clean_globals = {}
        allowed_global_keys = ["__name__", "__doc__", "__package__", "__loader__", "__spec__", "__annotations__", "__builtins__", "dcp"]
        for key in globals().keys():
            if key in allowed_global_keys:
                clean_globals[key] = globals()[key]
        exec(function_string, clean_globals, locals)
        return locals
    locals = user_code_namespace()
    function_name = next(iter(locals))
    return locals[function_name]

if "meta_arguments" not in globals():
    meta_arguments = []

if "argv_deserialized" not in globals():
    argv_deserialized = False

def bifrost2_setup():
    global meta_arguments
    global argv_deserialized

    if not len(meta_arguments):
        meta_arguments = sys.argv.pop()
    work_function_string = meta_arguments[0]

    user_work_function = eval_function(work_function_string)
    if len(meta_arguments) < 2:
        user_work_function()
        return

    serialized_serializers = meta_arguments[1]
    serializers = cloudpickle.loads(serialized_serializers)
    for serializer in serializers:
        serializer["interrogator"] = eval_function(serializer["interrogator"])
        serializer["serializer"]   = eval_function(serializer["serializer"])
        serializer["deserializer"] = eval_function(serializer["deserializer"])

    def serialize(value):
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

    def deserialize(value):
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
        allowed_serializer_names = [serializer["name"] for serializer in serializers]
        if serializer_name not in allowed_serializer_names:
            return value

        serializer = next((serializer for serializer in serializers if serializer["name"] == serializer_name), None)
        return serializer["deserializer"](value)

    if not argv_deserialized:
        for i in range(len(sys.argv)):
            arg = deserialize(sys.argv[i])
            sys.argv[i] = arg

    original_set_slice_handler = dcp.set_slice_handler
    def set_slice_handler(slice_handler):
        def slice_handler_deserialization_wrapper(serialized_datum):
            datum = deserialize(serialized_datum)
            result = slice_handler(datum)
            serialized_result = serialize(result)
            return serialized_result
        original_set_slice_handler(slice_handler_deserialization_wrapper)
    dcp.set_slice_handler = set_slice_handler
    user_work_function()
bifrost2_setup()
"""
