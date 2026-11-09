export const PROVIDER_LABELS: Record<string, string> = {
  '115': '115 网盘',
  quark: '夸克网盘',
  alipan: '阿里云盘',
  baidu: '百度网盘',
  uc: 'UC 网盘',
  telegram: 'TG 频道',
  manual: '手动转存',
}

export function providerLabel(provider?: string | null): string {
  const key = (provider ?? '').trim()
  if (!key) return '未知来源'
  return PROVIDER_LABELS[key] ?? key
}

export function mediaTypeLabel(type?: string | null): string {
  if (type === 'movie') return '电影'
  if (type === 'tv') return '剧集'
  if (type === 'variety') return '综艺'
  return '影视'
}

export function formatBytes(size?: number | null): string {
  if (!size || size <= 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = size
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  const digits = value >= 100 || unit <= 1 ? 0 : 1
  return `${value.toFixed(digits)} ${units[unit]}`
}

export function episodeLabel(season?: number | null, episode?: number | null): string {
  if (!season || !episode) return ''
  return `S${String(season).padStart(2, '0')}E${String(episode).padStart(2, '0')}`
}

export function shortEpisodeLabel(season?: number | null, episode?: number | null): string {
  if (!episode) return ''
  if (!season) return `E${String(episode).padStart(2, '0')}`
  return episodeLabel(season, episode)
}

export const TASK_STATE_LABELS: Record<string, string> = {
  queued: '排队中',
  running: '转存中',
  retry_wait: '等待重试',
  dead_letter: '转存失败',
  succeeded: '已入库',
  cancelled: '已跳过',
}

export type BadgeTone = 'default' | 'good' | 'warn' | 'bad' | 'info' | 'muted'

export function taskStateTone(state?: string | null): BadgeTone {
  if (state === 'succeeded') return 'good'
  if (state === 'dead_letter') return 'bad'
  if (state === 'retry_wait') return 'warn'
  if (state === 'running') return 'info'
  if (state === 'cancelled') return 'muted'
  return 'default'
}

export function relativeTime(input?: string | null): string {
  if (!input) return '—'
  const date = new Date(input)
  if (Number.isNaN(date.getTime())) return '—'
  const diff = Date.now() - date.getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} 天前`
  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

export function elapsedLabel(input?: string | null): string {
  if (!input) return ''
  const started = new Date(input).getTime()
  if (Number.isNaN(started)) return ''
  const seconds = Math.max(0, Math.floor((Date.now() - started) / 1000))
  if (seconds < 60) return `${seconds} 秒`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} 分 ${seconds % 60} 秒`
  return `${Math.floor(minutes / 60)} 小时 ${minutes % 60} 分`
}

/** 原始异常里往往重复了短标签，去掉后只留真正额外的信息。 */
export function failureDetailText(label?: string | null, detail?: string | null): string {
  const short = (label ?? '').trim()
  let text = (detail ?? '').replace(/\s+/g, ' ').trim()
  if (!text) return ''
  if (short) text = text.split(short).join(' ')
  text = text.replace(/^(整理失败|转存失败|错误|error)[:：\s-]*/i, '')
  text = text.replace(/[\s:：·@,，\-—]+/g, ' ').trim()
  return text.length >= 8 ? text : ''
}
