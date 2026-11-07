<script setup lang="ts">
import { Check } from '@lucide/vue'

const steps = ['添加订阅', '检查缺集', '全网找源', '优选版本', '转存入库']
defineProps<{ active?: number }>()
</script>

<template>
  <ol class="grid grid-cols-2 gap-2.5 sm:grid-cols-5">
    <li
      v-for="(step, index) in steps"
      :key="step"
      class="group relative flex min-h-12 items-center gap-3 rounded-xl border border-border bg-surface px-3 py-2 text-sm shadow-sm transition-all"
      :class="index <= (active ?? 0) ? 'border-border/80' : 'opacity-60'"
    >
      <span
        class="grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-semibold"
        :class="
          index < (active ?? 0)
            ? 'bg-status-ready/20 text-status-ready border border-status-ready/30'
            : index === (active ?? 0)
              ? 'bg-primary text-bg shadow-sm shadow-primary/20'
              : 'bg-surface-2 text-muted border border-border'
        "
      >
        <Check v-if="index < (active ?? 0)" class="h-3.5 w-3.5" />
        <span v-else>{{ index + 1 }}</span>
      </span>
      <span class="truncate font-medium text-xs sm:text-sm" :class="index === (active ?? 0) ? 'text-fg' : 'text-muted'">
        {{ step }}
      </span>
    </li>
  </ol>
</template>
