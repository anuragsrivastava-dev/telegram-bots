import os
import re
import uuid
import sqlite3
import httpx
from config import TEMPMAIL_BOT_TOKEN

from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tempmail.db")

# Primary & Fallback Endpoints
MAIL_TM_URL = "https://api.mail.tm"
MAIL_GW_URL = "https://api.mail.gw"
GUERRILLA_URL = "https://api.guerrillamail.com/ajax.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS temp_inboxes (
                user_id INTEGER PRIMARY KEY,
                provider TEXT,
                base_url TEXT,
                email TEXT,
                password TEXT,
                token TEXT,
                last_msg_id TEXT
            )
        """)
        conn.commit()


def escape_md(text: str) -> str:
    """Escapes MarkdownV2 reserved characters."""
    if not text:
        return ""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


def clean_html(raw_html: str) -> str:
    """Strips HTML tags for clean text presentation."""
    if not raw_html:
        return ""
    cleanr = re.compile(r"<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return (
        cleantext.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


def format_as_blockquote(text: str) -> str:
    """Wraps each line in > for Telegram MarkdownV2 blockquote formatting."""
    if not text:
        return "> _No message text body_"
    lines = text.strip().splitlines()
    escaped_lines = [f">{escape_md(line)}" for line in lines if line.strip()]
    return "\n".join(escaped_lines) if escaped_lines else "> _No message text body_"


# ==========================================
# Primary: Mail.tm / Mail.gw Engine
# ==========================================
async def try_create_mail_account(base_url: str) -> tuple[str, str, str] | None:
    async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=True) as client:
        try:
            dom_res = await client.get(f"{base_url}/domains")
            if dom_res.status_code != 200:
                return None
            domains = dom_res.json().get("hydra:member", [])
            if not domains:
                return None

            domain = next((d.get("domain") for d in domains if d.get("isActive", True)), domains[0].get("domain"))
            if not domain:
                return None

            username = f"usr_{uuid.uuid4().hex[:8]}"
            email = f"{username}@{domain}"
            password = uuid.uuid4().hex

            acc_res = await client.post(
                f"{base_url}/accounts",
                json={"address": email, "password": password},
            )
            if acc_res.status_code != 201:
                return None

            token_res = await client.post(
                f"{base_url}/token",
                json={"address": email, "password": password},
            )
            if token_res.status_code != 200:
                return None

            token = token_res.json().get("token")
            return email, password, token
        except Exception:
            return None


async def check_mail_messages(base_url: str, email: str, token: str, last_id: str, bot, user_id: int) -> str:
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=auth_headers, timeout=12, follow_redirects=True) as client:
        try:
            res = await client.get(f"{base_url}/messages")
            if res.status_code != 200:
                return last_id

            messages = res.json().get("hydra:member", [])
            if not messages:
                return last_id

            messages.reverse()

            for msg in messages:
                msg_id = msg.get("id")
                if last_id and msg_id <= last_id:
                    continue

                detail_res = await client.get(f"{base_url}/messages/{msg_id}")
                if detail_res.status_code != 200:
                    continue

                msg_data = detail_res.json()
                sender = msg_data.get("from", {}).get("address", "Unknown")
                subject = msg_data.get("subject", "(No Subject)")
                text_body = (msg_data.get("text") or msg_data.get("intro") or "").strip()[:3500]

                quoted_body = format_as_blockquote(text_body)
                alert = (
                    f"📩 *New Email Received\\!*\n\n"
                    f"• *To:* `{escape_md(email)}`\n"
                    f"• *From:* `{escape_md(sender)}`\n"
                    f"• *Subject:* *{escape_md(subject)}*\n\n"
                    f"{quoted_body}"
                )

                await bot.send_message(
                    chat_id=user_id,
                    text=alert,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                last_id = msg_id

            return last_id
        except Exception:
            return last_id


# ==========================================
# Fallback: Guerrilla Mail Engine
# ==========================================
async def try_create_guerrilla_account() -> tuple[str, str, str] | None:
    async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=True) as client:
        try:
            res = await client.get(f"{GUERRILLA_URL}?f=get_email_address")
            if res.status_code != 200:
                return None
            data = res.json()
            email = data.get("email_addr")
            sid_token = data.get("sid_token")
            if email and sid_token:
                return email, "", sid_token
            return None
        except Exception:
            return None


async def check_guerrilla_messages(email: str, sid_token: str, last_id: str, bot, user_id: int) -> str:
    seq_id = int(last_id) if last_id and last_id.isdigit() else 0
    async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=True) as client:
        try:
            res = await client.get(
                f"{GUERRILLA_URL}?f=check_email&seq={seq_id}&sid_token={sid_token}"
            )
            if res.status_code != 200:
                return str(seq_id)

            messages = res.json().get("list", [])
            for msg in messages:
                mail_id = int(msg.get("mail_id", 0))
                if mail_id <= seq_id or "guerrillamail.com" in msg.get("mail_from", "").lower():
                    if mail_id > seq_id:
                        seq_id = mail_id
                    continue

                detail_res = await client.get(
                    f"{GUERRILLA_URL}?f=fetch_email&email_id={mail_id}&sid_token={sid_token}"
                )
                if detail_res.status_code != 200:
                    continue

                msg_data = detail_res.json()
                sender = msg_data.get("mail_from", "Unknown")
                subject = msg_data.get("mail_subject", "(No Subject)")
                raw_body = msg_data.get("mail_body", "") or msg_data.get("mail_excerpt", "")

                text_body = clean_html(raw_body).strip()[:3500]
                quoted_body = format_as_blockquote(text_body)

                alert = (
                    f"📩 *New Email Received\\!*\n\n"
                    f"• *To:* `{escape_md(email)}`\n"
                    f"• *From:* `{escape_md(sender)}`\n"
                    f"• *Subject:* *{escape_md(subject)}*\n\n"
                    f"{quoted_body}"
                )

                await bot.send_message(
                    chat_id=user_id,
                    text=alert,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                seq_id = mail_id

            return str(seq_id)
        except Exception:
            return str(seq_id)


# ==========================================
# Telegram Bot Handlers
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📬 *Temporary Email Bot is ready\\!*\n\n"
        "• `/newmail` \\- Generate a fresh disposable email address\n"
        "• `/mymail` \\- View your currently active email\n"
        "• `/check` \\- Check for new emails immediately\n"
        "• `/delete` \\- Delete your active inbox\n"
        "• `/help` \\- View command guide\n\n"
        "_All incoming verification emails & OTPs are pushed directly to this chat\\._"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📬 *Temporary Email Bot Help Guide:*\n\n"
        "• `/newmail` \\- Allocates a brand new disposable email address\\.\n"
        "• `/mymail` \\- Displays your current active email address so you can copy it\\.\n"
        "• `/check` \\- Manually refreshes your inbox to fetch new emails immediately\\.\n"
        "• `/delete` \\- Deletes your active inbox\\.\n"
        "• `/help` \\- Shows this help message\\.\n\n"
        "_Note: The bot checks for new incoming emails automatically in the background every 15 seconds\\._"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2)


async def newmail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status_msg = await update.message.reply_text("⚡ Generating temporary address...")

    account_data = None
    provider = ""
    base_url = ""

    # Primary: Mail.tm
    account_data = await try_create_mail_account(MAIL_TM_URL)
    if account_data:
        provider = "mailtm"
        base_url = MAIL_TM_URL

    # Fallback 1: Mail.gw
    if not account_data:
        account_data = await try_create_mail_account(MAIL_GW_URL)
        if account_data:
            provider = "mailgw"
            base_url = MAIL_GW_URL

    # Fallback 2: Guerrilla Mail
    if not account_data:
        account_data = await try_create_guerrilla_account()
        if account_data:
            provider = "guerrilla"
            base_url = GUERRILLA_URL

    if not account_data:
        await status_msg.edit_text("❌ All email providers are currently unreachable. Please retry in a few moments.")
        return

    email, password, token = account_data

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO temp_inboxes (user_id, provider, base_url, email, password, token, last_msg_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, provider, base_url, email, password, token, ""),
        )
        conn.commit()

    escaped_email = escape_md(email)
    await status_msg.edit_text(
        f"📫 *Your Temporary Email:*\n`{escaped_email}`\n\n"
        f"Tap the address above to copy it\\. Incoming emails and OTP codes will be delivered here automatically\\!",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def mymail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT email FROM temp_inboxes WHERE user_id = ?", (user_id,)).fetchone()

    if not row:
        await update.message.reply_text("❌ You don't have an active temporary email. Use `/newmail` to create one.")
        return

    escaped_email = escape_md(row[0])
    await update.message.reply_text(
        f"📫 *Active Temporary Email:*\n`{escaped_email}`\n\nUse `/newmail` to generate a new one\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def delete_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM temp_inboxes WHERE user_id = ?", (user_id,))
        conn.commit()

    await update.message.reply_text("🗑️ Your temporary email has been deleted.")


async def process_user_inbox(user_id: int, provider: str, base_url: str, email: str, token: str, last_msg_id: str, bot) -> str:
    if provider in ["mailtm", "mailgw"]:
        return await check_mail_messages(base_url, email, token, last_msg_id, bot, user_id)
    elif provider == "guerrilla":
        return await check_guerrilla_messages(email, token, last_msg_id, bot, user_id)
    return last_msg_id


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT provider, base_url, email, token, last_msg_id FROM temp_inboxes WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        await update.message.reply_text("❌ No active email found. Use `/newmail` to generate one.")
        return

    provider, base_url, email, token, last_msg_id = row
    status_msg = await update.message.reply_text("🔄 Checking inbox...")
    new_last_id = await process_user_inbox(user_id, provider, base_url, email, token, last_msg_id, context.bot)

    if new_last_id != last_msg_id:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE temp_inboxes SET last_msg_id = ? WHERE user_id = ?",
                (new_last_id, user_id),
            )
            conn.commit()
        await status_msg.delete()
    else:
        await status_msg.edit_text("📭 Inbox is empty. No new messages.")


async def check_inboxes_job(context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT user_id, provider, base_url, email, token, last_msg_id FROM temp_inboxes"
        ).fetchall()

    for user_id, provider, base_url, email, token, last_msg_id in rows:
        new_last_id = await process_user_inbox(user_id, provider, base_url, email, token, last_msg_id, context.bot)
        if new_last_id != last_msg_id:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE temp_inboxes SET last_msg_id = ? WHERE user_id = ?",
                    (new_last_id, user_id),
                )
                conn.commit()


async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show command list & guide"),
        BotCommand("newmail", "Generate a new disposable email"),
        BotCommand("mymail", "Show active disposable email"),
        BotCommand("check", "Check inbox manually"),
        BotCommand("delete", "Delete active disposable email"),
    ])


init_db()

request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(TEMPMAIL_BOT_TOKEN).request(request).post_init(set_commands).build()
app.job_queue.run_repeating(check_inboxes_job, interval=15, first=5)

app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("newmail", newmail))
app.add_handler(CommandHandler("mymail", mymail))
app.add_handler(CommandHandler("check", check_command))
app.add_handler(CommandHandler("delete", delete_mail))