"""
Resources.

Package for resources such as the pyodide-lock file (formerly known as
repodata.json). 

Note: resources should be updated when switching to newer versions of
the pyodide worktime.

Author: Will Pringle <will@distributive.network>
Date: September 2024
"""
import os
import json

file_dirn = os.path.dirname(__file__)
file_path = os.path.join(file_dirn, 'pyodide-lock.json')

print(file_path)

with open(file_path, 'r') as file:
    pyodide_lock_repodata_json = json.load(file)

pyodide_lock_repodata_json 

del file_dirn
del file_path

