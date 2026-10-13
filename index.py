import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, abort
from werkzeug.security import generate_password_hash, check_password_hash

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "templates")
STATIC_DIR = os.path.join(CURRENT_DIR, "static")

import tempfile

# Bulletproof database location: write to OS temp directory (/tmp on Linux/Vercel)
if os.environ.get("VERCEL") or not os.access(CURRENT_DIR, os.W_OK):
    DATABASE = os.path.join(tempfile.gettempdir(), "access2work.db")
else:
    DATABASE = os.path.join(CURRENT_DIR, "access2work.db")

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static"
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "access2work-production-secret-key-2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def init_db():
    try:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    except Exception:
        pass
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('candidate', 'employer')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS candidate_profiles (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        skills TEXT DEFAULT '',
        location TEXT DEFAULT '',
        work_mode TEXT DEFAULT 'Any',
        accessibility_needs TEXT DEFAULT '',
        bio TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS employer_profiles (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        company TEXT DEFAULT '',
        location TEXT DEFAULT '',
        physical_access INTEGER DEFAULT 0,
        digital_access INTEGER DEFAULT 0,
        accessible_recruitment INTEGER DEFAULT 0,
        work_flexibility INTEGER DEFAULT 0,
        staff_awareness INTEGER DEFAULT 0,
        accommodation_process INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT DEFAULT '',
        work_mode TEXT DEFAULT 'Hybrid',
        description TEXT NOT NULL,
        skills TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
        candidate_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'Applied',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(job_id, candidate_id)
    );
    """)
    db.commit()
    db.close()


def get_db():
    if "db" not in g:
        if not os.path.exists(DATABASE):
            init_db()
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to continue.", "info")
                return redirect(url_for("login"))
            if session.get("role") != role:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.context_processor
def inject_user():
    user = None
    if session.get("user_id"):
        user = get_db().execute(
            "SELECT id, name, email, role FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
    return {"current_user": user}


@app.route("/")
def index():
    db = get_db()
    jobs = db.execute("""
        SELECT jobs.*, users.name AS employer_name
        FROM jobs JOIN users ON users.id = jobs.employer_id
        ORDER BY jobs.created_at DESC LIMIT 6
    """).fetchall()
    counts = {
        "jobs": db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "employers": db.execute("SELECT COUNT(*) FROM users WHERE role='employer'").fetchone()[0],
        "candidates": db.execute("SELECT COUNT(*) FROM users WHERE role='candidate'").fetchone()[0],
    }
    return render_template("index.html", jobs=jobs, counts=counts)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        if not name or not email or len(password) < 8 or role not in ("candidate", "employer"):
            flash("Enter your name and email, choose a role, and use a password with at least 8 characters.", "error")
            return render_template("register.html")
        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role)
            )
            uid = cur.lastrowid
            if role == "candidate":
                db.execute("INSERT INTO candidate_profiles (user_id) VALUES (?)", (uid,))
            else:
                db.execute("INSERT INTO employer_profiles (user_id, company) VALUES (?, ?)", (uid, name))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            flash("That email address already has an account. Please sign in.", "error")
            return render_template("register.html")
        session.clear()
        session["user_id"] = uid
        session["role"] = role
        session["name"] = name
        flash("Account created. Welcome to ACCESS2WORK!", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.", "error")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        flash("You are signed in.", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have signed out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    uid, role = session["user_id"], session["role"]
    if role == "candidate":
        profile = db.execute("SELECT * FROM candidate_profiles WHERE user_id=?", (uid,)).fetchone()
        applications = db.execute("""
            SELECT applications.*, jobs.title, jobs.company, jobs.location
            FROM applications JOIN jobs ON jobs.id=applications.job_id
            WHERE applications.candidate_id=? ORDER BY applications.created_at DESC
        """, (uid,)).fetchall()
        jobs = db.execute("""
            SELECT jobs.*, users.name AS employer_name FROM jobs
            JOIN users ON users.id=jobs.employer_id ORDER BY jobs.created_at DESC
        """).fetchall()
        return render_template("candidate_dashboard.html", profile=profile, applications=applications, jobs=jobs)
    profile = db.execute("SELECT * FROM employer_profiles WHERE user_id=?", (uid,)).fetchone()
    jobs = db.execute("SELECT * FROM jobs WHERE employer_id=? ORDER BY created_at DESC", (uid,)).fetchall()
    applicants = db.execute("""
        SELECT applications.id AS application_id, applications.status, applications.created_at,
               users.name AS candidate_name, users.email, jobs.title, jobs.id AS job_id,
               candidate_profiles.skills, candidate_profiles.location AS candidate_location,
               candidate_profiles.work_mode
        FROM applications JOIN users ON users.id=applications.candidate_id
        JOIN jobs ON jobs.id=applications.job_id
        LEFT JOIN candidate_profiles ON candidate_profiles.user_id=users.id
        WHERE jobs.employer_id=? ORDER BY applications.created_at DESC
    """, (uid,)).fetchall()
    score_weights = {"physical_access": 20, "digital_access": 20, "accessible_recruitment": 15,
                     "work_flexibility": 15, "staff_awareness": 15, "accommodation_process": 15}
    score = sum(profile[field] * weight for field, weight in score_weights.items())
    return render_template("employer_dashboard.html", profile=profile, jobs=jobs, applicants=applicants, readiness_score=score)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    uid, role = session["user_id"], session["role"]
    if role == "candidate":
        if request.method == "POST":
            db.execute("""UPDATE candidate_profiles SET skills=?, location=?, work_mode=?,
                          accessibility_needs=?, bio=? WHERE user_id=?""",
                       (request.form.get("skills", "").strip(), request.form.get("location", "").strip(),
                        request.form.get("work_mode", "Any"), request.form.get("accessibility_needs", "").strip(),
                        request.form.get("bio", "").strip(), uid))
            db.commit()
            flash("Your Ability Passport profile has been updated. Skills are self-reported until assessed.", "success")
            return redirect(url_for("dashboard"))
        profile_data = db.execute("SELECT * FROM candidate_profiles WHERE user_id=?", (uid,)).fetchone()
        return render_template("candidate_profile.html", profile=profile_data)
    if request.method == "POST":
        fields = ["physical_access", "digital_access", "accessible_recruitment",
                  "work_flexibility", "staff_awareness", "accommodation_process"]
        values = [1 if request.form.get(field) == "on" else 0 for field in fields]
        db.execute("""UPDATE employer_profiles SET company=?, location=?, physical_access=?,
                      digital_access=?, accessible_recruitment=?, work_flexibility=?,
                      staff_awareness=?, accommodation_process=? WHERE user_id=?""",
                   (request.form.get("company", "").strip(), request.form.get("location", "").strip(),
                    *values, uid))
        db.commit()
        flash("Employer profile and readiness checklist saved.", "success")
        return redirect(url_for("dashboard"))
    profile_data = db.execute("SELECT * FROM employer_profiles WHERE user_id=?", (uid,)).fetchone()
    return render_template("employer_profile.html", profile=profile_data)


@app.route("/jobs")
def job_list():
    jobs = get_db().execute("""
        SELECT jobs.*, users.name AS employer_name FROM jobs
        JOIN users ON users.id=jobs.employer_id ORDER BY jobs.created_at DESC
    """).fetchall()
    return render_template("jobs.html", jobs=jobs)


@app.route("/jobs/create", methods=["GET", "POST"])
@role_required("employer")
def create_job():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "").strip()
        work_mode = request.form.get("work_mode", "Hybrid")
        description = request.form.get("description", "").strip()
        skills = request.form.get("skills", "").strip()
        if not all([title, company, description]):
            flash("Job title, company and description are required.", "error")
            return render_template("create_job.html")
        db = get_db()
        db.execute("""INSERT INTO jobs (employer_id, title, company, location, work_mode, description, skills)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (session["user_id"], title, company, location, work_mode, description, skills))
        db.commit()
        flash("Job posted successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("create_job.html")


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = get_db().execute("""
        SELECT jobs.*, users.name AS employer_name FROM jobs
        JOIN users ON users.id=jobs.employer_id WHERE jobs.id=?
    """, (job_id,)).fetchone()
    if not job:
        abort(404)
    applied = False
    if session.get("role") == "candidate":
        applied = get_db().execute(
            "SELECT 1 FROM applications WHERE job_id=? AND candidate_id=?",
            (job_id, session["user_id"])
        ).fetchone() is not None
    return render_template("job_detail.html", job=job, applied=applied)


@app.route("/jobs/<int:job_id>/apply", methods=["POST"])
@role_required("candidate")
def apply_job(job_id):
    db = get_db()
    if not db.execute("SELECT id FROM jobs WHERE id=?", (job_id,)).fetchone():
        abort(404)
    try:
        db.execute("INSERT INTO applications (job_id, candidate_id) VALUES (?, ?)", (job_id, session["user_id"]))
        db.commit()
        flash("Application submitted. Your profile skills are self-reported unless independently verified.", "success")
    except sqlite3.IntegrityError:
        flash("You have already applied for this job.", "info")
    return redirect(url_for("job_detail", job_id=job_id))


@app.route("/applications/<int:application_id>/status", methods=["POST"])
@role_required("employer")
def update_application_status(application_id):
    status = request.form.get("status", "")
    allowed = {"Reviewing", "Interview", "Hired", "Not selected"}
    if status not in allowed:
        abort(400)
    db = get_db()
    owned = db.execute("""
        SELECT applications.id FROM applications JOIN jobs ON jobs.id=applications.job_id
        WHERE applications.id=? AND jobs.employer_id=?
    """, (application_id, session["user_id"])).fetchone()
    if not owned:
        abort(404)
    db.execute("UPDATE applications SET status=? WHERE id=?", (status, application_id))
    db.commit()
    flash("Application status updated.", "success")
    return redirect(url_for("dashboard"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you requested could not be found."), 404


handler = app
