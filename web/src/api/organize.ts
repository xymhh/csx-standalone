import { api } from './client'

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
