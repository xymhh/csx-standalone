export interface Envelope<T> {
  ok: boolean
  data: T | null
  error: { code: string; message: string; hint?: string } | null
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  const body = (await resp.json()) as Envelope<T>
  if (!resp.ok || !body.ok) {
    throw new Error(body.error?.message ?? `HTTP ${resp.status}`)
  }
  return body.data as T
}
