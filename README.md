# JobTrack — Private Flask Job Application Tracker

Flask application with registration, sign-in, sign-out, per-user application isolation, CSRF protection, and PostgreSQL support.

## Local setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 and create an account. Without `DATABASE_URL`, the app uses a local SQLite file for development. On Render, set `DATABASE_URL` to your Neon PostgreSQL connection string.

## Render

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Health check path: `/health`
- Environment variables:
  - `SECRET_KEY`: long random secret (Render can generate this)
  - `DATABASE_URL`: Neon PostgreSQL connection string
  - `COOKIE_SECURE=1`

## Security and data

- Every application query and write is scoped to the signed-in user.
- Passwords are stored as hashes.
- Keep `.env`, database files, and secrets out of GitHub.
- Use HTTPS in production.
- Back up the PostgreSQL database regularly. A free tier is not a substitute for backups.
- This is a personal portfolio project; before production use, add rate limiting, account recovery, monitoring, and tested backup/restore procedures.

## Existing SQLite data

The new PostgreSQL database starts empty. Existing local SQLite records are not automatically copied. Export/import them only after creating a backup and confirming ownership mapping.
