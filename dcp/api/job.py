import pythonmonkey as pm
import pickle
from ..js import utils
from .. import dry
from .job_serializers import Serializers
from .job_env import Env
from collections.abc import Iterator
from types import FunctionType
import urllib.parse


def job_maker(super_class):
    class Job(super_class):
        def __init__(self, *args, **kwargs):
            compute_for_js = pm.eval("globalThis.dcp.compute.for")
            job_js = dry.aio.blockify(compute_for_js)(*args, **kwargs)
            super().__init__(job_js)

            work_function_candidates = [arg for arg in args if isinstance(arg, FunctionType)]
            if len(work_function_candidates) > 1:
                raise Exception("More than one work function candidate detected. This is a bug")

            self._wrapper_set_attribute("_work_function", work_function_candidates[0])
            self._wrapper_set_attribute("_serializers_instance", Serializers())
            self._wrapper_set_attribute("_env_instance", Env())

        @property
        def serializers(self):
            return self._wrapper_get_attribute("_serializers_instance").serializers

        @property
        def env(self):
            return self._wrapper_get_attribute("_env_instance").env

        def exec(self, *args, **kwargs):
            self._wrapper_get_attribute("_serializers_instance").validate_serializers()

            serialized_input_data = []
            serialized_arguments = []
            serialized_work_function = b''

            for input_slice in self.js_ref.jobInputData:
                serialized_slice = self._wrapper_get_attribute("_serializers_instance").serialize(input_slice)
                serialized_input_data.append(serialized_slice)
            for argument in self.js_ref.jobArguments:
                serialized_argument = self._wrapper_get_attribute("_serializers_instance").serialize(argument)
                serialized_arguments.append(serialized_argument)

            if self.js_ref.worktime == 'pyodide':
                # TODO: this is where the Bf2 workfn should be inserted
                self.js_ref.workFunctionURI = urllib.parse.quote("");

            env_args = self._wrapper_get_attribute("_env_instance").convert_to_arguments();

            #TODO serialize JobFS and emplace in argument array. For now this is just a placeholder
            offset_to_argument_vector = 4 + len(env_args)
            self.js_ref.jobInputData = serialized_input_data
            self.js_ref.jobArguments = [offset_to_argument_vector] + ["gzImage", b''] + ["env"] + env_args + serialized_arguments + [serialized_work_function]

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

