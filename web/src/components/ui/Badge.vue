<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    tone?: 'default' | 'good' | 'warn' | 'bad' | 'info' | 'muted'
    pulse?: boolean
    class?: string
  }>(),
  { tone: 'default', pulse: false },
)

const classes = computed(() =>
  cn(
    'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-tight',
    'backdrop-blur-md transition-colors border',
    {
      'border-primary/10 bg-primary/5 text-fg-2': props.tone === 'default',
      'border-emerald-500/20 bg-emerald-500/10 text-emerald-400': props.tone === 'good',
      'border-amber-500/20 bg-amber-500/10 text-amber-400': props.tone === 'warn',
      'border-rose-500/20 bg-rose-500/10 text-rose-400': props.tone === 'bad',
      'border-sky-500/20 bg-sky-500/10 text-sky-400': props.tone === 'info',
      'border-primary/[0.06] bg-surface-solid/40 text-muted': props.tone === 'muted',
    },
    props.class,
  ),
)

const dotColor = computed(() => ({
  'bg-fg-2': props.tone === 'default',
  'bg-emerald-400': props.tone === 'good',
  'bg-amber-400': props.tone === 'warn',
  'bg-rose-400': props.tone === 'bad',
  'bg-sky-400': props.tone === 'info',
  'bg-subtle': props.tone === 'muted',
}))
</script>

<template>
  <span :class="classes">
    <span
      class="h-1.5 w-1.5 shrink-0 rounded-full"
      :class="[dotColor, pulse && 'animate-pulse shadow-[0_0_6px_currentColor]']"
    />
    <slot />
  </span>
</template>
