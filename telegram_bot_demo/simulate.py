"""simulate.py — drive the decision tree from the terminal, no Telegram needed.

Exercises the same engine.py + steplog.py the real bot uses, so a session
run here produces the same kind of steps.jsonl that analyze.py reads.
Useful for testing the tree and the logging without a bot token.

    python simulate.py                # interactive
    python simulate.py --user-id 42   # tag the session as a specific user
"""

import argparse
from pathlib import Path

from engine import START_NODE, get_node, is_leaf, load_tree, resolve_choice
from steplog import log_event

TREE_PATH = Path(__file__).parent / "tree.json"


def run(user_id: int) -> None:
    tree = load_tree(TREE_PATH)
    node_id = START_NODE
    log_event(user_id, "start", node_id)

    while True:
        node = get_node(tree, node_id)
        print(f"\n{node['text']}")

        if is_leaf(tree, node_id):
            log_event(user_id, "complete", node_id)
            print("\n(край на пътя)")
            return

        options = node["options"]
        for i, opt in enumerate(options):
            print(f"  {i}: {opt['label']}")
        print("  q: изход (симулира drop-off)")

        try:
            raw = input("> ").strip().lower()
        except EOFError:
            raw = "q"
        if raw == "q":
            log_event(user_id, "invalid_input", node_id, reason="user_quit")
            print("(сесията приключи без да стигне до резултат — drop-off)")
            return

        if not raw.isdigit():
            log_event(user_id, "invalid_input", node_id, reason="non_numeric")
            print("Моля, въведи номер на опция.")
            continue

        next_node = resolve_choice(tree, node_id, int(raw))
        if next_node is None:
            log_event(user_id, "invalid_input", node_id, reason="bad_choice_index")
            print("Невалиден номер, опитай пак.")
            continue

        log_event(user_id, "choice", node_id, choice_label=options[int(raw)]["label"], next_node=next_node)
        node_id = next_node


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, default=1)
    args = parser.parse_args()
    run(args.user_id)
