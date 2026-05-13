import sqlite3
conn = sqlite3.connect('novel_tts.db')
cur = conn.cursor()

tables = ['characters', 'characters_old', 'sentences', 'chapters', 'progress']
for table in tables:
    try:
        cur.execute(f'DELETE FROM {table}')
        print(f'Cleared {table}')
    except Exception as e:
        print(f'Skip {table}: {e}')

try:
    cur.execute('DELETE FROM sqlite_sequence')
    cur.execute("INSERT INTO sqlite_sequence(name, seq) VALUES('characters', 0)")
    cur.execute("INSERT INTO sqlite_sequence(name, seq) VALUES('chapters', 0)")
    cur.execute("INSERT INTO sqlite_sequence(name, seq) VALUES('sentences', 0)")
except Exception as e:
    print(f'sqlite_sequence: {e}')

conn.commit()

cur.execute('SELECT COUNT(*) FROM characters')
print(f'Characters after clean: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM sentences')
print(f'Sentences after clean: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM chapters')
print(f'Chapters after clean: {cur.fetchone()[0]}')

conn.close()
print('Database cleaned successfully')
