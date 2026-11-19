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

class ScheduleUpdate(BaseModel):
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
        SELECT s.id, s.user_id, s.subject_id, s.semester_period, 
               u.username as studentUser, u.full_name as teacherName, 
               sub.code as subjectCode, sub.name as subjectName, sub.semester_level as semester,
               s.day_of_week as day, s.start_time as startTime, s.end_time as endTime, s.room
        FROM schedules s
        JOIN users u ON s.user_id = u.id
        JOIN subjects sub ON s.subject_id = sub.id
    """
    rows = cursor.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/schedules")
def create_schedule(payload: ScheduleCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO schedules (user_id, subject_id, semester_period, day_of_week, start_time, end_time, room)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.user_id, payload.subject_id, payload.semester_period, payload.day_of_week, payload.start_time, payload.end_time, payload.room)
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {e}")
    conn.close()
    return {"message": "Horario y clase asignados con éxito", "id": new_id}

@app.put("/api/schedules/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE schedules 
            SET user_id = ?, subject_id = ?, semester_period = ?, day_of_week = ?, start_time = ?, end_time = ?, room = ?
            WHERE id = ?
            """,
            (payload.user_id, payload.subject_id, payload.semester_period, payload.day_of_week, payload.start_time, payload.end_time, payload.room, schedule_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Horario no encontrado.")
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Error de integridad: {e}")
    conn.close()
    return {"message": f"Horario con ID {schedule_id} actualizado con éxito."}

@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    return {"message": f"Asignación de horario con ID {schedule_id} eliminado."}


# =========================================================================
# MODELOS PYDANTIC PARA AUDITORÍA Y ASISTENCIA
# =========================================================================
class AuditLogCreate(BaseModel):
    user_id: int
    action: str
    details: Optional[str] = None

class AttendanceCreate(BaseModel):
    schedule_id: int
    student_id: int
    date: str  # Formato "YYYY-MM-DD"
    status: str  # "Presente", "Ausente", "Retardo"


# =========================================================================
# ENDPOINTS DE BITÁCORA DE AUDITORÍA Y ASISTENCIA
# =========================================================================
@app.get("/api/audit-logs")
def get_audit_logs(limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT a.id, u.username, u.full_name, a.action, a.details, a.timestamp
        FROM audit_logs a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
        LIMIT ?
    """
    rows = cursor.execute(query, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/audit-logs")
def create_audit_log(payload: AuditLogCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (payload.user_id, payload.action, payload.details)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"message": "Log registrado con éxito", "id": new_id}

@app.get("/api/attendance/{schedule_id}")
def get_attendance(schedule_id: int, date: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if date:
        query = "SELECT * FROM attendance WHERE schedule_id = ? AND date = ?"
        rows = cursor.execute(query, (schedule_id, date)).fetchall()
    else:
        query = "SELECT * FROM attendance WHERE schedule_id = ?"
        rows = cursor.execute(query, (schedule_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/attendance")
def save_attendance(payload: AttendanceCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Usamos INSERT OR REPLACE para actualizar si ya se había pasado lista ese día
    cursor.execute(
        """
        INSERT OR REPLACE INTO attendance (schedule_id, student_id, date, status)
        VALUES (?, ?, ?, ?)
        """,
        (payload.schedule_id, payload.student_id, payload.date, payload.status)
    )
    conn.commit()
    conn.close()
    return {"message": "Asistencia guardada correctamente."}

# =========================================================================
# MODELOS PYDANTIC PARA CALIFICACIONES Y KARDEX
# =========================================================================
class GradeCreate(BaseModel):
    user_id: int          # ID del alumno
    subject_id: int       # ID de la materia
    semester_period: str  # Ej. "2026-1"
    unit_1: Optional[float] = None
    unit_2: Optional[float] = None
    unit_3: Optional[float] = None
    unit_4: Optional[float] = None
    status: str = "Cursando"


# =========================================================================
# ENDPOINTS DE CALIFICACIONES Y KARDEX
# =========================================================================
@app.get("/api/grades")
def get_grades(student_id: Optional[int] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT g.id, g.user_id, u_student.full_name as studentName,
               g.subject_id, sub.code as subjectCode, sub.name as subjectName, sub.credits,
               g.semester_period, g.unit_1, g.unit_2, g.unit_3, g.unit_4, g.status
        FROM student_grades g
        JOIN users u_student ON g.user_id = u_student.id
        JOIN subjects sub ON g.subject_id = sub.id
    """
    
    if student_id:
        query += " WHERE g.user_id = ?"
        rows = cursor.execute(query, (student_id,)).fetchall()
    else:
        rows = cursor.execute(query).fetchall()
        
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/grades")
def save_grade(payload: GradeCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Verificamos si ya existe un registro para este alumno y materia en el mismo periodo
        cursor.execute(
            """
            SELECT id FROM student_grades 
            WHERE user_id = ? AND subject_id = ? AND semester_period = ?
            """,
            (payload.user_id, payload.subject_id, payload.semester_period)
        )
        existing = cursor.fetchone()

        if existing:
            # Si ya existe, actualizamos las unidades y el estatus
            cursor.execute(
                """
                UPDATE student_grades 
                SET unit_1 = ?, unit_2 = ?, unit_3 = ?, unit_4 = ?, status = ?
                WHERE id = ?
                """,
                (payload.unit_1, payload.unit_2, payload.unit_3, payload.unit_4, payload.status, existing["id"])
            )
            msg = "Calificaciones actualizadas con éxito."
            new_id = existing["id"]
        else:
            # Si no existe, lo insertamos nuevo
            cursor.execute(
                """
                INSERT INTO student_grades (user_id, subject_id, semester_period, unit_1, unit_2, unit_3, unit_4, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (payload.user_id, payload.subject_id, payload.semester_period, payload.unit_1, payload.unit_2, payload.unit_3, payload.unit_4, payload.status)
            )
            msg = "Calificación registrada con éxito."
            new_id = cursor.lastrowid

        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {e}")
    
    conn.close()
    return {"message": msg, "id": new_id}

@app.delete("/api/grades/{grade_id}")
def delete_grade(grade_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM student_grades WHERE id = ?", (grade_id,))
    conn.commit()
    conn.close()
    return {"message": f"Registro de calificaciones con ID {grade_id} eliminado."}

class GradeUpdate(BaseModel):
    unit_1: Optional[float] = None
    unit_2: Optional[float] = None
    unit_3: Optional[float] = None
    unit_4: Optional[float] = None
    status: str = "Cursando"

@app.put("/api/grades/{grade_id}")
def update_grade(grade_id: int, payload: GradeUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE student_grades 
            SET unit_1 = ?, unit_2 = ?, unit_3 = ?, unit_4 = ?, status = ?
            WHERE id = ?
            """,
            (payload.unit_1, payload.unit_2, payload.unit_3, payload.unit_4, payload.status, grade_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Registro de calificaciones no encontrado.")
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Error de integridad: {e}")
    conn.close()
    return {"message": f"Calificaciones con ID {grade_id} actualizadas con éxito."}