<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { Plus, RefreshCw, Trash2, Pause, Play, Film, SlidersHorizontal } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { useToast } from '@/composables/useToast'
import { subscriptionsApi, type Subscription } from '@/api/subscriptions'

const subscriptionsQuery = useQuery({
  queryKey: ['subscriptions'],
  queryFn: () => subscriptionsApi.list(),
})
const rows = computed(() => subscriptionsQuery.data.value ?? [])
const open = ref(false)
const syncingId = ref<number | null>(null)
const { toast } = useToast()

// 表单字段
const title = ref('')
const mediaType = ref('tv')
const year = ref<number | undefined>(new Date().getFullYear())
const seasonNumber = ref(1)
const episodeCount = ref(12)
const tmdbId = ref<number | undefined>(undefined)
const showAdvanced = ref(false)

async function load() {
  await subscriptionsQuery.refetch()
}

async function create() {
  try {
    if (!title.value.trim()) {
      toast('请输入影视片名', 'error')
      return
    }
    await subscriptionsApi.create({
      title: title.value.trim(),
      media_type: mediaType.value,
      year: year.value || undefined,
      season_number: mediaType.value === 'tv' ? seasonNumber.value : 1,
      episode_count: mediaType.value === 'tv' ? episodeCount.value : 1,
      tmdb_id: tmdbId.value || undefined,
    })
    open.value = false
    title.value = ''
    tmdbId.value = undefined
    await load()
    toast('追剧订阅已添加！系统已开始全网找源', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '添加失败', 'error')
  }
}

async function toggle(row: Subscription) {
  await subscriptionsApi.update(row.id, {
    state: row.state === 'active' ? 'paused' : 'active',
  })
  await load()
  toast(row.state === 'active' ? '已暂停追剧' : '已恢复追剧', 'info')
}

async function sync(id: number) {
  if (syncingId.value !== null) return
  syncingId.value = id
  try {
    const response = await subscriptionsApi.sync(id)
    toast(response.message, 'success')
    await load()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '搜源失败', 'error')
  } finally {
    syncingId.value = null
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-2xl font-semibold tracking-tight text-fg">我的追剧清单</h2>
        <p class="mt-1 text-sm text-muted">管理你正在追的电视剧和电影，系统会自动全网找源并转存最新更新</p>
      </div>
      <Button @click="open = true" class="flex items-center gap-2">
        <Plus class="h-4 w-4" />
        <span>添加追剧</span>
      </Button>
    </div>

    <div v-if="!rows.length" class="rounded-2xl border border-dashed border-border bg-surface/40 p-12 text-center text-sm text-muted">
      <Film class="mx-auto mb-3 h-8 w-8 text-muted" />
      <p class="font-medium text-fg">你的追剧清单还是空的</p>
      <p class="mt-1 text-xs text-muted">点击右上角「添加追剧」，输入片名即可全自动追更。</p>
    </div>

    <div class="grid gap-3.5 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="row in rows" :key="row.id" class="rounded-xl border border-border bg-surface p-5 transition-all hover:border-surface-3">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-semibold text-fg">{{ row.media?.title ?? `影视 #${row.media_id}` }}</h3>
            <p class="mt-1 text-xs text-muted">类型：{{ row.media?.type === 'movie' ? '电影' : '电视剧' }} · 编号 #{{ row.id }}</p>
          </div>
          <Badge :tone="row.state === 'active' ? 'good' : 'muted'" :pulse="row.state === 'active'">
            {{ row.state === 'active' ? '正在追更' : '已暂停' }}
          </Badge>
        </div>

        <div class="mt-4 flex flex-wrap gap-2 pt-2 border-t border-border/60">
          <Button variant="outline" size="sm" @click="toggle(row)">
            <component :is="row.state === 'active' ? Pause : Play" class="mr-1.5 h-3.5 w-3.5" />
            {{ row.state === 'active' ? '暂停' : '继续追' }}
          </Button>
          <Button variant="outline" size="sm" :disabled="syncingId !== null" @click="sync(row.id)">
            <RefreshCw class="mr-1.5 h-3.5 w-3.5" :class="syncingId === row.id ? 'animate-spin' : ''" />
            {{ syncingId === row.id ? '搜源中…' : '立即找资源' }}
          </Button>
          <Button variant="ghost" size="sm" class="text-rose-400 hover:text-rose-300 ml-auto" @click="subscriptionsApi.delete(row.id).then(load)">
            <Trash2 class="h-3.5 w-3.5" />
          </Button>
        </div>
      </article>
    </div>

    <!-- 全新大白话添加追剧弹窗 -->
    <Dialog :open="open" title="添加追更订阅" @close="open = false">
      <form class="space-y-4" @submit.prevent="create">
        <label class="block space-y-1.5 text-sm">
          <span class="font-medium text-fg">影视名称</span>
          <Input v-model="title" required placeholder="例如：庆余年、边水往事、死侍" />
          <span class="text-xs text-muted">直接输入中文或英文片名</span>
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="block space-y-1.5 text-sm">
            <span class="font-medium text-fg">类型</span>
            <Select
              v-model="mediaType"
              :options="[
                { value: 'tv', label: '电视剧 / 动漫 / 综艺' },
                { value: 'movie', label: '电影' },
              ]"
            />
          </label>
          <label class="block space-y-1.5 text-sm">
            <span class="font-medium text-fg">上映年份 (可选)</span>
            <Input v-model.number="year" type="number" min="1900" max="2100" placeholder="例如 2024" />
          </label>
        </div>

        <!-- 电视剧专属季数与集数设置 -->
        <div v-if="mediaType === 'tv'" class="grid grid-cols-2 gap-3 p-3 rounded-lg border border-border/60 bg-surface-2/30">
          <label class="block space-y-1 text-xs">
            <span class="text-muted">追更季数</span>
            <Input v-model.number="seasonNumber" type="number" min="1" max="100" />
          </label>
          <label class="block space-y-1 text-xs">
            <span class="text-muted">预计总集数</span>
            <Input v-model.number="episodeCount" type="number" min="1" max="1000" />
          </label>
        </div>

        <!-- 高级选填折叠 -->
        <div>
          <button
            type="button"
            class="flex items-center gap-1.5 text-xs text-muted hover:text-fg"
            @click="showAdvanced = !showAdvanced"
          >
            <SlidersHorizontal class="h-3 w-3" />
            <span>{{ showAdvanced ? '收起高级选项' : '高级选项 (可选 TMDB ID)' }}</span>
          </button>
          <div v-if="showAdvanced" class="mt-2 pt-2 border-t border-border/40">
            <label class="block space-y-1 text-xs">
              <span class="text-muted">TMDB ID (选填)</span>
              <Input v-model.number="tmdbId" type="number" placeholder="例如 94954" />
            </label>
          </div>
        </div>

        <Button type="submit" class="w-full">立即添加并开始全网找源</Button>
      </form>
    </Dialog>
  </div>
</template>
