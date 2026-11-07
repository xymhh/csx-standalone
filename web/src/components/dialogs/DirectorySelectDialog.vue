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

watch(() => props.accountId, (id) => { if (id) activeAccountId.value = id })
watch(() => props.open, (open) => { if (open) void loadRoot() })
watch(() => props.accounts, (accounts) => {
  if (!activeAccountId.value && accounts.length) activeAccountId.value = accounts[0].id
}, { immediate: true })

async function loadRoot() {
  roots.value = []
  children.value = {}
  expanded.value = {}
  selected.value = ''
  if (activeAccountId.value) roots.value = await drivesApi.folders(activeAccountId.value)
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
      <div v-else class="max-h-[55vh] overflow-y-auto rounded-xl border border-border/70 bg-bg/40 p-2">
        <button type="button" class="flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-left text-sm text-fg hover:bg-surface-2" :class="selected === '/' ? 'bg-surface-2' : ''" @click="chooseRoot"><Folder class="h-4 w-4 text-primary" />网盘根目录</button>
        <DirectoryTreeNode v-for="folder in roots" :key="folder.id" :folder="folder" :children="children" :expanded="expanded" :loading="loading" :selected="selected" @toggle="toggle" @choose="choose" />
        <p v-if="!roots.length" class="px-3 py-5 text-center text-sm text-muted">根目录下没有文件夹。</p>
      </div>
      <div class="flex items-center justify-between gap-3">
        <p class="min-w-0 truncate text-xs text-muted">{{ selected || '选择一个目录后确认' }}</p>
        <Button :disabled="!selected" @click="confirm">使用此目录</Button>
      </div>
    </div>
  </Dialog>
</template>
