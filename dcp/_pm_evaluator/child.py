"""
Entry point for the separate-process pythonmonkey evaluator's child side.
Invoked as: python <this file> --port <N>   (direct script path, NOT
`-m dcp._pm_evaluator.child` -- see channel.py's comment on _CHILD_SCRIPT).
"""
import argparse
import asyncio
import importlib.util
import os
import socket
import sys
import threading


def _bootstrap_files():
    """Resolved relative to the installed `dcp` package, not a hardcoded path,
    since this runs as a standalone child process that may live anywhere."""
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

    # access-lists.js masks every *configurable* global not on its allowlist
    # (see below) -- including our own bridge functions, since a real Node
    # sandbox never has extras like these to mask. Non-configurable is the
    # escape hatch its own masking code already checks for.
    def _define_protected_global(name, value):
        pm.globalThis[name] = value
        pm.eval(f"""
        Object.defineProperty(globalThis, {name!r}, {{
          value: globalThis[{name!r}],
          writable: true,
          configurable: false,
          enumerable: false,
        }});
        """)

    _define_protected_global("__pmChildWriteLine", _write_line)

    # url.js only reads globalThis.location on engines that already have a
    # native URL (pythonmonkey does; Node's bare sandbox doesn't, so it never
    # hits this branch there). Nothing else in this pipeline sets `location`.
    pm.eval("globalThis.location = new URL('file:///');")

    should_exit = threading.Event()

    def _die():
        # Tell the parent we're dying, then actually stop this process --
        # writing the socket line alone doesn't end the event loop.
        _write_line("DIE:")
        should_exit.set()

    _define_protected_global("__pmChildDie", _die)

    # The parent sends 'describe' the instant the socket connects, before
    # this process has even started its bootstrap -- and the handler that
    # answers it (calculate-capabilities.js) isn't registered until file #21
    # of 22. Node's real evaluator avoids this because it runs its whole
    # bootstrap before ever reading its input stream, so early messages just
    # sit in the OS pipe buffer. We read eagerly instead, so anything that
    # arrives before the bootstrap fully finishes must be buffered and
    # replayed afterward (_flush_pending, called from _wait_for_exit below).
    _pending_lines = []
    _bootstrap_done = threading.Event()

    pm.eval("""
    globalThis.writeln = function(line) {
      globalThis.__pmChildWriteLine(line);
    };
    // Same non-configurable protection as the bridge globals above --
    // access-lists.js would otherwise mask this too. Stays writable so
    // onreadln() can keep reassigning it.
    Object.defineProperty(globalThis, '__pmOnReadlnHandler', {
      value: null,
      writable: true,
      configurable: false,
      enumerable: false,
    });
    globalThis.onreadln = function(fn) { globalThis.__pmOnReadlnHandler = fn; };
    globalThis.die = function() { globalThis.__pmChildDie(); };
    """)

    def _socket_reader():
        # The wire protocol is asymmetric: LOG:/DIE:/MSG: prefixes are only
        # used in the child->parent direction (sa-ww-simulation.js's send()).
        # The parent always writes bare JSON, so every line here goes
        # straight to the onreadln handler with no prefix routing.
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
                if text:
                    loop.call_soon_threadsafe(_dispatch_incoming, text)
        should_exit.set()

    def _dispatch_incoming(line: str):
        if not _bootstrap_done.is_set():
            _pending_lines.append(line)
            return
        handler = pm.eval("globalThis.__pmOnReadlnHandler")
        # pm.eval("null") returns the `pythonmonkey.null` type itself, which
        # is truthy like any class -- `if handler:` alone can't tell "no
        # handler yet" from a real one, and calling the type raises instead.
        if handler and handler is not pm.null:
            handler(line)
        else:
            _pending_lines.append(line)

    def _flush_pending():
        # Runs once the bootstrap is fully done, so every listener
        # (including calculate-capabilities.js's) is registered.
        _bootstrap_done.set()
        handler = pm.eval("globalThis.__pmOnReadlnHandler")
        if handler and handler is not pm.null:
            while _pending_lines:
                handler(_pending_lines.pop(0))

    reader_thread = threading.Thread(target=_socket_reader, daemon=True)
    reader_thread.start()

    _write_line("LOG:pm evaluator child: pythonmonkey ready, pid=%d" % __import__("os").getpid())

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

    # sa-ww-simulation.js deletes its own writeln/onreadln/die once captured
    # privately -- expected to read False here, not a clobbering bug.
    still_ours = pm.eval("typeof globalThis.writeln === 'function' && typeof globalThis.onreadln === 'function'")
    _write_line(f"LOG:writeln/onreadln still intact after bootstrap: {still_ours}")

    async def _wait_for_exit():
        # Must run inside this active loop, not in the synchronous gap
        # before it: calculate-capabilities.js's 'describe' handler is
        # async and needs pythonmonkey's Python/JS event-loop bridge
        # (PyEventLoop::getRunningLoop()), which only finds a loop that is
        # actually running on this thread right now.
        _flush_pending()
        while not should_exit.is_set():
            await asyncio.sleep(0.05)

    loop.run_until_complete(_wait_for_exit())
    sock.close()


if __name__ == "__main__":
    main()
