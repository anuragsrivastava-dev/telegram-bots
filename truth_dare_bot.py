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
# 100+ PARTY & ICEBREAKER TRUTHS
# ----------------------------------------------------
TRUTHS_POOL = [
    "What is the most ridiculous lie you told with a completely straight face that everyone believed?",
    "What is your absolute biggest guilty pleasure song that you only blast when you are home alone?",
    "What is the weirdest food combination that you genuinely enjoy eating?",
    "If you could immediately master any single programming language or skill overnight, what would it be?",
    "What is the most embarrassing fashion or hairstyle phase you went through in the past?",
    "If you were granted $10 million tomorrow, what is the first completely unnecessary luxury item you would buy?",
    "What is the most awkward text message you accidentally sent to the wrong person or group?",
    "What is your honest opinion: tabs vs spaces, and light mode vs dark mode?",
    "What is a popular movie or TV show that everyone raves about, but you secretly think is totally overrated?",
    "What is the weirdest rabbit hole you've spent hours exploring on YouTube or Wikipedia at 3 AM?",
    "What is the worst piece of advice you’ve ever given to a friend with full confidence?",
    "If you were forced to eat only one meal for every single day for the rest of your life, what would it be?",
    "What is the funniest or most absurd reason you have ever given to cancel plans last minute?",
    "What is the absolute worst job or task you have ever had to do?",
    "If you could teleport anywhere on Earth right now for exactly 2 hours, where are you going?",
    "What is a silly superstition or irrational fear that you secretly hold?",
    "What is your most useless, bizarre hidden talent that serves zero real-world purpose?",
    "What is the most chaotic bug or error you have ever caused in a project or assignment?",
    "If you could live inside the universe of any video game, book, or movie, which one would you choose?",
    "What was your very first screen name, email address, or gaming handle?",
    "What is the most awkward encounter you've ever had with a teacher, professor, or boss?",
    "If your browser history from the last 7 days was projected on a billboard, how doomed would you be?",
    "What is a habit of yours that you think is completely normal, but others find unusual?",
    "Have you ever pretended to be on a phone call just to avoid talking to someone in public?",
    "What is the most spontaneous thing you have ever done without any planning?",
    "If you had to enter a talent show with only 5 minutes of preparation, what would your act be?",
    "What is the funniest rumor you’ve ever heard about yourself?",
    "What is an unpopular opinion you hold firmly that always starts debates among friends?",
    "If you were a superhero or supervillain, what would your theme music and catchphrase be?",
    "What is the most creative excuse you've ever used to get out of doing work or homework?",
    "What was the most disastrous cooking or baking experiment you ever attempted?",
    "If you could swap lives with any historical figure or fictional character for 24 hours, who would it be?",
    "What is something you bought on impulse that ended up being completely useless?",
    "What is the longest gaming, coding, or binge-watching marathon you have ever pulled?",
    "If animals could talk, which species do you think would be the rudest?",
    "What is your signature dance move when no one is watching?",
    "What is the most bizarre dream you can still vividly remember having?",
    "If you had to be trapped in an elevator for 4 hours with one celebrity, who would you pick?",
    "What is a word or slang term that you use ironically that eventually became part of your actual vocabulary?",
    "What is the most ridiculous thing you believed as a child for way too long?",
    "If you were to open a quirky themed café or restaurant, what would the concept and name be?",
    "What is your go-to karaoke track when you want to get the entire room singing along?",
    "Have you ever tried to fix something yourself and ended up making it ten times worse?",
    "What is the strangest gift you have ever received from someone?",
    "If you had a warning label attached to you, what would it say?",
    "What is the most trivial argument you have ever had with a friend that got surprisingly heated?",
    "What fictional world would you refuse to visit even if you were offered a million dollars?",
    "What is your most memorable accidental injury from doing something utterly stupid?",
    "If you could invent a holiday where everyone had to participate in one silly ritual, what would it be?",
    "What is the ultimate comfort movie that you have watched more than 5 times?",
    "What is something you are surprisingly terrible at despite trying multiple times to learn?",
    "If you had to describe your current work or study style in three words, what would they be?",
    "What is the most awkward zoom call or online meeting moment you’ve experienced?",
    "If you could eliminate one mundane daily chore forever, which one would it be?",
    "What is the best practical joke you have ever pulled (or had pulled on you)?",
    "What is the most adventurous thing on your bucket list that you haven't done yet?",
    "If you had to be an Olympic athlete, which sport would you have the highest chance of not embarrassing yourself in?",
    "What is the weirdest nickname you’ve ever been given and how did you get it?",
    "What is a skill from the 1800s that you wish was still common today?",
    "If you were writing an autobiography, what would the title of chapter 1 be?",
    "What is something you do to procrastinate that actually feels productive but isn't?",
    "If you had the power to make one thing illegal solely because it annoys you, what is it?",
    "What was the very first video game you ever fell in love with?",
    "If you could have dinner with any 3 people (alive, historical, or fictional), who are they?",
    "What is the most chaotic board game or multiplayer game night experience you've ever had?",
    "If you could instantly speak 3 new languages fluently, which ones would you pick?",
    "What is something simple that you constantly forget how to do or spell?",
    "If you were invisible for 24 hours, what harmless mischief would you get up to?",
    "What is your favorite memory from a road trip or vacation with friends?",
    "What was the most satisfying moment of instant karma you have ever witnessed?",
    "If you could design a new roller coaster, what would be its main gimmick?",
    "What is the most questionable life hack that you actually tried and used?",
    "If you could instantly know the undeniable truth behind one mystery in history, which would you pick?",
    "What is the most memorable concert, event, or convention you've ever attended?",
    "What is an app on your phone that you know you should delete but just can't bring yourself to?",
    "If you were challenged to survive on a deserted island with only 3 everyday items, what are they?",
    "What is the funniest inside joke you share with your circle of friends?",
    "If you had to rename yourself tomorrow, what cool new first name would you choose?",
    "What is the worst movie you have ever sat through entirely until the credits rolled?",
    "If your life was turned into a sitcom, what would be your recurring catchphrase or running gag?",
    "What is the strangest hobby or subculture you’ve ever stumbled across on the internet?",
    "What is the most awkward mispronunciation or autocorrect fail you've sent recently?",
    "If you were given a chance to travel to Mars on a one-way trip, would you take it?",
    "What is a food that everyone loves that you simply cannot stand?",
    "What was the boldest bluff you've ever pulled off in a card game or negotiation?",
    "If you had to spend 24 hours without any screens, what would your day look like?",
    "What is the most underrated superpower that would actually be amazingly useful in everyday life?",
    "What is your favorite retro tech gadget that you miss using?",
    "If you had to pitch a terrible movie plot that somehow gets a $100M budget, what is it?",
    "What is the coolest fact you learned recently that blew your mind?",
    "If you could have any mythical creature as a domesticated pet, which one are you adopting?",
    "What is the most embarrassing song in your Spotify / Apple Music wrapped?",
    "If you could instantly swap roles with your favorite YouTuber or streamer for a week, would you?",
    "What is a rule or tradition you think is completely outdated and needs to change?",
    "If you had to compete on a reality TV game show, which one gives you the best odds of winning?",
    "What is the funniest misunderstanding you’ve had with someone due to text without tone?",
    "What is your favorite coding, work, or study beverage of choice?",
    "If you found a time machine that only worked once, would you go to the past or future?",
    "What is the most dramatic overreaction you've ever had to something totally minor?",
    "What is one piece of technology you hope gets invented in the next 10 years?",
]

# ----------------------------------------------------
# 100+ PARTY & ICEBREAKER DARES
# ----------------------------------------------------
DARES_POOL = [
    "Send a 10-second voice note doing your best dramatic movie villain monologue.",
    "Type out your next 3 messages using ONLY emojis and let the group guess what you mean.",
    "Pitch a completely ridiculous startup idea to the chat in 3 sentences with maximum hype.",
    "Send a voice note rapping the lyrics of any nursery rhyme with serious hip-hop energy.",
    "Take a photo of the most random or interesting object within arm's reach and give it an epic backstory.",
    "Send a 5-second voice note doing your best robot impression warning everyone of an impending glitch.",
    "Write a short, overly dramatic 4-line poem about coffee, tea, or water and send it to the chat.",
    "Send a selfie making the most absurd, ridiculous face you can muster without laughing.",
    "Send a voice note speaking in a posh 19th-century Victorian aristocrat accent.",
    "Quickly draw a portrait of a cat or dog in 15 seconds (on paper or digital canvas) and send the photo.",
    "Send a voice note narrating your next physical action like you are a sports commentator at the Olympics.",
    "Tell a genuinely terrible dad joke in the chat. If no one laughs, you must send another.",
    "Send a screenshot of the 5th photo currently in your camera roll.",
    "Send a voice note humming the theme song of your favorite video game or movie and let others guess it.",
    "Type out a message explaining quantum computing or recursion in language that a 5-year-old would understand.",
    "Send a voice note doing an impression of your favorite cartoon or video game character.",
    "Drop your top 5 most frequently used emojis in the chat with zero context.",
    "Send a photo of your desk or workspace setup right this second without tidying anything up.",
    "Send a 5-second voice note making the most authentic race car acceleration sound you can create.",
    "Write an acrostic poem using the letters of your first name where every line is a superpower.",
    "Send a voice note giving an impassioned 15-second speech about why pineapple on pizza is either pure genius or a crime.",
    "Send a screenshot of your current battery percentage and screen time.",
    "Send a voice note speaking only in questions for 15 seconds.",
    "Drop a 3-sentence cliffhanger story that ends right at the most suspenseful moment.",
    "Take a photo of your shoes or socks right now and give them a fashion rating out of 10.",
    "Send a voice note singing the first line of the last song you listened to with full vibrato.",
    "Send a message where the first letter of every word spells out a secret hidden word.",
    "Send a voice note delivering a breaking news weather forecast for an imaginary alien planet.",
    "Give an overly intellectual review of an ordinary object nearby (like a pen, mug, or keyboard).",
    "Send a selfie giving two enthusiastic thumbs up with the biggest grin possible.",
    "Write a mini motivational speech in 2 sentences that sounds like a cheesy 80s movie coach.",
    "Send a voice note laughing like an evil mastermind who just successfully hacked a mainframe.",
    "Drop a completely made-up word in chat, give its dictionary definition, and use it in a sentence.",
    "Send a photo of the book, notebook, or tab closest to you and share one quote from it.",
    "Send a voice note doing an epic movie trailer voice over describing your daily routine.",
    "Write a short haiku about debugging or computer errors and post it.",
    "Send a voice note singing 'Happy Birthday' in opera style.",
    "Send a photo showing your view out the window right now.",
    "Send a voice note listing 10 fruits or vegetables as fast as you humanly can without stuttering.",
    "Pitch yourself as a playable fighting game character (list your 2 special moves and ultimate attack).",
    "Send a voice note doing your best impression of a pirate finding treasure.",
    "Share a random piece of trivia that sounds 100% fake but is actually real.",
    "Send a selfie saluting the camera like a starship captain ready for warp speed.",
    "Type out your favorite tongue twister 3 times fast without making a single typo.",
    "Send a voice note describing what you had for your last meal in the style of a Michelin star food critic.",
    "Invent a new superhero whose power is completely useless in combat but great at house chores.",
    "Send a photo of a doodle you drew on paper right now in under 10 seconds.",
    "Send a voice note pretending you are an astronaut reporting back to Houston about finding aliens.",
    "Drop a riddle in chat and see who in the group can solve it first without Googling.",
    "Send a voice note speaking in slow motion like a tape running out of batteries.",
    "Type out the lyrics to the chorus of your favorite song from memory without looking them up.",
    "Send a photo of whatever beverage you are currently drinking (or empty mug).",
    "Send a voice note acting out an audition for an action hero jumping out of an exploding helicopter.",
    "Give the person above you in chat an over-the-top superhero title and backstory.",
    "Send a 10-second voice note beatboxing your best rhythm.",
    "Send a screenshot of your phone's home screen wallpaper.",
    "Write a dramatic review of a slice of bread as if it changed your life.",
    "Send a voice note counting backwards from 20 to 1 in a whisper.",
    "Send a photo of your pet (or if you don't have one, draw your dream pet).",
    "Send a voice note giving a 10-second eulogy for a bug you accidentally stepped on.",
    "Type out a message backwards so the group has to read it in reverse.",
    "Send a voice note doing your best auctioneer fast-talking impression.",
    "Pick 3 random emojis and write a 1-sentence micro story connecting all three.",
    "Send a selfie giving a high-five directly to the camera lens.",
    "Send a voice note imitating the dial-up internet connection sound.",
    "Write a 3-line dialogue between a toaster and a microwave arguing over who is more important.",
    "Send a voice note singing the theme of Tetris using only 'la la la'.",
    "Send a photo of your favorite hoodie, jacket, or piece of clothing.",
    "Send a voice note speaking like a GPS navigation system recalculating a route.",
    "Give an acceptance speech for winning the 'World Champion of Napping' trophy.",
    "Send a photo of the nearest clock or watch showing current time.",
    "Send a voice note doing your best sheep, duck, or cow impression.",
    "Write a 1-sentence conspiracy theory about why socks mysteriously vanish in the laundry.",
    "Send a voice note presenting an infomercial for a magic pen that solves all problems.",
    "Send a selfie with an object balanced on your head without letting it fall.",
    "Send a voice note imitating a radio DJ introducing the next mega-hit track.",
    "Type a message using only words that start with the letter 'S'.",
    "Send a voice note singing a 5-second guitar solo using your voice.",
    "Send a screenshot of the last song you added to your music playlist.",
    "Write a horoscope prediction for tomorrow that is oddly specific and funny.",
    "Send a voice note greeting everyone in 4 different languages in a single breath.",
    "Send a photo of the most colorful thing in your room right now.",
    "Send a voice note pretending you are a medieval herald announcing royal decree.",
    "Send a message explaining your job or study using only cooking metaphors.",
    "Send a voice note reciting the alphabet backwards from G to A dramatically.",
    "Send a selfie wearing your sunglasses or headphones in a cool pose.",
    "Send a voice note making a continuous dramatic soap-opera gasp.",
    "Write a message describing what aliens would think if they observed human gym workouts.",
    "Send a photo of your current keyboard or mouse setup.",
    "Send a voice note acting like a chef who just dropped the world's most expensive soufflé.",
    "Send a message challenging anyone in the chat to a game of rock-paper-scissors.",
    "Send a voice note doing your best impression of an echo inside a giant canyon.",
    "Send a photo of something in your room that has the color yellow.",
    "Send a voice note whispering a top-secret classified spy message.",
    "Type out an inspiring quote from a fictional character without saying who said it.",
    "Send a voice note sounding like a commentator during a high-stakes chess championship.",
    "Send a selfie pointing at the screen with an approving nod.",
    "Send a voice note reviewing the ambient background noise in your room.",
    "Write a short 2-sentence manifesto declaring yourself ruler of a small fictional kingdom.",
    "Send a voice note finishing this dare with an enthusiastic 'Mission Accomplished!'.",
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
            InlineKeyboardButton("⚡ Dare", callback_data="tnd_dare"),
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
        return f"🗣️ *Truth for* *{user_name}*:\n\n> {prompt}", "truth"
    elif choice_type == "dare":
        prompt = escape_md(dare_deck.draw())
        return f"⚡ *Dare for* *{user_name}*:\n\n> {prompt}", "dare"
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
        f"🏓 *Pong!* `{latency}ms`\n🎲 *Truth & Dare Party Bot* is Online & Ready to Play! ✨",
        parse_mode="Markdown"
    )


async def helpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorized to use admin commands.")
        return
    admin_help = (
        "👑 *Truth & Dare Bot Admin Control Panel:*\n\n"
        "• `/ping` — Check bot latency & online status\n"
        "• `/tnd` — Start an interactive party round\n"
        "• `/truth` — Draw a Truth question\n"
        "• `/dare` — Draw a Dare challenge\n"
        "• `/random` — Draw a random prompt\n"
        "• `/skip` — Skip to next prompt\n"
        "• `/helpad` — Show this admin help menu"
    )
    await update.message.reply_text(admin_help, parse_mode="Markdown")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎲 *Truth or Dare Party Bot is ready\\!*\n\n"
        "Packed with 200\\+ fun icebreakers, funny stories, and creative challenges\\.\n"
        "Works in DMs & Group chats with both `/` and `.` prefixes\\.\n\n"
        "• `.tnd` or `/tnd` \\- Spin up interactive game board\n"
        "• `.truth` or `/truth` \\- Draw an engaging Truth question\n"
        "• `.dare` or `/dare` \\- Draw a fun Dare challenge\n"
        "• `.random` or `/random` \\- Draw a random prompt\n"
        "• `.skip` or `/skip` \\- Skip and draw another prompt\n"
        "• `.help` or `/help` \\- Show command guide"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 *Truth or Dare Party Game Guide:*\n\n"
        "1\\. Use `.tnd` or `/tnd` to start an interactive game round\\.\n"
        "2\\. Take turns tapping *Truth*, *Dare*, *Random*, or *Skip* buttons\\.\n"
        "3\\. You can also draw directly using `.truth`, `.dare`, `.random`, or `.skip`\\."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def tnd_round_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎲 *Truth or Dare Round Started\\!*\n\n"
        "Choose your challenge below:"
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
        BotCommand("start", "Start the Truth & Dare bot 🎲"),
        BotCommand("help", "Show game commands & rules 📖"),
        BotCommand("tnd", "Start an interactive Truth or Dare round 🎯"),
        BotCommand("truth", "Get a Truth question 🗣️"),
        BotCommand("dare", "Get a Dare challenge ⚡"),
        BotCommand("random", "Get a random Truth or Dare prompt 🎲"),
        BotCommand("skip", "Skip current prompt ⏭️"),
        BotCommand("ping", "Check bot latency & status 🏓"),
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