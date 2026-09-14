# Real, separate-process `localExec()` support for pythonmonkey — plan doc

Written to survive a session compaction or a fresh pickup with zero other
context. If you're reading this cold: read this whole document before
touching code. It supersedes any assumption that `localExec()` under
pythonmonkey works by sharing one JS global — it's being rebuilt to spawn
a real child process instead, matching how Node.js's `localExec()` already
works.

---

## 0. Why this document exists

`job.localExec()` under pythonmonkey was gotten working during an earlier
investigation (see `localexec_patch/STATUS.md` and
`localexec_patch/FIXES_SUMMARY.md` in `C:\Users\danie\DCP\`) via an
in-process simulation: pythonmonkey has one shared JS global, and the
"Supervisor" (job-management) code and the "sandboxed worker" (work
function execution) code were made to share it, with ~950 lines of
workarounds (`C:\Users\danie\DCP\localexec_patch\pm_localexec_setup.py`)
for everything that broke as a result (console/require/timer clobbering,
sandbox access-list masking nuking Supervisor globals, a timer-starvation
bug, a Worker-lifecycle completion-detection gap, silent error swallowing).

That got real jobs completing end-to-end, but every test script had to
manually `sys.path.insert(...)`, `import pm_localexec_setup`, call
`pm_localexec_setup.install()`, and wire up 3-4 more per-job patch function
calls before `job.localExec()` would work at all. The user's own words:
**"you added a bunch of stuff and this is sloppy as hell."**

The user showed the actual target API shape (see §2) and asked for
`localExec()` to work that cleanly, with zero manual wiring — which means
all of that machinery needs to move from a personal patch script into
bifrost2 (and, for some of it, the real `dcp` monorepo) as first-class,
automatic behavior.

While investigating how to do that cleanly, a bigger finding emerged (see
§3): the real Node.js `localExec()` doesn't share a global at all — it
spawns a **separate OS process**. The user explicitly chose to build the
architecturally-correct separate-process version rather than just
formalize the shared-global hack. **That is the current, in-progress
effort this document tracks.**

A first attempt at just the narrower `job.py` fix (not the full platform
work) was opened as bifrost2 PR #49 and **was closed by the user for being
low-quality** ("slop") — it excluded real bugs (thinking they were
local-only test scaffolding when they weren't) and didn't reflect the full
picture. Do not reopen or reference it as a model; this document and the
`pythonmonkey-platform-support` branch supersede it.

---

## 1. Desired end state — the target API shape

Exactly this, verbatim, with **no import beyond `json`/`dcp`, no manual
patch wiring, no `sys.path` hacks**:

```python
import json
import dcp
dcp.init()

# IDENTITY

# INPUT SET
input_set = list('yelling!')

# WORK FUNCTION
def work_function(letter):
  dcp.progress()
  return letter.upper()

# COMPUTE FOR
job = dcp.compute_for(input_set, work_function)

# COMPUTE GROUPS
job.computeGroups = [
  { 'joinKey':'demo', 'joinSecret':'dcp' },
  { 'joinKey':'public' }
];

# PUBLIC INFO
job.public.name = 'to-upper-case'
job.public.description = 'Minimal demonstration of a distributed job'
job.public.link = 'https://distributive.network'

# EVENTS
job.on('readystatechange', lambda s: print(f"Ready State: {s}"))
job.on('accepted', lambda _: print(f"  Job ID: {job.id}\n  Awaiting results..."))
job.on('noProgress', lambda n: print(json.dumps(n, indent=4).replace('\\n', '\n')))
job.on('error', lambda e: print(json.dumps(e, indent=4).replace('\\n', '\n')))
job.on('nofunds', lambda n: print(json.dumps(n, indent=4).replace('\\n', '\n')))
job.on('result', lambda r: print(json.dumps(r, indent=4).replace('\\n', '\n')))

# EXECUTION
results = job.localExec()   # <-- the only line that differs from exec()+wait()

# RESULT POST-PROCESSING
print(''.join(results))
```

`dcp.init()` alone must make pythonmonkey a fully-working dcp-client
platform (for both `exec()` and `localExec()`). `job.localExec()` alone
must work for any work function (JS or pyodide/Python), including
correctly propagating a broken work function's real error.

---

## 2. Current, real (not simulated) state of related work

These are already done, merged/open, independent of this effort:

- **PythonMonkey PR #509** — SpiderMonkey rebuilt to current mozilla-central
  (157a1) + SharedArrayBuffer/Atomics enabled.
  https://github.com/Distributive-Network/PythonMonkey/pull/509
- **PythonMonkey PR #510** — real `WebSocket` builtin module added.
  https://github.com/Distributive-Network/PythonMonkey/pull/510
- **dcp monorepo MR !3323** — pythonmonkey no longer excluded from the
  `['websocket','polling']` transport list (now uses WebSocket like every
  other platform). https://gitlab.com/Distributed-Compute-Protocol/dcp/-/merge_requests/3323
- **bifrost2 PR #49 — CLOSED, do not reuse.** Was a narrower `job.py`-only
  fix, judged incomplete/low-quality by the user.

None of the above four repos/PRs currently contain any of the
separate-process evaluator work below — that's all new, uncommitted, or
only in the branches noted in §6.

---

## 3. The core architectural finding

Read `src/dcp-client/worker/evaluators/node-localExec.js` in the dcp
monorepo (cloned locally at `C:\Users\danie\DCP\dcp-monorepo`, see §7 for
exact remote/commit info). It spawns a **child process**
(`child_process`, with `I_WANT_AN_INSECURE_DCP_WORKER` and
`DCP_SCHEDULER_LOCATION` env vars) connected over a socket/pipe — not an
in-process simulation.

Critically: the **client-side wire-protocol handler is platform-agnostic**.
`lib/standaloneWorker.js` (in the `dcp-client` repo, cloned locally at
`C:\Users\danie\DCP\dcp-client`) exports `StandaloneWorker`/`workerFactory`,
which just needs any `readStream`/`writeStream` — nothing Node-specific.
The wire protocol is line-based, newline-delimited:

- `LOG:<text>` — debug/log line, informational only, no action taken
- `DIE:` — child is shutting down (or parent telling child to shut down)
- `MSG:<json>` — a real message, JSON body has `type`:
  - `type: "workerMessage"` — a `postMessage()` payload, `message` field
    holds the actual JS value
  - `type: "result"` — with `exception` present (or not) to signal a slice
    succeeded/failed

This exact protocol is **already correctly implemented** on the pythonmonkey
side — `pm_localexec_setup.py`'s `install()` function's `writeln`/`onreadln`/
`die` globals are a from-scratch, in-process-only reimplementation of this
exact contract. That means the wire protocol doesn't need to be invented —
it needs to be connected to a **real socket** instead of fake in-process
dispatch.

**Decision (made explicitly by the user): build the real separate-process
version, not a formalized version of the shared-global hack.** The payoff:
eliminates essentially all of "Category A" below (console/require/timer
clobbering fixes, access-lists masking bypass) since a genuinely separate
process has its own JS global — nothing to clobber, nothing to mask.

---

## 4. Full fix inventory — what exists in `pm_localexec_setup.py` and where it needs to end up

Source: `C:\Users\danie\DCP\localexec_patch\pm_localexec_setup.py` (963
lines). Every function's exact docstring has real, hard-won reasoning —
read it before reimplementing, don't guess.

### Category A — pythonmonkey platform bootstrap (not localExec-specific; needed for `exec()` too)

| Function | Lines | What it does |
|---|---|---|
| `install()` | 65-195 | Builds a Worker-shaped evaluator constructor (`postMessage`/`onmessage`/`onerror`/`terminate`/`addEventListener`) matching what `Sandbox.start()` expects as a `SandboxConstructor`. Registers `globalThis.__pmEvaluatorCtor`. |
| `run_bootstrap_eagerly()` | 196-404 | Loads the 22-file sandbox bootstrap (BravoJS, access-lists, polyfills, pyodide-core, etc.) eagerly at top level rather than lazily nested (confirmed the lazy path stalls indefinitely). Also fixes 4 distinct global-clobbering bugs this causes (require, console, timers, XHR) by save/restore around the bootstrap call. |
| `fix_crypto_getrandomvalues()` | 452-484 | `crypto.getRandomValues` returns all zeros after the bootstrap runs (a stub wins via `Object.assign` source-ordering); restores a real one backed by `os.urandom`. |
| `fix_access_lists_masking()` | 485-539 | `access-lists.js`'s real sandbox-isolation logic nukes Supervisor-side globals (`dcpConfig` etc.) because pythonmonkey has no real separate realm; patches `Object.defineProperty` to no-op only this exact masking shape. |

**With a real separate-process child, this entire category should mostly
become unnecessary** — there's no shared global left to clobber or mask.
**Verify this empirically once the child-process bootstrap is built — do
not assume it; test it.** It's possible some subset is still needed even
in a fresh child process (e.g. if the 22 bootstrap files have bugs
independent of global-sharing) — find out by testing, not by assumption.

**Target home if still needed at all**: `dcp.init()` in bifrost2
(`dcp/initialization.py`'s `init()` closure, following the exact existing
"XXX apply dcp-client hacks XXX" convention already there for the
`getProcessPath` hack — see that file, already read this session).

### Category B — real `localExec()`-specific dcp-client bugs (still needed regardless of process architecture)

| Function | Lines | What it does |
|---|---|---|
| `route_job_arguments_through_local_files()` | 594-761 | `localExec()` otherwise unconditionally uploads job arguments/slice values to the real scheduler (`addSlices()`) regardless of size — defeats the point of *local* exec. Mirrors what Node's own `localExec()` does: route through local temp files instead. **Confirmed still needed this session** — removing it made the job hit a real `uploading` network state. |
| `force_job_completion_when_done()` | 832-928 | The local single-sandbox Worker never emits a terminating `'stop'` (starts a second `describe` round nobody replies to). Synthesizes a `'stop'`/`'complete'` once all expected slice results have arrived. **Confirmed still needed this session** — removing it hung indefinitely, zero result events. |
| `raise_on_first_work_error()` | 762-813 | **Not currently wired into any test script at all** — a real, unexercised bug: a broken work function currently returns normally from `localExec()`, fires `'error'` with an empty payload, and smuggles the real exception into the results list at a misaligned index. Hooks the same `"workError"` protocol message (see §3.3 below) to reject the underlying promise properly instead. |

Needed reason: these are dcp-client-level bugs in `localExec()`'s own
argument-upload path and completion detection — unrelated to whether the
worker is in-process or a real child process. Investigate whether a real
child process changes how completion/error signals arrive (it might — a
real child process may get to use `StandaloneWorker`'s already-correct
`'result'`/`'error'` event handling in `lib/standaloneWorker.js` lines
252-278, which already handles this properly for Node! **This may mean
Category B's `force_job_completion_when_done`/`raise_on_first_work_error`
become unnecessary too, IF the real child process correctly emits proper
`result`/exception messages the way `StandaloneWorker` already expects.**
This needs verification, not assumption — it's a promising simplification
but unconfirmed.

**Target home**: `Job.localExec()` in `dcp/api/job.py` (bifrost2) — same
file/method PR #49 touched, this time complete and tested.

### Category C — confirmed dead, already deleted from the canonical test script

| Function | Lines | Status |
|---|---|---|
| `start_fetchtask_keepalive()` | 405-450 | **Confirmed obsolete this session** — the `setInterval`-based watchdog timer-starvation bug it worked around does not reproduce on the rebuilt SpiderMonkey (157a1)/rewritten `JobQueue`. Removed, retested, job still completes correctly. |
| `patch_delay_manager()` | 544-593 | Same confirmed-obsolete finding, same test. |

**Do not port these anywhere.** They're gone for good, a real side benefit
of the PR #509 `JobQueue` rewrite this session — worth a mention in that
PR if not already there.

### Also needed: three small `dcp-client-bundle.js` patches, now understood to be real *monorepo* source changes

Source: `C:\Users\danie\DCP\localexec_patch\FIXES_SUMMARY.md` §3 (exact
diffs). These were previously applied as hand-patches to the *minified,
vendored* `dcp-client-bundle.js` — now traced to their real, editable
source in the `dcp` monorepo (see §7 for exact file paths):

1. **§3.1 localExec() platform gate** (`src/dcp-client/job/index.js`
   line ~645) — accept `"pythonmonkey"` as a valid `localExec()` platform,
   analogous to `"nodejs"`, using a `pythonmonkeyEvaluatorFactory()` (to be
   written, modeled on `nodeEvaluatorFactory()` in
   `src/dcp-client/worker/evaluators/node-localExec.js`) as the
   `SandboxConstructor`.
2. **§3.2 SocketIOTransport transports** — **already done**, MR !3323 (§2).
3. **§3.3 two `Sandbox.start()` onmessage hooks** — signals for
   `"complete"`/`"workError"` protocol messages, currently implemented as a
   hand-patch giving `pm_localexec_setup.py` a direct signal since the
   local single-sandbox simulation never fires real Job-level events.
   **Investigate whether a real child process needs these hooks at all**
   (see Category B note above — `StandaloneWorker` may already handle this
   correctly without needing bespoke hooks).

---

## 5. Progress so far this session (all in bifrost2, branch `pythonmonkey-platform-support`, NOT yet pushed/committed)

Directory: `C:\Users\danie\DCP\bifrost2\dcp\_pm_evaluator\` (new package).

- **`__init__.py`** — module docstring, wire protocol spec.
- **`channel.py`** — `EvaluatorChannel` class. Parent-side: spawns the
  child via direct script path (`subprocess.Popen([sys.executable,
  <path-to-child.py>, "--port", N])` — **deliberately NOT `-m
  dcp._pm_evaluator.child`**, which would force importing the entire `dcp`
  package first, confirmed slow/problematic), binds a TCP listener on an
  ephemeral port first, accepts the child's connection, then reads lines
  in a **background thread with blocking sockets** (not asyncio streams —
  see next bullet for why), delivering each line to `self.on_line` via
  `loop.call_soon_threadsafe()`.
- **Real bug found and fixed**: bifrost2's shared event loop
  (`dry.aio.loop`) has `nest_asyncio` applied (for pythonmonkey's
  reentrant event-loop needs elsewhere in the codebase). `nest_asyncio`'s
  patched loop **silently breaks plain asyncio `wait_for`/task scheduling**
  — confirmed via a real hang with zero exception (parent successfully
  spawned and connected to the child, per printed logs, but then just hung
  forever with no error). Switched from an asyncio-streams design to
  threads + blocking sockets specifically to sidestep this; do not go back
  to asyncio streams for this without first confirming `nest_asyncio`
  isn't going to bite again.
- **`child.py`** — **Stage 1 only, proof-of-plumbing, NOT the real sandbox
  child yet.** Connects to the given port, sends one `LOG:` line and one
  `MSG:{"type":"result","result":"stage1-ok"}` line, echoes any incoming
  `MSG:` as a `LOG:`, exits cleanly on `DIE:`. Deliberately has zero
  pythonmonkey/dcp involvement — pure stdlib socket code — to prove the
  subprocess+socket mechanics in isolation before adding complexity.
- **`_test_plumbing.py`** — smoke test, **currently passing**:
  ```
  [parent] spawning child...
  [parent] child connected in 0.09s, pid=9452
  [parent] received: LOG:pm evaluator child connected, pid=9452
  [parent] received: MSG:{"type":"result","result":"stage1-ok"}
  [parent] received: LOG:child received: {"type":"workerMessage","message":"hello from parent"}
  [parent] received: DIE:
  PLUMBING TEST PASSED
  ```
  Run with: `cd C:\Users\danie\DCP\bifrost2 && python -u -m dcp._pm_evaluator._test_plumbing`

**What this proves**: spawning a real child process and exchanging
messages over a real socket is fast (90ms) and reliable on this machine.
**What this does NOT yet prove**: that a real pythonmonkey instance can be
started inside that child, run the 22-file sandbox bootstrap in isolation,
and correctly execute a real work function. That's all still ahead.

---

## 5b. Further progress (this session, after §5) — real job.localExec() reaches real deployment

**Major finding: the whole separate-process architecture works, end to end, through real dcp-client deployment machinery**, using the EXISTING installed bundle's already-present §3.1 patch (`globalThis.__pmEvaluatorCtor` gate) — no monorepo change was even needed to reach this point.

Copied `dcp/_pm_evaluator/` into the site-packages `dcp` install (the known-working environment with all prior investigation patches already applied) and ran a real `job.localExec()` via `_test_real_job.py`. Progression across fixes:

1. **`evaluator.py` written and works.** Parent-side `globalThis.__pmEvaluatorCtor`, matching the exact shape from `pm_localexec_setup.py`'s `install()` (postMessage/onmessage/onerror/terminate/addEventListener), but internals route through a real `EvaluatorChannel` instead of fake in-process dispatch. Buffers `postMessage()` calls issued before the child finishes connecting (same pattern as `WebSocket.js`'s constructor).
2. **`child.py` stage 3 built and works**: real pythonmonkey instance in the child, portable bootstrap-file path resolution (via `importlib.util.find_spec('dcp')`, NOT the old hardcoded `C:\Users\danie\AppData\...` paths), all 22 sandbox bootstrap files load successfully in true isolation. Confirmed `writeln`/`onreadln`/`die` get deliberately deleted from `globalThis` by `sa-ww-simulation.js` after capturing them into a private closure (`/* Remove symbols from global scope that may be security leaks*/`) — **this is correct, intentional behavior, not a bug** (initially mis-flagged the check for this as a problem; it isn't).
3. **Hit `Error: module not found -- require('fs') from dcp-client/index.py`** the first time this ran against a *fresh* checkout that had never been patched. Root cause already known from the original investigation (FIXES_SUMMARY.md sec4.3) — `dcp-client/index.py` (itself part of the `dcp-client` npm package, confirmed by a fresh `npm i` reproducing the unpatched file) needs an `fs`/`os`/`child_process` shim for Supervisor-side code (`createBackingStore`/`obtainWorkerId`, i.e. the *parent* process establishing a persistent local-worker identity) that does real `require('fs')`. **This is unrelated to the new child-process work** — it's a parent-side (Supervisor) gap that exists regardless of evaluator architecture. Fixed by copying the already-patched `index.py` from the working site-packages install.
4. **Hit `DCPError: no transports defined` (DCPC-1014)** in the fresh checkout, confirmed via a control test to happen with *plain* `job.exec()` too — proving it was unrelated to any of this session's work. While investigating, the user relayed a diagnosis from a colleague (Tom Tang) of the **exact same class of bug**, found independently: `dcp/dry/aio.py` calls `nest_asyncio.apply()` unconditionally, which is broken under Python 3.14 (this machine's version) -- it doesn't propagate asyncio's "current task" context correctly, breaking any aiohttp call using `timeout=` (including pythonmonkey's `XMLHttpRequest-internal.py`, which backs DCP's socket.io polling transport) with `RuntimeError: Timeout should be used inside a task` *before the request is even sent* -- which dcp-client reports up as the much more confusing "no transports defined". **This is very likely also the same underlying cause of the `asyncio.wait_for` hang noted in §5 above** (`channel.py`'s original asyncio-streams design) -- both are "nest_asyncio broken on 3.14" symptoms. Applied the suggested fix to `dry/aio.py` (both this checkout and site-packages): only call `nest_asyncio.apply()` when a loop is *already running* in the current thread at import time (i.e. only when actually needed for Jupyter/web-server/GUI reentrant-loop support), not unconditionally. **This did NOT fully resolve the fresh-checkout "no transports defined" case** on retest -- there may be more than one contributing cause, or something else differs in that checkout. Not chased further this session (secondary to the core evaluator validation); the fix itself is real and worth keeping regardless. **`channel.py`'s thread-based design (built to work around the earlier `wait_for` hang) was NOT reverted back to asyncio streams after this fix** -- it works, wasn't broken, and reverting without retesting would be an unforced risk. Revisit only if there's a concrete reason to prefer the asyncio-streams version.
5. **With the working site-packages environment (all above fixes applied), the real job got all the way to**: `exec -> init -> preauth -> deploying -> listeners -> uploading`, then `DCPError: Could not connect to https://result-submitter.distributed.computer/result-submitter/ within 60s`. Confirmed NOT transient (reproduced twice). **This is expected and not yet a bug to fix** -- `route_job_arguments_through_local_files()` (Category B, per sec4) was deliberately not ported into the new evaluator flow yet; its whole purpose is keeping a local job's data off the real network, and result submission is very likely the same category of concern. This is the next real step, not a new mystery.

**Bottom line**: the separate-process architecture is now validated end-to-end through real dcp-client job deployment -- spawning, socket bridging, sandbox bootstrap, and the real `Sandbox.start()`/`DistributiveWorker` construction path all work. What's left is exactly what sec6 already outlined: port Category B's still-needed fixes (starting with local data routing) into the new flow, then re-verify whether the local-worker completion-detection/error-propagation hooks are still needed given the new architecture (per sec4's open question) or whether the real child process now handles this more correctly on its own.

### 5c. Session-ending blocker: external service outage, not a code issue

While testing whether `route_job_arguments_through_local_files()` (reused as-is from `pm_localexec_setup.py`, temporarily, just to check the hypothesis) fixes the `result-submitter.distributed.computer` timeout from sec5b item 5, hit a NEW failure: plain `dcp.init()` **alone**, with zero job/evaluator code involved, started failing with a real `HTTP Error 404: Not Found` from a `fetch()` call inside `dcp-client/index.py`'s own init sequence (some remote config/version check). Reproduced twice, consistently. **Confirmed NOT caused by this session's changes**: reverted the `nest_asyncio` gating fix (sec5b item 4) back to the original unconditional `nest_asyncio.apply()` and the exact same 404 still happened -- then restored the fix (it's independently correct and unrelated). This is external infrastructure instability -- almost certainly the same family of issues already confirmed earlier this session with `packages.distributed.computer` (real, reproducible 404s/502s on that service, independent of any client). Blocked further live testing when this was hit; **not a code problem to fix, a live-service dependency to wait out or verify against a different environment**.

**Resolved as expected/deliberate, not a bug**: confirmed with the user this was planned downtime -- "we took our services offline exactly at 1630hrs." Consistent with the evidence gathered before asking (6/6 repeated `curl` attempts against `https://scheduler.distributed.computer/etc/dcp-config.js` all returned a plain, consistent nginx 404 -- not the intermittent pattern seen with the actual `packages.distributed.computer` session-routing bug, which was the right thing to check first before assuming it was the same class of issue. It wasn't -- just an outage.

**If picking this up fresh**: first confirm `dcp.init()` succeeds at all (`python -c "import dcp; dcp.init()"`) before assuming any code-level regression. If it 404s on `<scheduler>/etc/dcp-config.js`, check whether DCP services are actually up before investigating further -- this exact failure has already been seen once and was just planned downtime, not a client bug.

## 5d. Code written during the outage (untested against live services -- verify first before trusting)

With DCP services down (planned outage, sec5c), continued with code-only work that doesn't need the network: writing the real (non-borrowed) versions of the still-needed fixes directly into `dcp/api/job.py` and wiring `evaluator.py` into `dcp/initialization.py`. **None of this has been tested against a real job yet** -- it imports cleanly (verified: `python -c "import dcp"` succeeds, no circular-import or syntax errors) but that's all that could be confirmed with services down.

**`dcp/api/job.py` changes** (this checkout, `pythonmonkey-platform-support` branch -- NOT yet copied to site-packages, NOT yet committed):

- **`_route_arguments_locally(self)`** (new method) -- a real port of `pm_localexec_setup.route_job_arguments_through_local_files()`'s file-rewriting half (KVIN-encode each `jobArguments`/`jobInputData` element, write to a local temp file, rewrite in place to a `file://` URL, `jobInputData` -> separate `marshaledDataValues` property). Same mechanism, ported to be a real `Job` method instead of an opt-in global hook. Returns `(grants, written_paths)` instead of stashing state in a module global.
- **`_grant_local_file_origins(self, grants, ...)`** (new method) -- the async-polling half (wait for `job.js_ref.localWorker.originManager` to exist, then grant one narrow per-file origin). Changed the retry loop from unbounded polling to a bounded `max_attempts` (200 x 0.05s = 10s) -- the original polled forever with no cap; add this back to being unbounded if 10s proves too short once tested, but an unbounded retry that silently never grants access on a genuine failure seemed worse than a bounded one that at least stops.
- **`localExec(self, *args, **kwargs)`** (new method, replacing the inherited generic-proxy fallback) -- calls `_before_exec()`, then `_route_arguments_locally()` synchronously (before the real JS `localExec()` call -- timing-critical, see the method's own docstring for why), then `_grant_local_file_origins()` (fire-and-forget, doesn't block), then delegates to `self.js_ref.localExec(*args, **kwargs)` via `dry.aio.blockify`, with the same error-unwrapping (`.jsError.message`) and return-value conversion (`Array.from` + per-element `deserialize`) already validated in the earlier (closed) PR #49 attempt. Cleans up temp files in a `finally` block.
- **Deliberately NOT ported yet**: `force_job_completion_when_done()`/`raise_on_first_work_error()`'s concerns. Per sec4's still-open question -- does the real child-process evaluator (via `StandaloneWorker`-compatible messaging) already handle local-worker completion/error signaling correctly on its own, making these unnecessary? -- porting them blind, without being able to test whether they're even still needed, would risk exactly the kind of "looks complete but wasn't verified" mistake this whole rework exists to fix. **This is the first thing to check once services are back**: run a real `job.localExec()` through the new code and see whether it hangs (needs the completion-detection fix) or silently mishandles a broken work function's error (needs the error-propagation fix) before porting either one.
- Added the matching explanatory note to `wait()` (why `.wait()` can't follow `.localExec()`), same reasoning as the closed PR #49.

**`dcp/initialization.py` changes**:
- `from ._pm_evaluator import evaluator as _pm_evaluator_module` at the top.
- `_pm_evaluator_module.install(aio.loop)` added inside `init()`, immediately before `js.dcp_client['init'](**kwargs)` -- registers the real `globalThis.__pmEvaluatorCtor` automatically, matching sec6 step 5's plan. Confirmed via `pm.eval('typeof globalThis.__pmEvaluatorCtor')` that it's `undefined` before `dcp.init()` runs and would need `dcp.init()` to actually reach this line to register it -- **not yet confirmed it successfully registers**, since `dcp.init()` couldn't complete (network down) far enough to reach this line in a real run. Once services are back, first check is simply: does `dcp.init()` now register the evaluator automatically, with zero manual `install_pm_evaluator(...)` call needed in the test script (unlike `_test_real_job.py`, sec5b, which called it manually)?

## 5e. Exact pickup sequence once DCP services are back online

1. Sanity check services are actually back: `curl -s -o /dev/null -w '%{http_code}\n' https://scheduler.distributed.computer/etc/dcp-config.js` should return `200`, not `404`.
2. Copy this checkout's `dcp/api/job.py`, `dcp/initialization.py`, and `dcp/_pm_evaluator/` into the site-packages install (same copy pattern used throughout sec5b/5c) -- OR switch to testing directly against this checkout once its own `dcp.init()` (fresh, unpatched `dcp-client` bundle) is confirmed working end-to-end independent of the site-packages shortcuts taken so far. Either is fine; site-packages is faster to unblock testing since it already has every other prerequisite patch (sec5b items 3-4) applied.
3. Run a real job with **zero manual evaluator install call** (letting `dcp.init()`'s new automatic wiring do it) -- e.g. adapt `_pm_evaluator/_test_real_job.py` to remove its manual `install_pm_evaluator(...)` line and confirm the evaluator ctor is present anyway.
4. Confirm the new `job.py`'s `localExec()` (with `_route_arguments_locally`/`_grant_local_file_origins` now real methods, not a borrowed external module) gets *past* the `result-submitter` timeout from sec5b item 5.
5. Once a real job completes: deliberately break a work function (make it raise) and confirm the error surfaces as a real Python exception with the actual traceback message -- this exercises the still-open `raise_on_first_work_error` question from sec4/5d. If it doesn't surface correctly, that's confirmation the fix is still needed and should be ported (from `pm_localexec_setup.py` lines 762-813) into `job.py` the same way the other two were.
6. If a job with more than a handful of slices, or a job that legitimately takes a while, hangs after all real results have arrived: that's confirmation `force_job_completion_when_done`'s concern is still needed too (port from lines 832-928).
7. Once real end-to-end success is confirmed (including error propagation): retest `pycomod_localexec_test.py` (heavier stress test) per sec6 step 6, then prepare the real PRs per sec6 step 7 -- monorepo MR (the `pythonmonkeyEvaluatorFactory()` + platform-gate change, sec4 item 1) and the bifrost2 PR (this branch), with a proper handoff doc.

## 6. Remaining steps, in order

1. **Build the real child process** (`child.py` stage 2). Replace the
   stage-1 stub with: import `pythonmonkey`, resolve the dcp-client
   bootstrap-file paths *portably* (not the hardcoded
   `C:\Users\danie\AppData\Roaming\...` paths `pm_localexec_setup.py`
   uses — resolve relative to the installed `dcp` package's own location,
   e.g. via `importlib.util.find_spec('dcp')`), run the same
   `BOOTSTRAP_FILES` list (copy the list from
   `pm_localexec_setup.py` lines 25-48, fix the paths), wire real
   `writeln`/`onreadln`/`die` globals to the actual socket (write out
   `LOG:`/`MSG:` lines instead of in-process dispatch; feed incoming
   socket lines to whatever `onreadln` registered). Test whether this
   genuinely-isolated bootstrap needs ANY of Category A's fixes — don't
   assume it doesn't just because the global is no longer shared; test it.
2. **Build the JS-side evaluator constructor** (parent, in bifrost2,
   injected via `pm.eval()` the same way `pm_localexec_setup.py` did) that
   wraps `EvaluatorChannel`: `postMessage()` writes a `MSG:` line via a
   Python bridge function exposed on `globalThis`; incoming lines
   (delivered via `channel.on_line`, called on the main loop thanks to
   `call_soon_threadsafe`) get parsed and dispatched to `onmessage`/
   `onerror`, matching `Sandbox.start()`'s expected contract exactly (same
   shape as the existing, proven `__pmEvaluatorCtor` in
   `pm_localexec_setup.py` lines 112-193 — reuse that shape, just change
   the internals to talk to a real channel instead of fake dispatch).
   Since spawning is not instant, buffer any `postMessage()` calls issued
   before the channel finishes connecting (same pattern already proven in
   `WebSocket.js`'s constructor this session — buffer-then-flush on
   connect).
3. **Test the JS↔Python bridge directly** against the stage-2 child,
   without going through real `Sandbox.start()`/dcp-client yet — construct
   the evaluator directly via `pm.eval()`, call `postMessage`, confirm
   `onmessage` fires with real data from the child's actual pythonmonkey
   instance.
4. **Monorepo changes** (`C:\Users\danie\DCP\dcp-monorepo`, need a fresh
   feature branch off `develop`):
   - `src/dcp-client/job/index.js` ~line 645: accept `"pythonmonkey"`
     platform (§4 item 1 above).
   - New file, modeled on `src/dcp-client/worker/evaluators/node-localExec.js`:
     a `pythonmonkeyEvaluatorFactory()` — but note, unlike Node's version,
     this doesn't need to do the spawning itself (that's already handled
     Python-side via `globalThis.__pmEvaluatorCtor`, exactly like the
     existing FIXES_SUMMARY.md §3.1 diff already established) — likely a
     much smaller file than `node-localExec.js`, just returning
     `globalThis.__pmEvaluatorCtor`.
   - Investigate/implement the `"complete"`/`"workError"` signal question
     from §4 Category B — determine whether `Sandbox.start()`'s existing
     onmessage handling (feeding into `StandaloneWorker`'s already-correct
     `'result'`/error dispatch) is now sufent once real socket messages are
     flowing, or whether the two bespoke hooks (§4 item 3) are still
     needed.
5. **bifrost2 changes**:
   - `dcp/initialization.py`: call the new evaluator-registration code
     automatically in `init()`, before `js.dcp_client['init'](**kwargs)`
     runs (ordering matters — confirmed by the original investigation).
     Only port whatever Category A fixes step 1's testing showed are still
     genuinely needed.
   - `dcp/api/job.py`: rewrite `localExec()` cleanly, folding in whatever
     Category B fixes are still needed after step 4's investigation
     (route-arguments-locally at minimum; completion/error detection only
     if still needed after checking `StandaloneWorker`'s existing handling).
6. **End-to-end test** against a real job. Use
   `C:\Users\danie\DCP\dcp_local_job_test.py` as the reference test job
   (uppercase-8-letters, Pyodide work function, `demo`/`dcp` compute
   group) — but the goal is for the **exact clean script in §1** to work,
   not a script with any manual patch wiring. Also retest
   `pycomod_localexec_test.py` (heavier stress test — filesystem shipping,
   extra Pyodide modules, cloudpickle round-trip) once the basic case
   works.
7. **Only once real, end-to-end, tested** — prepare PRs:
   - dcp monorepo MR (step 4's changes)
   - bifrost2 PR (step 5's changes) — this is the real replacement for the
     closed PR #49; make sure it's actually complete and tested this time,
     not another partial cut.
   - Write a handoff doc (matching the pattern of
     `SPIDERMONKEY_VERSION_BUMP.md`/`LOCALEXEC_PYODIDE_FIX_NOTES.md`)
     covering the full architecture, what was tested, what's flagged as
     needing review.

---

## 7. Repo/access reference

| Repo | Local path | Remote | Branch (this work) | Access |
|---|---|---|---|---|
| PythonMonkey | `C:\Users\danie\DCP\pythonmonkey-src` | `github.com/Distributive-Network/PythonMonkey` | (PRs #509, #510 already open on their own branches) | `gh`, push access confirmed |
| bifrost2 | `C:\Users\danie\DCP\bifrost2` | `github.com/Distributive-Network/bifrost2` | `pythonmonkey-platform-support` (current work, **not pushed yet**) | `gh`, push access confirmed |
| dcp monorepo | `C:\Users\danie\DCP\dcp-monorepo` | `gitlab.com:Distributed-Compute-Protocol/dcp.git` | `pythonmonkey-websocket-transport` used for MR !3323; **need a NEW branch off `develop` for this work** | SSH clone/push confirmed working (git only; `glab` installed but not authenticated) |
| dcp-client | `C:\Users\danie\DCP\dcp-client` | `gitlab.com:Distributed-Compute-Protocol/dcp-client.git` | detached at `v5.7.3`, clean, unmodified | read-only used so far; this repo is just a packaging wrapper around the monorepo (its `prepack` hook clones `dcp.git` and builds from there) — **the real source lives in dcp-monorepo, not here**, except `lib/standaloneWorker.js` which genuinely lives in *this* repo and is directly reusable (see §3) |

Tools: `gh` (GitHub CLI) installed portably at `C:\Users\danie\tools\bin\gh.exe`,
authenticated as `dan-distributive`. `glab` (GitLab CLI) installed
portably at `C:\Users\danie\tools\glab_extracted\bin\glab.exe`, **not
authenticated** (no browser device-flow available in this version; needs a
GitLab personal access token with `api`+`write_repository` scopes, or open
MRs manually via the printed `git push` URL).

Original investigation reference docs (read these for exact historical
reasoning, don't just take this plan doc's summaries as complete):
- `C:\Users\danie\DCP\localexec_patch\STATUS.md` — full investigation log
- `C:\Users\danie\DCP\localexec_patch\FIXES_SUMMARY.md` — clean summary of
  all fixes including the exact bundle diffs (§3)
- `C:\Users\danie\DCP\localexec_patch\pm_localexec_setup.py` — the actual
  963-line implementation being superseded/ported
- `C:\Users\danie\DCP\pythonmonkey-src\SPIDERMONKEY_VERSION_BUMP.md` — the
  SpiderMonkey rebuild handoff doc (PR #509), for the JobQueue-rewrite
  context behind Category C being obsolete
