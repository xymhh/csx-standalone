<script setup lang="ts">
defineProps<{ modelValue: string; items: { value: string; label: string }[] }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="inline-flex max-w-full gap-1 overflow-x-auto rounded-xl border border-border bg-surface p-1">
    <button
      v-for="item in items"
      :key="item.value"
      class="min-h-[40px] shrink-0 rounded-lg px-3 text-sm font-medium transition-colors"
      :class="modelValue === item.value ? 'bg-surface-3 text-fg shadow-sm' : 'text-muted hover:text-fg'"
      @click="$emit('update:modelValue', item.value)"
    >
      {{ item.label }}
    </button>
  </div>
</template>
