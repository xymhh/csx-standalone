<script setup lang="ts">
defineProps<{
  modelValue: string
  items: { value: string; label: string }[]
}>()

defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <!-- 苹果 HIG 经典药丸分段选择器 (Segmented Control) -->
  <div
    class="inline-flex max-w-full items-center gap-1 overflow-x-auto rounded-full border border-primary/[0.08] bg-surface-solid/60 p-1 backdrop-blur-xl shadow-inner scrollbar-none"
  >
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      class="relative z-10 shrink-0 rounded-full px-4 py-1.5 text-xs font-medium transition-all duration-200 focus-visible:outline-none"
      :class="
        modelValue === item.value
          ? 'bg-surface-2 text-fg shadow-md shadow-black/40 ring-1 ring-primary/10'
          : 'text-muted hover:text-fg-2'
      "
      @click="$emit('update:modelValue', item.value)"
    >
      {{ item.label }}
    </button>
  </div>
</template>
