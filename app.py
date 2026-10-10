import re
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = "campus-events-secret-key"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def db():
    return sqlite3.connect("campus.db")

def get_user(username):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT username, password, role FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def get_user_email(username):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""

def get_event(event_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT event_id, title, event_date, venue, capacity FROM events WHERE event_id = ?", (event_id,))
    row = cur.fetchone()
    conn.close()
    return row

def get_events():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT event_id, title, event_date, venue, capacity, event_type, skill_level, topic "
                "FROM events ORDER BY event_date")
    rows = cur.fetchall()
    events = []
    for r in rows:
        cur.execute("SELECT session_name, start_time, end_time FROM sessions "
                    "WHERE event_id = ? ORDER BY start_time", (r[0],))
        sessions = [f"{s[0]} ({s[1]}-{s[2]})" for s in cur.fetchall()]
        detail = ""
        if r[5] == "Workshop":
            detail = "Skill level: " + (r[6] or "-")
        elif r[5] == "Seminar":
            detail = "Topic: " + (r[7] or "-")
        events.append({"id": r[0], "title": r[1], "date": r[2], "venue": r[3],
                       "capacity": r[4], "type": r[5] or "-", "detail": detail,
                       "sessions": sessions})
    conn.close()
    return events

def get_student_events(username):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT event_id, title, event_date, venue, capacity, event_type FROM events ORDER BY event_date")
    rows = cur.fetchall()
    events = []
    for r in rows:
        cur.execute("SELECT COUNT(*) FROM registrations WHERE event_id = ? AND status = 'Confirmed'", (r[0],))
        taken = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM registrations WHERE event_id = ? AND username = ?", (r[0], username))
        mine = cur.fetchone()[0] > 0
        events.append({"id": r[0], "title": r[1], "date": r[2], "venue": r[3],
                       "type": r[5] or "-", "seats_left": max(r[4] - taken, 0), "registered": mine})
    conn.close()
    return events

def add_notification(username, registration_id, ntype, message):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notifications (username, registration_id, notification_type, message, created_on) "
        "VALUES (?, ?, ?, ?, ?)",
        (username, registration_id, ntype, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()

def generate_reminders(username):
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT r.registration_id, e.title, e.event_date, e.venue "
        "FROM registrations r JOIN events e ON r.event_id = e.event_id "
        "WHERE r.username = ? AND r.status = 'Confirmed' AND e.event_date = ?",
        (username, tomorrow),
    )
    due = cur.fetchall()
    conn.close()
    for reg_id, title, event_date, venue in due:
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM notifications WHERE registration_id = ? AND notification_type = 'Reminder'",
                    (reg_id,))
        already = cur.fetchone()[0] > 0
        conn.close()
        if not already:
            add_notification(username, reg_id, "Reminder",
                             f"Reminder: {title} is tomorrow ({event_date}) at {venue}.")

def get_notifications(username):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT notification_type, message, created_on FROM notifications "
                "WHERE username = ? ORDER BY notification_id DESC LIMIT 5", (username,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_my_registrations(username):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT e.title, e.event_date, e.venue, r.ticket_number, r.status, r.registered_on "
        "FROM registrations r JOIN events e ON r.event_id = e.event_id "
        "WHERE r.username = ? ORDER BY r.registration_id", (username,))
    rows = cur.fetchall()
    conn.close()
    return rows

def validate_event(title, date_str, venue, capacity_str, event_type, skill, topic):
    if not title:
        return "Title is required"
    if len(title) > 100:
        return "Title must be at most 100 characters"
    if not date_str:
        return "Date is required"
    try:
        event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date"
    if event_date < date.today():
        return "Event date cannot be in the past"
    if not venue:
        return "Venue is required"
    if not capacity_str.isdigit() or not (1 <= int(capacity_str) <= 500):
        return "Capacity must be a number between 1 and 500"
    if event_type not in ("Workshop", "Seminar"):
        return "Event type is required"
    if event_type == "Workshop" and not skill:
        return "Skill level is required for a Workshop"
    if event_type == "Seminar" and not topic:
        return "Topic is required for a Seminar"
    return None

def read_sessions(form):
    rows = []
    for n in ("1", "2"):
        name = form.get(f"s{n}_name", "").strip()
        start = form.get(f"s{n}_start", "").strip()
        end = form.get(f"s{n}_end", "").strip()
        if name or start or end:
            rows.append((name, start, end))
    return rows

def validate_sessions(rows):
    if not rows:
        return "At least one session is required"
    for name, start, end in rows:
        if not name or not start or not end:
            return "Session name, start time and end time are required"
        try:
            t1 = datetime.strptime(start, "%H:%M")
            t2 = datetime.strptime(end, "%H:%M")
        except ValueError:
            return "Invalid time format (use HH:MM)"
        if t2 <= t1:
            return "End time must be after start time"
    return None

def venue_is_free(venue, date_str):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM events WHERE LOWER(venue) = LOWER(?) AND event_date = ?",
                (venue, date_str))
    count = cur.fetchone()[0]
    conn.close()
    return count == 0

def validate_registration(event, username, email):
    if not email:
        return "Email is required"
    if not EMAIL_PATTERN.match(email):
        return "Invalid email address"
    event_id, title, event_date, venue, capacity = event
    if datetime.strptime(event_date, "%Y-%m-%d").date() < date.today():
        return "Registration closed"
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM registrations WHERE event_id = ? AND username = ?", (event_id, username))
    if cur.fetchone()[0] > 0:
        conn.close()
        return "Already registered"
    cur.execute("SELECT COUNT(*) FROM registrations WHERE event_id = ? AND status = 'Confirmed'", (event_id,))
    taken = cur.fetchone()[0]
    conn.close()
    if taken >= capacity:
        return "Event is full"
    return None

@app.route("/")
def home():
    if session.get("role") == "Organizer":
        return redirect(url_for("organizer_dashboard"))
    if session.get("role") == "Student":
        return redirect(url_for("student_dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "")

    if not username or not password:
        flash("Username and password are required")
        return redirect(url_for("home"))

    user = get_user(username)
    if user is None or not check_password_hash(user[1], password):
        flash("Invalid username or password")
        return redirect(url_for("home"))

    if user[2] != role:
        flash("Selected role does not match this account")
        return redirect(url_for("home"))

    session["username"] = user[0]
    session["role"] = user[2]
    if user[2] == "Organizer":
        return redirect(url_for("organizer_dashboard"))
    return redirect(url_for("student_dashboard"))

@app.route("/organizer")
def organizer_dashboard():
    if session.get("role") != "Organizer":
        flash("Access denied: only organizers can open this page")
        return redirect(url_for("home"))
    return render_template("organizer.html", username=session["username"], events=get_events())

@app.route("/create_event", methods=["GET", "POST"])
def create_event():
    if session.get("role") != "Organizer":
        flash("Access denied: only organizers can create events")
        return redirect(url_for("home"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        date_str = request.form.get("event_date", "").strip()
        venue = request.form.get("venue", "").strip()
        capacity = request.form.get("capacity", "").strip()
        event_type = request.form.get("event_type", "").strip()
        skill = request.form.get("skill_level", "").strip()
        topic = request.form.get("topic", "").strip()

        error = validate_event(title, date_str, venue, capacity, event_type, skill, topic)
        if error:
            return render_template("create_event.html", error=error, form=request.form)
        date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")

        session_rows = read_sessions(request.form)
        error = validate_sessions(session_rows)
        if error:
            return render_template("create_event.html", error=error, form=request.form)

        if not venue_is_free(venue, date_str):
            return render_template("create_event.html",
                                   error="Venue not available for the selected date",
                                   form=request.form)

        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (title, event_date, venue, capacity, created_by, event_type, skill_level, topic) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, date_str, venue, int(capacity), session["username"], event_type,
             skill if event_type == "Workshop" else None,
             topic if event_type == "Seminar" else None),
        )
        event_id = cur.lastrowid
        for name, start, end in session_rows:
            cur.execute("INSERT INTO sessions (event_id, session_name, start_time, end_time) VALUES (?, ?, ?, ?)",
                        (event_id, name, start, end))
        conn.commit()
        conn.close()
        flash("Event created successfully")
        return redirect(url_for("organizer_dashboard"))

    return render_template("create_event.html", error=None, form={})

@app.route("/student")
def student_dashboard():
    if session.get("role") != "Student":
        flash("Access denied: only students can open this page")
        return redirect(url_for("home"))
    generate_reminders(session["username"])
    return render_template("student.html", username=session["username"],
                           events=get_student_events(session["username"]),
                           notifications=get_notifications(session["username"]))

@app.route("/register/<int:event_id>", methods=["GET", "POST"])
def register_event(event_id):
    if "username" not in session:
        flash("Please log in to register for an event")
        return redirect(url_for("home"))
    if session.get("role") != "Student":
        flash("Access denied: only students can register for events")
        return redirect(url_for("home"))

    event = get_event(event_id)
    if event is None:
        flash("Event not found")
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        error = validate_registration(event, session["username"], email)
        if error:
            return render_template("register.html", event=event, error=error, email=email)

        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO registrations (event_id, username, email, ticket_number, status, registered_on) "
            "VALUES (?, ?, ?, ?, 'Confirmed', ?)",
            (event_id, session["username"], email, "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        reg_id = cur.lastrowid
        ticket = f"TKT-{event_id:03d}-{reg_id:04d}"
        cur.execute("UPDATE registrations SET ticket_number = ? WHERE registration_id = ?", (ticket, reg_id))
        conn.commit()
        conn.close()
        add_notification(session["username"], reg_id, "Confirmation",
                         f"Confirmation sent to {email}: you are registered for {event[1]} on {event[2]} "
                         f"at {event[3]}. Ticket number: {ticket}")
        flash(f"Registration successful. Your ticket number is {ticket}")
        return redirect(url_for("student_dashboard"))

    return render_template("register.html", event=event, error=None,
                           email=get_user_email(session["username"]))

@app.route("/my_registrations")
def my_registrations():
    if "username" not in session:
        flash("Please log in to view your registrations")
        return redirect(url_for("home"))
    if session.get("role") != "Student":
        flash("Access denied: only students can view registrations")
        return redirect(url_for("home"))
    return render_template("my_registrations.html", username=session["username"],
                           rows=get_my_registrations(session["username"]))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

if __name__ == "__main__":
    app.run(debug=True)