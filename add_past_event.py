import sqlite3

conn = sqlite3.connect("campus.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM events WHERE title = 'Past Orientation'")
if cur.fetchone()[0] == 0:
    cur.execute(
        "INSERT INTO events (title, event_date, venue, capacity, created_by, event_type, topic) "
        "VALUES ('Past Orientation', '2025-01-10', 'Old Hall', 50, 'S101', 'Seminar', 'History')"
    )
    conn.commit()
    print("Past event added for testing.")
else:
    print("Past event already exists.")
conn.close()