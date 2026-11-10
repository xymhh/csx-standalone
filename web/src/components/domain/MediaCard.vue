<script setup lang="ts">
import type { ProgressItem } from '@/api/subscriptions';import Badge from '@/components/ui/Badge.vue';defineProps<{media:ProgressItem}>()
</script>
<template>
  <article class="surface-card group relative overflow-hidden p-5">
    <div class="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-primary/[0.025] blur-2xl transition-colors group-hover:bg-primary/[0.06]" />
    <div class="relative flex items-start justify-between gap-3">
      <div class="min-w-0">
        <h3 class="truncate font-semibold tracking-tight">{{ media.title }}</h3>
        <p class="mt-1 font-mono text-xs tabular-nums text-muted">
          {{ media.owned_count }} / {{ media.aired_count }} 集已入库
        </p>
      </div>
      <Badge :tone="media.missing.length ? 'warn' : 'good'">
        {{ media.missing.length }} 集缺失
      </Badge>
    </div>
    <div class="relative mt-5 h-1.5 overflow-hidden rounded-full bg-surface-2">
      <div
        class="h-full rounded-full bg-status-ready shadow-md shadow-status-ready/40 transition-all"
        :style="{ width: media.aired_count ? `${Math.round((media.owned_count / media.aired_count) * 100)}%` : '0%' }"
      />
    </div>
    <RouterLink
      :to="`/progress#media-${media.media_id}`"
      class="relative mt-3 inline-flex min-h-[44px] items-center text-sm font-medium text-muted transition-colors hover:text-fg"
    >
      查看季集明细 <span class="ml-1 transition-transform group-hover:translate-x-0.5">→</span>
    </RouterLink>
  </article>
</template>
