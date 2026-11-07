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
    credentials: 'include',
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


export interface MediaRef { tmdb_id: number | null; title: string; type: string }
export interface Subscription { id: number; media_id: number; scope: Record<string, unknown>; quality_pref: Record<string, unknown>; state: string; source: string; created_at: string; updated_at: string; media?: MediaRef }
export interface Candidate { id: number; subscription_id: number; provider: string; share_url: string; state: string; score: number; payload: Record<string, unknown>; created_at: string }
export interface Task { id: number; subscription_id: number; resource_id: number; idempotency_key: string; state: string; attempt: number; next_retry_at: string | null; last_error: string | null; created_at: string; updated_at: string }
export interface ProgressEpisode { episode: number; title: string | null; air_date: string | null; aired: boolean; owned: boolean; file: { path: string; size: number; sha1: string; quality_bucket: string } | null }
export interface ProgressSeason { season: number; episodes: ProgressEpisode[] }
export interface ProgressItem { media_id: number; title: string; aired_count: number; owned_count: number; missing: { season: number; episode: number }[]; seasons: ProgressSeason[] }
export interface LibraryFile { id: number; media_id: number; path: string; size: number; sha1: string; quality_bucket: string; created_at: string }
export interface LibraryServer { provider: string; configured: boolean; valid: boolean | null }
export interface Account { id: number; provider: string; name: string; has_credential: boolean; masked: string }
export interface AccountTest { valid: boolean; provider: string; message: string }
export interface DoctorReport { database?: { ok: boolean; size_bytes: number; error: string }; accounts?: Array<Record<string, unknown>>; scheduler?: { running: boolean; active_workers: number; waiting_queue_depth: number }; disk?: Record<string, unknown> }
export type SettingSection = 'baseline' | 'sources' | 'transfer' | 'strm' | 'notify' | 'advanced'
export type Settings = Record<SettingSection, Record<string, unknown>>
export interface PageQuery { page?: number; page_size?: number }
const qs = (values: object) => { const q = new URLSearchParams(); Object.entries(values).forEach(([k,v]) => { if (v !== undefined && v !== null && v !== '') q.set(k, String(v)) }); return q.size ? `?${q}` : '' }

export const subscriptionsApi = {
  list: (params: PageQuery & { state?: string; keyword?: string } = {}) => api<Subscription[]>(`/api/v1/subscriptions${qs(params)}`),
  get: (id: number) => api<Subscription & { matches?: Candidate[] }>(`/api/v1/subscriptions/${id}`),
  create: (body: { media_id?: number; tmdb_id?: number; scope?: Record<string, unknown>; quality_pref?: Record<string, unknown> | string; source?: string }) => api<Subscription>('/api/v1/subscriptions', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: number, body: { state?: string; scope?: Record<string, unknown>; quality_pref?: Record<string, unknown> | string }) => api<Subscription>(`/api/v1/subscriptions/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (id: number) => api<{ deleted: boolean }>(`/api/v1/subscriptions/${id}`, { method: 'DELETE' }),
  sync: (id: number) => api<{ triggered: boolean; task_id: string; message: string }>(`/api/v1/subscriptions/${id}/sync`, { method: 'POST' }),
}
export const progressApi = { overview: () => api<ProgressItem[]>('/api/v1/progress'), getDetail: (id: number) => api<ProgressItem>(`/api/v1/progress/${id}`) }
export const candidatesApi = {
  list: (params: PageQuery & { subscription_id?: number; state?: string } = {}) => api<Candidate[]>(`/api/v1/candidates${qs(params)}`),
  accept: (id: number) => api<{ candidate_id: number; task_id: number; state: string }>(`/api/v1/candidates/${id}/accept`, { method: 'POST' }),
  ignore: (id: number) => api<{ candidate_id: number; state: string }>(`/api/v1/candidates/${id}/ignore`, { method: 'POST' }),
}
export const tasksApi = { list: (params: PageQuery & { state?: string } = {}) => api<Task[]>(`/api/v1/tasks${qs(params)}`), retry: (id: number) => api<Task>(`/api/v1/tasks/${id}/retry`, { method: 'POST' }), cancel: (id: number) => api<Task>(`/api/v1/tasks/${id}/cancel`, { method: 'POST' }) }
export const historyApi = { list: (params: PageQuery & { provider?: string; start?: string; end?: string; state?: string } = {}) => api<Task[]>(`/api/v1/history${qs(params)}`), retryBatch: (ids: number[]) => api<{ retried: number[] }>('/api/v1/history/retry_batch', { method: 'POST', body: JSON.stringify(ids) }) }
export const libraryApi = { listFiles: (params: PageQuery & { media_id?: number } = {}) => api<LibraryFile[]>(`/api/v1/library/files${qs(params)}`), getServers: () => api<LibraryServer[]>('/api/v1/library/servers') }
export const settingsApi = { getAll: () => api<Settings>('/api/v1/settings'), getSection: (section: SettingSection) => api<Record<string, unknown>>(`/api/v1/settings/${section}`), updateSection: (section: SettingSection, body: Record<string, unknown>) => api<Record<string, unknown>>(`/api/v1/settings/${section}`, { method: 'PUT', body: JSON.stringify(body) }), testProvider: (provider: string) => api<AccountTest>(`/api/v1/settings/test/${encodeURIComponent(provider)}`, { method: 'POST' }) }
export const accountsApi = { list: () => api<Account[]>('/api/v1/accounts'), create: (body: { provider: string; credential: string; name: string }) => api<Account>('/api/v1/accounts', { method: 'POST', body: JSON.stringify(body) }), update: (id: number, body: { credential?: string; name?: string }) => api<Account>(`/api/v1/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }), delete: (id: number) => api<{ deleted: boolean }>(`/api/v1/accounts/${id}`, { method: 'DELETE' }), test: (id: number) => api<AccountTest>(`/api/v1/accounts/${id}/test`, { method: 'POST' }) }
export const doctorApi = { diagnose: () => api<DoctorReport>('/api/v1/doctor') }
