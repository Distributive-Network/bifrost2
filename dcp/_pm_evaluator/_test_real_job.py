"""
STAGE 4 test: a REAL job.localExec() call through the real separate-process
evaluator, no Category A/B patches applied at all -- testing what actually
still breaks, empirically, rather than assuming.
"""
import sys
sys.path.insert(0, r"C:\Users\danie\DCP\bifrost2")  # use THIS checkout of dcp, not site-packages

import json
import dcp
dcp.init()

import pythonmonkey as pm
from dcp._pm_evaluator.evaluator import install as install_pm_evaluator
from dcp.dry.aio import loop as _shared_loop

install_pm_evaluator(_shared_loop)
print("Evaluator constructor installed:", pm.eval("typeof globalThis.__pmEvaluatorCtor"))

# Real identity via id.keystore, same safe pattern as the working tests.
_load_id_keystore = pm.eval("""
async () => {
  const wallet = dcp.wallet;
  const identity = dcp.identity;
  const idKeystore = await wallet.get('id', { KeystoreConstructor: wallet.IdKeystore });
  identity.set(idKeystore);
  return idKeystore.address.toString();
}
""")

async def _load_identity():
    return await _load_id_keystore()

address = _shared_loop.run_until_complete(_load_identity())
print("Using identity address:", address)

input_set = list('yelling!')

def work_function(letter):
    dcp.progress()
    return letter.upper()

job = dcp.compute_for(input_set, work_function)
job.computeGroups = [{'joinKey': 'demo', 'joinSecret': 'dcp'}]
job.public.name = 'pm-real-evaluator-test'
job.public.description = 'Real separate-process evaluator test'
job.public.link = 'https://distributive.network'

job.on('readystatechange', lambda s: print(f"Ready State: {s}", flush=True))
job.on('accepted', lambda _: print(f"  Job ID: {job.id}", flush=True))
job.on('error', lambda e: print("error event:", json.dumps(e, indent=2), flush=True))
job.on('result', lambda r: print("result event:", json.dumps(r, indent=2), flush=True))

print("Calling job.localExec()...", flush=True)
results = job.localExec()
print(''.join(results))
print("REAL JOB TEST COMPLETE")
