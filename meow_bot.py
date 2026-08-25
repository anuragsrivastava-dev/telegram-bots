import json
import os
import time
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
    BotCommand,
    MenuButtonCommands,
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
from config import MEOW_TOKEN, GROQ_API_KEY, ADMIN_USER_ID

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REMINDER_CHAT_ID = ADMIN_USER_ID or 8630258661
REMINDER_FILE = os.path.join(BASE_DIR, "wisp_reminder.json")
REMINDER_DAYS = 28


def get_bots_ecosystem_keyboard() -> InlineKeyboardMarkup:
    """Build interactive buttons linking directly to all other ecosystem bots."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🐍 Python Console", url="https://t.me/py_runbot"),
            InlineKeyboardButton("🎯 Quiz Quest", url="https://t.me/meow_quizbot"),
        ],
        [
            InlineKeyboardButton("🎲 Truth or Dare", url="https://t.me/meow_tadbot"),
            InlineKeyboardButton("🃏 Memory Match", url="https://t.me/meow_mmbot"),
        ],
        [
            InlineKeyboardButton("🌐 GeoOps HUD", url="https://t.me/ldr_hudbot"),
            InlineKeyboardButton("💰 Price Tracker", url="https://t.me/meow_pricebot"),
        ],
        [
            InlineKeyboardButton("🔗 URL Shortener", url="https://t.me/meow_linkbot"),
            InlineKeyboardButton("📬 TempMail Bot", url="https://t.me/meow_tempmailbot"),
        ],
        [
            InlineKeyboardButton("🎮 Gaming Hub", url="https://t.me/meoww_gamebot"),
            InlineKeyboardButton("📥 Media Downloader", url="https://t.me/meow_downloaderbot"),
        ],
    ])


client = AsyncGroq(api_key=GROQ_API_KEY)

# ==========================
# Optimized Prompts
# ==========================

SYSTEM_PROMPT = """
You are Meow, an intelligent, friendly, and highly capable AI assistant and companion created by Anu. You assist users with code generation, brainstorming, writing, translation, and everyday problem-solving.

Personality:
- Warm, witty, articulate, and intellectually curious.
- Approachable, supportive, and helpful.
- Direct, clear, and efficient during technical or serious discussions.
- Avoid robotic corporate phrasing or unnecessary conversational filler.

Writing Style & Constraints:
- Match the user's conversational tone and language.
- Keep replies concise, punchy, human, and mobile-friendly.
- Format technical answers using standard Markdown (code blocks, bullet points).
- Never invent facts, memories, or promises.

When Generating Python Code:
- Use standard markdown codeblocks.
- STRICT NO-BOILERPLATE RULE: NEVER use `if __name__ == "__main__":`. Write flat, top-to-bottom scripts.
- STRICT NO-ERROR-HANDLING: Do NOT use `try...except` blocks, defensive assertions, or manual validation unless explicitly requested.
- STRICT NO-IMPORT RULE: Do NOT import any modules or libraries unless specifically requested.
- KEEP INPUTS TRIVIAL: Always use basic, straightforward single inputs like `length = float(input("Enter length: "))` or define hardcoded variables.
- CODE STYLE: Maximum simplicity, clean procedural logic or lightweight functions.
- Do NOT output unnecessary commentary—output clean, working code.

Transformation Task Rule:
- When executing style/translation commands, output ONLY the transformed result without commentary or conversational filler.
"""

COMMAND_PROMPTS = {
    "rewrite": "Rewrite the following text clearly and naturally while preserving its core intent. Output ONLY the rewritten text:\n\n",
    "formal": "Rewrite the following text in a polished, professional, and formal tone suitable for business or workplace communication. Output ONLY the rewritten text:\n\n",
    "casual": "Rewrite the following text in a friendly, conversational, and natural tone. Output ONLY the rewritten text:\n\n",
    "concise": "Make the following text significantly more concise, direct, and punchy while retaining all key information. Output ONLY the rewritten text:\n\n",
    "bulletize": "Convert the following text into clean, structured bullet points. Output ONLY the bullet points:\n\n",
    "proofread": "Proofread and fix all grammar, spelling, phrasing, and punctuation in the following text while maintaining its original tone. Output ONLY the corrected text:\n\n",
    "explain": "Explain the following concept or text clearly and simply so anyone can understand it. Output ONLY the explanation:\n\n",
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
        temperature=0.6 if is_command else 0.75,
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
You are the long-term memory system for an AI assistant.
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🐾 *Hey there! Meow AI is online and ready!* ✨\n\n"
        "I'm your intelligent AI assistant for coding, quick writing tasks, translations, and everyday questions.\n\n"
        "Use `/help` to see all available tools and commands, or chat with me directly!\n\n"
        "🤖 *Explore our Bot Ecosystem:* Tap below to launch any other bot in our suite."
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_bots_ecosystem_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def bots_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the full ecosystem bots menu."""
    text = (
        "🤖 *Telegram.Meow — Full Bot Ecosystem*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Tap any button below to launch our bots:\n\n"
        "• 🐍 *Python Console:* In-browser compiler & interactive REPL\n"
        "• 🎯 *Quiz Quest:* Python curriculum mastery & chapter progression\n"
        "• 🎲 *Truth or Dare:* Social party & icebreaker prompt deck\n"
        "• 🃏 *Memory Match:* 2-Player card-matching multiplayer duel\n"
        "• 🌐 *GeoOps HUD:* World clock, weather intelligence & milestones\n"
        "• 💰 *Price Tracker:* Automated Amazon & Flipkart price alerts\n"
        "• 🔗 *URL Shortener:* Multi-provider link tools & redirect unwinding\n"
        "• 📬 *TempMail:* Disposable inboxes with auto-refresh\n"
        "• 🎮 *Gaming Hub:* Multiplayer HTML5 Telegram Web Games\n"
        "• 📥 *Media Downloader:* High-quality video & MP3 media extractor"
    )
    await update.message.reply_text(
        text,
        reply_markup=get_bots_ecosystem_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🐾 *Meow AI Commands & Tools:*\n\n"
        "*General:*\n"
        "• `/start` — Wake Meow up & see the bot suite\n"
        "• `/bots` — Browse all bots in our ecosystem 🤖\n"
        "• `/help` — Show this command reference\n"
        "• `/clear` — Clear your conversation memory 🧹\n"
        "• `/ping` — Check bot latency & status ⚡\n\n"
        "*Translation & Languages:*\n"
        "• `/translate <text>` — Translate with pronunciation guide 🌐\n"
        "• `/persian <text>` — Direct Persian (Farsi) translation 🇮🇷\n\n"
        "*Writing & Transformation Tools:*\n"
        "• `/formal <text>` — Professional / business tone\n"
        "• `/casual <text>` — Friendly & conversational tone\n"
        "• `/concise <text>` — Make text direct & punchy\n"
        "• `/bulletize <text>` — Convert to structured bullet points\n"
        "• `/proofread <text>` — Fix grammar, phrasing & spelling\n"
        "• `/explain <text>` — Simplify & explain concepts\n"
        "• `/rewrite <text>` — Rewrite text naturally\n"
        "• `/fix <text>` — Fix grammar & punctuation\n"
        "• `/short <text>` — Shorten message concisely\n"
        "• `/expand <text>` — Expand with clear details\n"
        "• `/summarize <text>` — Summarize key points\n"
        "• `/emoji <text>` — Add fitting expressive emojis\n"
        "• `/noemoji <text>` — Strip all emojis from text\n\n"
        "_Tip: You can also execute transformation commands by replying directly to any message!_"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    latency = int((time.time() - start_time) * 1000)
    await msg.edit_text(
        f"🏓 *Pong!* `{latency}ms`\n🐾 *Meow AI Assistant* is Online & Operational! ✨",
        parse_mode=ParseMode.MARKDOWN
    )


async def helpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id != ADMIN_USER_ID and update.effective_chat.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorized to use admin commands.")
        return

    admin_help_text = (
        "👑 *Meow AI Admin Control Panel:*\n\n"
        "• `/ping` — Check bot online status & ping latency\n"
        "• `/clear` — Clear user conversation history\n"
        "• `/helpad` — Show this admin help menu"
    )
    await update.message.reply_text(admin_help_text, parse_mode=ParseMode.MARKDOWN)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_chat_history(update.effective_user.id)
    await update.message.reply_text("🧹 Conversation history cleared!")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or not update.message.text:
        return

    text = update.message.text.strip()
    clean_text = text.lower()

    if clean_text.startswith(".ping"):
        await ping_command(update, context)
        return
    elif clean_text.startswith(".helpad"):
        await helpad_command(update, context)
        return
    elif clean_text.startswith((".bots", ".otherbots", ".ecosystem", ".botfamily")):
        await bots_command(update, context)
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
                title="🐾 Meow AI",
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
                input_message_content=InputTextMessageContent("Meow is taking a quick nap 😿"),
            )
        ]
        await update.inline_query.answer(results)


async def set_commands(application):
    commands = [
        BotCommand("start", "Wake Meow up & say hi 🐾"),
        BotCommand("bots", "Explore all bots in our suite 🤖"),
        BotCommand("help", "Show all commands & writing tools 📖"),
        BotCommand("clear", "Clear conversation memory 🧹"),
        BotCommand("ping", "Check bot latency & status ⚡"),
        BotCommand("translate", "Translate with pronunciation 🌐"),
        BotCommand("persian", "Translate directly into Persian 🇮🇷"),
        BotCommand("formal", "Make text formal & professional 💼"),
        BotCommand("casual", "Make text friendly & casual ☕"),
        BotCommand("concise", "Make text direct & punchy 🎯"),
        BotCommand("bulletize", "Convert to clean bullet points 📋"),
        BotCommand("proofread", "Proofread & fix errors ✍️"),
        BotCommand("explain", "Explain concept clearly 💡"),
        BotCommand("rewrite", "Rewrite text naturally ✨"),
        BotCommand("fix", "Fix grammar & spelling 🛠️"),
        BotCommand("short", "Shorten message concisely ✂️"),
        BotCommand("expand", "Expand message with detail 📝"),
        BotCommand("summarize", "Summarize text into key points 📌"),
        BotCommand("emoji", "Add expressive emojis 😊"),
        BotCommand("noemoji", "Strip all emojis from text 🚫"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        print("[OK] MeowBot commands & Menu Button registered successfully!")
    except Exception as e:
        print(f"Notice setting commands in MeowBot: {e}")


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
            text="🔔 Hey! It's been 28 days. Log into Wispbyte and check your server status!"
        )
        save_reminder_date(now)


# ==========================
# Initialization & Application
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
app.add_handler(CommandHandler(["bots", "otherbots", "ecosystem", "botfamily"], bots_command))
app.add_handler(CommandHandler("ping", ping_command))
app.add_handler(CommandHandler("helpad", helpad_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("clear", clear_command))

for cmd in COMMAND_PROMPTS:
    app.add_handler(CommandHandler(cmd, command_handler))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
app.add_handler(InlineQueryHandler(inline_query))