// =========================================================================
// MÓDULO DE AUTENTICACIÓN Y GESTIÓN DE SESIÓN (auth.js)
// =========================================================================

const SESSION_KEY = "rbac_active_session";
const USERS_STORAGE_KEY = "rbac_users_database";

const ROLE_META = {
  1: { name: "Alumno",        color: "var(--lvl1)" },
  2: { name: "Maestro",       color: "var(--lvl2)" },
  3: { name: "Director",      color: "var(--lvl3)" },
  4: { name: "Administrador", color: "var(--lvl4)" }
};

// Usuarios por defecto (se cargan la primera vez)
const DEFAULT_USERS = [
  { user: "Alumno1",  pass: "1111", fullName: "Carlos Méndez",  level: 1 },
  { user: "Maestro1", pass: "2222", fullName: "Ana Torres",     level: 2 },
  { user: "super1",   pass: "3333", fullName: "Roberto Silva",  level: 3 },
  { user: "admin",    pass: "4444", fullName: "Luis Guzmán",    level: 4 }
];

// Función para obtener la base de datos actual de usuarios
function getUsersDB() {
  const stored = localStorage.getItem(USERS_STORAGE_KEY);
  if (!stored) {
    localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(DEFAULT_USERS));
    return DEFAULT_USERS;
  }
  return JSON.parse(stored);
}

// Función para guardar cambios en la base de datos de usuarios (CRUD)
function saveUsersDB(updatedUsers) {
  localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(updatedUsers));
}

// Inicializamos USERS_DB apuntando a la base persistente
let USERS_DB = getUsersDB();

// Valida credenciales y guarda la sesión en memoria del navegador
function loginUser(username, password) {
  USERS_DB = getUsersDB(); // Aseguramos leer la lista más reciente
  const foundUser = USERS_DB.find(
    u => u.user === username.trim() && u.pass === password
  );

  if (!foundUser) return null;

  const sessionPayload = {
    user: foundUser.user,
    fullName: foundUser.fullName,
    level: foundUser.level
  };

  sessionStorage.setItem(SESSION_KEY, JSON.stringify(sessionPayload));
  return sessionPayload;
}

// Recupera la sesión activa
function getActiveSession() {
  const raw = sessionStorage.getItem(SESSION_KEY);
  return raw ? JSON.parse(raw) : null;
}

// Guardia de ruta: si no hay sesión, redirige al login inmediatamente
function requireAuth() {
  const session = getActiveSession();
  if (!session) {
    window.location.href = "index.html";
    return null;
  }
  return session;
}

// Destruye la sesión y regresa al login
function logoutUser() {
  sessionStorage.removeItem(SESSION_KEY);
  window.location.href = "index.html";
}