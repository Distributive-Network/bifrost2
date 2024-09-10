#!/usr/bin/env python3

import dcp
import datetime
import asyncio

dcp.init()

from dcp import compute_for

def workfn(datum):
    import dcp
    dcp.progress()
    return datum * datum

my_j = compute_for([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], workfn)

my_j.on('readystatechange', print)
my_j.on('result', print)
@my_j.on('accepted')
def accepted_handler(ev):
    print(f"jobid = {my_j.id}")

my_j.public.name = f'async simple bifrost2 example: {datetime.datetime.now()}'

my_j.computeGroups = [{ 'joinKey': '<join key here>', 'joinSecret': '<join secret here>' }]

loop = asyncio.get_event_loop()

async def main():
    await my_j.aio.exec()
    res = await my_j.aio.wait()
    print(">>>>>>>>>>>>>>>>>>>>>>>>>> RESULTS ARE IN")
    print(res)

loop.run_until_complete(main())

