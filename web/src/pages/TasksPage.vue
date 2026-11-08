<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  DownloadCloud,
  History,
  Layers,
  ListChecks,
  Plus,
  RefreshCw,
  Trash2,
  HardDrive,
  Clock,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Table from '@/components/ui/Table.vue'
import Tabs from '@/components/ui/Tabs.vue'
import CandidateCard from '@/components/domain/CandidateCard.vue'
import TaskRow from '@/components/domain/TaskRow.vue'
import { useEvents } from '@/composables/useEvents'
import { useToast } from '@/composables/useToast'
import {
  accountsApi,
  candidatesApi,
  historyApi,
  offlineApi,
  tasksApi,
  type Account,
  type Candidate,
  type OfflineTask,
  type Task,
} from '@/lib/api'

const tabs = [
  { value: 'queue', label: '正在转存' },
  { value: 'history', label: '转存历史' },
  { value: 'offline', label: '115 云端离线' },
  { value: 'candidates', label: '待选资源' },
]
const activeTab = ref('queue')

const rows = ref<Task[]>([])
const historyRows = ref<Task[]>([])
const candidates = ref<Candidate[]>([])
const offlineTasks = ref<OfflineTask[]>([])
const accounts = ref<Account[]>([])
const selectedAccountId = ref<string>('')
const selectedHistory = ref<number[]>([])
const { toast } = useToast()

// 添加离线任务
const addOpen = ref(false)
const magnetUrl = ref('')
const adding = ref(false)
const loadingOffline = ref(false)

async function loadQueue() {
  rows.value = await tasksApi.list()
}

async function loadHistory() {
  historyRows.value = await historyApi.list()
}

async function loadCandidates() {
  candidates.value = await candidatesApi.list({ state: 'discovered' })
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

useEvents((e) => {
  if (e.type === 'task_status') {
    void loadQueue()
    if (activeTab.value === 'history') void loadHistory()
  }
})

function switchTab(val: string) {
  activeTab.value = val
  if (val === 'queue') void loadQueue()
  if (val === 'history') void loadHistory()
  if (val === 'offline') void loadOffline()
  if (val === 'candidates') void loadCandidates()
}

async function retry(id: number) {
  await tasksApi.retry(id)
  toast('已重新排队开始转存', 'success')
  await loadQueue()
}

async function cancel(id: number) {
  await tasksApi.cancel(id)
  toast('转存任务已取消', 'info')
  await loadQueue()
}

async function retryHistoryBatch() {
  if (!selectedHistory.value.length) return
  try {
    const res = await historyApi.retryBatch(selectedHistory.value)
    toast(`已重新排队 ${res.retried.length} 个任务`, 'success')
    selectedHistory.value = []
    await loadHistory()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '重试失败', 'error')
  }
}

async function acceptCandidate(id: number) {
  try {
    const res = await candidatesApi.accept(id)
    toast(`已提交转存任务 #${res.task_id}`, 'success')
    await loadCandidates()
    void loadQueue()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '采纳失败', 'error')
  }
}

async function ignoreCandidate(id: number) {
  await candidatesApi.ignore(id)
  toast('已忽略该资源', 'info')
  await loadCandidates()
}

async function submitOffline() {
  if (!selectedAccountId.value || !magnetUrl.value.trim()) return
  adding.value = true
  try {
    await offlineApi.add({
      account_id: Number(selectedAccountId.value),
      url: magnetUrl.value.trim(),
    })
    toast('已提交到 115 官方云端离线！', 'success')
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
    toast('已删除该离线任务', 'info')
    await loadOffline()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '删除失败', 'error')
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-xl font-semibold tracking-tight text-fg">传输与下载管理</h2>
      <p class="mt-0.5 text-xs text-muted">监控本地转存进度、历史流水、115 云端磁力离线以及全网搜集的待选资源</p>
    </div>

    <!-- 顶部清晰选项卡 -->
    <Tabs :model-value="activeTab" :items="tabs" @update:model-value="switchTab" />

    <!-- 1. 正在转存队列 -->
    <div v-if="activeTab === 'queue'" class="space-y-4">
      <div v-if="!rows.length" class="rounded-2xl border border-dashed border-border/60 bg-surface/30 p-16 text-center text-xs text-muted">
        <DownloadCloud class="mx-auto mb-2 h-8 w-8 text-subtle/50" />
        <p class="font-medium text-fg">当前没有正在转存的任务</p>
        <p class="mt-1 text-subtle">系统在后台全天候监控追剧清单，一旦发现新资源会自动加入此队列。</p>
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

    <!-- 2. 转存历史 -->
    <div v-if="activeTab === 'history'" class="space-y-4">
      <div class="flex items-center justify-between">
        <span class="text-xs text-muted">已记录终态任务流水</span>
        <Button
          variant="outline"
          size="sm"
          :disabled="!selectedHistory.length"
          @click="retryHistoryBatch"
        >
          批量重试所选 ({{ selectedHistory.length }})
        </Button>
      </div>

      <div class="rounded-xl border border-border/60 bg-surface/40 overflow-hidden">
        <Table>
          <thead class="border-b border-border/60 text-xs text-subtle bg-surface-2/20">
            <tr>
              <th class="p-3 w-10 text-center">选择</th>
              <th class="p-3">任务编号</th>
              <th class="p-3">状态</th>
              <th class="p-3">尝试次数</th>
              <th class="p-3">错误信息</th>
              <th class="p-3 text-right">时间</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/30 text-xs">
            <tr v-for="row in historyRows" :key="row.id" class="transition-colors hover:bg-surface-2/30">
              <td class="p-3 text-center">
                <input
                  v-if="row.state === 'dead_letter'"
                  v-model="selectedHistory"
                  type="checkbox"
                  :value="row.id"
                  class="h-4 w-4 rounded accent-primary"
                />
              </td>
              <td class="p-3 font-mono font-medium text-fg">#{{ row.id }}</td>
              <td class="p-3">
                <Badge :tone="row.state === 'succeeded' ? 'good' : 'bad'">
                  {{ row.state === 'succeeded' ? '已转存入库' : '转存失败' }}
                </Badge>
              </td>
              <td class="p-3 font-mono text-subtle">{{ row.attempt }}</td>
              <td class="p-3 max-w-sm truncate text-subtle" :title="row.last_error ?? ''">
                {{ row.last_error ?? '—' }}
              </td>
              <td class="p-3 text-right text-subtle font-mono whitespace-nowrap">
                {{ new Date(row.updated_at).toLocaleString() }}
              </td>
            </tr>
          </tbody>
        </Table>
      </div>
    </div>

    <!-- 3. 115 云端离线任务 -->
    <div v-if="activeTab === 'offline'" class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-surface/40 p-4">
        <div class="flex items-center gap-3">
          <span class="text-xs text-muted">115 账号</span>
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

      <div v-if="!p115Accounts.length" class="rounded-2xl border border-dashed border-border/60 bg-surface/30 p-12 text-center text-xs text-muted">
        <HardDrive class="mx-auto mb-2 h-7 w-7 text-subtle/50" />
        <p>尚未绑定 115 网盘账号。请先前往「系统设置」完成扫码绑定。</p>
      </div>

      <div v-else-if="!offlineTasks.length" class="rounded-2xl border border-dashed border-border/60 bg-surface/30 p-12 text-center text-xs text-muted">
        <DownloadCloud class="mx-auto mb-2 h-7 w-7 text-subtle/50" />
        <p>当前账号没有离线任务</p>
      </div>

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
            <div class="mt-2 flex items-center gap-3">
              <div class="h-1.5 w-36 overflow-hidden rounded-full bg-surface-2 sm:w-56">
                <div class="h-full bg-status-ready transition-all" :style="{ width: `${task.percent}%` }" />
              </div>
              <span class="font-mono text-[11px] text-subtle">{{ task.percent.toFixed(1) }}%</span>
              <span class="font-mono text-[11px] text-subtle">{{ (task.size / 1024 ** 3).toFixed(2) }} GB</span>
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

    <!-- 4. 待选资源 -->
    <div v-if="activeTab === 'candidates'" class="space-y-4">
      <div v-if="!candidates.length" class="rounded-2xl border border-dashed border-border/60 bg-surface/30 p-12 text-center text-xs text-muted">
        <Layers class="mx-auto mb-2 h-7 w-7 text-subtle/50" />
        <p>暂无待处理候选资源</p>
      </div>

      <div class="grid gap-3.5 lg:grid-cols-2">
        <CandidateCard
          v-for="candidate in candidates"
          :key="candidate.id"
          :candidate="candidate"
          @accept="acceptCandidate"
          @ignore="ignoreCandidate"
        />
      </div>
    </div>

    <!-- 添加 115 磁力离线 Dialog -->
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
          <span class="text-xs text-muted">提交后 115 云端服务器将自动离线下载</span>
        </label>
        <Button type="submit" class="w-full" :disabled="adding">
          {{ adding ? '提交中…' : '立即提交到 115 云端' }}
        </Button>
      </form>
    </Dialog>
  </div>
</template>
