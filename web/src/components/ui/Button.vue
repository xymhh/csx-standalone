<script setup lang="ts">
import { cva } from 'class-variance-authority'
import { computed } from 'vue'

import { cn } from '@/lib/utils'

type Variant = 'default' | 'outline' | 'ghost'
type Size = 'default' | 'sm' | 'lg'

const props = withDefaults(defineProps<{ variant?: Variant; size?: Size }>(), {
  variant: 'default',
  size: 'default',
})

const buttonVariants = cva(
  'inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-bg hover:opacity-90',
        outline: 'border border-border bg-transparent hover:bg-surface-2',
        ghost: 'hover:bg-surface-2',
      },
      size: {
        default: 'h-9 px-4',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-11 px-6',
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
