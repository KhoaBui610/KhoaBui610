import sqlite3
import re

DB_NAME = "poc_contacts.db"  

# UNIQUE constraint
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pocs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            UNIQUE(org, name) ON CONFLICT REPLACE
        )
    ''')
    conn.commit()
    conn.close()

# === check if is an email
def is_email(s):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", s))

# Add or update POCs from input
def add_pocs_from_input(raw_input):
    lines = [line.strip() for line in raw_input.strip().split('\n') if line.strip()]
    if len(lines) % 3 != 0:
        print("❌ Error: Input must be in 3-line blocks (Name, Email/Phone, Phone/Org).")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    for i in range(0, len(lines), 3):
        name = lines[i]
        line2 = lines[i + 1]
        line3 = lines[i + 2]

        email = line2 if is_email(line2) else None
        phone, org = None, None

        if '\t' in line3:
            parts = line3.split('\t')
            if is_email(line2):  # line2 = email, line3 = phone + org
                phone, org = parts[0].strip(), parts[1].strip()
            else:  # line2 = phone, line3 = org
                phone = line2
                org = parts[1].strip()
        else:
            if is_email(line2):
                org = line3
            else:
                phone = line2
                org = line3

        # Insert or update record (based on UNIQUE(org, name))
        c.execute('''
            INSERT INTO pocs (org, name, email, phone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(org, name) DO UPDATE SET
                email=excluded.email,
                phone=excluded.phone
        ''', (org, name, email, phone))

        print(f"✅ Saved: {name} ({org}) | {email or 'No email'} | {phone or 'No phone'}")

    conn.commit()
    conn.close()

# Retrieve POCs for specific org 
def get_pocs_by_org(org):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, email, phone FROM pocs WHERE org = ?", (org,))
    results = c.fetchall()
    conn.close()

    if results:
        return [{
            'name': name,
            'email': email or 'N/A',
            'phone': phone or 'N/A'
        } for name, email, phone in results]
    else:
        return []

# Show all POCs in the db
def show_all_pocs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT org, name, email, phone FROM pocs ORDER BY org, name")
    results = c.fetchall()
    conn.close()

    if not results:
        print("📭 No POCs found in the database.")
        return

    print("\n📋 All POCs:\n")
    for org, name, email, phone in results:
        print(f"[{org}]\n  {name}\n  {email or 'N/A'}\n  {phone or 'N/A'}\n")

# Delete POC by org + name 
def delete_poc(org, name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM pocs WHERE org = ? AND name = ?", (org, name))
    conn.commit()
    conn.close()
    print(f"🗑️ Deleted: {name} from {org}")

# Run standalone
if __name__ == "__main__":
    init_db()
    print("Paste your POC entries (3 lines per contact, press Enter twice to finish):")
    input_lines = []
    while True:
        line = input()
        if line.strip() == '':
            break
        input_lines.append(line)

    raw_input = '\n'.join(input_lines)
    add_pocs_from_input(raw_input)

    print("\n---\nDo you want to view all saved POCs? (y/n)")
    if input().lower() == 'y':
        show_all_pocs()
