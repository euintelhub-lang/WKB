"""bot.py — Telegram front-end for the decision tree in tree.json.

Run with:
    BOT_TOKEN=<your token from @BotFather> python bot.py

Commands:
    /start   — begin (or restart) the decision tree
    /restart — same as /start, explicit

Every meaningful step (session start, each choice, invalid input, restart,
reaching a leaf) is appended to steps.jsonl via steplog.log_event, so
analyze.py can compute a drop-off funnel afterwards.
"""

import logging
import os
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from engine import START_NODE, get_node, is_leaf, load_tree, resolve_choice
from steplog import log_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TREE_PATH = Path(__file__).parent / "tree.json"
TREE = load_tree(TREE_PATH)

# In-memory per-user state: user_id -> current node id. A demo-scale
# choice — fine for testing with a handful of users; a restart of the
# process loses it, which is acceptable for an MVP walking-skeleton.
USER_STATE: dict[int, str] = {}


def render_node(node_id: str) -> tuple[str, InlineKeyboardMarkup | None]:
    node = get_node(TREE, node_id)
    if is_leaf(TREE, node_id):
        return node["text"] + "\n\n/start за нов избор", None
    buttons = [
        [InlineKeyboardButton(opt["label"], callback_data=f"{node_id}:{i}")]
        for i, opt in enumerate(node["options"])
    ]
    return node["text"], InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_restart = update.message.text.strip().lower().startswith("/restart")
    USER_STATE[user_id] = START_NODE
    log_event(user_id, "restart" if is_restart else "start", START_NODE)
    text, markup = render_node(START_NODE)
    await update.message.reply_text(text, reply_markup=markup)


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    node_id, _, index_str = query.data.partition(":")
    current_node = USER_STATE.get(user_id)

    # Guard against a stale button: user clicked an old keyboard after
    # already moving on (e.g. from a previous /start). Treat it as
    # invalid input rather than silently acting on a node they've left.
    if current_node != node_id:
        log_event(user_id, "invalid_input", node_id or "unknown", reason="stale_button")
        await query.edit_message_text("Тази стъпка вече не е активна. Напиши /start за начало.")
        return

    next_node = resolve_choice(TREE, node_id, int(index_str))
    if next_node is None:
        log_event(user_id, "invalid_input", node_id, reason="bad_choice_index")
        await query.edit_message_text("Невалиден избор. Напиши /start за начало.")
        return

    choice_label = TREE[node_id]["options"][int(index_str)]["label"]
    log_event(user_id, "choice", node_id, choice_label=choice_label, next_node=next_node)

    USER_STATE[user_id] = next_node
    text, markup = render_node(next_node)
    await query.edit_message_text(text, reply_markup=markup)

    if is_leaf(TREE, next_node):
        log_event(user_id, "complete", next_node)


async def handle_stray_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # A free-text message while a keyboard is pending — the tree only
    # understands button taps, so nudge the user back to the buttons
    # instead of failing silently.
    user_id = update.effective_user.id
    node_id = USER_STATE.get(user_id, START_NODE)
    log_event(user_id, "invalid_input", node_id, reason="free_text")
    await update.message.reply_text("Моля, избери една от опциите по-горе (или /start).")


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("error: set BOT_TOKEN env var (token from @BotFather)")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler(["start", "restart"], start))
    app.add_handler(CallbackQueryHandler(handle_choice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stray_text))

    logger.info("bot starting, polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
