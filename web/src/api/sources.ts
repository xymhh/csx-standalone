import { api } from './client'

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
  searchable?: boolean
  cols?: number
  suffix?: string
  source?: string
  show?: string
  accountKey?: string
  compact?: boolean
  dynamicOptions?: { scope?: string; key?: string; refreshable?: boolean }
}
export interface SearchSourceGroup { title: string; fields: SearchSourceField[] }
export interface SearchSourceSchema { id: string; name: string; order: number; enabled?: boolean; groups: SearchSourceGroup[] }
export interface SearchSourceTest { valid: boolean; elapsed_ms: number; message: string }
export interface SourceOption { title: string; value: string }
export interface SourceAccountDetail { label: string; value: string }
export interface SourceAccountCard {
  connected?: boolean
  name?: string
  username?: string
  email?: string
  avatar?: string
  points?: { label?: string; available?: number | string } | number | null
  level?: string
  is_vip?: boolean
  error?: string
  extra?: Record<string, unknown>
  user?: { name?: string; avatar?: string; badge?: string; is_vip?: boolean; membership_supported?: boolean }
  details?: SourceAccountDetail[]
}

export interface SourceOption {
  id: string
  name: string
}

export interface SourceGlobalSettings {
  search_proxy: string
  search_proxy_username: string
  search_proxy_password: string
  search_source_order: string[]
  resource_type_order: string[]
  magnet_metadata_url_template: string
  source_options: SourceOption[]
  resource_options: SourceOption[]
}

export interface SourceMeta {
  accounts: Record<string, SourceAccountCard>
  options: Record<string, { status?: string; items?: SourceOption[]; error?: string; channels?: SourceOption[]; plugins?: SourceOption[] }>
}
export interface HdhiveOauthStart { authorize_url: string; state: string; response_mode: string; expires_in: number }
export interface HdhiveOauthToken {
  access_token: string
  refresh_token: string
  token_expires_at: number
  expires_in: number
  refresh_expires_in: number
  scope: string
  user: Record<string, unknown>
  warning: string
}

export const searchSourcesApi = {
  schema: () => api<SearchSourceSchema[]>('/api/v1/settings/sources/schema'),
  save: (body: Record<string, Record<string, unknown>>) => api<SearchSourceSchema[]>('/api/v1/settings/sources', { method: 'PUT', body: JSON.stringify(body) }),
  test: (sourceId: string) => api<SearchSourceTest>(`/api/v1/settings/sources/test/${encodeURIComponent(sourceId)}`, { method: 'POST' }),
  meta: () => api<SourceMeta>('/api/v1/settings/sources/meta'),
  getGlobal: () => api<SourceGlobalSettings>('/api/v1/settings/sources/global'),
  saveGlobal: (body: Partial<SourceGlobalSettings>) =>
    api<SourceGlobalSettings>('/api/v1/settings/sources/global', { method: 'POST', body: JSON.stringify(body) }),
  refreshAccount: (sourceId: string) => api<SourceAccountCard>(`/api/v1/settings/sources/account/${encodeURIComponent(sourceId)}`, { method: 'POST' }),
  refreshOptions: (scope: string, key: string) => api<{ status?: string; items?: SourceOption[]; error?: string }>(`/api/v1/settings/sources/options/${encodeURIComponent(scope)}/${encodeURIComponent(key)}`, { method: 'POST' }),
  hdhiveOauthStart: (body: { client_id: string; redirect_uri: string; response_mode: string; scope?: string }) => api<HdhiveOauthStart>('/api/v1/settings/sources/hdhive/oauth/start', { method: 'POST', body: JSON.stringify(body) }),
  hdhiveOauthExchange: (body: { client_id: string; redirect_uri: string; response_mode: string; app_secret: string; callback: string }) => api<HdhiveOauthToken>('/api/v1/settings/sources/hdhive/oauth/exchange', { method: 'POST', body: JSON.stringify(body) }),
}
