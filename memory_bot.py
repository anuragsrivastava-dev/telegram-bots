import os
import asyncio
import random
import re
import time
import sqlite3
from config import MEMORY_BOT_TOKEN, ADMIN_USER_ID

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "memory_scores.db")

EMOJI_BANK = [
    "🌹", "💌", "🍫", "🥂", "💍", "✈️", "🌙", "🐱",
    "💋", "🍓", "🧸", "🍒", "🎁", "🕯️", "💎"
]
HIDDEN_CARD = "❓"

GRID_PRESETS = {
    "3x4": {"rows": 3, "cols": 4, "pairs": 6, "label": "3×4 \\(6 Pairs \\- Quick\\)"},
    "4x4": {"rows": 4, "cols": 4, "pairs": 8, "label": "4×4 \\(8 Pairs \\- Classic\\)"},
    "4x5": {"rows": 5, "cols": 4, "pairs": 10, "label": "4×5 \\(10 Pairs \\- Extended\\)"},
    "4x6": {"rows": 6, "cols": 4, "pairs": 12, "label": "4×6 \\(12 Pairs \\- Master\\)"},
}

# chat_id -> GameState dict
games: dict[int, dict] = {}


# ----------------------------------------------------
# SQLite Database Management
# ----------------------------------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                chat_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                wins INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                pairs_found INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        conn.commit()


init_db()


def record_game_results(chat_id: int, players: list[int], names: dict[int, str], scores: dict[int, int],
                        winner_id: int | None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for uid in players:
            uname = names.get(uid, "Unknown")
            is_win = 1 if (winner_id is not None and uid == winner_id) else 0
            pairs = scores.get(uid, 0)

            cursor.execute(
                """
                INSERT INTO stats (chat_id, user_id, user_name, wins, games_played, pairs_found)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    user_name = excluded.user_name,
                    wins = wins + excluded.wins,
                    games_played = games_played + 1,
                    pairs_found = pairs_found + excluded.pairs_found
                """,
                (chat_id, uid, uname, is_win, pairs)
            )
        conn.commit()


def get_chat_leaderboard(chat_id: int) -> list[tuple]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_name, wins, games_played, pairs_found
            FROM stats
            WHERE chat_id = ?
            ORDER BY wins DESC, pairs_found DESC
            LIMIT 10
            """,
            (chat_id,)
        )
        return cursor.fetchall()


def build_leaderboard_text(chat_id: int) -> str:
    leaderboard = get_chat_leaderboard(chat_id)
    if not leaderboard:
        return (
            "📊 *No games recorded yet\\!*\n\n"
            "Play a round with `.match` to start tracking your head\\-to\\-head wins\\."
        )

    lines = ["🏆 *Couple Memory Duel \\- All\\-Time Leaderboard*\n"]
    for idx, (uname, wins, played, pairs) in enumerate(leaderboard, start=1):
        escaped_name = escape_md(uname)
        win_rate = int((wins / played * 100)) if played > 0 else 0
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`{idx}\\.`"
        lines.append(
            f"{medal} *{escaped_name}*\n"
            f"   • 👑 Wins: `{wins}` / `{played}` matches \\({win_rate}% win rate\\)\n"
            f"   • 🧩 Total Pairs Found: `{pairs}`"
        )
    return "\n".join(lines)


# ----------------------------------------------------
# Game Logic & Helpers
# ----------------------------------------------------
def escape_md(text: str) -> str:
    """Escapes MarkdownV2 reserved characters."""
    if not text:
        return ""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


def get_grid_selector_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("⚡ 3×4 (Quick / 6 Pairs)", callback_data="grid_3x4"),
            InlineKeyboardButton("💖 4×4 (Classic / 8 Pairs)", callback_data="grid_4x4"),
        ],
        [
            InlineKeyboardButton("🔥 4×5 (10 Pairs)", callback_data="grid_4x5"),
            InlineKeyboardButton("👑 4×6 (Master / 12 Pairs)", callback_data="grid_4x6"),
        ],
        [
            InlineKeyboardButton("📊 View Leaderboard", callback_data="mem_view_stats"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_new_game(starter_id: int, starter_name: str, grid_key: str = "4x4") -> dict:
    preset = GRID_PRESETS.get(grid_key, GRID_PRESETS["4x4"])
    num_pairs = preset["pairs"]
    selected_emojis = random.sample(EMOJI_BANK, num_pairs)
    deck = selected_emojis * 2
    random.shuffle(deck)

    return {
        "grid_key": grid_key,
        "rows": preset["rows"],
        "cols": preset["cols"],
        "total_pairs": num_pairs,
        "board": deck,
        "revealed": [False] * len(deck),
        "flipped_indices": [],
        "players": [starter_id],
        "player_names": {starter_id: starter_name},
        "scores": {starter_id: 0},
        "current_turn_idx": 0,
        "lock": False,
        "recorded": False,
    }


def render_board(game: dict) -> InlineKeyboardMarkup:
    keyboard = []
    board = game["board"]
    revealed = game["revealed"]
    flipped = game["flipped_indices"]
    rows = game["rows"]
    cols = game["cols"]

    for r in range(rows):
        row_buttons = []
        for c in range(cols):
            idx = r * cols + c
            if revealed[idx] or idx in flipped:
                label = board[idx]
            else:
                label = HIDDEN_CARD
            row_buttons.append(
                InlineKeyboardButton(label, callback_data=f"flip_{idx}")
            )
        keyboard.append(row_buttons)

    # Control Row
    control_row = [
        InlineKeyboardButton("🔄 Replay", callback_data=f"mem_replay_{game['grid_key']}"),
        InlineKeyboardButton("📐 Size", callback_data="mem_change_grid"),
        InlineKeyboardButton("📊 Stats", callback_data="mem_view_stats"),
        InlineKeyboardButton("🛑 Stop", callback_data="mem_stop_game"),
    ]
    keyboard.append(control_row)
    return InlineKeyboardMarkup(keyboard)


def get_game_status_text(chat_id: int, game: dict) -> str:
    players = game["players"]
    names = game["player_names"]
    scores = game["scores"]
    total_pairs = game["total_pairs"]
    current_player_id = players[game["current_turn_idx"]]
    current_name = escape_md(names[current_player_id])

    # Check for game completion
    if all(game["revealed"]):
        if not game.get("recorded"):
            game["recorded"] = True
            winner_id = None
            if len(players) > 1:
                p1, p2 = players[0], players[1]
                if scores[p1] > scores[p2]:
                    winner_id = p1
                elif scores[p2] > scores[p1]:
                    winner_id = p2
            elif len(players) == 1:
                winner_id = players[0]
            record_game_results(chat_id, players, names, scores, winner_id)

        if len(players) == 1:
            return (
                f"🎉 *Game Complete\\!*\n\n"
                f"• *{current_name}* found all {total_pairs} pairs\\!\n\n"
                f"📊 _Score saved to leaderboard\\._"
            )
        p1, p2 = players[0], players[1]
        p1_name, p2_name = escape_md(names[p1]), escape_md(names[p2])
        p1_score, p2_score = scores[p1], scores[p2]

        if p1_score > p2_score:
            winner = f"🏆 *Winner:* *{p1_name}* \\({p1_score} vs {p2_score}\\)\\!"
        elif p2_score > p1_score:
            winner = f"🏆 *Winner:* *{p2_name}* \\({p2_score} vs {p1_score}\\)\\!"
        else:
            winner = f"🤝 *It's a Tie\\!* \\({p1_score} \\- {p2_score}\\)"

        return f"🎉 *All {total_pairs} Pairs Found\\!*\n\n{winner}\n\n📊 _Scores recorded to leaderboard\\._"

    # Active Game Status
    grid_name = GRID_PRESETS[game["grid_key"]]["label"]
    if len(players) == 1:
        score_line = f"• *{current_name}*: `{scores[current_player_id]}/{total_pairs}` pairs\n_\\(Waiting for Player 2 to tap a card\\.\\.\\.\\)_"
    else:
        p1, p2 = players[0], players[1]
        score_line = (
            f"• *{escape_md(names[p1])}*: `{scores[p1]}` pts\n"
            f"• *{escape_md(names[p2])}*: `{scores[p2]}` pts"
        )

    turn_line = f"👉 *Turn:* *{current_name}*"

    return (
        f"🧩 *Memory Match Duel* \\[{grid_name}\\]\n\n"
        f"{score_line}\n\n"
        f"{turn_line}\n"
        f"Tap two cards to find a match\\!"
    )


# ----------------------------------------------------
# Command Handlers
# ----------------------------------------------------
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    latency = int((time.time() - start_time) * 1000)
    await msg.edit_text(
        f"🏓 *Pong!* `{latency}ms`\n🧩 *Memory Match Bot* is Online & Ready!",
        parse_mode="Markdown"
    )


async def helpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorized to use admin commands.")
        return
    admin_help = (
        "👑 *Memory Match Bot Admin Control Panel:*\n\n"
        "• `/ping` — Check bot latency & online status\n"
        "• `/match` — Start Memory Match game\n"
        "• `/stop` — Stop active duel\n"
        "• `/stats` — View chat leaderboard & stats\n"
        "• `/helpad` — Show this admin help menu"
    )
    await update.message.reply_text(admin_help, parse_mode="Markdown")


async def start_game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🧩 *Memory Match Duel*\n\n"
        "Choose a grid size to start playing:"
    )
    await update.message.reply_text(
        msg,
        reply_markup=get_grid_selector_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def stop_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = games.pop(chat_id, None)

    if not game:
        await update.message.reply_text("❌ No active game is running.")
        return

    await update.message.reply_text(
        "🛑 *Game stopped\\.* Type `.match` or `/match` to start a new duel\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = build_leaderboard_text(chat_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Play Memory Match", callback_data="mem_change_grid")]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🧩 *Memory Match Duel Guide:*\n\n"
        "• `.match` or `/match` \\- Open grid size menu\n"
        "• `.stats` or `.leaderboard` \\- View head\\-to\\-head win counts\n"
        "• `.stop` or `/stop` \\- Stop the active game\n"
        "• Match a pair to score `+1 pt` and gain a bonus turn\\!"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


# ----------------------------------------------------
# Dot (.) Prefix Interceptor
# ----------------------------------------------------
async def handle_dot_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip().lower()
    if not text.startswith("."):
        return

    command = text[1:].split()[0].split("@")[0]

    if command == "ping":
        await ping_command(update, context)
    elif command == "helpad":
        await helpad_command(update, context)
    elif command in ["match", "memory", "mem", "pair"]:
        await start_game_menu(update, context)
    elif command in ["stop", "end", "cancel"]:
        await stop_game_command(update, context)
    elif command in ["stats", "score", "scores", "leaderboard", "ranks"]:
        await stats_command(update, context)
    elif command in ["help", "rules"]:
        await help_command(update, context)


# ----------------------------------------------------
# Inline Button Callbacks
# ----------------------------------------------------
async def handle_grid_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user = update.effective_user

    grid_key = query.data.replace("grid_", "")
    game = create_new_game(user.id, user.first_name, grid_key)
    games[chat_id] = game

    await query.edit_message_text(
        get_game_status_text(chat_id, game),
        reply_markup=render_board(game),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def handle_flip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    user = update.effective_user

    # Leaderboard View Button
    if query.data == "mem_view_stats":
        await query.answer()
        leaderboard_text = build_leaderboard_text(chat_id)

        active_game = games.get(chat_id)
        if active_game and not all(active_game["revealed"]):
            back_btn = InlineKeyboardButton("🔙 Back to Active Game", callback_data="mem_back_to_game")
        else:
            back_btn = InlineKeyboardButton("🔙 Choose Grid Size", callback_data="mem_change_grid")

        keyboard = InlineKeyboardMarkup([[back_btn]])
        await query.edit_message_text(
            leaderboard_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Return Back to Active Game Board
    if query.data == "mem_back_to_game":
        await query.answer()
        active_game = games.get(chat_id)
        if active_game:
            await query.edit_message_text(
                get_game_status_text(chat_id, active_game),
                reply_markup=render_board(active_game),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        else:
            await query.edit_message_text(
                "🧩 *Memory Match Duel*\n\nChoose a grid size to start playing:",
                reply_markup=get_grid_selector_keyboard(),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        return

    # Change Size / New Game Menu Selection
    if query.data == "mem_change_grid":
        await query.answer()
        await query.edit_message_text(
            "🧩 *Memory Match Duel*\n\nChoose a grid size to start playing:",
            reply_markup=get_grid_selector_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Stop Game Button Action
    if query.data == "mem_stop_game":
        await query.answer("Game stopped!")
        games.pop(chat_id, None)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎮 New Game", callback_data="mem_change_grid"),
                InlineKeyboardButton("📊 Leaderboard", callback_data="mem_view_stats"),
            ]
        ])
        await query.edit_message_text(
            "🛑 *Game stopped by user\\.*\nType `.match` or `/match` to start a new duel\\.",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    game = games.get(chat_id)
    if not game:
        await query.answer("No active game. Type .match to start!", show_alert=True)
        return

    # Handle Replay Same Size
    if query.data.startswith("mem_replay_"):
        await query.answer()
        grid_key = query.data.replace("mem_replay_", "")
        new_game = create_new_game(user.id, user.first_name, grid_key)
        games[chat_id] = new_game
        await query.edit_message_text(
            get_game_status_text(chat_id, new_game),
            reply_markup=render_board(new_game),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # STRICT LOCK: Reject clicks while mismatch is resetting
    if game["lock"]:
        await query.answer("Cards are resetting, please wait a second...", show_alert=False)
        return

    # Register second player
    if user.id not in game["players"]:
        if len(game["players"]) < 2:
            game["players"].append(user.id)
            game["player_names"][user.id] = user.first_name
            game["scores"][user.id] = 0
        else:
            await query.answer("This game already has 2 players!", show_alert=True)
            return

    # Turn validation
    current_player_id = game["players"][game["current_turn_idx"]]
    if user.id != current_player_id:
        current_name = game["player_names"][current_player_id]
        await query.answer(f"It's {current_name}'s turn!", show_alert=True)
        return

    card_idx = int(query.data.split("_")[1])

    # Check if already revealed or flipped
    if game["revealed"][card_idx] or card_idx in game["flipped_indices"]:
        await query.answer("This card is already flipped!", show_alert=False)
        return

    await query.answer()
    game["flipped_indices"].append(card_idx)

    # First card flipped
    if len(game["flipped_indices"]) == 1:
        await query.edit_message_text(
            get_game_status_text(chat_id, game),
            reply_markup=render_board(game),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Second card flipped: Evaluate Match
    if len(game["flipped_indices"]) == 2:
        idx1, idx2 = game["flipped_indices"]
        match = game["board"][idx1] == game["board"][idx2]

        if match:
            # Match found
            game["revealed"][idx1] = True
            game["revealed"][idx2] = True
            game["scores"][current_player_id] += 1
            game["flipped_indices"] = []

            await query.edit_message_text(
                get_game_status_text(chat_id, game),
                reply_markup=render_board(game),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        else:
            # Mismatch: Set lock BEFORE editing message so rapid taps get blocked immediately
            game["lock"] = True
            try:
                await query.edit_message_text(
                    get_game_status_text(chat_id, game),
                    reply_markup=render_board(game),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )

                # Exactly 1.0 second delay
                await asyncio.sleep(1.0)

                game["flipped_indices"] = []
                if len(game["players"]) > 1:
                    game["current_turn_idx"] = 1 - game["current_turn_idx"]

                await query.edit_message_text(
                    get_game_status_text(chat_id, game),
                    reply_markup=render_board(game),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
            finally:
                game["lock"] = False


async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("match", "Start Memory Match with grid selection"),
        BotCommand("stats", "View chat leaderboard & head-to-head wins"),
        BotCommand("stop", "Stop active game"),
        BotCommand("help", "Show game rules"),
    ])


request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(MEMORY_BOT_TOKEN).request(request).post_init(set_commands).build()

# Slash Commands
app.add_handler(CommandHandler(["match", "memory", "game"], start_game_menu))
app.add_handler(CommandHandler("ping", ping_command))
app.add_handler(CommandHandler("helpad", helpad_command))
app.add_handler(CommandHandler(["stop", "end", "cancel"], stop_game_command))
app.add_handler(CommandHandler(["stats", "score", "scores", "leaderboard", "ranks"], stats_command))
app.add_handler(CommandHandler("help", help_command))

# Dot Prefix Handler
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dot_prefix))

# Callbacks: Grid selection & Flips
app.add_handler(CallbackQueryHandler(handle_grid_selection, pattern=r"^grid_"))
app.add_handler(CallbackQueryHandler(handle_flip,
                                     pattern=r"^(flip_\d+|mem_replay_.+|mem_change_grid|mem_stop_game|mem_view_stats|mem_back_to_game)$"))