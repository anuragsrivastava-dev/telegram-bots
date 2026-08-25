import logging
import os
import time
import sqlite3
from config import GAME_BOT_TOKEN, ADMIN_USER_ID

from telegram import (
    Update,
    BotCommand,
    InlineQueryResultGame,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonCommands,
)
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "game_scores.db")

# =============================================================================
# Database Layer: Global Persistent Game Scores
# =============================================================================
def get_db():
    return sqlite3.connect(DB_PATH)


def init_game_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                game_key TEXT NOT NULL,
                high_score INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, chat_id, game_key)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                game_key TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, game_key)
            )
        """)
        conn.commit()


init_game_db()


def save_or_update_score(user_id: int, chat_id: int, user_name: str, game_key: str, score: int):
    if not user_id:
        return
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO game_scores (user_id, chat_id, user_name, game_key, high_score, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, chat_id, game_key) DO UPDATE SET
                high_score = MAX(game_scores.high_score, excluded.high_score),
                user_name = excluded.user_name,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, chat_id, user_name, game_key, max(0, score)))
        conn.commit()


def record_game_message(chat_id: int, game_key: str, message_id: int):
    if not chat_id or not message_id:
        return
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO game_messages (chat_id, game_key, message_id, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id, game_key) DO UPDATE SET
                message_id = excluded.message_id,
                updated_at = CURRENT_TIMESTAMP
        """, (chat_id, game_key, message_id))
        conn.commit()


# =============================================================================
# Game Definitions
# =============================================================================
GAMES = {
    "chess": {
        "url": "https://anu69-web.github.io/telegram-games/chess/",
        "title": "Chess Duel",
        "emoji": "♟️",
        "type": "2P",
        "unit": "wins",
    },
    "snakes": {
        "url": "https://anu69-web.github.io/telegram-games/snakes/",
        "title": "Snakes Clash",
        "emoji": "🐍",
        "type": "2P",
        "unit": "wins",
    },
    "uno": {
        "url": "https://anu69-web.github.io/telegram-games/uno/",
        "title": "UNO Duel",
        "emoji": "🃏",
        "type": "2P",
        "unit": "wins",
    },
    "paddle": {
        "url": "https://anu69-web.github.io/telegram-games/paddle/",
        "title": "Paddle Clash",
        "emoji": "🏓",
        "type": "2P",
        "unit": "wins",
    },
    "frog": {
        "url": "https://anu69-web.github.io/telegram-games/frog-fight/",
        "title": "Frog Fight",
        "emoji": "🐸",
        "type": "2P",
        "unit": "wins",
    },
    "flappy": {
        "url": "https://anu69-web.github.io/telegram-games/flappy-bird/",
        "title": "Flappy Bird",
        "emoji": "🐦",
        "type": "Solo",
        "unit": "pts",
    },
    "tower": {
        "url": "https://anu69-web.github.io/telegram-games/tower-builder/",
        "title": "Tower Builder",
        "emoji": "🏗️",
        "type": "Solo",
        "unit": "flr",
    },
    "helix": {
        "url": "https://anu69-web.github.io/telegram-games/helix-jump/",
        "title": "Helix Jump",
        "emoji": "🌀",
        "type": "Solo",
        "unit": "pts",
    },
    "heart_catcher": {
        "url": "https://anu69-web.github.io/telegram-games/heart-catcher/",
        "title": "Heart Catcher",
        "emoji": "💖",
        "type": "Solo",
        "unit": "pts",
    },
}

GAME_ORDER = ["chess", "snakes", "uno", "paddle", "frog", "flappy", "tower", "helix", "heart_catcher"]


def get_games_menu_keyboard() -> InlineKeyboardMarkup:
    """Build interactive inline buttons for all games with multiplayer games on top."""
    return InlineKeyboardMarkup([
        # --- MULTIPLAYER 2-PLAYER GAMES (TOP) ---
        [
            InlineKeyboardButton("♟️ Chess Duel (2P)", callback_data="play_game_chess"),
            InlineKeyboardButton("🐍 Snakes Clash (2P)", callback_data="play_game_snakes"),
        ],
        [
            InlineKeyboardButton("🃏 UNO Duel (2P)", callback_data="play_game_uno"),
            InlineKeyboardButton("🏓 Paddle Clash (2P)", callback_data="play_game_paddle"),
        ],
        [
            InlineKeyboardButton("🐸 Frog Fight (2P)", callback_data="play_game_frog"),
        ],
        # --- SOLO ARCADE GAMES ---
        [
            InlineKeyboardButton("🐦 Flappy Bird", callback_data="play_game_flappy"),
            InlineKeyboardButton("🏗️ Tower Builder", callback_data="play_game_tower"),
        ],
        [
            InlineKeyboardButton("🌀 Helix Jump", callback_data="play_game_helix"),
            InlineKeyboardButton("💖 Heart Catcher", callback_data="play_game_heart_catcher"),
        ],
        # --- LEADERBOARD & SHARE ---
        [
            InlineKeyboardButton("🏆 View Leaderboard", callback_data="view_leaderboard"),
            InlineKeyboardButton("✨ Share in Chat", switch_inline_query=""),
        ],
    ])


async def games_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send an interactive button list of all games starting with multiplayer games on top."""
    text = (
        "🎮 *Telegram Gaming Hub — Game Directory*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Select a game below to launch it instantly in this chat:\n\n"
        "👥 *Multiplayer 2-Player Duels (Top):*\n"
        "• ♟️ *Chess Duel* — Classic Staunton SVG P2P Chess\n"
        "• 🐍 *Snakes Clash* — 100-Tile Animated Board Game\n"
        "• 🃏 *UNO Duel* — 2-Player Card Showdown (+2/+4 Stacking)\n"
        "• 🏓 *Paddle Clash* — 60 FPS Real-time Pong Duel\n"
        "• 🐸 *Frog Fight* — Lily Pad Arena Duel\n\n"
        "🕹️ *Solo Arcade Games:*\n"
        "• 🐦 *Flappy Bird* — Retro Obstacle Runner\n"
        "• 🏗️ *Tower Builder* — Precision Block Stacker\n"
        "• 🌀 *Helix Jump* — 3D Spiral Bouncing Drop\n"
        "• 💖 *Heart Catcher* — Reflex Catcher\n\n"
        "💡 *Tip:* Type `@meoww_gamebot` in any chat to share inline!"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text,
            reply_markup=get_games_menu_keyboard(),
            parse_mode="Markdown",
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_games_menu_keyboard(),
            parse_mode="Markdown",
        )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    latency = int((time.time() - start_time) * 1000)
    await msg.edit_text(
        f"🏓 *Pong!* `{latency}ms`\n🎮 *Gaming Hub Bot* is Online & Ready to Play!",
        parse_mode="Markdown"
    )


async def helpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorized to use admin commands.")
        return
    admin_help = (
        "👑 *Gaming Hub Bot Admin Control Panel:*\n\n"
        "• `/ping` — Check bot latency & online status\n"
        "• `/games` — Interactive games list (Multiplayer on top)\n"
        "• `/chess`, `/snakes`, `/uno`, `/paddle`, `/frog` — Launch 2P games\n"
        "• `/flappy`, `/tower`, `/helix`, `/catch` — Launch Solo Arcade games\n"
        "• `/scores` — View leaderboard comparison chart\n"
        "• `/helpad` — Show this admin help menu"
    )
    await update.message.reply_text(admin_help, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🎮 *Game Bot Hub:*\n\n"
        "• `/games` or `.games` — Open Interactive Games Menu (Multiplayer on top) 🕹️\n\n"
        "👥 *Multiplayer 2-Player Games:*\n"
        "• `/chess` or `.chess` — Chess Master Duel (2P)\n"
        "• `/snakes` or `.snakes` — Snakes & Ladders Duel (100 Tiles)\n"
        "• `/uno` or `.uno` — UNO Duel (2P)\n"
        "• `/paddle` or `.paddle` — Paddle Clash (2P)\n"
        "• `/frog` or `.frog` — Frog Fight Lily Pad Duel (2P)\n\n"
        "🕹️ *Solo Arcade Games:*\n"
        "• `/flappy` or `.flappy` — Flappy Bird Odyssey\n"
        "• `/tower` or `.tower` — Tower Builder Deluxe\n"
        "• `/helix` or `.helix` — Helix Jump 3D\n"
        "• `/catch` or `.catch` — Solo Heart Catcher\n\n"
        "📊 *Leaderboard & Help:*\n"
        "• `/scores` or `.scores` — View all-games scoreboard chart\n"
        "• `/help` — Show this guide\n\n"
        "💡 *Inline Game:* Type `@meoww_gamebot` in any chat to share!"
    )
    await update.message.reply_text(
        help_text,
        reply_markup=get_games_menu_keyboard(),
        parse_mode="Markdown",
    )


# =============================================================================
# Game Launch Handlers
# =============================================================================
async def play_chess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="chess")
    if msg:
        record_game_message(chat_id, "chess", msg.message_id)


async def play_snakes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="snakes")
    if msg:
        record_game_message(chat_id, "snakes", msg.message_id)


async def play_uno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="uno")
    if msg:
        record_game_message(chat_id, "uno", msg.message_id)


async def play_paddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="paddle")
    if msg:
        record_game_message(chat_id, "paddle", msg.message_id)


async def play_catcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="heart_catcher")
    if msg:
        record_game_message(chat_id, "heart_catcher", msg.message_id)


async def play_flappy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="flappy")
    if msg:
        record_game_message(chat_id, "flappy", msg.message_id)


async def play_tower(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="tower")
    if msg:
        record_game_message(chat_id, "tower", msg.message_id)


async def play_helix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="helix")
    if msg:
        record_game_message(chat_id, "helix", msg.message_id)


async def play_frog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(chat_id=chat_id, game_short_name="frog")
    if msg:
        record_game_message(chat_id, "frog", msg.message_id)


async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Handle custom interactive menu button clicks
    if query.data:
        if query.data.startswith("play_game_"):
            game_key = query.data.replace("play_game_", "").strip()
            if game_key in GAMES:
                chat_id = update.effective_chat.id
                await query.answer(f"Launching {GAMES[game_key]['title']}...")
                msg = await context.bot.send_game(chat_id=chat_id, game_short_name=game_key)
                if msg:
                    record_game_message(chat_id, game_key, msg.message_id)
                return
        elif query.data == "view_leaderboard":
            await query.answer("Fetching leaderboard...")
            await leaderboard_command(update, context)
            return

    game_key = query.game_short_name or query.data

    if game_key not in GAMES:
        return

    user_id = query.from_user.id
    user_name = query.from_user.first_name or "Player"
    chat_id = query.message.chat_id if query.message else 0
    msg_id = query.message.message_id if query.message else ""
    inline_id = query.inline_message_id or ""

    if chat_id and msg_id:
        record_game_message(chat_id, game_key, msg_id)

    # Register user in database
    if chat_id:
        save_or_update_score(user_id, chat_id, user_name, game_key, 0)

    base_url = GAMES[game_key]["url"]
    target_url = (
        f"{base_url}?user_id={user_id}"
        f"&chat_id={chat_id}"
        f"&msg_id={msg_id}"
        f"&inline_id={inline_id}"
        f"&token={GAME_BOT_TOKEN}"
    )

    await query.answer(url=target_url)


async def inline_game_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = [
        # Multiplayer 2-Player Games (at the top, starting with Chess)
        InlineQueryResultGame(id="1", game_short_name="chess"),
        InlineQueryResultGame(id="2", game_short_name="snakes"),
        InlineQueryResultGame(id="3", game_short_name="uno"),
        InlineQueryResultGame(id="4", game_short_name="paddle"),
        InlineQueryResultGame(id="5", game_short_name="frog"),
        # Solo Arcade Games
        InlineQueryResultGame(id="6", game_short_name="flappy"),
        InlineQueryResultGame(id="7", game_short_name="tower"),
        InlineQueryResultGame(id="8", game_short_name="helix"),
        InlineQueryResultGame(id="9", game_short_name="heart_catcher"),
    ]
    await update.inline_query.answer(results, cache_time=0)


# =============================================================================
# Leaderboard Chart Builder
# =============================================================================
def format_cell(text: str, width: int, align: str = "left") -> str:
    s = str(text)
    if len(s) > width:
        s = s[:width - 1] + "…"
    if align == "right":
        return s.rjust(width)
    elif align == "center":
        return s.center(width)
    return s.ljust(width)


def build_leaderboard_chart(scores_by_user_game: dict, user_names: dict, current_user_id: int) -> str:
    player_ids = list(scores_by_user_game.keys())

    # --- 2-PLAYER HEAD-TO-HEAD DUEL COMPARISON CHART ---
    if len(player_ids) == 2:
        p1_id, p2_id = player_ids[0], player_ids[1]
        p1_name = user_names.get(p1_id, "Player 1")[:8]
        p2_name = user_names.get(p2_id, "Player 2")[:8]

        col1_w = 17
        col2_w = 8
        col3_w = 8

        lines = [
            "🏆 *ALL-GAMES ARCADE LEADERBOARD* 🏆",
            "```",
            f"{format_cell('Game Title', col1_w)}│{format_cell(p1_name, col2_w, 'center')}│{format_cell(p2_name, col3_w, 'center')}",
            f"{'─' * col1_w}┼{'─' * col2_w}┼{'─' * col3_w}"
        ]

        p1_total = 0
        p2_total = 0

        for key in GAME_ORDER:
            info = GAMES[key]
            s1 = scores_by_user_game[p1_id].get(key, 0)
            s2 = scores_by_user_game[p2_id].get(key, 0)
            p1_total += s1
            p2_total += s2

            # Badges
            tag1 = " 👑" if (s1 > s2 and s1 > 0) else (" ⭐" if (s1 > 0 and s1 == s2) else "")
            tag2 = " 👑" if (s2 > s1 and s2 > 0) else (" ⭐" if (s2 > 0 and s1 == s2) else "")

            c1_str = f"{s1}{tag1}" if s1 > 0 else "-"
            c2_str = f"{s2}{tag2}" if s2 > 0 else "-"

            name_str = f"{info['emoji']} {info['title']}"
            lines.append(f"{format_cell(name_str, col1_w)}│{format_cell(c1_str, col2_w, 'center')}│{format_cell(c2_str, col3_w, 'center')}")

        lines.append(f"{'─' * col1_w}┼{'─' * col2_w}┼{'─' * col3_w}")
        t1_badge = " 👑" if p1_total > p2_total else ""
        t2_badge = " 👑" if p2_total > p1_total else ""
        lines.append(f"{format_cell('🎖️ TOTAL WINS/PTS', col1_w)}│{format_cell(f'{p1_total}{t1_badge}', col2_w, 'center')}│{format_cell(f'{p2_total}{t2_badge}', col3_w, 'center')}")
        lines.append("```")

        if p1_total > p2_total:
            diff = p1_total - p2_total
            lines.append(f"👑 *Overall Leader:* *{p1_name}* (`+{diff} pts ahead`)")
        elif p2_total > p1_total:
            diff = p2_total - p1_total
            lines.append(f"👑 *Overall Leader:* *{p2_name}* (`+{diff} pts ahead`)")
        else:
            lines.append("🤝 *Tied Match:* Both players are perfectly even!")

        return "\n".join(lines)

    # --- SINGLE PLAYER OR MULTI-PLAYER STATS CHART ---
    target_uid = current_user_id if current_user_id in scores_by_user_game else (player_ids[0] if player_ids else current_user_id)
    target_name = user_names.get(target_uid, "You")
    user_scores = scores_by_user_game.get(target_uid, {})

    col1_w = 17
    col2_w = 6
    col3_w = 11

    lines = [
        f"🏆 *ARCADE STATS CHART* 🏆",
        f"👤 *Player:* `{target_name}` (Global High Scores)\n",
        "```",
        f"{format_cell('Game Title', col1_w)}│{format_cell('Mode', col2_w, 'center')}│{format_cell('High Score', col3_w, 'center')}",
        f"{'─' * col1_w}┼{'─' * col2_w}┼{'─' * col3_w}"
    ]

    total_score = 0
    for key in GAME_ORDER:
        info = GAMES[key]
        s = user_scores.get(key, 0)
        total_score += s

        score_text = f"{s} {info['unit']}" if s > 0 else "-"
        name_str = f"{info['emoji']} {info['title']}"
        lines.append(f"{format_cell(name_str, col1_w)}│{format_cell(info['type'], col2_w, 'center')}│{format_cell(score_text, col3_w, 'right')}")

    lines.append(f"{'─' * col1_w}┼{'─' * col2_w}┼{'─' * col3_w}")
    lines.append(f"{format_cell('🎖️ COMBINED TOTAL', col1_w)}│{format_cell('ALL', col2_w, 'center')}│{format_cell(f'{total_score} pts', col3_w, 'right')}")
    lines.append("```")
    lines.append("✨ _Scores update automatically whenever you finish a game!_")

    return "\n".join(lines)


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    user_name = user.first_name or "Player"

    # 1. Sync latest high scores from Telegram API for all tracked game messages
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT game_key, message_id FROM game_messages WHERE chat_id = ?", (chat_id,))
        tracked_msgs = cur.fetchall()

    for g_key, m_id in tracked_msgs:
        try:
            tg_scores = await context.bot.get_game_high_scores(
                user_id=user_id,
                chat_id=chat_id,
                message_id=m_id,
            )
            if tg_scores:
                for s in tg_scores:
                    p_name = s.user.first_name or "Player"
                    save_or_update_score(s.user.id, chat_id, p_name, g_key, s.score)
        except Exception:
            pass

    # 2. Fetch recorded scores for this chat (or user global fallback)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, user_name, game_key, high_score
            FROM game_scores
            WHERE chat_id = ?
        """, (chat_id,))
        chat_rows = cur.fetchall()

    # If no scores exist for chat yet, check global user scores
    if not chat_rows:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, user_name, game_key, MAX(high_score)
                FROM game_scores
                WHERE user_id = ?
                GROUP BY game_key
            """, (user_id,))
            chat_rows = [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]

    scores_by_user_game = {}
    user_names = {}

    for uid, name, gkey, hscore in chat_rows:
        if uid not in scores_by_user_game:
            scores_by_user_game[uid] = {}
        scores_by_user_game[uid][gkey] = hscore
        user_names[uid] = name

    # If still empty, initialize current user with 0s
    if not scores_by_user_game:
        scores_by_user_game[user_id] = {k: 0 for k in GAME_ORDER}
        user_names[user_id] = user_name

    chart_msg = build_leaderboard_chart(scores_by_user_game, user_names, user_id)
    if update.message:
        await update.message.reply_text(chart_msg, parse_mode="Markdown")
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(chart_msg, parse_mode="Markdown")


async def handle_dot_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip().lower()
    if text.startswith(".ping"):
        await ping_command(update, context)
    elif text.startswith(".helpad"):
        await helpad_command(update, context)
    elif text.startswith((".games", ".game", ".play", ".menu")):
        await games_menu_command(update, context)
    elif text.startswith((".chess", ".checkmate")):
        await play_chess(update, context)
    elif text.startswith((".snakes", ".snake", ".ladder", ".sl")):
        await play_snakes(update, context)
    elif text.startswith((".uno", ".card")):
        await play_uno(update, context)
    elif text.startswith((".paddle", ".duel")):
        await play_paddle(update, context)
    elif text.startswith((".frog", ".fight", ".lily")):
        await play_frog(update, context)
    elif text.startswith((".flappy", ".bird", ".fly")):
        await play_flappy(update, context)
    elif text.startswith((".tower", ".stack", ".build")):
        await play_tower(update, context)
    elif text.startswith((".helix", ".jump", ".drop")):
        await play_helix(update, context)
    elif text.startswith((".catch", ".heart")):
        await play_catcher(update, context)
    elif text.startswith((".scores", ".top", ".board", ".leaderboard")):
        await leaderboard_command(update, context)
    elif text.startswith((".help", ".start")):
        await help_command(update, context)


async def set_commands(application):
    commands = [
        # Main Interactive Directory
        BotCommand("games", "Open Interactive Games Menu (Multiplayer on top) 🎮"),
        # Multiplayer 2-Player Games (Top)
        BotCommand("chess", "Play Chess Master Duel (2P)"),
        BotCommand("snakes", "Play Snakes & Ladders Clash (2P)"),
        BotCommand("uno", "Play UNO Duel (2P)"),
        BotCommand("paddle", "Play Paddle Clash (2P)"),
        BotCommand("frog", "Play Frog Fight Lily Pad Clash (2P)"),
        # Solo Arcade Games
        BotCommand("flappy", "Play Flappy Bird Odyssey (Solo Arcade)"),
        BotCommand("tower", "Play Tower Builder Deluxe (Solo Stacker)"),
        BotCommand("helix", "Play Helix Jump (3D Ball Arcade)"),
        BotCommand("catch", "Play Solo Heart Catcher"),
        # Leaderboard & Help
        BotCommand("scores", "View All-Games Leaderboard Chart"),
        BotCommand("help", "Show game directory & help"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        print("[OK] GameBot commands & Menu Button registered successfully!")
    except Exception as e:
        print(f"Notice setting commands in GameBot: {e}")


request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(GAME_BOT_TOKEN).request(request).post_init(set_commands).build()

app.add_handler(CommandHandler(["start", "help"], help_command))
app.add_handler(CommandHandler(["games", "game", "menu", "play"], games_menu_command))
app.add_handler(CommandHandler("ping", ping_command))
app.add_handler(CommandHandler("helpad", helpad_command))
app.add_handler(CommandHandler(["chess"], play_chess))
app.add_handler(CommandHandler(["snakes", "snake", "ladder"], play_snakes))
app.add_handler(CommandHandler(["uno", "cards"], play_uno))
app.add_handler(CommandHandler(["paddle", "duel"], play_paddle))
app.add_handler(CommandHandler(["catch", "heart"], play_catcher))
app.add_handler(CommandHandler(["flappy", "bird", "fly"], play_flappy))
app.add_handler(CommandHandler(["tower", "stack", "build"], play_tower))
app.add_handler(CommandHandler(["helix", "jump", "drop"], play_helix))
app.add_handler(CommandHandler(["frog", "fight", "lily"], play_frog))
app.add_handler(CommandHandler(["scores", "top", "leaderboard"], leaderboard_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dot_prefix))
app.add_handler(CallbackQueryHandler(game_callback))
app.add_handler(InlineQueryHandler(inline_game_query))