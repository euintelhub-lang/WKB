---
name: run-wkb
description: Build, run, and test wkb.py (seal/check/ls/bridge — the WKB v1.2 record CLI). Use when asked to run wkb, test wkb.py, seal a WKB record, check a record's checksum, or bridge a record to another format.
---

`wkb.py` is a single-file Python CLI at the repo root — no build step,
no server, no GUI. Drive it directly, or via `scripts/smoke.sh`
(the same script CI runs) for an end-to-end pass over all four
commands. All paths below are relative to the repo root.

## Prerequisites

```bash
python3 --version   # tested on 3.11
pip install pyyaml   # only external dependency; often already present —
                      # `python3 -c "import yaml"` to check first
```

No build step — `wkb.py` runs as-is.

## Run (agent path)

The fastest way to confirm the tool works end to end is the same smoke
test CI runs:

```bash
bash scripts/smoke.sh
# → PASS: seal + check
# → PASS: bridge json -> SUCCESS
# → PASS: bridge csv -> DEGRADED (3 reasons)
# → PASS: bridge unknown-format -> generic fallback
# → PASS: bridge on tampered record -> FAILED
# → PASS: ls
# → ALL SMOKE TESTS PASSED
```

It seals real records into a throwaway `mktemp -d` directory, so it's
safe to run repeatedly — it doesn't touch a `records/` dir in the repo.

Individual commands, run from the repo root (records land in `./records/`):

```bash
python3 wkb.py seal --type decision --topic "..." --body "..."
# → sealed records/wkb-YYYYMMDD-xxxx.md id=wkb-YYYYMMDD-xxxx sha=...

python3 wkb.py check records/wkb-YYYYMMDD-xxxx.md
# → PASS records/... id=... sha=...   (or FAIL + reasons, exit 1)

python3 wkb.py ls
# → one line per record: id, type, status, topic

python3 wkb.py bridge records/wkb-YYYYMMDD-xxxx.md --target json
# → status: SUCCESS|DEGRADED|FAILED, dropped_fields, payload

python3 wkb.py bridge records/wkb-YYYYMMDD-xxxx.md --target restore
# → semantic translation: walks the parent chain and produces a
#   natural-language briefing a fresh LLM session can restore from,
#   not a structural field dump. --dir overrides where parents are
#   looked up (default: the file's own directory).
```

`seal` accepts `--parent <id>` (repeatable, must be a real `wkb-id`),
`--regime <state>@<source>`, `--interpretation
{rumen_only,claude_only,consensus}`, `--raw <note>`. Invalid `--parent`
or `--regime` (missing `@source`) are rejected at seal time, not later.

## Direct invocation

Most PRs touch `wkb.py`'s internals (e.g. `bridge_record`,
`KNOWN_TARGETS`) rather than just the CLI surface. Import and call
directly instead of shelling out:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
import wkb
header = {'wkb': '1.2', 'id': 'wkb-20260823-test', 'type': 'decision',
          'status': 'pending', 'parent': [], 'interpretation': '',
          'topic': 't', 'sha': None, 'regime': None}
body = 'hello\n'
header['sha'] = wkb.body_sha(body)
print(wkb.bridge_record(header, body, 'json').status)
"
# → SUCCESS
```

## Test

```bash
bash scripts/smoke.sh
```

Same command CI runs (`.github/workflows/ci.yml`, on push/PR/`workflow_dispatch`).
No separate unit test suite exists yet — `scripts/smoke.sh` is it.

## Gotchas

- **`regime` without `@source` doesn't degrade, it's rejected outright** —
  `seal --regime "expanding"` (no `@`) raises `WkbError` and exits 2.
  Per the v1.2 decision: "regime без произход не е поле."
- **`bridge` refuses to translate an unverified record.** If the header
  `sha` doesn't match the actual body hash, `bridge` returns `FAILED`
  regardless of `--target` — it never attempts translation on a record
  that fails its own integrity check.
- **CSV bridging is lossy by construction**, not a bug to fix: multiple
  `parent` entries collapse to the first one (`LOSSY_ENCODING`), a
  multiline body gets flattened (`LOSSY_ENCODING`), and anything over
  200 chars in the body cell is truncated (`CONSTRAINT_EXCEEDED`) —
  all three fire independently and appear together in `dropped_fields`.
- **`acceptable` is always `None`/unset in `bridge` output** — this is
  intentional (v1.2 decision: "acceptable никога не се попълва
  автоматично — Rumen решава"), not a missing feature.
- **No emoji rendering.** The v1.0 emoji legend was never recovered
  from source material — this implementation is YAML-only.
- **`--target restore` is the only *semantic* target** — `json`/`csv`
  structurally re-encode the same fields; `restore` walks `parent`
  and produces prose meant for a different LLM session to pick up
  continuity from (the "Semantic Engine" from the dialog log, and the
  first real consumer of the `parent` DAG). A missing ancestor doesn't
  fail the bridge — it degrades with `LOSSY_ENCODING` and a note
  naming which id(s) were unresolvable.
