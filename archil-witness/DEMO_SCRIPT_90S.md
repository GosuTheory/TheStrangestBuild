# WITNESS: Measured, Not Asserted — table demo

**Run:** `witness-1794376174-d8426a`  
**Format:** 90 seconds, then one minute of questions.  
**Display:** `epistemic_witness_demo.html`.

## Spoken script

“An agent can say it left your tests untouched. We built a way for another process to check that claim against the workspace.

First, before approval, the worker gets a read-only mount and no Archil API key. An attempted write actually fails with a read-only filesystem error.

After the approval step, we checkpoint the workspace and fork two branches from that same starting state.

These are deliberately scripted failure scenarios, executed on live Archil infrastructure. Branch A changes a protected test and claims it did not. Branch B makes the permitted code change and preserves the test.

A separate witness reads the baseline and both branches through read-only mounts. Here is the claim; here is the measured file difference. A is flagged. B passes the configured checks. The boundary-ID comparison also catches A's seeded mismatch.

The recorded cycle took 6.00 seconds before cleanup. The point is that the worker's explanation becomes a claim someone else can inspect.

Bingo Bongo. Show me the diff.”

## Screen choreography

1. Point to the read-only error and absent worker API key.
2. Select Branch A; show its assertion and the actual test diff.
3. Select Split-Screen Dual Compare; show A flagged and B passing.
4. Leave the diff visible for questions.

## Numbers for Q&A — do not read IDs aloud

| Measurement | Recorded value |
| --- | --- |
| Root disk | `dsk-000000000011907f` |
| Read-only probe | 279.63 ms |
| Branch A | `dsk-0000000000119081` / 203.51 ms |
| Branch B | `dsk-00000000001190a3` / 461.39 ms |
| Witness execution | 540.47 ms |
| Pipeline before cleanup | 6003.82 ms |

## Answers to keep precise

- Real infrastructure run; scripted worker changes and assistant claims.
- PROMOTED / QUARANTINED are returned verdicts. This demo does not merge branches.
- Boundary-ID match is structural, not proof of semantic re-anchoring.
- Filesystem hashes/diffs show endpoint differences, not every intervening action.
- The controller and verifier remain trusted; read-only mounts limit the worker's granted access.
