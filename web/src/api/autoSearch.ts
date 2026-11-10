import { api } from './client'

export interface AutoSearchSettings {
  enabled: boolean
  interval_hours: number
  auto_transfer: boolean
  max_per_round: number
  per_subscription_limit: number
}

export interface AutoSearchRunResult {
  candidates: number
  tasks: number[]
  skipped: Record<string, number>
  total?: number
  processed?: Array<{ ok: boolean; subscription_id: number; candidates?: number; tasks?: number[]; message?: string }>
}

export const autoSearchApi = {
  settings: () => api<AutoSearchSettings>('/api/v1/auto_search/settings'),
  save: (body: Partial<AutoSearchSettings>) =>
    api<AutoSearchSettings>('/api/v1/auto_search/settings', { method: 'PUT', body: JSON.stringify(body) }),
  run: (body: { subscription_id?: number; force?: boolean; dry_run?: boolean } = { force: true }) =>
    api<{ ok: boolean; mode: string; result: AutoSearchRunResult }>('/api/v1/auto_search/run', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
