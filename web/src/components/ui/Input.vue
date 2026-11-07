<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    modelValue?: string | number
    type?: string
    placeholder?: string
    autocomplete?: string
    disabled?: boolean
    invalid?: boolean
    class?: string
  }>(),
  { type: 'text', modelValue: '' },
)

const emit = defineEmits<{ 'update:modelValue': [value: any] }>()

const classes = computed(() =>
  cn(
    'min-h-[44px] w-full rounded-lg border bg-surface/80 px-3 text-sm text-fg placeholder:text-subtle',
    'transition-colors focus-visible:border-focus focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-focus',
    'disabled:opacity-50',
    props.invalid ? 'border-status-missing' : 'border-border',
    props.class,
  ),
)
</script>

<template>
  <input
    :class="classes"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :autocomplete="autocomplete"
    :disabled="disabled"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>
