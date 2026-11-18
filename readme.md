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
1. Prerrequisitos
Asegúrate de tener instalado Python 3.10+ en tu equipo.
2. Instalar Dependencias del BackendAbre tu terminal en la raíz del proyecto e instala los paquetes necesarios para FastAPI y Uvicorn:
```Bash
 pip install fastapi uvicorn
```
3. Inicializar la Base de DatosEjecuta el script de configuración para crear y poblar la base de datos SQLite con los esquemas relacionales y usuarios de prueba:
```Bash
python3 backend/init_db.py
```

## 🚀 ¿Cómo Ejecutar el Sistema?
Para que el frontend se comunique correctamente con la base de datos, debes mantener dos servicios corriendo en paralelo:

### Paso A: Encender el Servidor Backend (FastAPI)
1. Ubícate en la carpeta /backend desde tu terminal:
```Bash
cd backend
```
2. Inicia el servidor de desarrollo con Uvicorn:Bashuvicorn main:app --reload
El servidor estará disponible en http://127.0.0.1:8000.Puedes probar la documentación interactiva en http://127.0.0.1:8000/docs.

### Paso B: Levantar el Frontend (Interfaz Web)
1. Abre una nueva pestaña o ventana en tu terminal y colócate en la carpeta raíz del proyecto.
2. Sirve los archivos estáticos de la carpeta frontend mediante un servidor local (puedes usar la extensión Live Server de VS Code apuntando a login.html, o levantar un servidor web rápido con Python):
```Bash
python3 -m http.server 5500
```
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
