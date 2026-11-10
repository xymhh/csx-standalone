import { api, qs, type PageQuery } from './client'

export interface Task { id: number; subscription_id: number; resource_id: number; idempotency_key: string; state: string; stage?: string; stage_label?: string; attempt: number; next_retry_at: string | null; last_error: string | null; failure_label?: string; failure_detail?: string; created_at: string; updated_at: string }
export interface TransferTaskEnriched extends Task {
  media_id: number | null
  media_title: string
  media_year: number | null
  media_type: string
  poster_url: string
  season: number | null
  episode: number | null
  provider: string
  quality_bucket: string
  display_name: string
  file_path: string
  size: number | null
  landed: boolean
}
export interface HistoryGroup {
  key: string
  media_id: number | null
  title: string
  year: number | null
  type: string
  poster_url: string
  counts: { succeeded: number; failed: number; skipped: number }
  failure_labels: { label: string; count: number }[]
  providers: string[]
  total_size: number
  latest_at: string
  records: TransferTaskEnriched[]
}
export interface HistoryPage {
  groups: HistoryGroup[]
  total: number
  records_total: number
  page: number
  page_size: number
  filter_options: { providers: string[] }
}

export const tasksApi = { list: (params: PageQuery & { state?: string } = {}) => api<TransferTaskEnriched[]>(`/api/v1/tasks${qs(params)}`), retry: (id: number) => api<Task>(`/api/v1/tasks/${id}/retry`, { method: 'POST' }), cancel: (id: number) => api<Task>(`/api/v1/tasks/${id}/cancel`, { method: 'POST' }) }
export const historyApi = { list: (params: PageQuery & { provider?: string; start?: string; end?: string; state?: string; q?: string } = {}) => api<HistoryPage>(`/api/v1/history${qs(params)}`), retryBatch: (ids: number[]) => api<{ retried: number[] }>('/api/v1/history/retry_batch', { method: 'POST', body: JSON.stringify(ids) }), retryAllFailed: () => api<{ retried: number }>('/api/v1/history/retry_failed', { method: 'POST' }) }
