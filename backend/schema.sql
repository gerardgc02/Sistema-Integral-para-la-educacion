-- =========================================================================
-- ESQUEMA RELACIONAL DEL SISTEMA ESCOLAR (schema.sql)
-- Motor recomendado: MySQL / MariaDB / PostgreSQL
-- =========================================================================

-- 1. Catálogo de Roles y Niveles de Acceso
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,          -- 'alumno', 'maestro', 'director', 'admin'
    description VARCHAR(150) NOT NULL
);

-- 2. Tabla Global de Usuarios y Credenciales (Autenticación)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,       -- Contraseña protegida o texto plano para demo
    full_name VARCHAR(120) NOT NULL,
    role_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);

-- 3. Expediente Extendido del Alumno (Relación 1 a 1 con users)
CREATE TABLE IF NOT EXISTS student_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    student_code VARCHAR(30) NOT NULL UNIQUE,  -- Ej. ALU-2026-8492
    program VARCHAR(150) NOT NULL,             -- Ej. Ingeniería en Electrónica y Telecomunicaciones
    current_semester INT NOT NULL,
    cumulative_gpa DECIMAL(5,2) DEFAULT 0.00,  -- Promedio acumulado (ej. 91.40)
    tutor_name VARCHAR(120),
    phone VARCHAR(30),
    emergency_contact VARCHAR(150),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Catálogo Global de Asignaturas
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,          -- Clave de materia (ej. EMB-301)
    name VARCHAR(120) NOT NULL,
    credits INT NOT NULL,                      -- Créditos valorados
    semester_level INT NOT NULL                -- Semestre recomendado en retícula
);

-- 5. Kardex y Calificaciones por Unidad (Relación Alumno - Materia)
CREATE TABLE IF NOT EXISTS student_grades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,                      -- El Alumno
    subject_id INT NOT NULL,                   -- La Materia
    semester_period VARCHAR(20) NOT NULL,      -- Ej. '2026-A'
    unit_1 DECIMAL(5,2) DEFAULT NULL,
    unit_2 DECIMAL(5,2) DEFAULT NULL,
    unit_3 DECIMAL(5,2) DEFAULT NULL,
    unit_4 DECIMAL(5,2) DEFAULT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Cursando', -- 'Cursando', 'Aprobada', 'Reprobada'
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- 6. Bloques de Horarios y Aulas
CREATE TABLE IF NOT EXISTS schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,                      -- Alumno o Maestro asignado
    subject_id INT NOT NULL,
    semester_period VARCHAR(20) NOT NULL,      -- Ej. '2026-A'
    day_of_week VARCHAR(20) NOT NULL,          -- 'Lunes', 'Martes', etc.
    start_time TIME NOT NULL,                  -- '07:00:00'
    end_time TIME NOT NULL,                    -- '09:00:00'
    room VARCHAR(50) NOT NULL                  -- 'Lab. Electrónica 3'
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);