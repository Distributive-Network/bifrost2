#! /usr/bin/env python3
"""
My first more Pythonic appraoch.

The idea here is that the decorator will decorate the my_func function
as a function which creates a job with compute.for and passes my_func
as the workFunction with some extra code added for setting the slice
handler for instance.

You can also specify exec or localExec, perhaps you can stack compute
groups and other stuff ontop? Hmm... I'll consider that in a more
advanced appraoch.
"""

import dcp from distributive

@dcp.work_function.exec
def my_func(datum):
    dcp.progress()
    return datum * 3

results = my_func([1,2,3,4,5,6])
print("results:", results) # 3,6,9,12,15,18

