# JobTrack — Job Application Tracker

A beginner-friendly Flask + SQLite project for tracking job applications.

## Features
- Dashboard summary: total applications, in progress, interviews and offers
- Add, edit and delete applications
- Search by company, role or location
- Filter by application status
- Track work mode, job URL, applied date, follow-up date, compensation and notes
- SQLite database created automatically on first run
- CSRF protection with Flask-WTF
- Responsive interface

## Run locally (Windows / VS Code)

1. Install Python 3.10+.
2. Open this folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt terminal and run:
   ```cmd
   .venv\Scripts\activate.bat
   ```

5. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

6. Start the app:
   ```bash
   python app.py
   ```

7. Open http://127.0.0.1:5000 in your browser.

The SQLite database `tracker.db` is created automatically. It is intentionally excluded from Git.

## Before deploying
- Set a strong random `SECRET_KEY` environment variable in your hosting provider.
- Do not commit `.env`, `tracker.db`, or secrets.
- SQLite data on some free hosting services may be ephemeral. For a durable public deployment, use a persistent disk or managed database. We'll choose a host/database after local testing.

## Suggested GitHub repository
`job-application-tracker`
