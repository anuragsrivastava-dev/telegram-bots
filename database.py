import sqlite3

DATABASE = "meow.db"


def get_connection():
    return sqlite3.connect(DATABASE)


def initialize_database():
    with get_connection() as connection:
        cursor = connection.cursor()

        # Short-term conversation history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Long-term memories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                memory TEXT NOT NULL,
                importance INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Reminders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                remind_at TIMESTAMP NOT NULL,
                completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                settings TEXT
            )
        """)
        connection.commit()


# ==========================
# Messages
# ==========================

def get_chat_history(user_id: int):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (user_id,))
        rows = cursor.fetchall()

    rows.reverse()
    return [{"role": role, "content": content} for role, content in rows]


def save_message(user_id: int, role: str, content: str):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO messages (user_id, role, content)
            VALUES (?, ?, ?)
        """, (user_id, role, content))

        # Keep only the newest 10 messages for this user
        cursor.execute("""
            DELETE FROM messages
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 10
            )
        """, (user_id, user_id))
        connection.commit()


def clear_chat_history(user_id: int):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        connection.commit()


# ==========================
# Memories
# ==========================

def save_memory(user_id: int, category: str, memory: str, importance: int):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO memories (user_id, category, memory, importance)
            VALUES (?, ?, ?, ?)
        """, (user_id, category, memory, importance))
        connection.commit()


def get_memories(user_id: int):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, category, memory, importance
            FROM memories
            WHERE user_id = ?
            ORDER BY importance DESC, id DESC
        """, (user_id,))
        return cursor.fetchall()


def get_relevant_memories(user_id: int, limit: int = 20):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT category, memory, importance
            FROM memories
            WHERE user_id = ?
            ORDER BY importance DESC, id DESC
            LIMIT ?
        """, (user_id, limit))
        return cursor.fetchall()


if __name__ == "__main__":
    initialize_database()
    print("✅ Database initialized.")