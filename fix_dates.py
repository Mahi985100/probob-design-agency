import sqlite3

db = sqlite3.connect('probob.db')
cursor = db.cursor()
cursor.execute("UPDATE projects SET due_date = '2026-04-14' WHERE id = 1")
cursor.execute("UPDATE projects SET due_date = '2026-04-15' WHERE id = 2")
cursor.execute("UPDATE projects SET due_date = '2026-04-20' WHERE id = 3")
cursor.execute("UPDATE projects SET due_date = '2026-04-25' WHERE id = 4")
cursor.execute("UPDATE projects SET due_date = '2026-04-10' WHERE id = 5")
db.commit()
print('Dates explicitly set for 2026-04 for some projects.')
