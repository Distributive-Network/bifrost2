"""
Smoke test: spawn+socket-connect+message-exchange+terminate against the
real child.py. For a more thorough bootstrap check, see _test_bootstrap.py.

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

    # No onreadln handler exists yet at this point in the bootstrap, so this
    # is a no-op -- it only exercises the plumbing, not message dispatch.
    # Bare JSON, no "MSG:" prefix (see child.py's _socket_reader).
    channel.write_line('{"type":"workerMessage","message":"hello from parent"}')

    await asyncio.sleep(5.0)

    channel.terminate()
    await asyncio.sleep(0.5)

    assert any("pythonmonkey ready" in l for l in lines_received), "child pythonmonkey did not start"
    assert any("[bootstrap] all 22 files loaded successfully" in l for l in lines_received), "child did not finish loading the sandbox bootstrap"
    # False is correct: sa-ww-simulation.js deletes these once captured
    # privately (deliberate cleanup, not a clobbering bug).
    assert any("writeln/onreadln still intact after bootstrap: False" in l for l in lines_received), "expected writeln/onreadln removed post-bootstrap; got True"
    print("PLUMBING TEST PASSED (real pythonmonkey in child, full sandbox bootstrap, real socket round-trip)")


if __name__ == "__main__":
    asyncio.run(main())
