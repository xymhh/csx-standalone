import { api, qs, type PageQuery } from './client'

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

export const drivesApi = {
  folders: (accountId: number, parentId = '', parentPath = '') => api<DriveFolder[]>(`/api/v1/drives/${accountId}/folders${qs({ parent_id: parentId, parent_path: parentPath })}`),
  createFolder: (accountId: number, body: { parent_id: string; parent_path: string; name: string }) => api<DriveFolder>(`/api/v1/drives/${accountId}/folders`, { method: 'POST', body: JSON.stringify(body) }),
  inspectShare: (body: { provider: '115' | 'quark' | 'auto'; share_url: string; password?: string }) => api<{ provider: string; share_title: string; files: ShareInspectFile[] }>('/api/v1/drives/share/inspect', { method: 'POST', body: JSON.stringify(body) }),
  transferShare: (body: { account_id: number; share_url: string; password?: string; file_ids: string[]; target_dir: string; media_id?: number }) => api<{ task_id: number; state: string }>('/api/v1/drives/share/transfer', { method: 'POST', body: JSON.stringify(body) }),
}

export const libraryApi = { listFiles: (params: PageQuery & { media_id?: number } = {}) => api<LibraryFile[]>(`/api/v1/library/files${qs(params)}`), getServers: () => api<LibraryServer[]>('/api/v1/library/servers') }

export const accountsApi = {
  list: () => api<Account[]>('/api/v1/accounts'),
  create: (body: { provider: string; credential: string; name: string; is_enabled?: boolean; is_primary?: boolean; transfer_path?: string; media_path?: string }) => api<Account>('/api/v1/accounts', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: number, body: { credential?: string; name?: string; is_enabled?: boolean; is_primary?: boolean; transfer_path?: string; media_path?: string }) => api<Account>(`/api/v1/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (id: number) => api<{ deleted: boolean }>(`/api/v1/accounts/${id}`, { method: 'DELETE' }),
  test: (id: number) => api<AccountTest>(`/api/v1/accounts/${id}/test`, { method: 'POST' }),
  startQrcode: (provider: '115' | 'quark') => api<QrcodeStartResponse>('/api/v1/accounts/qrcode/start', { method: 'POST', body: JSON.stringify({ provider }) }),
  checkQrcode: (body: { provider: '115' | 'quark'; token_data: Record<string, string>; name: string; auto_save: boolean }) => api<QrcodeCheckResponse>('/api/v1/accounts/qrcode/check', { method: 'POST', body: JSON.stringify(body) }),
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
