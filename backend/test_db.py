from database import get_db_connection

db = get_db_connection()

if db:
    print("SUCCESS: CiviQ Cloud Database Connected!")
    db.close()
else:
    print("FAILED: Database connection not established.")