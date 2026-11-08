<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Menu, Plus } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import ManualTransferDialog from '@/components/dialogs/ManualTransferDialog.vue'
import { useEvents } from '@/composables/useEvents'

defineEmits<{ menu: [] }>()

const route = useRoute()
const transferDialogOpen = ref(false)

const titles: Record<string, string> = {
  '/': '我的追剧',
  '/discover': '探索推荐 · TMDB 榜单',
  '/search': '全网搜资源',
  '/tasks': '传输与下载',
  '/media': '媒体库与整理中心',
  '/settings': '系统设置',
  '/progress': '追剧进度',
  '/baseline': '我的订阅',
  '/radar': '搜源监控',
  '/candidates': '待选资源',
  '/history': '转存历史',
}

const { connected } = useEvents()
const title = computed(() => titles[route.path] ?? '我的追剧')
</script>

<template>
  <header
    class="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/[0.06] bg-black/60 px-4 backdrop-blur-2xl sm:px-6 lg:px-8"
  >
    <div class="flex items-center gap-3">
      <button
        class="grid h-9 w-9 place-items-center rounded-xl text-zinc-400 hover:bg-white/10 hover:text-white lg:hidden"
        aria-label="打开菜单"
        @click="$emit('menu')"
      >
        <Menu class="h-5 w-5" />
      </button>
      <h1 class="text-sm font-semibold tracking-tight text-white">{{ title }}</h1>
    </div>

    <!-- 右侧动作区：苹果胶囊反转按钮「+ 快捷转存」与实时在线指示 -->
    <div class="flex items-center gap-4">
      <div class="hidden sm:flex items-center gap-1.5 text-xs text-zinc-400">
        <span
          class="h-2 w-2 rounded-full transition-colors"
          :class="connected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-amber-400'"
        />
        <span>{{ connected ? '实时在线' : '重连中' }}</span>
      </div>

      <Button
        size="sm"
        class="apple-btn-primary flex items-center gap-1.5 px-4 shadow-sm"
        @click="transferDialogOpen = true"
      >
        <Plus class="h-4 w-4" />
        <span>快捷转存</span>
      </Button>
    </div>

    <ManualTransferDialog
      :open="transferDialogOpen"
      @close="transferDialogOpen = false"
    />
  </header>
</template>
