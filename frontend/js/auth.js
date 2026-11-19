// =========================================================================
// MÓDULO DE AUTENTICACIÓN CONECTADO AL BACKEND FastAPI (auth.js)
// =========================================================================

const SESSION_KEY = "rbac_active_session";
const API_BASE_URL = "http://127.0.0.1:8000/api";

const ROLE_META = {
  1: { name: "Alumno",        color: "var(--lvl1)" },
  2: { name: "Maestro",       color: "var(--lvl2)" },
  3: { name: "Director",      color: "var(--lvl3)" },
  4: { name: "Administrador", color: "var(--lvl4)" }
};

// Valida credenciales consumiendo la API REST de FastAPI de forma asíncrona
async function loginUser(username, password) {
  try {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username: username.trim(),
        password: password
      })
    });

    if (!response.ok) {
      return null; // Credenciales inválidas
    }

    const userData = await response.json();

    const sessionPayload = {
      id: userData.id,
      user: userData.user,
      fullName: userData.fullName,
      level: userData.level
    };

    sessionStorage.setItem(SESSION_KEY, JSON.stringify(sessionPayload));
    return sessionPayload;

  } catch (error) {
    console.error("Error de conexión con el backend:", error);
    alert("No se pudo conectar con el servidor backend. Asegúrate de que FastAPI esté corriendo en http://127.0.0.1:8000");
    return null;
  }
}

// Recupera la sesión activa desde sessionStorage
function getActiveSession() {
  const raw = sessionStorage.getItem(SESSION_KEY);
  return raw ? JSON.parse(raw) : null;
}

// Guardia de ruta: si no hay sesión, redirige al login
function requireAuth() {
  const session = getActiveSession();
  if (!session) {
    window.location.href = "login.html";
    return null;
  }
  return session;
}

// Cierra sesión y redirige
function logoutUser() {
  sessionStorage.removeItem(SESSION_KEY);
  window.location.href = "login.html";
}
