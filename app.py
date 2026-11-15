import os
from dotenv import load_dotenv
from datetime import date
from functools import wraps
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, case, or_, text
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-key-change-before-deploying")
app.config["WTF_CSRF_TIME_LIMIT"] = None
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"

database_url = os.environ.get("DATABASE_URL", "").strip()
if database_url:
    # Some providers supply postgres://; SQLAlchemy expects postgresql://.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    # Use psycopg 3 driver explicitly.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # Local development fallback. Render must receive DATABASE_URL.
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "tracker.db")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db = SQLAlchemy(app)
CSRFProtect(app)

STATUSES = ["Wishlist", "Applied", "Assessment", "Interview", "Offer", "Rejected"]
WORK_MODES = ["On-site", "Hybrid", "Remote"]


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    applications = db.relationship("Application", backref="owner", cascade="all, delete-orphan", lazy=True)


class Application(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), default="")
    work_mode = db.Column(db.String(30), default="On-site")
    status = db.Column(db.String(30), nullable=False, default="Wishlist")
    job_url = db.Column(db.Text, default="")
    applied_date = db.Column(db.String(20), default="")
    follow_up_date = db.Column(db.String(20), default="")
    salary = db.Column(db.String(80), default="")
    notes = db.Column(db.String(2000), default="")
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)


with app.app_context():
    db.create_all()


@app.context_processor
def inject_options():
    return {
        "statuses": STATUSES,
        "work_modes": WORK_MODES,
        "today": date.today().isoformat(),
        "current_user_email": session.get("user_email"),
    }


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id") is None:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)
    return wrapped_view


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not email or len(email) > 254 or "@" not in email:
            flash("Enter a valid email address.", "error")
        elif len(password) < 12:
            flash("Use a password with at least 12 characters.", "error")
        elif password != confirm:
            flash("The passwords do not match.", "error")
        elif User.query.filter(func.lower(User.email) == email).first():
            flash("An account with that email already exists. Please sign in.", "error")
        else:
            user = User(email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            session["user_email"] = user.email
            flash("Your account has been created.", "success")
            return redirect(url_for("index"))
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(func.lower(User.email) == email).first()
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Email or password is incorrect.", "error")
        else:
            session.clear()
            session["user_id"] = user.id
            session["user_email"] = user.email
            destination = request.args.get("next", "")
            if not destination.startswith("/") or destination.startswith("//"):
                destination = url_for("index")
            return redirect(destination)
    return render_template("auth.html", mode="login")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = Application.query.filter_by(user_id=user_id)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Application.company.ilike(pattern),
                Application.role.ilike(pattern),
                Application.location.ilike(pattern),
            )
        )
    if status in STATUSES:
        query = query.filter_by(status=status)
    applications = query.order_by(
        case(
            (Application.status == "Interview", 1),
            (Application.status == "Assessment", 2),
            (Application.status == "Applied", 3),
            (Application.status == "Offer", 4),
            (Application.status == "Wishlist", 5),
            else_=6,
        ),
        Application.applied_date.desc(),
        Application.created_at.desc(),
    ).all()

    count_rows = (
        db.session.query(Application.status, func.count(Application.id))
        .filter_by(user_id=user_id)
        .group_by(Application.status)
        .all()
    )
    counts = {name: total for name, total in count_rows}
    stats = {
        "total": sum(counts.values()),
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
    return {
        "company": form.get("company", "").strip(),
        "role": form.get("role", "").strip(),
        "location": form.get("location", "").strip(),
        "work_mode": form.get("work_mode", "On-site"),
        "status": form.get("status", "Wishlist"),
        "job_url": form.get("job_url", "").strip(),
        "applied_date": form.get("applied_date", "").strip(),
        "follow_up_date": form.get("follow_up_date", "").strip(),
        "salary": form.get("salary", "").strip(),
        "notes": form.get("notes", "").strip(),
    }


@app.route("/applications/new", methods=["GET", "POST"])
@login_required
def add_application():
    if request.method == "POST":
        error = validate_form(request.form)
        if error:
            flash(error, "error")
            return render_template("form.html", application=request.form, page_title="Add application")
        application = Application(**form_values(request.form), user_id=session["user_id"])
        db.session.add(application)
        db.session.commit()
        flash("Application added successfully.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", application={}, page_title="Add application")


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
@login_required
def edit_application(application_id):
    application = Application.query.filter_by(id=application_id, user_id=session["user_id"]).first_or_404()
    if request.method == "POST":
        error = validate_form(request.form)
        if error:
            flash(error, "error")
            return render_template("form.html", application=request.form, page_title="Edit application", edit_id=application_id)
        for key, value in form_values(request.form).items():
            setattr(application, key, value)
        db.session.commit()
        flash("Application updated.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", application=application, page_title="Edit application", edit_id=application_id)


@app.post("/applications/<int:application_id>/delete")
@login_required
def delete_application(application_id):
    application = Application.query.filter_by(id=application_id, user_id=session["user_id"]).first_or_404()
    db.session.delete(application)
    db.session.commit()
    flash("Application deleted.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.get("/health")
def health():
    # Lightweight Render health check; database availability is verified too.
    db.session.execute(text("SELECT 1"))
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
