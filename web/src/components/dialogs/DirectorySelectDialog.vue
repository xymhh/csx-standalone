<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { Folder } from '@lucide/vue'
import Dialog from '@/components/ui/Dialog.vue'
import Button from '@/components/ui/Button.vue'
import DirectoryTreeNode from '@/components/dialogs/DirectoryTreeNode.vue'
import { drivesApi, type Account, type DriveFolder } from '@/lib/api'

const props = defineProps<{ open: boolean; accounts: Account[]; accountId?: number | null }>()
const emit = defineEmits<{ close: []; select: [path: string]; 'update:accountId': [id: number] }>()
const roots = ref<DriveFolder[]>([])
const children = ref<Record<string, DriveFolder[]>>({})
const expanded = ref<Record<string, boolean>>({})
const loading = ref<Record<string, boolean>>({})
const selected = ref('')
const activeAccountId = ref<number | null>(props.accountId ?? props.accounts[0]?.id ?? null)

const rootsLoading = ref(false)
const loadError = ref('')

watch(() => props.accountId, (id) => {
  if (id) {
    activeAccountId.value = id
    if (props.open) void loadRoot()
  }
}, { immediate: true })

watch(() => props.open, (open) => {
  if (open) {
    // 每次打开弹窗，强制对齐 props 传入的指定账号
    activeAccountId.value = props.accountId ?? (props.accounts?.length ? props.accounts[0].id : null)
    void loadRoot()
  }
})

watch(() => props.accounts, (accounts) => {
  if (!activeAccountId.value && accounts?.length) {
    activeAccountId.value = props.accountId ?? accounts[0].id
    if (props.open) void loadRoot()
  }
}, { immediate: true })

async function loadRoot() {
  roots.value = []
  children.value = {}
  expanded.value = {}
  selected.value = ''
  loadError.value = ''
  if (!activeAccountId.value && props.accounts?.length) {
    activeAccountId.value = props.accounts[0].id
  }
  if (!activeAccountId.value) return
  rootsLoading.value = true
  try {
    const list = await drivesApi.folders(activeAccountId.value)
    roots.value = Array.isArray(list) ? list : []
  } catch (cause) {
    loadError.value = cause instanceof Error ? cause.message : '加载目录树失败'
  } finally {
    rootsLoading.value = false
  }
}

async function toggle(folder: DriveFolder) {
  const key = folder.id
  if (expanded.value[key]) {
    expanded.value[key] = false
    return
  }
  expanded.value[key] = true
  if (children.value[key]) return
  if (!activeAccountId.value) return
  loading.value[key] = true
  try {
    children.value[key] = await drivesApi.folders(activeAccountId.value, key)
  } finally {
    loading.value[key] = false
  }
}

  function choose(folder: DriveFolder) {
    selected.value = folder.path
  }

function chooseRoot() {
  selected.value = '/'
}

function confirm() {
  if (!selected.value) return
  if (activeAccountId.value) emit('update:accountId', activeAccountId.value)
  emit('select', selected.value)
  emit('close')
}

onMounted(() => { if (props.open) void loadRoot() })
</script>

<template>
  <Dialog :open="open" title="选择网盘目录" @close="emit('close')">
    <div class="space-y-4">
      <label class="block space-y-1.5 text-sm text-muted">
        <span>网盘账号</span>
        <select v-model.number="activeAccountId" class="min-h-11 w-full rounded-lg border border-border bg-bg px-3 text-fg" @change="loadRoot">
          <option v-for="account in accounts" :key="account.id" :value="account.id">{{ account.name }} · {{ account.provider }}</option>
        </select>
      </label>
      <div v-if="!accounts.length" class="rounded-lg border border-border p-5 text-center text-sm text-muted">请先绑定一个网盘账号。</div>
      <div v-else class="max-h-[55vh] overflow-y-auto rounded-xl border border-border/70 bg-bg/40 p-2 space-y-1">
        <button type="button" class="flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-left text-sm text-fg hover:bg-surface-2 transition-colors" :class="selected === '/' ? 'bg-surface-2 font-medium text-white' : ''" @click="chooseRoot">
          <Folder class="h-4 w-4 text-primary" />
          <span>网盘根目录 (/)</span>
        </button>

        <div v-if="rootsLoading" class="py-10 text-center text-xs text-muted space-y-2">
          <div class="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p>正在读取网盘目录树…</p>
        </div>

        <div v-else-if="loadError" class="py-8 text-center text-xs text-rose-400 space-y-2">
          <p>{{ loadError }}</p>
          <Button variant="outline" size="sm" @click="loadRoot">点击重试</Button>
        </div>

        <template v-else>
          <DirectoryTreeNode v-for="folder in roots" :key="folder.id" :folder="folder" :children="children" :expanded="expanded" :loading="loading" :selected="selected" @toggle="toggle" @choose="choose" />
          <p v-if="!roots.length" class="px-3 py-6 text-center text-xs text-muted">根目录下没有文件夹</p>
        </template>
      </div>
      <div class="flex items-center justify-between gap-3">
        <p class="min-w-0 truncate text-xs text-muted">{{ selected || '选择一个目录后确认' }}</p>
        <Button :disabled="!selected" @click="confirm">使用此目录</Button>
      </div>
    </div>
  </Dialog>
</template>
