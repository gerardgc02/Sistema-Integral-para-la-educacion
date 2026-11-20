import logging
import sqlite3
from contextlib import contextmanager
from typing import Optional

import bcrypt
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# =========================================================================
# CONFIGURACIÓN DE LOGGING
# =========================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("rbac_api")


# =========================================================================
# UTILIDADES DE CONTRASEÑAS (BCRYPT)
# =========================================================================
def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            stored_hash.encode("utf-8"),
        )
    except ValueError:
        return False


# =========================================================================
# 1. INSTANCIAR LA APLICACIÓN
# =========================================================================
app = FastAPI(
    title="Sistema Escolar RBAC - API",
    description="API RESTful conectada a SQLite para gestión escolar basada en roles.",
    version="1.1.0",
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


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


def error_response(
    status_code: int,
    code: str,
    message: str,
    detail: Optional[str] = None,
) -> JSONResponse:
    payload = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if detail:
        payload["error"]["detail"] = detail
    return JSONResponse(status_code=status_code, content=payload)


# =========================================================================
# MANEJADORES GLOBALES DE ERRORES
# =========================================================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        "HTTP %s en %s %s -> %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return error_response(
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errores = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "msg": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    logger.warning(
        "Error de validación en %s %s -> %s",
        request.method,
        request.url.path,
        errores,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Datos de entrada inválidos o incompletos.",
                "fields": errores,
            }
        },
    )


@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(request: Request, exc: sqlite3.Error):
    logger.error(
        "Error de SQLite en %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    if isinstance(exc, sqlite3.IntegrityError):
        return error_response(
            status_code=400,
            code="DB_INTEGRITY_ERROR",
            message="Violación de restricción en base de datos (clave única, foránea o nula).",
            detail=str(exc),
        )
    if isinstance(exc, sqlite3.OperationalError):
        return error_response(
            status_code=500,
            code="DB_OPERATIONAL_ERROR",
            message="Error operativo en SQLite (tabla inexistente, columna inválida o BD bloqueada).",
            detail=str(exc),
        )
    return error_response(
        status_code=500,
        code="DB_ERROR",
        message="Error interno de base de datos.",
        detail=str(exc),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.critical(
        "Excepción no controlada en %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="Ocurrió un error inesperado en el servidor.",
        detail=str(exc),
    )


# =========================================================================
# RUTA RAÍZ DE BIENVENIDA
# =========================================================================
@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Sistema Escolar RBAC API",
        "docs": "/docs",
    }


# =========================================================================
# MODELOS PYDANTIC
# =========================================================================
class LoginPayload(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)
    full_name: str = Field(..., min_length=1)
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


class AuditLogCreate(BaseModel):
    user_id: int
    action: str
    details: Optional[str] = None


class AttendanceCreate(BaseModel):
    schedule_id: int
    student_id: int
    date: str
    status: str


class GradeCreate(BaseModel):
    user_id: int
    subject_id: int
    semester_period: str
    unit_1: Optional[float] = None
    unit_2: Optional[float] = None
    unit_3: Optional[float] = None
    unit_4: Optional[float] = None
    status: str = "Cursando"


class GradeUpdate(BaseModel):
    unit_1: Optional[float] = None
    unit_2: Optional[float] = None
    unit_3: Optional[float] = None
    unit_4: Optional[float] = None
    status: str = "Cursando"


# =========================================================================
# ENDPOINTS DE AUTENTICACIÓN
# =========================================================================
@app.post("/api/login")
def login(payload: LoginPayload):
    clean_user = payload.username.strip()
    with get_db() as conn:
        user = conn.execute(
            """
            SELECT u.id, u.username, u.password_hash, u.full_name, u.role_id, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = ?
            """,
            (clean_user,),
        ).fetchone()

    if not user or not verify_password(payload.password, user["password_hash"]):
        logger.warning("Intento de login fallido para usuario '%s'", clean_user)
        raise HTTPException(status_code=401, detail="Credenciales inválidas o usuario no encontrado.")

    return {
        "id": user["id"],
        "user": user["username"],
        "fullName": user["full_name"],
        "level": user["role_id"],
        "roleName": user["role_name"],
    }


# =========================================================================
# ENDPOINTS DE GESTIÓN DE USUARIOS (CRUD)
# =========================================================================
@app.get("/api/users")
def get_users():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.username as user,
                   u.full_name as fullName, u.role_id as level, r.name as roleName
            FROM users u
            JOIN roles r ON u.role_id = r.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/users")
def create_user(payload: UserCreate):
    hashed_pw = hash_password(payload.password)
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, full_name, role_id) VALUES (?, ?, ?, ?)",
                (payload.username.strip(), hashed_pw, payload.full_name.strip(), payload.role_id),
            )
            conn.commit()
            new_id = cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.warning("Fallo al crear usuario '%s': %s", payload.username, e)
            raise HTTPException(
                status_code=400,
                detail="El nombre de usuario ya está registrado o el rol no existe.",
            )
    return {"message": "Usuario creado con éxito", "id": new_id}


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Usuario con ID {user_id} no encontrado.")
    return {"message": f"Usuario con ID {user_id} eliminado."}


# =========================================================================
# ENDPOINTS DE CATÁLOGO DE MATERIAS
# =========================================================================
@app.get("/api/subjects")
def get_subjects():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, code, name, credits, semester_level as semester FROM subjects"
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/subjects")
def create_subject(payload: SubjectCreate):
    clean_code = payload.code.strip().upper()
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO subjects (code, name, credits, semester_level) VALUES (?, ?, ?, ?)",
                (clean_code, payload.name.strip(), payload.credits, payload.semester_level),
            )
            conn.commit()
            new_id = cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.warning("Fallo al crear materia '%s': %s", clean_code, e)
            raise HTTPException(status_code=400, detail="La clave de materia ya existe.")
    return {"message": "Materia registrada con éxito", "id": new_id}


# =========================================================================
# ENDPOINTS DE HORARIOS Y AULAS
# =========================================================================
@app.get("/api/schedules")
def get_schedules():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.user_id, s.subject_id, s.semester_period,
                   u.username as studentUser, u.full_name as teacherName,
                   sub.code as subjectCode, sub.name as subjectName, sub.semester_level as semester,
                   s.day_of_week as day, s.start_time as startTime, s.end_time as endTime, s.room
            FROM schedules s
            JOIN users u ON s.user_id = u.id
            JOIN subjects sub ON s.subject_id = sub.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/schedules")
def create_schedule(payload: ScheduleCreate):
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO schedules (user_id, subject_id, semester_period, day_of_week, start_time, end_time, room)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.user_id,
                    payload.subject_id,
                    payload.semester_period,
                    payload.day_of_week,
                    payload.start_time,
                    payload.end_time,
                    payload.room,
                ),
            )
            conn.commit()
            new_id = cursor.lastrowid
        except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {e}")
    return {"message": "Horario y clase asignados con éxito", "id": new_id}


@app.put("/api/schedules/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleUpdate):
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """
                UPDATE schedules
                SET user_id = ?, subject_id = ?, semester_period = ?, day_of_week = ?,
                    start_time = ?, end_time = ?, room = ?
                WHERE id = ?
                """,
                (
                    payload.user_id,
                    payload.subject_id,
                    payload.semester_period,
                    payload.day_of_week,
                    payload.start_time,
                    payload.end_time,
                    payload.room,
                    schedule_id,
                ),
            )
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Horario no encontrado.")
        except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=400, detail=f"Error de integridad: {e}")
    return {"message": f"Horario con ID {schedule_id} actualizado con éxito."}


@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Horario con ID {schedule_id} no encontrado.")
    return {"message": f"Asignación de horario con ID {schedule_id} eliminado."}


# =========================================================================
# ENDPOINTS DE BITÁCORA DE AUDITORÍA Y ASISTENCIA
# =========================================================================
@app.get("/api/audit-logs")
def get_audit_logs(limit: int = 50):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT a.id, u.username, u.full_name, a.action, a.details, a.timestamp
            FROM audit_logs a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/audit-logs")
def create_audit_log(payload: AuditLogCreate):
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
                (payload.user_id, payload.action, payload.details),
            )
            conn.commit()
            new_id = cursor.lastrowid
        except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=400, detail=f"Usuario o datos inválidos para auditoría: {e}")
    return {"message": "Log registrado con éxito", "id": new_id}


@app.get("/api/attendance/{schedule_id}")
def get_attendance(schedule_id: int, date: Optional[str] = None):
    with get_db() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM attendance WHERE schedule_id = ? AND date = ?",
                (schedule_id, date),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM attendance WHERE schedule_id = ?",
                (schedule_id,),
            ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/attendance")
def save_attendance(payload: AttendanceCreate):
    with get_db() as conn:
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO attendance (schedule_id, student_id, date, status)
                VALUES (?, ?, ?, ?)
                """,
                (payload.schedule_id, payload.student_id, payload.date, payload.status),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=400, detail=f"Horario o alumno inexistente: {e}")
    return {"message": "Asistencia guardada correctamente."}


# =========================================================================
# ENDPOINTS DE CALIFICACIONES Y KARDEX
# =========================================================================
@app.get("/api/grades")
def get_grades(student_id: Optional[int] = None):
    with get_db() as conn:
        query = """
            SELECT g.id, g.user_id, u_student.full_name as studentName,
                   g.subject_id, sub.code as subjectCode, sub.name as subjectName, sub.credits,
                   g.semester_period, g.unit_1, g.unit_2, g.unit_3, g.unit_4, g.status
            FROM student_grades g
            JOIN users u_student ON g.user_id = u_student.id
            JOIN subjects sub ON g.subject_id = sub.id
        """
        if student_id:
            rows = conn.execute(query + " WHERE g.user_id = ?", (student_id,)).fetchall()
        else:
            rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/grades")
def save_grade(payload: GradeCreate):
    with get_db() as conn:
        try:
            existing = conn.execute(
                """
                SELECT id FROM student_grades
                WHERE user_id = ? AND subject_id = ? AND semester_period = ?
                """,
                (payload.user_id, payload.subject_id, payload.semester_period),
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE student_grades
                    SET unit_1 = ?, unit_2 = ?, unit_3 = ?, unit_4 = ?, status = ?
                    WHERE id = ?
                    """,
                    (
                        payload.unit_1,
                        payload.unit_2,
                        payload.unit_3,
                        payload.unit_4,
                        payload.status,
                        existing["id"],
                    ),
                )
                msg = "Calificaciones actualizadas con éxito."
                new_id = existing["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO student_grades
                        (user_id, subject_id, semester_period, unit_1, unit_2, unit_3, unit_4, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.user_id,
                        payload.subject_id,
                        payload.semester_period,
                        payload.unit_1,
                        payload.unit_2,
                        payload.unit_3,
                        payload.unit_4,
                        payload.status,
                    ),
                )
                msg = "Calificación registrada con éxito."
                new_id = cursor.lastrowid

            conn.commit()
        except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {e}")

    return {"message": msg, "id": new_id}


@app.put("/api/grades/{grade_id}")
def update_grade(grade_id: int, payload: GradeUpdate):
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """
                UPDATE student_grades
                SET unit_1 = ?, unit_2 = ?, unit_3 = ?, unit_4 = ?, status = ?
                WHERE id = ?
                """,
                (payload.unit_1, payload.unit_2, payload.unit_3, payload.unit_4, payload.status, grade_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Registro de calificaciones no encontrado.")
        except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=400, detail=f"Error de integridad: {e}")
    return {"message": f"Calificaciones con ID {grade_id} actualizadas con éxito."}


@app.delete("/api/grades/{grade_id}")
def delete_grade(grade_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM student_grades WHERE id = ?", (grade_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Registro de calificaciones con ID {grade_id} no encontrado.")
    return {"message": f"Registro de calificaciones con ID {grade_id} eliminado."}