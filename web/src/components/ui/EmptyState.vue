<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  title: string
  description?: string
  icon?: Component
}>()
</script>

<template>
  <div class="rounded-2xl border border-dashed border-border/60 bg-surface/30 p-12 text-center text-xs text-muted">
    <component :is="icon" v-if="icon" class="mx-auto mb-2 h-8 w-8 text-subtle/50" />
    <p class="font-medium text-fg">{{ title }}</p>
    <p v-if="description" class="mt-1 text-subtle">{{ description }}</p>
    <slot />
  </div>
</template>
