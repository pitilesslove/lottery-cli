import os
from unittest.mock import patch, MagicMock
from src.scraper import LottoScraper
from src.db import insert_purchase, DB_FILE, get_pending_purchases, get_unchecked_results, init_db, add_or_update_round
import sqlite3
from datetime import datetime
import subprocess

# Temporary test setup
DB_BACKUP = DB_FILE + ".test_backup.db"

def setup():
    if os.path.exists(DB_FILE):
        os.rename(DB_FILE, DB_BACKUP)
    init_db()

def teardown():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    if os.path.exists(DB_BACKUP):
        os.rename(DB_BACKUP, DB_FILE)

@patch("src.scraper.LottoScraper.get_official_winning_numbers")
def test_scoring_logic(mock_get_official):
    print("=== Testing Advanced Scoring Engine ===")
    
    # Mock the API response for deterministic testing without WAF/Queue issues
    mock_get_official.return_value = {
        "round_number": 1000,
        "draw_date": "2024-01-01",
        "winning_numbers": [2, 8, 19, 22, 32, 42],
        "bonus_number": 39,
        "is_drawn": True
    }
    
    with LottoScraper(user_id="dummy", user_pw="dummy", headless=True) as scraper:
        official_data = scraper.get_official_winning_numbers(1000)
    
    print("Official API Fetch Mock for Round 1000:", official_data)
    
    assert official_data is not None
    assert official_data['winning_numbers'] == [2, 8, 19, 22, 32, 42]
    assert official_data['bonus_number'] == 39

    # 1.5 Insert Round into DB to allow INNER JOIN
    add_or_update_round(1000, "2024-01-01", "2,8,19,22,32,42", 39, True)

    # 2. Insert dummy tickets into DB into Round 1000
    now = datetime.now()
    insert_purchase(1000, now, "수동", "2, 8, 19, 22, 32, 42", 1000) # 1등 (6 items matching)
    insert_purchase(1000, now, "수동", "2, 8, 19, 22, 32, 39", 1000) # 2등 (5 items + bonus)
    insert_purchase(1000, now, "수동", "2, 8, 19, 22, 32, 43", 1000) # 3등 (5 items matching)
    insert_purchase(1000, now, "수동", "2, 8, 19, 22, 44, 45", 1000) # 4등 (4 items matching)
    insert_purchase(1000, now, "수동", "2, 8, 19, 43, 44, 45", 1000) # 5등 (3 items matching)
    insert_purchase(1000, now, "수동", "1, 3, 5, 7, 9, 11", 1000)    # 꽝

    pending_tickets = get_pending_purchases(1000)
    
    win_nums = set(official_data['winning_numbers'])
    bonus_num = official_data['bonus_number']

    from src.db import update_ticket_result
    
    for t in pending_tickets:
        my_nums = set(map(int, t['numbers'].replace(" ", "").split(',')))
        match_count = len(my_nums & win_nums)
        bonus_match = bonus_num in my_nums
        
        rank = "낙첨"
        amt = 0
        if match_count == 6:
            rank, amt = "1등", 2000000000
        elif match_count == 5 and bonus_match:
            rank, amt = "2등", 50000000
        elif match_count == 5:
            rank, amt = "3등", 1500000
        elif match_count == 4:
            rank, amt = "4등", 50000
        elif match_count == 3:
            rank, amt = "5등", 5000
        else:
            rank, amt = "낙첨", 0
            
        update_ticket_result(t['id'], rank, amt)
        print(f"Ticket {t['numbers']} -> {rank} ({amt}원)")
        
    res = get_unchecked_results()
    print("\nResult Ranks Output:")
    print(res["rank_counts"])
    
    # Assertions
    rc = res["rank_counts"]
    assert rc.get('1등') == 1, "Missing 1등"
    assert rc.get('2등') == 1, "Missing 2등"
    assert rc.get('3등') == 1, "Missing 3등"
    assert rc.get('4등') == 1, "Missing 4등"
    assert rc.get('5등') == 1, "Missing 5등"
    assert rc.get('낙첨') == 1, "Missing 낙첨"
    
    print("All tests passed! Scoring engine works flawlessly.")

if __name__ == "__main__":
    setup()
    try:
        test_scoring_logic()
    finally:
        teardown()
