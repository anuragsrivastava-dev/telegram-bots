import json
import logging
import os
import time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import QUIZ_BOT_TOKEN, ADMIN_USER_ID

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COURSE_FILE = os.path.join(BASE_DIR, "python_course.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "python_progress.json")

DEFAULT_COURSE = [
    {
        "id": "ch1_variables",
        "title": "1. Variables & Data Types",
        "icon": "📦",
        "questions": [
            {
                "q": "What will be the output of:\n```python\nx = '10'\ny = '20'\nprint(x + y)\n```",
                "options": ["30", "1020", "TypeError", "'30'"],
                "answer": 1,
                "why": "Strings concatenate! Adding '10' and '20' yields '1020'.",
            },
            {
                "q": "Which variable name is INVALID in Python?",
                "options": ["_score", "user_2", "2nd_player", "myVar"],
                "answer": 2,
                "why": "Variable names cannot start with a number.",
            },
            {
                "q": "What data type does `type(3.14)` return?",
                "options": ["int", "float", "double", "decimal"],
                "answer": 1,
                "why": "Numbers with decimal points are float objects in Python.",
            },
        ],
    },
    {
        "id": "ch2_conditionals",
        "title": "2. Conditionals & Logic",
        "icon": "⚖️",
        "questions": [
            {
                "q": "What is the output?\n```python\na = True\nb = False\nprint(not a or b)\n```",
                "options": ["True", "False", "None", "SyntaxError"],
                "answer": 1,
                "why": "`not True` is False, and `False or False` is False.",
            },
            {
                "q": "What is the correct syntax for 'else if' in Python?",
                "options": ["elseif", "else if", "elif", "elsif"],
                "answer": 2,
                "why": "Python strictly uses `elif`.",
            },
        ],
    },
    {
        "id": "ch3_loops",
        "title": "3. Loops & Iteration",
        "icon": "🔁",
        "questions": [
            {
                "q": "How many numbers does `range(2, 6)` generate?",
                "options": ["3", "4", "5", "6"],
                "answer": 1,
                "why": "It yields [2, 3, 4, 5], which is exactly 4 elements.",
            },
            {
                "q": "Which keyword immediately exits an entire loop?",
                "options": ["break", "pass", "continue", "skip"],
                "answer": 0,
                "why": "`break` terminates the enclosing loop.",
            },
        ],
    },
]


def load_course() -> list:
    if os.path.exists(COURSE_FILE):
        try:
            with open(COURSE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_COURSE
    save_course(DEFAULT_COURSE)
    return DEFAULT_COURSE


def save_course(course_data: list):
    with open(COURSE_FILE, "w", encoding="utf-8") as f:
        json.dump(course_data, f, indent=2, ensure_ascii=False)


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_progress(data: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_user_unlocked_index(user_id: int) -> int:
    course = load_course()
    data = load_progress()
    u_data = data.get(str(user_id), {})
    unlocked_idx = 0

    for idx, ch in enumerate(course):
        ch_id = ch["id"]
        total_q = len(ch["questions"])
        best_score = u_data.get("scores", {}).get(ch_id, 0)

        # 100% required on previous chapter to unlock next
        if total_q > 0 and best_score == total_q:
            unlocked_idx = idx + 1
        else:
            break
    return min(unlocked_idx, max(0, len(course) - 1))


def record_chapter_score(user_id: int, name: str, chapter_id: str, score: int):
    data = load_progress()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"name": name, "scores": {}}
    prev_high = data[uid]["scores"].get(chapter_id, 0)
    data[uid]["scores"][chapter_id] = max(prev_high, score)
    data[uid]["name"] = name
    save_progress(data)


active_sessions: dict[int, dict] = {}


def build_roadmap_markup(user_id: int) -> InlineKeyboardMarkup:
    course = load_course()
    unlocked_max = get_user_unlocked_index(user_id)
    scores = load_progress().get(str(user_id), {}).get("scores", {})
    keyboard = []

    for idx, ch in enumerate(course):
        ch_id = ch["id"]
        total_q = len(ch["questions"])
        user_best = scores.get(ch_id, 0)
        is_perfect = (total_q > 0 and user_best == total_q)
        is_unlocked = (idx <= unlocked_max)

        if is_perfect:
            status = "⭐ COMPLETED"
        elif is_unlocked:
            status = f"🔓 OPEN ({user_best}/{total_q})"
        else:
            status = "🔒 LOCKED"

        btn_text = f"{ch.get('icon', '📘')} {ch['title']} [{status}]"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"py_ch:{user_id}:{idx}")])

    return InlineKeyboardMarkup(keyboard)


def build_question_markup(user_id: int, ch_idx: int, q_idx: int) -> InlineKeyboardMarkup:
    course = load_course()
    ch = course[ch_idx]
    q_data = ch["questions"][q_idx]
    keyboard = []
    row = []

    for opt_idx, opt_text in enumerate(q_data["options"]):
        cb_data = f"py_ans:{user_id}:{ch_idx}:{q_idx}:{opt_idx}"
        row.append(InlineKeyboardButton(text=opt_text, callback_data=cb_data))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    latency = int((time.time() - start_time) * 1000)
    await msg.edit_text(
        f"🏓 *Pong!* `{latency}ms`\n🎓 *Python Quiz Bot* is Online & Ready!",
        parse_mode="Markdown"
    )


async def helpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorized to use admin commands.")
        return
    admin_help = (
        "👑 *Python Quiz Bot Admin Control Panel:*\n\n"
        "• `/ping` — Check bot latency & online status\n"
        "• `/listq` — List all chapters, IDs, and indexed questions\n"
        "• `/addch <id> <icon> <title>` — Add a new chapter\n"
        "• `/delch <id>` — Delete a chapter and its questions\n"
        "• `/addq <id>` — Add a question (multi-line format)\n"
        "• `/delq <id> <index>` — Delete a question by number\n"
        "• `/helpad` — Show this admin help menu"
    )
    await update.message.reply_text(admin_help, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = update.effective_user.id == ADMIN_USER_ID
    help_text = (
        "🐍 *Python Quest Help:*\n\n"
        "• `/py` or `.py` — Open your chapter roadmap\n"
        "• `/help` — View available commands\n\n"
        "📌 *Progression Rule:* Score **100%** on a chapter to unlock the next one!"
    )
    if is_admin:
        help_text += (
            "\n\n👑 *Admin Chapter & Question Tools:*\n"
            "• `/listq` — List all chapters, IDs, and indexed questions\n"
            "• `/addch <id> <icon> <title>` — Add a new chapter\n"
            "• `/delch <id>` — Delete a chapter and its questions\n"
            "• `/addq <id>` — Add a question (multi-line format)\n"
            "• `/delq <id> <index>` — Delete a question by number"
        )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def py_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    course = load_course()

    if not course:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ No chapters available in the curriculum yet! Admins can add chapters using `/addch`.",
            parse_mode="Markdown",
        )
        return

    text = (
        f"🐍 *Python Learning Quest for {user.first_name}!* 🎓\n\n"
        f"Master each chapter with **100% accuracy** to unlock the next chapter.\n\n"
        f"Select an unlocked module below:"
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=build_roadmap_markup(user.id),
        parse_mode="Markdown",
    )


async def list_questions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    course = load_course()
    if not course:
        await update.message.reply_text("📋 Course is currently empty. Use `/addch` to create a chapter.")
        return

    lines = ["📋 *CURRENT PYTHON COURSE CURRICULUM:*\n"]
    for ch in course:
        icon = ch.get("icon", "📘")
        lines.append(f"{icon} *{ch['title']}* (`{ch['id']}`) — `{len(ch['questions'])} Qs`")
        for idx, q_obj in enumerate(ch["questions"], 1):
            short_q = q_obj["q"].split("\n")[0][:45]
            ans_txt = q_obj["options"][q_obj["answer"]]
            lines.append(f"   `{idx}.` {short_q}... *(Ans: {ans_txt})*")
        lines.append("")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def add_chapter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    if not context.args or len(context.args) < 3:
        usage = (
            "⚠️ *Usage:*\n"
            "`/addch <chapter_id> <icon> <Chapter Title>`\n\n"
            "*Example:*\n"
            "`/addch ch4_functions ⚡ 4. Functions & Scope`"
        )
        await update.message.reply_text(usage, parse_mode="Markdown")
        return

    ch_id = context.args[0].strip().lower()
    icon = context.args[1].strip()
    title = " ".join(context.args[2:]).strip()

    course = load_course()
    if any(ch["id"] == ch_id for ch in course):
        await update.message.reply_text(f"❌ Chapter with ID `{ch_id}` already exists!", parse_mode="Markdown")
        return

    new_chapter = {
        "id": ch_id,
        "title": title,
        "icon": icon,
        "questions": []
    }
    course.append(new_chapter)
    save_course(course)

    await update.message.reply_text(
        f"✅ *Chapter Added Successfully!*\n\n"
        f"• *ID:* `{ch_id}`\n"
        f"• *Title:* {icon} {title}\n"
        f"• *Questions:* 0\n\n"
        f"You can now add questions using `/addq {ch_id}`.",
        parse_mode="Markdown",
    )


async def delete_chapter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ *Usage:* `/delch <chapter_id>`", parse_mode="Markdown")
        return

    target_ch_id = context.args[0].strip().lower()
    course = load_course()
    target_ch = next((ch for ch in course if ch["id"] == target_ch_id), None)

    if not target_ch:
        await update.message.reply_text(f"❌ Chapter ID `{target_ch_id}` not found!", parse_mode="Markdown")
        return

    course = [ch for ch in course if ch["id"] != target_ch_id]
    save_course(course)

    # Clean up orphaned scores in progress file
    progress = load_progress()
    for uid in progress:
        if "scores" in progress[uid] and target_ch_id in progress[uid]["scores"]:
            del progress[uid]["scores"][target_ch_id]
    save_progress(progress)

    await update.message.reply_text(
        f"🗑️ Deleted chapter *{target_ch['title']}* (`{target_ch_id}`).",
        parse_mode="Markdown",
    )


async def add_question_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    lines = [line.strip() for line in update.message.text.splitlines() if line.strip()]

    if len(lines) < 7:
        template = (
            "⚠️ *Invalid Format!* Use this template:\n\n"
            "```text\n"
            "/addq ch1_variables\n"
            "Q: What is 2 ** 3 in Python?\n"
            "O1: 6\n"
            "O2: 8\n"
            "O3: 9\n"
            "O4: 5\n"
            "A: 2\n"
            "W: ** is power operator, 2^3 = 8.\n"
            "```"
        )
        await update.message.reply_text(template, parse_mode="Markdown")
        return

    try:
        header_parts = lines[0].split()
        target_ch_id = header_parts[1].lower()
        q_text, options, ans_idx, why_text = "", [], None, ""

        for line in lines[1:]:
            if line.startswith("Q:"):
                q_text = line[2:].strip()
            elif line.startswith(("O1:", "O2:", "O3:", "O4:")):
                options.append(line[3:].strip())
            elif line.startswith("A:"):
                ans_idx = int(line[2:].strip()) - 1
            elif line.startswith("W:"):
                why_text = line[2:].strip()

        if len(options) != 4 or ans_idx is None or not (0 <= ans_idx < 4):
            await update.message.reply_text("❌ Question must have 4 options (O1-O4) and answer (A) must be 1, 2, 3, or 4.")
            return

        course = load_course()
        target_chapter = next((ch for ch in course if ch["id"] == target_ch_id), None)
        if not target_chapter:
            await update.message.reply_text(f"❌ Chapter `{target_ch_id}` not found! Use `/addch` to create it first.", parse_mode="Markdown")
            return

        target_chapter["questions"].append({
            "q": q_text,
            "options": options,
            "answer": ans_idx,
            "why": why_text,
        })
        save_course(course)
        await update.message.reply_text(
            f"✅ Question added to *{target_chapter['title']}* (Total: {len(target_chapter['questions'])} Qs)!",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to parse: `{str(e)}`")


async def delete_question_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ *Usage:*\n`/delq <chapter_id> <question_number>`\n\n*Example:*\n`/delq ch1_variables 2`\n_(Find numbers using `/listq`)_",
            parse_mode="Markdown",
        )
        return

    target_ch_id = context.args[0].strip().lower()
    try:
        q_num = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Question number must be an integer.", parse_mode="Markdown")
        return

    course = load_course()
    target_chapter = next((ch for ch in course if ch["id"] == target_ch_id), None)
    if not target_chapter:
        await update.message.reply_text(f"❌ Chapter `{target_ch_id}` not found!", parse_mode="Markdown")
        return

    q_list = target_chapter["questions"]
    if not (1 <= q_num <= len(q_list)):
        await update.message.reply_text(
            f"❌ Invalid question number `{q_num}`. Chapter `{target_ch_id}` has `{len(q_list)}` question(s).",
            parse_mode="Markdown",
        )
        return

    deleted_q = q_list.pop(q_num - 1)
    save_course(course)

    short_q = deleted_q["q"].split("\n")[0][:40]
    await update.message.reply_text(
        f"🗑️ Deleted Question #{q_num} from *{target_chapter['title']}*:\n`{short_q}...`\n\nRemaining: `{len(q_list)}` questions.",
        parse_mode="Markdown",
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    caller = query.from_user
    data = query.data

    if not data or not data.startswith("py_"):
        return

    parts = data.split(":")
    action, starter_user_id = parts[0], int(parts[1])

    if caller.id != starter_user_id:
        await query.answer("⚠️ Only the person who started this quest can interact!\nType .py to start your own.", show_alert=True)
        return

    course = load_course()

    if action == "py_ch":
        ch_idx = int(parts[2])
        if ch_idx >= len(course):
            await query.answer("Chapter no longer exists.", show_alert=True)
            return

        if ch_idx > get_user_unlocked_index(caller.id):
            prev_ch = course[ch_idx - 1]
            await query.answer(f"🔒 LOCKED!\n\nYou must score 100% on '{prev_ch['title']}' first!", show_alert=True)
            return

        ch = course[ch_idx]
        if not ch["questions"]:
            await query.answer("This chapter has no questions yet! Ask admin to add questions.", show_alert=True)
            return

        active_sessions[caller.id] = {"ch_idx": ch_idx, "q_idx": 0, "score": 0}
        await query.edit_message_text(
            text=f"📖 *{ch['title']}*\nQuestion 1 of {len(ch['questions'])}\n\n{ch['questions'][0]['q']}",
            reply_markup=build_question_markup(caller.id, ch_idx, 0),
            parse_mode="Markdown",
        )
        await query.answer()

    elif action == "py_map":
        await query.edit_message_text(
            text=f"🐍 *Python Learning Quest for {caller.first_name}!* 🎓\n\nSelect an unlocked module below:",
            reply_markup=build_roadmap_markup(caller.id),
            parse_mode="Markdown",
        )
        await query.answer()

    elif action == "py_ans":
        ch_idx, q_idx, chosen_opt = int(parts[2]), int(parts[3]), int(parts[4])
        session = active_sessions.get(caller.id)
        if not session or session.get("ch_idx") != ch_idx or session.get("q_idx") != q_idx:
            await query.answer("This question is completed.")
            return

        if ch_idx >= len(course) or q_idx >= len(course[ch_idx]["questions"]):
            await query.answer("Course content was modified.", show_alert=True)
            return

        ch = course[ch_idx]
        current_q = ch["questions"][q_idx]
        total_q = len(ch["questions"])
        is_correct = (chosen_opt == current_q["answer"])

        if is_correct:
            session["score"] += 1
            feedback = f"✅ Correct!\n\n💡 {current_q['why']}"
        else:
            feedback = f"❌ Incorrect!\n\n💡 {current_q['why']}"

        await query.answer(text=feedback, show_alert=True)
        next_idx = q_idx + 1
        session["q_idx"] = next_idx

        if next_idx < total_q:
            next_q = ch["questions"][next_idx]
            await query.edit_message_text(
                text=f"📖 *{ch['title']}*\nQuestion {next_idx + 1} of {total_q} | Score: `{session['score']}/{next_idx}`\n\n{next_q['q']}",
                reply_markup=build_question_markup(caller.id, ch_idx, next_idx),
                parse_mode="Markdown",
            )
        else:
            final_score = session["score"]
            record_chapter_score(caller.id, caller.first_name, ch["id"], final_score)
            is_perfect = (final_score == total_q)

            if is_perfect:
                next_msg = "🔓 *NEXT CHAPTER UNLOCKED!* 🎉 Mastered!" if ch_idx + 1 < len(course) else "🏆 *ALL CHAPTERS COMPLETED!* 👑"
                btn = InlineKeyboardButton("🗺️ Return to Roadmap", callback_data=f"py_map:{caller.id}")
            else:
                next_msg = f"⚠️ *Need {total_q}/{total_q} to unlock next chapter!*\nYou scored {final_score}/{total_q}."
                btn = InlineKeyboardButton("🔄 Retry Chapter", callback_data=f"py_ch:{caller.id}:{ch_idx}")

            text = f"🏁 *Chapter Finished!* 🏁\n\n📌 *{ch['title']}*\n📊 Score: *{final_score}/{total_q}*\n\n{next_msg}"
            markup = InlineKeyboardMarkup([[btn], [InlineKeyboardButton("🗺️ Chapter Menu", callback_data=f"py_map:{caller.id}")]])
            await query.edit_message_text(text=text, reply_markup=markup, parse_mode="Markdown")
            active_sessions.pop(caller.id, None)


async def handle_dot_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip().lower()
    if text.startswith(".ping"):
        await ping_command(update, context)
    elif text.startswith(".helpad"):
        await helpad_command(update, context)
    elif text.startswith((".py", ".learn", ".course")):
        await py_command(update, context)
    elif text.startswith((".help", ".quizhelp")):
        await help_command(update, context)


async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("py", "Open Python Chapter Quest"),
        BotCommand("help", "Show Python Quest Help"),
        BotCommand("listq", "(Admin) List curriculum and questions"),
        BotCommand("addch", "(Admin) Add a new chapter"),
        BotCommand("delch", "(Admin) Delete a chapter"),
        BotCommand("addq", "(Admin) Add a question"),
        BotCommand("delq", "(Admin) Delete a question"),
    ])


from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

app = ApplicationBuilder().token(QUIZ_BOT_TOKEN).request(request).post_init(set_commands).build()
app.add_handler(CommandHandler("ping", ping_command))
app.add_handler(CommandHandler("helpad", helpad_command))
app.add_handler(CommandHandler(["py", "learn", "course"], py_command))
app.add_handler(CommandHandler(["help", "start"], help_command))

# Admin Curriculum Management Handlers
app.add_handler(CommandHandler("listq", list_questions_command))
app.add_handler(CommandHandler("addch", add_chapter_command))
app.add_handler(CommandHandler("delch", delete_chapter_command))
app.add_handler(CommandHandler("addq", add_question_command))
app.add_handler(CommandHandler("delq", delete_question_command))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dot_prefix))
app.add_handler(CallbackQueryHandler(handle_callback, pattern=r"^py_"))