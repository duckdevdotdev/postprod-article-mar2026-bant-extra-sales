import sqlite3
import time
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            call_id TEXT PRIMARY KEY,
            client_phone TEXT,
            audio_url TEXT,
            status TEXT DEFAULT 'PENDING',  -- PENDING, STT_OK, LLM_OK, CRM_OK, ERROR
            transcript TEXT,
            bant_result TEXT,
            created_at INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def create_call_record(call_id, client_phone, audio_url):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO calls (call_id, client_phone, audio_url, created_at) VALUES (?, ?, ?, ?)',
                     (call_id, client_phone, audio_url, int(time.time())))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Идемпотентность: защита от дублей вебхуков
    finally:
        conn.close()

def update_call_state(call_id, status, transcript=None, bant_result=None):
    conn = get_db_connection()
    query = "UPDATE calls SET status = ?"
    params = [status]

    if transcript:
        query += ", transcript = ?"
        params.append(transcript)
    if bant_result:
        query += ", bant_result = ?"
        params.append(bant_result)

    query += " WHERE call_id = ?"
    params.append(call_id)

    conn.execute(query, params)
    conn.commit()
    conn.close()