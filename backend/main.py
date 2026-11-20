## @file main.py
## @brief API RESTful con FastAPI y SQLite para el Sistema Escolar RBAC.
## @details Gestiona autenticación con `bcrypt`, administración de usuarios,
##          catálogo de materias, horarios, asistencia, bitácora de auditoría
##          y calificaciones, con manejo centralizado de errores y logging.
## @version 1.1.0

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


## @defgroup logging_config Configuración de Logging
## @{

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
## Instancia principal del logger para la API RBAC.
logger = logging.getLogger("rbac_api")

## @}


## @defgroup security_utils Utilidades de Contraseñas (bcrypt)
## @{

## @brief Genera un hash seguro de contraseña utilizando `bcrypt`.
## @param plain_password Contraseña en texto plano a hashear.
## @return Cadena UTF-8 con el hash generado (incluye salt).
def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


## @brief Verifica si una contraseña en texto plano coincide con un hash `bcrypt`.
## @param plain_password Contraseña ingresada por el usuario.
## @param stored_hash Hash almacenado en base de datos.
## @return `True` si coincide, `False` si no coincide o si el formato del hash es inválido.
def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            stored_hash.encode("utf-8"),
        )
    except ValueError:
        return False

## @}


## @defgroup app_setup Aplicación FastAPI y Conexión a Base de Datos
## @{

## Instancia principal de la aplicación FastAPI.
app = FastAPI(
    title="Sistema Escolar RBAC - API",
    description="API RESTful conectada a SQLite para gestión escolar basada en roles.",
    version="1.1.0",
)

# Middleware CORS abierto para desarrollo y consumo desde cliente web.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

## Ruta o nombre del archivo de base de datos SQLite.
DB_NAME = "database.db"


## @brief Context manager para abrir y cerrar conexiones SQLite de forma segura.
## @details Configura `row_factory = sqlite3.Row` para acceder a columnas por nombre
##          y activa `PRAGMA foreign_keys = ON;` en cada conexión.
## @return Objeto `sqlite3.Connection` listo para ejecutar consultas.
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


## @brief Construye una respuesta JSON estandarizada para errores de la API.
## @param status_code Código de estado HTTP (por ejemplo, 400, 401, 404, 500).
## @param code Código de error interno legible por máquina.
## @param message Mensaje descriptivo del error para el cliente.
## @param detail Detalle técnico adicional opcional.
## @return `JSONResponse` con estructura `{"error": {"code", "message", ...}}`.
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

## @}


## @defgroup error_handlers Manejadores Globales de Errores
## @{

## @brief Captura excepciones `HTTPException` y devuelve el formato de error estándar.
## @param request Petición HTTP entrante.
## @param exc Excepción HTTP lanzada por un endpoint o middleware.
## @return `JSONResponse` con código HTTP correspondiente y `code = "HTTP_<status>"`.
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


## @brief Captura errores de validación de Pydantic (`RequestValidationError`).
## @param request Petición HTTP entrante.
## @param exc Excepción con los errores de validación de campos.
## @return `JSONResponse` con estado `422` y arreglo `fields` con el detalle por campo.
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


## @brief Captura errores de SQLite (`sqlite3.Error`) y mapea violaciones o fallos operativos.
## @param request Petición HTTP entrante.
## @param exc Excepción lanzada por `sqlite3`.
## @return `JSONResponse` con estado `400` para `IntegrityError` o `500` para errores operativos/generales.
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


## @brief Captura cualquier excepción no controlada (`Exception`) para evitar fugas de traza crudas.
## @param request Petición HTTP entrante.
## @param exc Excepción no manejada.
## @return `JSONResponse` con estado `500` y `code = "INTERNAL_SERVER_ERROR"`.
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

## @}


## @defgroup root_endpoint Ruta Raíz
## @{

## @brief Endpoint de verificación de estado de la API (`GET /`).
## @return Diccionario con estado `"online"`, nombre del sistema y ruta `/docs`.
@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Sistema Escolar RBAC API",
        "docs": "/docs",
    }

## @}


## @defgroup pydantic_models Modelos de Entrada (Pydantic)
## @{

## @brief Credenciales para inicio de sesión.
class LoginPayload(BaseModel):
    ## Nombre de usuario.
    username: str
    ## Contraseña en texto plano.
    password: str


## @brief Payload para registrar un nuevo usuario.
class UserCreate(BaseModel):
    ## Nombre de usuario único (3 a 50 caracteres).
    username: str = Field(..., min_length=3, max_length=50)
    ## Contraseña (6 a 72 caracteres por límite de `bcrypt`).
    password: str = Field(..., min_length=6, max_length=72)
    ## Nombre completo del usuario.
    full_name: str = Field(..., min_length=1)
    ## Identificador del rol asignado (`roles.id`).
    role_id: int


## @brief Payload para crear una materia en el catálogo.
class SubjectCreate(BaseModel):
    ## Clave única de la materia.
    code: str
    ## Nombre de la materia.
    name: str
    ## Número de créditos académicos.
    credits: int
    ## Semestre o nivel en el plan de estudios.
    semester_level: int


## @brief Payload para asignar un horario/clase (`POST /api/schedules`).
class ScheduleCreate(BaseModel):
    ## ID del usuario (docente o responsable) asociado al horario.
    user_id: int
    ## ID de la materia (`subjects.id`).
    subject_id: int
    ## Periodo escolar (por ejemplo, `"2026-1"`).
    semester_period: str
    ## Día de la semana.
    day_of_week: str
    ## Hora de inicio.
    start_time: str
    ## Hora de finalización.
    end_time: str
    ## Aula o salón asignado.
    room: str


## @brief Payload para actualizar un horario existente (`PUT /api/schedules/{schedule_id}`).
class ScheduleUpdate(BaseModel):
    ## ID del usuario asociado al horario.
    user_id: int
    ## ID de la materia (`subjects.id`).
    subject_id: int
    ## Periodo escolar.
    semester_period: str
    ## Día de la semana.
    day_of_week: str
    ## Hora de inicio.
    start_time: str
    ## Hora de finalización.
    end_time: str
    ## Aula o salón asignado.
    room: str


## @brief Payload para registrar una entrada en la bitácora de auditoría.
class AuditLogCreate(BaseModel):
    ## ID del usuario que ejecuta la acción.
    user_id: int
    ## Nombre o clave de la acción realizada.
    action: str
    ## Descripción o detalles adicionales opcionales.
    details: Optional[str] = None


## @brief Payload para registrar o actualizar asistencia (`POST /api/attendance`).
class AttendanceCreate(BaseModel):
    ## ID del horario (`schedules.id`).
    schedule_id: int
    ## ID del alumno (`users.id`).
    student_id: int
    ## Fecha del registro de asistencia.
    date: str
    ## Estado de asistencia (por ejemplo, `"Presente"`, `"Falta"`, `"Retardo"`).
    status: str


## @brief Payload para crear o actualizar calificaciones por unidad (`POST /api/grades`).
class GradeCreate(BaseModel):
    ## ID del alumno (`users.id`).
    user_id: int
    ## ID de la materia (`subjects.id`).
    subject_id: int
    ## Periodo escolar.
    semester_period: str
    ## Calificación de la unidad 1.
    unit_1: Optional[float] = None
    ## Calificación de la unidad 2.
    unit_2: Optional[float] = None
    ## Calificación de la unidad 3.
    unit_3: Optional[float] = None
    ## Calificación de la unidad 4.
    unit_4: Optional[float] = None
    ## Estado académico del registro (por defecto `"Cursando"`).
    status: str = "Cursando"


## @brief Payload para modificar calificaciones existentes (`PUT /api/grades/{grade_id}`).
class GradeUpdate(BaseModel):
    ## Calificación de la unidad 1.
    unit_1: Optional[float] = None
    ## Calificación de la unidad 2.
    unit_2: Optional[float] = None
    ## Calificación de la unidad 3.
    unit_3: Optional[float] = None
    ## Calificación de la unidad 4.
    unit_4: Optional[float] = None
    ## Estado académico del registro.
    status: str = "Cursando"

## @}


## @defgroup auth_endpoints Endpoints de Autenticación
## @{

## @brief Autentica a un usuario mediante `username` y `password` (`POST /api/login`).
## @param payload Credenciales de acceso (`LoginPayload`).
## @return Datos básicos del usuario autenticado (`id`, `user`, `fullName`, `level`, `roleName`).
## @throws HTTPException `401` si el usuario no existe o la contraseña no es válida.
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

## @}


## @defgroup users_endpoints Gestión de Usuarios (CRUD)
## @{

## @brief Lista todos los usuarios registrados junto con su rol (`GET /api/users`).
## @return Lista de diccionarios con `id`, `user`, `fullName`, `level` y `roleName`.
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


## @brief Crea un nuevo usuario con contraseña hasheada en `bcrypt` (`POST /api/users`).
## @param payload Datos del usuario a crear (`UserCreate`).
## @return Mensaje de confirmación y el `id` generado.
## @throws HTTPException `400` si el `username` ya existe o el `role_id` no es válido.
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


## @brief Elimina un usuario por su identificador (`DELETE /api/users/{user_id}`).
## @param user_id Identificador numérico del usuario en la tabla `users`.
## @return Mensaje confirmando la eliminación.
## @throws HTTPException `404` si no existe un usuario con `user_id`.
@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Usuario con ID {user_id} no encontrado.")
    return {"message": f"Usuario con ID {user_id} eliminado."}

## @}


## @defgroup subjects_endpoints Catálogo de Materias
## @{

## @brief Obtiene el catálogo completo de materias (`GET /api/subjects`).
## @return Lista de materias con `id`, `code`, `name`, `credits` y `semester`.
@app.get("/api/subjects")
def get_subjects():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, code, name, credits, semester_level as semester FROM subjects"
        ).fetchall()
    return [dict(row) for row in rows]


## @brief Registra una nueva materia en el catálogo (`POST /api/subjects`).
## @details Normaliza `code` eliminando espacios y convirtiéndolo a mayúsculas.
## @param payload Datos de la materia (`SubjectCreate`).
## @return Mensaje de confirmación y el `id` asignado.
## @throws HTTPException `400` si la clave (`code`) de la materia ya está registrada.
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

## @}


## @defgroup schedules_endpoints Horarios y Aulas
## @{

## @brief Obtiene todos los horarios con información de usuario y materia (`GET /api/schedules`).
## @return Lista de registros de horario con datos combinados de `schedules`, `users` y `subjects`.
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


## @brief Crea una nueva asignación de horario y clase (`POST /api/schedules`).
## @param payload Datos del horario (`ScheduleCreate`).
## @return Mensaje de confirmación y el `id` creado.
## @throws HTTPException `400` si falla alguna restricción de integridad en SQLite.
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


## @brief Actualiza un horario existente por ID (`PUT /api/schedules/{schedule_id}`).
## @param schedule_id Identificador del horario a actualizar.
## @param payload Nuevos datos del horario (`ScheduleUpdate`).
## @return Mensaje de confirmación.
## @throws HTTPException `404` si el horario no existe; `400` si hay error de integridad.
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


## @brief Elimina una asignación de horario por ID (`DELETE /api/schedules/{schedule_id}`).
## @param schedule_id Identificador del horario a eliminar.
## @return Mensaje de confirmación.
## @throws HTTPException `404` si no se encuentra el horario.
@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Horario con ID {schedule_id} no encontrado.")
    return {"message": f"Asignación de horario con ID {schedule_id} eliminado."}

## @}


## @defgroup audit_attendance_endpoints Bitácora de Auditoría y Asistencia
## @{

## @brief Consulta los registros recientes de la bitácora de auditoría (`GET /api/audit-logs`).
## @param limit Cantidad máxima de registros a devolver (por defecto `50`).
## @return Lista ordenada descendentemente por `timestamp` con datos de usuario y acción.
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


## @brief Registra un evento en la bitácora de auditoría (`POST /api/audit-logs`).
## @param payload Datos del evento (`AuditLogCreate`).
## @return Mensaje de confirmación y el `id` del log creado.
## @throws HTTPException `400` si el `user_id` no existe o los datos violan restricciones.
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


## @brief Consulta registros de asistencia para un horario (`GET /api/attendance/{schedule_id}`).
## @param schedule_id Identificador del horario (`schedules.id`).
## @param date Fecha opcional (`YYYY-MM-DD`) para filtrar un día específico.
## @return Lista de registros de asistencia coincidentes.
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


## @brief Inserta o reemplaza un pase de lista (`POST /api/attendance`).
## @details Utiliza `INSERT OR REPLACE` apoyado en la restricción única `(schedule_id, student_id, date)`.
## @param payload Datos de asistencia (`AttendanceCreate`).
## @return Mensaje de confirmación.
## @throws HTTPException `400` si el horario o el alumno no existen en la base de datos.
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

## @}


## @defgroup grades_endpoints Calificaciones y Kardex
## @{

## @brief Obtiene calificaciones, opcionalmente filtradas por alumno (`GET /api/grades`).
## @param student_id ID opcional del alumno (`users.id`) para filtrar su historial.
## @return Lista de calificaciones por unidad y materia.
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


## @brief Crea o actualiza un registro de calificaciones (`POST /api/grades`).
## @details Busca si ya existe un registro para `(user_id, subject_id, semester_period)`;
##          si existe lo actualiza, y si no lo inserta.
## @param payload Datos de calificaciones (`GradeCreate`).
## @return Diccionario con `message` e `id` del registro afectado.
## @throws HTTPException `400` si hay error de integridad referencial en SQLite.
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


## @brief Actualiza las unidades y estado de un registro de calificación (`PUT /api/grades/{grade_id}`).
## @param grade_id Identificador del registro en `student_grades`.
## @param payload Nuevos valores de calificaciones y estado (`GradeUpdate`).
## @return Mensaje de confirmación.
## @throws HTTPException `404` si no existe el registro; `400` si ocurre un error de integridad.
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


## @brief Elimina un registro de calificaciones por ID (`DELETE /api/grades/{grade_id}`).
## @param grade_id Identificador del registro en `student_grades`.
## @return Mensaje de confirmación.
## @throws HTTPException `404` si no se encuentra el registro.
@app.delete("/api/grades/{grade_id}")
def delete_grade(grade_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM student_grades WHERE id = ?", (grade_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Registro de calificaciones con ID {grade_id} no encontrado.")
    return {"message": f"Registro de calificaciones con ID {grade_id} eliminado."}

## @}
