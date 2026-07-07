import sqlite3

DB_PATH = "app.db"

def init_db():
    
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS courses (
        course_id TEXT PRIMARY KEY,
        title TEXT,
        subject TEXT
    );

    CREATE TABLE IF NOT EXISTS sections (
        section_id TEXT PRIMARY KEY,
        course_id TEXT REFERENCES courses(course_id),
        section_number TEXT,
        instructor TEXT
    );

    CREATE TABLE IF NOT EXISTS seat_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id TEXT,
        open_seats BOOLEAN,
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS watches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id TEXT,
        subject TEXT,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_active_watches(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM watches WHERE active = 1")
    return cur.fetchall()
    
def get_last_snapshot(conn, section_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT open_seats FROM seat_snapshots
        WHERE section_id = ?
        ORDER BY id DESC LIMIT 1
    """, (section_id,))
    row = cur.fetchone()
    return row["open_seats"] if row else None

def save_snapshot(conn, section_id, open_seats):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO seat_snapshots (section_id, open_seats)
        VALUES (?, ?)
    """, (section_id, open_seats))
    conn.commit()
    
def add_watch(section_id, subject):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO watches (section_id, subject) VALUES (?, ?)", (section_id, subject))
    conn.commit()
    conn.close()
    print(f"Now watching section {section_id}.")

def remove_watch(section_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE watches SET active = 0 WHERE section_id = ?", (section_id,))
    conn.commit()
    conn.close()
    print(f"Stopped watching section {section_id}.")