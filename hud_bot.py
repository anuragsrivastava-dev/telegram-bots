import os
import time
import asyncio
import datetime
import math
import random
import re
import sqlite3
import httpx
from zoneinfo import ZoneInfo

from config import HUD_BOT_TOKEN, ADMIN_USER_ID

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hud_bot.db")

CITY_PROFILES = {
    "hub1": {
        "name": "Kolkata, IN",
        "tz": "Asia/Kolkata",
        "lat": 22.5726,
        "lon": 88.3639,
        "flag": "🇮🇳",
    },
    "hub2": {
        "name": "London, UK",
        "tz": "Europe/London",
        "lat": 51.5074,
        "lon": -0.1278,
        "flag": "🇬🇧",
    },
    "hub3": {
        "name": "San Francisco, US",
        "tz": "America/Los_Angeles",
        "lat": 37.7749,
        "lon": -122.4194,
        "flag": "🇺🇸",
    },
    "hub4": {
        "name": "Tokyo, JP",
        "tz": "Asia/Tokyo",
        "lat": 35.6762,
        "lon": 139.6503,
        "flag": "🇯🇵",
    },
}

DEV_TIPS_NOTES = [
    "Premature optimization is the root of all evil. Keep designs clean and simple first.",
    "Make it work, make it right, make it fast — in that exact order.",
    "Simplicity is prerequisite for reliability. Modularize early, decouple often.",
    "Good code is its own best documentation. Name variables and functions with explicit intent.",
    "Automate repetitive workflows. CI/CD and scripted tooling save hundreds of engineering hours.",
    "Always measure before optimizing. Profile memory and CPU bottlenecks with empirical data.",
    "Designing for failure produces resilient architectures. Build graceful fallbacks.",
    "Small, atomic git commits make code review, bisecting, and rollback effortless.",
    "Code is read far more often than it is written. Optimize for clarity over cleverness.",
    "The fastest code is the code that never runs. Cache intelligently and avoid redundant I/O.",
]


# ----------------------------------------------------
# Database Management
# ----------------------------------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                title TEXT,
                target_date TEXT
            )
            """
        )
        conn.commit()


init_db()


def add_milestone(chat_id: int, title: str, target_date: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO milestones (chat_id, title, target_date) VALUES (?, ?, ?)",
            (chat_id, title, target_date),
        )
        conn.commit()


def get_milestones(chat_id: int) -> list[tuple]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, target_date FROM milestones WHERE chat_id = ? ORDER BY target_date ASC",
            (chat_id,),
        )
        return cursor.fetchall()


def delete_milestone(milestone_id: int, chat_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM milestones WHERE id = ? AND chat_id = ?",
            (milestone_id, chat_id),
        )
        conn.commit()


# ----------------------------------------------------
# Utilities (Math, Weather & Time)
# ----------------------------------------------------
def escape_md(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[int, int]:
    r_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    km = int(r_km * c)
    miles = int(km * 0.621371)
    return km, miles


async def fetch_weather(lat: float, lon: float) -> tuple[str, str]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,is_day",
    }
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            res = await client.get(url, params=params)
            if res.status_code == 200:
                data = res.json().get("current", {})
                temp = round(data.get("temperature_2m", 25))
                code = data.get("weather_code", 0)
                is_day = data.get("is_day", 1)

                if code == 0:
                    condition = "☀️ Clear" if is_day else "🌙 Clear Night"
                elif code in [1, 2, 3]:
                    condition = "⛅ Partly Cloudy"
                elif code in [45, 48]:
                    condition = "🌫️ Foggy"
                elif code in [51, 53, 55, 61, 63, 65, 80, 81]:
                    condition = "🌧️ Rain"
                elif code in [71, 73, 75, 85]:
                    condition = "❄️ Snow"
                elif code in [95, 96, 99]:
                    condition = "⛈️ Thunderstorm"
                else:
                    condition = "🌡️ Moderate"

                return f"{temp}°C", condition
    except Exception:
        pass
    return "N/A", "⛅ Fair"


def format_countdown(target_date_str: str) -> str:
    try:
        target = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
        now = datetime.datetime.now()
        diff = target - now

        if diff.total_seconds() <= 0:
            return "🚀 *Milestone Reached / Release Day\\!*"

        days = diff.days
        hours, rem = divmod(diff.seconds, 3600)
        minutes, _ = divmod(rem, 60)

        parts = []
        if days > 0:
            parts.append(f"`{days}d`")
        if hours > 0 or days > 0:
            parts.append(f"`{hours}h`")
        parts.append(f"`{minutes}m`")

        return " ".join(parts)
    except Exception:
        return "Invalid date"


# ----------------------------------------------------
# UI & Layout Builders
# ----------------------------------------------------
def get_hud_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh Operations HUD", callback_data="hud_refresh"),
            InlineKeyboardButton("⏳ Milestones", callback_data="hud_milestones"),
        ],
        [
            InlineKeyboardButton("💡 Engineering Tip", callback_data="hud_quote"),
            InlineKeyboardButton("➕ Add Milestone", callback_data="hud_add_prompt"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def build_hud_text(chat_id: int) -> str:
    h1 = CITY_PROFILES["hub1"]
    h2 = CITY_PROFILES["hub2"]
    h3 = CITY_PROFILES["hub3"]

    now_h1 = datetime.datetime.now(ZoneInfo(h1["tz"]))
    now_h2 = datetime.datetime.now(ZoneInfo(h2["tz"]))
    now_h3 = datetime.datetime.now(ZoneInfo(h3["tz"]))

    t1_str = now_h1.strftime("%I:%M %p")
    d1_str = now_h1.strftime("%a, %b %d")

    t2_str = now_h2.strftime("%I:%M %p")
    d2_str = now_h2.strftime("%a, %b %d")

    t3_str = now_h3.strftime("%I:%M %p")
    d3_str = now_h3.strftime("%a, %b %d")

    diff_hours_1_2 = (now_h1.utcoffset() - now_h2.utcoffset()).total_seconds() / 3600
    if diff_hours_1_2 >= 0:
        offset_str = f"Kolkata is +{diff_hours_1_2:g}h ahead of London"
    else:
        offset_str = f"London is +{abs(diff_hours_1_2):g}h ahead of Kolkata"

    temp1, cond1 = await fetch_weather(h1["lat"], h1["lon"])
    temp2, cond2 = await fetch_weather(h2["lat"], h2["lon"])
    temp3, cond3 = await fetch_weather(h3["lat"], h3["lon"])

    km_12, miles_12 = calculate_distance(h1["lat"], h1["lon"], h2["lat"], h2["lon"])

    milestones = get_milestones(chat_id)
    if milestones:
        m_id, m_title, m_date = milestones[0]
        cd_str = format_countdown(m_date)
        milestone_section = (
            f"🎯 *Next Target Milestone:*\n"
            f"• *{escape_md(m_title)}* \\(`{escape_md(m_date)}`\\)\n"
            f"  ⏳ Countdown: {cd_str}\n"
        )
    else:
        milestone_section = (
            "🎯 *Project Milestones:* _No active deadlines saved\\._\n"
            "_\\(Add one using `.add <Title> <YYYY-MM-DD>`\\)_\n"
        )

    day_of_year = int(now_h1.strftime("%j"))
    daily_tip = escape_md(DEV_TIPS_NOTES[day_of_year % len(DEV_TIPS_NOTES)])

    lines = [
        "🌐 *GLOBAL OPERATIONS & WORLD CLOCK HUD*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"{h1['flag']} *{escape_md(h1['name'])}* \\(IST / UTC\\+5:30\\)",
        f"• 🕒 `{t1_str}` \\| {escape_md(d1_str)}",
        f"• {escape_md(cond1)} \\(`{escape_md(temp1)}`\\)",
        "",
        f"{h2['flag']} *{escape_md(h2['name'])}* \\(GMT / UTC\\+0\\)",
        f"• 🕒 `{t2_str}` \\| {escape_md(d2_str)}",
        f"• {escape_md(cond2)} \\(`{escape_md(temp2)}`\\)",
        "",
        f"{h3['flag']} *{escape_md(h3['name'])}* \\(PST / UTC\\-8\\)",
        f"• 🕒 `{t3_str}` \\| {escape_md(d3_str)}",
        f"• {escape_md(cond3)} \\(`{escape_md(temp3)}`\\)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📏 *Geodesic Distance (IN ↔ UK):* `{km_12:,} km` \\(`{miles_12:,} mi`\\)",
        f"⏱️ *Timezone Delta:* `{escape_md(offset_str)}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        milestone_section,
        f"💡 *Engineering Wisdom:*\n> _{daily_tip}_",
    ]

    return "\n".join(lines)


# ----------------------------------------------------
# Command Handlers
# ----------------------------------------------------
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    latency = int((time.time() - start_time) * 1000)
    await msg.edit_text(
        f"🏓 *Pong!* `{latency}ms`\n🌐 *GeoOps HUD Bot* is Online & Synchronized!",
        parse_mode="Markdown"
    )


async def helpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorized to use admin commands.")
        return
    admin_help = (
        "👑 *GeoOps HUD Bot Admin Control Panel:*\n\n"
        "• `/ping` — Check bot latency & status\n"
        "• `/hud` — Display live operations dashboard\n"
        "• `/events` — View project milestone countdowns\n"
        "• `/add <title> <YYYY-MM-DD>` — Add project milestone\n"
        "• `/del <id>` — Delete a milestone\n"
        "• `/helpad` — Show this admin help menu"
    )
    await update.message.reply_text(admin_help, parse_mode="Markdown")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌐 *GeoOps World Clock & Operations HUD is ready\\!*\n\n"
        "Track multi\\-timezone clocks, real\\-time weather data, geodesic distances, and sprint milestones\\.\n\n"
        "• `.hud` or `/hud` \\- Display live status dashboard\n"
        "• `.events` or `/events` \\- View & manage milestone countdowns\n"
        "• `.add <title> <YYYY-MM-DD>` \\- Add a new project milestone\n"
        "• `.del <id>` \\- Delete a milestone\n"
        "• `.help` \\- Show command list"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def hud_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = await build_hud_text(chat_id)
    await update.message.reply_text(
        text,
        reply_markup=get_hud_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def add_milestone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n`.add <Title> <YYYY-MM-DD>`\n\n*Example:*\n`.add v2.0 Release Launch 2026-10-15`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    target_date = context.args[-1]
    title = " ".join(context.args[:-1])

    try:
        datetime.datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid date format\\. Please use `YYYY-MM-DD` \\(e\\.g\\. `2026-10-15`\\)\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    add_milestone(chat_id, title, target_date)
    await update.message.reply_text(
        f"✅ *Milestone Saved\\!*\n\n🎯 *Event:* {escape_md(title)}\n📅 *Target Date:* `{target_date}`\n⏳ Countdown: {format_countdown(target_date)}",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def milestones_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    milestones = get_milestones(chat_id)

    if not milestones:
        await update.message.reply_text(
            "⏳ *No milestones saved yet\\!*\n\nAdd one using:\n`.add <Event Title> <YYYY-MM-DD>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    lines = ["⏳ *Upcoming Project Milestones & Countdowns*\n"]
    for m_id, title, date_str in milestones:
        cd = format_countdown(date_str)
        lines.append(
            f"• *{escape_md(title)}* `[ID: {m_id}]`\n"
            f"  📅 Date: `{date_str}`\n"
            f"  ⏳ Countdown: {cd}\n"
        )
    lines.append("_\\(To delete a milestone, use `/del <id>`\\)_")

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to HUD", callback_data="hud_refresh")]])
    await update.message.reply_text("\n".join(lines), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)


async def delete_milestone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "Usage:\n`.del <milestone_id>`\n_\\(Find IDs in `.events`\\)_",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        m_id = int(context.args[0])
        delete_milestone(m_id, chat_id)
        await update.message.reply_text(f"🗑️ Milestone `{m_id}` deleted successfully\\.", parse_mode=ParseMode.MARKDOWN_V2)
    except ValueError:
        await update.message.reply_text("❌ Milestone ID must be a number\\.", parse_mode=ParseMode.MARKDOWN_V2)


async def handle_dot_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if not text.startswith("."):
        return

    parts = text[1:].split()
    command = parts[0].lower().split("@")[0]
    context.args = parts[1:]

    if command == "ping":
        await ping_command(update, context)
    elif command == "helpad":
        await helpad_command(update, context)
    elif command in ["hud", "dashboard", "status", "time", "clock"]:
        await hud_command(update, context)
    elif command in ["add", "addevent", "newevent", "addmilestone"]:
        await add_milestone_command(update, context)
    elif command in ["events", "milestones", "countdowns", "cd"]:
        await milestones_command(update, context)
    elif command in ["del", "delete", "rm"]:
        await delete_milestone_command(update, context)
    elif command in ["start", "help"]:
        await start_command(update, context)


# ----------------------------------------------------
# Inline Button Callbacks
# ----------------------------------------------------
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    data = query.data

    if data == "hud_refresh":
        await query.answer("Refreshing Operations HUD...")
        text = await build_hud_text(chat_id)
        await query.edit_message_text(
            text,
            reply_markup=get_hud_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif data == "hud_milestones":
        await query.answer()
        milestones = get_milestones(chat_id)
        if not milestones:
            text = "⏳ *No milestones saved yet\\!*\n\nUse `.add <Title> <YYYY-MM-DD>` in chat to add your next release target or deadline\\."
        else:
            lines = ["⏳ *Upcoming Project Milestones & Countdowns*\n"]
            for m_id, title, date_str in milestones:
                cd = format_countdown(date_str)
                lines.append(
                    f"• *{escape_md(title)}* `[ID: {m_id}]`\n"
                    f"  📅 Date: `{date_str}`\n"
                    f"  ⏳ Countdown: {cd}\n"
                )
            lines.append("_\\(Delete with `/del <id>`\\)_")
            text = "\n".join(lines)

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to HUD", callback_data="hud_refresh")]])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

    elif data == "hud_quote":
        await query.answer("New tip drawn!")
        tip = escape_md(random.choice(DEV_TIPS_NOTES))
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to HUD", callback_data="hud_refresh")]])
        await query.edit_message_text(
            f"💡 *Engineering Wisdom:*\n\n> _{tip}_",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif data == "hud_add_prompt":
        await query.answer()
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to HUD", callback_data="hud_refresh")]])
        await query.edit_message_text(
            "➕ *To add a project milestone, send this command in chat:*\n\n"
            "`.add <Milestone Title> <YYYY-MM-DD>`\n\n"
            "*Example:*\n"
            "`.add Production v2.0 Launch 2026-11-01`",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def set_commands(application):
    commands = [
        BotCommand("hud", "Display live operations & world clock dashboard 🌐"),
        BotCommand("events", "View project milestone countdowns ⏳"),
        BotCommand("add", "Add a target deadline or milestone ➕"),
        BotCommand("del", "Delete a milestone 🗑️"),
        BotCommand("help", "Show commands guide 📖"),
        BotCommand("ping", "Check bot latency & status ⚡"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e:
        print(f"Notice setting commands in HudBot: {e}")


request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(HUD_BOT_TOKEN).request(request).post_init(set_commands).build()

app.add_handler(CommandHandler(["start", "help"], start_command))
app.add_handler(CommandHandler("ping", ping_command))
app.add_handler(CommandHandler("helpad", helpad_command))
app.add_handler(CommandHandler(["hud", "status", "dashboard"], hud_command))
app.add_handler(CommandHandler(["events", "milestones"], milestones_command))
app.add_handler(CommandHandler("add", add_milestone_command))
app.add_handler(CommandHandler("del", delete_milestone_command))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dot_prefix))
app.add_handler(CallbackQueryHandler(handle_callbacks, pattern=r"^hud_"))