import sqlite3

import config

con = sqlite3.connect(config.DB_PATH)
for table in ["employees", "salaries", "customers", "api_keys"]:
    total = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"\n== {table} ({total} dong) ==")
    for row in con.execute(f"SELECT * FROM {table} LIMIT 3"):
        print(row)
con.close()