import { api } from './client'
import type { AccountTest } from './drives'

export interface DoctorReport { database?: { ok: boolean; size_bytes: number; error: string }; accounts?: Array<Record<string, unknown>>; scheduler?: { running: boolean; active_workers: number; waiting_queue_depth: number }; disk?: Record<string, unknown> }
export type SettingSection =
  | 'baseline'
  | 'sources'
  | 'transfer'
  | 'strm'
  | 'notify'
  | 'advanced'
  | 'category'

export interface CrossTransferSettings {
  enabled: boolean
  library_drive: string
  download_threads: number
  max_concurrent: number
  direct_stream: boolean
  cache_dir: string
  cache_free_gb: number
  drive_options: { value: string; label: string; primary: boolean }[]
}

export type Settings = Record<SettingSection, Record<string, unknown>>

export const settingsApi = { getAll: () => api<Settings>('/api/v1/settings'), getSection: (section: SettingSection) => api<Record<string, unknown>>(`/api/v1/settings/${section}`), updateSection: (section: SettingSection, body: Record<string, unknown>) => api<Record<string, unknown>>(`/api/v1/settings/${section}`, { method: 'PUT', body: JSON.stringify(body) }), testProvider: (provider: string) => api<AccountTest>(`/api/v1/settings/test/${encodeURIComponent(provider)}`, { method: 'POST' }) }

export const crossTransferApi = {
  get: () => api<CrossTransferSettings>('/api/v1/settings/cross/config'),
  save: (body: Partial<CrossTransferSettings>) =>
    api<CrossTransferSettings>('/api/v1/settings/cross/config', { method: 'POST', body: JSON.stringify(body) }),
}

export const doctorApi = { diagnose: () => api<DoctorReport>('/api/v1/doctor') }
