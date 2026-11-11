# WITNESS: Measured, Not Asserted

**“Trust me, bro” is not a state check.** WITNESS is a live Archil demonstration of checking an agent’s account against retained workspace states from a separately constrained, read-only verifier.

The recorded run (`witness-1794376174-d8426a`) took **6,003.82 ms before cleanup** (another **514.84 ms**). Its worker actions were seeded scenarios run on live Archil infrastructure; this demonstrates the verification arrangement, not autonomous agents independently choosing to cheat. `PROMOTED` and `QUARANTINED` are verifier verdict labels. The demo does not merge branches.

## The three acts

1. **Gate:** Before sign-off, the worker is given a read-only workspace mount and no `ARCHIL_API_KEY`. A write attempt fails with the filesystem’s `Read-only file system` error.
2. **Branch:** After sign-off, WITNESS checkpoints the contract state and forks two isolated candidate branches from that shared baseline.
3. **Witness:** A separate execution mounts the baseline and both candidate states read-only. It checks configured file hashes and diffs, plus a recorded transcript boundary ID. In the seeded encounter, Branch A changes a protected test while claiming it did not; Branch B preserves the test and passes the configured checks.

The comparison identifies endpoint differences. A boundary-ID match is structural evidence, not proof of semantic continuity or re-anchoring. The controller and verifier remain trusted; read-only mounts constrain the worker’s granted access.

## Where it is useful

- **Reviewing a patch:** Check whether a claimed code fix also changed a protected test, policy, or guard.
- **Comparing alternatives:** Run candidate prompts, models, or refactors from the same checkpoint and inspect their resulting states side by side.
- **Checking a handoff:** Compare a claimed checkpoint or transcript boundary with the recorded workspace before a continuation is allowed to write.

## View the recorded demo

The recorded view works without an Archil key. Open [`epistemic_witness_demo.html`](epistemic_witness_demo.html) in a browser, or regenerate it and the 90-second demo script from the checked-in evidence:

```powershell
python -X utf8 render_witness_view.py --evidence recorded_run_evidence.json
```

The renderer writes [`epistemic_witness_demo.html`](epistemic_witness_demo.html) and [`DEMO_SCRIPT_90S.md`](DEMO_SCRIPT_90S.md) beside the renderer by default.

## Run the live Archil demonstration

Only the live runner needs an Archil API key. In a Python environment, install the Archil Python SDK (`archil==0.21.0`) and configure `ARCHIL_API_KEY`. The engine defaults `ARCHIL_REGION` to `aws-us-west-2` when it is unset. From the WSL environment used for this repo:

```bash
/home/computer/archil-hack/.venv/bin/python -m pip install 'archil==0.21.0'
```

```bash
bash -lc '/home/computer/archil-hack/.venv/bin/python /mnt/c/Users/computer/archil-hack-relay/epistemic_witness.py'
```

Evidence from a new live run is saved beside the engine as `live_run_evidence.json` (or at `--output PATH`); it does not replace the checked-in recorded evidence. Failed runs exit nonzero and retain error evidence.

The engine creates temporary disks and cleans them up after the run. Use `--keep` only when you need to preserve them for inspection.

## Project files

- [`epistemic_witness.py`](epistemic_witness.py) — live Archil runner.
- [`recorded_run_evidence.json`](recorded_run_evidence.json) — recorded run telemetry and witness report.
- [`render_witness_view.py`](render_witness_view.py) — renderer for the HTML demo and spoken script.
- [`epistemic_witness_demo.html`](epistemic_witness_demo.html) — standalone interactive demo view.
- [`DEMO_SCRIPT_90S.md`](DEMO_SCRIPT_90S.md) — 90-second table-demo script and precise Q&A notes.
- [`SUBMISSION_PACKAGE.md`](SUBMISSION_PACKAGE.md) — submission copy and detailed demo framing.
- [`ARCHIL_ORACLE.md`](ARCHIL_ORACLE.md) — SDK and runtime reference notes.

## Check the verifier

```powershell
python -m unittest -v test_epistemic_witness.py
```

Fifteen offline tests exercise retained history, deletions, missing evidence, isolation checks, and saved failure reports.
