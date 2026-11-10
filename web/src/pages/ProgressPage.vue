<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { ChevronDown, ChevronUp, Film } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import EpisodeMatrix from '@/components/domain/EpisodeMatrix.vue'
import MediaDrawer from '@/components/domain/MediaDrawer.vue'
import { progressApi } from '@/api/subscriptions'

const { data } = useQuery({
  queryKey: ['progress', 'overview'],
  queryFn: () => progressApi.overview(),
})
const items = computed(() => data.value ?? [])
const expanded = ref<Record<number, boolean>>({})
const drawerMediaId = ref<number | null>(null)

function toggle(id: number) {
  expanded.value[id] = !expanded.value[id]
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold tracking-tight text-fg">追剧进度</h2>
        <p class="mt-0.5 text-xs text-muted">监控关注剧集的入库情况与缺失集数</p>
      </div>
      <Badge tone="muted">共 {{ items.length }} 部关注中</Badge>
    </div>

    <EmptyState
      v-if="!items.length"
      :icon="Film"
      title="暂无追剧进度数据"
      description="先去「我的订阅」添加一部剧吧！"
    />

    <!-- 剧集卡片流：单个卡片，不套娃 -->
    <div class="space-y-3">
        <div
          v-for="media in items"
        :key="media.media_id"
        class="rounded-xl border border-border/60 bg-surface/40 p-4 transition-colors hover:border-border/90"
        :id="`media-${media.media_id}`"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2.5">
              <button class="min-h-11 truncate text-left text-sm font-semibold text-fg hover:text-primary" @click="drawerMediaId = media.media_id">{{ media.title }}</button>
              <Badge :tone="media.missing.length ? 'warn' : 'good'">
                {{ media.missing.length ? `缺 ${media.missing.length} 集` : '全集已入库' }}
              </Badge>
            </div>
            <!-- 进度条与数字 -->
            <div class="mt-2 flex items-center gap-3">
              <div class="h-1.5 w-32 overflow-hidden rounded-full bg-surface-2 sm:w-48">
                <div
                  class="h-full bg-status-ready transition-all"
                  :style="{
                    width: media.aired_count ? `${Math.round((media.owned_count / media.aired_count) * 100)}%` : '0%',
                  }"
                />
              </div>
              <span class="font-mono text-xs text-subtle">
                {{ media.owned_count }} / {{ media.aired_count }} 集
              </span>
            </div>
          </div>

          <!-- 展开按钮 -->
          <Button variant="ghost" size="sm" class="text-xs text-muted hover:text-fg" @click="toggle(media.media_id)">
            <span>{{ expanded[media.media_id] ? '收起详情' : '季集详情' }}</span>
            <component :is="expanded[media.media_id] ? ChevronUp : ChevronDown" class="ml-1 h-3.5 w-3.5" />
          </Button>
        </div>

        <!-- 展开后的季集矩阵 -->
        <div v-if="expanded[media.media_id]" class="mt-4 border-t border-border/40 pt-4">
          <EpisodeMatrix :seasons="media.seasons" />
        </div>
      </div>
    </div>
    <MediaDrawer :open="drawerMediaId !== null" :media-id="drawerMediaId" @close="drawerMediaId = null" />
  </div>
</template>
