<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { File, Folder, LoaderCircle, Search } from '@lucide/vue'

import Dialog from '@/components/ui/Dialog.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import DirectorySelectDialog from '@/components/dialogs/DirectorySelectDialog.vue'
import { useToast } from '@/composables/useToast'
import { accountsApi, drivesApi, type Account, type ShareInspectFile } from '@/lib/api'

const props = withDefaults(
  defineProps<{
    open: boolean
    initialUrl?: string
    initialPassword?: string
    /** 打开时优先选择该网盘的账号（搜索结果里网盘类型已知） */
    preferredProvider?: '115' | 'quark' | ''
  }>(),
  { initialUrl: '', initialPassword: '', preferredProvider: '' },
)
const emit = defineEmits<{ close: [] }>()
const { toast } = useToast()
const accounts = ref<Account[]>([])
const accountId = ref<number | null>(null)
const shareUrl = ref('')
const password = ref('')
const targetDir = ref('')
const files = ref<ShareInspectFile[]>([])
const selectedIds = ref<string[]>([])
const inspecting = ref(false)
const submitting = ref(false)
const folderDialogOpen = ref(false)
const error = ref('')
const selectedAccount = computed(() => accounts.value.find((item) => item.id === accountId.value))

function pickAccount() {
  const preferred = props.preferredProvider
  const matched = preferred ? accounts.value.find((item) => item.provider === preferred) : undefined
  return matched?.id ?? accounts.value[0]?.id ?? null
}

onMounted(async () => {
  try {
    accounts.value = await accountsApi.list()
    accountId.value = pickAccount()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '账号列表加载失败'
  }
})

// 从搜索结果打开时预填链接/提取码，并自动解析一次，省掉复制粘贴
watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return
    error.value = ''
    if (!accounts.value.length) {
      try {
        accounts.value = await accountsApi.list()
      } catch (cause) {
        error.value = cause instanceof Error ? cause.message : '账号列表加载失败'
      }
    }
    accountId.value = pickAccount()
    if (props.initialUrl) {
      shareUrl.value = props.initialUrl
      password.value = props.initialPassword
      files.value = []
      selectedIds.value = []
      await inspect()
    }
  },
)

async function inspect() {
  if (!shareUrl.value.trim() || !selectedAccount.value) return
  inspecting.value = true
  error.value = ''
  try {
    const result = await drivesApi.inspectShare({
      provider: selectedAccount.value.provider === '115' ? '115' : 'quark',
      share_url: shareUrl.value.trim(),
      password: password.value,
    })
    files.value = result.files
    selectedIds.value = result.files.filter((item) => !item.is_dir).map((item) => item.id)
    targetDir.value = ''
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '分享解析失败'
  } finally {
    inspecting.value = false
  }
}

async function submit() {
  if (!accountId.value || !selectedIds.value.length || !targetDir.value) return
  submitting.value = true
  error.value = ''
  try {
    const result = await drivesApi.transferShare({
      account_id: accountId.value,
      share_url: shareUrl.value.trim(),
      password: password.value,
      file_ids: selectedIds.value,
      target_dir: targetDir.value,
    })
    toast(`已加入转存队列，任务 #${result.task_id}`, 'success')
    emit('close')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '提交转存任务失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Dialog :open="open" title="快捷转存" @close="emit('close')">
    <div class="space-y-4">
      <label class="block space-y-1.5 text-sm"><span class="text-xs text-muted">分享链接</span><Input v-model="shareUrl" placeholder="粘贴 115 或夸克分享链接" /></label>
      <div class="grid gap-3 sm:grid-cols-2">
        <label class="space-y-1.5 text-sm"><span class="text-xs text-muted">提取码（可选）</span><Input v-model="password" placeholder="提取码" /></label>
        <label class="space-y-1.5 text-sm"><span class="text-xs text-muted">转存账号</span><select v-model.number="accountId" class="min-h-11 w-full rounded-lg border border-border bg-bg px-3 text-sm text-fg"><option v-for="account in accounts" :key="account.id" :value="account.id">{{ account.name }} · {{ account.provider }}</option></select></label>
      </div>
      <Button :disabled="inspecting || !shareUrl.trim() || !accountId" variant="outline" class="w-full" @click="inspect"><LoaderCircle v-if="inspecting" class="h-4 w-4 animate-spin" /><Search v-else class="h-4 w-4" />解析分享文件</Button>
      <div v-if="files.length" class="space-y-3">
        <div class="flex items-center justify-between gap-3"><h3 class="text-sm font-semibold text-fg">选择要转存的文件</h3><span class="text-xs text-muted">已选 {{ selectedIds.length }} 项</span></div>
        <div class="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-border/70 bg-bg/40 p-2">
          <label v-for="file in files" :key="file.id" class="flex min-h-11 items-center gap-3 rounded-lg px-2 hover:bg-surface-2" :class="file.is_dir ? 'text-muted' : 'text-fg'">
            <input v-if="!file.is_dir" v-model="selectedIds" type="checkbox" :value="file.id" class="h-4 w-4 accent-primary" />
            <Folder v-else class="h-4 w-4" />
            <File v-if="!file.is_dir" class="h-4 w-4 shrink-0 text-muted" />
            <span class="min-w-0 flex-1 truncate text-sm">{{ file.name }}</span>
            <span v-if="file.size" class="text-xs tabular-nums text-muted">{{ (file.size / 1024 / 1024).toFixed(0) }} MB</span>
          </label>
        </div>
      </div>
      <div class="space-y-2 rounded-xl border border-border/70 bg-bg/30 p-3">
        <p class="text-xs font-medium text-muted">目标目录</p>
        <div class="flex items-center gap-2"><p class="min-w-0 flex-1 truncate font-mono text-sm text-fg">{{ targetDir || '尚未选择' }}</p><Button variant="outline" size="sm" :disabled="!accountId" @click="folderDialogOpen = true">浏览</Button></div>
      </div>
      <p v-if="error" class="rounded-lg border border-status-missing/30 bg-status-missing/10 p-3 text-sm text-status-missing">{{ error }}</p>
      <Button class="w-full" :disabled="submitting || !files.length || !selectedIds.length || !targetDir || !accountId" @click="submit">{{ submitting ? '正在提交…' : '立即转存' }}</Button>
    </div>
    <DirectorySelectDialog :open="folderDialogOpen" :accounts="accounts" :account-id="accountId" @close="folderDialogOpen = false" @select="targetDir = $event" @update:account-id="accountId = $event" />
  </Dialog>
</template>
