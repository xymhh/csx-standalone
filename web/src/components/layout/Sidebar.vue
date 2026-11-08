<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Clapperboard,
  Compass,
  DownloadCloud,
  Film,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Settings,
  Tv,
  X,
} from '@lucide/vue'

import { authApi } from '@/lib/api'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; compactChange: [compact: boolean] }>()

const route = useRoute()
const compact = ref(false)

// 5 大众化核心顶级入口
const mainLinks = [
  { path: '/discover', label: '探索推荐', icon: Compass, match: (p: string) => p === '/discover' },
  { path: '/', label: '我的追剧', icon: Tv, match: (p: string) => p === '/' || p === '/baseline' || p === '/progress' },
  { path: '/search', label: '全网搜源', icon: Search, match: (p: string) => p === '/search' || p === '/radar' },
  { path: '/tasks', label: '传输与下载', icon: DownloadCloud, match: (p: string) => p === '/tasks' || p === '/candidates' || p === '/history' },
  { path: '/media', label: '媒体库', icon: Film, match: (p: string) => p === '/media' },
  { path: '/settings', label: '系统设置', icon: Settings, match: (p: string) => p === '/settings' },
] as const

function toggleCompact() {
  compact.value = !compact.value
  emit('compactChange', compact.value)
}

async function logout() {
  try {
    await authApi.logout()
  } catch {}
  window.location.href = '/login'
}
</script>

<template>
  <!-- 移动端暗色遮罩 -->
  <button
    aria-label="关闭导航"
    class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity lg:hidden"
    :class="open ? 'opacity-100' : 'pointer-events-none opacity-0'"
    @click="$emit('close')"
  />

  <aside
    class="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border/80 bg-zinc-950/95 shadow-2xl transition-all duration-200 lg:translate-x-0"
    :class="[open ? 'translate-x-0' : '-translate-x-full', compact ? 'lg:w-16' : 'lg:w-64']"
  >
    <!-- Logo 区域：极简、现代、零截断 -->
    <div class="flex h-16 items-center gap-3 border-b border-border/60 px-4">
      <div class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-zinc-950 shadow-sm shadow-white/10 font-bold">
        <Clapperboard class="h-4.5 w-4.5" />
      </div>
      <div v-if="!compact || open" class="min-w-0 flex-1 overflow-hidden">
        <p class="truncate text-xs font-bold uppercase tracking-wider text-zinc-100">CloudSubscribeX</p>
        <p class="truncate text-[10px] text-zinc-400">自动追剧与网盘中枢</p>
      </div>
      <button
        class="ml-auto grid h-8 w-8 place-items-center rounded-lg text-subtle hover:bg-surface hover:text-fg lg:hidden"
        aria-label="关闭侧栏"
        @click="$emit('close')"
      >
        <X class="h-4 w-4" />
      </button>
      <button
        class="ml-auto hidden h-8 w-8 place-items-center rounded-lg text-subtle hover:bg-surface hover:text-fg lg:grid"
        :aria-label="compact ? '展开侧栏' : '收起侧栏'"
        @click="toggleCompact"
      >
        <component :is="compact ? PanelLeftOpen : PanelLeftClose" class="h-4 w-4" />
      </button>
    </div>

    <!-- 导航项：采用 taste-skill 高对比反转与 2px 微动画 -->
    <nav class="flex-1 space-y-1.5 px-3 py-6">
      <RouterLink
        v-for="item in mainLinks"
        :key="item.path"
        :to="item.path"
        :title="item.label"
        class="group relative flex h-11 items-center gap-3.5 rounded-xl px-3 text-sm font-medium transition-all duration-150"
        :class="
          item.match(route.path)
            ? 'bg-zinc-900 text-white shadow-sm ring-1 ring-white/10'
            : 'text-zinc-400 hover:bg-zinc-900/50 hover:text-white'
        "
        @click="$emit('close')"
      >
        <!-- 激活左指示微光条 -->
        <span
          v-if="item.match(route.path)"
          class="absolute inset-y-2.5 left-0 w-1 rounded-r-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)]"
        />
        <component
          :is="item.icon"
          class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105"
          :class="item.match(route.path) ? 'text-white' : 'text-zinc-400 group-hover:text-zinc-200'"
        />
        <span v-if="!compact || open" class="truncate tracking-tight">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <!-- 底部管理员身份卡片 -->
    <div class="border-t border-border/60 p-3">
      <div class="flex items-center justify-between rounded-xl p-2 transition-colors hover:bg-zinc-900/60">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-zinc-800 font-mono text-xs font-semibold text-zinc-300">
            A
          </div>
          <div v-if="!compact || open" class="min-w-0">
            <p class="truncate text-xs font-medium text-zinc-200">admin</p>
            <p class="text-[10px] text-zinc-500">管理员</p>
          </div>
        </div>
        <button
          v-if="!compact || open"
          class="grid h-8 w-8 place-items-center rounded-lg text-zinc-500 transition-colors hover:bg-rose-500/10 hover:text-rose-400"
          title="退出登录"
          @click="logout"
        >
          <LogOut class="h-4 w-4" />
        </button>
      </div>
    </div>
  </aside>
</template>
