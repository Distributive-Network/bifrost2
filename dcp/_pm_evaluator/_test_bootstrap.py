"""
STAGE 3 test: does the real 22-file sandbox bootstrap load successfully in
a genuinely isolated child process? Key question this answers: does
process isolation eliminate the need for Category A's console/require/
timer-clobbering fixes and the access-lists-masking bypass (see
PYTHONMONKEY_EVALUATOR_PLAN.md), or is at least some of it still needed
even with no shared global?

Run: cd C:\\Users\\danie\\DCP\\bifrost2 && python -u -m dcp._pm_evaluator._test_bootstrap
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

    def _on_line(line):
        print("[parent]", line, flush=True)
        lines_received.append(line)

    channel.on_line = _on_line

    print("[parent] spawning child...", flush=True)
    t0 = time.time()
    channel.spawn_and_connect()
    print(f"[parent] child connected in {time.time()-t0:.2f}s, pid=", channel.proc.pid, flush=True)

    # Bootstrap loading took real, non-trivial time in the original
    # investigation (22 files, some doing real async work) -- give it a
    # generous window and poll for completion rather than a fixed sleep.
    deadline = time.time() + 90
    while time.time() < deadline:
        if any("bootstrap] all 22 files loaded" in l or "bootstrap] ABORTED" in l for l in lines_received):
            break
        await asyncio.sleep(0.5)

    channel.terminate()
    await asyncio.sleep(0.5)

    aborted = [l for l in lines_received if "ABORTED" in l or "FAILED" in l]
    succeeded = any("all 22 files loaded" in l for l in lines_received)
    intact = [l for l in lines_received if "still intact" in l]

    print()
    print("=" * 60)
    print(f"Bootstrap succeeded: {succeeded}")
    print(f"Failures/aborts: {aborted}")
    print(f"writeln/onreadln intact after bootstrap: {intact}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
