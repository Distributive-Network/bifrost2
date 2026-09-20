"""
A real, separate-process evaluator for job.localExec() under pythonmonkey.
Spawns a real child process for the sandbox rather than sharing one JS
global with the Supervisor -- more isolated than Node's own localExec()
(which uses a same-process, pipe-connected worker; see
src/dcp-client/worker/evaluators/node-localExec.js), but the isolation is
what actually matters here, not matching Node's specific mechanism.

REQUIRES PythonMonkey PR #509 installed first (SpiderMonkey rebuilt for
SharedArrayBuffer/Atomics, plus JobQueue checkpoint fixes) -- see
PYTHONMONKEY_EVALUATOR_PLAN.md's top section. Without it, jobs hang, they
don't error cleanly.

Wire protocol (matches lib/standaloneWorker.js's StandaloneWorker, so a
real dcp-worker-shaped child speaks a protocol dcp-client already
understands) -- ASYMMETRIC, not the same both directions:
  - child -> parent: newline-delimited, prefixed --
      "LOG:" <text>  -- debug/log line, informational only
      "DIE:"         -- child is shutting down
      "MSG:" <json>  -- {"type": "workerMessage", "message": ...} (a
                        postMessage payload) or {"type": "result", ...}
  - parent -> child: newline-delimited, bare JSON, NO prefix -- e.g.
      {"type": "workerMessage", "message": ...} or {"type": "die"}
"""
