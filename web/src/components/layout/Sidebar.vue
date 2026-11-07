<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Database,
  Gauge,
  History,
  Layers,
  LayoutDashboard,
  Library,
  ListChecks,
  PanelLeftClose,
  PanelLeftOpen,
  Radio,
  Search,
  Settings,
  X,
} from '@lucide/vue'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; compactChange: [compact: boolean] }>()

const route = useRoute()
const compact = ref(false)
const links = [
  ['/', '控制台', LayoutDashboard],
  ['/progress', '追剧进度', Gauge],
  ['/baseline', '我的订阅', Database],
  ['/radar', '搜索监控', Radio],
  ['/candidates', '待选资源', Layers],
  ['/search', '搜影视', Search],
  ['/tasks', '转存任务', ListChecks],
  ['/history', '转存历史', History],
  ['/media', '媒体库', Library],
  ['/settings', '设置', Settings],
] as const

function toggleCompact() {
  compact.value = !compact.value
  emit('compactChange', compact.value)
}
</script>

<template>
  <button
    aria-label="关闭导航"
    class="fixed inset-0 z-40 bg-bg/75 backdrop-blur-sm transition-opacity lg:hidden"
    :class="open ? 'opacity-100' : 'pointer-events-none opacity-0'"
    @click="$emit('close')"
  />
  <aside
    class="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-bg/95 shadow-2xl shadow-black/30 backdrop-blur-md transition-all duration-200 lg:translate-x-0"
    :class="[open ? 'translate-x-0' : '-translate-x-full', compact ? 'lg:w-20' : 'lg:w-64']"
  >
    <div class="flex min-h-16 items-center gap-3 border-b border-border px-4">
      <span class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-zinc-100 text-sm font-bold text-zinc-900 shadow-sm shadow-primary/10">CS</span>
      <div v-if="!compact || open" class="min-w-0 flex-1">
        <p class="text-sm font-semibold tracking-tight text-fg whitespace-nowrap">CloudSubscribeX</p>
        <p class="text-xs text-muted">自动追剧与网盘助手</p>
      </div>
      <button
        class="ml-auto grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg lg:hidden"
        aria-label="关闭侧栏"
        @click="$emit('close')"
      >
        <X class="h-4 w-4" />
      </button>
      <button
        class="ml-auto hidden min-h-[44px] min-w-[44px] rounded-lg text-muted hover:bg-surface-2 hover:text-fg lg:block"
        :aria-label="compact ? '展开侧栏' : '收起侧栏'"
        @click="toggleCompact"
      >
        <component :is="compact ? PanelLeftOpen : PanelLeftClose" class="mx-auto h-4 w-4" />
      </button>
    </div>
    <nav class="flex-1 space-y-1 overflow-y-auto p-3">
      <RouterLink
        v-for="[path, label, icon] in links"
        :key="path"
        :to="path"
        :title="label"
        class="group relative flex min-h-[44px] items-center gap-3 rounded-lg px-3 text-sm transition-all hover:bg-surface-2/70 hover:text-fg"
        :class="route.path === path ? 'bg-surface-2 text-fg shadow-[inset_0_0_0_1px_var(--color-border)]' : 'text-muted'"
        @click="$emit('close')"
      >
        <span
          v-if="route.path === path"
          class="absolute inset-y-2 left-0 w-0.5 rounded-full bg-primary shadow-[0_0_12px_var(--color-primary)]"
        />
        <component
          :is="icon"
          class="h-4 w-4 shrink-0 transition-colors"
          :class="route.path === path ? 'text-primary' : 'text-subtle group-hover:text-fg'"
        />
        <span v-if="!compact || open" class="font-medium">{{ label }}</span>
      </RouterLink>
    </nav>
    <div v-if="!compact || open" class="border-t border-border p-4">
      <p class="mb-1 text-[11px] font-semibold tracking-wider text-subtle">自动追剧流程</p>
      <p class="text-xs leading-5 text-muted">订阅 → 查缺 → 找源 → 优选 → 入库</p>
      <p class="mt-2 font-mono text-[10px] tracking-wider text-subtle">全自动无人值守</p>
    </div>
  </aside>
</template>
