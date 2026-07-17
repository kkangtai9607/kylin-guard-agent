const API = "/api/v1";

interface Envelope<T> { data: T; meta: { mode: string; is_demo: boolean }; error: unknown }

function expireSession(path: string) {
  if (path === "/auth/login") return;
  localStorage.removeItem("kylin-token");
  localStorage.removeItem("kylin-user");
  localStorage.removeItem("kylin-mode");
  if (window.location.pathname !== "/login") {
    window.location.href = "/login?expired=1";
  }
}

async function readPayload(response: Response) {
  try {
    return await response.json();
  } catch {
    return { error: { message: `HTTP ${response.status}` } };
  }
}

function raiseIfFailed(response: Response, payload: { error?: { message?: string } }, path: string) {
  if (response.ok) return;
  if (response.status === 401) {
    expireSession(path);
    throw new Error(path === "/auth/login" ? payload.error?.message || "登录失败" : "登录已过期，请重新登录");
  }
  throw new Error(payload.error?.message || `HTTP ${response.status}`);
}

export async function apiAs<T>(path: string, token: string | null, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  const payload = await readPayload(response);
  raiseIfFailed(response, payload, path);
  return payload.data as T;
}

export async function apiEnvelope<T>(path: string, options: RequestInit = {}): Promise<Envelope<T>> {
  const token = localStorage.getItem("kylin-token");
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  const payload = await readPayload(response);
  raiseIfFailed(response, payload, path);
  return payload as Envelope<T>;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  return apiAs<T>(path, localStorage.getItem("kylin-token"), options);
}

export interface Task { id: string; goal: string; mode: string; state: string; version: number }
export interface AuditEvent { id?: string; event_id?: string; event_type: string; created_at?: string; timestamp?: string; payload: Record<string, unknown> }
