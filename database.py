import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect("campus.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('Organizer', 'Student')),
            email TEXT
        )
    """)

    sample_users = [
        ("S101", "org123", "Organizer", "s101@univ.edu"),
        ("S102", "org456", "Organizer", "s102@univ.edu"),
        ("ST201", "stu123", "Student", "rahul@univ.edu"),
        ("ST202", "stu456", "Student", "priya@univ.edu"),
        ("ST203", "stu789", "Student", "amit@univ.edu"),
    ]
    for username, password, role, email in sample_users:
        cur.execute(
            "INSERT OR IGNORE INTO users (username, password, role, email) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), role, email),
        )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            venue TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            created_by TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            session_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(event_id)
        )
    """)

    existing_cols = [row[1] for row in cur.execute("PRAGMA table_info(events)")]
    for col in ("event_type", "skill_level", "topic"):
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            ticket_number TEXT,
            status TEXT NOT NULL,
            registered_on TEXT NOT NULL,
            UNIQUE (event_id, username),
            FOREIGN KEY (event_id) REFERENCES events(event_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            registration_id INTEGER,
            notification_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_on TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Database ready. All tables created (users, events, sessions, registrations, notifications).")

if __name__ == "__main__":
    init_db()