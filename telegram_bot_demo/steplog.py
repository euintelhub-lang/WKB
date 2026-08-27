"""steplog.py — append-only JSONL logging of user steps through the tree.

One line per event. This is the raw material analyze.py reads to compute
drop-off: where in the tree sessions end without ever reaching a leaf.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).parent / "steps.jsonl"
_lock = threading.Lock()


def log_event(user_id: int, event: str, node: str, log_path: Path = DEFAULT_LOG_PATH, **extra) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "event": event,  # start | choice | invalid_input | complete | restart
        "node": node,
        **extra,
    }
    line = json.dumps(record, ensure_ascii=False)
    with _lock:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
