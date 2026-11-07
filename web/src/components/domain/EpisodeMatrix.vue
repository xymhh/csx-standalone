<script setup lang="ts">
import type { ProgressSeason } from '@/lib/api'

defineProps<{ seasons: ProgressSeason[] }>()
</script>

<template>
  <div class="space-y-3">
    <section
      v-for="season in seasons"
      :key="season.season"
      class="rounded-xl border border-border bg-surface/70 p-4"
    >
      <div class="mb-3 flex items-center justify-between">
        <h4 class="text-sm font-medium">第 {{ season.season }} 季</h4>
        <span class="font-mono text-xs tabular-nums text-subtle">{{ season.episodes.length }} 集</span>
      </div>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(44px,1fr))] gap-2">
        <span
          v-for="ep in season.episodes"
          :key="ep.episode"
          class="grid aspect-square min-h-11 place-items-center rounded-xl border font-mono text-xs font-medium tabular-nums transition-transform hover:-translate-y-0.5"
          :title="ep.title ?? `第 ${ep.episode} 集`"
          :class="ep.owned ? 'border-status-ready/20 bg-status-ready/10 text-status-ready shadow-inner shadow-status-ready/5' : ep.aired ? 'border-status-missing/20 bg-status-missing/10 text-status-missing' : 'border-border bg-surface-2/70 text-subtle'"
        >
          {{ String(ep.episode).padStart(2, '0') }}
        </span>
      </div>
    </section>
  </div>
</template>
