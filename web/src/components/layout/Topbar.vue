<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Menu, Search } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import { useEvents } from '@/composables/useEvents'

defineEmits<{ menu: [] }>()

const route = useRoute()
const titles: Record<string, { title: string; subtitle: string }> = {
  '/': { title: '控制台', subtitle: '全自动追剧与转存概况' },
  '/progress': { title: '追剧进度', subtitle: '查看关注影视的入库与缺失集数' },
  '/baseline': { title: '我的订阅', subtitle: '正在追更的电视剧与电影清单' },
  '/radar': { title: '搜索监控', subtitle: '全网资源搜寻站点健康状态' },
  '/candidates': { title: '待选资源', subtitle: '为你搜集到的影视分享链接' },
  '/search': { title: '全网搜影视', subtitle: '跨网盘聚合搜索影视资源' },
  '/tasks': { title: '转存任务', subtitle: '正在下载和整理的影视文件' },
  '/history': { title: '转存历史', subtitle: '已完成与失败的转存记录流水' },
  '/media': { title: '我的媒体库', subtitle: '已整理入库的网盘影视与播放服务' },
  '/settings': { title: '系统设置', subtitle: '配置网盘账号、追剧偏好与通知' },
}

const { connected } = useEvents()
const current = computed(() => titles[route.path] ?? { title: 'CloudSubscribeX', subtitle: '自动追剧与网盘助手' })
</script>

<template>
  <header
    class="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-bg/85 px-4 shadow-sm backdrop-blur-md sm:px-6 lg:px-8"
  >
    <button
      class="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg lg:hidden"
      aria-label="打开菜单"
      @click="$emit('menu')"
    >
      <Menu class="h-5 w-5" />
    </button>
    <div>
      <h1 class="text-base font-semibold tracking-tight text-fg">{{ current.title }}</h1>
      <p class="hidden text-xs text-muted sm:block">{{ current.subtitle }}</p>
    </div>
    <div class="ml-auto flex items-center gap-3">
      <Badge :tone="connected ? 'good' : 'warn'" :pulse="connected">
        {{ connected ? '实时在线' : '正在连接' }}
      </Badge>
      <RouterLink
        to="/search"
        class="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg border border-border bg-surface-2/40 text-muted transition-colors hover:bg-surface-2 hover:text-fg"
        aria-label="全网搜索"
      >
        <Search class="h-4 w-4" />
      </RouterLink>
    </div>
  </header>
</template>
