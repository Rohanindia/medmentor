"""
MedMentor Admin System
======================
Handles admin authentication and dashboard operations.
Separate from student auth — uses its own JWT secret.

Credentials (hardcoded):
  username : Rohan
  password : HareKrishna
"""

import sqlite3
import jwt
import os
from datetime import datetime, timedelta, timezone

# ── Config ────────────────────────────────────────────────────────────────────
ADMIN_USERNAME      = "Rohan"
ADMIN_PASSWORD      = "HareKrishna"
ADMIN_SECRET_KEY    = os.environ.get("ADMIN_JWT_SECRET", "medmentor-admin-secret-2026")
ADMIN_TOKEN_EXPIRY  = 12   # hours
DB_PATH             = "medmentor.db"


# ── Admin JWT ─────────────────────────────────────────────────────────────────
def generate_admin_token() -> str:
    """Generate a short-lived admin JWT (separate from student tokens)."""
    payload = {
        "role"     : "admin",
        "username" : ADMIN_USERNAME,
        "exp"      : datetime.now(timezone.utc) + timedelta(hours=ADMIN_TOKEN_EXPIRY),
    }
    return jwt.encode(payload, ADMIN_SECRET_KEY, algorithm="HS256")


def verify_admin_token(token: str) -> dict | None:
    """
    Verify admin JWT token.
    Returns decoded payload dict, or None if invalid / expired.
    """
    try:
        payload = jwt.decode(token, ADMIN_SECRET_KEY, algorithms=["HS256"])
        if payload.get("role") != "admin":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── Admin Login ───────────────────────────────────────────────────────────────
def admin_login(username: str, password: str) -> dict:
    """
    Validate admin credentials (hardcoded).
    Returns { success, token } on success or { success, message } on failure.
    """
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = generate_admin_token()
        return {
            "success"  : True,
            "token"    : token,
            "username" : ADMIN_USERNAME,
            "message"  : "Admin login successful",
        }
    return {"success": False, "message": "Invalid admin credentials"}


# ── DB Helper ─────────────────────────────────────────────────────────────────
def _get_conn():
    """Return a SQLite connection with row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_drug_check_table(conn):
    """Create DRUG_CHECK table if it doesn't exist yet (defensive)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drug_checks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            drug_one   TEXT,
            drug_two   TEXT,
            result     TEXT,
            checked_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


# ── Student Queries ───────────────────────────────────────────────────────────
def get_all_students() -> list[dict]:
    """Return all students with full details (password excluded)."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT id, full_name, email, college, course,
                   created_at, is_active
            FROM students
            ORDER BY id DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def toggle_student_active(student_id: int) -> dict:
    """
    Flip the is_active flag for a student.
    Returns { success, is_active, message }.
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT is_active FROM students WHERE id=?", (student_id,)
        ).fetchone()
        if not row:
            return {"success": False, "message": "Student not found"}

        new_status = 0 if row["is_active"] else 1
        conn.execute(
            "UPDATE students SET is_active=? WHERE id=?", (new_status, student_id)
        )
        conn.commit()
        label = "activated" if new_status else "deactivated"
        return {"success": True, "is_active": bool(new_status),
                "message": f"Student {label} successfully"}
    finally:
        conn.close()


def delete_student(student_id: int) -> dict:
    """Permanently delete a student record."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM students WHERE id=?", (student_id,)
        ).fetchone()
        if not row:
            return {"success": False, "message": "Student not found"}

        conn.execute("DELETE FROM students WHERE id=?", (student_id,))
        conn.commit()
        return {"success": True, "message": "Student deleted successfully"}
    finally:
        conn.close()


# ── Stats ─────────────────────────────────────────────────────────────────────
def get_admin_stats() -> dict:
    """
    Return aggregated dashboard statistics:
      - total, active, inactive student counts
      - registrations today and this calendar week
      - total drug interaction checks (if table exists)
    """
    conn = _get_conn()
    try:
        # Student counts
        total    = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        active   = conn.execute("SELECT COUNT(*) FROM students WHERE is_active=1").fetchone()[0]
        inactive = total - active

        # Today's registrations (SQLite DATE() uses UTC)
        today_count = conn.execute(
            "SELECT COUNT(*) FROM students WHERE DATE(created_at)=DATE('now')"
        ).fetchone()[0]

        # This week's registrations (Mon–Sun ISO week)
        week_count = conn.execute(
            "SELECT COUNT(*) FROM students WHERE strftime('%Y-%W', created_at)=strftime('%Y-%W', 'now')"
        ).fetchone()[0]

        # Drug-check count (optional table)
        _ensure_drug_check_table(conn)
        drug_checks = conn.execute("SELECT COUNT(*) FROM drug_checks").fetchone()[0]

        return {
            "total_students"      : total,
            "active_students"     : active,
            "inactive_students"   : inactive,
            "registrations_today" : today_count,
            "registrations_week"  : week_count,
            "drug_checks_total"   : drug_checks,
        }
    finally:
        conn.close()


def get_drug_checks() -> list[dict]:
    """Return all drug interaction check records."""
    conn = _get_conn()
    try:
        _ensure_drug_check_table(conn)
        rows = conn.execute(
            "SELECT * FROM drug_checks ORDER BY checked_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
