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
export interface ProgressEpisode { episode: number; title: string | null; air_date: string | null; aired: boolean; owned: boolean; file: { file_id: number; path: string; size: number; sha1: string | null; quality_bucket: string; created_at: string } | null }
export interface ProgressSeason { season: number; episodes: ProgressEpisode[] }
export interface ProgressItem { media_id: number; title: string; type?: string; year?: number | null; overview?: string; poster_url?: string; rating?: number | null; aired_count: number; owned_count: number; missing: { season: number; episode: number }[]; seasons: ProgressSeason[] }
export interface DriveFolder { id: string; name: string; path: string; has_children: boolean }
export interface ShareInspectFile { id: string; name: string; size: number; is_dir: boolean }
export interface LibraryFile { id: number; media_id: number; path: string; size: number; sha1: string; quality_bucket: string; provider?: string; created_at: string }
export interface LibraryServer { provider: string; configured: boolean; valid: boolean | null }
export interface AccountProfile {
  connected?: boolean
  user_name?: string
  avatar?: string
  is_vip?: boolean
  vip_expire?: string
  total_space?: string
  used_space?: string
  remaining_space?: string
}

export interface Account {
  id: number
  provider: string
  name: string
  is_enabled: boolean
  is_primary: boolean
  transfer_path: string
  media_path: string
  has_credential: boolean
  masked: string
  info?: AccountProfile
}

export interface AccountTest {
  valid: boolean
  provider: string
  message: string
  info?: AccountProfile
}
export interface QrcodeStartResponse { provider: '115' | 'quark'; qrcode: string; token_data: Record<string, string>; hint: string }
export interface QrcodeCheckResponse { status: 'waiting' | 'scanned' | 'success' | 'expired'; message: string; account: Account | null }
export interface DoctorReport { database?: { ok: boolean; size_bytes: number; error: string }; accounts?: Array<Record<string, unknown>>; scheduler?: { running: boolean; active_workers: number; waiting_queue_depth: number }; disk?: Record<string, unknown> }
export type SettingSection = 'baseline' | 'sources' | 'transfer' | 'strm' | 'notify' | 'advanced'
export interface SearchSourceField {
  key: string
  label: string
  type: string
  default: unknown
  value: unknown
  description: string
  hint?: string
  placeholder?: string
  options?: { title?: string; label?: string; value: string | number }[]
  items?: { title?: string; label?: string; value: string | number }[]
  min?: number
  max?: number
  step?: number
  multiple?: boolean
  cols?: number
}
export interface SearchSourceGroup { title: string; fields: SearchSourceField[] }
export interface SearchSourceSchema { id: string; name: string; order: number; enabled?: boolean; groups: SearchSourceGroup[] }
export interface SearchSourceTest { valid: boolean; elapsed_ms: number; message: string }
export interface TelegramShareLink { url: string; provider: string; password: string }
export interface TelegramParseResult { title: string; season: number | null; episode: number | null; links: TelegramShareLink[]; matched_subscription_id: number | null }
export interface TelegramStatus { enabled: boolean; channels: string[]; auto_transfer: boolean; ingested_count: number }
export type Settings = Record<SettingSection, Record<string, unknown>>
export interface PageQuery { page?: number; page_size?: number }
const qs = (values: object) => { const q = new URLSearchParams(); Object.entries(values).forEach(([k,v]) => { if (v !== undefined && v !== null && v !== '') q.set(k, String(v)) }); return q.size ? `?${q}` : '' }

export const subscriptionsApi = {
  list: (params: PageQuery & { state?: string; keyword?: string } = {}) => api<Subscription[]>(`/api/v1/subscriptions${qs(params)}`),
  get: (id: number) => api<Subscription & { matches?: Candidate[] }>(`/api/v1/subscriptions/${id}`),
  create: (body: {
    media_id?: number
    tmdb_id?: number
    title?: string
    media_type?: string
    year?: number
    season_number?: number
    episode_count?: number
    scope?: Record<string, unknown>
    quality_pref?: Record<string, unknown> | string
    source?: string
  }) => api<Subscription>('/api/v1/subscriptions', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: number, body: { state?: string; scope?: Record<string, unknown>; quality_pref?: Record<string, unknown> | string }) => api<Subscription>(`/api/v1/subscriptions/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (id: number) => api<{ deleted: boolean }>(`/api/v1/subscriptions/${id}`, { method: 'DELETE' }),
  sync: (id: number) => api<{ triggered: boolean; task_id: string; message: string }>(`/api/v1/subscriptions/${id}/sync`, { method: 'POST' }),
}
export const progressApi = { overview: () => api<ProgressItem[]>('/api/v1/progress'), getDetail: (id: number) => api<ProgressItem>(`/api/v1/progress/${id}`) }
export const drivesApi = {
  folders: (accountId: number, parentId = '', parentPath = '') => api<DriveFolder[]>(`/api/v1/drives/${accountId}/folders${qs({ parent_id: parentId, parent_path: parentPath })}`),
  createFolder: (accountId: number, body: { parent_id: string; parent_path: string; name: string }) => api<DriveFolder>(`/api/v1/drives/${accountId}/folders`, { method: 'POST', body: JSON.stringify(body) }),
  inspectShare: (body: { provider: '115' | 'quark' | 'auto'; share_url: string; password?: string }) => api<{ provider: string; share_title: string; files: ShareInspectFile[] }>('/api/v1/drives/share/inspect', { method: 'POST', body: JSON.stringify(body) }),
  transferShare: (body: { account_id: number; share_url: string; password?: string; file_ids: string[]; target_dir: string; media_id?: number }) => api<{ task_id: number; state: string }>('/api/v1/drives/share/transfer', { method: 'POST', body: JSON.stringify(body) }),
}
export const candidatesApi = {
  list: (params: PageQuery & { subscription_id?: number; state?: string } = {}) => api<Candidate[]>(`/api/v1/candidates${qs(params)}`),
  accept: (id: number) => api<{ candidate_id: number; task_id: number; state: string }>(`/api/v1/candidates/${id}/accept`, { method: 'POST' }),
  ignore: (id: number) => api<{ candidate_id: number; state: string }>(`/api/v1/candidates/${id}/ignore`, { method: 'POST' }),
}
export const tasksApi = { list: (params: PageQuery & { state?: string } = {}) => api<Task[]>(`/api/v1/tasks${qs(params)}`), retry: (id: number) => api<Task>(`/api/v1/tasks/${id}/retry`, { method: 'POST' }), cancel: (id: number) => api<Task>(`/api/v1/tasks/${id}/cancel`, { method: 'POST' }) }
export const historyApi = { list: (params: PageQuery & { provider?: string; start?: string; end?: string; state?: string } = {}) => api<Task[]>(`/api/v1/history${qs(params)}`), retryBatch: (ids: number[]) => api<{ retried: number[] }>('/api/v1/history/retry_batch', { method: 'POST', body: JSON.stringify(ids) }) }
export const libraryApi = { listFiles: (params: PageQuery & { media_id?: number } = {}) => api<LibraryFile[]>(`/api/v1/library/files${qs(params)}`), getServers: () => api<LibraryServer[]>('/api/v1/library/servers') }
export const settingsApi = { getAll: () => api<Settings>('/api/v1/settings'), getSection: (section: SettingSection) => api<Record<string, unknown>>(`/api/v1/settings/${section}`), updateSection: (section: SettingSection, body: Record<string, unknown>) => api<Record<string, unknown>>(`/api/v1/settings/${section}`, { method: 'PUT', body: JSON.stringify(body) }), testProvider: (provider: string) => api<AccountTest>(`/api/v1/settings/test/${encodeURIComponent(provider)}`, { method: 'POST' }) }
export const searchSourcesApi = {
  schema: () => api<SearchSourceSchema[]>('/api/v1/settings/sources/schema'),
  save: (body: Record<string, Record<string, unknown>>) => api<SearchSourceSchema[]>('/api/v1/settings/sources', { method: 'PUT', body: JSON.stringify(body) }),
  test: (sourceId: string) => api<SearchSourceTest>(`/api/v1/settings/sources/test/${encodeURIComponent(sourceId)}`, { method: 'POST' }),
}
export const telegramApi = {
  parse: (text: string, extra_urls: string[] = []) => api<TelegramParseResult>('/api/v1/tg/parse', { method: 'POST', body: JSON.stringify({ text, extra_urls }) }),
  ingest: (body: { channel: string; message_id?: number; text: string; auto_transfer?: boolean }) => api<{ ingested: boolean; resources_count: number; tasks_created: number[]; message: string }>('/api/v1/tg/ingest', { method: 'POST', body: JSON.stringify(body) }),
  status: () => api<TelegramStatus>('/api/v1/tg/status'),
}
export const accountsApi = {
  list: () => api<Account[]>('/api/v1/accounts'),
  create: (body: { provider: string; credential: string; name: string; is_enabled?: boolean; is_primary?: boolean; transfer_path?: string; media_path?: string }) => api<Account>('/api/v1/accounts', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: number, body: { credential?: string; name?: string; is_enabled?: boolean; is_primary?: boolean; transfer_path?: string; media_path?: string }) => api<Account>(`/api/v1/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (id: number) => api<{ deleted: boolean }>(`/api/v1/accounts/${id}`, { method: 'DELETE' }),
  test: (id: number) => api<AccountTest>(`/api/v1/accounts/${id}/test`, { method: 'POST' }),
  startQrcode: (provider: '115' | 'quark') => api<QrcodeStartResponse>('/api/v1/accounts/qrcode/start', { method: 'POST', body: JSON.stringify({ provider }) }),
  checkQrcode: (body: { provider: '115' | 'quark'; token_data: Record<string, string>; name: string; auto_save: boolean }) => api<QrcodeCheckResponse>('/api/v1/accounts/qrcode/check', { method: 'POST', body: JSON.stringify(body) }),
}

export interface DuplicateFile {
  id: number
  path: string
  size: number
  provider: string
  quality_bucket: string
  recommended: boolean
}

export interface DuplicateGroup {
  media_id: number
  title: string
  season: number
  episode: number
  keep_file_id: number
  files: DuplicateFile[]
}

export interface OrganizeMatchedItem {
  file_id: string
  name: string
  source_path: string
  size: number
  recognized: boolean
  media_id: number
  title: string
  season: number
  episode: number
  quality_bucket: string
  target_path: string
}

export interface OrganizeScanResult {
  matched: OrganizeMatchedItem[]
  unrecognized: Array<{ file_id: string; name: string; source_path: string; reason: string }>
}

export const duplicateApi = {
  list: () => api<DuplicateGroup[]>('/api/v1/library/duplicates'),
  clean: (file_ids: number[]) =>
    api<{ deleted: number[]; failed: Array<{ file_id: number; error: string }> }>(
      '/api/v1/library/duplicates/clean',
      { method: 'POST', body: JSON.stringify({ file_ids }) }
    ),
}

export const organizeApi = {
  scan: (body: { account_id: number; source_path: string }) =>
    api<OrganizeScanResult>('/api/v1/organize/scan', { method: 'POST', body: JSON.stringify(body) }),
  execute: (body: { account_id: number; source_path: string; file_ids: string[] }) =>
    api<{ moved: string[]; errors: Array<{ file_id: string; error: string }>; cleaned_directories: number }>(
      '/api/v1/organize/execute',
      { method: 'POST', body: JSON.stringify(body) }
    ),
}

export interface OfflineTask {
  id: string
  name: string
  size: number
  state: string
  status_text: string
  percent: number
  add_time: number
  file_id?: string
  parent_id?: string
}

export const offlineApi = {
  tasks: (accountId: number) =>
    api<OfflineTask[]>(`/api/v1/drives/offline/tasks${qs({ account_id: accountId })}`),
  add: (body: { account_id: number; url: string; parent_id?: string }) =>
    api<{ state: boolean }>('/api/v1/drives/offline/add', { method: 'POST', body: JSON.stringify(body) }),
  delete: (body: { account_id: number; hashes: string[] }) =>
    api<{ deleted: boolean }>('/api/v1/drives/offline/delete', { method: 'POST', body: JSON.stringify(body) }),
}

export interface TmdbItem {
  id: number
  title: string
  type: 'tv' | 'movie'
  year: number | null
  release_date: string
  vote_average: number
  overview: string
  poster_url: string | null
  backdrop_url: string | null
  popularity?: number
  seasons?: Array<{ season_number: number; name: string; episode_count: number; poster_url: string | null }>
}

export const tmdbApi = {
  trending: () => api<TmdbItem[]>('/api/v1/tmdb/trending'),
  popularTv: () => api<TmdbItem[]>('/api/v1/tmdb/popular/tv'),
  popularMovies: () => api<TmdbItem[]>('/api/v1/tmdb/popular/movies'),
  search: (query: string) => api<TmdbItem[]>(`/api/v1/tmdb/search?query=${encodeURIComponent(query)}`),
  detail: (type: string, id: number) => api<TmdbItem>(`/api/v1/tmdb/detail/${type}/${id}`),
}

export const doctorApi = { diagnose: () => api<DoctorReport>('/api/v1/doctor') }
