"""
Job.

Wrapper class to get Bifrost2 API for the job.

Author: Severn Lortie <severn@distributive.network>
Date: July 2024
"""
import pythonmonkey as pm
import cloudpickle
import dill
import asyncio
from ..js import utils
from .. import dry
from .job_serializers import (
    default_serializers,
    serialize,
    deserialize,
    convert_serializers_to_arguments,
    validate_serializers
)
from .job_env import convert_env_to_arguments
from .job_modules import convert_modules_to_requires, pyodide_full_module_dependencies, convert_module_names_to_import_names
from .job_fs import JobFS
from collections.abc import Iterator
from types import FunctionType
import urllib
from .pyodide_work_function import get_work_function_string

def job_maker(super_class):
    class Job(super_class):
        def __init__(self, job_js):
            super().__init__(job_js)
            self.js_ref.worktime = 'pyodide'

            self._wrapper_set_attribute("serializers", default_serializers)
            self._wrapper_set_attribute("env", {})
            job_js.modules = [] #TODO: why is this only done this way for job modules?
            self._wrapper_set_attribute("fs", JobFS())
            self._wrapper_set_attribute("_exec_called", False)
            self.aio.exec = self._exec;
            self.aio.wait = self._wait;

        def _get_raw_work_function(self):
            """
            Parse the raw work function and remove preceeding whitespace which
            can occur when a function is defined within another indented scope.
            """
            work_function = urllib.parse.unquote(self.js_ref.workFunctionURI)
            work_function = work_function.replace("data:,", "")

            # remove additional indentation
            lines = work_function.split('\n')
            first_loc = next(line for line in lines if line.strip()) # find the first real line of code

            num_indent_chars = len(first_loc) - len(first_loc.lstrip())
            stripped_lines = [line[num_indent_chars:] if len(line) >= num_indent_chars else line for line in lines]

            unindented_work_function = '\n'.join(stripped_lines)

            return unindented_work_function

        def _before_exec(self, *args, **kwargs):

            # Any other worktime, do not apply serializers, env, jobfs
            if not self.js_ref.worktime == "pyodide":
                return

            # pyodide worktime / bifrost 2 flavoured setup below

            work_function = self._get_raw_work_function()

            meta_arguments = [
                work_function
            ]

            serialized_arguments = []
            serialized_input_data = []
            if len(self.serializers):
                validate_serializers(self.serializers)

                super_range_object = pm.eval("globalThis.dcp['range-object'].SuperRangeObject")
                if isinstance(self.js_ref.jobInputData, list) or utils.instanceof(self.js_ref.jobInputData, pm.globalThis.Array):
                    for input_slice in self.js_ref.jobInputData:
                        # TODO - find better solution
                        # un-hide values from PythonMonkey which aren't supported
                        if isinstance(input_slice, dict) and '__pythonmonkey_guard' in input_slice:
                            input_slice = input_slice['__pythonmonkey_guard']

                        serialized_slice = serialize(input_slice, self.serializers)
                        serialized_input_data.append(serialized_slice)
                elif isinstance(self.js_ref.jobInputData, Iterator) and not utils.instanceof(self.js_ref.jobInputData, super_range_object):
                    serialized_input_data = serialize(self.js_ref.jobInputData, self.serializers)
                else:
                    serialized_input_data = self.js_ref.jobInputData

                for argument in self.js_ref.jobArguments:
                    # TODO - find better solution
                    # un-hide values from PythonMonkey which aren't supported
                    if isinstance(input_slice, dict) and '__pythonmonkey_guard' in argument:
                        argument = argument['__pythonmonkey_guard']

                    serialized_argument = serialize(argument, self.serializers)
                    serialized_arguments.append(serialized_argument)

                serialized_serializers = convert_serializers_to_arguments(self.serializers)
                meta_arguments.append(serialized_serializers)
            else:
                serialized_arguments = self.js_ref.jobArguments
                serialized_input_data = self.js_ref.jobInputData

            # TODO don't copy to bytearray, use bytes directly
            job_fs = bytearray(self.fs.to_gzip_tar())
            env_args = convert_env_to_arguments(self.env)

            modules_pyodide = pyodide_full_module_dependencies(self.modules)

            #modules_dcp_packages = convert_modules_to_requires(modules_pyodide)
            modules_dcp_packages = [] # TODO: is it a good design to use import names instead?

            modules_import_names = convert_module_names_to_import_names(modules_pyodide)

            if len(modules_dcp_packages) > 0:
                self.js_ref.requires(modules_dcp_packages)

            offset_to_argument_vector = 3 + len(env_args)
            self.js_ref.jobInputData = serialized_input_data
            self.js_ref.jobArguments = [offset_to_argument_vector] + ["gzImage", job_fs] + env_args + serialized_arguments + [meta_arguments]
            self.js_ref.workFunctionURI = "data:," + urllib.parse.quote(get_work_function_string(modules_import_names), safe="=:,#+;")

        def _exec(self, *args):
            self._before_exec()
            self._wrapper_set_attribute("_exec_called", True)
            accepted_future = asyncio.Future()
            def handle_accepted():
                accepted_future.set_result(self.js_ref.id)
            self.js_ref.on('accepted', handle_accepted)
            self.js_ref.exec(*args)

            return accepted_future

        def _wait(self):
            if not self._exec_called:
                raise Exception("Wait called before exec()")
            complete_future = asyncio.Future()
            def handle_complete(resultHandle):
                serialized_results = resultHandle["values"]()
                results = []
                for serialized_result in serialized_results:
                    result = deserialize(serialized_result, self.serializers)
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

