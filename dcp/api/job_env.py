"""
Converts Job Env arguments for Pyodide worktime.

Author: Severn Lortie <severn@distributive.network>
Date: Aug 2024
"""

def convert_env_to_arguments(env):
    if not len(env):
        return []
    args = ["env"]
    for env_key in env:
        args.append(f"{env_key}={env[env_key]}")
    return args
