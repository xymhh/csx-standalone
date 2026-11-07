<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{ tone?: 'default' | 'good' | 'warn' | 'bad' | 'info' | 'muted'; pulse?: boolean }>(),
  { tone: 'default', pulse: false },
)

const tones = {
  default: 'border-primary/15 bg-primary/10 text-primary',
  good: 'border-status-ready/20 bg-status-ready/10 text-status-ready',
  warn: 'border-status-waiting/20 bg-status-waiting/10 text-status-waiting',
  bad: 'border-status-missing/20 bg-status-missing/10 text-status-missing',
  info: 'border-status-transferred/20 bg-status-transferred/10 text-status-transferred',
  muted: 'border-border bg-surface-2 text-muted',
} as const

const dots = {
  default: 'bg-primary',
  good: 'bg-status-ready',
  warn: 'bg-status-waiting',
  bad: 'bg-status-missing',
  info: 'bg-status-transferred',
  muted: 'bg-subtle',
} as const

const classes = computed(() =>
  cn(
    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium leading-none',
    tones[props.tone],
  ),
)
</script>

<template>
  <span :class="classes">
    <span
      class="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full"
      :class="[dots[tone], pulse ? 'shadow-[0_0_8px_currentColor]' : '']"
      aria-hidden="true"
    />
    <slot />
  </span>
</template>
