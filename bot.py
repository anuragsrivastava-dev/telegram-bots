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
chat_sessions: dict[int, dict] = {}


def get_console_url(chat_id: int = 0) -> str:
    if chat_id:
        return f"{WEBAPP_URL}?chat_id={chat_id}&token={PYBOT_TOKEN}"
    return WEBAPP_URL


def get_console_keyboard(chat_id: int = 0):
    url = get_console_url(chat_id)
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
    chat_id = update.effective_chat.id if update.effective_chat else 0
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
        reply_markup=get_console_keyboard(chat_id),
        parse_mode="Markdown"
    )


async def console_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else 0
    await update.message.reply_text(
        "⚡ *Python Console (Web IDE)*\n\n"
        "Click below to launch the full-featured interactive compiler with real-time output, auto-indentation, and autocompletion:\n\n"
        "🔗 *Direct Link:* [t.me/py_runbot/console](https://t.me/py_runbot/console)",
        reply_markup=get_console_keyboard(chat_id),
        parse_mode="Markdown"
    )


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.inline_query.from_user.id if update.inline_query and update.inline_query.from_user else 0
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
            reply_markup=get_console_keyboard(user_id)
        )
    ]
    await update.inline_query.answer(results, cache_time=1)


async def monitor(chat_id: int, application: Application):
    state = chat_sessions.get(chat_id)
    if not state or not state["session"]:
        return

    session = state["session"]

    while session and session.running():
        if session.timed_out():
            session.stop()
            chat_sessions.pop(chat_id, None)
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
        last_line = error.splitlines()[-1]
        await application.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Error\n\n```{last_line}```",
            parse_mode="Markdown"
        )
    elif output.strip():
        await application.bot.send_message(
            chat_id=chat_id,
            text=f"```\n{output.strip()}\n```",
            parse_mode="Markdown"
        )
    else:
        await application.bot.send_message(
            chat_id=chat_id,
            text="✅ Program finished with no output."
        )

    session.stop()
    chat_sessions.pop(chat_id, None)


async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message.text
    lines = message.splitlines()
    code = "\n".join(lines[1:]).strip()

    if not code:
        await update.message.reply_text(
            "Usage:\n\n/run\nprint('Hello World')",
            reply_markup=get_console_keyboard(chat_id)
        )
        return

    if chat_id in chat_sessions and chat_sessions[chat_id]["session"]:
        chat_sessions[chat_id]["session"].stop()

    session = PythonSession()
    session.start(code)
    chat_sessions[chat_id] = {"session": session, "waiting_for_input": False}

    asyncio.create_task(monitor(chat_id, context.application))


async def receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = chat_sessions.get(chat_id)

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
    asyncio.create_task(monitor(chat_id, context.application))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = chat_sessions.pop(chat_id, None)

    if not state or not state["session"]:
        await update.message.reply_text("❌ No program is running.")
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