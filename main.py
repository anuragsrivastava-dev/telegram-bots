import asyncio
import logging
import sys

from telegram.error import TimedOut, NetworkError

from bot import app as python_bot
from meow_bot import app as meow_bot
from price import app as price_bot
from tempmail_bot import app as tempmail_bot
from shortener_bot import app as shortener_bot
from truth_dare_bot import app as tnd_bot
from memory_bot import app as memory_bot
from hud_bot import app as hud_bot
from game_bot import app as game_bot
from quiz_bot import app as quiz_bot

from config import GAME_BOT_TOKEN, QUIZ_BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)


async def global_error_handler(update, context):
    if isinstance(context.error, (TimedOut, NetworkError)):
        logging.warning("Transient network timeout in bot (%s). Handled gracefully.", context.error)
        return
    logging.error("Exception while handling an update:", exc_info=context.error)


# Base list of unique bot instances
bots = [
    python_bot,
    meow_bot,
    price_bot,
    tempmail_bot,
    shortener_bot,
    tnd_bot,
    memory_bot,
    hud_bot,
    game_bot,
]

# Only start quiz_bot as a separate polling service if it has its own distinct token
if QUIZ_BOT_TOKEN and QUIZ_BOT_TOKEN != GAME_BOT_TOKEN:
    bots.append(quiz_bot)


async def main():
    for bot_app in bots:
        bot_app.add_error_handler(global_error_handler)
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(
            drop_pending_updates=True,
            timeout=20,
            bootstrap_retries=5,
        )
        await asyncio.sleep(0.5)

    print("🤖 Python Runner Bot is online...")
    print("🐱 Meow Bot is online...")
    print("💰 Price Bot is online...")
    print("📬 TempMail Bot is online...")
    print("🔗 Shortener Bot is online...")
    print("🎉 Truth & Dare Bot is online...")
    print("🧩 Memory Match Bot is online...")
    print("🌐 LDR HUD & Milestone Bot is online...")
    print("🎮 Heart Catcher Game Bot is online...")
    if QUIZ_BOT_TOKEN != GAME_BOT_TOKEN:
        print("🐍 Python Quiz Quest Bot is online...")
    print("✅ All bots are online and operational!")

    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        print("\n🛑 Stopping bots...")
        for bot_app in bots:
            try:
                if bot_app.updater and bot_app.updater.running:
                    await bot_app.updater.stop()
                if bot_app.running:
                    await bot_app.stop()
                await bot_app.shutdown()
            except Exception:
                pass
        print("👋 All bots shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)