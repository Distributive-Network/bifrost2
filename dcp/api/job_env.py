"""
Stores and converts Job Env arguments for Pyodide worktime.

Author: Severn Lortie <severn@distributive.network>
Date: Aug 2024
"""

class Env:
    def __init__(self):
        self.env = {}
    def convert_to_arguments(self):
        if len(self.env) < 1:
            return []
        args = ["env"]
        for env_key in self.env:
            args.append(f"{env_key}={self.env[env_key]}")
        return args
