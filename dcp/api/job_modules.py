"""
Stores and converts Job modules (Pyodide core packages) for Pyodide worktime.

Author: Severn Lortie <severn@distributive.network>
Date: Aug 2024
"""

class Modules:
    def __init__(self):
        self.modules = []
    def convert_to_requires(self):
        requires = []
        for module in self.modules:
            requires.append(f"pyodide-{module}/pyodide-{module}.js")
        return requires

