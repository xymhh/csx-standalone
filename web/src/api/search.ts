import { api, qs } from './client'

export interface SearchSourceStatus { id: string; name: string; status: 'ok' | 'empty' | 'error' | 'timeout' | 'disabled' | 'skipped'; count: number; message: string; elapsed_ms: number }
export interface SearchSourceOption { id: string; name: string; icon?: string; order: number; enabled: boolean }
export interface SearchResultItem {
  id: string
  source: string
  source_name: string
  title: string
  url: string
  urls: string[]
  password: string
  resource_type: string
  resource_type_name: string
  size: number | null
  size_text: string
  update_time: string
  description: string
  source_url: string
  media_page_url: string
  fansub: string
  needs_unlock: boolean
  unlock_points: number
  can_transfer: boolean
  duplicate_of: string
}
export interface SearchResponse { query: string; sources: SearchSourceStatus[]; items: SearchResultItem[]; total: number; elapsed_ms: number }
export const searchApi = {
  sources: () => api<{ sources: SearchSourceOption[] }>('/api/v1/search/sources'),
  run: (params: { q: string; type?: string; year?: number | null; season?: number | null; sources?: string; limit?: number }) => api<SearchResponse>(`/api/v1/search${qs(params)}`),
}
