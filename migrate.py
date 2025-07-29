import sqlite3

with sqlite3.connect('chat.db') as conn:
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN english_level TEXT DEFAULT 'Intermediate'")
        print("✅ 'english_level' column added successfully.")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Already added or error: {e}")
