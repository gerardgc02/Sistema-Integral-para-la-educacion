-- =========================================================================
-- DATOS INICIALES DEL SISTEMA (seed.sql)
-- =========================================================================

-- 1. Insertar Roles del Sistema
INSERT INTO roles (id, name, description) VALUES
(1, 'alumno', 'Acceso a expediente, calificaciones y horarios personales'),
(2, 'maestro', 'Acceso a captura de calificaciones y grupos asignados'),
(3, 'director', 'Gestión académica total: usuarios, materias y control operativo'),
(4, 'admin', 'Mantenimiento de infraestructura y auditoría del sistema');

-- 2. Insertar Usuarios Base (Contraseñas en texto plano para prototipo local)
INSERT INTO users (id, username, password_hash, full_name, role_id) VALUES
(1, 'Alumno1', '1111', 'Carlos Méndez', 1),
(2, 'Maestro1', '2222', 'Ana Torres', 2),
(3, 'super1', '3333', 'Roberto Silva', 3),
(4, 'admin', '4444', 'Luis Guzmán', 4);

-- 3. Insertar Perfil Extendido para el Alumno 1
INSERT INTO student_profiles (user_id, student_code, program, current_semester, cumulative_gpa, tutor_name, phone, emergency_contact) VALUES
(1, 'ALU-2026-8492', 'Ingeniería en Electrónica y Telecomunicaciones', 6, 91.40, 'Dr. Alberto Ríos', '+52 (951) 555-0142', 'María Pérez (Madre)');

-- 4. Insertar Catálogo de Materias
INSERT INTO subjects (id, code, name, credits, semester_level) VALUES
(1, 'EMB-301', 'Sistemas Embebidos', 6, 6),
(2, 'ARQ-302', 'Arquitectura de Computadoras', 5, 6),
(3, 'RED-201', 'Redes de Computadoras', 5, 6),
(4, 'OS-401', 'Sistemas Operativos y Kernel', 6, 6);

-- 5. Insertar Calificaciones Iniciales (Kardex del Alumno 1 en el periodo 2026-A)
INSERT INTO student_grades (user_id, subject_id, semester_period, unit_1, unit_2, unit_3, unit_4, status) VALUES
(1, 1, '2026-A', 90.00, 85.00, 92.00, NULL, 'Cursando'),
(1, 2, '2026-A', 88.00, 90.00, 85.00, NULL, 'Cursando'),
(1, 3, '2026-A', 95.00, 92.00, 90.00, NULL, 'Cursando'),
(1, 4, '2026-A', 82.00, 88.00, 86.00, NULL, 'Cursando');

-- 6. Insertar Horarios del Alumno 1
INSERT INTO schedules (user_id, subject_id, semester_period, day_of_week, start_time, end_time, room) VALUES
(1, 1, '2026-A', 'Lunes', '07:00:00', '09:00:00', 'Lab. Electrónica 3'),
(1, 2, '2026-A', 'Martes', '09:00:00', '11:00:00', 'Aula 204'),
(1, 3, '2026-A', 'Miércoles', '11:00:00', '13:00:00', 'Lab. Redes 1'),
(1, 4, '2026-A', 'Jueves', '07:00:00', '09:00:00', 'Lab. Sistemas 2');