"""
compute_for API

Author: Will Pringle <will@distributive.network>
Date: July 2024
"""
def compute_for_maker(Job):
    def compute_for(*args, **kwargs):
        return Job(*args, **kwargs)
    return compute_for
