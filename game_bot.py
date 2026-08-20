import logging
from config import GAME_BOT_TOKEN

from telegram import (
    Update,
    BotCommand,
    InlineQueryResultGame,
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

GAMES = {
    "chess": {
        "url": "https://anu69-web.github.io/telegram-games/chess/",
        "title": "Couple Chess Duel",
    },
    "snakes": {
        "url": "https://anu69-web.github.io/telegram-games/snakes/",
        "title": "Snakes & Ladders Clash",
    },
    "uno": {
        "url": "https://anu69-web.github.io/telegram-games/uno/",
        "title": "Couple UNO Duel",
    },
    "paddle": {
        "url": "https://anu69-web.github.io/telegram-games/paddle/",
        "title": "Couple Paddle Clash",
    },
    "heart_catcher": {
        "url": "https://anu69-web.github.io/telegram-games/heart-catcher/",
        "title": "Heart Catcher",
    },
    "flappy": {
        "url": "https://anu69-web.github.io/telegram-games/flappy-bird/",
        "title": "Flappy Bird Odyssey",
    },
    "tower": {
        "url": "https://anu69-web.github.io/telegram-games/tower-builder/",
        "title": "Tower Builder Deluxe",
    },
    "helix": {
        "url": "https://anu69-web.github.io/telegram-games/helix-jump/",
        "title": "Helix Jump",
    },
    "frog": {
        "url": "https://anu69-web.github.io/telegram-games/frog-fight/",
        "title": "Frog Fight",
    },
}


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🎮 *Game Bot Hub:*\n\n"
        "👥 *Multiplayer 2-Player Games:*\n"
        "• `/chess` or `.chess` — Couple Chess Duel (2P)\n"
        "• `/snakes` or `.snakes` — Snakes & Ladders Duel (100 Tiles)\n"
        "• `/uno` or `.uno` — Couple UNO Duel (2P)\n"
        "• `/paddle` or `.paddle` — Couple Paddle Clash (2P)\n"
        "• `/frog` or `.frog` — Frog Fight Lily Pad Duel (2P)\n\n"
        "🕹️ *Solo Arcade Games:*\n"
        "• `/flappy` or `.flappy` — Flappy Bird Odyssey\n"
        "• `/tower` or `.tower` — Tower Builder Deluxe\n"
        "• `/helix` or `.helix` — Helix Jump 3D\n"
        "• `/catch` or `.catch` — Solo Heart Catcher\n\n"
        "📊 *Leaderboard & Help:*\n"
        "• `/scores` or `.scores` — View chat leaderboard\n"
        "• `/help` — Show this guide\n\n"
        "💡 *Inline Game:* Type `@meoww_gamebot` in any chat to share!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


chat_last_game_msg: dict[int, int] = {}


async def play_chess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="chess",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def play_snakes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="snakes",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def play_uno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="uno",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def play_paddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="paddle",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def play_catcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="heart_catcher",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def play_flappy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="flappy",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def play_tower(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="tower",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def play_helix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="helix",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def play_frog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_game(
        chat_id=chat_id,
        game_short_name="frog",
    )
    if msg:
        chat_last_game_msg[chat_id] = msg.message_id


async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    game_key = query.game_short_name or query.data

    if game_key not in GAMES:
        return

    user_id = query.from_user.id
    chat_id = query.message.chat_id if query.message else ""
    msg_id = query.message.message_id if query.message else ""
    inline_id = query.inline_message_id or ""

    if chat_id and msg_id:
        try:
            chat_last_game_msg[int(chat_id)] = int(msg_id)
        except Exception:
            pass

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


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    target_msg_id = None
    if update.message and update.message.reply_to_message:
        target_msg_id = update.message.reply_to_message.message_id
    elif chat_id in chat_last_game_msg:
        target_msg_id = chat_last_game_msg[chat_id]

    if not target_msg_id:
        await update.message.reply_text(
            "🏆 *Game Leaderboard:*\n\nScores are updated directly on each game card in chat!\n\nTo fetch text leaderboard, reply to a game card with `/scores` or launch a game (`/chess`, `/snakes`, `/uno`, `/paddle`, `/frog`, `/flappy`, `/tower`, `/helix`, `/catch`).",
            parse_mode="Markdown"
        )
        return

    try:
        scores = await context.bot.get_game_high_scores(
            user_id=user_id,
            chat_id=chat_id,
            message_id=target_msg_id,
        )
        if not scores:
            await update.message.reply_text("🏆 No match wins logged yet on this game card! Finish a match to set a record.")
            return

        lines = ["🏆 *Game Card Leaderboard:*\n"]
        for score_obj in scores:
            lines.append(f"`#{score_obj.position}` *{score_obj.user.first_name}* — `{score_obj.score}` wins")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("🏆 *Scores are live on the game message card above!*\n\nFinish a match to update the scoreboard.")


async def handle_dot_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip().lower()
    if text.startswith((".chess", ".checkmate")):
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
    elif text.startswith((".scores", ".top", ".board")):
        await leaderboard_command(update, context)
    elif text.startswith((".help", ".start")):
        await help_command(update, context)


async def set_commands(application):
    await application.bot.set_my_commands([
        # Multiplayer 2-Player Games (Top)
        BotCommand("chess", "Play Couple Chess Duel (2P)"),
        BotCommand("snakes", "Play Snakes & Ladders Clash (2P)"),
        BotCommand("uno", "Play Couple UNO Duel (2P)"),
        BotCommand("paddle", "Play Couple Paddle Clash (2P)"),
        BotCommand("frog", "Play Frog Fight Lily Pad Clash (2P)"),
        # Solo Arcade Games
        BotCommand("flappy", "Play Flappy Bird Odyssey (Solo Arcade)"),
        BotCommand("tower", "Play Tower Builder Deluxe (Solo Stacker)"),
        BotCommand("helix", "Play Helix Jump (3D Ball Arcade)"),
        BotCommand("catch", "Play Solo Heart Catcher"),
        BotCommand("scores", "View Leaderboard"),
        BotCommand("help", "Show game help"),
    ])


request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(GAME_BOT_TOKEN).request(request).post_init(set_commands).build()

app.add_handler(CommandHandler(["start", "help"], help_command))
app.add_handler(CommandHandler(["chess"], play_chess))
app.add_handler(CommandHandler(["snakes", "snake", "ladder"], play_snakes))
app.add_handler(CommandHandler(["uno", "cards"], play_uno))
app.add_handler(CommandHandler(["paddle", "duel"], play_paddle))
app.add_handler(CommandHandler(["catch", "heart"], play_catcher))
app.add_handler(CommandHandler(["flappy", "bird", "fly"], play_flappy))
app.add_handler(CommandHandler(["tower", "stack", "build"], play_tower))
app.add_handler(CommandHandler(["helix", "jump", "drop"], play_helix))
app.add_handler(CommandHandler(["frog", "fight", "lily"], play_frog))
app.add_handler(CommandHandler(["scores", "top"], leaderboard_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dot_prefix))
app.add_handler(CallbackQueryHandler(game_callback))
app.add_handler(InlineQueryHandler(inline_game_query))