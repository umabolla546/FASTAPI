import sqlite3

conn = sqlite3.connect('addresses.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM addresses")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
