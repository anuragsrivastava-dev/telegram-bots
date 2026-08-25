# 🤖 Telegram Multi-Bot Backend Suite

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Framework](https://img.shields.io/badge/Framework-python--telegram--bot%20v20%2B-2CA5E0?style=for-the-badge&logo=telegram)](https://python-telegram-bot.org/)
[![AI Engine](https://img.shields.io/badge/AI_Engine-Groq_API_%7C_GPT--OSS--120B-F05032?style=for-the-badge&logo=openai)](https://groq.com/)
[![Database](https://img.shields.io/badge/Database-SQLite3-003B57?style=for-the-badge&logo=sqlite)](https://sqlite.org/)
[![Deployment](https://img.shields.io/badge/Deployment-Wispbyte_Cloud-6C5CE7?style=for-the-badge&logo=serverless)](https://wispbyte.com)

A high-performance, asynchronous multi-bot backend suite engineered in Python. It orchestrates 9+ independent Telegram bots running concurrently within a single `asyncio` event loop process, providing developer tools, AI assistance, gaming hubs, price tracking, disposable email inboxes, and operations monitoring.

---

## 📑 Table of Contents
- [Architecture Overview](#-architecture-overview)
- [Bot Services Deep Dive](#-bot-services-deep-dive)
  - [1. Python Runner & REPL (`bot.py` & `runner.py`)](#1-python-runner--repl-botpy--runnerpy)
  - [2. Meow AI Assistant (`meow_bot.py`)](#2-meow-ai-assistant-meow_botpy)
  - [3. Telegram Gaming Hub (`game_bot.py`)](#3-telegram-gaming-hub-game_botpy)
  - [4. World Clock & GeoOps HUD (`hud_bot.py`)](#4-world-clock--geoops-hud-hud_botpy)
  - [5. Multiplayer Memory Match (`memory_bot.py`)](#5-multiplayer-memory-match-memory_botpy)
  - [6. E-Commerce Price Tracker (`price.py`)](#6-e-commerce-price-tracker-pricepy)
  - [7. Python Learning Quest (`quiz_bot.py`)](#7-python-learning-quest-quiz_botpy)
  - [8. Disposable TempMail Manager (`tempmail_bot.py`)](#8-disposable-tempmail-manager-tempmail_botpy)
  - [9. URL Shortener & Inspector (`shortener_bot.py`)](#9-url-shortener--inspector-shortener_botpy)
  - [10. Party & Icebreaker Bot (`truth_dare_bot.py`)](#10-party--icebreaker-bot-truth_dare_botpy)
- [Database Persistence Layer](#-database-persistence-layer)
- [Installation & Local Setup](#-installation--local-setup)
- [Environment Configuration](#-environment-configuration)
- [Deployment Guide](#-deployment-guide)

---

## ⚡ Architecture Overview

```
                          ┌────────────────────────────┐
                          │   main.py (Master Runner)  │
                          │   Asyncio Polling Engine   │
                          └─────────────┬──────────────┘
                                        │
        ┌──────────────┬────────────────┼────────────────┬──────────────┐
        ▼              ▼                ▼                ▼              ▼
   ┌──────────┐  ┌───────────┐    ┌───────────┐    ┌───────────┐  ┌───────────┐
   │  PyBot   │  │  Meow AI  │    │ Game Hub  │    │  GeoOps   │  │ Price Bot │
   │ (Runner) │  │  (Groq)   │    │  (HTML5)  │    │   (HUD)   │  │ (Scraper) │
   └────┬─────┘  └─────┬─────┘    └─────┬─────┘    └─────┬─────┘  └─────┬─────┘
        │              │                │                │              │
        ▼              ▼                ▼                ▼              ▼
   [Subprocess]   [SQLite DB]      [PeerJS /       [Open-Meteo]   [BS4 / Jina]
   [WASM Bridge]  [meow.db]        Telegram API]   [hud_bot.db]   [tracker.db]
```

### Key Engineering Highlights:
- **Unified Concurrency:** Uses `python-telegram-bot` (v20+ `async/await` native) to initialize and poll updates across all bot instances concurrently with automated error handling and timeout recovery.
- **Sandboxed Execution:** Python runner spawns isolated subprocesses with real-time stdout/stderr streams, dynamic `input()` patching, and strict wall-clock timeouts.
- **Resilient Web Scraping:** E-commerce tracker utilizes dual-engine scraping with fallback proxy routing via Jina AI reader to bypass bot-detection challenges.
- **Zero-Polling Webhook/Polling Compatibility:** Supports local development via long-polling (`drop_pending_updates=True`) and cloud production deployment.

---

## 🤖 Bot Services Deep Dive

### 1. Python Runner & REPL (`bot.py` & `runner.py`)
- **Token:** `PYBOT_TOKEN`
- **Capabilities:**
  - Evaluates expressions and executes full multi-line Python scripts directly in Telegram chats.
  - Interactive input prompts (`input()`) captured via asynchronous stdin pipes.
  - Companion **Python Console WebApp** (`t.me/py_runbot/console`) built with Pyodide WebAssembly.
- **Commands:** `/run <code>`, `/console`, `/stop`, `/ping`

### 2. Meow AI Assistant (`meow_bot.py`)
- **Token:** `MEOW_TOKEN` | **Engine:** Groq API (`openai/gpt-oss-120b`)
- **Capabilities:**
  - Conversational AI companion with persistent multi-turn history and long-term memory extraction.
  - Text transformation pipeline (`/formal`, `/casual`, `/concise`, `/bulletize`, `/proofread`, `/explain`, `/rewrite`, `/fix`, `/summarize`).
  - Multilingual translation with phonetic transliteration guides and direct Persian (`/persian`) output.
  - Automated 28-day infrastructure maintenance reminders via `JobQueue`.
- **Commands:** `/start`, `/help`, `/bots`, `/clear`, `/translate`, `/formal`, `/casual`, `/explain`

### 3. Telegram Gaming Hub (`game_bot.py`)
- **Token:** `GAME_BOT_TOKEN`
- **Capabilities:**
  - Dispatches interactive Telegram Game cards (`InlineQueryResultGame`) into direct messages and group chats.
  - Bridges launch callbacks to static HTML5 games hosted on GitHub Pages.
  - Synchronizes player scores back to Telegram using `setGameScore` and queries global chat rankings via `getGameHighScores`.
- **Database:** `game_scores.db`

### 4. World Clock & GeoOps HUD (`hud_bot.py`)
- **Token:** `HUD_BOT_TOKEN`
- **Capabilities:**
  - Multi-timezone operations dashboard tracking distributed tech hubs (Kolkata, London, San Francisco, Tokyo).
  - Real-time weather intelligence fetched via Open-Meteo REST API.
  - Haversine geodesic distance calculation between international coordinate pairs.
  - SQLite-backed project milestone and sprint release countdowns.
- **Database:** `hud_bot.db` | **Commands:** `/hud`, `/events`, `/add`, `/del`

### 5. Multiplayer Memory Match (`memory_bot.py`)
- **Token:** `MEMORY_BOT_TOKEN`
- **Capabilities:**
  - 2-Player turn-based card-matching game played inside Telegram chat messages using dynamic inline keyboards.
  - Asyncio locking to prevent race conditions during rapid multi-tap card flips.
  - Configurable board grids: `3x4` (6 pairs), `4x4` (8 pairs), `4x5` (10 pairs), and `4x6` (12 pairs).
  - SQLite win-loss ratio and match streak tracking.
- **Database:** `memory_scores.db` | **Commands:** `/match`, `/stats`, `/stop`

### 6. E-Commerce Price Tracker (`price.py`)
- **Token:** `PRICE_BOT_TOKEN`
- **Capabilities:**
  - Monitors product URLs from Amazon and Flipkart for price-drop notifications.
  - BeautifulSoup4 parser with automated fallback to Jina AI proxy rendering when rate-limited.
  - Automated daily price verification at 12:00 PM IST via `JobQueue`.
- **Database:** `tracker.db` | **Commands:** `/track <url>`, `/list`, `/checknow`, `/untrack <id>`

### 7. Python Learning Quest (`quiz_bot.py`)
- **Token:** `QUIZ_BOT_TOKEN`
- **Capabilities:**
  - Interactive Python curriculum structured into bite-sized chapters with progress unlock persistence.
  - Multiple-choice questions with dynamic explanation feedback on every answer.
- **Storage:** `python_course.json`, `python_progress.json` | **Commands:** `/learn`, `/progress`, `/reset`

### 8. Disposable TempMail Manager (`tempmail_bot.py`)
- **Token:** `TEMPMAIL_BOT_TOKEN`
- **Capabilities:**
  - Generates disposable email addresses on demand across multiple provider engines (Mail.tm, Mail.gw, Guerrilla Mail).
  - Background polling task runs every 15 seconds to fetch incoming emails.
  - Automatic OTP verification code parsing with regex extraction.
- **Database:** `tempmail.db` | **Commands:** `/gen`, `/check`, `/otp`, `/delete`

### 9. URL Shortener & Inspector (`shortener_bot.py`)
- **Token:** `SHORTENER_BOT_TOKEN`
- **Capabilities:**
  - Shortens long URLs using clean direct-redirect APIs (`ulvis.net`, `da.gd`) with optional custom aliases.
  - Unwinds redirect hops to reveal destination URLs for link safety inspection.
- **Commands:** `/short <url>`, `/unshort <url>`

### 10. Party & Icebreaker Bot (`truth_dare_bot.py`)
- **Token:** `TND_BOT_TOKEN`
- **Capabilities:**
  - 200+ curated icebreakers, tech dilemmas, creative challenges, and funny story prompts.
  - Auto-refilling zero-repeat shuffled deck cycle engine.
- **Commands:** `/tnd`, `/truth`, `/dare`, `/random`, `/skip`

---

## 💾 Database Persistence Layer

| Database File | Managing Module | Schema / Data Stored |
| :--- | :--- | :--- |
| `meow.db` | `database.py` | Chat history (last 10 messages), long-term memories, user settings, reminders |
| `game_scores.db` | `game_bot.py` | High scores, chat IDs, user names, game keys, Telegram message references |
| `memory_scores.db`| `memory_bot.py` | Wins, total games played, pairs found per chat & user |
| `tracker.db` | `price.py` | Tracked URLs, platforms, titles, target prices, last scraped prices |
| `tempmail.db` | `tempmail_bot.py` | Active inboxes, provider tokens, passwords, last processed email IDs |
| `hud_bot.db` | `hud_bot.py` | Chat milestone titles and target dates |

---

## 🛠️ Installation & Local Setup

### Prerequisites
- Python 3.11 or 3.12
- Git

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/anuragsrivastava-dev/telegram-bots.git
cd telegram-bots

python -m venv .venv

# On Windows:
.\.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Multi-Bot Suite
```bash
python main.py
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the `telegram-bots/` directory:

```env
# Administrator
ADMIN_USER_ID=123456789

# AI Engine
GROQ_API_KEY=gsk_your_groq_api_key_here

# Telegram Bot Tokens (from @BotFather)
PYBOT_TOKEN=123456:ABC-DEF...
MEOW_TOKEN=123456:ABC-DEF...
PRICE_BOT_TOKEN=123456:ABC-DEF...
TEMPMAIL_BOT_TOKEN=123456:ABC-DEF...
SHORTENER_BOT_TOKEN=123456:ABC-DEF...
TND_BOT_TOKEN=123456:ABC-DEF...
MEMORY_BOT_TOKEN=123456:ABC-DEF...
HUD_BOT_TOKEN=123456:ABC-DEF...
GAME_BOT_TOKEN=123456:ABC-DEF...
QUIZ_BOT_TOKEN=123456:ABC-DEF...
```

---

## 🚀 Deployment Guide

### Deployment on Wispbyte Cloud / VPS
1. Push changes to the repository `https://github.com/anuragsrivastava-dev/telegram-bots.git`.
2. Connect your repository to **Wispbyte** or standard cloud host.
3. Configure environment variables in the host control panel.
4. Set execution entrypoint: `python main.py`.
5. The process automatically starts polling with drop-pending updates enabled for clean startup.

---

## 📄 License
This project is open-source and maintained by [anuragsrivastava-dev](https://github.com/anuragsrivastava-dev).
