<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Plus, RefreshCw, Trash2, DownloadCloud, HardDrive, ListChecks } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Tabs from '@/components/ui/Tabs.vue'
import TaskRow from '@/components/domain/TaskRow.vue'
import { useEvents } from '@/composables/useEvents'
import { useToast } from '@/composables/useToast'
import {
  accountsApi,
  offlineApi,
  tasksApi,
  type Account,
  type OfflineTask,
  type Task,
} from '@/lib/api'

const tabs = [
  { value: 'queue', label: '本地转存队列' },
  { value: 'offline', label: '115 云端离线' },
]
const activeTab = ref('queue')

const rows = ref<Task[]>([])
const offlineTasks = ref<OfflineTask[]>([])
const accounts = ref<Account[]>([])
const selectedAccountId = ref<string>('')
const { toast } = useToast()

// 添加离线任务弹窗
const addOpen = ref(false)
const magnetUrl = ref('')
const adding = ref(false)
const loadingOffline = ref(false)

async function loadQueue() {
  rows.value = await tasksApi.list()
}

const p115Accounts = computed(() => accounts.value.filter((a) => a.provider.toLowerCase() === '115'))

async function loadAccounts() {
  try {
    accounts.value = await accountsApi.list()
    if (!selectedAccountId.value && p115Accounts.value.length > 0) {
      selectedAccountId.value = String(p115Accounts.value[0].id)
    }
  } catch {}
}

async function loadOffline() {
  if (!selectedAccountId.value) return
  loadingOffline.value = true
  try {
    offlineTasks.value = await offlineApi.tasks(Number(selectedAccountId.value))
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '获取离线任务失败', 'error')
  } finally {
    loadingOffline.value = false
  }
}

onMounted(() => {
  void loadQueue()
  void loadAccounts()
})

const { connected } = useEvents((e) => {
  if (e.type === 'task_status') void loadQueue()
})

function switchTab(val: string) {
  activeTab.value = val
  if (val === 'queue') void loadQueue()
  if (val === 'offline') void loadOffline()
}

async function retry(id: number) {
  await tasksApi.retry(id)
  toast('任务已重新排队', 'success')
  await loadQueue()
}

async function cancel(id: number) {
  await tasksApi.cancel(id)
  toast('排队任务已取消', 'success')
  await loadQueue()
}

async function submitOffline() {
  if (!selectedAccountId.value || !magnetUrl.value.trim()) return
  adding.value = true
  try {
    await offlineApi.add({
      account_id: Number(selectedAccountId.value),
      url: magnetUrl.value.trim(),
    })
    toast('离线下载任务已提交到 115 云端！', 'success')
    addOpen.value = false
    magnetUrl.value = ''
    await loadOffline()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '提交离线任务失败', 'error')
  } finally {
    adding.value = false
  }
}

async function deleteOffline(hash: string) {
  if (!selectedAccountId.value) return
  try {
    await offlineApi.delete({
      account_id: Number(selectedAccountId.value),
      hashes: [hash],
    })
    toast('已删除离线任务', 'info')
    await loadOffline()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '删除失败', 'error')
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight text-fg">转存与下载任务</h2>
        <p class="mt-0.5 text-xs text-muted">监控本地转存执行进度与 115 云端磁力离线下载</p>
      </div>
      <Badge :tone="connected ? 'good' : 'warn'">
        {{ connected ? '实时在线' : '重连中' }}
      </Badge>
    </div>

    <!-- 顶部选项卡 -->
    <Tabs :model-value="activeTab" :items="tabs" @update:model-value="switchTab" />

    <!-- 1. 本地转存队列 -->
    <div v-if="activeTab === 'queue'" class="space-y-4">
      <div v-if="!rows.length" class="rounded-xl border border-dashed border-border/60 bg-surface/30 p-12 text-center text-xs text-muted">
        <ListChecks class="mx-auto mb-2 h-7 w-7 text-subtle/50" />
        <p>当前没有正在排队或执行的转存任务</p>
      </div>

      <div v-else class="space-y-2.5">
        <TaskRow
          v-for="task in rows"
          :key="task.id"
          :task="task"
          @retry="retry"
          @cancel="cancel"
        />
      </div>
    </div>

    <!-- 2. 115 云端离线任务 -->
    <div v-if="activeTab === 'offline'" class="space-y-5">
      <!-- 头部控制栏 -->
      <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-surface/40 p-4">
        <div class="flex items-center gap-3">
          <span class="text-xs text-muted">115 网盘账号</span>
          <div class="w-48">
            <Select
              v-model="selectedAccountId"
              :options="p115Accounts.map((a) => ({ value: String(a.id), label: a.name }))"
              @update:model-value="loadOffline"
            />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" :disabled="loadingOffline" @click="loadOffline">
            <RefreshCw class="mr-1.5 h-3.5 w-3.5" :class="{ 'animate-spin': loadingOffline }" />
            <span>刷新</span>
          </Button>
          <Button size="sm" :disabled="!p115Accounts.length" @click="addOpen = true">
            <Plus class="mr-1.5 h-3.5 w-3.5" />
            <span>添加磁力离线</span>
          </Button>
        </div>
      </div>

      <div v-if="!p115Accounts.length" class="rounded-xl border border-dashed border-border/60 bg-surface/30 p-12 text-center text-xs text-muted">
        <HardDrive class="mx-auto mb-2 h-7 w-7 text-subtle/50" />
        <p>尚未绑定 115 网盘账号。请先前往「系统设置」完成 115 账号绑定即可使用云端离线下载功能。</p>
      </div>

      <div v-else-if="!offlineTasks.length" class="rounded-xl border border-dashed border-border/60 bg-surface/30 p-12 text-center text-xs text-muted">
        <DownloadCloud class="mx-auto mb-2 h-7 w-7 text-subtle/50" />
        <p>当前账号下没有进行中的离线下载任务</p>
      </div>

      <!-- 离线任务列表 -->
      <div v-else class="space-y-2.5">
        <div
          v-for="task in offlineTasks"
          :key="task.id"
          class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-border/60 bg-surface/40 p-4 transition-colors hover:border-border"
        >
          <div class="min-w-0 flex-1 pr-4">
            <div class="flex items-center gap-2">
              <strong class="truncate text-xs font-semibold text-fg" :title="task.name">{{ task.name }}</strong>
              <Badge :tone="task.state === 'completed' ? 'good' : task.state === 'failed' ? 'bad' : 'info'">
                {{ task.status_text }}
              </Badge>
            </div>
            <!-- 进度条 -->
            <div class="mt-2 flex items-center gap-3">
              <div class="h-1.5 w-36 overflow-hidden rounded-full bg-surface-2 sm:w-56">
                <div
                  class="h-full bg-status-ready transition-all"
                  :style="{ width: `${task.percent}%` }"
                />
              </div>
              <span class="font-mono text-[11px] text-subtle">
                {{ task.percent.toFixed(1) }}%
              </span>
              <span class="font-mono text-[11px] text-subtle">
                {{ (task.size / 1024 ** 3).toFixed(2) }} GB
              </span>
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <Button variant="ghost" size="sm" class="text-rose-400 hover:text-rose-300" @click="deleteOffline(task.id)">
              <Trash2 class="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加离线任务 Dialog -->
    <Dialog :open="addOpen" title="添加 115 磁力离线下载" @close="addOpen = false">
      <form class="space-y-4" @submit.prevent="submitOffline">
        <label class="block space-y-1.5 text-sm">
          <span class="font-medium text-fg">下载链接</span>
          <textarea
            v-model="magnetUrl"
            required
            rows="4"
            placeholder="粘贴磁力链接 magnet:?xt=... 或 http/https/ftp 下载地址"
            class="w-full rounded-xl border border-border bg-bg/80 p-3 font-mono text-xs leading-5 text-fg focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
          />
          <span class="text-xs text-muted">系统将直接调用 115 官方云端接口在服务器离线拉取资源</span>
        </label>
        <Button type="submit" class="w-full" :disabled="adding">
          {{ adding ? '提交中…' : '立即提交到 115 云端' }}
        </Button>
      </form>
    </Dialog>
  </div>
</template>
