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

def _clean_js_error_message(e):
    """The real traceback pointing at the user's own work function is on
    e.jsError.message; str(e) alone is buried under dcp-client's internal
    JS stack frames."""
    js_error = getattr(e, 'jsError', None)
    message = getattr(js_error, 'message', None) if js_error is not None else None
    return message or str(e)

def _check_localexec_pm_capability():
    """localExec() runs the work function's pyodide sandbox in-process,
    which needs SharedArrayBuffer/Atomics (PythonMonkey PR #509+) to link.
    exec() never loads pyodide locally -- it only dispatches -- so this
    check is scoped to localExec() rather than gating dcp.init() for
    everyone. Fails fast with a clear error instead of the silent hang an
    unpatched pythonmonkey produces deep inside sandbox startup."""
    if pm.eval("typeof SharedArrayBuffer") == "undefined":
        raise RuntimeError(
            "job.localExec() requires a PythonMonkey build with "
            "SharedArrayBuffer/Atomics support (PythonMonkey PR #509 or "
            "later) -- the pythonmonkey installed here doesn't have it. "
            "job.exec() is unaffected and works normally."
        )

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
            self._wrapper_set_attribute("_local_results", None)
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
                if hasattr(self.jobInputData, 'js_ref') and dry.class_manager.reg.find_from_js_instance(self.jobInputData.js_ref):
                    serialized_input_data = self.jobInputData.js_ref
                elif isinstance(self.js_ref.jobInputData, list) or utils.instanceof(self.js_ref.jobInputData, pm.globalThis.Array):
                    for input_slice in self.js_ref.jobInputData:
                        # TODO - find better solution
                        # un-hide values from PythonMonkey which aren't supported
                        if isinstance(input_slice, dict) and '__pythonmonkey_guard' in input_slice:
                            input_slice = input_slice['__pythonmonkey_guard']

                        # only serialize non-dcp values
                        if hasattr(input_slice, 'js_ref') and dry.class_manager.reg.find_from_js_instance(input_slice.js_ref):
                            serialized_input_data.append(input_slice.js_ref)
                        else:
                            serialized_slice = serialize(input_slice, self.serializers)
                            serialized_input_data.append(serialized_slice)
                else:
                    serialized_input_data = self.js_ref.jobInputData
                if hasattr(self.jobArguments, 'js_ref') and dry.class_manager.reg.find_from_js_instance(self.jobArguments.js_ref):
                    serialized_arguments = [self.jobArguments.js_ref]
                else:
                    for argument in self.js_ref.jobArguments:
                        # TODO - find better solution
                        # un-hide values from PythonMonkey which aren't supported
                        if isinstance(argument, dict) and '__pythonmonkey_guard' in argument:
                            argument = argument['__pythonmonkey_guard']
                        if utils.instanceof(argument, pm.eval("URL")): # Still needed?
                            serialized_arguments.append(argument)
                            continue

                        # only serialize non-dcp values
                        if hasattr(argument, 'js_ref') and dry.class_manager.reg.find_from_js_instance(argument.js_ref):
                            serialized_arguments.append(argument.js_ref)
                        else:
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

            # convert single string to list of one string
            if isinstance(self.modules, str):
                self.modules = [self.modules]

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

            # localExec() already ran the whole job to completion, 'complete'
            # event included, before it returned (see its own docstring) --
            # by the time wait() could register a listener the event has
            # already fired and gone unheard (EventEmitters don't replay).
            # Returning the results it already collected -- rather than
            # trying to listen for an event that already happened -- is what
            # lets `job.localExec(); results = job.wait()` mirror the real
            # `job.exec(); results = job.wait()` pattern exactly.
            if self._local_results is not None:
                complete_future = asyncio.Future()
                complete_future.set_result(self._local_results)
                return complete_future

            complete_future = asyncio.Future()
            def handle_complete(resultHandle):
                serialized_results = resultHandle["values"]()
                results = []
                for serialized_result in serialized_results:
                    result = deserialize(serialized_result, self.serializers)
                    results.append(result)
                complete_future.set_result(results)
            # TODO: on cancel, pass to cancel listener
            self.js_ref.on("complete", handle_complete)
            self.js_ref.on("cancel", handle_complete)
            return complete_future

        def exec(self, *args):
            results = dry.aio.blockify(self._exec)(*args)
            return results

        def wait(self):
            # For a localExec() job, the real JS localExec() Promise
            # (awaited inside localExec() below) doesn't resolve until the
            # WHOLE job -- 'complete' event included -- has already
            # finished, so a *fresh* listener registered here would always
            # miss it (EventEmitters don't replay past events). _wait()
            # handles this by returning localExec()'s already-cached
            # results instead of listening for an event that already fired.
            # For real distributed jobs via exec()/aio.exec(), no such cache
            # exists yet at this point, so this registers listeners and
            # blocks for 'complete' normally.
            return dry.aio.blockify(self._wait)()

        def _route_arguments_locally(self):
            """
            localExec() otherwise unconditionally routes job data through
            the real scheduler: jobArguments once a payload exceeds a size
            threshold (a scheduler-hosted URL), slice *values* via a
            dedicated, unconditional bulk upload (addSlices(), during the
            "uploading" state) that runs regardless of size unless
            jobRef.marshaledDataValues is already set, a range-shaped input
            set (e.g. MultiRangeObject) inlined as-is in the deploy payload,
            and the work function source embedded directly in
            workFunctionURI as a data: URI. Real Node localExec() avoids all
            of this by writing each to a local temp file and granting the
            local worker a narrow, path-scoped file:// origin per file
            instead -- this mirrors that for every case Node handles
            (job/index.js's own platform-gated rewrite only runs for
            'nodejs', so pythonmonkey needs its own copy).

            Must run SYNCHRONOUSLY, immediately after _before_exec()
            populates jobArguments/jobInputData/workFunctionURI and before
            the real JS localExec() call (and therefore deployJob()'s
            upload) ever runs: the scheduler snapshots all of this during
            deploy, and the slice-value upload is scheduled immediately
            once deploy completes -- both well before localWorker/
            originManager exist or any async callback would get a turn to
            run.

            Returns the list of (path, purpose) grants still needing
            origin access once the local worker exists (see
            _grant_local_file_origins, called separately, async, after
            this returns).
            """
            import tempfile
            import os as _os

            written_paths = []

            def _write_temp_file(encoded_str, suffix):
                fd, path = tempfile.mkstemp(prefix="bifrost2-localExec-arg-", suffix=suffix)
                with _os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(encoded_str)
                written_paths.append(path)
                return path

            pm.globalThis["__pmWriteLocalArgFile"] = _write_temp_file
            rewrite = pm.eval("""
            (jobRef) => {
              const KVIN = new (require('kvin').KVIN)();
              const { SuperRangeObject, MultiRangeObject } = globalThis.dcp['range-object'];
              const { RemoteDataSet } = globalThis.dcp.compute;
              const grants = [];
              const toLocalURL = (v, purpose) => {
                if (v instanceof URL) return v;
                const encoded = KVIN.stringify(v);
                const filePath = globalThis.__pmWriteLocalArgFile(encoded, '.kvin');
                grants.push({ path: filePath, purpose });
                return new URL('file://' + filePath);
              };
              if (jobRef.jobArguments) {
                jobRef.jobArguments = jobRef.jobArguments.map((v) => toLocalURL(v, 'fetchArguments'));
              }

              // Same detection marshalInputData() uses (job/index.js) to
              // decide dataRange vs dataValues -- a range object encodes
              // job design (e.g. combinatorial dimensions), not raw slice
              // values, but Node treats it as equally local-only, so this
              // matches that rather than treating it as safe to inline.
              const inputData = jobRef.jobInputData;
              const isRange = inputData instanceof SuperRangeObject
                || (inputData && inputData.hasOwnProperty && inputData.hasOwnProperty('ranges') && inputData.ranges instanceof MultiRangeObject)
                || (inputData && inputData.hasOwnProperty && inputData.hasOwnProperty('start') && inputData.hasOwnProperty('end'));

              if (isRange) {
                const filePath = globalThis.__pmWriteLocalArgFile(JSON.stringify(inputData), '.json');
                grants.push({ path: filePath, purpose: 'fetchData' });
                jobRef.marshaledDataRange = new RemoteDataSet([new URL('file://' + filePath)]);
                jobRef.rangeLength = inputData.length;
              } else if (Array.isArray(inputData)) {
                jobRef.marshaledDataValues = inputData.map((v) => toLocalURL(v, 'fetchData'));
              }

              // workFunctionURI is a separate field from jobArguments, set
              // directly by bifrost2's _before_exec() as a data: URI
              // embedding the full wrapped work function source -- Node's
              // own rewrite (job/index.js, gated to 'nodejs') never runs
              // for pythonmonkey, so nothing else does this.
              if (typeof jobRef.workFunctionURI === 'string' && jobRef.workFunctionURI.startsWith('data:')) {
                const commaIndex = jobRef.workFunctionURI.indexOf(',');
                const source = decodeURIComponent(jobRef.workFunctionURI.slice(commaIndex + 1));
                const filePath = globalThis.__pmWriteLocalArgFile(source, '.js');
                grants.push({ path: filePath, purpose: 'fetchWorkFunctions' });
                jobRef.workFunctionURI = new URL('file://' + filePath).href;
              }

              return grants;
            }
            """)
            grants = [{"path": g["path"], "purpose": g["purpose"]} for g in rewrite(self.js_ref)]
            return grants, written_paths

        def _grant_local_file_origins(self, grants, poll_interval=0.05, max_attempts=200):
            """
            The local worker doesn't fetch its arguments/slice values until
            well after deploy/upload finishes, so (unlike
            _route_arguments_locally) this half can safely poll
            asynchronously for job.js_ref.localWorker.originManager to
            exist, then grant one narrow, path-scoped origin per file, with
            the purpose matching what it actually is ('fetchArguments' vs
            'fetchData') -- never a blanket grant.

            NEEDS TESTING once services are back up: this is a direct port
            of the proven-working pm_localexec_setup.py version, adapted to
            be a real Job method rather than an opt-in hook, but has not
            itself been re-tested against a live job yet (blocked on a
            planned DCP services outage -- see PYTHONMONKEY_EVALUATOR_PLAN.md
            sec5c). In particular: does this timing assumption
            (job.js_ref.localWorker.originManager appearing) still hold
            with the new separate-process evaluator, where localWorker
            construction now involves a real spawned child process instead
            of synchronous in-process dispatch?
            """
            grant_origin = pm.eval("""
            (originManager, filePath, purpose) => {
              originManager.add(new URL('file://' + filePath).pathname, purpose, null);
            }
            """)

            def _try_grant(attempts_left):
                try:
                    worker = self.js_ref["localWorker"]
                    if worker is None or isinstance(worker, pm.null.__class__):
                        if attempts_left > 0:
                            dry.aio.loop.call_later(poll_interval, _try_grant, attempts_left - 1)
                        return
                    origin_manager = worker["originManager"]
                    if origin_manager is None or isinstance(origin_manager, pm.null.__class__):
                        if attempts_left > 0:
                            dry.aio.loop.call_later(poll_interval, _try_grant, attempts_left - 1)
                        return
                    for grant in grants:
                        grant_origin(origin_manager, grant["path"], grant["purpose"])
                except Exception:
                    if attempts_left > 0:
                        dry.aio.loop.call_later(poll_interval, _try_grant, attempts_left - 1)

            dry.aio.loop.call_later(poll_interval, _try_grant, max_attempts)

        def localExec(self, *args, **kwargs):
            """
            localExec() was otherwise inherited unmodified from the generic
            JS-proxy wrapper (dry/class_manager.py __getattr__), which calls
            straight through to self.js_ref['localExec'] and skips
            _before_exec() entirely. For the pyodide worktime, _before_exec()
            is what rewrites workFunctionURI into the real bifrost2-wrapped
            script (imports, serializers, and the dcp.set_slice_handler()
            registration) -- without it the raw user Python source is sent
            as-is, which never calls dcp.set_slice_handler() (->
            ENOSLICEHANDLER in the pyodide worktime). Mirrors _exec()'s
            setup.

            Works both as a single call (`results = job.localExec()`,
            matching Node's own usage) and, since the results are cached on
            the job once collected, as `job.localExec(); results =
            job.wait()` -- matching `job.exec(); results = job.wait()`
            exactly, so swapping exec for localExec never requires moving
            where `results =` appears. See wait()'s own note for why a
            *fresh* listener registered after the fact would otherwise miss
            the 'complete' event.

            force_job_completion_when_done()'s concern (the local Worker
            never signaling a terminating 'stop') did not need porting --
            confirmed by testing, the real evaluator's Sandbox/Worker
            machinery completes jobs correctly on its own.
            """
            _check_localexec_pm_capability()

            self._before_exec()
            self._wrapper_set_attribute("_exec_called", True)

            grants, written_paths = self._route_arguments_locally()
            self._grant_local_file_origins(grants)

            try:
                try:
                    ret_val = dry.aio.blockify(self.js_ref.localExec)(*args, **kwargs)
                except Exception as e:
                    raise RuntimeError(_clean_js_error_message(e)) from None
            finally:
                # These files hold real job argument/slice-value data
                # (potentially sensitive) and are not otherwise cleaned up.
                # The local worker has already read them by the time
                # localExec()'s own promise settles (succeeded or failed).
                import os as _os
                for path in written_paths:
                    try:
                        _os.unlink(path)
                    except OSError:
                        pass

            # ret_val resolves to the job's ResultHandle -- a Proxy whose
            # get/has/ownKeys traps make pythonmonkey report
            # `typeof ret_val === "function"`, which doesn't support the
            # generic subscript-based __getattr__ wrap_obj() normally relies
            # on. Convert it to a plain JS array the same way Node's own
            # usage does (Array.from(results)) and deserialize each value
            # exactly like _wait()'s handle_complete does.
            to_array = pm.eval("(rh) => Array.from(rh)")
            raw_values = to_array(ret_val)
            results = [deserialize(v, self.serializers) for v in raw_values]

            # A slice whose work function raised resolves normally here --
            # the exception lands as a value in `results`, not a rejection
            # of the promise above -- so it has to be checked explicitly.
            for result in results:
                if isinstance(result, BaseException):
                    raise RuntimeError(_clean_js_error_message(result)) from None

            self._wrapper_set_attribute("_local_results", results)
            return results

        def on(self, *args):
            # deserialize job on event parameters before passing them to user defined callback
            def cb_deserialize_wrapper(callback):
                def new_cb(*inner_args):
                    new_args = []
                    for arg in inner_args:
                        if isinstance(arg, dict):
                            for key in arg:
                                arg[key] = deserialize(arg[key], self.serializers)
                        new_args.append(deserialize(arg, self.serializers))
                    return callback(*new_args)
                return new_cb

            if len(args) > 1 and callable(args[1]):
                event_name = args[0]
                event_cb = cb_deserialize_wrapper(args[1])
                self.js_ref.on(event_name, event_cb)
            else:
                event_name = args[0]
                def decorator(fn):
                    event_cb = cb_deserialize_wrapper(fn)
                    self.js_ref.on(event_name, event_cb)
                return decorator
    return Job

