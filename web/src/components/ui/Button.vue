<script setup lang="ts">
import { cva } from 'class-variance-authority'
import { computed } from 'vue'

import { cn } from '@/lib/utils'

type Variant = 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive'
type Size = 'default' | 'sm' | 'lg'

const props = withDefaults(defineProps<{ variant?: Variant; size?: Size }>(), {
  variant: 'default',
  size: 'default',
})

const buttonVariants = cva(
  'inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-bg shadow-sm hover:bg-primary-hover active:scale-[0.98]',
        secondary: 'bg-surface-2 text-fg hover:bg-surface-3',
        outline: 'border border-border bg-transparent text-fg hover:bg-surface-2',
        ghost: 'text-muted hover:bg-surface-2 hover:text-fg',
        destructive: 'bg-status-missing text-primary hover:bg-status-missing/90',
      },
      size: {
        default: 'h-11 px-4',
        sm: 'h-10 px-3 text-xs',
        lg: 'h-12 px-6',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

const classes = computed(() => cn(buttonVariants({ variant: props.variant, size: props.size })))
</script>

<template>
  <button :class="classes">
    <slot />
  </button>
</template>
