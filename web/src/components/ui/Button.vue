<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'danger'
    size?: 'sm' | 'md' | 'lg'
    disabled?: boolean
    class?: string
    type?: 'button' | 'submit' | 'reset'
  }>(),
  { variant: 'default', size: 'md', disabled: false, type: 'button' },
)

const classes = computed(() =>
  cn(
    'inline-flex items-center justify-center font-medium transition-all duration-200 cursor-pointer select-none',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20',
    'disabled:pointer-events-none disabled:opacity-40',
    // 苹果反转胶囊风格
    {
      'apple-btn-primary active:scale-[0.97]': props.variant === 'default',
      'rounded-full bg-zinc-800/90 text-white border border-white/10 hover:bg-zinc-700 active:scale-[0.97] shadow-sm': props.variant === 'secondary',
      'rounded-full border border-white/10 bg-white/[0.03] text-zinc-200 backdrop-blur-md hover:bg-white/[0.08] hover:border-white/20 active:scale-[0.97]': props.variant === 'outline',
      'rounded-full text-zinc-400 hover:text-white hover:bg-white/[0.06] active:scale-[0.97]': props.variant === 'ghost',
      'rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/20 hover:bg-rose-500/25 active:scale-[0.97]': props.variant === 'danger',
    },
    {
      'h-8 px-3 text-xs gap-1.5': props.size === 'sm',
      'h-10 px-4 text-sm gap-2': props.size === 'md',
      'h-12 px-6 text-base gap-2.5': props.size === 'lg',
    },
    props.class,
  ),
)
</script>

<template>
  <button :type="type" :class="classes" :disabled="disabled">
    <slot />
  </button>
</template>
