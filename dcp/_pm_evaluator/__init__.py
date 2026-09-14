"""
A real, separate-process evaluator for job.localExec() under pythonmonkey,
matching how localExec() actually works on Node.js -- a genuinely separate
process, not a shared JS global.

See src/dcp-client/worker/evaluators/node-localExec.js (dcp monorepo) for
the reference architecture this mirrors: a SandboxConstructor that spawns
a worker connected over a socket, wrapped to satisfy the same postMessage/
onmessage/onerror/terminate/addEventListener contract Sandbox.start()
expects from any platform's evaluator.

Wire protocol (matches lib/standaloneWorker.js's StandaloneWorker exactly,
so a real dcp-worker-shaped child speaks a protocol dcp-client already
understands): newline-delimited, three line-prefixes:
  - "LOG:" <text>            -- debug/log line, informational only
  - "DIE:"                   -- child is shutting down
  - "MSG:" <json>             -- {"type": "workerMessage", "message": ...}
                                 (postMessage payload) or {"type": "result", ...}
"""
