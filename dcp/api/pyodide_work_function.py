"""
The BiFrost2 work function. Handles deserializing/serializing job data and running
the real (user provided) work function. Code from job_serializers.py is also
copied in.

Author: Severn Lortie <severn@distributive.network>
Date: Aug 2024
"""
import dill
from .job_serializers import serialize, deserialize

def get_work_function_string(module_imports):
    module_imports.extend(['cloudpickle', 'numpy']) # required for bifrost2 deserialization

    imports_string = """
import sys
from collections.abc import Iterator

# Below are automatically imported modules
    """

    for python_module_to_import in module_imports:
        imports_string += f"\nimport {python_module_to_import}\n"

    serialize_string   = dill.source.getsource(serialize, lstrip=True)
    deserialize_string = dill.source.getsource(deserialize, lstrip=True)

    work_function_string = """
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

if "first_run" not in globals():
    first_run = True

def bifrost2_setup():
    global meta_arguments
    global first_run

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

    def slice_handler_deserialization_wrapper(serialized_datum):
        datum = deserialize(serialized_datum, serializers)
        result = user_work_function(datum)
        serialized_result = serialize(result, serializers)
        return serialized_result

    if first_run:
        for i in range(len(sys.argv)):
            arg = deserialize(sys.argv[i], serializers)
            sys.argv[i] = arg

    dcp.set_slice_handler(slice_handler_deserialization_wrapper)
    first_run = False
bifrost2_setup()
    """

    return f"""
{imports_string}
{serialize_string}
{deserialize_string}
{work_function_string}
    """


