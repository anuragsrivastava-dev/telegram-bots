import random
import re
import time
from config import TND_BOT_TOKEN, ADMIN_USER_ID

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    MenuButtonCommands,
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

# ----------------------------------------------------
# 100+ SPICY & ROMANTIC TRUTHS (LDR / COUPLES)
# ----------------------------------------------------
TRUTHS_POOL = [
    "What is the very first thing you want to do the second we see each other in person?",
    "What is your absolute favorite romantic or intimate memory of us so far?",
    "What is a dirty or romantic fantasy about us that you have never told me?",
    "Which photo or video of me is secretly your favorite to look at when you miss me?",
    "What is something I do or say over call or text that instantly turns you on?",
    "What were you honestly thinking the exact moment you realized you had feelings for me?",
    "What is your favorite part of my body, and what do you want to do to it?",
    "If we had an entire weekend locked in a hotel room together, how would we spend it?",
    "What is the wildest place you would ever want to hook up with me?",
    "What is something you wish I would wear (or not wear) on our late-night video calls?",
    "What was the most vivid romantic or spicy dream you’ve ever had about me?",
    "What is your favorite outfit or style that you've seen me in?",
    "What is the most sensitive spot on your body that drives you crazy when touched?",
    "Do you prefer slow, passionate intimacy or rough, intense energy?",
    "What is a secret nickname you secretly wish you could call me in private?",
    "What is something completely innocent that I do which you find unexpectedly seductive?",
    "If you could have me do whatever you wanted for 30 minutes, what would your instructions be?",
    "What song always makes you think of me or gets you in the mood?",
    "Have you ever re-read our spicy chats when you were alone in bed?",
    "What is your honest opinion on morning intimacy vs late-night intimacy?",
    "What is one thing you are most excited to try together in bed when we close the distance?",
    "What is the biggest turn-on you have that you rarely talk about?",
    "If I walked into your room right now with zero warning, what is the first thing you'd do?",
    "What is your favorite way to be kissed—soft and gentle or deep and dominant?",
    "What is the most distracting thought about me you've had during a normal work or study day?",
    "Would you rather be tied up/pinned down, or be the one in total control?",
    "What is something romantic or cheesy that you secretly love when I do it?",
    "What is the longest time you've spent thinking about me in bed before falling asleep?",
    "What is your favorite compliment I've ever given you?",
    "If we were playing strip poker right now, how many rounds before you're completely bare?",
    "What is one outfit of yours that makes you feel the hottest?",
    "What kind of teasing drives you the most insane over text or voice notes?",
    "What is something you want me to whisper in your ear when we are cuddling in bed?",
    "If you had to describe our chemistry in three words, which three would you pick?",
    "What is the most daring thing you'd do with me in a semi-public place?",
    "What is one habit of mine that you find irresistibly adorable?",
    "Do you like being told what to do, or do you prefer giving the orders?",
    "What is a spicy photo angle of yours that you know always gets my attention?",
    "What was your heart rate doing the very first time we started flirting heavily?",
    "If you could wake up next to me tomorrow morning, what is the first thing we'd do?",
    "What is your favorite physical sensation when we are affectionate?",
    "What is the biggest romantic surprise you have ever daydreamed about planning for me?",
    "What is something naughty you thought about doing to me during our last video call?",
    "Do you prefer lights on, dim candle-light, or pitch black darkness?",
    "What is one question about my desires or kinks that you've been too shy to ask?",
    "What is the sweetest thing I have ever done that genuinely melted your heart?",
    "If I gave you a full body massage, where would you want me to start and finish?",
    "What is the craziest thing distance has made you appreciate about our connection?",
    "What is your favorite teasing message I have ever sent you?",
    "If we had only 10 minutes together before a flight, what would we do?",
    "What is something you want us to do under the blankets that we haven't done yet?",
    "How often do you stare at my pictures when you're feeling lonely?",
    "What kind of lingerie or sleepwear do you look best in?",
    "What is the most vulnerable you have ever felt with me, and did it bring us closer?",
    "If you could freeze time for 1 hour with just the two of us, what are we doing?",
    "What is a physical gesture (like forehead kisses, hand holding, neck kisses) you crave most?",
    "What is the hottest text message you have ever drafted to me but hesitated to send?",
    "If you had to pick one word to describe how you feel when we look at each other, what is it?",
    "What is your absolute favorite spot to be kissed?",
    "What is something you want me to do to you that would make you completely lose your mind?",
    "What is the most romantic date night idea you want us to experience in person?",
    "What is something spicy you've always wanted to try but haven't told anyone before?",
    "If I dared you to kiss me right in front of a crowd, would you do it without hesitation?",
    "What is the most intense feeling you've had while listening to my voice notes?",
    "What is one thing about my personality that makes you feel completely safe with me?",
    "What would you do if I suddenly pinned your hands above your head?",
    "What is your favorite time of day to get flirty with me?",
    "How long after waking up do you usually check your phone for my message?",
    "What is the most attractive quality a person can have in your eyes?",
    "If you could teleport to my bed right this second, what are you wearing?",
    "What is something I say that gives you butterflies every single time?",
    "What is your stance on spicy roleplay, and what role would you pick?",
    "What is the deepest emotional connection point you feel we share?",
    "What is one thing you can never get enough of when it comes to us?",
    "If we were stranded on a private island, what would our daily routine look like?",
    "What is the most seductive look I give you on camera?",
    "What is something you want me to do more often during our private calls?",
    "What is the most meaningful promise we have made to each other?",
    "If you had to pick between endless kisses or endless cuddles, which wins?",
    "What is a secret romantic habit you have when you think about our future together?",
]

# ----------------------------------------------------
# 100+ SPICY & ROMANTIC DARES (LDR / COUPLES)
# ----------------------------------------------------
DARES_POOL = [
    "Send a 10-second voice note whispering in your most seductive voice what you want to do to me.",
    "Send a mirror selfie showing off your favorite outfit or curve right now.",
    "Bite your lip, take a close-up photo, and send it to the chat.",
    "Record a voice note describing what you are wearing right now in sensual detail.",
    "Send a photo of your bare legs or shoulders from bed.",
    "Send a 5-second voice note breathing softly into the mic like you are lying right next to me.",
    "Take a spicy picture from an angle you've never sent before and send it to the chat.",
    "Type out an explicit paragraph describing exactly how our first night together will go.",
    "Send a voice note confessing your dirtiest thought about me from today.",
    "Give your phone camera a slow, intense kiss and send the video snippet.",
    "Unbutton or lift up one piece of clothing, take a tease photo, and send it.",
    "Send a voice note calling me your favorite pet name with full emotion.",
    "Send a screenshot of your lock screen wallpaper right now.",
    "Record a 10-second voice message telling me exactly what you love most about my body.",
    "Send a selfie from bed giving your most seductive bedroom eyes.",
    "Send a photo showing off your collarbone or neckline.",
    "Send a voice note describing a fantasy scenario involving us in vivid detail.",
    "Send a voice note telling me 'You belong to me' in your most commanding tone.",
    "Drop your top 3 favorite spicy emojis that describe what you want right now.",
    "Send a 5-second clip running your fingers through your hair while looking into the camera.",
    "Send a photo of the bed where we will eventually sleep together.",
    "Send a voice note saying 'I miss you so much it hurts' as softly as you can.",
    "Type out 5 explicit things you want me to do to you the next time we are alone.",
    "Send a picture of your lips making a pout or gentle kiss face.",
    "Send a voice note describing the exact touch or kiss you crave right this second.",
    "Send a tease photo showing the waistband of your underwear or sleepwear.",
    "Record a voice note making the cutest soft gasp or sigh you can make.",
    "Send a photo of your favorite scent/perfume/cologne bottle and tell me what it reminds you of.",
    "Send a voice note ranking the top 3 physical things you want to do with me from 1 to 3.",
    "Send a close-up photo of your eyes looking straight into the lens.",
    "Type out a mini erotic story where we are the two main characters.",
    "Send a voice note saying 'Good girl' / 'Good boy' or 'My love' in your deepest tone.",
    "Send a video snippet blowing a slow, passionate kiss directly to the camera.",
    "Take a silhouette or low-light photo in your room and send it.",
    "Send a voice note telling me what you would do if I climbed on top of you right now.",
    "Send a picture of your hands resting in your lap.",
    "Send a voice note laughing gently and telling me how crazy you are about me.",
    "Send a spicy text message that would make anyone else blush if they read it.",
    "Send a photo of yourself wearing something that belongs to me (or your favorite lounge wear).",
    "Send a 10-second voice note talking about how good it will feel when distance is finally zero.",
    "Send a close-up photo of your neck or jawline.",
    "Record a voice note moaning my name very softly.",
    "Send a picture showing off your back or waist.",
    "Type out a romantic vow you want to make to me for when we are together.",
    "Send a voice note telling me what my voice does to your body.",
    "Send a selfie holding a piece of paper that says 'All yours'.",
    "Send a photo from bed showing the empty space next to you waiting for me.",
    "Send a voice note daring me to do something spicy back to you.",
    "Send a 5-second video tracing your finger along your collarbone or lips.",
    "Send a screenshot of the romantic/spicy song currently at the top of your mind.",
    "Send a voice note asking for permission in the naughtiest way possible.",
    "Send a tease photo showing off your bare back or shoulders in low light.",
    "Record a voice note giving me three strict rules I must obey when we meet in person.",
    "Send a selfie biting your finger or thumb seductively.",
    "Send a voice note telling me the most naughty thing you've ever imagined doing to me in a car.",
    "Send a photo showing your bare feet or ankles resting on the sheets.",
    "Send a voice note describing in 3 sentences what you'd do if we woke up tangled together.",
    "Send a picture of yourself wearing red or black, or your favorite nightwear.",
    "Type out the most intense compliment you have ever wanted to give my body.",
    "Send a voice note whispering 'You're mine' 3 times with increasing intensity.",
    "Send a photo of your hand making a heart over your chest.",
    "Record a 5-second voice note telling me where you want my hands first.",
    "Send a tease selfie where your face is hidden but your body looks irresistible.",
    "Send a voice note describing what my scent or cologne does to you.",
    "Send a photo showing your smile right now after reading this prompt.",
]


# ----------------------------------------------------
# No-Repeat Shuffle Cycle Engine
# ----------------------------------------------------
class ShuffledDeck:
    def __init__(self, items: list[str]):
        self.original = list(items)
        self.deck = []
        self._refill()

    def _refill(self):
        self.deck = list(self.original)
        random.shuffle(self.deck)

    def draw(self) -> str:
        if not self.deck:
            self._refill()
        return self.deck.pop()


truth_deck = ShuffledDeck(TRUTHS_POOL)
dare_deck = ShuffledDeck(DARES_POOL)


def escape_md(text: str) -> str:
    """Escapes MarkdownV2 reserved characters."""
    if not text:
        return ""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


def get_game_keyboard(last_type: str = "random") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🗣️ Truth", callback_data="tnd_truth"),
            InlineKeyboardButton("🔥 Dare", callback_data="tnd_dare"),
        ],
        [
            InlineKeyboardButton("🎲 Random", callback_data="tnd_random"),
            InlineKeyboardButton("⏭️ Skip", callback_data=f"tnd_skip_{last_type}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_prompt_text(user_name: str, choice_type: str) -> tuple[str, str]:
    if choice_type == "truth":
        prompt = escape_md(truth_deck.draw())
        return f"💋 *Truth for* *{user_name}*:\n\n> {prompt}", "truth"
    elif choice_type == "dare":
        prompt = escape_md(dare_deck.draw())
        return f"🔥 *Dare for* *{user_name}*:\n\n> {prompt}", "dare"
    else:  # random or skip resolution
        is_truth = random.choice([True, False])
        if is_truth:
            prompt = escape_md(truth_deck.draw())
            return f"🎲 *Random Choice: Truth for* *{user_name}*:\n\n> {prompt}", "truth"
        else:
            prompt = escape_md(dare_deck.draw())
            return f"🎲 *Random Choice: Dare for* *{user_name}*:\n\n> {prompt}", "dare"


# ----------------------------------------------------
# Command Handlers (. and / prefixes)
# ----------------------------------------------------
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    latency = int((time.time() - start_time) * 1000)
    await msg.edit_text(
        f"🏓 *Pong!* `{latency}ms`\n🔥 *Truth & Dare Bot* is Online & Ready to Play! ✨",
        parse_mode="Markdown"
    )


async def helpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorized to use admin commands.")
        return
    admin_help = (
        "👑 *Truth & Dare Bot Admin Control Panel:*\n\n"
        "• `/ping` — Check bot latency & online status\n"
        "• `/tnd` — Start a spicy round\n"
        "• `/truth` — Draw a spicy Truth question\n"
        "• `/dare` — Draw a spicy Dare challenge\n"
        "• `/random` — Draw a random prompt\n"
        "• `/skip` — Skip to next prompt\n"
        "• `/helpad` — Show this admin help menu"
    )
    await update.message.reply_text(admin_help, parse_mode="Markdown")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌹 *Spicy & Romantic Truth or Dare Bot is ready\\!*\n\n"
        "Works in DMs & Groups with both `/` and `.` prefixes\\.\n\n"
        "• `.tnd` or `/tnd` \\- Spin up interactive game board\n"
        "• `.truth` or `/truth` \\- Draw a deep/spicy truth\n"
        "• `.dare` or `/dare` \\- Draw a spicy/romantic dare\n"
        "• `.random` or `/random` \\- Draw a random spicy prompt\n"
        "• `.skip` or `/skip` \\- Skip and draw another prompt\n"
        "• `.help` or `/help` \\- Show command guide"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 *Couple Game Guide:*\n\n"
        "1\\. Use `.tnd` or `/tnd` to start a round\\.\n"
        "2\\. Take turns tapping *Truth*, *Dare*, *Random*, or *Skip*\\.\n"
        "3\\. You can also call direct commands like `.truth`, `.dare`, `.random`, or `.skip`\\."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def tnd_round_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔥 *Spicy Truth or Dare Round Started\\!*\n\n"
        "Choose your fate below, my love:"
    )
    await update.message.reply_text(
        msg,
        reply_markup=get_game_keyboard("random"),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def truth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = escape_md(update.effective_user.first_name)
    text, last_type = get_prompt_text(user_name, "truth")
    await update.message.reply_text(
        text,
        reply_markup=get_game_keyboard(last_type),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def dare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = escape_md(update.effective_user.first_name)
    text, last_type = get_prompt_text(user_name, "dare")
    await update.message.reply_text(
        text,
        reply_markup=get_game_keyboard(last_type),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = escape_md(update.effective_user.first_name)
    text, last_type = get_prompt_text(user_name, "random")
    await update.message.reply_text(
        text,
        reply_markup=get_game_keyboard(last_type),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = escape_md(update.effective_user.first_name)
    text, last_type = get_prompt_text(user_name, "random")
    skip_header = f"⏭️ *Skipped\\! New Prompt for* *{user_name}*:\n\n"
    content = text.split(":\n\n> ")[-1]
    formatted = f"{skip_header}> {content}"
    await update.message.reply_text(
        formatted,
        reply_markup=get_game_keyboard(last_type),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


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
    elif command in ["tnd", "game", "play"]:
        await tnd_round_command(update, context)
    elif command == "truth":
        await truth_command(update, context)
    elif command == "dare":
        await dare_command(update, context)
    elif command == "random":
        await random_command(update, context)
    elif command in ["skip", "next"]:
        await skip_command(update, context)
    elif command in ["help", "start"]:
        await help_command(update, context)


# ----------------------------------------------------
# Inline Button Callbacks
# ----------------------------------------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_name = escape_md(query.from_user.first_name)
    choice = query.data

    if choice == "tnd_truth":
        text, last_type = get_prompt_text(user_name, "truth")
    elif choice == "tnd_dare":
        text, last_type = get_prompt_text(user_name, "dare")
    elif choice == "tnd_random":
        text, last_type = get_prompt_text(user_name, "random")
    elif choice.startswith("tnd_skip"):
        parts = choice.split("_")
        re_roll_type = parts[2] if len(parts) > 2 else "random"
        raw_text, last_type = get_prompt_text(user_name, re_roll_type)
        content = raw_text.split(":\n\n> ")[-1]
        text = f"⏭️ *Skipped\\! New Prompt for* *{user_name}*:\n\n> {content}"
    else:
        text, last_type = get_prompt_text(user_name, "random")

    await query.message.reply_text(
        text,
        reply_markup=get_game_keyboard(last_type),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def set_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show game commands"),
        BotCommand("tnd", "Start a spicy Truth or Dare round"),
        BotCommand("truth", "Get a spicy Truth question"),
        BotCommand("dare", "Get a spicy Dare challenge"),
        BotCommand("random", "Get a random spicy prompt"),
        BotCommand("skip", "Skip current prompt"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e:
        print(f"Notice setting commands in TnDBot: {e}")


request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(TND_BOT_TOKEN).request(request).post_init(set_commands).build()

# Slash Commands
app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("ping", ping_command))
app.add_handler(CommandHandler("helpad", helpad_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler(["tnd", "game"], tnd_round_command))
app.add_handler(CommandHandler("truth", truth_command))
app.add_handler(CommandHandler("dare", dare_command))
app.add_handler(CommandHandler("random", random_command))
app.add_handler(CommandHandler(["skip", "next"], skip_command))

# Dot Prefix Handler
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dot_prefix))

# Inline Keyboards Callback Handler
app.add_handler(CallbackQueryHandler(handle_callback, pattern=r"^tnd_"))