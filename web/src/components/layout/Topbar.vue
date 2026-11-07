<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Menu, Search } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import { useEvents } from '@/composables/useEvents'

defineEmits<{ menu: [] }>()

const route = useRoute()
const titles: Record<string, string> = {
  '/': '控制台',
  '/progress': '追剧进度',
  '/baseline': '我的订阅',
  '/radar': '搜源监控',
  '/candidates': '待选资源',
  '/search': '全网搜资源',
  '/tasks': '转存任务',
  '/history': '转存历史',
  '/media': '媒体库',
  '/settings': '系统设置',
}

const { connected } = useEvents()
const title = computed(() => titles[route.path] ?? '控制台')
</script>

<template>
  <header
    class="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border/60 bg-bg/80 px-4 backdrop-blur-md sm:px-6 lg:px-8"
  >
    <div class="flex items-center gap-3">
      <button
        class="grid h-8 w-8 place-items-center rounded-md text-subtle hover:bg-surface hover:text-fg lg:hidden"
        aria-label="打开菜单"
        @click="$emit('menu')"
      >
        <Menu class="h-4 w-4" />
      </button>
      <h1 class="text-sm font-semibold tracking-tight text-fg">{{ title }}</h1>
    </div>

    <div class="flex items-center gap-3">
      <div class="flex items-center gap-1.5 text-xs text-subtle">
        <span
          class="h-2 w-2 rounded-full transition-colors"
          :class="connected ? 'bg-status-ready shadow-[0_0_8px_var(--color-status-ready)]' : 'bg-status-waiting'"
        />
        <span>{{ connected ? '实时在线' : '正在连接' }}</span>
      </div>
      <RouterLink
        to="/search"
        class="grid h-8 w-8 place-items-center rounded-md border border-border/60 bg-surface/50 text-subtle transition-colors hover:bg-surface hover:text-fg"
        aria-label="搜索"
      >
        <Search class="h-3.5 w-3.5" />
      </RouterLink>
    </div>
  </header>
</template>
