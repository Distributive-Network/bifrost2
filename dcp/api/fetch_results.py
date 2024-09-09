"""
fetchResults API

Author: Will Pringle <will@distributive.network>
Date: September 2024
"""

import pythonmonkey as pm
from .. import dry
from .. import js
from .job_serializers import default_serializers, deserialize

def fetch_results_maker(fetch_results_js):
    def fetch_results(*args, serializers=default_serializers):
        serialized_results = dry.aio.blockify(fetch_results_js)(*args)

        results = []
        for element in serialized_results:
            deserialized_value = deserialize(element['value'], serializers)
            slice_number = int(element['slice'])

            results.append({ 'slice': slice_number, 'value': deserialized_value })
        
        return results
    return fetch_results 

