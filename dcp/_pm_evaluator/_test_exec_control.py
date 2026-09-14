"""Control test: does plain job.exec() (unrelated to the new evaluator)
also hit 'no transports defined' in this fresh checkout? Disambiguates a
general environment/config issue from something specific to localExec()."""
import json
import dcp
dcp.init()

import pythonmonkey as pm
from dcp.dry.aio import loop as _shared_loop

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
print("Using identity address:", address, flush=True)

input_set = list('yelling!')

def work_function(letter):
    dcp.progress()
    return letter.upper()

job = dcp.compute_for(input_set, work_function)
job.computeGroups = [{'joinKey': 'demo', 'joinSecret': 'dcp'}]
job.public.name = 'fresh-checkout-exec-control'
job.public.description = 'control test'
job.public.link = 'https://distributive.network'

job.on('readystatechange', lambda s: print(f"Ready State: {s}", flush=True))
job.on('accepted', lambda _: print(f"  Job ID: {job.id}", flush=True))
job.on('error', lambda e: print("error event:", json.dumps(e, indent=2), flush=True))
job.on('result', lambda r: print("result event:", json.dumps(r, indent=2), flush=True))

print("Calling job.exec()...", flush=True)
job.exec()
results = job.wait()
print(''.join(results))
print("EXEC CONTROL TEST COMPLETE")
