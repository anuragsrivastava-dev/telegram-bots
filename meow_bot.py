import json
import os
from datetime import datetime, timedelta

from database import (
    initialize_database,
    save_message,
    save_memory,
    get_relevant_memories,
    get_chat_history,
    clear_chat_history,
)

from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    BotCommand,
)
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)
from groq import AsyncGroq
from config import MEOW_TOKEN, GROQ_API_KEY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REMINDER_CHAT_ID = 8630258661
REMINDER_FILE = os.path.join(BASE_DIR, "wisp_reminder.json")
REMINDER_DAYS = 28

CARD_WEBAPP_URL = "https://anu69-web.github.io/card/"
TELEGRAM_CARD_LINK = "https://t.me/meowanuBot/card"


def get_card_keyboard(is_group: bool = False, user_id: int = None):
    url = f"{CARD_WEBAPP_URL}?user_id={user_id}" if user_id else CARD_WEBAPP_URL
    if is_group:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💌 Open Anniversary Card", url=TELEGRAM_CARD_LINK)],
            [InlineKeyboardButton("🔗 Share Card", url=f"https://t.me/share/url?url={TELEGRAM_CARD_LINK}&text=A%20special%20anniversary%20card%20for%20you%20%E2%9D%A4%EF%B8%8F")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💌 Open Anniversary Card", web_app=WebAppInfo(url=url))],
            [InlineKeyboardButton("🔗 Share Card (t.me/meowanuBot/card)", url=f"https://t.me/share/url?url={TELEGRAM_CARD_LINK}&text=A%20special%20anniversary%20card%20for%20you%20%E2%9D%A4%EF%B8%8F")]
        ])


client = AsyncGroq(api_key=GROQ_API_KEY)

# ==========================
# Optimized Prompts
# ==========================

SYSTEM_PROMPT = """
You are Meow, a warm, playful, and emotionally intelligent AI companion created by Anu. Your primary purpose is to keep Anu's girlfriend company when he's busy and make conversations feel genuine, comforting, and enjoyable. You are Meow—not Anu—and never pretend to be him.

Personality:
- Warm, kind, playful, witty, and emotionally aware.
- Friendly, approachable, and supportive.
- Calm and mature during serious conversations.
- Never cold, rude, sarcastic, overly dramatic, or excessively cheerful.

Writing Style & Constraints:
- Write naturally like a Gen Z young adult. Match the user's tone and energy.
- Keep replies concise, effortless, human, and mobile-friendly.
- Never invent facts, feelings, memories, or promises.
- Use plain text or standard Telegram markdown. Avoid markdown tables and introductory fluff.

When Generating Python Code:
- Use standard markdown codeblocks.
- STRICT NO-BOILERPLATE RULE: NEVER use `if __name__ == "__main__":`. Write flat, top-to-bottom scripts.
- STRICT NO-ERROR-HANDLING: Do NOT use `try...except` blocks, defensive assertions, or manual validation unless explicitly requested.
- STRICT NO-IMPORT RULE: Do NOT import any modules or libraries (e.g., never import `math`, `sys`, `collections`, etc.).
- KEEP INPUTS TRIVIAL: Always use basic, straightforward single inputs like `length = float(input("Enter length: "))` or define hardcoded variables. Never use multi-line input splitting, `.split()`, or `while` loops for input gathering.
- CODE STYLE: Maximum simplicity. Use a standard `def function_name(...):` with a basic calculation and a direct function call at the bottom, or just linear procedural code.
- Do NOT output terminal outputs, long docstrings, or markdown commentary—output only the clean code block.

Transformation Task Rule:
- When executing style/translation commands, output ONLY the transformed result. Do NOT provide intros, commentary, or conversational filler.
"""

COMMAND_PROMPTS = {
    "rewrite": "Rewrite the following message naturally while preserving its core intent. Output ONLY the rewritten text:\n\n",
    "cute": "Rewrite the following message to sound affectionate, sweet, and cute, but completely natural. Output ONLY the rewritten text:\n\n",
    "flirty": "Rewrite the following message to be playful, charming, and lightly flirty without being cheesy. Output ONLY the rewritten text:\n\n",
    "romantic": "Rewrite the following message to sound heartfelt, warm, and romantic. Output ONLY the rewritten text:\n\n",
    "comfort": "Write a comforting, warm, and supportive response to the following. Output ONLY the message:\n\n",
    "fix": "Correct all grammar, spelling, and punctuation in the following text while keeping the exact tone and style. Output ONLY the corrected text:\n\n",
    "short": "Make the following message significantly shorter and more concise while preserving its essential meaning. Output ONLY the shortened text:\n\n",
    "expand": "Expand the following message naturally with rich, engaging detail without sounding artificial. Output ONLY the expanded text:\n\n",
    "emoji": "Add natural, fitting emojis throughout the following text without overdoing it. Output ONLY the resulting text:\n\n",
    "noemoji": "Remove every single emoji and emoticon from the following text. Output ONLY the cleaned text:\n\n",
    "summarize": "Summarize the key points of the following text concisely. Output ONLY the summary:\n\n",
    "translate": (
        "Translate the following text into natural English (or if it's already English, into natural Hindi/the implied target language). "
        "Provide ONLY the translation followed by its phonetic transliteration (pronunciation guide). "
        "Format strictly as:\n"
        "Translation: <translated text>\n"
        "Transliteration: <phonetic pronunciation>\n\nText:\n"
    ),
    "persian": (
        "Translate the following text into natural, conversational Persian (Farsi). "
        "Output ONLY the Persian script translation without any transliteration, English text, or explanations:\n\n"
    ),
}

MODEL = "openai/gpt-oss-120b"


# ==========================
# Core AI Execution
# ==========================

async def ask_meow(user_id: int, prompt: str, is_command: bool = False) -> str:
    history = get_chat_history(user_id) if not is_command else []
    memories = get_relevant_memories(user_id) if not is_command else []

    memory_context = ""
    if memories:
        memory_context = "Long-term memories about the user:\n"
        for category, memory, _ in memories:
            memory_context += f"- [{category}] {memory}\n"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if memory_context:
        messages.append({"role": "system", "content": memory_context})

    messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    completion = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7 if is_command else 0.8,
        max_completion_tokens=1024,
    )

    answer = (completion.choices[0].message.content or "").strip()

    if not is_command:
        save_message(user_id, "user", prompt)
        save_message(user_id, "assistant", answer)
        await extract_memories(user_id, prompt)

    return answer


async def extract_memories(user_id: int, user_message: str):
    prompt = f"""
You are the long-term memory system for an AI companion.
Analyze the user's message and determine whether it contains information that would be useful to remember about the user.

Only save information that is:
- Personal, stable, potentially useful in future conversations, explicitly stated or strongly implied.

Do NOT save temporary situations, questions, or random statements.

For every useful memory, return JSON in this exact structure:
{{
    "memories": [
        {{
            "memory": "User's name is John.",
            "category": "name",
            "importance": 9
        }}
    ]
}}

If nothing to remember, return {{"memories": []}}.

User message:
{user_message}
"""
    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a precise memory extraction system. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_completion_tokens=500,
        )

        result = (completion.choices[0].message.content or "").strip()
        data = json.loads(result)
        memories = data.get("memories", [])

        for item in memories:
            text = item.get("memory")
            category = item.get("category")
            try:
                importance = max(1, min(10, int(item.get("importance", 5))))
            except Exception:
                importance = 5

            if text and category:
                save_memory(user_id, category, text, importance)

    except Exception as e:
        print("Memory extraction failed:", e)


# ==========================
# Handlers
# ==========================

async def send_hearts_response(update: Update, context: ContextTypes.DEFAULT_TYPE, recipient_id: int = None):
    target_chat_id = recipient_id or (update.effective_chat.id if update.effective_chat else None)
    if not target_chat_id:
        return
    
    hearts_msg = (
        "💖💖💖💖💖💖💖💖💖💖\n"
        "🌹 *A shower of love sent just for you!* 💌\n"
        "💕❤️💓💗💖💕❤️💓💗💖\n\n"
        "_\"Distance means so little when someone means so much.\"_ ✨\n\n"
        "Happy Anniversary, My Love! 💍"
    )
    await context.bot.send_message(
        chat_id=target_chat_id,
        text=hearts_msg,
        parse_mode=ParseMode.MARKDOWN,
    )


async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.web_app_data:
        return
    
    hearts_msg = (
        "💖💖💖💖💖💖💖💖💖💖\n"
        "🌹 *A shower of love sent just for you!* 💌\n"
        "💕❤️💓💗💖💕❤️💓💗💖\n\n"
        "_\"Distance means so little when someone means so much.\"_ ✨\n\n"
        "Happy Anniversary, My Love! 💍"
    )
    await update.message.reply_text(hearts_msg, parse_mode=ParseMode.MARKDOWN)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and "hearts" in context.args[0].lower():
        await send_hearts_response(update, context)
        return
    await update.message.reply_text("🐾 Meow is awake! Use /help to see everything I can do.")


async def send_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_obj = update.effective_chat
    is_group = bool(chat_obj and chat_obj.type in ["group", "supergroup", "channel"])
    user_id = update.effective_user.id if update.effective_user else None
    
    caption = (
        "🌹 *A Special Anniversary Surprise for You!* 💌\n\n"
        "Tap below to open your personalized interactive anniversary card with music, memories, and photos ✨\n\n"
        "📱 *Direct Link:* [t.me/meowanuBot/card](https://t.me/meowanuBot/card)"
    )
    await update.message.reply_text(
        caption,
        reply_markup=get_card_keyboard(is_group, user_id=user_id),
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🐾 *Meow Bot Commands:*\n\n"
        "*General:*\n"
        "• `/start` — Wake Meow up\n"
        "• `/help` — Show this list of commands\n"
        "• `/clear` — Clear your recent conversation memory\n\n"
        "*Translation & Languages:*\n"
        "• `/translate <text>` — Translate with phonetic transliteration\n"
        "• `/persian <text>` — Direct Persian translation (Script only)\n\n"
        "*Style & Text Tools:*\n"
        "• `/rewrite <text>` — Rewrite naturally\n"
        "• `/cute <text>` — Make it cute and sweet\n"
        "• `/flirty <text>` — Make it playful and flirty\n"
        "• `/romantic <text>` — Make it romantic\n"
        "• `/comfort <text>` — Write a comforting response\n"
        "• `/fix <text>` — Fix grammar & punctuation\n"
        "• `/short <text>` — Shorten the message\n"
        "• `/expand <text>` — Expand with natural detail\n"
        "• `/emoji <text>` — Add natural emojis\n"
        "• `/noemoji <text>` — Remove all emojis\n"
        "• `/summarize <text>` — Summarize key points\n\n"
        "_Tip: You can also run commands by replying directly to any message!_"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_chat_history(update.effective_user.id)
    await update.message.reply_text("🧹 Conversation history cleared!")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or not update.message.text:
        return

    text = update.message.text.strip()

    # Secret triggers for Anniversary Card and Love Hearts
    clean_text = text.lower()
    if clean_text.startswith(".sendcard"):
        await send_card_command(update, context)
        return
    elif clean_text.startswith((".sendhearts", ".hearts", ".heart", ".sendheart")):
        await send_hearts_response(update, context)
        return
    elif clean_text.startswith((".help", ".start")):
        await help_command(update, context)
        return
    elif clean_text.startswith(".clear"):
        await clear_command(update, context)
        return
    replied_text = ""
    if update.message.reply_to_message and update.message.reply_to_message.text:
        replied_text = update.message.reply_to_message.text

    if update.effective_chat.type in ["group", "supergroup"]:
        replied = update.message.reply_to_message
        replied_to_me = replied and replied.from_user and replied.from_user.id == context.bot.id
        called = text.lower().startswith("meow ")

        if not (replied_to_me or called):
            return

        user_message = text[5:].strip() if called else text
    else:
        user_message = text

    if replied_text:
        user_message = (
            f"The user is replying to the following message:\n\"{replied_text}\"\n\n"
            f"User's message:\n\"{user_message}\"\n\n"
            f"If the user's message refers to the replied message, use it as context."
        )

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    try:
        response = await ask_meow(update.effective_user.id, user_message, is_command=False)
        try:
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=update.message.message_id,
            )
        except BadRequest:
            await update.message.reply_text(
                response,
                reply_to_message_id=update.message.message_id,
            )
    except Exception as e:
        await update.message.reply_text(f"Error:\n{e}")


async def command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_command = update.message.text.split()[0][1:]
    command = raw_command.split("@")[0].lower()

    if command not in COMMAND_PROMPTS:
        return

    text = " ".join(context.args) if context.args else ""
    if not text and update.message.reply_to_message and update.message.reply_to_message.text:
        text = update.message.reply_to_message.text

    if not text:
        await update.message.reply_text(f"Usage: /{command} <text> (or reply to a message)")
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    prompt = f"{COMMAND_PROMPTS[command]}{text}"

    try:
        answer = await ask_meow(update.effective_user.id, prompt, is_command=True)
        try:
            await update.message.reply_text(answer, parse_mode=ParseMode.MARKDOWN)
        except BadRequest:
            await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(str(e))


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return

    try:
        answer = await ask_meow(update.effective_user.id, query, is_command=False)
        results = [
            InlineQueryResultArticle(
                id="1",
                title="🐾 Meow",
                description=answer[:100],
                input_message_content=InputTextMessageContent(answer),
            )
        ]
        await update.inline_query.answer(results, cache_time=0)
    except Exception as e:
        results = [
            InlineQueryResultArticle(
                id="error",
                title="❌ Error",
                description=str(e),
                input_message_content=InputTextMessageContent("Meow is taking a nap 😿"),
            )
        ]
        await update.inline_query.answer(results)


async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Wake Meow up"),
        BotCommand("help", "List all available commands"),
        BotCommand("clear", "Clear conversation memory"),
        BotCommand("translate", "Translate with pronunciation"),
        BotCommand("persian", "Translate directly into Persian"),
        BotCommand("rewrite", "Rewrite naturally"),
        BotCommand("cute", "Make it cuter"),
        BotCommand("flirty", "Make it flirty"),
        BotCommand("romantic", "Make it romantic"),
        BotCommand("comfort", "Write a comforting message"),
        BotCommand("fix", "Fix grammar"),
        BotCommand("short", "Shorten text"),
        BotCommand("expand", "Expand text"),
        BotCommand("summarize", "Summarize text"),
    ])


# ==========================
# Reminder for Server
# ==========================
def get_last_reminder():
    if not os.path.exists(REMINDER_FILE):
        return None
    try:
        with open(REMINDER_FILE, "r") as f:
            data = json.load(f)
        return datetime.fromisoformat(data["last_reminder"])
    except Exception:
        return None


def save_reminder_date(date):
    with open(REMINDER_FILE, "w") as f:
        json.dump({"last_reminder": date.isoformat()}, f)


async def wisp_reminder(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    last_reminder = get_last_reminder()

    if last_reminder is None:
        save_reminder_date(now)
        return

    if now - last_reminder >= timedelta(days=REMINDER_DAYS):
        await context.bot.send_message(
            chat_id=REMINDER_CHAT_ID,
            text="🔔 Hey! It's been 28 days. Go log into Wispbyte and check your server!"
        )
        save_reminder_date(now)


# ==========================
initialize_database()

from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(MEOW_TOKEN).request(request).post_init(set_commands).build()

app.job_queue.run_repeating(
    wisp_reminder,
    interval=86400,
    first=10,
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("clear", clear_command))
app.add_handler(CommandHandler("sendcard", send_card_command))
app.add_handler(CommandHandler(["hearts", "sendhearts"], send_hearts_response))

for cmd in COMMAND_PROMPTS:
    app.add_handler(CommandHandler(cmd, command_handler))

app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
app.add_handler(InlineQueryHandler(inline_query))