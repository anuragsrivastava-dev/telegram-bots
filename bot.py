# Bot that executes python code directly from telegram chat and links to Python Console WebApp

import asyncio
import json
from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    WebAppInfo,
    MenuButtonWebApp,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
    filters,
)

from config import PYBOT_TOKEN
from runner import PythonSession

WEBAPP_URL = "https://anu69-web.github.io/python-console/"
TELEGRAM_WEBAPP_LINK = "https://t.me/py_runbot/console"
chat_sessions: dict[tuple[int, int], dict] = {}


def get_console_url(chat_id: int = 0) -> str:
    if chat_id:
        return f"{WEBAPP_URL}?chat_id={chat_id}&token={PYBOT_TOKEN}"
    return WEBAPP_URL


def get_console_keyboard(chat_id: int = 0, is_group: bool = False):
    url = get_console_url(chat_id)
    if is_group:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🐍 Launch Python Console", url=TELEGRAM_WEBAPP_LINK)],
            [InlineKeyboardButton("🔗 Share App", url=f"https://t.me/share/url?url={TELEGRAM_WEBAPP_LINK}&text=Try%20Python%20Console%20on%20Telegram!")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🐍 Launch Python Console", web_app=WebAppInfo(url=url))],
            [InlineKeyboardButton("🔗 Share App (t.me/py_runbot/console)", url=f"https://t.me/share/url?url={TELEGRAM_WEBAPP_LINK}&text=Try%20Python%20Console%20on%20Telegram!")]
        ])


def get_reply_keyboard(chat_id: int = 0):
    url = get_console_url(chat_id)
    return ReplyKeyboardMarkup(
        [[KeyboardButton("💻 Open Python Console", web_app=WebAppInfo(url=url))]],
        resize_keyboard=True
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = chat.id if chat else 0
    is_group = bool(chat and chat.type in ["group", "supergroup", "channel"])
    
    help_text = (
        "🐍 *Python Code Runner & Console:*\n\n"
        "• `/console` or `.console` — Open interactive Web IDE with autocomplete\n"
        "• `/run <code>` or `.run` — Execute multi-line Python code in chat\n"
        "• `/stop` or `.stop` — Force stop the current executing script\n"
        "• `/help` — Show this guide\n\n"
        "📱 *Direct Web App:* [t.me/py_runbot/console](https://t.me/py_runbot/console)\n\n"
        "*Quick Run Example:*\n"
        "```python\n"
        "/run\n"
        "name = input('Your name: ')\n"
        "print(f'Hello {name}!')\n"
        "```"
    )
    await update.message.reply_text(
        help_text,
        reply_markup=get_console_keyboard(chat_id, is_group),
        parse_mode="Markdown"
    )


async def console_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = chat.id if chat else 0
    is_group = bool(chat and chat.type in ["group", "supergroup", "channel"])
    
    await update.message.reply_text(
        "⚡ *Python Console (Web IDE)*\n\n"
        "Click below to launch the full-featured interactive compiler with real-time output, auto-indentation, and autocompletion:\n\n"
        "🔗 *Direct Link:* [t.me/py_runbot/console](https://t.me/py_runbot/console)",
        reply_markup=get_console_keyboard(chat_id, is_group),
        parse_mode="Markdown"
    )


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = [
        InlineQueryResultArticle(
            id="python_console_app",
            title="🐍 Open Python Console",
            description="Launch interactive in-browser Python IDE with auto-complete & runner",
            input_message_content=InputTextMessageContent(
                "⚡ *Python Console (Web IDE)*\n\n"
                "Interactive Python compiler with instant execution and auto-complete.\n\n"
                "📱 *Direct Link:* [t.me/py_runbot/console](https://t.me/py_runbot/console)",
                parse_mode="Markdown"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🐍 Launch Python Console", url=TELEGRAM_WEBAPP_LINK)]
            ])
        )
    ]
    await update.inline_query.answer(results, cache_time=1)


async def monitor(session_key: tuple[int, int], chat_id: int, application: Application):
    state = chat_sessions.get(session_key)
    if not state or not state["session"]:
        return

    session = state["session"]

    while session and session.running():
        if session.timed_out():
            session.stop()
            chat_sessions.pop(session_key, None)
            await application.bot.send_message(
                chat_id=chat_id,
                text="⏰ Program timed out after 10 seconds."
            )
            return

        out = session.get_stdout()
        if out and "__INPUT__" in out:
            prompt = out.split("__INPUT__")[1].split("\n")[0]
            session.clear_accumulated()
            state["waiting_for_input"] = True
            await application.bot.send_message(
                chat_id=chat_id,
                text=prompt if prompt.strip() else "Input:"
            )
            return

        await asyncio.sleep(0.05)

    await asyncio.sleep(0.1)

    output = session.get_stdout()
    error = session.get_stderr().strip()

    if error:
        err_lines = [l for l in error.splitlines() if "tempfile" not in l and "INPUT_PATCH" not in l]
        clean_err = "\n".join(err_lines[-10:]).strip()
        if len(clean_err) > 3500:
            clean_err = clean_err[-3500:]
        await application.bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error:*\n\n```{clean_err}```",
            parse_mode="Markdown"
        )
    elif output.strip():
        out_text = output.strip()
        if len(out_text) > 3800:
            out_text = out_text[:3800] + "\n\n... [Output truncated: reached Telegram length limit]"
        await application.bot.send_message(
            chat_id=chat_id,
            text=f"```\n{out_text}\n```",
            parse_mode="Markdown"
        )
    else:
        await application.bot.send_message(
            chat_id=chat_id,
            text="✅ Program finished with no output."
        )

    session.stop()
    chat_sessions.pop(session_key, None)


async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = chat.id if chat else 0
    user_id = update.effective_user.id if update.effective_user else 0
    session_key = (chat_id, user_id)
    is_group = bool(chat and chat.type in ["group", "supergroup", "channel"])

    message = update.message.text
    lines = message.splitlines()
    code = "\n".join(lines[1:]).strip()

    if not code:
        await update.message.reply_text(
            "Usage:\n\n/run\nprint('Hello World')",
            reply_markup=get_console_keyboard(chat_id, is_group)
        )
        return

    if session_key in chat_sessions and chat_sessions[session_key]["session"]:
        chat_sessions[session_key]["session"].stop()

    session = PythonSession()
    session.start(code)
    chat_sessions[session_key] = {"session": session, "waiting_for_input": False}

    asyncio.create_task(monitor(session_key, chat_id, context.application))


async def receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else 0
    session_key = (chat_id, user_id)
    state = chat_sessions.get(session_key)

    if not state or not state["waiting_for_input"] or not state["session"]:
        # Handle dot prefixes if not actively waiting for input
        text = update.message.text.strip().lower()
        if text.startswith(".run"):
            await run(update, context)
        elif text.startswith(".stop"):
            await stop(update, context)
        elif text.startswith((".console", ".code", ".web")):
            await console_command(update, context)
        elif text.startswith((".help", ".start")):
            await help_command(update, context)
        return

    state["waiting_for_input"] = False
    state["session"].send_input(update.message.text)
    asyncio.create_task(monitor(session_key, chat_id, context.application))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else 0
    session_key = (chat_id, user_id)
    state = chat_sessions.pop(session_key, None)

    if not state or not state["session"]:
        await update.message.reply_text("❌ No program is currently running.")
        return

    state["session"].stop()
    await update.message.reply_text("🛑 Program stopped.")


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.web_app_data:
        return

    raw_data = update.message.web_app_data.data
    try:
        payload = json.loads(raw_data)
        code = payload.get("code", "")
        if code:
            await update.message.reply_text(
                f"📥 *Received code from Python Console:*\n\n```python\n{code}\n```\n"
                "To run this code in chat, send `/run` followed by the code.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"📥 Received data: `{raw_data}`", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(f"📥 Received from WebApp:\n```\n{raw_data}\n```", parse_mode="Markdown")


async def set_commands(application: Application):
    await application.bot.set_my_commands([
        BotCommand("console", "Open interactive Python Console"),
        BotCommand("run", "Run Python script in chat"),
        BotCommand("stop", "Stop executing code"),
        BotCommand("help", "Show code runner help"),
    ])
    try:
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="💻 Console",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
    except Exception as e:
        print(f"Notice: set_chat_menu_button info: {e}")


from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(PYBOT_TOKEN).request(request).post_init(set_commands).build()

app.add_handler(CommandHandler(["start", "help"], help_command))
app.add_handler(CommandHandler(["console", "code", "web"], console_command))
app.add_handler(CommandHandler("run", run))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(InlineQueryHandler(inline_query_handler))
app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive))