"""
Parent-side: the real `globalThis.__pmEvaluatorCtor` -- a Worker-shaped
(postMessage/onmessage/onerror/terminate/addEventListener) constructor
matching what dcp-client's Sandbox.start() expects as a SandboxConstructor
(see FIXES_SUMMARY.md sec3.1 / node-localExec.js's nodeEvaluatorFactory
for the reference contract). Backed by a REAL child process
(EvaluatorChannel), not the old in-process simulation.
"""
import asyncio

import pythonmonkey as pm

from .channel import EvaluatorChannel

_ctor_factory = pm.eval("""
(spawnAndGetHandle) => {
  return function PythonMonkeyEvaluator(_options) {
    var self = this;
    this.onmessage = null;
    this.onerror = null;
    this._listeners = {};
    this.addEventListener = function(type, listener) {
      (self._listeners[type] = self._listeners[type] || []).push(listener);
    };
    this.removeEventListener = function(type, listener) {
      if (!self._listeners[type]) return;
      self._listeners[type] = self._listeners[type].filter((l) => l !== listener);
    };

    var terminated = false;
    var sendBuffer = [];
    var channelWrite = null;
    var channelTerminate = null;

    function fireEnd() {
      Promise.resolve().then(() => {
        (self._listeners['end'] || []).forEach((fn) => { try { fn(); } catch (e) {} });
      });
    }

    function handleLine(line) {
      if (terminated) return;
      if (line.indexOf('LOG:') === 0) return;
      if (line.indexOf('DIE:') === 0) {
        terminated = true;
        fireEnd();
        return;
      }
      if (line.indexOf('MSG:') !== 0) return;
      var obj;
      try { obj = JSON.parse(line.slice(4)); } catch (e) { return; }
      Promise.resolve().then(() => {
        if (obj.type === 'workerMessage' && self.onmessage) {
          self.onmessage({ data: obj.message });
        } else if (obj.type === 'result' && obj.exception && self.onerror) {
          self.onerror(obj.exception);
        }
      });
    }

    this.postMessage = function(msg) {
      var line = 'MSG:' + JSON.stringify({ type: 'workerMessage', message: msg });
      if (channelWrite) channelWrite(line);
      else sendBuffer.push(line);
    };

    this.terminate = function() {
      if (terminated) return;
      terminated = true;
      if (channelTerminate) channelTerminate();
      fireEnd();
    };

    spawnAndGetHandle(handleLine).then((handle) => {
      if (terminated) { handle.terminate(); return; }
      channelWrite = handle.write;
      channelTerminate = handle.terminate;
      for (var i = 0; i < sendBuffer.length; i++) channelWrite(sendBuffer[i]);
      sendBuffer = [];
    }).catch((e) => {
      console.error('PythonMonkeyEvaluator: spawn failed:', e);
      terminated = true;
      fireEnd();
    });
  };
}
""")


def install(loop: asyncio.AbstractEventLoop):
    """Registers globalThis.__pmEvaluatorCtor, backed by real child
    processes. Call once, before dcp-client's own init runs (matching the
    ordering the original in-process version required -- unverified
    whether that ordering constraint still applies here, but preserved
    out of caution until tested otherwise)."""

    async def _spawn_and_get_handle(on_line_js_callback):
        channel = EvaluatorChannel(loop)
        channel.on_line = on_line_js_callback
        await loop.run_in_executor(None, channel.spawn_and_connect)
        return {"write": channel.write_line, "terminate": channel.terminate}

    pm.globalThis["__pmEvaluatorCtor"] = _ctor_factory(_spawn_and_get_handle)
