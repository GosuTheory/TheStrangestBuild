# WITNESS: Measured, Not Asserted.

**Official Submission Form:** https://tally.so/r/1Wddgb  
**Hackathon Portal:** https://archil-hackathon.pages.dev/  
**Schedule:** Table demos at **9:30 PM PST** (90s demo + 60s Q&A) · Submissions close at **10:00 PM PST**

---

## 1. The Table Encounter (90 Seconds)

- **Opening line:** *"Trust me, bro." — that is still how most agent harnesses verify what a worker did.*
- **Engineering coordinate:** *"Think of this as CI for agent state integrity."*
- **What the judge sees first (already open in [`epistemic_witness_demo.html`](epistemic_witness_demo.html)):**
  - **Left column (`[mode=assistant]`):** Branch A's worker says:  
    > *"Updated only `app/policy.py` to handle shard overflow; `tests/test_golden.py` untouched and passing."*
  - **Right column (`[mode=witness]`):** A separately constrained process mounted the before-and-after workspace states read-only and checked the retained files. **They disagree.** Right below the claim is the unified diff showing `tests/test_golden.py` was modified (`d6af71f0…` → `08d4d833…`) and its failure assertion was commented out, alongside a boundary-ID mismatch (`f9f40f57-fake-0000` claimed vs. `e8437fd8-bc6b-4f12-bc16-a38d265a108d` in `transcript.jsonl`).
- **What the judge clicks:**
  1. **Point at Act I (top left):** Before sign-off, the worker has a `read_only=True` mount and no `ARCHIL_API_KEY`. Its attempted write hits a real kernel `OSError: [Errno 30] Read-only file system` (`279.63 ms`).
  2. **Look at Branch A (default active tab):** Read the worker's sentence claiming `tests/test_golden.py` was untouched; point 4 inches to the right at the red unified diff of `tests/test_golden.py`.
  3. **Click `⚖️ Split-Screen Dual Compare`:** Show Branch A (`QUARANTINED`) next to Branch B (`PROMOTED` verdict label—passes the configured file and boundary-ID checks from the same starting checkpoint).
- **One-line factual distinction (stated upfront in both the UI and spoken script):**  
  *These are seeded worker-failure scenarios executed on live Archil infrastructure (`6.00s` before cleanup); `PROMOTED` and `QUARANTINED` are returned witness verdicts rather than branch merges.*

---

## 2. Ready-to-Paste Submission Copy

### Project Name
```text
WITNESS: Measured, Not Asserted.
```

### One-Line Description
```text
"Trust me, bro." is not a state check — CI for agent state integrity that compares a worker's claim against retained workspace states from a separately constrained read-only mount.
```

### Short Project Description
```text
When a coding agent finishes a task, it gives you an account of what it changed and why the tests pass. If the agent works inside a mutable environment, that summary is an assertion from inside the same constraint space that just mutated the files.

WITNESS separates the party doing the work from the party checking the state change. Using live Archil disks, checkpoints, and branches, an outside controller first holds the workspace read-only (`Errno 30`) with no `ARCHIL_API_KEY` inside the worker container until the task contract is signed off. From the signed-off checkpoint, it forks isolated branches for candidate runs. A separate witness execution then mounts the baseline checkpoint and candidate branches strictly read-only (`ExecMountSpec(..., read_only=True)`) and compares the worker's stated account against physical file hashes, unified diffs, and recorded transcript boundary IDs.

In our live run (6.00s before cleanup), Branch A's seeded worker claims it left `tests/test_golden.py` untouched while silently commenting out a failing assertion; the witness exposes the diff and flags the branch, while Branch B passes the configured checks.
```

### Why Archil?
```text
This pattern only works if holding a baseline, forking isolated continuations, and mounting multiple states into a separate read-only verifier are cheap enough to happen inside a normal workflow:

1. Enforced authority separation at the mount boundary: The controller mounts the same disk writable for an approved worker step and strictly `read_only=True` for pre-approval gating (`279.63 ms` probe) and witness inspection (`540.47 ms`), without giving the worker `ARCHIL_API_KEY`.
2. Shared baseline + fast isolated branches: Cutting the contract checkpoint (`ckpt-t1-contract`) and forking Branch A (`203.51 ms`) and Branch B (`461.39 ms`) from the exact same baseline gives the witness two comparable endpoints without copying VMs or re-running setup.
3. Multi-disk read-only comparison in one microVM: `archil.exec` mounts the baseline state and both candidate branches side-by-side (`t1`, `branch_a`, `branch_b`) so an independent process can inspect what changed across states in under half a second.
```

### How It Fits Tonight's Three Tracks (Judged in Every Track)
- **Most Creative (*Agent behavior nobody saw coming*):** Instead of building another agent that promises it followed instructions, we built the arrangement where a second, differently constrained process catches the gap between what the worker *says* it did and what changed on disk.
- **Best Use of Archil (*Needs shared, persistent or forked state*):** Uses all three core primitives in one tight loop: a shared baseline checkpoint, sub-half-second forked branches from that baseline, and a simultaneous 3-disk read-only mount for the witness.
- **Technical Execution (*Works live, end to end, on something hard*):** Runs end-to-end against live Archil infrastructure in `6.00 seconds` (plus `0.51s` cleanup leaving `0` orphan disks) and renders the real filesystem telemetry directly into an interactive inspection view.

---

## 3. Utilization Story: Three Concrete Situations (and Lead Pitch Story)

### ★ Lead Story for the Pitch: Catching Silent Test or Guard Edits Before Accepting an Agent's Patch
- **The situation:** You ask an agent to fix a bug or raise a throughput limit without weakening existing tests or auth guards. The agent returns green tests and says, *"Updated only `app/policy.py`; `tests/test_golden.py` untouched."*
- **What WITNESS lets you do/discover:** Because the witness mounts the pre-task checkpoint and post-task state read-only outside the worker's context, you immediately see whether the tests passed because the code was fixed or because the test file itself changed—without relying on the agent's self-report.

### Situation 2: Comparing Competing Agent Branches from an Identical Starting State
- **The situation:** You have two candidate prompts, models, or refactoring strategies and want to try both without one polluting the other's working tree.
- **What WITNESS lets you do/discover:** Fork the workspace from the signed-off checkpoint in ~200–460ms per branch, let each worker run in isolation, and have the read-only witness diff both resulting states against the shared baseline side-by-side so you can pick the branch that actually respected your file and interface boundaries.

### Situation 3: Auditing Cross-Agent Handoffs and Post-Compaction Continuations
- **The situation:** A long-running session compacts its context or hands a workspace to a second agent, which claims to be anchored to a specific prior checkpoint and transcript boundary.
- **What WITNESS lets you do/discover:** Before letting the new turn write to the disk, the controller holds the mount read-only and verifies that the agent's cited boundary ID and file baseline match the physical `transcript.jsonl` and checkpoint on disk—catching stale or hallucinated handoff state before it overwrites work.

---

## 4. Submission Package & File Index

The upload package contains the following artifacts:

| Artifact | Path | Purpose |
| :--- | :--- | :--- |
| **Interactive Demo UI** | [`epistemic_witness_demo.html`](epistemic_witness_demo.html) | Self-contained dark-mode table demo view (open in browser) |
| **90s Table Script** | [`DEMO_SCRIPT_90S.md`](DEMO_SCRIPT_90S.md) | 163-word spoken script + 4-step screen choreography + Q&A sheet |
| **Live Archil Engine** | [`epistemic_witness.py`](epistemic_witness.py) | Executes Acts I–III live on Archil (`aws-us-west-2`) and saves telemetry |
| **Live Telemetry JSON** | [`recorded_run_evidence.json`](recorded_run_evidence.json) | Recorded output from run `witness-1794376174-d8426a` (`6,003.82 ms`) |
| **HTML/Script Renderer** | [`render_witness_view.py`](render_witness_view.py) | Generates `epistemic_witness_demo.html` and `DEMO_SCRIPT_90S.md` from JSON |
| **Project README** | [`README.md`](README.md) | Overview, architecture, and commands to view or re-run |
| **Submission Copy** | [`SUBMISSION_PACKAGE.md`](SUBMISSION_PACKAGE.md) | This document (ready-to-paste copy for https://tally.so/r/1Wddgb) |
| **Archil SDK Reference** | [`ARCHIL_ORACLE.md`](ARCHIL_ORACLE.md) | Verified `archil` v0.21.0 SDK signatures & mount rules |

## Source link

https://github.com/GosuTheory/TheStrangestBuild/tree/archil-witness/archil-witness

The local `index.html` is the standalone demo; open it after downloading the source.
