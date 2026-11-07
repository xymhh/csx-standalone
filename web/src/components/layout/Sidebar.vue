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
  Film,
} from '@lucide/vue'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; compactChange: [compact: boolean] }>()

const route = useRoute()
const compact = ref(false)

const groups = [
  {
    title: '追更',
    items: [
      { path: '/', label: '控制台', icon: LayoutDashboard },
      { path: '/progress', label: '追剧进度', icon: Gauge },
      { path: '/baseline', label: '我的订阅', icon: Database },
      { path: '/search', label: '全网找资源', icon: Search },
    ],
  },
  {
    title: '转存',
    items: [
      { path: '/candidates', label: '待选资源', icon: Layers },
      { path: '/tasks', label: '转存任务', icon: ListChecks },
      { path: '/history', label: '转存历史', icon: History },
    ],
  },
  {
    title: '系统',
    items: [
      { path: '/media', label: '媒体库', icon: Library },
      { path: '/radar', label: '搜源监控', icon: Radio },
      { path: '/settings', label: '系统设置', icon: Settings },
    ],
  },
] as const

function toggleCompact() {
  compact.value = !compact.value
  emit('compactChange', compact.value)
}
</script>

<template>
  <button
    aria-label="关闭导航"
    class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity lg:hidden"
    :class="open ? 'opacity-100' : 'pointer-events-none opacity-0'"
    @click="$emit('close')"
  />
  <aside
    class="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-bg/95 shadow-xl transition-all duration-200 lg:translate-x-0"
    :class="[open ? 'translate-x-0' : '-translate-x-full', compact ? 'lg:w-16' : 'lg:w-64']"
  >
    <!-- Logo 区域：极简、舒展 -->
    <div class="flex h-14 items-center gap-2.5 border-b border-border/60 px-4">
      <div class="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-zinc-100 text-xs font-bold text-zinc-950 shadow-sm">
        CS
      </div>
      <div v-if="!compact || open" class="min-w-0 flex-1">
        <p class="whitespace-nowrap text-sm font-semibold tracking-tight text-fg">CloudSubscribeX</p>
      </div>
      <button
        class="ml-auto grid h-8 w-8 place-items-center rounded-md text-subtle hover:bg-surface hover:text-fg lg:hidden"
        aria-label="关闭侧栏"
        @click="$emit('close')"
      >
        <X class="h-4 w-4" />
      </button>
      <button
        class="ml-auto hidden h-8 w-8 place-items-center rounded-md text-subtle hover:bg-surface hover:text-fg lg:grid"
        :aria-label="compact ? '展开侧栏' : '收起侧栏'"
        @click="toggleCompact"
      >
        <component :is="compact ? PanelLeftOpen : PanelLeftClose" class="h-4 w-4" />
      </button>
    </div>

    <!-- 导航组：分组清晰、层次优雅 -->
    <nav class="flex-1 space-y-5 overflow-y-auto px-3 py-4">
      <div v-for="group in groups" :key="group.title" class="space-y-1">
        <p v-if="!compact || open" class="px-2.5 text-[11px] font-medium text-subtle tracking-wider">
          {{ group.title }}
        </p>
        <RouterLink
          v-for="item in group.items"
          :key="item.path"
          :to="item.path"
          :title="item.label"
          class="group relative flex h-9 items-center gap-2.5 rounded-md px-2.5 text-xs font-medium transition-colors"
          :class="
            route.path === item.path
              ? 'bg-zinc-800/80 text-fg shadow-sm'
              : 'text-muted hover:bg-surface hover:text-fg'
          "
          @click="$emit('close')"
        >
          <component
            :is="item.icon"
            class="h-4 w-4 shrink-0 transition-colors"
            :class="route.path === item.path ? 'text-fg' : 'text-subtle group-hover:text-muted'"
          />
          <span v-if="!compact || open" class="truncate">{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>
  </aside>
</template>
