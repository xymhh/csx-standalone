import type { Component } from 'vue'
import { Anchor, Clapperboard, Dices, FileText, Film, Globe, Link2, MessagesSquare, MonitorPlay, Radar, Satellite, Snail, Sparkles, Sprout, Database } from '@lucide/vue'

// 搜索渠道图标映射（渠道切换栏与渠道详情共用）
export const SOURCE_ICONS: Record<string, Component> = {
  pansou: Radar,
  hdhive: Dices,
  hdhaven: Clapperboard,
  dian115: Film,
  juying: MonitorPlay,
  woniu: Snail,
  pinglian: Link2,
  mikan: Sparkles,
  animegarden: Sprout,
  seedhub: Sprout,
  tgchannels: MessagesSquare,
  piratebay: Anchor,
  pianku: Database,
  uindex: Globe,
  online_docs: FileText,
}

export function sourceIcon(sourceId: string) {
  return SOURCE_ICONS[sourceId] || Satellite
}
