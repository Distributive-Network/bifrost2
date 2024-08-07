"""
Converts Job modules (Pyodide core packages) for Pyodide worktime.

Author: Severn Lortie <severn@distributive.network>
Date: Aug 2024
"""

def convert_modules_to_requires(modules):
    requires = []
    for module in modules:
        requires.append(f"pyodide-{module}/pyodide-{module}.js")
    return requires

