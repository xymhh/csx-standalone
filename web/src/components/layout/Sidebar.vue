<script setup lang="ts">
import { storeToRefs } from 'pinia'
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

import { useAuthStore } from '@/stores/auth'
import { useGlobalStore } from '@/stores/global'

defineProps<{ open: boolean }>()
defineEmits<{ close: [] }>()

const auth = useAuthStore()
const global = useGlobalStore()
const { sidebarCompact: compact } = storeToRefs(global)

// 苹果风格 5 大核心工作区导航
const mainLinks = [
  { path: '/', label: '我的追剧', icon: Tv },
  { path: '/discover', label: '探索推荐', icon: Compass },
  { path: '/search', label: '搜索资源', icon: Search },
  { path: '/tasks', label: '传输与下载', icon: DownloadCloud },
  { path: '/media', label: '媒体库', icon: Film },
  { path: '/settings', label: '系统设置', icon: Settings },
] as const

function toggleCompact() {
  global.toggleSidebarCompact()
}

async function logout() {
  try {
    await auth.logout()
  } catch {
    // 登出接口失败也照常跳转登录页
  }
  window.location.href = '/login'
}
</script>

<template>
  <!-- 移动端暗色毛玻璃遮罩 -->
  <button
    aria-label="关闭导航"
    class="fixed inset-0 z-40 bg-bg/60 backdrop-blur-md transition-opacity lg:hidden"
    :class="open ? 'opacity-100' : 'pointer-events-none opacity-0'"
    @click="$emit('close')"
  />

  <aside
    class="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-primary/[0.08] bg-canvas/85 backdrop-blur-2xl shadow-2xl transition-all duration-300 ease-out lg:translate-x-0"
    :class="[open ? 'translate-x-0' : '-translate-x-full', compact ? 'lg:w-20' : 'lg:w-64']"
  >
    <!-- Logo 区域：极简苹果风格 -->
    <div class="flex h-16 items-center gap-3 border-b border-primary/[0.06] px-5">
      <div class="grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-primary text-primary-fg shadow-md shadow-white/10 font-bold">
        <Clapperboard class="h-4.5 w-4.5" />
      </div>
      <div v-if="!compact || open" class="min-w-0 flex-1 overflow-hidden">
        <p class="truncate text-sm font-semibold tracking-tight text-fg">CloudSubscribeX</p>
        <p class="truncate text-[10px] text-muted">自动追剧 · 网盘助手</p>
      </div>
      <button
        class="ml-auto grid h-8 w-8 place-items-center rounded-lg text-muted hover:bg-primary/10 hover:text-fg lg:hidden"
        aria-label="关闭侧栏"
        @click="$emit('close')"
      >
        <X class="h-4 w-4" />
      </button>
      <button
        class="ml-auto hidden h-8 w-8 place-items-center rounded-lg text-muted hover:bg-primary/10 hover:text-fg lg:grid"
        :aria-label="compact ? '展开侧栏' : '收起侧栏'"
        @click="toggleCompact"
      >
        <component :is="compact ? PanelLeftOpen : PanelLeftClose" class="h-4 w-4" />
      </button>
    </div>

    <!-- 苹果风格分段侧栏导航 -->
    <nav class="flex-1 space-y-1.5 px-3 py-6">
      <RouterLink
        v-for="item in mainLinks"
        :key="item.path"
        :to="item.path"
        :title="item.label"
        class="group relative flex h-11 items-center gap-3.5 rounded-2xl px-3.5 text-sm font-medium transition-all duration-200"
        :class="
          $route.path === item.path
            ? 'bg-primary/10 text-fg shadow-sm ring-1 ring-primary/15 backdrop-blur-xl'
            : 'text-muted hover:bg-primary/[0.04] hover:text-fg'
        "
        @click="$emit('close')"
      >
        <component
          :is="item.icon"
          class="h-4.5 w-4.5 shrink-0 transition-transform group-hover:scale-105"
          :class="$route.path === item.path ? 'text-fg' : 'text-muted group-hover:text-fg-2'"
        />
        <span v-if="!compact || open" class="truncate tracking-tight">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <!-- 底部管理员 -->
    <div class="border-t border-primary/[0.06] p-3">
      <div class="flex items-center justify-between rounded-xl p-2 transition-colors hover:bg-primary/[0.04]">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-surface-2 font-mono text-xs font-semibold text-fg-2">
            A
          </div>
          <div v-if="!compact || open" class="min-w-0">
            <p class="truncate text-xs font-medium text-fg-2">{{ auth.user?.username ?? 'admin' }}</p>
            <p class="text-[10px] text-subtle">已登录</p>
          </div>
        </div>
        <button
          v-if="!compact || open"
          class="grid h-8 w-8 place-items-center rounded-lg text-subtle transition-colors hover:bg-rose-500/10 hover:text-rose-400"
          title="退出登录"
          @click="logout"
        >
          <LogOut class="h-4 w-4" />
        </button>
      </div>
    </div>
  </aside>
</template>
