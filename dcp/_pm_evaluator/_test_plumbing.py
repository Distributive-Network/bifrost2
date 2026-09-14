"""
STAGE 1 smoke test: proves spawn+socket-connect+message-exchange+terminate
works at all on this machine, with zero pythonmonkey/bifrost2 involvement --
isolates subprocess/socket mechanics from everything else before adding
that complexity on top.

Run directly: python -m dcp._pm_evaluator._test_plumbing
"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dcp._pm_evaluator.channel import EvaluatorChannel


async def main():
    loop = asyncio.get_running_loop()
    channel = EvaluatorChannel(loop)

    lines_received = []
    channel.on_line = lambda line: (print("[parent] received:", line, flush=True), lines_received.append(line))

    print("[parent] spawning child...", flush=True)
    t0 = time.time()
    channel.spawn_and_connect()
    print(f"[parent] child connected in {time.time()-t0:.2f}s, pid=", channel.proc.pid, flush=True)

    channel.write_line('MSG:{"type":"workerMessage","message":"hello from parent"}')

    await asyncio.sleep(2.0)

    channel.terminate()
    await asyncio.sleep(0.5)

    assert any("pythonmonkey ready" in l for l in lines_received), "child pythonmonkey did not start"
    assert any("child JS onreadln got" in l for l in lines_received), "child's real pythonmonkey JS did not receive our message via onreadln"
    print("STAGE 2 PLUMBING TEST PASSED (real pythonmonkey in child, real socket round-trip)")


if __name__ == "__main__":
    asyncio.run(main())
