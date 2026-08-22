import os
import re
import json
import time
import asyncio
import sqlite3
import requests
from datetime import time as dt_time
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from config import PRICE_BOT_TOKEN, ADMIN_USER_ID

from telegram import Update, BotCommand, MenuButtonCommands
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

SCHEDULED_TIME = dt_time(hour=12, minute=0, second=0, tzinfo=ZoneInfo("Asia/Kolkata"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tracker.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                url TEXT UNIQUE,
                title TEXT,
                last_price REAL
            )
        """)
        conn.commit()


def clean_price(price_val) -> float | None:
    if price_val is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(price_val).replace(",", ""))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def scrape_amazon(url: str):
    try:
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if response.status_code != 200:
            return scrape_via_jina(url, "Amazon")

        soup = BeautifulSoup(response.content, "html.parser")
        title_elem = soup.find("span", {"id": "productTitle"})
        title = title_elem.get_text(strip=True) if title_elem else None
        price = None

        core_price_box = (
            soup.find("div", {"id": "corePriceDisplay_desktop_feature_div"})
            or soup.find("div", {"id": "corePrice_feature_div"})
            or soup.find("div", {"id": "apex_desktop"})
        )
        if core_price_box:
            selling_elem = core_price_box.find("span", class_="priceToPay") or core_price_box.find("span", class_="a-price")
            if selling_elem:
                offscreen = selling_elem.find("span", class_="a-offscreen")
                if offscreen:
                    price = clean_price(offscreen.get_text(strip=True))

        if not price:
            p_to_pay = soup.find("span", class_="priceToPay")
            if p_to_pay:
                offscreen = p_to_pay.find("span", class_="a-offscreen")
                if offscreen:
                    price = clean_price(offscreen.get_text(strip=True))

        if not price or not title:
            return scrape_via_jina(url, "Amazon")

        return title, price
    except Exception:
        return scrape_via_jina(url, "Amazon")


def scrape_flipkart(url: str):
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(url, timeout=15, allow_redirects=True)
        final_url = response.url

        title = None
        price = None

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or script.text)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") == "Product":
                            title = item.get("name", title)
                            offers = item.get("offers", {})
                            if isinstance(offers, list) and offers:
                                offers = offers[0]
                            raw_price = offers.get("price") or offers.get("lowPrice")
                            if raw_price:
                                price = clean_price(raw_price)
                                break
                    if price:
                        break
                except Exception:
                    continue

            if not title:
                title_elem = (
                    soup.find("span", class_="VU-ZEz")
                    or soup.find("span", class_="B_NuCI")
                    or soup.find("h1", class_="PDJ3Or")
                    or soup.find("h1")
                )
                title = title_elem.get_text(strip=True) if title_elem else None

            if not price:
                price_elem = (
                    soup.find("div", class_="Nx9bqj CxhGGd")
                    or soup.find("div", class_="Nx9bqj")
                    or soup.find("div", class_="_30jeq3 _16Jk6d")
                    or soup.find("div", class_="_30jeq3")
                )
                if price_elem:
                    price = clean_price(price_elem.get_text(strip=True))

        if not title or not price:
            return scrape_via_jina(final_url, "Flipkart")

        return title, price
    except Exception:
        return scrape_via_jina(url, "Flipkart")


def scrape_via_jina(url: str, platform_name: str):
    try:
        proxy_url = f"https://r.jina.ai/{url}"
        res = requests.get(
            proxy_url,
            headers={"User-Agent": "Mozilla/5.0", "X-No-Cache": "true"},
            timeout=20,
        )
        if res.status_code != 200:
            return None, None

        text = res.text
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else f"{platform_name} Product"

        price_matches = re.findall(r"(?:₹|INR|\bRs\.?)\s*([\d,]+(?:\.\d{2})?)", text)
        price = None
        for match in price_matches:
            val = clean_price(match)
            if val and val > 10:
                price = val
                break

        return title, price
    except Exception:
        return None, None


def fetch_product_info_sync(url: str):
    url_lower = url.lower()
    if "amazon." in url_lower or "amzn." in url_lower:
        return ("Amazon", *scrape_amazon(url))
    elif "flipkart." in url_lower:
        return ("Flipkart", *scrape_flipkart(url))
    return (None, None, None)


async def fetch_product_info(url: str):
    return await asyncio.to_thread(fetch_product_info_sync, url)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    latency = int((time.time() - start_time) * 1000)
    await msg.edit_text(
        f"🏓 *Pong!* `{latency}ms`\n💰 *Price Tracker Bot* is Online & Tracking! ✨",
        parse_mode="Markdown"
    )


async def helpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorized to use admin commands.")
        return
    admin_help = (
        "👑 *Price Tracker Bot Admin Control Panel:*\n\n"
        "• `/ping` — Check bot latency & online status\n"
        "• `/list` — View your watchlist & trigger live checks\n"
        "• `/remove <ID>` — Stop tracking an item\n"
        "• `/helpad` — Show this admin help menu"
    )
    await update.message.reply_text(admin_help, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "💰 *Price Tracker Bot Help:*\n\n"
        "• Paste any *Amazon* or *Flipkart* link into chat to track it\n"
        "• `/list` or `.list` — View your watchlist & trigger live checks\n"
        "• `/remove <ID>` — Stop tracking an item\n"
        "• `/help` — Show this guide\n\n"
        "⏰ Automated background checks run daily at 12:00 PM IST."
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, platform, title, last_price, url FROM tracked_items WHERE user_id = ?",
            (user_id,),
        )
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("You aren't tracking any products yet.")
        return

    status_msg = await update.message.reply_text(
        f"🔄 *Checking live prices for {len(rows)} item(s)...*",
        parse_mode="Markdown",
    )

    msg = "📋 *Your Monitored Products:*\n\n"

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for item_id, platform, title, last_price, url in rows:
            _, _, live_price = await fetch_product_info(url)
            short_title = title[:40] + "..." if len(title) > 40 else title

            if live_price is not None:
                if last_price and live_price < last_price:
                    diff = last_price - live_price
                    change_str = f"🟢 *(Dropped by ₹{diff:,.2f})*"
                elif last_price and live_price > last_price:
                    diff = live_price - last_price
                    change_str = f"🔴 *(Rose by ₹{diff:,.2f})*"
                else:
                    change_str = "⚪ *(Unchanged)*"

                msg += (
                    f"• *ID:* `{item_id}` | [{platform}] {short_title}\n"
                    f"  *Price:* ₹{live_price:,.2f} {change_str}\n"
                    f"  [View Product]({url})\n\n"
                )
                cursor.execute(
                    "UPDATE tracked_items SET last_price = ? WHERE id = ?",
                    (live_price, item_id),
                )
            else:
                fallback = f"₹{last_price:,.2f}" if last_price else "N/A"
                msg += (
                    f"• *ID:* `{item_id}` | [{platform}] {short_title}\n"
                    f"  *Price:* {fallback} *(Live check failed)*\n"
                    f"  [View Product]({url})\n\n"
                )
            await asyncio.sleep(1)
        conn.commit()

    msg += "To remove an item, type `/remove <ID>`"
    await status_msg.edit_text(
        msg,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify the item ID: `/remove <ID>`", parse_mode="Markdown")
        return

    item_id = context.args[0]
    user_id = update.effective_user.id

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tracked_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        deleted = cursor.rowcount
        conn.commit()

    if deleted > 0:
        await update.message.reply_text(f"✅ Removed item `{item_id}` from your watchlist.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Item ID not found or doesn't belong to you.")


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text.startswith(".ping"):
        await ping_command(update, context)
        return
    elif text.startswith(".helpad"):
        await helpad_command(update, context)
        return
    elif text.startswith(".list"):
        await list_command(update, context)
        return
    elif text.startswith((".help", ".start")):
        await help_command(update, context)
        return

    url_match = re.search(r"(https?://[^\s]+)", text, re.IGNORECASE)
    if not url_match:
        return

    url = url_match.group(1)
    url_lower = url.lower()
    if "amazon." not in url_lower and "amzn." not in url_lower and "flipkart." not in url_lower:
        await update.message.reply_text("Unsupported store. Only Amazon and Flipkart links are supported.")
        return

    status_msg = await update.message.reply_text("🔍 Checking product details...")
    platform, title, price = await fetch_product_info(url)

    if not price:
        await status_msg.edit_text(
            "❌ Could not parse product price. The item might be out of stock, require login, or blocked by verification."
        )
        return

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO tracked_items (user_id, platform, url, title, last_price) VALUES (?, ?, ?, ?, ?)",
                (user_id, platform, url, title, price),
            )
            conn.commit()
            await status_msg.edit_text(
                f"✅ *Tracking Added!*\n\n"
                f"• *Platform:* {platform}\n"
                f"• *Product:* {title}\n"
                f"• *Tracked Price:* ₹{price:,.2f}\n\n"
                f"Daily checks run every day at 12:00 PM IST (Noon).",
                parse_mode="Markdown",
            )
        except sqlite3.IntegrityError:
            await status_msg.edit_text("⚠️ You are already tracking this product link.")


async def daily_price_checker(context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, platform, url, title, last_price FROM tracked_items")
        items = cursor.fetchall()

    for item_id, user_id, platform, url, title, last_price in items:
        _, _, current_price = await fetch_product_info(url)
        if current_price is None:
            continue

        if last_price is not None and current_price < last_price:
            savings = last_price - current_price
            drop_percent = (savings / last_price) * 100
            alert = (
                f"🚨 *PRICE DROP ALERT!*\n\n"
                f"[{platform}] [{title}]({url})\n\n"
                f"• *Old Price:* ₹{last_price:,.2f}\n"
                f"• *New Price:* ₹{current_price:,.2f}\n"
                f"• *You Save:* ₹{savings:,.2f} ({drop_percent:.1f}% OFF)\n\n"
                f"[Click to View Product]({url})"
            )
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=alert,
                    parse_mode="Markdown",
                    disable_web_page_preview=False,
                )
            except Exception:
                pass

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tracked_items SET last_price = ? WHERE id = ?", (current_price, item_id))
            conn.commit()

        await asyncio.sleep(2)


init_db()

async def set_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("list", "View your tracked items"),
        BotCommand("remove", "Remove item by ID"),
        BotCommand("help", "Show price tracker guide"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e:
        print(f"Notice setting commands in PriceBot: {e}")

from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(PRICE_BOT_TOKEN).request(request).post_init(set_commands).build()

app.job_queue.run_daily(
    daily_price_checker,
    time=SCHEDULED_TIME,
)

app.add_handler(CommandHandler(["start", "help"], help_command))
app.add_handler(CommandHandler("ping", ping_command))
app.add_handler(CommandHandler("helpad", helpad_command))
app.add_handler(CommandHandler("list", list_command))
app.add_handler(CommandHandler("remove", remove_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))