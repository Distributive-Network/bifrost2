"""
Converts Job modules (Pyodide core packages) for Pyodide worktime.

Author:
    Severn Lortie <severn@distributive.network>
    Will Pringle <will@distributive.network>

Date: Aug 2024
"""

from ..resources import pyodide_lock_repodata_json as repodata

def pyodide_full_module_dependencies(modules):
    """Generates a list of every required pip package."""
    dependencies = []

    # PIP packages are case insensitive, see pep-0508
    modules = list(map(lambda x: x.lower(), modules))

    for module in modules:
        if not module in repodata['packages']:
            raise Exception(f'Usage of unsupported module "{module}". "{module}" is currently not supported by the Pyodide Worktime.')
        dependencies.extend(repodata['packages'][module]['depends'])

    dependencies = list(set(dependencies))
    dependencies = list(filter(lambda module: module in repodata['packages'], dependencies))

    if len(dependencies) > 0:
        return modules + pyodide_full_module_dependencies(dependencies)

    return modules

# TODO: do we need this?
def convert_modules_to_requires(modules):
    """Convert pip module package names to dcp package names."""
    dcp_packages = []
    for pyodide_module in modules:
        dcp_packages.append(f"pyodide-{pyodide_module}/pyodide-{pyodide_module}.js")
    return dcp_packages

def convert_module_names_to_import_names(modules):
    """Converts pip module package name to import names."""
    imports = []
    for module in modules:
        imports.extend(repodata['packages'][module]['imports']) # 1 or more unique imports per module
    return imports
    

