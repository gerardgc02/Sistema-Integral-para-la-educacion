import sqlite3
import os

DB_PATH = "database.db"
SCHEMA_PATH = "schema.sql"
SEED_PATH = "seed.sql"

def init_database():
    # Si ya existe una base de datos previa, la limpiamos para empezar frescos
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("[-] Base de datos anterior eliminada.")

    # Crear la conexión a SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # CRUCIAL: Habilitar restricciones de llaves foráneas en SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Ejecutar el esquema (schema.sql)
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_script = f.read()
            cursor.executescript(schema_script)
        print("[+] Esquema relacional (schema.sql) aplicado con éxito.")
    else:
        print("[-] Error: No se encontró el archivo schema.sql")

    # 2. Ejecutar los datos iniciales (seed.sql)
    if os.path.exists(SEED_PATH):
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            seed_script = f.read()
            cursor.executescript(seed_script)
        print("[+] Datos iniciales (seed.sql) insertados con éxito.")
    else:
        print("[-] Error: No se encontró el archivo seed.sql")

    conn.commit()
    conn.close()
    print(f"\n[✓] Base de datos SQLite lista y guardada en: {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    init_database()