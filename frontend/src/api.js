const API = "/api/v1";
function expireSession(path) {
    if (path === "/auth/login")
        return;
    localStorage.removeItem("kylin-token");
    localStorage.removeItem("kylin-user");
    localStorage.removeItem("kylin-mode");
    if (window.location.pathname !== "/login") {
        window.location.href = "/login?expired=1";
    }
}
async function readPayload(response) {
    try {
        return await response.json();
    }
    catch {
        return { error: { message: `HTTP ${response.status}` } };
    }
}
function raiseIfFailed(response, payload, path) {
    if (response.ok)
        return;
    if (response.status === 401) {
        expireSession(path);
        throw new Error(path === "/auth/login" ? payload.error?.message || "登录失败" : "登录已过期，请重新登录");
    }
    throw new Error(payload.error?.message || `HTTP ${response.status}`);
}
export async function apiAs(path, token, options = {}) {
    const response = await fetch(`${API}${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    });
    const payload = await readPayload(response);
    raiseIfFailed(response, payload, path);
    return payload.data;
}
export async function apiEnvelope(path, options = {}) {
    const token = localStorage.getItem("kylin-token");
    const response = await fetch(`${API}${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    });
    const payload = await readPayload(response);
    raiseIfFailed(response, payload, path);
    return payload;
}
export async function api(path, options = {}) {
    return apiAs(path, localStorage.getItem("kylin-token"), options);
}
