"""
HealthBridge AI - SQLite Database Management & Data Access Layer
Thread-safe connection handling, parameterized queries, and automatic schema initialization.
"""

import os
import sqlite3
import json
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "healthbridge.db")

@contextmanager
def get_db():
    """Context manager for SQLite connections with row factory."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes all database tables and seeds initial verified knowledge."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Diseases knowledge table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS diseases (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            simple_definition TEXT,
            medical_definition TEXT,
            common_symptoms TEXT,
            possible_causes TEXT,
            risk_factors TEXT,
            general_prevention TEXT,
            common_diagnostic_tests TEXT,
            general_treatment TEXT,
            warning_signs TEXT,
            when_to_seek_doctor TEXT,
            faqs TEXT,
            related_medical_terms TEXT,
            source TEXT,
            source_url TEXT,
            last_updated TEXT
        );
        """)

        # Medical terms table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS medical_terms (
            id TEXT PRIMARY KEY,
            term TEXT NOT NULL,
            category TEXT,
            medical_definition TEXT,
            simple_explanation TEXT,
            very_simple_explanation TEXT,
            tamil_explanation TEXT,
            hindi_explanation TEXT,
            related_terms TEXT,
            source TEXT
        );
        """)

        # Lab tests table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lab_tests (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            what_is_it TEXT,
            why_is_it_performed TEXT,
            what_does_it_measure TEXT,
            what_does_result_represent TEXT,
            important_limitations TEXT,
            source TEXT
        );
        """)

        # User reports table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_filename TEXT NOT NULL,
            secure_filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary_text TEXT,
            status TEXT DEFAULT 'processed',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # User report lab values
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            result_value TEXT,
            reference_range TEXT,
            status TEXT,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
        );
        """)

        # User appointments
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            location TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # User reminders
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            reminder_type TEXT NOT NULL,
            reminder_date TEXT NOT NULL,
            reminder_time TEXT NOT NULL,
            notes TEXT,
            email_notify INTEGER DEFAULT 0,
            is_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # Health timeline events
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # Health claims table (for Fact Checker)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_text TEXT NOT NULL,
            verdict TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            source TEXT NOT NULL
        );
        """)

        # Feedback table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            module TEXT NOT NULL,
            rating INTEGER,
            comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)

        # Indices for fast querying and isolation
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_user ON appointments(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_user ON health_timeline(user_id);")

        seed_knowledge(cursor)

def _str_field(val, default=""):
    """Safely convert a field value that may be list, string, or None to a string."""
    if val is None:
        return default
    if isinstance(val, list):
        return json.dumps(val)
    return str(val)


def seed_knowledge(cursor):
    """Loads curated diseases, medical terms, and lab tests into SQLite."""
    kb_base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "knowledge_base")

    # Seed diseases
    diseases_file = os.path.join(kb_base, "diseases", "diseases_data.json")
    if os.path.exists(diseases_file):
        with open(diseases_file, "r", encoding="utf-8") as f:
            diseases = json.load(f)
            for d in diseases:
                cursor.execute("""
                INSERT OR REPLACE INTO diseases (
                    id, name, simple_definition, medical_definition, common_symptoms,
                    possible_causes, risk_factors, general_prevention, common_diagnostic_tests,
                    general_treatment, warning_signs, when_to_seek_doctor, faqs,
                    related_medical_terms, source, source_url, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d["id"], d["name"],
                    _str_field(d.get("simple_definition")),
                    _str_field(d.get("medical_definition")),
                    json.dumps(d.get("common_symptoms", [])),
                    json.dumps(d.get("possible_causes", [])),
                    json.dumps(d.get("risk_factors", [])),
                    json.dumps(d.get("general_prevention", [])),
                    json.dumps(d.get("common_diagnostic_tests", [])),
                    _str_field(d.get("general_treatment")),
                    _str_field(d.get("warning_signs")),
                    _str_field(d.get("when_to_seek_doctor")),
                    json.dumps(d.get("faqs", [])),
                    json.dumps(d.get("related_medical_terms", [])),
                    _str_field(d.get("source")),
                    _str_field(d.get("source_url")),
                    _str_field(d.get("last_updated"))
                ))

    # Seed medical terms
    terms_file = os.path.join(kb_base, "medical_terms", "medical_terms_data.json")
    if os.path.exists(terms_file):
        with open(terms_file, "r", encoding="utf-8") as f:
            terms = json.load(f)
            for t in terms:
                cursor.execute("""
                INSERT OR REPLACE INTO medical_terms (
                    id, term, category, medical_definition, simple_explanation,
                    very_simple_explanation, tamil_explanation, hindi_explanation,
                    related_terms, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    t["id"], t["term"], t.get("category", "General"),
                    t.get("medical_definition", ""),
                    t.get("simple_explanation", ""),
                    t.get("very_simple_explanation", ""),
                    t.get("tamil_explanation", ""),
                    t.get("hindi_explanation", ""),
                    json.dumps(t.get("related_terms", [])),
                    t.get("source", "")
                ))

    # Seed lab tests
    labs_file = os.path.join(kb_base, "lab_tests", "lab_tests_data.json")
    if os.path.exists(labs_file):
        with open(labs_file, "r", encoding="utf-8") as f:
            labs = json.load(f)
            for l in labs:
                cursor.execute("""
                INSERT OR REPLACE INTO lab_tests (
                    id, name, what_is_it, why_is_it_performed, what_does_it_measure,
                    what_does_result_represent, important_limitations, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    l["id"], l["name"], l.get("what_is_it", ""),
                    l.get("why_is_it_performed", ""),
                    l.get("what_does_it_measure", ""),
                    l.get("what_does_result_represent", ""),
                    l.get("important_limitations", ""),
                    l.get("source", "")
                ))
