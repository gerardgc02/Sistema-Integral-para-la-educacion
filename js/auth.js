// =========================================================================
// MÓDULO DE AUTENTICACIÓN Y GESTIÓN DE SESIÓN (auth.js)
// =========================================================================

const SESSION_KEY = "rbac_active_session";

const ROLE_META = {
  1: { name: "Alumno",      color: "var(--lvl1)" },
  2: { name: "Maestro",       color: "var(--lvl2)" },
  3: { name: "Director",    color: "var(--lvl3)" },
  4: { name: "Administrador", color: "var(--lvl4)" }
};

const USERS_DB = [
  { user: "Alumno1", pass: "1111", fullName: "Carlos Méndez",  level: 1 },
  { user: "Maestro1",  pass: "2222", fullName: "Ana Torres",     level: 2 },
  { user: "super1",    pass: "3333", fullName: "Roberto Silva",  level: 3 },
  { user: "admin",     pass: "4444", fullName: "Luis Guzmán",    level: 4 }
];

// Valida credenciales y guarda la sesión en memoria del navegador
function loginUser(username, password) {
  const foundUser = USERS_DB.find(
    u => u.user === username.trim() && u.pass === password
  );

  if (!foundUser) return null;

  // Guardamos una copia sin la contraseña en sessionStorage
  const sessionPayload = {
    user: foundUser.user,
    fullName: foundUser.fullName,
    level: foundUser.level,
    role: foundUser.role
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
    window.location.href = "login.html";
    return null;
  }
  return session;
}

// Destruye la sesión y regresa al login
function logoutUser() {
  sessionStorage.removeItem(SESSION_KEY);
  window.location.href = "login.html";
}