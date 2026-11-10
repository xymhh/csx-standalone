<script setup lang="ts">
import { computed, ref } from 'vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'

type Option = { title?: string; label?: string; value: string | number }
type ResolvedOption = { title: string; value: string }
export type SourceField = {
  key: string
  label?: string
  type?: string
  hint?: string
  description?: string
  placeholder?: string
  default?: unknown
  items?: Option[]
  options?: Option[]
  dynamicOptions?: { scope?: string; key?: string; refreshable?: boolean }
  multiple?: boolean
  searchable?: boolean
  min?: number
  max?: number
  step?: number
  suffix?: string
  source?: string
  show?: string
}
export type AccountCard = {
  connected?: boolean
  name?: string
  username?: string
  email?: string
  avatar?: string
  points?: { label?: string; available?: number | string } | number | null
  level?: string
  is_vip?: boolean
  error?: string
  user?: { name?: string; avatar?: string; badge?: string; is_vip?: boolean; membership_supported?: boolean }
  details?: { label: string; value: string }[]
}

const props = withDefaults(
  defineProps<{
    field: SourceField
    modelValue: unknown
    options?: Option[]
    account?: AccountCard | null
    busy?: boolean
    oauthBusy?: '' | 'start' | 'exchange'
    oauthCallback?: string
    accountRefreshing?: boolean
  }>(),
  { options: () => [], account: null, busy: false, oauthBusy: '', oauthCallback: '', accountRefreshing: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  'update:oauthCallback': [value: string]
  test: []
  'refresh-account': []
  'oauth-start': []
  'oauth-exchange': []
}>()

const showPassword = ref(false)
const multiOpen = ref(false)
const multiSearch = ref('')
const tagDraft = ref('')
const orderDraft = ref('')

const items = computed<ResolvedOption[]>(() => {
  const list = props.options.length ? props.options : props.field.items || props.field.options || []
  return list.map((item) => ({
    title: String(item.title ?? item.label ?? item.value),
    value: String(item.value),
  }))
})

const selectedValues = computed<string[]>(() => {
  const value = props.modelValue
  if (Array.isArray(value)) return value.map((v) => String(v))
  if (value === null || value === undefined || value === '') return []
  return [String(value)]
})

const selectedItems = computed(() =>
  selectedValues.value.map((value) => items.value.find((item) => item.value === value) || { title: value, value }),
)

const filteredItems = computed(() => {
  const keyword = multiSearch.value.trim().toLowerCase()
  if (!keyword) return items.value
  return items.value.filter(
    (item) => item.title.toLowerCase().includes(keyword) || item.value.toLowerCase().includes(keyword),
  )
})

function toggleMulti(value: string) {
  const next = new Set(selectedValues.value)
  if (next.has(value)) next.delete(value)
  else next.add(value)
  emit('update:modelValue', [...next])
}

function removeMulti(value: string) {
  emit(
    'update:modelValue',
    selectedValues.value.filter((item) => item !== value),
  )
}

const tags = computed<string[]>(() => (Array.isArray(props.modelValue) ? props.modelValue.map((v) => String(v)) : []))

function addTags(raw: string) {
  const parts = raw
    .split(/[,，\n]/)
    .map((part) => part.trim())
    .filter(Boolean)
  if (!parts.length) return
  const next = [...tags.value]
  for (const part of parts) if (!next.includes(part)) next.push(part)
  emit('update:modelValue', next)
  tagDraft.value = ''
}

function onTagKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    addTags(tagDraft.value)
  } else if (event.key === 'Backspace' && !tagDraft.value && tags.value.length) {
    emit('update:modelValue', tags.value.slice(0, -1))
  }
}

const orderValues = computed<string[]>(() => (Array.isArray(props.modelValue) ? props.modelValue.map((v) => String(v)) : []))

function moveOrder(index: number, delta: number) {
  const next = [...orderValues.value]
  const target = index + delta
  if (target < 0 || target >= next.length) return
  ;[next[index], next[target]] = [next[target], next[index]]
  emit('update:modelValue', next)
}

function removeOrder(index: number) {
  emit(
    'update:modelValue',
    orderValues.value.filter((_, i) => i !== index),
  )
}

function addOrder() {
  const value = orderDraft.value.trim()
  if (!value) return
  if (!orderValues.value.includes(value)) emit('update:modelValue', [...orderValues.value, value])
  orderDraft.value = ''
}

const documents = computed<{ url: string; resource_types: string[] }[]>(() => {
  const value = props.modelValue
  if (!Array.isArray(value)) return []
  return value.map((row) => ({
    url: String((row as { url?: string })?.url ?? ''),
    resource_types: Array.isArray((row as { resource_types?: string[] })?.resource_types)
      ? ((row as { resource_types?: string[] }).resource_types as string[]).map((v) => String(v))
      : [],
  }))
})

const docTypes = computed<ResolvedOption[]>(() =>
  items.value.length
    ? items.value
    : [
        { title: '115网盘', value: '115' },
        { title: '123网盘', value: '123' },
        { title: '夸克网盘', value: 'quark' },
        { title: '阿里云盘', value: 'alipan' },
        { title: '百度网盘', value: 'baidu' },
        { title: 'UC网盘', value: 'uc' },
        { title: '天翼云盘', value: 'tianyi' },
        { title: '移动云盘', value: 'yun139' },
        { title: '光鸭网盘', value: 'guangya' },
        { title: '迅雷网盘', value: 'xunlei' },
      ],
)

function updateDoc(index: number, patch: Partial<{ url: string; resource_types: string[] }>) {
  const next = documents.value.map((row, i) => (i === index ? { ...row, ...patch } : { ...row }))
  emit('update:modelValue', next)
}

function toggleDocType(index: number, value: string) {
  const row = documents.value[index]
  const types = new Set(row.resource_types)
  if (types.has(value)) types.delete(value)
  else types.add(value)
  updateDoc(index, { resource_types: [...types] })
}

function addDoc(index: number) {
  const next = documents.value.map((row) => ({ ...row }))
  next.splice(index + 1, 0, { url: '', resource_types: [] })
  emit('update:modelValue', next)
}

function removeDoc(index: number) {
  const next = documents.value.map((row) => ({ ...row }))
  if (next.length <= 1) next.splice(0, 1, { url: '', resource_types: [] })
  else next.splice(index, 1)
  emit('update:modelValue', next)
}

function numberValue(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  emit('update:modelValue', raw === '' ? null : Number(raw))
}
</script>

<template>
  <!-- 开关 -->
  <Switch
    v-if="field.type === 'switch'"
    :model-value="Boolean(modelValue)"
    @update:model-value="emit('update:modelValue', $event)"
  />

  <!-- 单选下拉 -->
  <Select
    v-else-if="field.type === 'select' && !field.multiple"
    :model-value="String(modelValue ?? '')"
    :options="items.map((item) => ({ value: item.value, label: item.title }))"
    @update:model-value="emit('update:modelValue', $event)"
  />

  <!-- 多选（带搜索） -->
  <div v-else-if="field.type === 'select' && field.multiple" class="space-y-2">
    <div class="flex flex-wrap gap-1.5">
      <span
        v-for="item in selectedItems"
        :key="item.value"
        class="inline-flex items-center gap-1 rounded-md bg-primary/[0.08] px-2 py-0.5 text-[11px] text-fg-2"
      >
        {{ item.title }}
        <button type="button" class="text-subtle hover:text-rose-400 cursor-pointer" @click="removeMulti(item.value)">×</button>
      </span>
      <button
        type="button"
        class="inline-flex items-center rounded-md border border-dashed border-primary/20 px-2 py-0.5 text-[11px] text-muted hover:text-fg hover:border-primary/40 cursor-pointer"
        @click="multiOpen = !multiOpen"
      >
        {{ multiOpen ? '收起' : selectedItems.length ? '继续选择' : '选择' }}
      </button>
      <button
        v-if="selectedValues.length"
        type="button"
        class="text-[11px] text-subtle hover:text-fg-2 cursor-pointer"
        @click="emit('update:modelValue', [])"
      >
        清空
      </button>
    </div>
    <div v-if="multiOpen" class="rounded-lg border border-primary/10 bg-bg/40 p-2 space-y-2">
      <Input v-if="field.searchable !== false" v-model="multiSearch" placeholder="搜索…" class="h-8 text-xs" />
      <div class="max-h-44 overflow-y-auto space-y-0.5">
        <label
          v-for="item in filteredItems"
          :key="item.value"
          class="flex items-center gap-2 rounded px-2 py-1 text-[11px] text-fg-2 hover:bg-primary/[0.06] cursor-pointer"
        >
          <input
            type="checkbox"
            class="accent-emerald-500"
            :checked="selectedValues.includes(item.value)"
            @change="toggleMulti(item.value)"
          />
          <span class="truncate">{{ item.title }}</span>
        </label>
        <p v-if="!filteredItems.length" class="px-2 py-1.5 text-[11px] text-subtle">没有可选项</p>
      </div>
    </div>
  </div>

  <!-- 标签输入（combobox） -->
  <div
    v-else-if="field.type === 'combobox'"
    class="flex min-h-[38px] flex-wrap items-center gap-1.5 rounded-lg border border-border bg-surface/80 px-2 py-1.5"
  >
    <span
      v-for="(tag, index) in tags"
      :key="`${tag}-${index}`"
      class="inline-flex items-center gap-1 rounded bg-primary/[0.08] px-1.5 py-0.5 text-[11px] text-fg-2"
    >
      {{ tag }}
      <button type="button" class="text-subtle hover:text-rose-400 cursor-pointer" @click="emit('update:modelValue', tags.filter((_, i) => i !== index))">×</button>
    </span>
    <input
      v-model="tagDraft"
      class="h-6 min-w-[80px] flex-1 bg-transparent text-xs text-fg outline-none placeholder:text-faint"
      :placeholder="tags.length ? '' : field.placeholder || '输入后回车添加'"
      @keydown="onTagKeydown"
      @blur="addTags(tagDraft)"
    />
  </div>

  <!-- 优先级排序 -->
  <div v-else-if="field.type === 'priority-order'" class="space-y-1.5">
    <div
      v-for="(value, index) in orderValues"
      :key="`${value}-${index}`"
      class="flex items-center gap-1.5 rounded-lg border border-primary/10 bg-primary/[0.03] px-2 py-1"
    >
      <span class="w-4 text-center text-[10px] text-subtle">{{ index + 1 }}</span>
      <span class="flex-1 truncate text-xs text-fg-2">{{ value }}</span>
      <button type="button" class="px-1 text-subtle hover:text-fg cursor-pointer disabled:opacity-30" :disabled="index === 0" @click="moveOrder(index, -1)">↑</button>
      <button type="button" class="px-1 text-subtle hover:text-fg cursor-pointer disabled:opacity-30" :disabled="index === orderValues.length - 1" @click="moveOrder(index, 1)">↓</button>
      <button type="button" class="px-1 text-subtle hover:text-rose-400 cursor-pointer" @click="removeOrder(index)">×</button>
    </div>
    <div class="flex gap-1.5">
      <Input v-model="orderDraft" :placeholder="field.placeholder || '添加字幕组 / 关键词'" class="h-8 text-xs" @keydown.enter="addOrder" />
      <Button variant="outline" size="sm" class="h-8 shrink-0 text-xs" @click="addOrder">添加</Button>
    </div>
  </div>

  <!-- 在线文档 -->
  <div v-else-if="field.type === 'online-documents'" class="space-y-2">
    <div v-for="(doc, index) in documents" :key="index" class="rounded-lg border border-primary/10 bg-primary/[0.03] p-2.5 space-y-2">
      <div class="flex items-center gap-1.5">
        <Input
          :model-value="doc.url"
          placeholder="https://docs.qq.com/..."
          class="h-8 text-xs"
          @update:model-value="updateDoc(index, { url: String($event) })"
        />
        <Button variant="outline" size="sm" class="h-8 shrink-0 px-2 text-xs" title="在下方添加文档" @click="addDoc(index)">+</Button>
        <Button variant="outline" size="sm" class="h-8 shrink-0 px-2 text-xs text-rose-400" title="删除此文档" @click="removeDoc(index)">×</Button>
      </div>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="type in docTypes"
          :key="type.value"
          type="button"
          class="rounded px-1.5 py-0.5 text-[10px] transition-colors cursor-pointer"
          :class="doc.resource_types.includes(type.value) ? 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/30' : 'bg-primary/[0.05] text-muted hover:text-fg'"
          @click="toggleDocType(index, type.value)"
        >
          {{ type.title }}
        </button>
      </div>
    </div>
  </div>

  <!-- 账户信息 -->
  <div
    v-else-if="field.type === 'account'"
    class="rounded-xl border border-primary/10 bg-primary/[0.03] px-3 py-2.5"
  >
    <div v-if="account?.connected" class="flex items-center gap-3">
      <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-[11px] font-semibold text-emerald-300">
        {{ (account.name || '?').slice(0, 1).toUpperCase() }}
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-xs font-medium text-fg">{{ account.name || account.username || '已登录' }}</p>
        <div class="flex flex-wrap items-center gap-2 text-[11px] text-muted">
          <span v-if="account.level">{{ account.level }}</span>
          <span v-if="account.points !== null && account.points !== undefined">{{ account.points }} 积分</span>
          <span v-if="account.email" class="truncate">{{ account.email }}</span>
        </div>
      </div>
      <Button variant="outline" size="sm" class="h-7 shrink-0 text-[11px]" :disabled="accountRefreshing" @click="emit('refresh-account')">
        {{ accountRefreshing ? '刷新中…' : '刷新' }}
      </Button>
    </div>
    <div v-else class="flex items-center justify-between gap-3">
      <p class="text-[11px] text-subtle">{{ account?.error || '保存账户配置后可读取账户信息' }}</p>
      <Button variant="outline" size="sm" class="h-7 shrink-0 text-[11px]" :disabled="accountRefreshing" @click="emit('refresh-account')">
        {{ accountRefreshing ? '读取中…' : '读取' }}
      </Button>
    </div>
  </div>

  <!-- HDHive OAuth -->
  <div v-else-if="field.type === 'hdhive-oauth'" class="space-y-2 rounded-xl border border-primary/10 bg-primary/[0.03] p-3">
    <div class="flex flex-wrap items-center gap-2">
      <Badge :tone="oauthBusy === 'exchange' ? 'muted' : 'muted'" class="text-[10px]">授权范围 query unlock write</Badge>
      <span class="text-[11px] text-subtle">先在 HDHive 开放平台登记 Redirect URI，再发起授权。</span>
    </div>
    <Input
      :model-value="oauthCallback"
      placeholder="粘贴授权完成后的完整回调 URL（含 code 与 state）"
      class="h-8 text-xs"
      @update:model-value="emit('update:oauthCallback', String($event))"
    />
    <div class="flex flex-wrap gap-2">
      <Button variant="outline" size="sm" class="h-8 text-xs" :disabled="Boolean(oauthBusy) && oauthBusy !== 'start'" @click="emit('oauth-start')">
        {{ oauthBusy === 'start' ? '生成中…' : '打开 HDHive 授权页' }}
      </Button>
      <Button variant="outline" size="sm" class="h-8 text-xs" :disabled="Boolean(oauthBusy) || !oauthCallback.trim()" @click="emit('oauth-exchange')">
        {{ oauthBusy === 'exchange' ? '校验中…' : '校验回调并完成授权' }}
      </Button>
    </div>
  </div>

  <!-- 测试按钮 -->
  <Button
    v-else-if="field.type === 'test-source'"
    variant="outline"
    size="sm"
    class="h-8 text-xs"
    :disabled="busy"
    @click="emit('test')"
  >
    {{ busy ? '测试中…' : field.label || '测试搜索' }}
  </Button>

  <!-- 数字 -->
  <div v-else-if="field.type === 'number'" class="flex items-center gap-2">
    <Input
      type="number"
      class="h-9 text-xs"
      :min="field.min"
      :max="field.max"
      :step="field.step ?? 1"
      :placeholder="field.placeholder"
      :model-value="modelValue === null || modelValue === undefined ? '' : String(modelValue)"
      @input="numberValue"
    />
    <span v-if="field.suffix" class="shrink-0 text-[11px] text-subtle">{{ field.suffix }}</span>
  </div>

  <!-- 密码 -->
  <div v-else-if="field.type === 'password'" class="relative">
    <Input
      :type="showPassword ? 'text' : 'password'"
      class="h-9 pr-12 text-xs"
      :placeholder="field.placeholder"
      :model-value="modelValue === null || modelValue === undefined ? '' : String(modelValue)"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <button
      type="button"
      class="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] text-subtle hover:text-fg-2 cursor-pointer"
      @click="showPassword = !showPassword"
    >
      {{ showPassword ? '隐藏' : '显示' }}
    </button>
  </div>

  <!-- 多行文本 -->
  <textarea
    v-else-if="field.type === 'textarea'"
    :value="String(modelValue ?? '')"
    :placeholder="field.placeholder"
    rows="2"
    class="w-full rounded-lg border border-border bg-surface/80 px-3 py-2 text-xs text-fg outline-none placeholder:text-faint focus-visible:border-focus"
    @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
  />

  <!-- 普通文本 -->
  <Input
    v-else
    class="h-9 text-xs"
    :placeholder="field.placeholder"
    :model-value="modelValue === null || modelValue === undefined ? '' : String(modelValue)"
    @update:model-value="emit('update:modelValue', $event)"
  />
</template>
