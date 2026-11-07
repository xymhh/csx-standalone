<script setup lang="ts">
import type { ProgressSeason } from '@/lib/api'

defineProps<{ seasons: ProgressSeason[] }>()
</script>

<template>
  <div class="space-y-4">
    <section
      v-for="season in seasons"
      :key="season.season"
      class="space-y-2"
    >
      <div class="flex items-center justify-between text-xs text-muted">
        <h4 class="font-medium text-fg">第 {{ season.season }} 季</h4>
        <span class="font-mono text-[11px] tabular-nums text-subtle">{{ season.episodes.length }} 集</span>
      </div>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(40px,1fr))] gap-1.5">
        <span
          v-for="ep in season.episodes"
          :key="ep.episode"
          class="grid aspect-square min-h-10 place-items-center rounded-lg border font-mono text-xs font-medium tabular-nums transition-colors"
          :title="ep.title ?? `第 ${ep.episode} 集`"
          :class="ep.owned ? 'border-status-ready/30 bg-status-ready/10 text-status-ready' : ep.aired ? 'border-status-missing/30 bg-status-missing/10 text-status-missing' : 'border-border/60 bg-surface-2/40 text-subtle'"
        >
          {{ String(ep.episode).padStart(2, '0') }}
        </span>
      </div>
    </section>
  </div>
</template>
