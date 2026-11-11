"""Offline tests of the actual embedded witness, without SDK or credentials."""
import ast
import builtins
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SOURCE = Path(__file__).with_name("epistemic_witness.py")
ENGINE = ast.parse(SOURCE.read_text(encoding="utf-8"))
SCRIPT = next(
    ast.literal_eval(node.value)
    for node in ast.walk(ENGINE)
    if isinstance(node, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == "witness_script" for t in node.targets)
)
PYTHON = SCRIPT.split("python3 - <<'EOF'\n", 1)[1].rsplit("\nEOF", 1)[0]
SCRIPT_AST = ast.parse(PYTHON)
# Only mount lookup changes for local fixtures; all witness logic runs unchanged.
for node in SCRIPT_AST.body:
    if isinstance(node, ast.FunctionDef) and node.name == "locate_mount":
        node.body = ast.parse("return MOUNTS[name]").body
ast.fix_missing_locations(SCRIPT_AST)
SCRIPT_CODE = compile(SCRIPT_AST, str(SOURCE) + ":embedded", "exec")
CONSTANTS = {
    node.targets[0].id: ast.literal_eval(node.value)
    for node in ENGINE.body
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id in {"GOLDEN_TEST_PY", "SEED_POLICY_PY", "BRANCH_B_POLICY_PY", "BRANCH_A_POLICY_PY"}
}


class WitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.mounts = {name: str(Path(self.temp.name) / name) for name in ("t1", "branch_a", "branch_b")}
        self.boundary = {"type": "compact_boundary", "boundary_id": "boundary-1", "pre_tokens": 100}
        self.contract = {
            "allowed_files": ["app/policy.py"],
            "forbidden_mutations": ["disable verify_boundary", "touch tests/test_golden.py"],
            "require_reanchor": True,
        }
        self.baseline = self.record(self.boundary)
        self.seed()

    @staticmethod
    def record(value):
        return (json.dumps(value) + "\n").encode()

    def claim(self, boundary="boundary-1"):
        return self.record({"type": "assistant", "content": "Updated app/policy.py; tests/test_golden.py untouched [COMPACTION_REANCHOR_CHECKPOINT v1 boundary_id=" + boundary + "]"})

    def write(self, mount, rel, data):
        path = Path(self.mounts[mount]) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def seed(self):
        for mount in self.mounts:
            self.write(mount, ".grill_me_resolved", json.dumps(self.contract))
            self.write(mount, "app/policy.py", CONSTANTS["SEED_POLICY_PY"])
            self.write(mount, "tests/test_golden.py", CONSTANTS["GOLDEN_TEST_PY"])
            self.write(mount, "transcript.jsonl", self.baseline + (b"" if mount == "t1" else self.claim()))
        self.write("branch_b", "app/policy.py", CONSTANTS["BRANCH_B_POLICY_PY"])

    def run_witness(self, unreadable=None):
        real_open = builtins.open
        def guarded_open(path, *args, **kwargs):
            if str(path).endswith(".witness_probe_write"):
                raise OSError(30, "Read-only file system")
            if unreadable is not None and Path(path) == unreadable:
                raise PermissionError("fixture unreadable")
            return real_open(path, *args, **kwargs)
        namespace = {"MOUNTS": self.mounts}
        with mock.patch("builtins.open", guarded_open), contextlib.redirect_stdout(io.StringIO()):
            exec(SCRIPT_CODE, namespace)
        return namespace["witness_output"]["results"]["branch_b_faithful"]

    def assert_quarantined(self, result):
        self.assertFalse(result["contract_check"]["passed"])
        self.assertTrue(result["verdict"].startswith("QUARANTINED"))

    def test_clean_branch_b_promotes(self):
        result = self.run_witness()
        self.assertTrue(result["contract_check"]["passed"])
        self.assertTrue(result["compaction_reanchor_check"]["verified"])
        self.assertTrue(result["comparison_asserted_vs_measured"]["measured_golden_test_untouched"])

    def test_rewritten_baseline_is_rejected(self):
        self.write("branch_b", "transcript.jsonl", self.record({**self.boundary, "pre_tokens": 1}) + self.claim())
        result = self.run_witness()
        self.assert_quarantined(result)
        self.assertFalse(result["compaction_reanchor_check"]["verified"])
        self.assertTrue(any("byte prefix" in v for v in result["contract_check"]["violations"]))

    def test_baseline_requires_newline(self):
        self.baseline = self.baseline.rstrip(b"\n")
        self.seed()
        self.assert_quarantined(self.run_witness())

    def test_deleted_contract_is_unapproved(self):
        (Path(self.mounts["branch_b"]) / ".grill_me_resolved").unlink()
        result = self.run_witness()
        self.assert_quarantined(result)
        self.assertIn(".grill_me_resolved", result["delta"]["deleted"])
        self.assertIn("--- t1/.grill_me_resolved", result["unified_diffs"][".grill_me_resolved"])
        self.assertTrue(any("Unapproved" in v and ".grill_me_resolved" in v for v in result["contract_check"]["violations"]))

    def test_deleted_golden_is_not_untouched(self):
        (Path(self.mounts["branch_b"]) / "tests/test_golden.py").unlink()
        result = self.run_witness()
        self.assert_quarantined(result)
        self.assertFalse(result["comparison_asserted_vs_measured"]["measured_golden_test_untouched"])
        self.assertTrue(result["comparison_asserted_vs_measured"]["discrepancies"])
        self.assertIn("-import pytest", result["unified_diffs"]["tests/test_golden.py"])

    def test_missing_boundary_and_claim_cannot_match(self):
        for physical in (None, "", "   "):
            with self.subTest(physical=physical):
                self.boundary["boundary_id"] = physical
                self.baseline = self.record(self.boundary)
                self.seed()
                self.write("branch_b", "transcript.jsonl", self.baseline)
                result = self.run_witness()
                self.assert_quarantined(result)
                self.assertFalse(result["compaction_reanchor_check"]["verified"])

    def test_old_claims_do_not_count_as_new_evidence(self):
        self.baseline += self.claim()
        self.seed()
        self.write("branch_b", "transcript.jsonl", self.baseline)
        result = self.run_witness()
        self.assert_quarantined(result)
        self.assertFalse(result["comparison_asserted_vs_measured"]["asserted_golden_test_untouched"])
        self.assertIsNone(result["compaction_reanchor_check"]["claimed_boundary_id"])

    def test_incomplete_append_is_rejected(self):
        self.write("branch_b", "transcript.jsonl", (self.baseline + self.claim()).rstrip(b"\n"))
        self.assert_quarantined(self.run_witness())

    def test_unreadable_file_aborts_measurement(self):
        with self.assertRaisesRegex(OSError, "Cannot read witness file"):
            self.run_witness(Path(self.mounts["branch_b"]) / "tests/test_golden.py")

    def test_boundary_bypass_still_rejected(self):
        self.write("branch_b", "app/policy.py", CONSTANTS["BRANCH_A_POLICY_PY"])
        result = self.run_witness()
        self.assert_quarantined(result)
        self.assertTrue(any("bypassed" in v for v in result["contract_check"]["violations"]))


class EvidenceRuntimeTests(unittest.TestCase):
    """Exercise the orchestrator with a fake SDK, including its finally path."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        nodes = [node for node in ENGINE.body if isinstance(node, (ast.Assign, ast.FunctionDef))
                 or isinstance(node, ast.Import) and all(alias.name != "archil" for alias in node.names)]
        self.namespace = {"__file__": str(Path(self.temp.name) / "epistemic_witness.py")}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), self.namespace)
        self.report = {
            "witness_isolation": {"read_only_mounts_enforced": {name: True for name in ("t1", "branch_a", "branch_b")},
                                  "api_key_present_in_witness": False},
            "results": {name: {"verdict": "fixture verdict"} for name in ("branch_a_drifted", "branch_b_faithful")},
        }
        self.gate = {"errno_30_blocked": True, "api_key_present_in_worker": False}
        self.gate_exit = 0
        self.witness_exit = 0
        self.witness_stdout = None
        self.seed_exit = 0
        self.deleted = False
        owner = self

        class FakeDisk:
            id = "fixture-disk"
            def wait_until_ready(self, **kwargs):
                return self
            def exec(self, command):
                code = owner.seed_exit if "ckpt-t0-gated" in command else 0
                return SimpleNamespace(exit_code=code, stdout="fixture disk exec", stderr="")
            def delete_object(self, path):
                pass
            def create_branch(self, name, **kwargs):
                return SimpleNamespace(branch_name=name, filesystem_id=name)
            def delete(self):
                owner.deleted = True

        def fake_exec(**kwargs):
            if set(kwargs["disks"]) == {"work"}:
                return SimpleNamespace(exit_code=self.gate_exit, stdout=json.dumps(self.gate), stderr="")
            stdout = self.witness_stdout
            if stdout is None:
                stdout = "===WITNESS_JSON_START===\n" + json.dumps(self.report) + "\n===WITNESS_JSON_END==="
            return SimpleNamespace(exit_code=self.witness_exit, stdout=stdout, stderr="fixture witness stderr")

        self.namespace["archil"] = SimpleNamespace(
            create_disk=lambda **kwargs: SimpleNamespace(disk=FakeDisk()),
            get_disk=lambda disk_id: FakeDisk(), exec=fake_exec, list_disks=lambda: [],
        )
        self.namespace["ExecMountSpec"] = lambda disk, **kwargs: (disk, kwargs)
        self.output = Path(self.temp.name) / "nested" / "evidence.json"

    def run_engine(self, output=True):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.namespace["run_epistemic_witness"](output_path=self.output if output else None)

    def assert_saved_failure(self):
        saved = json.loads(self.output.read_text())
        self.assertEqual(saved["meta"]["status"], "failed")
        self.assertEqual(saved["meta"]["error"]["type"], "RuntimeError")
        self.assertTrue(saved["cleanup"]["root_disk_deleted"])
        self.assertEqual(saved["cleanup"]["orphan_disks_remaining"], 0)
        self.assertIn("cleanup_ms", saved["timings_summary_ms"])
        self.assertTrue(self.deleted)
        return saved

    def test_default_path_is_beside_script(self):
        self.run_engine(output=False)
        saved = json.loads((Path(self.temp.name) / "live_run_evidence.json").read_text())
        self.assertEqual(saved["meta"]["status"], "success")
        self.assertTrue(self.deleted)

    def test_failure_replaces_previous_success_after_cleanup(self):
        self.run_engine()
        self.seed_exit = 9
        with self.assertRaisesRegex(RuntimeError, "Seeding failed"):
            self.run_engine()
        self.assert_saved_failure()
        self.assertFalse(list(self.output.parent.glob("*.tmp")))

    def test_gate_requires_read_only_and_credential_isolation(self):
        cases = [(1, self.gate), (0, {"errno_30_blocked": False, "api_key_present_in_worker": False}),
                 (0, {"errno_30_blocked": True, "api_key_present_in_worker": True}), (0, {})]
        for code, gate in cases:
            with self.subTest(code=code, gate=gate):
                self.gate_exit, self.gate = code, gate
                with self.assertRaisesRegex(RuntimeError, "Hardware gate"):
                    self.run_engine()
                self.assert_saved_failure()

    def test_bad_witness_results_save_failure(self):
        cases = [(3, None), (0, "no delimiters"),
                 (0, "===WITNESS_JSON_START===not json===WITNESS_JSON_END==="),
                 (0, "===WITNESS_JSON_START==={}===WITNESS_JSON_END===")]
        for code, stdout in cases:
            with self.subTest(code=code, stdout=stdout):
                self.witness_exit, self.witness_stdout = code, stdout
                with self.assertRaises(RuntimeError):
                    self.run_engine()
                saved = self.assert_saved_failure()
                self.assertIn("act3_witness_exec_ms", saved["timings_summary_ms"])
                self.assertEqual(saved["act_3_epistemic_witness"]["exit_code"], code)

    def test_witness_isolation_and_branch_results_required(self):
        valid_report = json.loads(json.dumps(self.report))
        for mutation in ("mount", "credential", "branch"):
            with self.subTest(mutation=mutation):
                self.report = json.loads(json.dumps(valid_report))
                if mutation == "mount":
                    self.report["witness_isolation"]["read_only_mounts_enforced"]["branch_a"] = False
                elif mutation == "credential":
                    self.report["witness_isolation"]["api_key_present_in_witness"] = True
                else:
                    del self.report["results"]["branch_b_faithful"]
                with self.assertRaises(RuntimeError):
                    self.run_engine()
                self.assert_saved_failure()


if __name__ == "__main__":
    unittest.main()
