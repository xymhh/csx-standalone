import { api } from './client'

export interface TelegramShareLink { url: string; provider: string; password: string }
export interface TelegramParseResult { title: string; season: number | null; episode: number | null; links: TelegramShareLink[]; matched_subscription_id: number | null }
export interface TelegramStatus { enabled: boolean; channels: string[]; auto_transfer: boolean; ingested_count: number }
export interface TgClientChannel { channel: string; last_message_id: number; scanned_at: string | null; ingested: number; error: string | null }
export interface TgClientStatus { enabled: boolean; configured: boolean; running: boolean; interval_minutes: number; last_scan_at: string | null; last_error: string | null; channels: TgClientChannel[] }
export interface TgScanResult { scanned_channels: number; new_messages: number; ingested: number; errors: string[] }

export const telegramApi = {
  parse: (text: string, extra_urls: string[] = []) => api<TelegramParseResult>('/api/v1/tg/parse', { method: 'POST', body: JSON.stringify({ text, extra_urls }) }),
  ingest: (body: { channel: string; message_id?: number; text: string; auto_transfer?: boolean }) => api<{ ingested: boolean; resources_count: number; tasks_created: number[]; message: string }>('/api/v1/tg/ingest', { method: 'POST', body: JSON.stringify(body) }),
  status: () => api<TelegramStatus>('/api/v1/tg/status'),
  clientStatus: () => api<TgClientStatus>('/api/v1/tg/client/status'),
  clientScan: () => api<TgScanResult>('/api/v1/tg/client/scan', { method: 'POST' }),
}
