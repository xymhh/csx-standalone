<script setup lang="ts">
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import type { Candidate } from '@/lib/api'

defineProps<{ candidate: Candidate }>()
defineEmits<{ accept: [id: number]; ignore: [id: number] }>()
</script>

<template>
  <article class="surface-card group relative overflow-hidden p-5 transition-colors hover:border-primary/20">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="mb-2 font-mono text-[10px] uppercase tracking-wider text-subtle">
          {{ candidate.provider }} <span class="mx-1 text-border">/</span> #{{ candidate.id }}
        </p>
        <h3 class="break-all font-semibold tracking-tight">
          {{ candidate.payload.title ?? (candidate.share_url || `候选 #${candidate.id}`) }}
        </h3>
        <p class="mt-1 text-xs text-muted">订阅 #{{ candidate.subscription_id }}</p>
      </div>
      <Badge tone="info">评分 {{ candidate.score }}</Badge>
    </div>
    <p v-if="candidate.payload.quality_bucket" class="mt-4 rounded-lg bg-surface-2/60 px-3 py-2 text-sm text-muted">
      画质 <span class="ml-2 font-mono text-fg">{{ candidate.payload.quality_bucket }}</span>
    </p>
    <div class="mt-5 flex flex-wrap gap-2">
      <Button @click="$emit('accept', candidate.id)">采纳并转存</Button>
      <Button variant="outline" @click="$emit('ignore', candidate.id)">忽略</Button>
    </div>
  </article>
</template>
