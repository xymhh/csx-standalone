<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

const props = defineProps<{ open: boolean; title: string }>()
const emit = defineEmits<{ close: [] }>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.open) emit('close')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md"
      @click.self="emit('close')"
    >
      <section
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl shadow-black/50"
      >
        <header class="mb-5 flex items-center justify-between gap-4">
          <h2 class="text-lg font-semibold tracking-tight">{{ title }}</h2>
          <button
            class="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-xl text-muted hover:bg-surface-2 hover:text-fg"
            aria-label="关闭"
            @click="emit('close')"
          >
            ×
          </button>
        </header>
        <slot />
      </section>
    </div>
  </Teleport>
</template>
