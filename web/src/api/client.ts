export interface Envelope<T> {
  ok: boolean
  data: T | null
  error: { code: string; message: string; hint?: string } | null
}

// 未登录处理：由路由层注册回调（client 不反向依赖 router/store，避免循环依赖）
let unauthorizedHandler: (() => void) | null = null
export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler
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
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })

  let body: Envelope<T> | null = null
  try {
    body = (await resp.json()) as Envelope<T>
  } catch {
    // 非 JSON 响应：body 保持 null，后面按 HTTP 状态退化处理
  }

  if (!resp.ok || !body?.ok) {
    const code = body?.error?.code ?? 'NETWORK'
    // 未登录：交给路由层注册的回调处理，避免每个调用点都写跳转
    if (resp.status === 401 && !path.includes('/auth/login')) {
      unauthorizedHandler?.()
    }
    throw new ApiError(resp.status, code, body?.error?.message ?? `HTTP ${resp.status}`)
  }
  return body.data as T
}

export interface PageQuery { page?: number; page_size?: number }
export const qs = (values: object) => { const q = new URLSearchParams(); Object.entries(values).forEach(([k,v]) => { if (v !== undefined && v !== null && v !== '') q.set(k, String(v)) }); return q.size ? `?${q}` : '' }
