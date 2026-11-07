<script setup lang="ts">
import { onMounted, ref } from 'vue'

import EpisodeMatrix from '@/components/domain/EpisodeMatrix.vue'
import MediaCard from '@/components/domain/MediaCard.vue'
import Button from '@/components/ui/Button.vue'
import { progressApi, type ProgressItem } from '@/lib/api'

const items = ref<ProgressItem[]>([])
const selected = ref<number | null>(null)
const layout = ref<'grid' | 'list'>('grid')

onMounted(async () => {
  items.value = await progressApi.overview()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-2xl font-semibold tracking-tight text-fg">追剧进度</h2>
        <p class="mt-1 text-sm text-muted">查看每一部影视的季集状态：绿色已存入网盘，红色为待转存缺集，灰色尚未播出</p>
      </div>
      <div class="flex gap-2">
        <Button variant="outline" size="sm" :class="{ 'bg-surface-2': layout === 'grid' }" @click="layout = 'grid'">网格卡片</Button>
        <Button variant="outline" size="sm" :class="{ 'bg-surface-2': layout === 'list' }" @click="layout = 'list'">清单列表</Button>
      </div>
    </div>

    <div v-if="!items.length" class="rounded-2xl border border-dashed border-border bg-surface/40 p-12 text-center text-sm text-muted">
      暂无追剧进度数据。先去「我的订阅」添加一部剧吧！
    </div>

    <div class="grid gap-4" :class="layout === 'grid' ? 'sm:grid-cols-2 xl:grid-cols-3' : 'space-y-4'">
      <article
        v-for="media in items"
        :id="`media-${media.media_id}`"
        :key="media.media_id"
        class="space-y-3 rounded-2xl border border-border bg-surface p-5 transition-all hover:border-zinc-700"
      >
        <MediaCard :media="media" />
        <Button
          variant="outline"
          size="sm"
          class="w-full"
          @click="selected = selected === media.media_id ? null : media.media_id"
        >
          {{ selected === media.media_id ? '收起每集详情' : '展开查看各集状态' }}
        </Button>
        <EpisodeMatrix v-if="selected === media.media_id" :seasons="media.seasons" />
      </article>
    </div>
  </div>
</template>
