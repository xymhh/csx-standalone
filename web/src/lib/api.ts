export interface Envelope<T> {
  ok: boolean
  data: T | null
  error: { code: string; message: string; hint?: string } | null
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message)
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })

  let body: Envelope<T> | null = null
  try {
    body = (await resp.json()) as Envelope<T>
  } catch {
    body = null
  }

  if (!resp.ok || !body?.ok) {
    const code = body?.error?.code ?? 'NETWORK'
    // 未登录：交给路由守卫处理，避免每个调用点都写跳转
    if (resp.status === 401 && !path.includes('/auth/login')) {
      window.dispatchEvent(new CustomEvent('csx:unauthorized'))
    }
    throw new ApiError(resp.status, code, body?.error?.message ?? `HTTP ${resp.status}`)
  }
  return body.data as T
}

export interface Me {
  username: string
}

export const authApi = {
  login: (username: string, password: string) =>
    api<Me>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => api<null>('/api/v1/auth/logout', { method: 'POST' }),
  me: () => api<Me>('/api/v1/auth/me'),
  changePassword: (old_password: string, new_password: string) =>
    api<{ changed: boolean }>('/api/v1/auth/password', {
      method: 'POST',
      body: JSON.stringify({ old_password, new_password }),
    }),
}
