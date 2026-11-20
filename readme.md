# Sistema Integral para la Educación - RBAC

Sistema de gestión escolar basado en Control de Acceso Basado en Roles (RBAC), desarrollado como demostración académica. Permite la administración modular de usuarios, materias, horarios y calificaciones con persistencia en bases de datos relacionales.

---

## 🛠 Tecnologías Utilizadas

* **Backend:** Python, FastAPI, SQLite, Pydantic.
* **Frontend:** HTML5, CSS3, JavaScript (Vanilla con Fetch API y gestión de sesiones mediante `sessionStorage`).
* **Control de Acceso (RBAC):** Jerarquía de 4 niveles de privilegios (Alumno, Maestro, Director, Administrador).

---

## 📂 Estructura del Proyecto

```text
.
├── backend
│   ├── database.db          # Base de datos SQLite generada
│   ├── init_db.py           # Script de inicialización y siembra (seed)
│   ├── main.py              # API REST principal con FastAPI
│   ├── schema.sql           # Definición de tablas relacionales
│   └── seed.sql             # Datos iniciales de prueba
├── frontend
│   ├── css/                 # Estilos globales y temas
│   ├── js/                  # Módulos de autenticación (auth.js)
│   ├── login.html           # Puerta de entrada principal al sistema
│   ├── dashboard.html       # Panel dinámico según rol
│   ├── manage_users.html    # Módulo CRUD de usuarios (Director/Admin)
│   ├── manage_subjects.html # Catálogo y gestión de materias
│   ├── manage_schedules.html# Gestión de horarios y aulas
│   └── student_info.html    # Vistas de expediente y kardex académico
└── readme.md
```
## ⚙️ Guía de Instalación y Configuración

### 1. Prerrequisitos
Asegúrate de tener instalado **Python 3.10+** en tu equipo.

### 2. Crear entorno virtual e instalar dependencias
Abre tu terminal en la **raíz del proyecto**, crea un entorno virtual e instala las dependencias del backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn pydantic bcrypt
```

3. Inicializar la base de datos

Con el entorno virtual activado, ejecuta el script para generar database.db con el esquema, datos iniciales y contraseñas hasheadas con bcrypt:
```Bash
python backend/init_db.py
```
## 🚀 ¿Cómo Ejecutar el Sistema?

Para trabajar con el sistema completo, mantén dos terminales abiertas en paralelo:
Paso A: Encender el Servidor Backend (FastAPI)

Desde la raíz del proyecto, activa el entorno virtual (si aún no está activo) y entra a backend:

```Bash
    source .venv/bin/activate
    cd backend
```
Inicia el servidor en modo desarrollo:
 ```Bash
    uvicorn main:app --reload
```
API disponible en: http://127.0.0.1:8000

Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

Paso B: Levantar el Frontend (Interfaz Web)

Abre otra pestaña o ventana en tu terminal y ubícate en la carpeta frontend:
```Bash
cd frontend
```
Levanta un servidor local estático (o usa la extensión Live Server de VS Code):
```Bash
python -m http.server 5500
```
Abre en tu navegador http://127.0.0.1:5500/login.html (o http://127.0.0.1:5500).

3. Abre tu navegador favorito (Firefox / Chrome) e ingresa a:
👉 http://127.0.0.1:5500/frontend/login.html

## 🔑 Usuarios de Prueba del Sistema
El sistema cuenta con perfiles precargados para probar los diferentes niveles de jerarquía (RBAC):

|Usuario|Contraseña|Nivel / Rol|Permisos Principales|
|-------|----------|-----------|--------------------|
|Alumno1|1111|Nivel 1 (Alumno)|Visualización de expediente y kardex personal.|
|Maestro1|2222Nivel 2 (Maestro)|Consulta de grupos y asignaciones académicas.|
|super1|3333|Nivel 3 (Director)|CRUD completo de usuarios, materias y horarios.|
|admin|4444|Nivel 4 (Admin)|Control total del sistema e infraestructura.|
