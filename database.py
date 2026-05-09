import sqlite3

DB_NAME = 'helpdesk.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT DEFAULT 'user'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            equipment TEXT,
            cabinet TEXT,
            description TEXT,
            status TEXT DEFAULT 'Відкрита 🔴',
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, full_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?, ?)', (user_id, full_name))
    conn.commit()
    conn.close()

def add_ticket(user_id, equipment, cabinet, description):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tickets (user_id, equipment, cabinet, description) 
        VALUES (?, ?, ?, ?)
    ''', (user_id, equipment, cabinet, description))
    # Отримуємо ID щойно створеної заявки
    ticket_id = cursor.lastrowid 
    conn.commit()
    conn.close()
    return ticket_id

# ДОДАЛИ id у вибірку
def get_user_tickets(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, equipment, cabinet, status FROM tickets WHERE user_id = ? ORDER BY id DESC LIMIT 5', (user_id,))
    tickets = cursor.fetchall()
    conn.close()
    return tickets

def get_all_tickets():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, equipment, cabinet, description, status FROM tickets')
    tickets = cursor.fetchall()
    conn.close()
    return tickets

# НОВА ФУНКЦІЯ: Редагування бази даних (Зміна статусу)
def close_ticket(ticket_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET status = 'Вирішено ✅' WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()

# НОВА ФУНКЦІЯ: Видалення з бази даних
def delete_ticket(ticket_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()
    
if __name__ == '__main__':
    init_db()