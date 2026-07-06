"""
MedMentor Authentication System
================================
Handles student registration and login.
Only medical college emails allowed (.ac.in / .edu)
"""

import sqlite3
import bcrypt
import jwt
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET", "medmentor-secret-key-2026")
DB_PATH    = "medmentor.db"
TOKEN_EXPIRY_HOURS = 24

# ── Allowed Medical College Email Domains ─────────────────────────────────────
ALLOWED_DOMAINS = [
    # Indian medical colleges
    ".ac.in",
    ".edu.in",
    # International
    ".edu",
    # Specific top medical colleges
    "aiims.edu",
    "manipal.edu",
    "jipmer.edu.in",
    "kmc.edu.in",
    "mahe.edu",
    "amrita.edu",
    "srmc.ac.in",
    "kgmu.org",
]

# ── Allowed Courses ───────────────────────────────────────────────────────────
ALLOWED_COURSES = [
    "MBBS",
    "MD",
    "MS",
    "BDS",
    "MDS",
    "BAMS",
    "BHMS",
    "B.Pharm",
    "M.Pharm",
    "B.Sc Nursing",
    "M.Sc Nursing",
    "BPT",
    "MPT",
    "BMLT",
    "B.Sc Medical",
    "Other Medical Course"
]

# ── Database Setup ────────────────────────────────────────────────────────────
def init_db():
    """Create database and tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name   TEXT    NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            college     TEXT    NOT NULL,
            course      TEXT    NOT NULL,
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
            is_active   INTEGER DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            email       TEXT    NOT NULL,
            full_name   TEXT    NOT NULL,
            login_at    TEXT    DEFAULT CURRENT_TIMESTAMP,
            logout_at   TEXT,
            is_active   INTEGER DEFAULT 1,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)
    conn.commit()
    conn.close()

# ── Email Validation ──────────────────────────────────────────────────────────
def is_valid_medical_email(email: str) -> tuple[bool, str]:
    """
    Check if email is from a valid medical college.
    Returns (is_valid, reason)
    """
    email = email.lower().strip()

    # Basic email format check
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"

    # Reject personal email providers
    personal_domains = [
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "rediffmail.com", "icloud.com", "protonmail.com", "ymail.com"
    ]
    domain = email.split("@")[1]
    if domain in personal_domains:
        return False, "Personal emails not allowed. Please use your college email."

    # Check if it's an allowed academic domain
    for allowed in ALLOWED_DOMAINS:
        if email.endswith(allowed):
            return True, "Valid medical college email"

    return False, "Only medical college emails (.ac.in / .edu) are allowed."

# ── Register ──────────────────────────────────────────────────────────────────
def register_student(full_name: str, email: str, password: str,
                     college: str, course: str) -> dict:
    """Register a new medical student."""

    # Validate inputs
    if not all([full_name, email, password, college, course]):
        return {"success": False, "message": "All fields are required."}

    if len(full_name.strip()) < 2:
        return {"success": False, "message": "Please enter your full name."}

    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}

    # Validate email
    is_valid, reason = is_valid_medical_email(email)
    if not is_valid:
        return {"success": False, "message": reason}

    # Validate course
    if course not in ALLOWED_COURSES:
        return {"success": False, "message": "Please select a valid medical course."}

    # Hash password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Save to database
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (full_name, email, password, college, course) VALUES (?,?,?,?,?)",
            (full_name.strip(), email.lower().strip(),
             hashed.decode('utf-8'), college.strip(), course)
        )
        student_id = cursor.lastrowid
        # Record session
        cursor.execute(
            "INSERT INTO sessions (student_id, email, full_name) VALUES (?,?,?)",
            (student_id, email.lower().strip(), full_name.strip())
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Generate token
        token = generate_token(email.lower().strip(), full_name.strip())
        return {
            "success"    : True,
            "message"    : f"Welcome to MedMentor, {full_name.split()[0]}! 🎉",
            "token"      : token,
            "session_id" : session_id,
            "student"    : {"name": full_name.strip(), "email": email, "course": course, "college": college}
        }

    except sqlite3.IntegrityError:
        return {"success": False, "message": "This email is already registered. Please login."}
    except Exception as e:
        return {"success": False, "message": f"Registration failed: {str(e)}"}

# ── Login ─────────────────────────────────────────────────────────────────────
def login_student(email: str, password: str) -> dict:
    """Login a medical student."""

    if not email or not password:
        return {"success": False, "message": "Email and password are required."}

    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT full_name, email, password, college, course, is_active FROM students WHERE email=?",
            (email.lower().strip(),)
        )
        student = cursor.fetchone()
        conn.close()

        if not student:
            return {"success": False, "message": "Email not found. Please register first."}

        full_name, email_db, hashed_pw, college, course, is_active = student

        if not is_active:
            return {"success": False, "message": "Your account has been deactivated."}

        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), hashed_pw.encode('utf-8')):
            return {"success": False, "message": "Incorrect password. Please try again."}

        # Get student id
        conn2   = sqlite3.connect(DB_PATH)
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT id FROM students WHERE email=?", (email_db,))
        row2 = cursor2.fetchone()
        student_id = row2[0] if row2 else None

        # Record session
        session_id = None
        if student_id:
            cursor2.execute(
                "INSERT INTO sessions (student_id, email, full_name) VALUES (?,?,?)",
                (student_id, email_db, full_name)
            )
            session_id = cursor2.lastrowid
            conn2.commit()
        conn2.close()

        # Generate token
        token = generate_token(email_db, full_name)
        return {
            "success"    : True,
            "message"    : f"Welcome back, {full_name.split()[0]}! 👋",
            "token"      : token,
            "session_id" : session_id,
            "student"    : {"name": full_name, "email": email_db, "course": course, "college": college}
        }

    except Exception as e:
        return {"success": False, "message": f"Login failed: {str(e)}"}

# ── JWT Token ─────────────────────────────────────────────────────────────────
def generate_token(email: str, name: str) -> str:
    """Generate JWT token for authenticated student."""
    payload = {
        "email" : email,
        "name"  : name,
        "exp"   : datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict | None:
    """Verify JWT token. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ── Logout ────────────────────────────────────────────────────────────────────
def logout_student(session_id: int) -> dict:
    """Mark a session as ended by setting logout_at and is_active=0."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET logout_at=CURRENT_TIMESTAMP, is_active=0 WHERE id=?",
            (session_id,)
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# ── Sessions (for admin) ──────────────────────────────────────────────────────
def get_all_sessions() -> list:
    """Return all sessions ordered by most recent login."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        rows   = cursor.execute("""
            SELECT id, student_id, email, full_name,
                   login_at, logout_at, is_active
            FROM sessions
            ORDER BY login_at DESC
            LIMIT 200
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def get_online_count() -> int:
    """Return number of currently active (logged-in) sessions."""
    try:
        conn  = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM sessions WHERE is_active=1").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

# ── Initialize DB on import ───────────────────────────────────────────────────
init_db()
