---
name: auto-coder
description: Autonomous spec-driven development agent. Reads DEV_SPEC.md, identifies next task, implements code, runs tests, and persists progress — all in one command with minimal user intervention. Use when user says "auto code", "自动开发", "自动写代码", "auto dev", "一键开发", "autopilot", or wants fully automated spec-to-code workflow. Replaces manual dev-workflow pipeline with autonomous execution.
---

# Auto Coder

Autonomous agent: one trigger completes **read spec → find task → code → test → persist progress**.

## Trigger

| User Says | Behavior |
|-----------|----------|
| "auto code" / "自动开发" | Next task, full cycle |
| "auto code B2" | Specific task |
| "auto code --no-commit" | Skip git commit |

---

## Pipeline

```
Sync Spec (DEV_SPEC + Supplements) → Find Task → Implement → Test (≤3 fix rounds) → Persist
```

Only pause at the very end for commit confirmation. Everything else runs autonomously.

> **⚠️ CRITICAL: ALL Python commands MUST run inside the project venv.**
> Before executing ANY `python` or `pytest` command, activate the venv first:
> ```powershell
> .\.venv\Scripts\Activate.ps1
> ```
> Verify by checking `Get-Command python` points to `.venv\Scripts\python.exe`.
> **Never use system Python. Never skip this step.**

---

### 1. Sync Spec

Activate venv first, then sync:
```powershell
.\.venv\Scripts\Activate.ps1
python .github/skills/auto-coder/scripts/sync_spec.py
```

This syncs **two sources**:
1. **DEV_SPEC.md chapters** → `.github/skills/auto-coder/specs/01-07.md`
2. **Supplementary docs** (e.g., `*_SPEC.md`, `*_GUIDE.md`) → `specs/supplements/`

Then read:
- `.github/skills/auto-coder/specs/06-schedule.md` — task statuses
- `.github/skills/auto-coder/specs/specification_index.md` — index of all available docs

**New**: The index file lists all specifications and their purposes, making it easy to reference supplementary guides during implementation.

Task markers:

| Marker | Status |
|--------|--------|
| `[ ]` / `⬜` | Not started |
| `[~]` / `🔶` / `(进行中)` | In progress |
| `[x]` / `✅` / `(已完成)` | Completed |

---

### 2. Find Task

Priority: first `IN_PROGRESS`, then first `NOT_STARTED`. If user specified a task ID, use that directly.

Quick-check predecessor artifacts exist (file-level only). On mismatch, log warning and continue — only stop if the target task itself is blocked.

---

### 3. Implement

1. **Read relevant specs** from `.github/skills/auto-coder/specs/`:
   - Architecture: `05-architecture.md`
   - Tech details: `03-tech-stack.md`
   - Testing conventions: `04-testing.md`
   - **NEW**: Check `specification_index.md` for supplementary guide references

2. **Consult supplementary guides** in `specs/supplements/` for detailed:
   - Implementation code examples
   - Complete class/function signatures
   - Test scenarios and validation approaches
   - Example: If implementing Loader, read `supplements/LOADER_EXTENSION_SPEC.md`

3. **Extract** from specs: inputs/outputs, design principles (Pluggable? Config-driven? Factory?), file list, acceptance criteria.

4. **Plan** files to create/modify before writing any code.

5. **Code** — mandatory standards:
   - Type hints on all signatures
   - Google-style docstrings on public APIs
   - No hardcoded values (use config)
   - Single responsibility, short functions
   - Error handling for external integrations
   - Reference supplementary docs for code patterns and examples

6. **Write tests** alongside code:
   - `tests/unit/test_<module>.py` or `tests/integration/` per spec
   - Naming: `test_<func>_<scenario>_<expected>`
   - Mock external deps in unit tests
   - Check supplementary test scenarios for comprehensive coverage

7. **Self-review** before running tests: all planned files exist, type hints present, no hardcoded values, tests import correctly.

---

### 4. Test & Auto-Fix

```

Round 0..2:
  Run pytest on relevant test file
  If pass → go to step 5
  If fail → analyze error, apply fix, re-run

Round 3 still failing → STOP, show failure report to user
```

---

### 5. Persist

1. **Update `DEV_SPEC.md`** (global file): change task marker `[ ]` → `[x]`
2. **Re-sync**: `python .github/skills/auto-coder/scripts/sync_spec.py --force`
   - This updates chapters AND rescans supplementary docs
   - Generates fresh `specification_index.md`
3. **Show summary & ask**:

```
✅ [A3] 配置加载与校验 — done
   Files: src/core/settings.py, tests/unit/test_settings.py
   Tests: 8/8 passed
   Commit: feat(config): [A3] implement config loader
   
   Synced: 7 chapters + 5 supplementary guides
   Latest docs: specs/supplements/LOADER_EXTENSION_SPEC.md, ...

   "commit" → git add + commit
   "skip"   → end
   "next"   → commit + start next task
```

On "next", loop back to step 1 for the next task (auto-synced spec will be fresh).

---

## Guardrails

- One task per cycle, atomic commits
- Spec is single source of truth
- 3-round test fix limit
- Match existing codebase style
- **MUST activate `.venv` before ANY `python`/`pytest` command** — no exceptions. If unsure whether venv is active, run `.\.venv\Scripts\Activate.ps1` again (idempotent)

---

## Directory Structure

```
auto-coder/
├── SKILL.md                        ← this file
├── .spec_hash                      ← auto-generated hash (includes supplements)
├── scripts/
│   └── sync_spec.py               ← syncs DEV_SPEC.md chapters + supplements
└── specs/                          ← auto-generated from sync
    ├── 01-overview.md
    ├── 02-features.md
    ├── 03-tech-stack.md
    ├── 04-testing.md
    ├── 05-architecture.md
    ├── 06-schedule.md
    ├── 07-future.md
    ├── specification_index.md      ← ✨ NEW: lists all docs and guides
    └── supplements/                ← ✨ NEW: supplementary design docs
        ├── LOADER_EXTENSION_SPEC.md
        ├── STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md
        ├── DASHBOARD_ADAPTATION_GUIDE.md
        ├── IMPLEMENTATION_SUMMARY.md
        └── ...other_spec_guides.md
```

**Key Change**: `supplements/` directory now contains all `*_SPEC.md`, `*_GUIDE.md`, 
and other supplementary design documents synced from project root.

All paths are self-contained. This skill has no external dependencies on other skills.
