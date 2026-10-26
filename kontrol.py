import sqlite3
conn = sqlite3.connect("chat_history.db")
cur = conn.cursor()
cur.execute("SELECT id, title, archived FROM conversations")
for row in cur.fetchall():
    print(row)
conn.close()
