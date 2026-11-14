import os
import sqlite3
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, g, abort
from flask_wtf.csrf import CSRFProtect

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "tracker.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-before-deploying")
app.config["WTF_CSRF_TIME_LIMIT"] = None
CSRFProtect(app)

STATUSES = ["Wishlist", "Applied", "Assessment", "Interview", "Offer", "Rejected"]
WORK_MODES = ["On-site", "Hybrid", "Remote"]

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            location TEXT DEFAULT '',
            work_mode TEXT DEFAULT 'On-site',
            status TEXT NOT NULL DEFAULT 'Wishlist',
            job_url TEXT DEFAULT '',
            applied_date TEXT DEFAULT '',
            follow_up_date TEXT DEFAULT '',
            salary TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    db.close()

@app.context_processor
def inject_options():
    return {"statuses": STATUSES, "work_modes": WORK_MODES, "today": date.today().isoformat()}

@app.route("/")
def index():
    db = get_db()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = "SELECT * FROM applications WHERE 1=1"
    params = []
    if q:
        query += " AND (company LIKE ? OR role LIKE ? OR location LIKE ?)"
        params.extend([f"%{q}%"] * 3)
    if status in STATUSES:
        query += " AND status = ?"
        params.append(status)
    query += """ ORDER BY
        CASE status WHEN 'Interview' THEN 1 WHEN 'Assessment' THEN 2
        WHEN 'Applied' THEN 3 WHEN 'Offer' THEN 4 WHEN 'Wishlist' THEN 5 ELSE 6 END,
        COALESCE(applied_date, '') DESC, created_at DESC"""
    applications = db.execute(query, params).fetchall()
    counts = {row["status"]: row["total"] for row in db.execute(
        "SELECT status, COUNT(*) AS total FROM applications GROUP BY status"
    ).fetchall()}
    total = sum(counts.values())
    stats = {
        "total": total,
        "active": counts.get("Applied", 0) + counts.get("Assessment", 0) + counts.get("Interview", 0),
        "interviews": counts.get("Interview", 0),
        "offers": counts.get("Offer", 0),
    }
    return render_template("index.html", applications=applications, stats=stats, q=q, selected_status=status)

def validate_form(form):
    company = form.get("company", "").strip()
    role = form.get("role", "").strip()
    status = form.get("status", "Wishlist")
    work_mode = form.get("work_mode", "On-site")
    if not company or not role:
        return "Company and job title are required."
    if status not in STATUSES:
        return "Please choose a valid application status."
    if work_mode not in WORK_MODES:
        return "Please choose a valid work mode."
    return None

def form_values(form):
    return (
        form.get("company", "").strip(),
        form.get("role", "").strip(),
        form.get("location", "").strip(),
        form.get("work_mode", "On-site"),
        form.get("status", "Wishlist"),
        form.get("job_url", "").strip(),
        form.get("applied_date", "").strip(),
        form.get("follow_up_date", "").strip(),
        form.get("salary", "").strip(),
        form.get("notes", "").strip(),
    )

@app.route("/applications/new", methods=["GET", "POST"])
def add_application():
    if request.method == "POST":
        error = validate_form(request.form)
        if error:
            flash(error, "error")
            return render_template("form.html", application=request.form, page_title="Add application")
        db = get_db()
        db.execute("""INSERT INTO applications
            (company, role, location, work_mode, status, job_url, applied_date, follow_up_date, salary, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", form_values(request.form))
        db.commit()
        flash("Application added successfully.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", application={}, page_title="Add application")

@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def edit_application(application_id):
    db = get_db()
    application = db.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    if application is not None:
        application = dict(application)
    if application is None:
        abort(404)
    if request.method == "POST":
        error = validate_form(request.form)
        if error:
            flash(error, "error")
            return render_template("form.html", application=request.form, page_title="Edit application", edit_id=application_id)
        db.execute("""UPDATE applications SET
            company=?, role=?, location=?, work_mode=?, status=?, job_url=?,
            applied_date=?, follow_up_date=?, salary=?, notes=? WHERE id=?""",
            form_values(request.form) + (application_id,))
        db.commit()
        flash("Application updated.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", application=application, page_title="Edit application", edit_id=application_id)

@app.post("/applications/<int:application_id>/delete")
def delete_application(application_id):
    db = get_db()
    db.execute("DELETE FROM applications WHERE id = ?", (application_id,))
    db.commit()
    flash("Application deleted.", "success")
    return redirect(url_for("index"))

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
