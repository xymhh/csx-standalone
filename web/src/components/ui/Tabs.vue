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
    class="inline-flex max-w-full items-center gap-1 overflow-x-auto rounded-full border border-white/[0.08] bg-zinc-900/60 p-1 backdrop-blur-xl shadow-inner scrollbar-none"
  >
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      class="relative z-10 shrink-0 rounded-full px-4 py-1.5 text-xs font-medium transition-all duration-200 focus-visible:outline-none"
      :class="
        modelValue === item.value
          ? 'bg-zinc-800 text-white shadow-md shadow-black/40 ring-1 ring-white/10'
          : 'text-zinc-400 hover:text-zinc-200'
      "
      @click="$emit('update:modelValue', item.value)"
    >
      {{ item.label }}
    </button>
  </div>
</template>
