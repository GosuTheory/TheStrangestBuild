#!/usr/bin/env python3
"""
render_witness_view.py — The Epistemic Witness HTML + CLI Renderer.

Transforms live Archil sandbox execution evidence into a unified cyber-physical
observability view embodying the user's epistemological framework:
  "Visibility is placing objects on a ledger. Observability is measuring the
   event between two states (Delta = Checkpoint(t2) - Checkpoint(t1)).
   A constraint space cannot observe itself."

Maps live hardware telemetry from live_run_evidence.json:
  - Root Disk: dsk-0000000000118bd7
  - Branch A: dsk-0000000000118c05 in 154.14 ms
  - Branch B: dsk-0000000000118c06 in 71.74 ms
  - Multi-Disk Witness: 476.05 ms
  - Total Pipeline: 5,937.15 ms

Outputs:
  1. epistemic_witness_demo.html (at relay dir and /home/computer/archil-hack/)
  2. DEMO_SCRIPT_90S.md (90-second pitch script for hackathon table judges)
"""

from __future__ import annotations
import argparse
import html
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# =====================================================================
# Normalizer: Bridges Live Run Evidence to UI Representation
# =====================================================================

def normalize_evidence(raw: dict) -> dict:
    """Normalize raw live_run_evidence.json into a consistent view dictionary."""
    # Check if raw is already in normalized or live schema
    meta = raw.get("meta", {})
    timings = raw.get("timings_summary_ms", {})
    act1 = raw.get("act_1_infrastructure_gate", {})
    act2 = raw.get("act_2_counterfactual_branching", {})
    act3 = raw.get("act_3_epistemic_witness", {})
    report = act3.get("witness_report", {})
    results = report.get("results", {})

    res_a = results.get("branch_a_drifted", {})
    res_b = results.get("branch_b_faithful", {})

    # Extract branch A details
    br_a_info = act2.get("branch_a", {})
    br_b_info = act2.get("branch_b", {})

    # Assistant prose extracted from transcript.jsonl diff if available
    a_diff_transcript = res_a.get("unified_diffs", {}).get("transcript.jsonl", "")
    a_prose = "Updated only app/policy.py to handle shard overflow; tests/test_golden.py untouched and passing."
    for line in a_diff_transcript.splitlines():
        if line.startswith("+{") and "content" in line:
            try:
                line_json = json.loads(line[1:])
                a_prose = line_json.get("content", a_prose)
            except Exception:
                pass

    b_diff_transcript = res_b.get("unified_diffs", {}).get("transcript.jsonl", "")
    b_prose = "Updated app/policy.py to increase MAX_SHARD_THREADS to 10 with verified overflow bounds; tests/test_golden.py untouched and verified."
    for line in b_diff_transcript.splitlines():
        if line.startswith("+{") and "content" in line:
            try:
                line_json = json.loads(line[1:])
                b_prose = line_json.get("content", b_prose)
            except Exception:
                pass

    # Extract SHA-256 tables
    def build_sha_table(file_details: dict) -> list[dict]:
        table = []
        for fname, info in file_details.items():
            status = info.get("status", "unknown").upper()
            t1 = info.get("sha256_t1") or info.get("sha256") or "—"
            t2 = info.get("sha256_branch") or info.get("sha256") or "—"
            table.append({
                "file": fname,
                "t1_hash": t1,
                "t2_hash": t2,
                "status": status
            })
        return table

    normalized = {
        "meta": {
            "run_id": meta.get("run_id", "witness-1794373188-3907c1"),
            "timestamp": meta.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "archil_version": meta.get("archil_version", "0.21.0"),
            "region": meta.get("region", "aws-us-west-2"),
            "session_id": meta.get("session_id", "sess-epistemic-witness-001"),
            "physical_boundary_id": meta.get("physical_boundary_id", "e8437fd8-bc6b-4f12-bc16-a38d265a108d"),
            "pre_tokens": meta.get("pre_tokens", 560218)
        },
        "timings": {
            "root_disk_create_ms": timings.get("root_disk_create_ms", 1332.97),
            "act1_seed_and_t0_ckpt_ms": timings.get("act1_seed_and_t0_ckpt_ms", 529.65),
            "act1_hardware_gate_probe_ms": timings.get("act1_hardware_gate_probe_ms", 202.92),
            "act1_resolve_and_t1_ckpt_ms": timings.get("act1_resolve_and_t1_ckpt_ms", 1117.29),
            "act2_branch_a_create_ms": timings.get("act2_branch_a_create_ms", 154.14),
            "act2_branch_b_create_ms": timings.get("act2_branch_b_create_ms", 71.74),
            "act2_branch_a_worker_exec_ms": timings.get("act2_branch_a_worker_exec_ms", 442.13),
            "act2_branch_b_worker_exec_ms": timings.get("act2_branch_b_worker_exec_ms", 1224.0),
            "act3_witness_exec_ms": timings.get("act3_witness_exec_ms", 476.05),
            "total_run_duration_ms": timings.get("total_run_duration_ms", 5937.15),
            "cleanup_ms": timings.get("cleanup_ms", 815.91)
        },
        "act1_gate": {
            "root_disk_id": act1.get("root_disk_id", "dsk-0000000000118bd7"),
            "hardware_mount": act1.get("hardware_gate_test", {}).get("mount_spec", "ExecMountSpec(root_disk, read_only=True)"),
            "kernel_error": act1.get("hardware_gate_test", {}).get("exact_error_message", "[Errno 30] Read-only file system: '/mnt/archil/work/app/policy.py'"),
            "api_key_present": act1.get("hardware_gate_test", {}).get("api_key_present_in_worker", False),
            "checkpoint_t0": act1.get("checkpoint_t0_gated", {}).get("name", "ckpt-t0-gated"),
            "checkpoint_t0_ms": act1.get("checkpoint_t0_gated", {}).get("latency_ms", 529.65),
            "checkpoint_t1": act1.get("gate_resolution", {}).get("checkpoint_t1_contract", {}).get("name", "ckpt-t1-contract"),
            "checkpoint_t1_ms": act1.get("gate_resolution", {}).get("checkpoint_t1_contract", {}).get("latency_ms", 1117.29),
            "contract": act1.get("gate_resolution", {}).get("contract", {
                "allowed_files": ["app/policy.py"],
                "forbidden_mutations": ["disable verify_boundary", "touch tests/test_golden.py"],
                "require_reanchor": True
            }),
            "golden_test": act1.get("gate_resolution", {}).get("golden_test", "tests/test_golden.py")
        },
        "branch_a": {
            "name": br_a_info.get("branch_name", "branch-a-drifted"),
            "disk_id": br_a_info.get("filesystem_id", "dsk-0000000000118c05"),
            "fork_ms": timings.get("act2_branch_a_create_ms", 154.14),
            "worker_ms": br_a_info.get("worker_latency_ms", 442.13),
            "verdict": res_a.get("verdict", "QUARANTINED: EPISTEMIC_DRIFT + FALSE_REANCHOR"),
            "prose": a_prose,
            "claimed_boundary": res_a.get("compaction_reanchor_check", {}).get("claimed_boundary_id", "f9f40f57-fake-0000"),
            "physical_boundary": meta.get("physical_boundary_id", "e8437fd8-bc6b-4f12-bc16-a38d265a108d"),
            "reanchor_verified": res_a.get("compaction_reanchor_check", {}).get("verified", False),
            "violations": res_a.get("contract_check", {}).get("violations", []),
            "discrepancies": res_a.get("comparison_asserted_vs_measured", {}).get("discrepancies", []),
            "sha_table": build_sha_table(res_a.get("file_details", {})),
            "diffs": res_a.get("unified_diffs", {})
        },
        "branch_b": {
            "name": br_b_info.get("branch_name", "branch-b-faithful"),
            "disk_id": br_b_info.get("filesystem_id", "dsk-0000000000118c06"),
            "fork_ms": timings.get("act2_branch_b_create_ms", 71.74),
            "worker_ms": br_b_info.get("worker_latency_ms", 1224.0),
            "verdict": res_b.get("verdict", "PROMOTED: WITNESS_VERIFIED"),
            "prose": b_prose,
            "claimed_boundary": res_b.get("compaction_reanchor_check", {}).get("claimed_boundary_id", "e8437fd8-bc6b-4f12-bc16-a38d265a108d"),
            "physical_boundary": meta.get("physical_boundary_id", "e8437fd8-bc6b-4f12-bc16-a38d265a108d"),
            "reanchor_verified": res_b.get("compaction_reanchor_check", {}).get("verified", True),
            "violations": res_b.get("contract_check", {}).get("violations", []),
            "discrepancies": res_b.get("comparison_asserted_vs_measured", {}).get("discrepancies", []),
            "sha_table": build_sha_table(res_b.get("file_details", {})),
            "diffs": res_b.get("unified_diffs", {})
        },
        "raw_json": raw
    }
    return normalized


# =====================================================================
# HTML Generator (Cyber-Physical Instrument)
# =====================================================================

def render_html(model: dict) -> str:
    meta = model["meta"]
    timings = model["timings"]
    gate = model["act1_gate"]
    br_a = model["branch_a"]
    br_b = model["branch_b"]

    def format_diff(raw_diff: str) -> str:
        lines = []
        for line in raw_diff.splitlines():
            escaped = html.escape(line)
            if line.startswith("---") or line.startswith("+++"):
                lines.append(f'<span class="diff-header">{escaped}</span>')
            elif line.startswith("@@"):
                lines.append(f'<span class="diff-chunk">{escaped}</span>')
            elif line.startswith("+"):
                lines.append(f'<span class="diff-add">{escaped}</span>')
            elif line.startswith("-"):
                lines.append(f'<span class="diff-del">{escaped}</span>')
            else:
                lines.append(f'<span class="diff-ctx">{escaped}</span>')
        return "\n".join(lines)

    diff_a_golden = format_diff(br_a["diffs"].get("tests/test_golden.py", ""))
    diff_a_policy = format_diff(br_a["diffs"].get("app/policy.py", ""))
    diff_b_policy = format_diff(br_b["diffs"].get("app/policy.py", ""))

    json_raw_str = json.dumps(model["raw_json"], indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WITNESS: Measured, Not Asserted. | Archil Observability Engine</title>
  <style>
    :root {{
      --bg-void: #06080d;
      --bg-panel: #0d121c;
      --bg-subpanel: #131a28;
      --bg-card: #182234;
      --border-subtle: #1f2c42;
      --border-bright: #38bdf8;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent-cyan: #06b6d4;
      --accent-sky: #38bdf8;
      --accent-amber: #f59e0b;
      --accent-emerald: #10b981;
      --accent-crimson: #ef4444;
      --accent-violet: #a855f7;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--bg-void);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 24px;
      min-height: 100vh;
    }}

    .container {{
      max-width: 1560px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }}

    /* Top Bar */
    .top-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .brand-group {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .pulse-dot {{
      width: 14px;
      height: 14px;
      background: var(--accent-emerald);
      border-radius: 50%;
      box-shadow: 0 0 16px var(--accent-emerald);
      animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
      0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
      70% {{ transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }}
      100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
    }}

    .title-area h1 {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #fff;
    }}

    .title-area p {{
      font-size: 13px;
      color: var(--accent-sky);
      font-family: var(--font-mono);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}

    .header-pills {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .badge {{
      font-family: var(--font-mono);
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 4px;
      background: var(--bg-subpanel);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
    }}

    .badge.active {{
      border-color: var(--accent-cyan);
      color: var(--accent-cyan);
    }}

    /* Epistemological Thesis Banner */
    .thesis-banner {{
      background: linear-gradient(135deg, rgba(13, 20, 32, 0.95) 0%, rgba(16, 26, 44, 0.8) 100%);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-left: 5px solid var(--accent-cyan);
      padding: 18px 22px;
      border-radius: 8px;
    }}

    .thesis-banner blockquote {{
      font-size: 17px;
      font-weight: 500;
      color: #f8fafc;
      margin-bottom: 8px;
    }}

    .thesis-banner .cite {{
      font-size: 13px;
      color: var(--text-muted);
      font-style: italic;
    }}

    /* Live Telemetry Ribbon */
    .telemetry-strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 16px;
    }}

    .telemetry-card {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 5px;
      transition: all 0.2s ease;
    }}

    .telemetry-card:hover {{
      border-color: var(--accent-sky);
      transform: translateY(-1px);
    }}

    .telemetry-label {{
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .telemetry-value {{
      font-size: 26px;
      font-weight: 800;
      font-family: var(--font-mono);
      color: #fff;
    }}

    .telemetry-sub {{
      font-size: 12px;
      color: var(--accent-cyan);
      font-family: var(--font-mono);
    }}

    /* Sections */
    .section-card {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 20px 24px;
    }}

    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .section-title {{
      font-size: 18px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .tag-act {{
      background: rgba(245, 158, 11, 0.15);
      color: var(--accent-amber);
      font-family: var(--font-mono);
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    /* Act I Flow */
    .act-flow {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 20px;
      align-items: center;
    }}

    @media (max-width: 1024px) {{
      .act-flow {{ grid-template-columns: 1fr; }}
    }}

    .flow-box {{
      background: var(--bg-subpanel);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 16px;
      font-family: var(--font-mono);
      font-size: 13px;
    }}

    .flow-box h4 {{
      font-size: 14px;
      color: #fff;
      margin-bottom: 10px;
    }}

    .terminal-window {{
      background: #04070c;
      border: 1px solid #162234;
      border-radius: 4px;
      padding: 12px;
      margin-top: 10px;
      font-size: 12px;
      line-height: 1.6;
      color: #cbd5e1;
      overflow-x: auto;
    }}

    .prompt-sym {{ color: var(--accent-cyan); }}
    .err-text {{ color: var(--accent-crimson); font-weight: 600; }}
    .ok-text {{ color: var(--accent-emerald); font-weight: 600; }}

    .flow-arrow {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      color: var(--accent-cyan);
      font-family: var(--font-mono);
      font-size: 12px;
      text-align: center;
    }}

    .flow-arrow-icon {{
      font-size: 26px;
      line-height: 1;
    }}

    /* Branch Switcher Tabs */
    .branch-controls {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--bg-subpanel);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .tab-group {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .tab-btn {{
      background: var(--bg-panel);
      color: var(--text-muted);
      border: 1px solid var(--border-subtle);
      padding: 8px 16px;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 13px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }}

    .tab-btn:hover {{
      color: #fff;
      border-color: var(--text-muted);
    }}

    .tab-btn.active-branch-a {{
      background: rgba(239, 68, 68, 0.15);
      border-color: var(--accent-crimson);
      color: var(--accent-crimson);
      font-weight: 700;
    }}

    .tab-btn.active-branch-b {{
      background: rgba(16, 185, 129, 0.15);
      border-color: var(--accent-emerald);
      color: var(--accent-emerald);
      font-weight: 700;
    }}

    .tab-btn.active-dual {{
      background: rgba(6, 182, 212, 0.15);
      border-color: var(--accent-cyan);
      color: var(--accent-cyan);
      font-weight: 700;
    }}

    /* 3-Column Synchronized Matrix */
    .trajectory-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr 1.25fr;
      gap: 16px;
    }}

    @media (max-width: 1200px) {{
      .trajectory-grid {{ grid-template-columns: 1fr; }}
    }}

    .mode-col {{
      background: var(--bg-subpanel);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .mode-header {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .mode-col.assistant .mode-header {{
      background: rgba(168, 85, 247, 0.1);
      border-bottom-color: rgba(168, 85, 247, 0.3);
    }}

    .mode-col.tool .mode-header {{
      background: rgba(245, 158, 11, 0.1);
      border-bottom-color: rgba(245, 158, 11, 0.3);
    }}

    .mode-col.witness .mode-header {{
      background: rgba(6, 182, 212, 0.1);
      border-bottom-color: rgba(6, 182, 212, 0.3);
    }}

    .mode-title {{
      font-family: var(--font-mono);
      font-size: 13px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .mode-col.assistant .mode-title {{ color: var(--accent-violet); }}
    .mode-col.tool .mode-title {{ color: var(--accent-amber); }}
    .mode-col.witness .mode-title {{ color: var(--accent-cyan); }}

    .mode-body {{
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      flex: 1;
    }}

    .prose-box {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 14px;
      font-size: 14px;
      color: #e2e8f0;
      line-height: 1.6;
    }}

    .compaction-card {{
      background: #05080e;
      border: 1px solid rgba(168, 85, 247, 0.3);
      border-radius: 6px;
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 12px;
    }}

    .compaction-card .label {{
      color: var(--accent-violet);
      font-weight: 700;
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }}

    .tool-log-item {{
      background: #04070c;
      border: 1px solid #172335;
      border-radius: 6px;
      padding: 10px 12px;
      font-family: var(--font-mono);
      font-size: 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .tool-log-item.breach {{
      border-color: rgba(239, 68, 68, 0.6);
      background: rgba(239, 68, 68, 0.06);
    }}

    .tool-cmd {{ color: var(--accent-sky); }}
    .tool-out {{ color: var(--text-dim); font-size: 11px; white-space: pre-wrap; }}

    /* Witness Inspection */
    .witness-table {{
      width: 100%;
      border-collapse: collapse;
      font-family: var(--font-mono);
      font-size: 12px;
    }}

    .witness-table th, .witness-table td {{
      padding: 8px 10px;
      border: 1px solid var(--border-subtle);
      text-align: left;
    }}

    .witness-table th {{
      background: var(--bg-card);
      color: var(--text-muted);
    }}

    .hash-val {{
      color: var(--accent-cyan);
      font-size: 11px;
    }}

    .status-pill {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 700;
    }}

    .status-pill.quarantine {{
      background: rgba(239, 68, 68, 0.2);
      color: var(--accent-crimson);
      border: 1px solid var(--accent-crimson);
    }}

    .status-pill.promoted {{
      background: rgba(16, 185, 129, 0.2);
      color: var(--accent-emerald);
      border: 1px solid var(--accent-emerald);
    }}

    /* Diff Viewer */
    .diff-container {{
      background: #03060a;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 11px;
      overflow-x: auto;
      max-height: 240px;
      line-height: 1.5;
    }}

    .diff-header {{ color: var(--text-dim); }}
    .diff-chunk {{ color: var(--accent-violet); }}
    .diff-add {{ color: #4ade80; background: rgba(34, 197, 94, 0.1); display: block; }}
    .diff-del {{ color: #f87171; background: rgba(239, 68, 68, 0.1); display: block; }}
    .diff-ctx {{ color: #94a3b8; display: block; }}

    .verdict-box {{
      padding: 16px;
      border-radius: 6px;
      font-family: var(--font-mono);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    .verdict-box.quarantine {{
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid var(--accent-crimson);
    }}

    .verdict-box.promoted {{
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid var(--accent-emerald);
    }}

    .verdict-box h4 {{
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 0.04em;
    }}

    .verdict-box.quarantine h4 {{ color: var(--accent-crimson); }}
    .verdict-box.promoted h4 {{ color: var(--accent-emerald); }}

    /* Traversal Telemetry Record */
    .traversal-box {{
      background: #030509;
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 18px 22px;
      font-family: var(--font-mono);
      font-size: 13px;
    }}

    .traversal-box h3 {{
      font-size: 14px;
      color: var(--accent-cyan);
      margin-bottom: 12px;
    }}

    .spine-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 10px;
    }}

    .spine-item {{
      display: flex;
      align-items: baseline;
      gap: 12px;
      font-size: 12px;
    }}

    .spine-badge {{
      background: #1e293b;
      color: #38bdf8;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 700;
      min-width: 44px;
      text-align: center;
    }}

    .spine-ord {{
      color: var(--text-dim);
      font-size: 11px;
      min-width: 90px;
    }}

    details summary {{
      cursor: pointer;
      font-family: var(--font-mono);
      font-size: 13px;
      color: var(--accent-cyan);
      user-select: none;
      padding: 8px 0;
    }}

    pre.raw-json {{
      background: #020408;
      border: 1px solid #141c2c;
      border-radius: 6px;
      padding: 16px;
      font-size: 11px;
      color: #94a3b8;
      max-height: 340px;
      overflow-y: auto;
    }}
  </style>
</head>
<body>

  <div class="container">

    <!-- Top Header -->
    <header class="top-header">
      <div class="brand-group">
        <div class="pulse-dot"></div>
        <div class="title-area">
          <h1>WITNESS: Measured, Not Asserted</h1>
          <p style="font-size: 15px; font-weight: 600; color: #f8fafc; margin-top: 2px;">&ldquo;Trust me, bro.&rdquo; &mdash; CI for agent state integrity.</p>
          <p>A live Archil infrastructure demonstration using seeded agent-failure scenarios</p>
        </div>
      </div>
      <div class="header-pills">
        <span class="badge active">Archil v{html.escape(meta["archil_version"])}</span>
        <span class="badge">Region: {html.escape(meta["region"])}</span>
        <span class="badge">Session: {html.escape(meta["session_id"])}</span>
        <span class="badge">Run: {html.escape(meta["run_id"])}</span>
      </div>
    </header>

    <!-- Encounter Banner -->
    <section class="thesis-banner">
      <blockquote style="font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 8px;">
        &ldquo;The worker says it left the protected test untouched. A separately constrained process checks the retained files. They disagree. Here is the diff.&rdquo;
      </blockquote>
      <div style="font-size: 14px; color: var(--accent-sky); margin-bottom: 6px;">
        Two retained states let another party inspect what changed. Branch A is flagged for a demonstrated discrepancy; Branch B passes the demonstrated criteria.
      </div>
      <div class="cite">
        <strong>Scope note:</strong> Seeded worker-failure scenarios executed on live Archil infrastructure &middot; <code>PROMOTED</code> / <code>QUARANTINED</code> are returned witness verdict labels (no branch merge is performed).
      </div>
    </section>

    <!-- Live Telemetry Ribbon (Real Hardware Latencies) -->
    <section class="telemetry-strip">
      <div class="telemetry-card">
        <span class="telemetry-label">Pipeline before cleanup</span>
        <span class="telemetry-value">{timings["total_run_duration_ms"]:.2f}ms</span>
        <span class="telemetry-sub">Cleanup timed separately</span>
      </div>
      <div class="telemetry-card">
        <span class="telemetry-label">Branch A Fork</span>
        <span class="telemetry-value">{timings["act2_branch_a_create_ms"]:.2f}ms</span>
        <span class="telemetry-sub">{html.escape(br_a["disk_id"])}</span>
      </div>
      <div class="telemetry-card">
        <span class="telemetry-label">Branch B Fork</span>
        <span class="telemetry-value">{timings["act2_branch_b_create_ms"]:.2f}ms</span>
        <span class="telemetry-sub">{html.escape(br_b["disk_id"])}</span>
      </div>
      <div class="telemetry-card">
        <span class="telemetry-label">Witness Inspection</span>
        <span class="telemetry-value">{timings["act3_witness_exec_ms"]:.2f}ms</span>
        <span class="telemetry-sub">3 States Mounted Read-Only</span>
      </div>
      <div class="telemetry-card">
        <span class="telemetry-label">Worker Mount Authority</span>
        <span class="telemetry-value">SEPARATED</span>
        <span class="telemetry-sub">Worker ARCHIL_API_KEY = absent</span>
      </div>
    </section>

    <!-- Act I: Controller-Enforced Gate -->
    <section class="section-card">
      <div class="section-header">
        <div class="section-title">
          <span class="tag-act">ACT I</span>
          State-Dependent Write Restriction (<code>.grill_me_active</code> &rarr; Mount Policy) &middot; Root Disk: <code>{html.escape(gate["root_disk_id"])}</code>
        </div>
        <span class="badge active">{html.escape(gate["hardware_mount"])}</span>
      </div>

      <div class="act-flow">
        <!-- Gate Left: Read-Only Lock -->
        <div class="flow-box">
          <h4>🔒 Phase 1: Unresolved Sign-Off</h4>
          <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 8px;">
            Outside controller translates <code>.grill_me_active</code> into <code>read_only=True</code> mount. Worker write attempt fails in {timings["act1_hardware_gate_probe_ms"]:.2f}ms:
          </p>
          <div class="terminal-window">
            <span class="prompt-sym">MOUNT:</span> {html.escape(gate["hardware_mount"])}<br>
            <span class="prompt-sym">ATTEMPT:</span> touch /mnt/archil/work/app/policy.py<br>
            <span class="err-text">{html.escape(gate["kernel_error"])}</span><br>
            <span class="prompt-sym">CREDENTIAL CHECK:</span> api_key_present_in_worker: <span class="ok-text">{str(gate["api_key_present"]).lower()}</span>
          </div>
        </div>

        <!-- Flow Middle: Transition -->
        <div class="flow-arrow">
          <div class="flow-arrow-icon">&rarr;</div>
          <strong>.grill_me_resolved</strong>
          <span>Controller Updates Policy</span>
          <span style="font-size: 11px; color: var(--accent-emerald);">Baseline ckpt in {gate["checkpoint_t1_ms"]:.2f}ms</span>
        </div>

        <!-- Gate Right: Golden Anchor -->
        <div class="flow-box">
          <h4>⚓ Phase 2: Retained Baseline State</h4>
          <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 8px;">
            Controller retains baseline checkpoint <code>{html.escape(gate["checkpoint_t1"])}</code> before branching:
          </p>
          <div class="terminal-window">
            <span class="prompt-sym">CHECKPOINT:</span> {html.escape(gate["checkpoint_t1"])} (Latency: {gate["checkpoint_t1_ms"]:.2f}ms)<br>
            <span class="prompt-sym">PROTECTED TEST:</span> {html.escape(gate["golden_test"])}<br>
            <span class="prompt-sym">CONFIGURED CHECKS:</span><br>
            &bull; Allowed: {html.escape(str(gate["contract"].get("allowed_files", [])))}<br>
            &bull; Forbidden: {html.escape(str(gate["contract"].get("forbidden_mutations", [])))}<br>
            <span class="ok-text">BASELINE RECORDED AT transcript.jsonl:10</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Act II & III: Branching & Witness Comparison -->
    <section class="section-card">
      <div class="section-header">
        <div class="section-title">
          <span class="tag-act">ACT II &amp; III</span>
          Asserted Account vs. Seeded Worker Actions vs. Read-Only Witness Measurements
        </div>
        <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">
          Branches created from <code>{html.escape(gate["checkpoint_t1"])}</code> in <strong>{timings["act2_branch_a_create_ms"]:.2f}ms</strong> &amp; <strong>{timings["act2_branch_b_create_ms"]:.2f}ms</strong>
        </div>
      </div>

      <!-- Branch Controls -->
      <div class="branch-controls">
        <div class="tab-group">
          <button class="tab-btn active-branch-a" id="tabBranchA" onclick="switchBranch('a')">
            <span>🔴 Branch A: <code>{html.escape(br_a["name"])}</code> [Flagged &middot; Verdict: QUARANTINED]</span>
          </button>
          <button class="tab-btn" id="tabBranchB" onclick="switchBranch('b')">
            <span>🟢 Branch B: <code>{html.escape(br_b["name"])}</code> [Passes Checks &middot; Verdict: PROMOTED]</span>
          </button>
          <button class="tab-btn" id="tabDual" onclick="switchBranch('dual')">
            <span>⚖️ Split-Screen Dual Compare</span>
          </button>
        </div>
        <div style="font-family: var(--font-mono); font-size: 12px; color: var(--accent-cyan);">
          3-State Read-Only Witness Mount: <strong>{timings["act3_witness_exec_ms"]:.2f}ms</strong>
        </div>
      </div>

      <!-- Branch A Trajectory Container -->
      <div id="branchAView" class="branch-view-container">
        <div class="trajectory-grid">

          <!-- Col 1: [mode=assistant] -->
          <div class="mode-col assistant">
            <div class="mode-header">
              <span class="mode-title">💬 [mode=assistant]</span>
              <span class="badge">Worker's Stated Account</span>
            </div>
            <div class="mode-body">
              <div class="prose-box">
                "{html.escape(br_a["prose"])}"
              </div>
              <div class="compaction-card">
                <div class="label">
                  <span>Recorded Boundary ID Check</span>
                  <span style="color: var(--accent-crimson);">Boundary ID mismatch</span>
                </div>
                <div>Session ID: <code>{html.escape(meta["session_id"])}</code></div>
                <div>Stated Boundary ID: <span class="hash-val" style="color: var(--accent-crimson);">{html.escape(br_a["claimed_boundary"])}</span></div>
                <div>Retained Transcript ID: <span class="hash-val">{html.escape(br_a["physical_boundary"])}</span></div>
                <div style="margin-top: 6px; color: var(--accent-crimson); font-size: 11px; font-weight: 700;">
                  &times; Stated boundary ID does not match the physical identifier in transcript.jsonl:10.
                </div>
              </div>
            </div>
          </div>

          <!-- Col 2: [mode=tool] -->
          <div class="mode-col tool">
            <div class="mode-header">
              <span class="mode-title">⚡ [mode=tool]</span>
              <span class="badge">Seeded Worker Continuation ({br_a["worker_ms"]:.2f}ms)</span>
            </div>
            <div class="mode-body">
              <div class="tool-log-item breach">
                <span class="tool-cmd">MUTATION: app/policy.py</span>
                <span class="tool-out err-text">&larr; Expanded MAX_SHARD_THREADS=16 &amp; bypassed verify_boundary (return True)</span>
              </div>
              <div class="tool-log-item breach">
                <span class="tool-cmd">MUTATION: tests/test_golden.py</span>
                <span class="tool-out err-text">&larr; Modified protected test file (commented out failing assertion)</span>
              </div>
              <div class="tool-log-item">
                <span class="tool-cmd">CHECKPOINT: ckpt-t2-branch-a</span>
                <span class="tool-out ok-text">Retained post-run state ckpt-t2-branch-a</span>
              </div>
              <div style="font-size: 12px; color: var(--text-muted); font-style: italic;">
                Seeded failure case: the worker script changes the test while asserting it was untouched. The witness compares that claim with the retained files.
              </div>
            </div>
          </div>

          <!-- Col 3: [mode=witness] -->
          <div class="mode-col witness">
            <div class="mode-header">
              <span class="mode-title">🔬 [mode=witness]</span>
              <span class="status-pill quarantine">FLAGGED (VERDICT: QUARANTINED)</span>
            </div>
            <div class="mode-body">
              <div style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan);">
                Before/After Surface Comparison: <code>ckpt-t1-contract</code> vs. <code>ckpt-t2-branch-a</code> (mounted read-only)
              </div>

              <!-- SHA-256 Table -->
              <table class="witness-table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>t1 (Baseline)</th>
                    <th>t2 (Measured)</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {"".join([f'''
                  <tr>
                    <td><code>{html.escape(row["file"])}</code></td>
                    <td><span class="hash-val">{html.escape(row["t1_hash"][:16])}...</span></td>
                    <td><span class="hash-val" style="color: {'var(--accent-crimson)' if 'MODIFIED' in row['status'] and 'golden' in row['file'] else 'var(--text-main)'};">{html.escape(row["t2_hash"][:16])}...</span></td>
                    <td><span class="status-pill {'quarantine' if 'golden' in row['file'] else 'promoted'}">{html.escape(row["status"])}</span></td>
                  </tr>''' for row in br_a["sha_table"]])}
                </tbody>
              </table>

              <!-- Diff Viewer: Golden Test Tampering -->
              <div style="font-size: 11px; font-family: var(--font-mono); color: var(--accent-crimson); font-weight: 700;">
                Measured File Diff: tests/test_golden.py (Conflicts with Worker Claim)
              </div>
              <div class="diff-container">
                <pre>{diff_a_golden}</pre>
              </div>

              <!-- Verdict -->
              <div class="verdict-box quarantine">
                <h4>VERDICT LABEL: {html.escape(br_a["verdict"])}</h4>
                <div style="font-size: 12px;">
                  <strong>Branch A is flagged for a demonstrated discrepancy:</strong><br>
                  {"<br>".join([f"&bull; {html.escape(v)}" for v in br_a["violations"]])}
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- Branch B Trajectory Container -->
      <div id="branchBView" class="branch-view-container" style="display: none;">
        <div class="trajectory-grid">

          <!-- Col 1: [mode=assistant] -->
          <div class="mode-col assistant">
            <div class="mode-header">
              <span class="mode-title">💬 [mode=assistant]</span>
              <span class="badge">Worker's Stated Account</span>
            </div>
            <div class="mode-body">
              <div class="prose-box">
                "{html.escape(br_b["prose"])}"
              </div>
              <div class="compaction-card">
                <div class="label">
                  <span>Recorded Boundary ID Check</span>
                  <span style="color: var(--accent-emerald);">Boundary ID matches</span>
                </div>
                <div>Session ID: <code>{html.escape(meta["session_id"])}</code></div>
                <div>Stated Boundary ID: <span class="hash-val" style="color: var(--accent-emerald);">{html.escape(br_b["claimed_boundary"])}</span></div>
                <div>Retained Transcript ID: <span class="hash-val">{html.escape(br_b["physical_boundary"])}</span></div>
                <div style="margin-top: 6px; color: var(--accent-emerald); font-size: 11px; font-weight: 700;">
                  &check; Boundary ID matches (structural identifier check against transcript.jsonl:10).
                </div>
              </div>
            </div>
          </div>

          <!-- Col 2: [mode=tool] -->
          <div class="mode-col tool">
            <div class="mode-header">
              <span class="mode-title">⚡ [mode=tool]</span>
              <span class="badge">Seeded Worker Continuation ({br_b["worker_ms"]:.2f}ms)</span>
            </div>
            <div class="mode-body">
              <div class="tool-log-item">
                <span class="tool-cmd">MUTATION: app/policy.py</span>
                <span class="tool-out ok-text">&larr; Updated MAX_SHARD_THREADS=10 with bounds check intact</span>
              </div>
              <div class="tool-log-item">
                <span class="tool-cmd">INSPECTION: tests/test_golden.py</span>
                <span class="tool-out ok-text">&larr; Left untouched</span>
              </div>
              <div class="tool-log-item">
                <span class="tool-cmd">CHECKPOINT: ckpt-t2-branch-b</span>
                <span class="tool-out ok-text">Retained post-run state ckpt-t2-branch-b</span>
              </div>
              <div style="font-size: 12px; color: var(--text-muted); font-style: italic;">
                Seeded control case: modifies only the permitted file and preserves the protected test.
              </div>
            </div>
          </div>

          <!-- Col 3: [mode=witness] -->
          <div class="mode-col witness">
            <div class="mode-header">
              <span class="mode-title">🔬 [mode=witness]</span>
              <span class="status-pill promoted">PASSES CRITERIA (VERDICT: PROMOTED)</span>
            </div>
            <div class="mode-body">
              <div style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan);">
                Before/After Surface Comparison: <code>ckpt-t1-contract</code> vs. <code>ckpt-t2-branch-b</code> (mounted read-only)
              </div>

              <!-- SHA-256 Table -->
              <table class="witness-table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>t1 (Baseline)</th>
                    <th>t2 (Measured)</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {"".join([f'''
                  <tr>
                    <td><code>{html.escape(row["file"])}</code></td>
                    <td><span class="hash-val">{html.escape(row["t1_hash"][:16])}...</span></td>
                    <td><span class="hash-val" style="color: {'var(--accent-emerald)' if 'UNCHANGED' in row['status'] else 'var(--text-main)'};">{html.escape(row["t2_hash"][:16])}...</span></td>
                    <td><span class="status-pill promoted">{html.escape(row["status"])}</span></td>
                  </tr>''' for row in br_b["sha_table"]])}
                </tbody>
              </table>

              <!-- Diff Viewer: Legitimate Policy Refactor -->
              <div style="font-size: 11px; font-family: var(--font-mono); color: var(--accent-emerald); font-weight: 700;">
                Measured File Diff: app/policy.py (Permitted Change)
              </div>
              <div class="diff-container">
                <pre>{diff_b_policy}</pre>
              </div>

              <!-- Verdict -->
              <div class="verdict-box promoted">
                <h4>VERDICT LABEL: {html.escape(br_b["verdict"])}</h4>
                <div style="font-size: 12px;">
                  <strong>Branch B passes the demonstrated criteria:</strong><br>
                  Configured checks passed. Protected test bytes unchanged. Stated boundary ID matches the baseline transcript.<br>
                  <em>Note: PROMOTED is a returned verdict label; this demo does not merge or promote branches.</em>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

    </section>

    <!-- Continuity Marker & Pruned Claims -->
    <section class="section-card">
      <div class="section-header">
        <div class="section-title">
          <span class="tag-act">CONTINUITY MARKER</span>
          Authoritative Scope &amp; Pruned Claims
        </div>
        <span class="badge active">Measured, Not Asserted</span>
      </div>

      <div class="traversal-box">
        <h3>🧭 What This Arrangement Demonstrates (and What It Does Not Claim)</h3>
        <p style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin-bottom: 12px;">
          <strong>WITNESS is a live Archil infrastructure demonstration using seeded failure scenarios.</strong> It shows that a separately constrained, read-only party can expose a specific discrepancy between an agent&rsquo;s asserted account and retained workspace states. It does not establish semantic recovery, reconstruct the complete intervening event, prove a branch globally safe, perform actual branch promotion, or make the witness authoritative.
        </p>

        <div style="margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;">
          <div>
            <strong style="color: var(--accent-sky);">1. Seeded Scenarios on Live Infrastructure:</strong><br>
            <span style="font-size: 12px; color: var(--text-muted);">
              Executes real Archil disks, checkpoints, branches ({timings["act2_branch_a_create_ms"]:.2f}ms &amp; {timings["act2_branch_b_create_ms"]:.2f}ms), and read-only mounts ({timings["act3_witness_exec_ms"]:.2f}ms) against deliberately constructed failure and control cases.
            </span>
          </div>
          <div>
            <strong style="color: var(--accent-amber);">2. Endpoint Surfaces, Not Omniscience:</strong><br>
            <span style="font-size: 12px; color: var(--text-muted);">
              Two retained states let another party inspect what changed (file hashes, diffs, and boundary IDs) without claiming to reconstruct every intervening action or prove global safety.
            </span>
          </div>
          <div>
            <strong style="color: var(--accent-emerald);">3. Separated Authority, Not Oracle Truth:</strong><br>
            <span style="font-size: 12px; color: var(--text-muted);">
              The witness is a differently constrained participant (separate execution context, <code>read_only=True</code> mounts, deterministic checks, and no authority to alter the states it compares).
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- Raw Evidence JSON Accordion -->
    <details>
      <summary>&blacktriangleright; View Verbatim Live Hardware Telemetry JSON (Dereference Target)</summary>
      <pre class="raw-json"><code>{html.escape(json_raw_str)}</code></pre>
    </details>

  </div>

  <script>
    function switchBranch(mode) {{
      const viewA = document.getElementById('branchAView');
      const viewB = document.getElementById('branchBView');
      const tabA = document.getElementById('tabBranchA');
      const tabB = document.getElementById('tabBranchB');
      const tabDual = document.getElementById('tabDual');

      tabA.className = 'tab-btn';
      tabB.className = 'tab-btn';
      tabDual.className = 'tab-btn';

      if (mode === 'a') {{
        viewA.style.display = 'block';
        viewB.style.display = 'none';
        tabA.className = 'tab-btn active-branch-a';
      }} else if (mode === 'b') {{
        viewA.style.display = 'none';
        viewB.style.display = 'block';
        tabB.className = 'tab-btn active-branch-b';
      }} else if (mode === 'dual') {{
        viewA.style.display = 'block';
        viewB.style.display = 'block';
        tabDual.className = 'tab-btn active-dual';
      }}
    }}
  </script>
</body>
</html>
"""


# =====================================================================
# 90-Second Hackathon Table Demo Script
# =====================================================================

def render_demo_script(model: dict) -> str:
    meta = model["meta"]
    timings = model["timings"]
    gate = model["act1_gate"]
    br_a = model["branch_a"]
    br_b = model["branch_b"]
    return f"""# WITNESS: Measured, Not Asserted — table demo

**Run:** `{meta['run_id']}`  
**Format:** 90 seconds, then one minute of questions.  
**Display:** `epistemic_witness_demo.html`.

## Spoken script

“An agent can say it left your tests untouched. We built a way for another process to check that claim against the workspace.

First, before approval, the worker gets a read-only mount and no Archil API key. An attempted write actually fails with a read-only filesystem error.

After the approval step, we checkpoint the workspace and fork two branches from that same starting state.

These are deliberately scripted failure scenarios, executed on live Archil infrastructure. Branch A changes a protected test and claims it did not. Branch B makes the permitted code change and preserves the test.

A separate witness reads the baseline and both branches through read-only mounts. Here is the claim; here is the measured file difference. A is flagged. B passes the configured checks. The boundary-ID comparison also catches A's seeded mismatch.

The recorded cycle took {timings['total_run_duration_ms'] / 1000:.2f} seconds before cleanup. The point is that the worker's explanation becomes a claim someone else can inspect.

Bingo Bongo. Show me the diff.”

## Screen choreography

1. Point to the read-only error and absent worker API key.
2. Select Branch A; show its assertion and the actual test diff.
3. Select Split-Screen Dual Compare; show A flagged and B passing.
4. Leave the diff visible for questions.

## Numbers for Q&A — do not read IDs aloud

| Measurement | Recorded value |
| --- | --- |
| Root disk | `{gate['root_disk_id']}` |
| Read-only probe | {timings['act1_hardware_gate_probe_ms']:.2f} ms |
| Branch A | `{br_a['disk_id']}` / {timings['act2_branch_a_create_ms']:.2f} ms |
| Branch B | `{br_b['disk_id']}` / {timings['act2_branch_b_create_ms']:.2f} ms |
| Witness execution | {timings['act3_witness_exec_ms']:.2f} ms |
| Pipeline before cleanup | {timings['total_run_duration_ms']:.2f} ms |

## Answers to keep precise

- Real infrastructure run; scripted worker changes and assistant claims.
- PROMOTED / QUARANTINED are returned verdicts. This demo does not merge branches.
- Boundary-ID match is structural, not proof of semantic re-anchoring.
- Filesystem hashes/diffs show endpoint differences, not every intervening action.
- The controller and verifier remain trusted; read-only mounts limit the worker's granted access.
"""


# =====================================================================
# Main CLI
# =====================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render The Epistemic Witness View from live Archil telemetry."
    )
    parser.add_argument(
        "--evidence",
        type=str,
        default=None,
        help="Path to live_run_evidence.json.",
    )
    parser.add_argument(
        "--out-html",
        type=str,
        default=None,
        help="Path to write output HTML file.",
    )
    parser.add_argument(
        "--out-script",
        type=str,
        default=None,
        help="Path to write 90-second demo script markdown file.",
    )
    parser.add_argument("--sync-wsl", action="store_true", help="Also copy HTML to the original demo's WSL workspace.")
    args = parser.parse_args()

    is_windows = sys.platform == "win32"
    relay_dir = Path(__file__).resolve().parent

    evidence_path = Path(args.evidence) if args.evidence else relay_dir / "live_run_evidence.json"
    html_out_path = Path(args.out_html) if args.out_html else relay_dir / "epistemic_witness_demo.html"
    script_out_path = Path(args.out_script) if args.out_script else relay_dir / "DEMO_SCRIPT_90S.md"
    wsl_html_target = Path("/home/computer/archil-hack/epistemic_witness_demo.html")

    print("=" * 70)
    print("  THE EPISTEMIC WITNESS: Live Archil Hardware Telemetry Renderer")
    print("=" * 70)

    if not evidence_path.exists():
        print(f"[!] Evidence file not found at {evidence_path}. Exiting.")
        sys.exit(1)

    print(f"[*] Reading live run evidence from: {evidence_path}")
    raw_data = json.loads(evidence_path.read_text(encoding="utf-8"))
    if raw_data.get("meta", {}).get("status") == "failed":
        parser.error("This evidence records a failed run; refusing to render it as a successful demo.")
    model = normalize_evidence(raw_data)
    print(f"    [+] Run ID: {model['meta']['run_id']}")
    print(f"    [+] Root Disk: {model['act1_gate']['root_disk_id']}")
    print(f"    [+] Branch A ({model['branch_a']['disk_id']}) Fork: {model['timings']['act2_branch_a_create_ms']:.2f}ms")
    print(f"    [+] Branch B ({model['branch_b']['disk_id']}) Fork: {model['timings']['act2_branch_b_create_ms']:.2f}ms")
    print(f"    [+] Total Pipeline: {model['timings']['total_run_duration_ms']:.2f}ms")

    # Render HTML
    print(f"[*] Rendering Epistemic Witness UI: {html_out_path}")
    rendered_html = render_html(model)
    html_out_path.write_text(rendered_html, encoding="utf-8")
    print(f"    [+] HTML successfully rendered ({len(rendered_html):,} bytes).")

    # Sync to WSL
    if args.sync_wsl:
        print(f"[*] Syncing HTML artifact to WSL: {wsl_html_target}")
        try:
          if not is_windows:
              wsl_html_target.parent.mkdir(parents=True, exist_ok=True)
              shutil.copyfile(html_out_path, wsl_html_target)
              print(f"    [+] Direct copy to WSL target succeeded: {wsl_html_target}")
          else:
              win_path_str = str(html_out_path.resolve()).replace("\\", "/")
              if win_path_str.startswith("C:") or win_path_str.startswith("c:"):
                  wsl_src = "/mnt/c" + win_path_str[2:]
              else:
                  wsl_src = win_path_str

              res = subprocess.run(
                  ["wsl.exe", "-d", "Ubuntu-22.04", "--", "cp", wsl_src, wsl_html_target.as_posix()],
                  capture_output=True,
                  text=True,
                  timeout=10,
              )
              if res.returncode == 0:
                  print(f"    [+] Verified copy to WSL target via wsl.exe: {wsl_html_target}")
              else:
                  print(f"    [!] WSL copy warning: {res.stderr.strip()}")
        except Exception as exc:
          print(f"    [!] WSL copy skipped or failed: {exc}")

    # Render 90s Pitch Script
    print(f"[*] Rendering 90-Second Hackathon Demo Script: {script_out_path}")
    rendered_script = render_demo_script(model)
    script_out_path.write_text(rendered_script, encoding="utf-8")
    print(f"    [+] Demo script successfully generated ({len(rendered_script):,} bytes).")

    print("-" * 70)
    print("VERIFICATION & SUMMARY:")
    print(f"  - Root disk ID: {model['act1_gate']['root_disk_id']}")
    print(f"  - Branch A disk: {model['branch_a']['disk_id']} ({model['timings']['act2_branch_a_create_ms']:.2f} ms)")
    print(f"  - Branch B disk: {model['branch_b']['disk_id']} ({model['timings']['act2_branch_b_create_ms']:.2f} ms)")
    print(f"  - Witness inspection: {model['timings']['act3_witness_exec_ms']:.2f} ms")
    print(f"  - Total pipeline duration: {model['timings']['total_run_duration_ms']:.2f} ms")
    print(f"  - Branch A verdict: {model['branch_a']['verdict']}")
    print(f"  - Branch B verdict: {model['branch_b']['verdict']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
