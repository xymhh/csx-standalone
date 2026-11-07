<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    type?: string
    placeholder?: string
    autocomplete?: string
    disabled?: boolean
    invalid?: boolean
    class?: string
  }>(),
  { type: 'text', modelValue: '' },
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const classes = computed(() =>
  cn(
    'h-10 w-full rounded-md border bg-surface-2 px-3 text-sm text-fg placeholder:text-muted/70',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
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
