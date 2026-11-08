<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Menu, Plus, Search } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import ManualTransferDialog from '@/components/dialogs/ManualTransferDialog.vue'
import { useEvents } from '@/composables/useEvents'
import { ref } from 'vue'

defineEmits<{ menu: [] }>()

const route = useRoute()
const transferDialogOpen = ref(false)

const titles: Record<string, string> = {
  '/': '我的追剧',
  '/search': '搜全网资源',
  '/tasks': '传输与下载',
  '/media': '媒体库与整理中心',
  '/settings': '系统设置',
  '/progress': '追剧进度',
  '/baseline': '追剧订阅',
  '/radar': '搜源监控',
  '/candidates': '待选资源',
  '/history': '转存历史',
}

const { connected } = useEvents()
const title = computed(() => titles[route.path] ?? '我的追剧')
</script>

<template>
  <header
    class="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border/70 bg-bg/85 px-4 backdrop-blur-md sm:px-6 lg:px-8"
  >
    <div class="flex items-center gap-3">
      <button
        class="grid h-9 w-9 place-items-center rounded-lg text-subtle hover:bg-surface hover:text-fg lg:hidden"
        aria-label="打开菜单"
        @click="$emit('menu')"
      >
        <Menu class="h-5 w-5" />
      </button>
      <h1 class="text-base font-semibold tracking-tight text-fg">{{ title }}</h1>
    </div>

    <!-- 右侧动作区：常驻白底黑字「+ 快捷转存」与实时在线指示 -->
    <div class="flex items-center gap-3">
      <div class="hidden sm:flex items-center gap-1.5 text-xs text-subtle">
        <span
          class="h-2 w-2 rounded-full transition-colors"
          :class="connected ? 'bg-status-ready shadow-[0_0_8px_var(--color-status-ready)]' : 'bg-status-waiting'"
        />
        <span>{{ connected ? '实时在线' : '重连中' }}</span>
      </div>

      <Button
        size="sm"
        class="flex items-center gap-1.5 shadow-sm shadow-white/10"
        @click="transferDialogOpen = true"
      >
        <Plus class="h-4 w-4" />
        <span class="font-medium">快捷转存</span>
      </Button>
    </div>

    <!-- 全局快捷转存弹窗 -->
    <ManualTransferDialog
      :open="transferDialogOpen"
      @close="transferDialogOpen = false"
    />
  </header>
</template>
