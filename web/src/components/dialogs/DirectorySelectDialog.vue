<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Folder, FolderPlus } from '@lucide/vue'
import Dialog from '@/components/ui/Dialog.vue'
import Button from '@/components/ui/Button.vue'
import DirectoryTreeNode from '@/components/dialogs/DirectoryTreeNode.vue'
import { drivesApi, type Account, type DriveFolder } from '@/lib/api'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ open: boolean; accounts: Account[]; accountId?: number | null }>()
const emit = defineEmits<{ close: []; select: [path: string]; 'update:accountId': [id: number] }>()
const { toast } = useToast()
const roots = ref<DriveFolder[]>([])
const children = ref<Record<string, DriveFolder[]>>({})
const expanded = ref<Record<string, boolean>>({})
const loading = ref<Record<string, boolean>>({})
const selected = ref('')
const selectedId = ref('0')
const activeAccountId = ref<number | null>(props.accountId ?? props.accounts[0]?.id ?? null)

const rootsLoading = ref(false)
const loadError = ref('')

const creating = ref(false)
const newFolderName = ref('')
const createError = ref('')
const createBusy = ref(false)
const nameInput = ref<HTMLInputElement | null>(null)

const parentLabel = computed(() => selected.value || '/')

function resetTree() {
  roots.value = []
  children.value = {}
  expanded.value = {}
  loadError.value = ''
}

watch(() => props.accountId, (id) => {
  if (id) {
    activeAccountId.value = id
    if (props.open) void loadRoot()
  }
}, { immediate: true })

watch(() => props.open, (open) => {
  if (open) {
    // 每次打开弹窗，强制对齐 props 传入的指定账号，并清空上一次的展开与选中状态
    activeAccountId.value = props.accountId ?? (props.accounts?.length ? props.accounts[0].id : null)
    cancelCreate()
    void loadRoot()
  }
})

watch(() => props.accounts, (accounts) => {
  if (!activeAccountId.value && accounts?.length) {
    activeAccountId.value = props.accountId ?? accounts[0].id
    if (props.open) void loadRoot()
  }
}, { immediate: true })

async function loadRoot(resetSelection = true) {
  resetTree()
  if (resetSelection) {
    selected.value = ''
    selectedId.value = '0'
  }
  if (!activeAccountId.value && props.accounts?.length) {
    activeAccountId.value = props.accounts[0].id
  }
  if (!activeAccountId.value) return
  rootsLoading.value = true
  try {
    const list = await drivesApi.folders(activeAccountId.value, '', '/')
    roots.value = Array.isArray(list) ? list : []
  } catch (cause) {
    loadError.value = cause instanceof Error ? cause.message : '加载目录树失败'
  } finally {
    rootsLoading.value = false
  }
}

async function loadChildren(folder: DriveFolder) {
  if (!activeAccountId.value) return
  loading.value[folder.id] = true
  try {
    children.value[folder.id] = await drivesApi.folders(activeAccountId.value, folder.id, folder.path)
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '读取目录失败', 'error')
  } finally {
    loading.value[folder.id] = false
  }
}

async function toggle(folder: DriveFolder) {
  const key = folder.id
  if (expanded.value[key]) {
    expanded.value[key] = false
    return
  }
  expanded.value[key] = true
  delete children.value[key]
  await loadChildren(folder)
}

function choose(folder: DriveFolder) {
  selected.value = folder.path
  selectedId.value = folder.id
}

function chooseRoot() {
  selected.value = '/'
  selectedId.value = '0'
}

function confirm() {
  if (!selected.value) return
  if (activeAccountId.value) emit('update:accountId', activeAccountId.value)
  emit('select', selected.value)
  emit('close')
}

async function startCreate() {
  creating.value = true
  createError.value = ''
  newFolderName.value = ''
  await nextTick()
  nameInput.value?.focus()
}

function cancelCreate() {
  creating.value = false
  newFolderName.value = ''
  createError.value = ''
  createBusy.value = false
}

async function submitCreate() {
  const name = newFolderName.value.trim()
  const accountId = activeAccountId.value
  if (!accountId) return
  if (!name) {
    createError.value = '请输入文件夹名称'
    return
  }
  if (name.includes('/') || name.includes('\\')) {
    createError.value = '文件夹名称不能包含斜杠'
    return
  }
  createBusy.value = true
  createError.value = ''
  const parentId = selectedId.value
  const parentPath = selected.value || '/'
  try {
    const created = await drivesApi.createFolder(accountId, {
      parent_id: parentId,
      parent_path: parentPath,
      name,
    })
    if (parentId === '0') {
      await loadRoot(false)
    } else {
      delete children.value[parentId]
      expanded.value[parentId] = true
      await loadChildren({ id: parentId, name: '', path: parentPath, has_children: true })
    }
    selected.value = created.path
    selectedId.value = created.id
    toast(`已新建文件夹「${created.name}」`, 'success')
    cancelCreate()
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : '新建文件夹失败'
  } finally {
    createBusy.value = false
  }
}

onMounted(() => { if (props.open) void loadRoot() })
</script>

<template>
  <Dialog :open="open" title="选择网盘目录" @close="emit('close')">
    <div class="space-y-4">
      <label class="block space-y-1.5 text-sm text-muted">
        <span>网盘账号</span>
        <select v-model.number="activeAccountId" class="min-h-11 w-full rounded-lg border border-border bg-bg px-3 text-fg" @change="loadRoot()">
          <option v-for="account in accounts" :key="account.id" :value="account.id">{{ account.name }} · {{ account.provider }}</option>
        </select>
      </label>
      <div v-if="!accounts.length" class="rounded-lg border border-border p-5 text-center text-sm text-muted">请先绑定一个网盘账号。</div>
      <div v-else class="space-y-2">
        <div class="flex items-center justify-between gap-2 px-1">
          <p class="min-w-0 truncate text-xs text-muted">当前目录：{{ parentLabel }}</p>
          <button
            type="button"
            class="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-border/70 px-2.5 py-1.5 text-xs text-fg transition-colors hover:bg-surface-2 disabled:opacity-50"
            :disabled="creating || rootsLoading || !!loadError"
            @click="startCreate"
          >
            <FolderPlus class="h-3.5 w-3.5 text-primary" />
            新建文件夹
          </button>
        </div>
        <div v-if="creating" class="space-y-1.5 rounded-xl border border-primary/40 bg-surface-2/60 p-2.5">
          <div class="flex items-center gap-2">
            <input
              ref="nameInput"
              v-model="newFolderName"
              maxlength="128"
              placeholder="文件夹名称"
              class="min-h-10 min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 text-sm text-fg outline-none focus:border-primary"
              @keyup.enter="submitCreate"
              @keyup.esc="cancelCreate"
            />
            <Button size="sm" :disabled="createBusy" @click="submitCreate">{{ createBusy ? '创建中…' : '创建' }}</Button>
            <Button size="sm" variant="outline" :disabled="createBusy" @click="cancelCreate">取消</Button>
          </div>
          <p class="px-1 text-xs text-muted">将创建在 {{ parentLabel }}</p>
          <p v-if="createError" class="px-1 text-xs text-rose-400">{{ createError }}</p>
        </div>
        <div class="max-h-[55vh] overflow-y-auto rounded-xl border border-border/70 bg-bg/40 p-2 space-y-1">
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
            <Button variant="outline" size="sm" @click="loadRoot()">点击重试</Button>
          </div>

          <template v-else>
            <DirectoryTreeNode v-for="folder in roots" :key="folder.id" :folder="folder" :children="children" :expanded="expanded" :loading="loading" :selected="selected" @toggle="toggle" @choose="choose" />
            <p v-if="!roots.length" class="px-3 py-6 text-center text-xs text-muted">根目录下没有文件夹</p>
          </template>
        </div>
      </div>
      <div class="flex items-center justify-between gap-3">
        <p class="min-w-0 truncate text-xs text-muted">{{ selected || '选择一个目录后确认' }}</p>
        <Button :disabled="!selected" @click="confirm">使用此目录</Button>
      </div>
    </div>
  </Dialog>
</template>
