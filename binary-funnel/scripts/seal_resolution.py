#!/usr/bin/env python3
"""Bridge a Binary Funnel resolution export into a real WKB record.

Deliberately a separate, manual step from the app itself — WKB never
auto-fills `acceptable`, a human decides, so sealing is not triggered by
the browser. Run after downloading a resolution via ResolutionScreen's
"Export за WKB" button:

    python3 binary-funnel/scripts/seal_resolution.py export.json --dir records
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WKB_PY = REPO_ROOT / "wkb.py"


def build_body(export: dict) -> str:
    lines = [export["body"].rstrip("\n")]
    positions = export.get("positions") or []
    if positions:
        lines.append("")
        lines.append("## Dispatch positions")
        for p in positions:
            lines.append(f"- {p['provider']} (sha {p['sha'][:12]}...): {p['text']}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_file", help="JSON exported from ResolutionScreen")
    parser.add_argument("--dir", default="records")
    parser.add_argument("--parent", action="append", default=[])
    args = parser.parse_args(argv)

    export = json.loads(Path(args.export_file).read_text(encoding="utf-8"))
    for required in ("topic", "status", "regime", "body"):
        if required not in export:
            print(f"error: export is missing required field '{required}'", file=sys.stderr)
            return 2

    body = build_body(export)
    cmd = [
        sys.executable, str(WKB_PY), "seal",
        "--type", "funnel-resolution",
        "--topic", export["topic"],
        "--status", export["status"],
        "--regime", export["regime"],
        "--body", body,
        "--dir", args.dir,
    ]
    for p in args.parent:
        cmd.extend(["--parent", p])

    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
