"""engine.py — a tiny decision-tree engine, independent of Telegram.

Loads a tree from JSON (node id -> {text, options: [{label, next}]}) and
answers two questions: what does a node show, and where does a given
choice lead. Kept free of any bot/network code so it can be driven by
the real Telegram bot or by simulate.py for local testing.
"""

import json
from pathlib import Path

START_NODE = "start"


class TreeError(Exception):
    pass


def load_tree(path: Path) -> dict:
    tree = json.loads(Path(path).read_text(encoding="utf-8"))
    if START_NODE not in tree:
        raise TreeError(f"tree has no '{START_NODE}' node")
    for node_id, node in tree.items():
        for opt in node.get("options", []):
            if opt["next"] not in tree:
                raise TreeError(f"node '{node_id}' points to missing node '{opt['next']}'")
    return tree


def get_node(tree: dict, node_id: str) -> dict:
    if node_id not in tree:
        raise TreeError(f"no such node: {node_id}")
    return tree[node_id]


def is_leaf(tree: dict, node_id: str) -> bool:
    return not get_node(tree, node_id).get("options")


def resolve_choice(tree: dict, node_id: str, choice_index: int) -> str | None:
    """Return the next node id for choice_index at node_id, or None if invalid."""
    options = get_node(tree, node_id).get("options", [])
    if choice_index < 0 or choice_index >= len(options):
        return None
    return options[choice_index]["next"]
