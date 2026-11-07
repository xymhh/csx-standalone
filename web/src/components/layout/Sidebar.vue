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
  ['/', '总览', LayoutDashboard],
  ['/progress', '追更进度', Gauge],
  ['/baseline', '订阅基准', Database],
  ['/radar', '双源雷达', Radio],
  ['/candidates', '候选资源', Layers],
  ['/search', '手动搜索', Search],
  ['/tasks', '执行队列', ListChecks],
  ['/history', '转存流水', History],
  ['/media', '媒体资产', Library],
  ['/settings', '系统设置', Settings],
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
    class="fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-border bg-bg/95 shadow-2xl shadow-black/30 backdrop-blur-md transition-all duration-200 lg:translate-x-0"
    :class="[open ? 'translate-x-0' : '-translate-x-full', compact ? 'lg:w-20' : 'lg:w-60']"
  >
    <div class="flex min-h-16 items-center gap-3 border-b border-border px-4">
      <span class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-zinc-100 text-sm font-bold text-zinc-900 shadow-sm shadow-primary/10">CS</span>
      <div v-if="!compact || open" class="min-w-0">
        <p class="truncate text-sm font-semibold tracking-tight">CloudSubscribeX</p>
        <p class="text-xs text-muted">媒体自动化控制台</p>
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
        <span v-if="!compact || open">{{ label }}</span>
      </RouterLink>
    </nav>
    <div v-if="!compact || open" class="border-t border-border p-4">
      <p class="mb-2 text-[11px] font-semibold uppercase tracking-widest text-subtle">Pipeline</p>
      <p class="text-xs leading-6 text-muted">基准面 → 缺集 → 双源 → 候选 → 转存</p>
      <p class="mt-3 font-mono text-[10px] tracking-wider text-subtle">CSX · P7 STABLE</p>
    </div>
  </aside>
</template>
