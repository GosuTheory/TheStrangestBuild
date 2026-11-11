# Archil v0.21.0 Complete SDK & Runtime Reference (Zero-Lookup Cheat Sheet)

> **STOP READING `site-packages/archil` OR SCRAPING DOCS.** Every method, parameter, return type, and gotcha in `archil` v0.21.0 is documented below.

## 1. Environment & Initialization
- **Env vars:** `ARCHIL_API_KEY` (`ak_...` or `key-...`), `ARCHIL_REGION` (`aws-us-west-2`, `aws-us-east-1`, `aws-eu-west-1`, `gcp-us-central1`), optional `ARCHIL_MAX_THROTTLE_WAIT` (seconds, default `10.0`, `"inf"` for indefinite).
- **WSL 2 (`Ubuntu-22.04`) Gotcha:** Default `~/.bashrc` has an interactive guard (`case $- in *i*) ;; *) return;; esac`) on line 6! `source ~/.bashrc` inside `bash -lc` is a no-op unless the exports are in `~/.profile` or loaded via `eval "$(grep '^export ARCHIL_' ~/.bashrc)"`.
- **Client vs Module-Level Helpers:**
  ```python
  import archil
  from archil import Archil, ExecMountSpec, SandboxMountSpec, SandboxNetwork, SandboxEgressPolicy, SandboxEgressRule, SandboxEgressTransform, RootAttrs

  # Option A: Module-level singleton (reads ARCHIL_API_KEY & ARCHIL_REGION from env)
  archil.configure(api_key="...", region="aws-us-west-2")  # optional if env vars set

  # Option B: Explicit client (supports .aio async variants on every method)
  client = Archil(api_key="...", region="aws-us-west-2", max_throttle_wait=30.0)
  ```
- **Sync + Async (`synchronicity`):** Every method on `Archil`, `Disks`, `Disk`, `Sandboxes`, `Sandbox`, `Workspace`, `Images`, `Tokens` works synchronously (`disk.put_object(...)`) AND asynchronously (`await disk.put_object.aio(...)`).

---

## 2. Disks (`archil.create_disk`, `archil.get_disk`, `archil.list_disks`)
- **Create & Wait:**
  ```python
  created = archil.create_disk(
      name="my-disk",
      root_attrs=RootAttrs(uid=1000, gid=1000, mode=0o755),  # optional
  )
  disk = created.disk.wait_until_ready(timeout=60.0, poll_interval=1.0)
  # created.token is the one-time mount token (only needed for external FUSE mounts)
  ```
- **S3-Compatible Object API (No Mount Required — Over HTTPS):**
  ```python
  disk.put_object("traces/run1.jsonl", b"...", "application/x-ndjson", mode=0o644, uid=0, gid=0)
  disk.append_object("traces/run1.jsonl", "next line\n")  # max 1 MiB per append call!
  raw: bytes = disk.get_object("traces/run1.jsonl")
  exists: bool = disk.object_exists("traces/run1.jsonl")
  meta = disk.head_object("traces/run1.jsonl")            # ObjectMetadata(size, etag, content_type, last_modified) or None
  listing = disk.list_objects("traces/", recursive=True)  # ListObjectsResult(objects=[S3Object(key, size, etag, last_modified)], common_prefixes=[...])
  disk.delete_object("traces/run1.jsonl")
  disk.delete_objects(["a.txt", "b.txt"])
  share = disk.share("traces/run1.jsonl", expires_in=86400)  # ShareUrl(url, expires_in) — public signed download link!
  ```
- **Parallel Serverless Grep Across Disk:**
  ```python
  res = disk.grep(
      directory="traces",
      pattern="COMPACTION_REANCHOR",
      recursive=True,
      ignore_case=False,
      multiline=False,
      globs=["*.jsonl"],
      context_before=2,
      context_after=2,
      max_results=100,
  )
  # res.matches -> list[GrepMatch(file, line, text, end_line)]
  # res.files_scanned, res.containers_dispatched, res.duration_ms
  ```
- **Serverless Bash Exec on a Single Disk (`disk.exec`):**
  - **MOUNT PATH GOTCHA:** Single-disk `disk.exec("...")` mounts the disk at `/mnt` (specifically `/mnt/archil` on some runners or `/mnt` directly — always check `MNT=/mnt/archil; [ -d "$MNT" ] || MNT=/mnt`).
  ```python
  res = disk.exec(
      "ls -la /mnt",
      base_image="python:3.12-slim",  # optional
      vcpu_count=2,                   # optional
      mem_size_mib=4096,              # optional
      network=SandboxNetwork(...),    # optional
  )
  # res -> ExecResult(exit_code, stdout, stderr, timing=ExecTiming(total_ms, queue_ms, execute_ms))
  ```
- **Multi-Disk Serverless Exec (`archil.exec`):**
  - Mounts each named disk at `/mnt/<name>`!
  - Supports `ExecMountSpec(disk, subdirectory=None, read_only=False, conditional=False)`:
    - `read_only=True`: enforces kernel/filesystem-level read-only mount (cannot be mutated by the exec container).
    - `conditional=True`: concurrent read-write mount without exclusive inode delegation checkout.
  ```python
  res = archil.exec(
      disks={
          "work": work_disk,  # mounted RW at /mnt/work
          "truth": ExecMountSpec(truth_disk, subdirectory="traces", read_only=True, conditional=False),  # mounted RO at /mnt/truth
      },
      command="python3 /mnt/truth/verify.py /mnt/work/candidate.json",
  )
  ```

---

## 3. Checkpoints, Branches & Delegations (Leases)
- **Creating a Disk Checkpoint (Verified Live — 0.82s):**
  - Inside `disk.exec(...)`, `archil checkpoints create` IS pre-installed on Archil's runner!
  ```python
  ckpt_cmd = (
      "set -e\n"
      "MNT=/mnt/archil; [ -d \"$MNT\" ] || MNT=/mnt\n"
      "sync\n"
      "archil checkpoints create \"$MNT\" ckpt-v1 || archil checkpoints create /mnt/archil ckpt-v1\n"
  )
  disk.exec(ckpt_cmd)  # -> "Checkpoint 'ckpt-v1' created successfully." in ~0.82s
  ```
- **Branches (`disk.create_branch`, `disk.list_branches`, `disk.get_branch` — Verified Live in 0.19s):**
  ```python
  br = disk.create_branch("exp-branch", from_checkpoint="ckpt-v1", from_branch=None)
  # br -> Branch(root_filesystem_id, branch_name, filesystem_id, from_checkpoint_name, from_checkpoint_filesystem_id, created_at)
  branch_disk = archil.get_disk(br.filesystem_id).wait_until_ready()
  # GOTCHA: Never call branch_disk.delete() directly ("Cannot delete a branch disk directly; delete the root disk instead"). Calling root_disk.delete() deletes all branches!
  ```
- **Delegations / Leases (`disk.list_delegations`, `disk.revoke_delegation`):**
  ```python
  for d in disk.list_delegations():
      # d -> Delegation(client_id, inode_id, is_pending, is_orphaned, path)
      if d.is_orphaned:
          disk.revoke_delegation(d)
  ```

---

## 4. Multi-Disk Workspaces & Drop-In Agent Tools (`archil.workspace`)
- Combines multiple disks under top-level prefix names (`<name>/...`), implementing the exact same methods as `Disk` (`get_object`, `put_object`, `delete_object`, `list_objects`, `grep`, `exec`, `agent_tools`) and enforcing `read_only=True` in Python as well as in `exec`!
  ```python
  ws = archil.workspace({
      "work": work_disk,
      "truth": ExecMountSpec(truth_disk, subdirectory="traces", read_only=True),
  })
  # Direct API:
  ws.put_object("work/output.json", "{}")
  ws.get_object("truth/session.jsonl")
  ws.grep(directory="", pattern="ERROR", recursive=True)  # fans out across all mounted disks in parallel!
  ws.exec("ls -la /mnt/work /mnt/truth")

  # Dynamic mount/unmount at runtime:
  ws.add_disk("branch_a", branch_disk)
  ws.remove_disk("branch_a")

  # Agent tools (read_file, write_file, delete_file, list_files, grep, run_bash):
  raw_tools = ws.agent_tools().tools                     # list[BoundTool(name, description, parameters, fn, afn)]
  oa_tools = ws.agent_tools().for_openai_agents()
  lc_tools = ws.agent_tools().for_langchain()
  ```

---

## 5. Sandboxes (`archil.create_sandbox`, `sandbox.fork`, `sandbox.pause`, `sandbox.exec`, `sandbox.run`)
- **Lifecycle & Forking:**
  ```python
  sb = archil.create_sandbox(
      name="agent-root",
      vcpu_count=2,          # 1..32 (default 1)
      mem_size_mib=2048,     # 256..65536 (default 2048)
      base_image="python:3.12-slim",
      mounts=[
          SandboxMountSpec(disk=truth_disk, path="/mnt/truth", read_only=True),
          SandboxMountSpec(disk=work_disk, path="/mnt/work", conditional=True),
      ],
      ports=[8080],
  )
  res = sb.exec("python3 --version", cwd="/")  # SandboxProcessResult(status, stdout, stderr, exit_code)

  # Fork a running or paused sandbox (NOTE: a sandbox with extra `mounts` must be stopped before forking;
  # a sandbox without extra `mounts` can be forked while running — it auto-pauses, snapshots, clones child in ~5s, and resumes parent!):
  # GOTCHA: Sandbox names must be unique across your active sandboxes ("A sandbox with this name already exists").
  # GOTCHA: Always call sb.stop() before sb.delete() ("Stop the sandbox before deleting it unless it has exited or failed").
  # GOTCHA: Delete CHILD sandboxes BEFORE deleting their PARENT sandbox ("sandbox has dependent forks: delete 1 child sandbox disk first"). (Opposite of Disks, where deleting the root disk deletes all branches!)
  child_sb = sb.fork(name="hypothesis-a-001")

  # File upload/download to running sandbox:
  sb.files.upload_file("./local.py", "/work/local.py")
  sb.files.download_file("/work/out.json", "./out.json")

  # Expose public HTTPS endpoint or private port token:
  host = sb.expose_port(8080)  # -> https://<host>
  tok = sb.create_port_token(8080, ttl="1h")  # headers={"X-Archil-Token": tok.token}
  ```
- **Network Egress Policy & Header Injection (`drain_on_pause`, `SandboxEgressTransform`):**
  - Can lock a sandbox to specific domains (`default="deny"`, `allow=[...]`), inject API keys at the hypervisor boundary (`SandboxEgressTransform(headers={"Authorization": ...})`) so the sandbox guest NEVER sees the secret key in env/disk, or drain active LLM streams before pausing (`drain_on_pause=["*.anthropic.com", "api.openai.com"]`)!
