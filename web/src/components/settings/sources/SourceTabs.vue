<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, List, SlidersHorizontal } from '@lucide/vue'
import { sourceIcon } from '@/components/settings/sources/sourceIcons'
import type { SearchSourceSchema } from '@/api/sources'

// 渠道切换栏：选中渠道以 v-model:selected 与父级共享，schemas/values 只读传入
const props = defineProps<{
  schemas: SearchSourceSchema[]
  values: Record<string, Record<string, any>>
}>()
const selected = defineModel<string>('selected', { required: true })

const sourceMenuOpen = ref(false)

const visibleSourceTabs = computed(() => props.schemas.slice(0, 4))
const hiddenSourceTabs = computed(() => props.schemas.slice(4))

function pickSource(sourceId: string) {
  selected.value = sourceId
  sourceMenuOpen.value = false
}
</script>

<template>
      <!-- 渠道切换栏 -->
      <div class="apple-glass relative rounded-2xl px-2 py-2">
        <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          <button
            type="button"
            class="flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-all cursor-pointer whitespace-nowrap"
            :class="selected === 'general' ? 'bg-primary/15 text-fg ring-1 ring-primary/20' : 'text-muted hover:bg-primary/[0.05] hover:text-fg'"
            @click="pickSource('general')"
          >
            <SlidersHorizontal class="h-3.5 w-3.5 shrink-0" />
            <span>通用设置</span>
          </button>
          <button
            v-for="s in visibleSourceTabs"
            :key="s.id"
            type="button"
            class="flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-all cursor-pointer whitespace-nowrap"
            :class="selected === s.id ? 'bg-primary/15 text-fg ring-1 ring-primary/20' : 'text-muted hover:bg-primary/[0.05] hover:text-fg'"
            @click="pickSource(s.id)"
          >
            <component :is="sourceIcon(s.id)" class="h-3.5 w-3.5 shrink-0" />
            <span>{{ s.name }}</span>
            <span
              class="h-1.5 w-1.5 rounded-full"
              :class="values[s.id]?.enabled === false ? 'bg-faint' : 'bg-emerald-400'"
            />
          </button>
          <button
            v-if="hiddenSourceTabs.length"
            type="button"
            class="flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium text-muted transition-all hover:bg-primary/[0.05] hover:text-fg cursor-pointer whitespace-nowrap"
            :class="hiddenSourceTabs.some((s) => s.id === selected) ? 'bg-primary/15 text-fg ring-1 ring-primary/20' : ''"
            @click="sourceMenuOpen = !sourceMenuOpen"
          >
            <List class="h-3.5 w-3.5 shrink-0" />
            <span>更多 ({{ schemas.length }})</span>
          </button>
        </div>
        <div
          v-if="sourceMenuOpen"
          class="absolute left-2 right-2 top-full z-30 mt-1 max-h-72 overflow-y-auto rounded-xl border border-primary/10 bg-[#121214] p-1.5 shadow-2xl"
        >
          <button
            v-for="s in schemas"
            :key="s.id"
            type="button"
            class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-fg-2 hover:bg-primary/[0.06] cursor-pointer"
            :class="selected === s.id ? 'text-fg' : ''"
            @click="pickSource(s.id)"
          >
            <component :is="sourceIcon(s.id)" class="h-3.5 w-3.5 shrink-0 text-subtle" />
            <span class="flex-1 text-left">{{ s.name }}</span>
            <span
              v-if="values[s.id]?.enabled === false"
              class="rounded bg-primary/[0.06] px-1 py-0.5 text-[10px] text-subtle"
            >停用</span>
            <Check v-else-if="selected === s.id" class="h-3.5 w-3.5 text-emerald-400" />
          </button>
        </div>
      </div>
</template>
