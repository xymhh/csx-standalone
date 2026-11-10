import { api, qs, type PageQuery } from './client'

export interface MediaRef { tmdb_id: number | null; title: string; type: string }
export interface Subscription { id: number; media_id: number; scope: Record<string, unknown>; quality_pref: Record<string, unknown>; state: string; source: string; created_at: string; updated_at: string; media?: MediaRef }
export interface Candidate { id: number; subscription_id: number; provider: string; share_url: string; state: string; score: number; payload: Record<string, unknown>; created_at: string }

export interface ProgressEpisode { episode: number; title: string | null; air_date: string | null; aired: boolean; owned: boolean; file: { file_id: number; path: string; size: number; sha1: string | null; quality_bucket: string; created_at: string } | null }
export interface ProgressSeason { season: number; episodes: ProgressEpisode[] }
export interface ProgressItem { media_id: number; title: string; type?: string; year?: number | null; overview?: string; poster_url?: string; rating?: number | null; subscription_id?: number | null; subscription_state?: string | null; aired_count: number; owned_count: number; missing: { season: number; episode: number }[]; seasons: ProgressSeason[] }

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

export const candidatesApi = {
  list: (params: PageQuery & { subscription_id?: number; state?: string } = {}) => api<Candidate[]>(`/api/v1/candidates${qs(params)}`),
  accept: (id: number) => api<{ candidate_id: number; task_id: number; state: string }>(`/api/v1/candidates/${id}/accept`, { method: 'POST' }),
  ignore: (id: number) => api<{ candidate_id: number; state: string }>(`/api/v1/candidates/${id}/ignore`, { method: 'POST' }),
}
