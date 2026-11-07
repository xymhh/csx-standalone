<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Menu, Search } from '@lucide/vue'

import { useEvents } from '@/composables/useEvents'

const emit = defineEmits<{ menu: [] }>()
const route = useRoute()
const titles: Record<string, string> = {
  '/': '追更总览',
  '/progress': '追更进度',
  '/baseline': '订阅基准',
  '/radar': '双源雷达',
  '/candidates': '候选资源',
  '/search': '手动搜索',
  '/tasks': '执行队列',
  '/history': '转存流水',
  '/media': '媒体资产',
  '/settings': '系统设置',
}
const { connected } = useEvents()
const title = computed(() => titles[route.path] ?? 'CloudSubscribeX')
</script>

<template>
  <header class="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-bg/80 px-4 backdrop-blur-md sm:px-6 lg:px-8">
    <button
      class="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg lg:hidden"
      aria-label="打开菜单"
      @click="emit('menu')"
    >
      <Menu class="h-5 w-5" />
    </button>
    <div>
      <h1 class="text-sm font-semibold tracking-tight">{{ title }}</h1>
      <p class="hidden text-xs text-muted sm:block">CloudSubscribeX <span class="mx-1 text-subtle">/</span> 实时任务与媒体管理</p>
    </div>
    <div class="ml-auto flex items-center gap-3">
      <span class="hidden items-center gap-2 text-xs text-muted sm:inline-flex">
        <span
          class="h-2 w-2 rounded-full"
          :class="connected ? 'animate-pulse bg-status-ready shadow-[0_0_10px_var(--color-status-ready)]' : 'bg-status-waiting'"
        />
        {{ connected ? '实时连接' : '正在重连' }}
      </span>
      <RouterLink
        to="/search"
        class="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg border border-border text-muted transition-colors hover:bg-surface-2 hover:text-fg"
        aria-label="搜索"
      >
        <Search class="h-4 w-4" />
      </RouterLink>
    </div>
  </header>
</template>
