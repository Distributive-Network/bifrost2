#! /usr/bin/env python3

import dcp from distributive

@dcp.job(
    compute_groups=[{
        "joinKey": "will",
        "joinSecret": "bozo"
    }],
    public={ "name": "my epic job" },
    auto_close=False,
)
def my_func(datum):
    dcp.progress()
    return datum * 3

job = my_func([1,2,3,4,5,6])

@job.on('readystatechange')
def state_change_cb(state)
    print(f"Job in state: {state}")

results = job.exec_sync(
    slice_payment_offer=0.35,
)

print("results:", results) # 3,6,9,12,15,18

