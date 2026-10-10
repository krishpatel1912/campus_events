import sqlite3
from datetime import datetime

conn = sqlite3.connect("campus.db")
cur = conn.cursor()
cur.execute("SELECT event_id, event_date FROM events")
fixed = 0
for event_id, event_date in cur.fetchall():
    try:
        clean = datetime.strptime(event_date, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        continue
    if clean != event_date:
        cur.execute("UPDATE events SET event_date = ? WHERE event_id = ?", (clean, event_id))
        fixed += 1
conn.commit()
conn.close()
print(f"Dates checked. {fixed} date(s) corrected to YYYY-MM-DD.")