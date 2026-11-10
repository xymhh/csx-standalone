<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ChevronDown, RefreshCw, RotateCcw, Search } from '@lucide/vue'
import SearchSourceField from '@/components/config/SearchSourceField.vue'
import { sourceIcon } from '@/components/settings/sources/sourceIcons'
import { useHdhiveOauth } from '@/components/settings/sources/useHdhiveOauth'
import { useToast } from '@/composables/useToast'
import { type SearchSourceSchema, type SearchSourceTest, type SourceMeta, searchSourcesApi } from '@/api/sources'

// 单个搜索渠道的详情面板：账户卡片 + 连通性测试 + 参数分组，字段值以 v-model:sourceValues 与父级共享
const props = defineProps<{
  source: SearchSourceSchema
  selected: string
  active: boolean
}>()
const sourceValues = defineModel<Record<string, Record<string, any>>>('sourceValues', { required: true })

const { toast } = useToast()

const sourceTest = ref<SearchSourceTest | null>(null)
const sourceTestRunning = ref(false)
const sourceMeta = ref<SourceMeta>({ accounts: {}, options: {} })
const sourceMetaLoading = ref(false)
const sourceAccountRefreshing = ref(false)
const pansouMeta = ref<{ channels: { title: string; value: string }[]; plugins: { title: string; value: string }[]; status?: string }>({ channels: [], plugins: [] })
const collapsedGroups = ref<Record<string, boolean>>({})

// 切换渠道时清空上一个渠道的测试结果（与原 pickSource 行为一致）
watch(
  () => props.selected,
  () => {
    sourceTest.value = null
  },
)

const currentAccount = computed(() => sourceMeta.value.accounts[props.selected] || null)

async function testSelectedSource() {
  if (!props.selected) return
  sourceTestRunning.value = true
  sourceTest.value = null
  try {
    sourceTest.value = await searchSourcesApi.test(props.selected)
  } catch (cause) {
    sourceTest.value = {
      valid: false,
      elapsed_ms: 0,
      message: cause instanceof Error ? cause.message : '测试失败',
    }
  } finally {
    sourceTestRunning.value = false
  }
}

function groupTitle(group: { title?: string }): string {
  const title = String(group.title || '').trim()
  if (!title) return '参数配置'
  if (title === props.source?.name) return '账号与连接'
  return title
}

function toggleGroup(key: string) {
  collapsedGroups.value = { ...collapsedGroups.value, [key]: !collapsedGroups.value[key] }
}

function isGroupCollapsed(key: string): boolean {
  return Boolean(collapsedGroups.value[key])
}

function restoreSourceDefaults() {
  const source = props.source
  if (!source) return
  const values = { ...(sourceValues.value[source.id] || {}) }
  for (const group of source.groups) {
    for (const field of group.fields) {
      if (field.default !== undefined && field.key && !['account', 'test'].some((t) => (field.type || '').includes(t))) {
        values[field.key] = field.default
      }
    }
  }
  sourceValues.value[source.id] = values
  toast(`${source.name} 已恢复为默认值，记得点「保存配置」`, 'success')
}

function accountPoints(card: { points?: unknown } | null): string {
  const points = card?.points
  const raw = points && typeof points === 'object' ? (points as { available?: unknown }).available : points
  const value = Number(raw)
  if (!Number.isFinite(value)) return ''
  return value.toLocaleString('zh-CN')
}

function accountPointsLabel(card: { points?: unknown } | null): string {
  const points = card?.points
  return points && typeof points === 'object' ? String((points as { label?: string }).label || '可用积分') : '可用积分'
}

async function loadSourceMeta() {
  sourceMetaLoading.value = true
  try {
    const meta = await searchSourcesApi.meta()
    sourceMeta.value = meta
    const pansou = meta.options?.pansou || {}
    pansouMeta.value = {
      channels: pansou.channels || [],
      plugins: pansou.plugins || [],
      status: pansou.status,
    }
  } catch {
    // 元数据失败不阻塞设置页
  } finally {
    sourceMetaLoading.value = false
  }
}

function sourceFieldVisible(field: { show?: string }) {
  const expr = String(field.show || '').trim()
  if (!expr) return true
  const match = expr.match(/^config\.([A-Za-z0-9_]+)\s*(?:===\s*['"]([^'"]*)['"])?$/)
  if (!match) return true
  const values = sourceValues.value[props.source?.id || '']
  const value = values?.[match[1]]
  if (match[2] === undefined) return Boolean(value)
  return String(value) === match[2]
}

function sourceFieldCols(field: { cols?: number }) {
  const cols = Number(field.cols || 12)
  if (cols <= 3) return 'col-span-12 sm:col-span-3'
  if (cols === 4) return 'col-span-12 sm:col-span-4'
  if (cols === 6) return 'col-span-12 sm:col-span-6'
  if (cols === 8) return 'col-span-12 sm:col-span-8'
  return 'col-span-12'
}

function sourceFieldOptions(field: {
  dynamicOptions?: { scope?: string; key?: string }
  items?: { title?: string; label?: string; value: string | number }[]
}) {
  const dynamic = field.dynamicOptions
  if (dynamic?.scope === 'pansou') {
    return dynamic.key === 'plugins' ? pansouMeta.value.plugins : pansouMeta.value.channels
  }
  return (field.items || []).map((item) => ({
    title: String(item.title ?? item.label ?? item.value),
    value: String(item.value),
  }))
}

async function refreshSourceOptions(field: { key?: string; dynamicOptions?: { scope?: string; key?: string } }) {
  const dynamic = field.dynamicOptions
  if (!dynamic?.scope || !dynamic.key) return
  try {
    const result = await searchSourcesApi.refreshOptions(dynamic.scope, dynamic.key)
    const items = result.items || []
    if (dynamic.scope === 'pansou' && dynamic.key === 'plugins') pansouMeta.value.plugins = items
    else if (dynamic.scope === 'pansou') pansouMeta.value.channels = items
    toast(`已刷新 ${items.length} 个可选项`, items.length ? 'success' : 'error')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '刷新选项失败', 'error')
  }
}

const { sourceOauthBusy, sourceOauthCallback, startHdhiveOauth, exchangeHdhiveOauth } =
  useHdhiveOauth(sourceValues)

const sourceAccountPending = ref<Set<string>>(new Set())

// 进入某个渠道时静默拉一次账户信息，卡片才能一进页面就显示
async function ensureSourceAccount(sourceId: string) {
  if (!sourceId || sourceId === 'general') return
  if (sourceMeta.value.accounts[sourceId]) return
  if (sourceAccountPending.value.has(sourceId)) return
  const pending = new Set(sourceAccountPending.value)
  pending.add(sourceId)
  sourceAccountPending.value = pending
  try {
    const card = await searchSourcesApi.refreshAccount(sourceId)
    sourceMeta.value.accounts = { ...sourceMeta.value.accounts, [sourceId]: card }
  } catch {
    // 静默失败：卡片位置会提示未连接，不打扰用户
  } finally {
    const next = new Set(sourceAccountPending.value)
    next.delete(sourceId)
    sourceAccountPending.value = next
  }
}

watch([() => props.selected, () => props.active], () => {
  if (props.active) void ensureSourceAccount(props.selected)
})

async function refreshSourceAccount(sourceId: string) {
  sourceAccountRefreshing.value = true
  try {
    const card = await searchSourcesApi.refreshAccount(sourceId)
    sourceMeta.value.accounts = { ...sourceMeta.value.accounts, [sourceId]: card }
    if (card.connected) toast(`已读取 ${card.name || '账户'} 信息`, 'success')
    else toast(card.error || '账户信息读取失败', 'error')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '账户信息读取失败', 'error')
  } finally {
    sourceAccountRefreshing.value = false
  }
}

defineExpose({ reloadMeta: loadSourceMeta })

onMounted(() => {
  void loadSourceMeta()
  void ensureSourceAccount(props.selected)
})
</script>

<template>
      <div class="apple-glass overflow-hidden rounded-2xl">
        <!-- 渠道标题 -->
        <div class="flex items-center justify-between gap-3 px-4 py-3">
          <div class="flex min-w-0 items-center gap-2">
            <component :is="sourceIcon(source.id)" class="h-4 w-4 shrink-0 text-emerald-400" />
            <h4 class="truncate text-sm font-semibold text-fg">{{ source.name }}</h4>
          </div>
          <div class="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              class="flex items-center gap-1 rounded-lg border border-primary/10 px-2 py-1 text-[11px] text-muted hover:border-primary/25 hover:text-fg cursor-pointer"
              :disabled="sourceTestRunning"
              @click="testSelectedSource"
            >
              <Search class="h-3 w-3" />
              {{ sourceTestRunning ? '测试中…' : '测试' }}
            </button>
            <button
              type="button"
              class="flex items-center gap-1 rounded-lg border border-rose-500/25 px-2 py-1 text-[11px] text-rose-300 hover:bg-rose-500/10 cursor-pointer"
              @click="restoreSourceDefaults"
            >
              <RotateCcw class="h-3 w-3" />
              恢复默认值
            </button>
          </div>
        </div>

        <!-- 账户卡片 -->
        <div v-if="currentAccount" class="flex items-start gap-3 border-t border-primary/[0.06] px-4 py-3.5">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary/[0.06]">
            <img v-if="currentAccount.user?.avatar" :src="currentAccount.user.avatar" class="h-full w-full object-cover" alt="" />
            <component :is="sourceIcon(source.id)" v-else class="h-4 w-4 text-subtle" />
          </div>
          <div class="min-w-0 flex-1 space-y-1.5">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="truncate text-sm font-medium text-fg">
                {{ currentAccount.connected ? currentAccount.user?.name || currentAccount.name || '未知用户' : '账号未连接' }}
              </span>
              <span
                v-if="currentAccount.connected && currentAccount.user?.badge"
                class="rounded-md bg-emerald-500/15 px-1.5 py-0.5 text-[10px] text-emerald-300"
              >{{ currentAccount.user.badge }}</span>
              <span
                v-if="currentAccount.connected && accountPoints(currentAccount)"
                class="rounded-md bg-primary/[0.06] px-1.5 py-0.5 text-[10px] text-fg-2"
              >{{ accountPointsLabel(currentAccount) }} {{ accountPoints(currentAccount) }}</span>
            </div>
            <div v-if="currentAccount.connected && currentAccount.details?.length" class="flex flex-wrap gap-1.5">
              <span
                v-for="item in currentAccount.details"
                :key="item.label"
                class="rounded-md bg-primary/[0.05] px-1.5 py-0.5 text-[10px] text-muted"
              >{{ item.label }}：<span class="text-fg-2">{{ item.value }}</span></span>
            </div>
            <p v-if="!currentAccount.connected" class="text-[11px] leading-relaxed text-amber-400">
              {{ currentAccount.error || '请填写登录凭证并保存配置' }}
            </p>
          </div>
          <button
            type="button"
            class="shrink-0 p-1.5 text-subtle hover:text-emerald-400 cursor-pointer"
            title="刷新账户信息"
            @click="refreshSourceAccount(source.id)"
          >
            <RefreshCw class="h-3.5 w-3.5" :class="sourceAccountRefreshing ? 'animate-spin' : ''" />
          </button>
        </div>

        <!-- 连通性结果 -->
        <div
          v-if="sourceTest"
          class="mx-4 my-2 flex items-center justify-between rounded-xl border px-3 py-2 text-[11px]"
          :class="sourceTest.valid ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-rose-500/30 bg-rose-500/10 text-rose-400'"
        >
          <span class="truncate">{{ sourceTest.valid ? '连通正常' : '连通失败' }}：{{ sourceTest.message }}</span>
          <span class="ml-2 shrink-0 font-mono text-[11px]">{{ sourceTest.elapsed_ms }} ms</span>
        </div>

        <!-- 参数分组 -->
        <section
          v-for="group in source.groups"
          :key="group.title || 'default'"
          class="border-t border-primary/[0.06]"
        >
          <button
            type="button"
            class="flex w-full items-center gap-2 px-4 py-2.5 text-left cursor-pointer"
            @click="toggleGroup(groupTitle(group))"
          >
            <ChevronDown
              class="h-3.5 w-3.5 shrink-0 text-subtle transition-transform"
              :class="isGroupCollapsed(groupTitle(group)) ? '-rotate-90' : ''"
            />
            <span class="text-xs font-semibold text-fg-2">{{ groupTitle(group) }}</span>
          </button>
          <div v-show="!isGroupCollapsed(groupTitle(group))">
            <div
              v-for="field in group.fields"
              :key="field.key"
              v-show="sourceFieldVisible(field) && field.type !== 'account' && !String(field.type || '').startsWith('test')"
              class="flex items-start gap-4 border-t border-primary/[0.04] px-4 py-3 text-xs"
            >
              <div class="w-[36%] min-w-[104px] shrink-0">
                <p class="leading-5 font-medium text-fg">{{ field.label }}</p>
                <p v-if="field.hint || field.description" class="mt-0.5 text-[11px] leading-relaxed text-subtle">
                  {{ field.hint || field.description }}
                </p>
              </div>
              <div class="min-w-0 flex-1">
                <SearchSourceField
                  :field="field"
                  :model-value="sourceValues[source.id][field.key]"
                  :options="sourceFieldOptions(field)"
                  :account="sourceMeta.accounts[source.id]"
                  :busy="sourceTestRunning"
                  :account-refreshing="sourceAccountRefreshing"
                  :oauth-busy="sourceOauthBusy"
                  :oauth-callback="sourceOauthCallback"
                  @update:model-value="sourceValues[source.id][field.key] = $event"
                  @update:oauth-callback="sourceOauthCallback = $event"
                  @test="testSelectedSource()"
                  @refresh-account="refreshSourceAccount(source.id)"
                  @oauth-start="startHdhiveOauth()"
                  @oauth-exchange="exchangeHdhiveOauth()"
                />
              </div>
            </div>
          </div>
        </section>
      </div>
</template>
