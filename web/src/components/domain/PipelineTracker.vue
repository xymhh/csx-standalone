<script setup lang="ts">
import { Check } from '@lucide/vue'

const steps = ['订阅基准', '追更缺集', '双源发现', '候选决策', '转存入库']
defineProps<{ active?: number }>()
</script>

<template>
  <ol class="grid grid-cols-2 gap-2 sm:grid-cols-5">
    <li
      v-for="(step, index) in steps"
      :key="step"
      class="relative flex min-h-14 items-center gap-3 rounded-xl border px-3 text-sm transition-colors"
      :class="index < (active ?? 0) ? 'border-status-ready/20 bg-status-ready/5 text-fg' : index === active ? 'border-primary/20 bg-surface shadow-lg shadow-primary/5' : 'border-border bg-surface/60 text-muted'"
    >
      <span
        class="grid h-8 w-8 shrink-0 place-items-center rounded-full font-mono text-xs tabular-nums"
        :class="index < (active ?? 0) ? 'bg-status-ready/15 text-status-ready' : index === active ? 'bg-primary text-bg shadow-md shadow-primary/10' : 'bg-surface-2 text-subtle'"
      >
        <Check v-if="index < (active ?? 0)" class="h-4 w-4" />
        <span v-else>{{ String(index + 1).padStart(2, '0') }}</span>
      </span>
      <span class="truncate font-medium">{{ step }}</span>
      <span v-if="index === active" class="absolute bottom-0 left-3 right-3 h-px bg-primary/60 shadow-[0_0_8px_var(--color-primary)]" />
    </li>
  </ol>
</template>
