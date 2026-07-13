const API = "/api/v1";
export async function apiAs(path, token, options = {}) {
    const response = await fetch(`${API}${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    });
    const payload = await response.json();
    if (!response.ok)
        throw new Error(payload.error?.message || `HTTP ${response.status}`);
    return payload.data;
}
export async function apiEnvelope(path, options = {}) {
    const token = localStorage.getItem("kylin-token");
    const response = await fetch(`${API}${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    });
    const payload = await response.json();
    if (!response.ok)
        throw new Error(payload.error?.message || `HTTP ${response.status}`);
    return payload;
}
export async function api(path, options = {}) {
    return apiAs(path, localStorage.getItem("kylin-token"), options);
}
