const API = "/api/v1";

interface Envelope<T> { data: T; meta: { mode: string; is_demo: boolean }; error: unknown }

export async function apiAs<T>(path: string, token: string | null, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || `HTTP ${response.status}`);
  return payload.data as T;
}

export async function apiEnvelope<T>(path: string, options: RequestInit = {}): Promise<Envelope<T>> {
  const token = localStorage.getItem("kylin-token");
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || `HTTP ${response.status}`);
  return payload as Envelope<T>;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  return apiAs<T>(path, localStorage.getItem("kylin-token"), options);
}

export interface Task { id: string; goal: string; mode: string; state: string; version: number }
export interface AuditEvent { id?: string; event_id?: string; event_type: string; created_at?: string; timestamp?: string; payload: Record<string, unknown> }
