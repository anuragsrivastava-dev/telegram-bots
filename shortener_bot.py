import re
import httpx
from config import SHORTENER_BOT_TOKEN

from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

URL_REGEX = re.compile(
    r"https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?",
    re.IGNORECASE,
)


def escape_md(text: str) -> str:
    """Escapes MarkdownV2 reserved characters."""
    if not text:
        return ""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


async def shorten_url(url: str, custom_alias: str | None = None) -> tuple[str | None, str | None]:
    """Shortens a URL using clean direct-redirect APIs (ulvis.net and da.gd)."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=False) as client:
        # 1. Primary Provider: ulvis.net (Clean direct redirect, supports alias)
        try:
            params = {"url": url, "type": "json"}
            if custom_alias:
                params["custom"] = custom_alias

            res = await client.get("https://ulvis.net/API/write/get", params=params)
            if res.status_code == 200:
                data = res.json()
                if data.get("success"):
                    return data.get("data", {}).get("url"), None
                elif "error" in data:
                    if custom_alias:
                        return None, data["error"].get("msg", "Alias already taken or invalid.")
        except Exception:
            pass

        # 2. Fallback Provider: da.gd (Minimalist raw plain text direct 301 API)
        try:
            params = {"url": url}
            if custom_alias:
                params["shorturl"] = custom_alias

            res = await client.get("https://da.gd/s", params=params)
            if res.status_code == 200 and res.text.strip().startswith("http"):
                return res.text.strip(), None
            elif res.status_code == 400 and custom_alias:
                return None, "Custom alias is unavailable."
        except Exception:
            pass

    return None, "All shortening providers are unreachable. Please try again later."


async def expand_url(short_url: str) -> str | None:
    """Follows HTTP redirects to resolve the destination URL."""
    if not short_url.startswith(("http://", "https://")):
        short_url = "https://" + short_url

    async with httpx.AsyncClient(headers=HEADERS, timeout=10, follow_redirects=True) as client:
        try:
            res = await client.head(short_url)
            return str(res.url)
        except Exception:
            try:
                res = await client.get(short_url)
                return str(res.url)
            except Exception:
                return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔗 *Link Shortener Bot is ready\\!*\n\n"
        "• Send any link to shorten it directly\n"
        "• `/short <url> [alias]` \\- Shorten with an optional custom name\n"
        "• `/expand <url>` \\- Reveal target URL behind a short link\n"
        "• `/help` \\- Show command guide"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 *Link Shortener Guide:*\n\n"
        "1\\. *Direct Shorten:* Paste any URL directly into chat\\.\n"
        "2\\. *Custom Name:* `/short https://example.com mylink`\n"
        "3\\. *Inspect Short Link:* `/expand https://ulvis.net/xyz`"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage:\n`/short <url> [custom_alias]`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    url = context.args[0]
    alias = context.args[1] if len(context.args) > 1 else None

    short_link, err = await shorten_url(url, alias)
    if not short_link:
        err_msg = escape_md(err or "Failed to shorten link.")
        await update.message.reply_text(f"❌ Error: {err_msg}", parse_mode=ParseMode.MARKDOWN_V2)
        return

    escaped_short = escape_md(short_link)
    escaped_orig = escape_md(url)
    await update.message.reply_text(
        f"🔗 *Shortened Link:*\n`{escaped_short}`\n\n"
        f"• *Target:* `{escaped_orig}`",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def expand_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage:\n`/expand <short_url>`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    short_url = context.args[0]
    dest = await expand_url(short_url)

    if not dest:
        await update.message.reply_text("❌ Could not resolve destination link.")
        return

    escaped_short = escape_md(short_url)
    escaped_dest = escape_md(dest)
    await update.message.reply_text(
        f"🔍 *Destination Resolved:*\n\n"
        f"• *Short Link:* `{escaped_short}`\n"
        f"• *Target URL:* `{escaped_dest}`",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def handle_direct_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = URL_REGEX.search(text)
    if not match:
        return

    raw_url = match.group(0)
    short_link, err = await shorten_url(raw_url)

    if not short_link:
        await update.message.reply_text("❌ Failed to shorten link. Please try again.")
        return

    escaped_short = escape_md(short_link)
    await update.message.reply_text(
        f"🔗 *Shortened Link:*\n`{escaped_short}`",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show command guide"),
        BotCommand("short", "Shorten URL with optional alias"),
        BotCommand("expand", "Reveal original URL behind a short link"),
    ])


request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(SHORTENER_BOT_TOKEN).request(request).post_init(set_commands).build()

app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("short", short_command))
app.add_handler(CommandHandler("expand", expand_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_url))