import pythonmonkey as pm
import pickle
from ..js import utils
from collections.abc import Iterator
from types import FunctionType
import urllib.parse


def job_maker(super_class):
    class Job(super_class):
        def __init__(self, *args, **kwargs):
            super.__init__(*args, **kwargs)
            self.work_function = args[0]

        def exec(self, *args, **kwargs):
            def validateSerializers():
                required_keys = ['name', 'interrogator', 'serializer', 'deserializer']
                for i in range(len(self.serializers)):
                    serializer = self.serializers[i]
                    missing_keys = [key for key in required_keys if key not in serializer]
                    if len(missing_keys) > 0:
                        raise TypeError(f"Serializer at index {i} is missing keys: {missing_keys}")
                    if len(serializer.name) > 256:
                        raise TypeError(f"Serializer at index {i} has name '{serializer.name}' which exceeds 256 characters")
            validateSerializers()

            class IteratorWrapper:
                def __init__(self, iterator):
                    self.iterator = iterator

                def __iter__(self):
                    return self

                def __next__(self):
                    value = next(self.iterator)
                    return serialize(value)

            def serialize(value):
                primitive_types = (int, float, bool, str, bytes)
                if isinstance(value, primitive_types):
                    return value
                super_range_object = pm.eval("globalThis.dcp['range-object'].SuperRangeObject")
                if utils.instanceof(value, super_range_object):
                    return value
                if isinstance(value, Iterator):
                    return IteratorWrapper(value)

                for serializer in self.serializers:
                    if serializer.interrogate(value):
                        serialized_value = serializer.serialize(value)
                        serialized_serializer_name = serializer.name.encode()
                        return serialized_serializer_name + serialized_value

            serialized_input_data = []
            serialized_arguments = []
            serialized_work_function = b''

            for input_slice in self.js_ref.jobInputData:
                serialized_input_data.append(serialize(input_slice))
            for argument in self.js_ref.jobArguments:
                serialized_arguments.append(serialize(argument))

            if self.js_ref.worktime == 'pyodide':
                self.js_ref.workFunctionURI = urllib.parse.quote("");
            else:
                if isinstance(self.work_function, str):
                    self.js_ref.workFunctionURI = urllib.parse.quote(self.work_function)

            def convert_job_env_to_arguments():
                args = []
                for env_key in self.env:
                    args.append(f"{env_key}={self.env[env_key]}")
                return args;
            env_args = convert_job_env_to_arguments();

            #TODO serialize JobFS and emplace in argument array. For now this is just a placeholder
            offset_to_argument_vector = 4 + len(env_args)
            self.js_ref.jobArguments  = offset_to_argument_vector + ["gzImage", b''] + ["env"] + env_args + serialized_arguments + serialized_work_function

            def on(self, *args):
                if len(args) > 1 and callable(args[1]):
                    event_name = args[0]
                    event_cb = args[1]
                    self.js_ref.on(event_name, event_cb)
                else:
                    event_name = args[0]
                    def decorator(fn):
                        self.js_ref.on(event_name, fn)
                    return decorator
    return Job

