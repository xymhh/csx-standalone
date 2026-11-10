<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { AlertTriangle, ChevronDown, Film, Inbox, RefreshCw, RotateCcw, Search } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { historyApi, type HistoryGroup, type TransferTaskEnriched } from '@/api/transfer'
import {
  episodeLabel,
  failureDetailText,
  formatBytes,
  mediaTypeLabel,
  providerLabel,
  relativeTime,
  taskStateTone,
} from '@/lib/transfer'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()

const page = ref(1)
const pageSize = ref(20)
const stateFilter = ref<'all' | 'succeeded' | 'failed' | 'skipped'>('all')
const providerFilter = ref('')
const keyword = ref('')
const debouncedKeyword = ref('')
const expanded = ref(new Set<string>())
const retryingAll = ref(false)
const brokenPosters = ref(new Set<string>())

const STATE_FILTERS = [
  { value: 'all', label: '全部' },
  { value: 'succeeded', label: '已入库' },
  { value: 'failed', label: '失败' },
  { value: 'skipped', label: '跳过' },
] as const

const groups = computed<HistoryGroup[]>(() => data.value?.groups ?? [])
const total = computed(() => data.value?.total ?? 0)
const recordsTotal = computed(() => data.value?.records_total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value) || 1))
const failedInView = computed(() =>
  groups.value.reduce((sum, group) => sum + group.counts.failed, 0),
)
const providerOptions = computed(() => [
  { value: '', label: '全部来源' },
  ...(data.value?.filter_options.providers ?? []).map((provider) => ({
    value: provider,
    label: providerLabel(provider),
  })),
])

let searchTimer: ReturnType<typeof setTimeout> | undefined

// 筛选/分页条件即查询键：任一条件变化自动重新拉取（搜索词经 300ms 防抖后进入查询键）
const historyQuery = useQuery({
  queryKey: computed(
    () =>
      [
        'history',
        page.value,
        pageSize.value,
        stateFilter.value,
        providerFilter.value,
        debouncedKeyword.value,
      ] as const,
  ),
  queryFn: () =>
    historyApi.list({
      page: page.value,
      page_size: pageSize.value,
      state: stateFilter.value === 'all' ? undefined : stateFilter.value,
      provider: providerFilter.value || undefined,
      q: debouncedKeyword.value || undefined,
    }),
})
const data = computed(() => historyQuery.data.value ?? null)
const loading = computed(() => historyQuery.isFetching.value)

watch(
  () => historyQuery.error.value,
  (cause) => {
    if (cause) toast(cause instanceof Error ? cause.message : '加载转存历史失败', 'error')
  },
)
// 当前页超出总页数时回退到最后一页（与改造前 load 内的钳制逻辑一致）
watch(data, (value) => {
  if (value && page.value > totalPages.value) {
    page.value = totalPages.value
  }
})

async function load() {
  await historyQuery.refetch()
}

defineExpose({ reload: load })

function setStateFilter(value: (typeof STATE_FILTERS)[number]['value']) {
  if (stateFilter.value === value) return
  stateFilter.value = value
  page.value = 1
}

function onProviderChange(value: string) {
  providerFilter.value = value
  page.value = 1
}

function onKeywordInput(value: string) {
  keyword.value = value
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    debouncedKeyword.value = keyword.value.trim()
    page.value = 1
  }, 300)
}

function onPageSizeChange(value: string) {
  pageSize.value = Number(value)
  page.value = 1
}

function goto(target: number) {
  if (target < 1 || target > totalPages.value || target === page.value) return
  page.value = target
}

function toggle(key: string) {
  const next = new Set(expanded.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expanded.value = next
}

function isExpanded(key: string) {
  return expanded.value.has(key)
}

function posterVisible(group: HistoryGroup) {
  return group.poster_url && !brokenPosters.value.has(group.key)
}

function markPosterBroken(key: string) {
  const next = new Set(brokenPosters.value)
  next.add(key)
  brokenPosters.value = next
}

function recordStatus(record: TransferTaskEnriched): string {
  if (record.state === 'succeeded') return '已入库'
  if (record.state === 'cancelled') return '已跳过'
  return '失败'
}

function recordTone(record: TransferTaskEnriched) {
  return taskStateTone(record.state)
}

function episodeText(record: TransferTaskEnriched) {
  if (record.media_type === 'movie') return '电影'
  return episodeLabel(record.season, record.episode) || '—'
}

function recordFailureDetail(record: TransferTaskEnriched) {
  return failureDetailText(record.failure_label, record.failure_detail)
}

async function retryRecords(ids: number[]) {
  if (!ids.length) return
  try {
    const result = await historyApi.retryBatch(ids)
    toast(
      result.retried.length
        ? `已重新排队 ${result.retried.length} 个任务`
        : '这些任务已不在可重试状态',
      result.retried.length ? 'success' : 'info',
    )
    await load()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '重试失败', 'error')
  }
}

async function retryGroup(group: HistoryGroup) {
  await retryRecords(group.records.filter((record) => record.state === 'dead_letter').map((r) => r.id))
}

async function retryOne(record: TransferTaskEnriched) {
  await retryRecords([record.id])
}

async function retryAllFailed() {
  retryingAll.value = true
  try {
    const result = await historyApi.retryAllFailed()
    toast(result.retried ? `已重新排队 ${result.retried} 个失败任务` : '当前没有失败任务', result.retried ? 'success' : 'info')
    await load()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '批量重试失败', 'error')
  } finally {
    retryingAll.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- 筛选栏 -->
    <div
      class="flex flex-col gap-3 rounded-2xl border border-primary/[0.07] bg-surface/40 p-3 lg:flex-row lg:items-center"
    >
      <div class="flex items-center gap-1 overflow-x-auto scrollbar-none">
        <button
          v-for="item in STATE_FILTERS"
          :key="item.value"
          type="button"
          class="shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
          :class="
            stateFilter === item.value
              ? 'bg-primary/10 text-fg ring-1 ring-primary/10'
              : 'text-muted hover:text-fg-2'
          "
          @click="setStateFilter(item.value)"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center lg:justify-end">
        <div class="relative flex-1 sm:max-w-64">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle" />
          <Input
            :model-value="keyword"
            placeholder="搜索片名或文件名"
            class="min-h-[36px] pl-8 text-xs"
            @update:model-value="onKeywordInput"
          />
        </div>
        <div class="flex items-center gap-2">
          <Select
            :model-value="providerFilter"
            :options="providerOptions"
            class="min-h-[36px] flex-1 text-xs sm:w-36 sm:flex-none"
            @update:model-value="onProviderChange"
          />
          <Button variant="ghost" size="sm" :disabled="loading" @click="load">
            <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
          </Button>
          <Button
            v-if="failedInView"
            variant="outline"
            size="sm"
            class="justify-center"
            :disabled="retryingAll"
            @click="retryAllFailed"
          >
            <RotateCcw class="mr-1.5 h-3.5 w-3.5" />
            <span class="hidden sm:inline">重试全部失败</span>
            <span class="sm:hidden">重试失败</span>
            ({{ failedInView }})
          </Button>
        </div>
      </div>
    </div>

    <!-- 空态 -->
    <div
      v-if="!loading && !groups.length"
      class="rounded-2xl border border-dashed border-border/60 bg-surface/30 p-16 text-center text-xs text-muted"
    >
      <Inbox class="mx-auto mb-2 h-8 w-8 text-subtle/50" />
      <p class="font-medium text-fg">
        {{ keyword || providerFilter || stateFilter !== 'all' ? '没有匹配的转存记录' : '还没有转存历史' }}
      </p>
      <p class="mt-1 text-subtle">
        {{
          keyword || providerFilter || stateFilter !== 'all'
            ? '换个关键词或清空筛选条件再试。'
            : '追更清单里的新资源转存完成后会按片名归档到这里。'
        }}
      </p>
    </div>

    <!-- 分组列表 -->
    <div v-else class="space-y-2.5">
      <article
        v-for="group in groups"
        :key="group.key"
        class="overflow-hidden rounded-2xl border border-primary/[0.07] bg-surface/40"
        :class="group.counts.failed ? 'ring-1 ring-rose-500/10' : ''"
      >
        <button
          type="button"
          class="flex w-full items-center gap-3 px-3 py-3 text-left transition-colors hover:bg-primary/[0.03]"
          @click="toggle(group.key)"
        >
          <ChevronDown
            class="h-4 w-4 shrink-0 text-subtle transition-transform duration-200"
            :class="{ '-rotate-90': !isExpanded(group.key) }"
          />

          <div
            class="relative h-14 w-10 shrink-0 overflow-hidden rounded-md bg-gradient-to-br from-surface-2 to-surface-solid ring-1 ring-primary/[0.06]"
          >
            <img
              v-if="posterVisible(group)"
              :src="group.poster_url"
              alt=""
              class="h-full w-full object-cover"
              loading="lazy"
              @error="markPosterBroken(group.key)"
            />
            <Film v-else class="absolute inset-0 m-auto h-4 w-4 text-faint" />
          </div>

          <div class="min-w-0 flex-1">
            <div class="flex items-baseline gap-2">
              <h3 class="truncate text-sm font-semibold tracking-tight text-fg">
                {{ group.title }}
                <span v-if="group.year" class="ml-1 text-[11px] font-normal text-subtle">
                  {{ group.year }}
                </span>
              </h3>
              <span class="hidden shrink-0 text-[11px] text-subtle sm:inline">
                {{ mediaTypeLabel(group.type) }} · {{ group.records.length }} 条
                <template v-if="group.total_size"> · {{ formatBytes(group.total_size) }}</template>
              </span>
            </div>
            <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
              <Badge v-for="provider in group.providers" :key="provider" tone="muted">
                {{ providerLabel(provider) }}
              </Badge>
              <Badge v-if="group.counts.succeeded" tone="good">
                成功 {{ group.counts.succeeded }}
              </Badge>
              <Badge v-if="group.counts.failed" tone="bad">失败 {{ group.counts.failed }}</Badge>
              <Badge v-if="group.counts.skipped" tone="muted">跳过 {{ group.counts.skipped }}</Badge>
              <span
                v-for="label in group.failure_labels"
                :key="label.label"
                class="hidden items-center gap-1 rounded-full bg-rose-500/[0.08] px-2 py-0.5 text-[11px] text-rose-300/90 sm:inline-flex"
              >
                {{ label.label }} ×{{ label.count }}
              </span>
            </div>
          </div>

          <div class="shrink-0 text-right">
            <p class="text-[11px] text-subtle">{{ relativeTime(group.latest_at) }}</p>
            <span
              v-if="group.counts.failed"
              class="mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] text-amber-300/90 transition-colors hover:bg-amber-400/10 hover:text-amber-200"
              @click.stop="retryGroup(group)"
            >
              重试失败
            </span>
          </div>
        </button>

        <!-- 展开明细 -->
        <div v-if="isExpanded(group.key)" class="border-t border-primary/[0.06] bg-bg/20">
          <div
            v-for="record in group.records"
            :key="record.id"
            class="border-b border-primary/[0.04] px-3 py-2.5 transition-colors last:border-b-0 hover:bg-primary/[0.02] sm:px-4"
          >
            <!-- 桌面：一行看全（集号/文件名/大小/来源/画质/状态/失败原因/时间） -->
            <div class="hidden items-center gap-3 md:flex">
              <span class="w-14 shrink-0 font-mono text-[11px] text-subtle">
                {{ episodeText(record) }}
              </span>
              <span
                class="min-w-0 flex-1 truncate text-xs text-fg-2"
                :title="record.display_name"
              >
                {{ record.display_name }}
              </span>
              <span class="w-20 shrink-0 text-right font-mono text-[11px] text-subtle">
                {{ formatBytes(record.size) }}
              </span>
              <span class="w-20 shrink-0 text-[11px] text-subtle">
                {{ providerLabel(record.provider) }}
              </span>
              <span class="w-12 shrink-0 text-[11px] uppercase text-subtle">
                {{ record.quality_bucket || '—' }}
              </span>
              <Badge :tone="recordTone(record)" class="w-20 shrink-0 justify-center">
                {{ recordStatus(record) }}
              </Badge>
              <span
                class="w-36 shrink-0 truncate text-[11px] text-rose-300/80"
                :title="record.failure_detail || record.last_error || ''"
              >
                {{ record.failure_label || '—' }}
              </span>
              <span class="w-14 shrink-0 text-right text-[11px] text-subtle">
                {{ relativeTime(record.updated_at) }}
              </span>
              <span class="w-14 shrink-0 text-right">
                <Button
                  v-if="record.state === 'dead_letter'"
                  variant="ghost"
                  size="sm"
                  class="px-2 text-amber-300/90 hover:text-amber-200"
                  @click="retryOne(record)"
                >
                  重试
                </Button>
              </span>
            </div>

            <!-- 移动端：文件名独立占行，元信息折到第二行 -->
            <div class="flex items-start gap-2.5 md:hidden">
              <div class="min-w-0 flex-1">
                <p class="line-clamp-2 text-xs leading-5 text-fg-2">
                  {{ record.display_name }}
                </p>
                <div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-subtle">
                  <span class="font-mono">{{ episodeText(record) }}</span>
                  <span>{{ providerLabel(record.provider) }}</span>
                  <span>{{ formatBytes(record.size) }}</span>
                  <span v-if="record.quality_bucket" class="uppercase">
                    {{ record.quality_bucket }}
                  </span>
                  <span>{{ relativeTime(record.updated_at) }}</span>
                </div>
                <div
                  v-if="record.failure_label"
                  class="mt-1.5 flex items-start gap-1.5 text-[11px] leading-4 text-rose-300/80"
                >
                  <AlertTriangle class="mt-0.5 h-3 w-3 shrink-0" />
                  <span class="line-clamp-2">
                    {{ record.failure_label
                    }}<span v-if="recordFailureDetail(record)" class="text-rose-300/45">
                      · {{ recordFailureDetail(record) }}</span
                    >
                  </span>
                </div>
              </div>
              <div class="flex shrink-0 flex-col items-end gap-1.5">
                <Badge :tone="recordTone(record)">{{ recordStatus(record) }}</Badge>
                <Button
                  v-if="record.state === 'dead_letter'"
                  variant="ghost"
                  size="sm"
                  class="px-2 text-amber-300/90 hover:text-amber-200"
                  @click="retryOne(record)"
                >
                  重试
                </Button>
              </div>
            </div>
          </div>
        </div>
      </article>

      <!-- 分页 -->
      <div class="flex flex-wrap items-center justify-between gap-3 px-1 pt-1 text-xs text-muted">
        <span>
          共 {{ total }} 部 · {{ recordsTotal }} 条记录
          <span v-if="loading" class="ml-2 text-subtle">刷新中…</span>
        </span>
        <div class="flex items-center gap-2">
          <Select
            :model-value="String(pageSize)"
            :options="[
              { value: '20', label: '20 / 页' },
              { value: '50', label: '50 / 页' },
              { value: '100', label: '100 / 页' },
            ]"
            class="min-h-[32px] w-24 text-xs"
            @update:model-value="onPageSizeChange"
          />
          <Button variant="outline" size="sm" :disabled="page <= 1" @click="goto(page - 1)">
            上一页
          </Button>
          <span class="font-mono text-[11px] text-subtle">{{ page }} / {{ totalPages }}</span>
          <Button
            variant="outline"
            size="sm"
            :disabled="page >= totalPages"
            @click="goto(page + 1)"
          >
            下一页
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
