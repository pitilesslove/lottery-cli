import os
from click.testing import CliRunner
from main import check_pending
from src.db import init_db, DB_FILE, insert_purchase, add_or_update_round, update_ticket_result
from datetime import datetime
import sqlite3

def test_cli():
    print("=== Testing Formatting Strategy ===")
    
    # Backup & Init
    DB_BACKUP = DB_FILE + ".cli_backup.db"
    if os.path.exists(DB_FILE):
        os.rename(DB_FILE, DB_BACKUP)
    init_db()

    try:
        # Mock Round data
        add_or_update_round(1163, "2025-03-15", "2,13,15,16,33,43", 4, True)
        now = datetime.now()
        
        # Test 1등
        insert_purchase(1163, now, "수동", "2, 13, 15, 16, 33, 43")
        update_ticket_result(1, "1등", 2000000000)
        
        # Test 3등
        insert_purchase(1163, now, "수동", "2, 13, 15, 16, 33, 40")
        update_ticket_result(2, "3등", 1500000)

        # Test 낙첨 (similar to user's photo)
        insert_purchase(1163, now, "수동", "2, 12, 13, 17, 18, 25")
        update_ticket_result(3, "낙첨", 0)
        
        insert_purchase(1163, now, "수동", "3, 6, 9, 21, 27, 29")
        update_ticket_result(4, "낙첨", 0)

        insert_purchase(1163, now, "수동", "4, 8, 11, 13, 16, 34")
        update_ticket_result(5, "낙첨", 0)
        
        insert_purchase(1163, now, "자동", "확인필요")
        update_ticket_result(6, "낙첨", 0)

        runner = CliRunner()
        result = runner.invoke(check_pending)
        print(result.output)

    finally:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        if os.path.exists(DB_BACKUP):
            os.rename(DB_BACKUP, DB_FILE)

if __name__ == "__main__":
    test_cli()
