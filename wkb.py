#!/usr/bin/env python3
"""wkb.py — reference implementation of the WKB v1.2 minimal record schema.

Built from the schema reconstructed out of Google Drive material:
  - wkb-20260727-b7e2 (critique that produced v1.2: YAML is the source of
    truth, emoji is only a render; parent must be a real id, not free text;
    sha is a real checksum on the body; regime is state@source or absent)
  - the WKBE dialog log (interpretation enum added 2026-08-16)

Four commands: check, seal, ls (named in the dialog log), plus bridge —
the BridgeResult contract added 2026-08-16 (SUCCESS/DEGRADED/FAILED,
dropped_fields with a reason, generic fallback for unknown targets).

Record format: a Markdown file with a YAML frontmatter header (delimited
by '---' lines), followed by a free-text body.

    ---
    wkb: "1.2"
    id: wkb-20260823-a1b2
    type: decision
    status: pending
    parent: []
    interpretation: ""
    topic: "..."
    sha: "<sha256 of the body>"
    ---
    Body text goes here.

Known gaps, left unfilled rather than guessed:
  - The emoji legend (which symbol renders which field) was never
    captured as text anywhere in Drive — only UI labels survived. This
    implementation is YAML-only; no emoji rendering.
  - The full v1.0 canonical `type`/`status` enums were never recovered.
    Both are free-form strings here, not validated against a closed set.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import uuid
from dataclasses import dataclass, field as dataclass_field
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

WKB_VERSION = "1.2"
ID_RE = re.compile(r"^wkb-(\d{8})-([0-9a-f]{4})$")
INTERPRETATION_VALUES = {"", "rumen_only", "claude_only", "consensus"}
DEFAULT_DIR = Path("records")


class WkbError(Exception):
    pass


def make_id(on_date: date | None = None) -> str:
    on_date = on_date or datetime.now(timezone.utc).date()
    return f"wkb-{on_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}"


def validate_id(value: str, field: str) -> None:
    if not ID_RE.match(value):
        raise WkbError(
            f"{field}: '{value}' is not a valid wkb id "
            "(expected wkb-YYYYMMDD-<4 hex chars>)"
        )


def validate_regime(value: str) -> None:
    # Defect #4 from the v1.2 critique: a regime without a stated origin
    # (the part after '@') is not allowed to exist at all.
    if value and "@" not in value:
        raise WkbError(
            f"regime: '{value}' has no '@source' — "
            "regime without provenance is not a field, per v1.2 decision"
        )


def validate_interpretation(value: str) -> None:
    if value not in INTERPRETATION_VALUES:
        raise WkbError(
            f"interpretation: '{value}' not in {sorted(INTERPRETATION_VALUES)}"
        )


def split_record(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise WkbError("record has no YAML frontmatter (must start with '---')")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise WkbError("record frontmatter is not closed with a second '---'")
    header = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return header, body


def render_record(header: dict, body: str) -> str:
    yaml_text = yaml.safe_dump(header, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_text}---\n{body}"


def body_sha(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


# --- Bridge --------------------------------------------------------------
# From the WKBE dialog log, 2026-08-16: "Bridge частично решен — BridgeResult
# contract + generic fallback." Closed enum SUCCESS/DEGRADED/FAILED.
# dropped_fields carries a reason (NO_TARGET_EQUIVALENT / LOSSY_ENCODING /
# CONSTRAINT_EXCEEDED). acceptable is never auto-filled — a human decides.
# Unknown target_format falls back to the 9 core fields, raw, untranslated,
# marked DEGRADED.

CORE_FIELDS = (
    "wkb", "id", "type", "status", "parent",
    "interpretation", "topic", "sha", "regime",
)  # the 9 fields from the v1.2 critique (regime is the one that's optional)

REASON_NO_TARGET_EQUIVALENT = "NO_TARGET_EQUIVALENT"
REASON_LOSSY_ENCODING = "LOSSY_ENCODING"
REASON_CONSTRAINT_EXCEEDED = "CONSTRAINT_EXCEEDED"

CSV_CELL_LIMIT = 200  # a flat CSV cell can't hold arbitrary body length


@dataclass
class BridgeResult:
    status: str  # SUCCESS | DEGRADED | FAILED
    target_format: str
    dropped_fields: list = dataclass_field(default_factory=list)
    acceptable: None = None  # spec: never auto-filled, Rumen decides
    payload: object = None
    note: str = ""


def _bridge_to_json(header: dict, body: str) -> BridgeResult:
    payload = {k: header.get(k) for k in CORE_FIELDS}
    payload["body"] = body
    return BridgeResult(
        status="SUCCESS",
        target_format="json",
        payload=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False),
    )


def _bridge_to_csv(header: dict, body: str) -> BridgeResult:
    dropped = []
    row = {}
    for f in CORE_FIELDS:
        v = header.get(f)
        if f == "parent" and isinstance(v, list):
            if len(v) > 1:
                dropped.append({"field": "parent", "reason": REASON_LOSSY_ENCODING})
            v = v[0] if v else ""
        row[f] = "" if v is None else str(v)

    if "\n" in body:
        dropped.append({"field": "body", "reason": REASON_LOSSY_ENCODING})
    body_cell = " ".join(body.split())
    if len(body_cell) > CSV_CELL_LIMIT:
        dropped.append({"field": "body", "reason": REASON_CONSTRAINT_EXCEEDED})
        body_cell = body_cell[:CSV_CELL_LIMIT]
    row["body"] = body_cell

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(CORE_FIELDS) + ["body"])
    writer.writeheader()
    writer.writerow(row)

    return BridgeResult(
        status="DEGRADED" if dropped else "SUCCESS",
        target_format="csv",
        dropped_fields=dropped,
        payload=buf.getvalue(),
    )


KNOWN_TARGETS = {"json": _bridge_to_json, "csv": _bridge_to_csv}


def _bridge_generic_fallback(header: dict, target_format: str) -> BridgeResult:
    payload = {k: header.get(k) for k in CORE_FIELDS}
    dropped = [
        {"field": k, "reason": REASON_NO_TARGET_EQUIVALENT}
        for k in header
        if k not in CORE_FIELDS
    ]
    return BridgeResult(
        status="DEGRADED",
        target_format=target_format,
        dropped_fields=dropped,
        payload=payload,
        note="unknown target_format — generic fallback, core fields only, no semantic translation",
    )


def bridge_record(header: dict, body: str, target_format: str) -> BridgeResult:
    if header.get("sha") != body_sha(body):
        return BridgeResult(
            status="FAILED",
            target_format=target_format,
            note="record fails its own sha check — refusing to bridge an unverified record",
        )
    translate = KNOWN_TARGETS.get(target_format)
    if translate:
        return translate(header, body)
    return _bridge_generic_fallback(header, target_format)


def cmd_bridge(args: argparse.Namespace) -> int:
    path = Path(args.file)
    text = path.read_text(encoding="utf-8")
    try:
        header, body = split_record(text)
    except WkbError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    result = bridge_record(header, body, args.target)
    print(f"status: {result.status}")
    print(f"target_format: {result.target_format}")
    print("acceptable: <not set — Rumen decides>")
    if result.note:
        print(f"note: {result.note}")
    if result.dropped_fields:
        print("dropped_fields:")
        for d in result.dropped_fields:
            print(f"  - {d['field']}: {d['reason']}")
    else:
        print("dropped_fields: []")
    if result.payload is not None:
        print("payload:")
        payload = result.payload
        print(payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2))

    return 1 if result.status == "FAILED" else 0


def cmd_seal(args: argparse.Namespace) -> int:
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    elif args.body is not None:
        body = args.body
    else:
        body = sys.stdin.read()
    body = body.rstrip("\n") + "\n"

    parents = args.parent or []
    for p in parents:
        validate_id(p, "parent")
    validate_regime(args.regime or "")
    validate_interpretation(args.interpretation)

    record_id = make_id()
    header = {
        "wkb": WKB_VERSION,
        "id": record_id,
        "type": args.type,
        "status": args.status,
        "parent": parents,
        "interpretation": args.interpretation,
        "topic": args.topic,
        "sha": body_sha(body),
    }
    if args.regime:
        header["regime"] = args.regime
    if args.raw:
        header["raw"] = args.raw

    out_dir = Path(args.dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{record_id}.md"
    out_path.write_text(render_record(header, body), encoding="utf-8")

    print(f"sealed {out_path} id={record_id} sha={header['sha'][:12]}...")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.file)
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []

    try:
        header, body = split_record(text)
    except WkbError as e:
        print(f"FAIL {path}: {e}")
        return 1

    for field in ("wkb", "id", "type", "status", "topic", "sha"):
        if field not in header:
            problems.append(f"missing required field: {field}")

    if "id" in header:
        try:
            validate_id(header["id"], "id")
        except WkbError as e:
            problems.append(str(e))

    for p in header.get("parent") or []:
        try:
            validate_id(p, "parent")
        except WkbError as e:
            problems.append(str(e))

    try:
        validate_regime(header.get("regime", ""))
    except WkbError as e:
        problems.append(str(e))

    try:
        validate_interpretation(header.get("interpretation", ""))
    except WkbError as e:
        problems.append(str(e))

    expected_sha = header.get("sha", "")
    actual_sha = body_sha(body)
    if expected_sha != actual_sha:
        problems.append(
            f"sha mismatch: header says {expected_sha[:12]}..., "
            f"body hashes to {actual_sha[:12]}..."
        )

    if problems:
        print(f"FAIL {path}")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"PASS {path} id={header['id']} sha={actual_sha[:12]}...")
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    d = Path(args.dir)
    if not d.exists():
        print(f"(no such directory: {d})")
        return 0

    records = []
    for path in sorted(d.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            header, body = split_record(text)
        except WkbError as e:
            records.append((path.name, None, str(e)))
            continue
        ok = header.get("sha") == body_sha(body)
        records.append((path.name, header, None if ok else "sha mismatch"))

    if not records:
        print(f"(no records in {d})")
        return 0

    for name, header, err in records:
        if header is None:
            print(f"{name}: UNREADABLE ({err})")
            continue
        flag = "" if err is None else f"  [{err}]"
        print(
            f"{header.get('id', name):24} "
            f"{header.get('type', '?'):12} "
            f"{header.get('status', '?'):10} "
            f"{header.get('topic', '')}{flag}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wkb.py", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    seal = sub.add_parser("seal", help="create and checksum a new record")
    seal.add_argument("--type", required=True)
    seal.add_argument("--topic", required=True)
    seal.add_argument("--status", default="pending")
    seal.add_argument("--parent", action="append", default=[])
    seal.add_argument("--interpretation", default="")
    seal.add_argument("--regime", default="")
    seal.add_argument("--raw", default="")
    seal.add_argument("--body")
    seal.add_argument("--body-file")
    seal.add_argument("--dir", default=str(DEFAULT_DIR))
    seal.set_defaults(func=cmd_seal)

    check = sub.add_parser("check", help="verify a record's checksum and fields")
    check.add_argument("file")
    check.set_defaults(func=cmd_check)

    ls = sub.add_parser("ls", help="list records in a directory")
    ls.add_argument("--dir", default=str(DEFAULT_DIR))
    ls.set_defaults(func=cmd_ls)

    bridge = sub.add_parser(
        "bridge", help="translate a record to a target format (SUCCESS/DEGRADED/FAILED)"
    )
    bridge.add_argument("file")
    bridge.add_argument("--target", required=True)
    bridge.set_defaults(func=cmd_bridge)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except WkbError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
