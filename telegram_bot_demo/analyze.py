"""analyze.py — turn steps.jsonl into a drop-off funnel per node.

For each node reached, reports how many sessions reached it and how many
of those went on to reach a further node (advanced) vs stopped there
(dropped — either an explicit quit/invalid-input or simply no next event).

    python analyze.py [path/to/steps.jsonl]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).parent / "steps.jsonl"


def load_events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def sessions_by_user(events: list[dict]) -> dict:
    by_user = defaultdict(list)
    for e in events:
        by_user[e["user_id"]].append(e)
    for evs in by_user.values():
        evs.sort(key=lambda e: e["ts"])
    return by_user


def compute_funnel(events: list[dict]) -> dict:
    by_user = sessions_by_user(events)

    reached = defaultdict(int)   # node -> sessions that visited it
    completed = defaultdict(int)  # node -> sessions that left it via a further choice or completion
    dropped = defaultdict(int)   # node -> sessions whose last relevant event was here, unresolved

    for user_events in by_user.values():
        visited_nodes = []
        last_node = None
        finished = False
        for e in user_events:
            if e["event"] in ("start", "restart"):
                visited_nodes = [e["node"]]
                last_node = e["node"]
                finished = False
            elif e["event"] == "choice":
                visited_nodes.append(e["next_node"])
                last_node = e["next_node"]
            elif e["event"] == "complete":
                finished = True

        for n in visited_nodes:
            reached[n] += 1
        if last_node is not None:
            if finished:
                completed[last_node] += 1
            else:
                dropped[last_node] += 1
        for n in visited_nodes[:-1]:
            completed[n] += 1  # advanced past this node to the next one

    return {"reached": reached, "completed": completed, "dropped": dropped}


def print_report(funnel: dict) -> None:
    reached = funnel["reached"]
    dropped = funnel["dropped"]
    if not reached:
        print("(no sessions logged yet)")
        return
    print(f"{'node':<20} {'reached':>8} {'dropped_here':>14} {'drop_rate':>10}")
    for node, count in sorted(reached.items(), key=lambda kv: -kv[1]):
        d = dropped.get(node, 0)
        rate = f"{d / count:.0%}" if count else "-"
        print(f"{node:<20} {count:>8} {d:>14} {rate:>10}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LOG_PATH
    events = load_events(path)
    funnel = compute_funnel(events)
    print_report(funnel)
