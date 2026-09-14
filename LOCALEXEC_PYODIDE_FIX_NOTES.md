# `job.localExec()` broken for pyodide work functions — investigation notes

Handover notes for this fix. Written for the bifrost2/DCP team reviewing
the accompanying PR — read this for the "why," not just the diff.

## Context

This surfaced while getting `job.localExec()` working end-to-end under
`pythonmonkey` (dcp-client running inside a Python process via
[PythonMonkey](https://github.com/Distributive-Network/PythonMonkey),
no Node.js) for a Python/pyodide work function. It is **not**
pythonmonkey-specific — it's a gap in `Job.localExec()` itself that
affects any platform, since `localExec()` never worked for pyodide work
functions at all as shipped.

## The bug

`Job.localExec()` is not implemented as its own method — it falls through
to the generic JS-proxy wrapper (`dry/class_manager.py`'s `__getattr__`),
which just calls `self.js_ref['localExec']` directly. Compare this to
`Job.exec()` (`_exec()`), which explicitly calls `self._before_exec()`
first.

`_before_exec()` is what rewrites `workFunctionURI` into the real
bifrost2-wrapped script for the pyodide worktime (imports, serializers,
and critically, the `dcp.set_slice_handler()` registration). Skip it, and
the raw user Python source is sent to the worktime as-is — which never
calls `dcp.set_slice_handler()`, so every slice fails immediately with
`ENOSLICEHANDLER`.

Net effect: **`job.localExec()` cannot work for any pyodide work function,
on any platform**, since the generic proxy fallback it inherits skips the
one setup step pyodide jobs actually need.

## The fix

Add a real `localExec()` method (mirroring `_exec()`'s setup) that:

1. Calls `self._before_exec()` before delegating, fixing the core bug
   above.
2. Marks `_exec_called = True`, matching `_exec()`'s behavior (relevant if
   anything downstream still checks it).
3. Delegates to the real JS `localExec()` and returns its value directly —
   see "Two more real bugs" below for why this needs its own handling
   rather than reusing `.wait()`.

### Two more real bugs, found while fixing the first one

**a) The return value is unusable as-is.** The JS call resolves to the
job's `ResultHandle` — a Proxy whose `get`/`has`/`ownKeys` traps make
pythonmonkey report `typeof ret_val === "function"` (confirmed empirically
by pythonmonkey wrapping it as a `JSFunctionProxy`, not a
`JSObjectProxy`), which breaks the generic subscript-based `__getattr__`
deserialization (`'pythonmonkey.JSFunctionProxy' object is not
subscriptable`). Fixed by converting it to a plain JS array first
(`Array.from(resultHandle)`, matching the real Node.js usage pattern) and
deserializing each value the same way `_wait()`'s `handle_complete` does.

**b) `.wait()` doesn't work after `.localExec()`, and can't be made to.**
Confirmed by instrumenting dcp-client's own `'complete'`/`'stop'`/
`'stopped'` emission points directly: for a `localExec()` job, the whole
job (including the `'complete'` event `_wait()` listens for) has already
finished by the time the real JS `localExec()` Promise resolves. By the
time a caller's `_wait()` call would register its listener, that event has
already fired and been missed — `EventEmitter`s don't replay past events
to newly-added listeners. This is why `localExec()` returns its own
result directly instead of requiring a separate `.wait()` call afterward,
matching the real Node.js usage pattern
(`const results = await job.localExec()`, no `.wait()`). `.wait()` itself
is untouched and remains correct for real distributed jobs via
`exec()`/`aio.exec()`, where `'complete'` genuinely arrives later.

**c) Error messages get buried.** When a work function raises, the real
error message (a genuine Python traceback pointing at the user's own work
function) is already present on the caught exception's
`.jsError.message` — pythonmonkey's `SpiderMonkeyError` exposes the
underlying JS `Error` as `.jsError`. Without unwrapping it, the caller
sees a `SpiderMonkeyError` whose message is buried under a wall of
dcp-client's own internal JS stack frames
(`DCPError`/`onCancel`/`eventHandlerWrapper`/...) that have nothing to do
with the actual bug. Fixed by re-raising a plain `RuntimeError` with just
the real message when it's available.

## What was deliberately left out of this PR

The investigation this fix came out of also built a local-only file-based
argument-routing workaround (so job arguments could be tested without a
real scheduler upload endpoint available) and wired two optional hooks
into an earlier draft of this fix to support it
(`__pmRouteJobArgumentsLocally`/`__pmCleanupLocalArgFiles`, checked via
`pythonmonkey.globalThis`). Those hooks are pure local-testing scaffolding
for that investigation's own test harness — meaningless to a real caller
of `job.localExec()`, and not something that belongs in bifrost2's source.
This PR's `localExec()` does **not** include them.

## Testing

Re-verified against a real end-to-end job after removing the local-only
hooks (not just re-testing the original draft that had them): a full
`dcp.compute_for()` job over an 8-letter input set with a Python work
function (uppercasing), executed via `job.localExec()` under pythonmonkey.
Confirmed: real pyodide worktime engaged (real `cloudpickle`/`numpy`
package loading, not stubbed), all 8 slices completed, correct final
result. Not yet tested on a non-pythonmonkey platform, since this
investigation's whole environment is pythonmonkey-based — the fix itself
has no pythonmonkey-specific dependency (unlike the two hooks that were
removed), so it should behave identically elsewhere, but that's reasoning,
not an independent test on another platform.
