import pythonmonkey as pm
import cloudpickle
import dill
import asyncio
from ..js import utils
from .. import dry
from .job_serializers import Serializers
from .job_env import Env
from .job_modules import Modules
from .job_fs import JobFS
from collections.abc import Iterator
from types import FunctionType
import urllib.parse
from .pyodide_work_function import work_function_string


def job_maker(super_class):
    class Job(super_class):
        def __init__(self, *args, **kwargs):
            compute_for_js = pm.eval("globalThis.dcp.compute.for")
            job_js = dry.aio.blockify(compute_for_js)(*args, **kwargs)
            job_js.worktime = "pyodide"
            super().__init__(job_js)

            work_function = None
            work_function_candidates = [arg for arg in args if isinstance(arg, FunctionType)]
            if len(work_function_candidates):
                 work_function = work_function_candidates[0]

            self._wrapper_set_attribute("_work_function", work_function)
            self._wrapper_set_attribute("_serializers_instance", Serializers())
            self._wrapper_set_attribute("_env_instance", Env())
            self._wrapper_set_attribute("_modules_instance", Modules())
            self._wrapper_set_attribute("fs", JobFS())
            self._wrapper_set_attribute("exec_called", False)
            self.aio.exec = self._exec;
            self.aio.wait = self._wait;

        @property
        def serializers(self):
            return self._serializers_instance.serializers

        @property
        def env(self):
            return self._env_instance.env

        @property
        def modules(self):
            return self._modules_instance.modules

        def _before_exec(self, *args, **kwargs):
            worktime = self.js_ref.worktime
            if not worktime == "pyodide":
                pass

            work_function = self._work_function
            if work_function is None:
                work_function = self.js_ref.workFunctionURI
            else:
                work_function = dill.source.getsource(work_function)

            meta_arguments = [
                work_function
            ]

            serializers = self._serializers_instance
            serialized_input_data = []
            serialized_arguments = []
            if not serializers.empty():
                serializers.validate_serializers()
                for input_slice in self.js_ref.jobInputData:
                    serialized_slice = self._serializers_instance.serialize(input_slice)
                    serialized_input_data.append(serialized_slice)
                for argument in self.js_ref.jobArguments:
                    serialized_argument = self._serializers_instance.serialize(argument)
                    serialized_arguments.append(serialized_argument)
                serializers_arg = self._serializers_instance.convert_to_arguments()
                meta_arguments.append(serializers_arg)
            else:
                serialized_input_data = self.js_ref.jobInputData
                serialized_arguments = self.js_ref.jobArguments

            job_fs = bytearray(self.fs.to_gzip_tar())
            env_args = self._env_instance.convert_to_arguments()
            modules = self._modules_instance.convert_to_requires()
            if len(modules) > 0:
                self.js_ref.requires(modules)

            offset_to_argument_vector = 3 + len(env_args)
            self.js_ref.jobInputData = serialized_input_data
            self.js_ref.jobArguments = [offset_to_argument_vector] + ["gzImage", job_fs] + env_args + serialized_arguments + [meta_arguments]
            self.js_ref.workFunctionURI = "data:," + urllib.parse.quote(work_function_string, safe="=:,#+")

        #TODO Make sure this runs on our event loop
        def _exec(self, *args):
            self._before_exec()
            self._wrapper_set_attribute("exec_called", True)
            accepted_future = asyncio.Future()
            def handle_accepted():
                accepted_future.set_result(self.js_ref.id)
            self.js_ref.on('accepted', handle_accepted)
            self.js_ref.exec(*args)
            return accepted_future

        #TODO Make sure this runs on our event loop
        def _wait(self):
            if not self.exec_called:
                raise Exception("Wait called before exec()")
            complete_future = asyncio.Future()
            def handle_complete(resultHandle):
                serialized_results = resultHandle["values"]()
                results = []
                for serialized_result in serialized_results:
                    result = self._serializers_instance.deserialize(serialized_result)
                    results.append(result)
                complete_future.set_result(results)
            self.js_ref.on("complete", handle_complete)
            return complete_future

        def exec(self, *args):
            results = dry.aio.blockify(self._exec)(*args)
            return results

        def wait(self):
            return dry.aio.blockify(self._wait)()

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

