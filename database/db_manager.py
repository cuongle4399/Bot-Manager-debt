import sqlite3
import os
import hashlib
from datetime import datetime
from config import DATABASE_PATH
from contextlib import contextmanager

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id BIGINT,
                creditor_id BIGINT,
                creditor_name TEXT,
                debtor_id BIGINT,
                debtor_name TEXT,
                amount INTEGER,
                reason TEXT,
                raw_message TEXT,
                created_at DATETIME,
                created_by BIGINT,
                message_id BIGINT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                last_seen DATETIME
            )
        ''')
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN last_seen DATETIME')
        except sqlite3.OperationalError:
            pass
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_id ON transactions(group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users ON transactions(creditor_id, debtor_id)")
        conn.commit()

def find_user_id_by_username(username):
    if not username: return None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE username = ?', (username.lower().replace("@", ""),))
        row = cursor.fetchone()
        return row[0] if row else None

def get_user_id_or_pseudo(username):
    if not username: return None
    username = username.lower().replace("@", "")
    real_id = find_user_id_by_username(username)
    if real_id:
        return real_id
    # Pseudo-ID logic (negative hash)
    return -(int(hashlib.md5(username.encode()).hexdigest()[:12], 16))

def update_user(user_id, username, full_name):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, full_name, last_seen)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username.lower() if username else None, full_name, datetime.now()))
        
        # Đồng bộ hóa công nợ cũ của người dùng này nếu trước đó dùng pseudo-ID (từ username)
        if username:
            pseudo_id = get_user_id_or_pseudo(username)
            cursor.execute("UPDATE transactions SET creditor_id = ? WHERE creditor_id = ?", (user_id, pseudo_id))
            cursor.execute("UPDATE transactions SET debtor_id = ? WHERE debtor_id = ?", (user_id, pseudo_id))
            cursor.execute("UPDATE transactions SET created_by = ? WHERE created_by = ?", (user_id, pseudo_id))
        conn.commit()

def save_transaction(group_id, creditor, debtor, amount, reason, raw_message, created_by, message_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions 
            (group_id, creditor_id, creditor_name, debtor_id, debtor_name, amount, reason, raw_message, created_at, created_by, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (group_id, creditor['id'], creditor['name'], debtor['id'], debtor['name'], 
              amount, reason, raw_message, datetime.now(), created_by, message_id))
        conn.commit()
        return cursor.lastrowid

def get_debts_in_group(group_id):
    with get_db() as conn:
        return conn.execute('SELECT * FROM transactions WHERE group_id = ? ORDER BY id ASC', (group_id,)).fetchall()

def get_transactions_by_user(group_id, user_id):
    """Lấy giao dịch liên quan đến 1 user trong group, lọc bằng SQL để tối ưu hiệu suất."""
    with get_db() as conn:
        return conn.execute('''
            SELECT * FROM transactions 
            WHERE group_id = ? AND (creditor_id = ? OR debtor_id = ?)
            ORDER BY id DESC
        ''', (group_id, user_id, user_id)).fetchall()

def delete_transaction(transaction_id, user_id, is_admin=False):
    with get_db() as conn:
        cursor = conn.cursor()
        if is_admin:
            cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
        else:
            cursor.execute('DELETE FROM transactions WHERE id = ? AND (created_by = ? OR creditor_id = ? OR debtor_id = ?)', 
                           (transaction_id, user_id, user_id, user_id))
        success = cursor.rowcount > 0
        conn.commit()
        return success

def delete_transactions_by_message(message_id, user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE message_id = ? AND created_by = ?', (message_id, user_id))
        count = cursor.rowcount
        conn.commit()
        return count

def get_all_groups():
    with get_db() as conn:
        rows = conn.execute('SELECT DISTINCT group_id FROM transactions').fetchall()
        return [row[0] for row in rows]

def clear_group_data(group_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE group_id = ?', (group_id,))
        count = cursor.rowcount
        conn.commit()
        return count
