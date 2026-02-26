import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db')
DB_FILE = os.path.join(DB_DIR, 'lottery.db')

def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create rounds table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rounds (
        round_number INTEGER PRIMARY KEY,
        draw_date DATE,
        winning_numbers TEXT,
        bonus_number INTEGER,
        is_drawn BOOLEAN DEFAULT 0
    )
    ''')

    # Create purchases table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_number INTEGER,
        purchase_date DATETIME,
        mode TEXT,
        numbers TEXT,
        cost INTEGER,
        win_amount INTEGER DEFAULT 0,
        win_rank TEXT DEFAULT '추첨 전',
        is_user_checked BOOLEAN DEFAULT 0
    )
    ''')
    
    # Handle migration if is_user_checked is missing
    cursor.execute("PRAGMA table_info(purchases)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'is_user_checked' not in columns:
        cursor.execute("ALTER TABLE purchases ADD COLUMN is_user_checked BOOLEAN DEFAULT 0")

    conn.commit()
    conn.close()

def insert_purchase(round_number: int, purchase_date: datetime, mode: str, numbers: str, cost: int = 1000):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO purchases (round_number, purchase_date, mode, numbers, cost, is_user_checked)
    VALUES (?, ?, ?, ?, ?, 0)
    ''', (round_number, purchase_date.strftime("%Y-%m-%d %H:%M:%S"), mode, numbers, cost))
    
    conn.commit()
    conn.close()

def add_or_update_round(round_number: int, draw_date: str, winning_numbers: str, bonus_number: int, is_drawn: bool = True):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Upsert logic
    cursor.execute('''
    INSERT OR REPLACE INTO rounds (round_number, draw_date, winning_numbers, bonus_number, is_drawn)
    VALUES (?, ?, ?, ?, ?)
    ''', (round_number, draw_date, winning_numbers, bonus_number, is_drawn))
    
    conn.commit()
    conn.close()

def update_winning_result(round_number: int, numbers: str, win_amount: int, win_rank: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Update the winning result based on round number and the specific numbers selected
    cursor.execute('''
    UPDATE purchases
    SET win_amount = ?, win_rank = ?
    WHERE round_number = ? AND numbers = ? AND win_rank = '추첨 전'
    ''', (win_amount, win_rank, round_number, numbers))
    
    conn.commit()
    conn.close()

def get_unchecked_results():
    """
    Returns results that have been drawn but not yet checked by the user.
    Once retrieved, they are immediately marked as checked.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find records where round is drawn, user hasn't checked, and outcome is calculated (not '추첨 전')
    cursor.execute('''
    SELECT p.id, p.win_rank, p.win_amount, p.cost
    FROM purchases p
    JOIN rounds r ON p.round_number = r.round_number
    WHERE r.is_drawn = 1 AND p.is_user_checked = 0 AND p.win_rank != '추첨 전'
    ''')
    
    rows = cursor.fetchall()
    
    total_games = len(rows)
    total_cost = sum(r['cost'] for r in rows)
    total_win = sum(r['win_amount'] for r in rows)
    
    rank_counts = {}
    ids_to_update = []
    
    for row in rows:
        ids_to_update.append(row['id'])
        rank = row['win_rank']
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
    # Mark as checked
    if ids_to_update:
        id_placeholders = ",".join("?" for _ in ids_to_update)
        cursor.execute(f'''
        UPDATE purchases
        SET is_user_checked = 1
        WHERE id IN ({id_placeholders})
        ''', ids_to_update)
    
    conn.commit()
    conn.close()
    
    return {
        "total_games": total_games,
        "total_cost": total_cost,
        "total_win": total_win,
        "rank_counts": rank_counts
    }

def get_all_checked_results():
    """
    Returns aggregated stats over all items the user HAS checked.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT p.win_rank, p.win_amount, p.cost
    FROM purchases p
    WHERE p.is_user_checked = 1 AND p.win_rank != '추첨 전'
    ''')
    
    rows = cursor.fetchall()
    
    total_games = len(rows)
    total_cost = sum(r['cost'] for r in rows)
    total_win = sum(r['win_amount'] for r in rows)
    
    rank_counts = {}
    for row in rows:
        rank = row['win_rank']
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
    conn.close()
    
    return {
        "total_games": total_games,
        "total_cost": total_cost,
        "total_win": total_win,
        "net_profit": total_win - total_cost,
        "rank_counts": rank_counts
    }

def get_round_details(round_number: int):
    """
    Specific details for a given round, including official winning numbers and user's tickets.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM rounds WHERE round_number = ?", (round_number,))
    round_info = cursor.fetchone()
    
    cursor.execute('''
    SELECT numbers, cost, win_amount, win_rank
    FROM purchases
    WHERE round_number = ?
    ORDER BY win_amount DESC
    ''', (round_number,))
    tickets = cursor.fetchall()
    
    conn.close()
    
    return {
        "round_info": dict(round_info) if round_info else None,
        "tickets": [dict(t) for t in tickets]
    }

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 총 지출 금액
    cursor.execute("SELECT SUM(cost) FROM purchases")
    total_cost = cursor.fetchone()[0] or 0
    
    # 총 당첨 금액
    cursor.execute("SELECT SUM(win_amount) FROM purchases WHERE win_rank != '추첨 전' AND win_rank != '낙첨'")
    total_win = cursor.fetchone()[0] or 0
    
    # 미확인 게임 수 (is_user_checked = 0 이면서 최신 라운드 처리 여부 상관 없이 일단 추첨 전인 것 포함)
    cursor.execute("SELECT COUNT(*) FROM purchases WHERE win_rank = '추첨 전'")
    pending_games = cursor.fetchone()[0] or 0
    
    # 최근 10건 내역
    cursor.execute('''
    SELECT round_number, purchase_date, mode, numbers, cost, win_amount, win_rank
    FROM purchases
    ORDER BY purchase_date DESC
    LIMIT 10
    ''')
    recent_history = cursor.fetchall()
    
    conn.close()
    
    return {
        "total_cost": total_cost,
        "total_win": total_win,
        "net_profit": total_win - total_cost,
        "pending_games": pending_games,
        "recent_history": recent_history
    }
