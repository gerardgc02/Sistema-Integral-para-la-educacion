from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pydantic import BaseModel
from typing import Optional

# 1. Instanciar la aplicación PRIMERO (antes de cualquier ruta)
app = FastAPI(
    title="Sistema Escolar RBAC - API",
    description="API RESTful conectada a SQLite para gestión escolar basada en roles.",
    version="1.0.0"
)

# 2. Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Retorna diccionarios con nombres de columna
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# =========================================================================
# RUTA RAÍZ DE BIENVENIDA
# =========================================================================
@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Sistema Escolar RBAC API",
        "docs": "/docs"
    }

# =========================================================================
# MODELOS PYDANTIC (Validación de datos de entrada)
# =========================================================================
class LoginPayload(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password_hash: str
    full_name: str
    role_id: int

class SubjectCreate(BaseModel):
    code: str
    name: str
    credits: int
    semester_level: int

class ScheduleCreate(BaseModel):
    user_id: int
    subject_id: int
    semester_period: str
    day_of_week: str
    start_time: str
    end_time: str
    room: str


# =========================================================================
# ENDPOINTS DE AUTENTICACIÓN
# =========================================================================
@app.post("/api/login")
def login(payload: LoginPayload):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT u.id, u.username, u.full_name, u.role_id, r.name as role_name
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.username = ? AND u.password_hash = ?
    """
    user = cursor.execute(query, (payload.username.strip(), payload.password)).fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas o usuario no encontrado.")

    return {
        "id": user["id"],
        "user": user["username"],
        "fullName": user["full_name"],
        "level": user["role_id"],
        "roleName": user["role_name"]
    }


# =========================================================================
# ENDPOINTS DE GESTIÓN DE USUARIOS (CRUD)
# =========================================================================
@app.get("/api/users")
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT u.id, u.username as user, u.password_hash as pass, u.full_name as fullName, u.role_id as level, r.name as roleName
        FROM users u
        JOIN roles r ON u.role_id = r.id
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/users")
def create_user(payload: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, role_id) VALUES (?, ?, ?, ?)",
            (payload.username, payload.password_hash, payload.full_name, payload.role_id)
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado.")
    conn.close()
    return {"message": "Usuario creado con éxito", "id": new_id}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"message": f"Usuario con ID {user_id} eliminado."}


# =========================================================================
# ENDPOINTS DE CATÁLOGO DE MATERIAS
# =========================================================================
@app.get("/api/subjects")
def get_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, code, name, credits, semester_level as semester FROM subjects").fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/subjects")
def create_subject(payload: SubjectCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO subjects (code, name, credits, semester_level) VALUES (?, ?, ?, ?)",
            (payload.code.upper(), payload.name, payload.credits, payload.semester_level)
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="La clave de materia ya existe.")
    conn.close()
    return {"message": "Materia registrada con éxito", "id": new_id}


# =========================================================================
# ENDPOINTS DE HORARIOS Y AULAS
# =========================================================================
@app.get("/api/schedules")
def get_schedules():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
            SELECT s.id, u.username as studentUser, sub.code as subjectCode, 
                s.day_of_week as day, s.start_time as startTime, s.end_time as endTime, s.room
            FROM schedules s  -- <--- Asegúrate de que diga FROM en lugar de Posts
            JOIN users u ON s.user_id = u.id
            JOIN subjects sub ON s.subject_id = sub.id
        """
    rows = cursor.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]