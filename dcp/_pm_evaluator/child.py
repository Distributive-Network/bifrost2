"""
Entry point for the separate-process pythonmonkey evaluator's child side.
Invoked as: python <this file> --port <N>   (direct script path, NOT
`-m dcp._pm_evaluator.child` -- see channel.py's comment on _CHILD_SCRIPT
for why: `-m` forces importing the whole `dcp` package first, which this
process does not need and which was confirmed to slow/complicate startup).

STAGE 2 (current): adds a real pythonmonkey instance and wires writeln/
onreadln/die to the real socket, matching the wire protocol StandaloneWorker
(dcp-client's lib/standaloneWorker.js) expects on its read side. Does NOT
yet run the 22-file sandbox bootstrap -- that's the next stage, added only
once this stage is confirmed working (pythonmonkey starts reliably in a
spawned subprocess, and the writeln/onreadln bridge works end to end).
"""
import argparse
import asyncio
import importlib.util
import os
import socket
import sys
import threading


def _bootstrap_files():
    """Portable resolution of the 22 sandbox control-code files -- NOT the
    hardcoded C:\\Users\\danie\\AppData\\... paths pm_localexec_setup.py
    used. Resolved relative to wherever `dcp` is actually installed."""
    spec = importlib.util.find_spec("dcp")
    dcp_dir = os.path.dirname(spec.origin)
    js_root = os.path.join(dcp_dir, "js", "node_modules")
    dcp_client = os.path.join(js_root, "dcp-client")
    sandbox = os.path.join(dcp_client, "libexec", "sandbox")
    return [
        os.path.join(js_root, "kvin", "kvin.js"),
        os.path.join(sandbox, "sa-ww-simulation.js"),
        os.path.join(sandbox, "script-load-wrapper.js"),
        os.path.join(sandbox, "timer-classes.js"),
        os.path.join(sandbox, "wrap-event-listeners.js"),
        os.path.join(sandbox, "event-loop-virtualization.js"),
        os.path.join(sandbox, "lift-webgl.js"),
        os.path.join(sandbox, "lift-wasm.js"),
        os.path.join(sandbox, "lift-webgpu.js"),
        os.path.join(sandbox, "url.js"),
        os.path.join(sandbox, "polyfills.js"),
        os.path.join(sandbox, "access-lists.js"),
        os.path.join(sandbox, "fetch-factory.js"),
        os.path.join(sandbox, "bravojs-init.js"),
        os.path.join(js_root, "bravojs", "bravo.js"),
        os.path.join(sandbox, "bravojs-env.js"),
        os.path.join(sandbox, "worktimes.js"),
        os.path.join(sandbox, "pyodide-core.js"),
        os.path.join(sandbox, "pyodide-worktime.js"),
        os.path.join(sandbox, "map-basic-worktime.js"),
        os.path.join(sandbox, "calculate-capabilities.js"),
        os.path.join(sandbox, "bootstrap.js"),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", args.port))

    import pythonmonkey as pm

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _write_line(line: str):
        try:
            sock.sendall((line + "\n").encode("utf-8"))
        except OSError:
            pass

    pm.globalThis["__pmChildWriteLine"] = _write_line

    # Same writeln contract as the real sandbox control-code files expect
    # (see pm_localexec_setup.py's install(), which this mirrors) -- but
    # now genuinely writing to a real socket instead of fake in-process
    # dispatch.
    pm.eval("""
    globalThis.writeln = function(line) {
      globalThis.__pmChildWriteLine(line);
    };
    globalThis.__pmOnReadlnHandler = null;
    globalThis.onreadln = function(fn) { globalThis.__pmOnReadlnHandler = fn; };
    globalThis.die = function() { globalThis.__pmChildWriteLine('DIE:'); };
    """)

    should_exit = threading.Event()

    def _socket_reader():
        buf = b""
        while True:
            try:
                data = sock.recv(4096)
            except OSError:
                break
            if not data:
                break
            buf += data
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                text = raw.decode("utf-8", errors="replace")
                if text.startswith("DIE:"):
                    should_exit.set()
                    return
                elif text.startswith("MSG:"):
                    loop.call_soon_threadsafe(_dispatch_incoming, text[4:])
        should_exit.set()

    def _dispatch_incoming(json_text: str):
        handler = pm.eval("globalThis.__pmOnReadlnHandler")
        if handler:
            # onreadln handlers, per the real protocol, receive the RAW
            # "MSG:<json>\n" line, not the decoded payload -- matches
            # pm_localexec_setup.py's writeln() parsing the raw line itself.
            handler("MSG:" + json_text + "\n")

    reader_thread = threading.Thread(target=_socket_reader, daemon=True)
    reader_thread.start()

    _write_line("LOG:pm evaluator child: pythonmonkey ready, pid=%d" % __import__("os").getpid())

    # STAGE 3: run the real 22-file sandbox bootstrap, in TRUE isolation --
    # this process's JS global is used for NOTHING else (no shared
    # "Supervisor" role), so console/require/timer clobbering and
    # access-lists masking should not be able to break anything else the
    # way they did in the old in-process simulation. Verifying that
    # empirically here, not assuming it.
    async def _run_bootstrap():
        for f in _bootstrap_files():
            _write_line(f"LOG:[bootstrap] loading {f}")
            try:
                src = open(f, encoding="utf-8").read()
                pm.eval(src)
            except Exception as e:
                _write_line(f"LOG:[bootstrap] FAILED loading {f}: {type(e).__name__}: {e}")
                raise
            _write_line(f"LOG:[bootstrap] done {f}")

    try:
        loop.run_until_complete(_run_bootstrap())
        _write_line("LOG:[bootstrap] all 22 files loaded successfully")
    except Exception as e:
        _write_line(f"LOG:[bootstrap] ABORTED: {type(e).__name__}: {e}")
        sock.close()
        sys.exit(1)

    # Confirm writeln/onreadln/die are still OUR functions after the
    # bootstrap ran (i.e. nothing in the 22 files redefined them out from
    # under us) -- this is exactly the kind of clobbering that broke the
    # in-process simulation; check it explicitly rather than assume
    # isolation fixed it.
    still_ours = pm.eval("typeof globalThis.writeln === 'function' && typeof globalThis.onreadln === 'function'")
    _write_line(f"LOG:writeln/onreadln still intact after bootstrap: {still_ours}")

    async def _wait_for_exit():
        while not should_exit.is_set():
            await asyncio.sleep(0.05)

    loop.run_until_complete(_wait_for_exit())
    sock.close()


if __name__ == "__main__":
    main()
