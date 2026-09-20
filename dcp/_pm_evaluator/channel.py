"""
Parent-side channel: spawns the child evaluator process, listens for its
connection, and bridges line-based traffic to/from it.

Uses a background thread with plain blocking sockets, not asyncio streams:
bifrost2's shared loop has nest_asyncio applied (for pythonmonkey's
reentrant event-loop needs), which silently breaks asyncio task/timeout
scheduling. A thread reading a blocking socket sidesteps that; each line
is handed to the main loop via loop.call_soon_threadsafe().
"""
import json
import os
import socket
import subprocess
import sys
import threading

_CHILD_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "child.py")


class EvaluatorChannel:
    def __init__(self, loop):
        self.loop = loop
        self.proc: subprocess.Popen | None = None
        self.sock: socket.socket | None = None
        self.on_line = None  # callable(str) -> None; called ON THE MAIN LOOP/THREAD
        self._reader_thread = None
        self._stop = False

    def spawn_and_connect(self, connect_timeout=20):
        """Synchronous -- binds, spawns, accepts. Call this from a Python
        thread/context that's fine blocking briefly (the accept() wait is
        normally sub-second; the child does no heavy work before connecting)."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        srv.settimeout(connect_timeout)

        self.proc = subprocess.Popen([sys.executable, _CHILD_SCRIPT, "--port", str(port)])

        try:
            conn, _ = srv.accept()
        finally:
            srv.close()

        self.sock = conn
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        return self

    def _read_loop(self):
        buf = b""
        while not self._stop:
            try:
                data = self.sock.recv(4096)
            except OSError:
                break
            if not data:
                break
            buf += data
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                text = raw.decode("utf-8", errors="replace")
                if self.on_line:
                    self.loop.call_soon_threadsafe(self.on_line, text)

    def write_line(self, line: str):
        if self.sock is None:
            return
        try:
            self.sock.sendall((line + "\n").encode("utf-8"))
        except OSError:
            pass

    def terminate(self):
        # Bare JSON, not a "DIE:" line -- see child.py's _socket_reader.
        self.write_line(json.dumps({"type": "die"}))
        self._stop = True
        if self.proc:
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
