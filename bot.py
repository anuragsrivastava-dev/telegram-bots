import asyncio
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import PYBOT_TOKEN
from runner import PythonSession

chat_sessions: dict[int, dict] = {}


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🐍 *Python Code Runner Help:*\n\n"
        "• `/run <code>` or `.run` — Execute multi-line Python code safely\n"
        "• `/stop` or `.stop` — Force stop the current executing script\n"
        "• `/help` — Show this guide\n\n"
        "*Example:*\n"
        "```python\n"
        "/run\n"
        "name = input('Your name: ')\n"
        "print(f'Hello {name}!')\n"
        "```"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


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
        await update.message.reply_text("Usage:\n\n/run\nprint('Hello World')")
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


async def set_commands(application: Application):
    await application.bot.set_my_commands([
        BotCommand("run", "Run Python script"),
        BotCommand("stop", "Stop executing code"),
        BotCommand("help", "Show code runner help"),
    ])


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
app.add_handler(CommandHandler("run", run))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive))