# Campus Event Management System

Flask + SQLite web application for managing campus events. Built for the Software Engineering PBL project and managed in JIRA.

## Modules
- Event Creation & Scheduling (organizer): create events, check venue availability, add sessions, Workshop/Seminar types
- Event Registration (student): register, ticket number, confirmation, reminder, My Registrations
- Login (supporting): role-based login for Organizer and Student

## Run
1. python3 -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.txt
4. python database.py
5. python app.py
6. Open http://127.0.0.1:5000

## Sample accounts
- Organizer: S101 / org123
- Student: ST201 / stu123, ST202 / stu456, ST203 / stu789

Author: Krish Patel