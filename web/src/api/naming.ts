import { api } from './client'

export interface NamingVariable { name: string; label: string; example: string; group: string }
export interface NamingConfig {
  movie_format: string
  tv_format: string
  variety_format: string
  defaults: { movie_format: string; tv_format: string; variety_format: string }
  variables: NamingVariable[]
}
export interface NamingPreview {
  valid: boolean
  message: string
  relative_path: string
  folder?: string
  filename?: string
}
export interface NamingPreviewBody {
  template?: string
  media_type?: string
  title?: string
  year?: number | null
  season?: number | null
  episode?: number | null
  episode_title?: string
  total_episodes?: number | null
  extension?: string
  quality_bucket?: string
  part?: string | null
}

export const namingApi = {
  get: () => api<NamingConfig>('/api/v1/naming'),
  update: (body: { movie_format: string; tv_format: string; variety_format?: string }) =>
    api<NamingConfig>('/api/v1/naming', { method: 'PUT', body: JSON.stringify(body) }),
  preview: (body: NamingPreviewBody) =>
    api<NamingPreview>('/api/v1/naming/preview', { method: 'POST', body: JSON.stringify(body) }),
}
