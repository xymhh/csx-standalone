<script setup lang="ts">
defineProps<{ modelValue: boolean; label?: string }>()
defineEmits<{ 'update:modelValue': [value: boolean] }>()
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :aria-label="label"
    class="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    @click="$emit('update:modelValue', !modelValue)"
  >
    <span
      class="flex h-6 w-11 items-center rounded-full border border-border p-1 transition-colors"
      :class="modelValue ? 'bg-status-ready/80' : 'bg-surface-3'"
    >
      <span
        class="h-4 w-4 rounded-full bg-primary shadow-sm transition-transform"
        :class="modelValue ? 'translate-x-5' : 'translate-x-0'"
      />
    </span>
  </button>
</template>
