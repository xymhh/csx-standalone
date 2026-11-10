<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { Copy, ExternalLink, LoaderCircle, Search, Settings2, WifiOff } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import ManualTransferDialog from '@/components/dialogs/ManualTransferDialog.vue'
import { searchApi, type SearchResultItem, type SearchSourceOption, type SearchSourceStatus } from '@/api/search'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()
const keyword = ref('')
const mediaType = ref('all')
const year = ref('')
const season = ref('')
const perSource = ref('20')
const loading = ref(false)
const searched = ref(false)
// 可用搜索源（加载失败时按空列表处理，与改造前一致）
const sourcesQuery = useQuery({
  queryKey: ['search', 'sources'],
  queryFn: () => searchApi.sources(),
})
const options = computed<SearchSourceOption[]>(() => sourcesQuery.data.value?.sources ?? [])
const selectedSources = ref<string[]>([])
const statuses = ref<SearchSourceStatus[]>([])
const items = ref<SearchResultItem[]>([])
const elapsed = ref(0)

const transferOpen = ref(false)
const transferUrl = ref('')
const transferPassword = ref('')
const transferProvider = ref<'115' | 'quark' | ''>('')

const typeOptions = [
  { value: 'all', label: '全部' },
  { value: 'movie', label: '电影' },
  { value: 'tv', label: '剧集' },
]
const limitOptions = [
  { value: '10', label: '每源 10 条' },
  { value: '20', label: '每源 20 条' },
  { value: '30', label: '每源 30 条' },
  { value: '50', label: '每源 50 条' },
]

const enabledSources = computed(() => options.value.filter((item) => item.enabled))
const activeCount = computed(() => statuses.value.filter((item) => item.status === 'ok').length)
const summary = computed(() => {
  if (!searched.value) return ''
  const ok = statuses.value.filter((item) => item.status === 'ok')
  const failed = statuses.value.filter((item) => ['error', 'timeout', 'skipped'].includes(item.status))
  const count = ok.reduce((total, item) => total + item.count, 0)
  const parts = [`${ok.length} 个渠道返回 ${count} 条`]
  if (failed.length) parts.push(`${failed.length} 个渠道不可用`)
  parts.push(`耗时 ${(elapsed.value / 1000).toFixed(1)}s`)
  return parts.join(' · ')
})
const canSearch = computed(() => keyword.value.trim().length > 0 && !loading.value)

function toggleSource(id: string, enabled: boolean) {
  if (!enabled) return
  selectedSources.value = selectedSources.value.includes(id)
    ? selectedSources.value.filter((item) => item !== id)
    : [...selectedSources.value, id]
}

async function runSearch() {
  if (!canSearch.value) return
  loading.value = true
  try {
    const data = await searchApi.run({
      q: keyword.value.trim(),
      type: mediaType.value,
      year: year.value ? Number(year.value) : null,
      season: mediaType.value === 'tv' && season.value ? Number(season.value) : null,
      sources: selectedSources.value.join(','),
      limit: Number(perSource.value),
    })
    statuses.value = data.sources
    items.value = data.items
    elapsed.value = data.elapsed_ms
    searched.value = true
    if (!data.items.length) toast('没有搜索到结果，换个关键词或检查渠道配置', 'info')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '搜索失败', 'error')
  } finally {
    loading.value = false
  }
}

function statusTone(status: SearchSourceStatus['status']) {
  if (status === 'ok') return 'good'
  if (status === 'empty') return 'muted'
  if (status === 'disabled' || status === 'skipped') return 'default'
  return 'warn'
}

function typeBadge(item: SearchResultItem) {
  const key = item.resource_type || 'unknown'
  if (key === 'magnet' || key === 'ed2k') return 'warn'
  if (key === 'unknown') return 'muted'
  return 'info'
}

function typeLabel(item: SearchResultItem) {
  if (item.resource_type === 'magnet') return '磁力'
  if (item.resource_type === 'ed2k') return '电驴'
  return item.resource_type_name || item.resource_type || '未知'
}

function openTransfer(item: SearchResultItem) {
  transferUrl.value = item.url
  transferPassword.value = item.password
  transferProvider.value = item.resource_type === '115' ? '115' : item.resource_type === 'quark' ? 'quark' : ''
  transferOpen.value = true
}

async function copyLink(item: SearchResultItem) {
  const text = item.password ? `${item.url} 提取码：${item.password}` : item.url
  try {
    await navigator.clipboard.writeText(text)
    toast('链接已复制', 'success')
  } catch {
    toast('复制失败，请手动选择文本', 'error')
  }
}

function openSourcePage(item: SearchResultItem) {
  const url = item.source_url || item.media_page_url
  if (url) window.open(url, '_blank', 'noopener')
}
</script>

<template>
  <div class="space-y-5">
    <Card class="p-5 sm:p-7">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 class="text-xl font-semibold text-fg">搜索新资源</h1>
          <p class="mt-1 text-sm text-muted">聚合后台已配置的搜索渠道，找到网盘或磁力直接转存</p>
        </div>
        <RouterLink to="/settings" class="inline-flex min-h-11 items-center gap-1.5 text-sm text-primary">
          <Settings2 class="h-4 w-4" />渠道设置
        </RouterLink>
      </div>

      <form class="mt-5 space-y-3" @submit.prevent="runSearch">
        <div class="flex flex-col gap-2 sm:flex-row">
          <Input v-model="keyword" class="min-h-[52px] flex-1" placeholder="输入影视名称，如 三体 / 沙丘2" />
          <Button type="submit" class="min-h-[52px] sm:w-36" :disabled="!canSearch">
            <LoaderCircle v-if="loading" class="h-4 w-4 animate-spin" />
            <Search v-else class="h-4 w-4" />
            {{ loading ? '搜索中…' : '开始搜索' }}
          </Button>
        </div>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Select v-model="mediaType" :options="typeOptions" />
          <Input v-model="year" inputmode="numeric" placeholder="年份（可选）" />
          <Input v-model="season" inputmode="numeric" :disabled="mediaType !== 'tv'" placeholder="季（剧集可选）" />
          <Select v-model="perSource" :options="limitOptions" />
        </div>
      </form>

      <div v-if="options.length" class="mt-4 space-y-2">
        <p class="text-xs text-muted">搜索范围（不选则查全部已启用渠道）</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="source in options"
            :key="source.id"
            type="button"
            class="min-h-9 rounded-full border px-3 text-xs transition-colors"
            :class="[
              !source.enabled ? 'cursor-not-allowed border-border/60 text-muted/60 line-through' : 'border-border text-fg hover:border-primary/60',
              selectedSources.includes(source.id) ? 'border-primary bg-primary/10 text-primary' : '',
            ]"
            :disabled="!source.enabled"
            @click="toggleSource(source.id, source.enabled)"
          >
            {{ source.name }}
          </button>
        </div>
      </div>
    </Card>

    <Card v-if="searched" class="p-4 sm:p-5">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <p class="text-sm font-medium text-fg">{{ summary }}</p>
        <p class="text-xs text-muted">{{ activeCount }} / {{ statuses.length }} 个渠道命中</p>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <Badge v-for="status in statuses" :key="status.id" :tone="statusTone(status.status)">
          {{ status.name }}<template v-if="status.status === 'ok'">· {{ status.count }}</template>
        </Badge>
      </div>
      <details v-if="statuses.some((item) => item.message)" class="mt-3 text-xs text-muted">
        <summary class="cursor-pointer">查看渠道提示</summary>
        <ul class="mt-2 space-y-1">
          <li v-for="status in statuses.filter((item) => item.message)" :key="status.id">
            {{ status.name }}：{{ status.message }}
          </li>
        </ul>
      </details>
    </Card>

    <Card class="p-4 sm:p-5">
      <div v-if="loading" class="space-y-3">
        <div v-for="index in 4" :key="index" class="h-16 animate-pulse rounded-xl bg-surface-2/60" />
      </div>
      <template v-else-if="items.length">
        <ul class="divide-y divide-border/60">
          <li v-for="item in items" :key="item.id" class="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div class="min-w-0 space-y-1">
              <p class="truncate text-sm font-medium text-fg" :title="item.title">{{ item.title }}</p>
              <div class="flex flex-wrap items-center gap-1.5 text-xs text-muted">
                <Badge tone="default">{{ item.source_name }}</Badge>
                <Badge :tone="typeBadge(item)">{{ typeLabel(item) }}</Badge>
                <span v-if="item.size_text">{{ item.size_text }}</span>
                <span v-if="item.fansub">{{ item.fansub }}</span>
                <span v-if="item.update_time">{{ item.update_time }}</span>
                <span v-if="item.needs_unlock" class="text-amber-400">需解锁{{ item.unlock_points ? `（${item.unlock_points} 积分）` : '' }}</span>
              </div>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <Button v-if="item.can_transfer" size="sm" @click="openTransfer(item)">转存</Button>
              <Button v-if="item.url" variant="outline" size="sm" @click="copyLink(item)">
                <Copy class="h-3.5 w-3.5" />复制
              </Button>
              <Button
                v-if="item.source_url || item.media_page_url"
                variant="ghost"
                size="sm"
                @click="openSourcePage(item)"
              >
                <ExternalLink class="h-3.5 w-3.5" />原页
              </Button>
            </div>
          </li>
        </ul>
      </template>
      <div v-else class="flex flex-col items-center gap-2 py-10 text-center text-sm text-muted">
        <WifiOff class="h-6 w-6 text-muted" />
        <template v-if="!searched">输入关键词后开始搜索</template>
        <template v-else-if="!enabledSources.length">
          还没有启用任何搜索渠道，<RouterLink to="/settings" class="text-primary">去设置</RouterLink>
        </template>
        <template v-else>没有匹配结果，试试更短的关键词或年份</template>
      </div>
    </Card>

    <ManualTransferDialog
      :open="transferOpen"
      :initial-url="transferUrl"
      :initial-password="transferPassword"
      :preferred-provider="transferProvider"
      @close="transferOpen = false"
    />
  </div>
</template>
