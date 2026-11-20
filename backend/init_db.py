import os
import sqlite3
import bcrypt

DB_PATH = "database.db"
SCHEMA_PATH = "schema.sql"
SEED_PATH = "seed.sql"


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def is_bcrypt_hash(value: str) -> bool:
    return value.startswith(("$2a$", "$2b$", "$2y$"))


def migrate_seed_passwords(conn: sqlite3.Connection) -> int:
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, username, password_hash FROM users").fetchall()
    updated = 0

    for user_id, username, pw_value in rows:
        if pw_value and not is_bcrypt_hash(pw_value):
            new_hash = hash_password(pw_value)
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id),
            )
            updated += 1
            print(f"  [i] Contraseña hasheada para usuario '{username}' (id={user_id}).")

    return updated


def init_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("[-] Base de datos anterior eliminada.")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            cursor.executescript(f.read())
        print("[+] Esquema relacional (schema.sql) aplicado con éxito.")
    else:
        print("[-] Error: No se encontró el archivo schema.sql")
        conn.close()
        return

    if os.path.exists(SEED_PATH):
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            cursor.executescript(f.read())
        print("[+] Datos iniciales (seed.sql) insertados con éxito.")
    else:
        print("[-] Error: No se encontró el archivo seed.sql")
        conn.close()
        return

    count = migrate_seed_passwords(conn)
    conn.commit()
    conn.close()

    print(f"[+] Contraseñas actualizadas a bcrypt: {count}")
    print(f"\n[✓] Base de datos SQLite lista y guardada en: {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    init_database()