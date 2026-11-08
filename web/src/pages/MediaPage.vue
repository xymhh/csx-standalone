<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  FolderSync,
  Copy,
  Check,
  Play,
  Trash2,
  HardDrive,
  RefreshCw,
  FolderOpen,
  Sparkles,
  Layers,
  Film,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import DirectorySelectDialog from '@/components/dialogs/DirectorySelectDialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Table from '@/components/ui/Table.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useToast } from '@/composables/useToast'
import {
  accountsApi,
  duplicateApi,
  libraryApi,
  organizeApi,
  type Account,
  type DuplicateGroup,
  type LibraryFile,
  type LibraryServer,
  type OrganizeScanResult,
} from '@/lib/api'

const tabs = [
  { value: 'files', label: '已入库文件' },
  { value: 'organize', label: '网盘全盘整理' },
  { value: 'duplicates', label: '多版本查重' },
]
const activeTab = ref('files')

const files = ref<LibraryFile[]>([])
const servers = ref<LibraryServer[]>([])
const accounts = ref<Account[]>([])
const duplicates = ref<DuplicateGroup[]>([])
const selectedDups = ref<number[]>([])
const error = ref('')
const { toast } = useToast()

// 整理表单状态
const selectedAccountId = ref<string>('')
const organizeSourcePath = ref('/CSX/_inbox')
const dirDialogOpen = ref(false)
const scanning = ref(false)
const executing = ref(false)
const scanResult = ref<OrganizeScanResult | null>(null)
const selectedFileIds = ref<string[]>([])
const copiedFileId = ref<number | null>(null)

async function loadFiles() {
  try {
    ;[files.value, servers.value] = await Promise.all([
      libraryApi.listFiles(),
      libraryApi.getServers(),
    ])
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载失败'
  }
}

async function loadDuplicates() {
  try {
    duplicates.value = await duplicateApi.list()
    // 默认全选所有待清理的低画质副本
    const toClean: number[] = []
    for (const group of duplicates.value) {
      for (const f of group.files) {
        if (!f.recommended) toClean.push(f.id)
      }
    }
    selectedDups.value = toClean
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '查重数据加载失败', 'error')
  }
}

async function loadAccounts() {
  try {
    accounts.value = await accountsApi.list()
    if (!selectedAccountId.value && accounts.value.length > 0) {
      selectedAccountId.value = String(accounts.value[0].id)
    }
  } catch {}
}

onMounted(() => {
  void loadFiles()
  void loadAccounts()
})

function switchTab(val: string) {
  activeTab.value = val
  if (val === 'files') void loadFiles()
  if (val === 'duplicates') void loadDuplicates()
}

// 整理流程
async function handleScan() {
  if (!selectedAccountId.value) {
    toast('请先绑定并选择一个网盘账号', 'error')
    return
  }
  scanning.value = true
  scanResult.value = null
  selectedFileIds.value = []
  try {
    const res = await organizeApi.scan({
      account_id: Number(selectedAccountId.value),
      source_path: organizeSourcePath.value.trim() || '/CSX/_inbox',
    })
    scanResult.value = res
    // 默认勾选所有已成功识别的
    selectedFileIds.value = res.matched.map((m) => m.file_id)
    if (!res.matched.length) {
      toast('未发现可整理的文件', 'info')
    } else {
      toast(`扫描完成，识别到 ${res.matched.length} 个可整理视频`, 'success')
    }
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '网盘扫描失败', 'error')
  } finally {
    scanning.value = false
  }
}

async function handleExecute() {
  if (!selectedAccountId.value || !selectedFileIds.value.length) return
  executing.value = true
  try {
    const res = await organizeApi.execute({
      account_id: Number(selectedAccountId.value),
      source_path: organizeSourcePath.value.trim() || '/CSX/_inbox',
      file_ids: selectedFileIds.value,
    })
    toast(`整理完成！已成功移动归位 ${res.moved.length} 个文件`, 'success')
    scanResult.value = null
    selectedFileIds.value = []
    void loadFiles()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '执行整理失败', 'error')
  } finally {
    executing.value = false
  }
}

async function cleanDuplicates() {
  if (!selectedDups.value.length) return
  try {
    const res = await duplicateApi.clean(selectedDups.value)
    toast(`已清理 ${res.deleted.length} 个冗余文件副本，释放网盘空间`, 'success')
    void loadDuplicates()
    void loadFiles()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '清理失败', 'error')
  }
}

function copyPlayUrl(fileId: number) {
  const url = `${window.location.origin}/api/v1/stream/redirect?file_id=${fileId}`
  navigator.clipboard.writeText(url)
  copiedFileId.value = fileId
  toast('已复制 302 直链播放地址到剪贴板！', 'success')
  setTimeout(() => {
    if (copiedFileId.value === fileId) copiedFileId.value = null
  }, 2000)
}

const totalSize = computed(() => files.value.reduce((n, f) => n + f.size, 0))
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-xl font-semibold tracking-tight text-fg">媒体库与整理中心</h2>
      <p class="mt-0.5 text-xs text-muted">入库媒体管理、网盘全盘扫描归位与多版本查重治理</p>
    </div>

    <!-- 顶部选项卡 -->
    <Tabs :model-value="activeTab" :items="tabs" @update:model-value="switchTab" />

    <!-- 1. 已入库文件列表 -->
    <div v-if="activeTab === 'files'" class="space-y-5">
      <div v-if="error" class="rounded-lg border border-status-missing/20 bg-status-missing/10 px-4 py-3 text-xs text-status-missing">
        {{ error }}
      </div>

      <!-- 统计指标 -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div class="rounded-xl border border-border/60 bg-surface/40 p-4">
          <p class="text-xs text-subtle">已入库视频文件</p>
          <p class="mt-1 font-mono text-2xl font-semibold text-fg">{{ files.length }}</p>
        </div>
        <div class="rounded-xl border border-border/60 bg-surface/40 p-4">
          <p class="text-xs text-subtle">媒体总容量</p>
          <p class="mt-1 font-mono text-2xl font-semibold text-fg">{{ (totalSize / 1024 ** 3).toFixed(1) }} GB</p>
        </div>
        <div class="col-span-2 sm:col-span-1 rounded-xl border border-border/60 bg-surface/40 p-4">
          <p class="text-xs text-subtle">Emby 媒体服务</p>
          <div class="mt-1 flex items-center gap-2">
            <span class="h-2 w-2 rounded-full bg-status-ready"></span>
            <span class="text-sm font-medium text-fg">302 原画直连就绪</span>
          </div>
        </div>
      </div>

      <!-- 文件表格 -->
      <div class="rounded-xl border border-border/60 bg-surface/40 overflow-hidden">
        <div v-if="!files.length" class="py-12 text-center text-xs text-muted">
          <Film class="mx-auto mb-2 h-7 w-7 text-subtle/50" />
          <p>媒体库还是空的。通过转存或手动整理即可快速填充媒体库！</p>
        </div>

        <Table v-else>
          <thead class="border-b border-border/60 text-xs text-subtle bg-surface-2/20">
            <tr>
              <th class="p-3">文件路径</th>
              <th class="p-3 w-28">画质</th>
              <th class="p-3 w-28">大小</th>
              <th class="p-3 w-28">网盘</th>
              <th class="p-3 w-32 text-right">播放直链</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/30 text-xs">
            <tr v-for="file in files" :key="file.id" class="transition-colors hover:bg-surface-2/30">
              <td class="p-3 max-w-[400px] truncate font-medium text-fg" :title="file.path">
                {{ file.path }}
              </td>
              <td class="p-3">
                <Badge tone="info" class="uppercase">{{ file.quality_bucket }}</Badge>
              </td>
              <td class="p-3 font-mono text-subtle">
                {{ (file.size / 1024 ** 3).toFixed(2) }} GB
              </td>
              <td class="p-3">
                <Badge tone="muted" class="uppercase">{{ file.provider || 'quark' }}</Badge>
              </td>
              <td class="p-3 text-right">
                <Button variant="outline" size="sm" class="h-7 text-xs" @click="copyPlayUrl(file.id)">
                  <component :is="copiedFileId === file.id ? Check : Copy" class="mr-1 h-3 w-3" />
                  {{ copiedFileId === file.id ? '已复制' : '复制 302' }}
                </Button>
              </td>
            </tr>
          </tbody>
        </Table>
      </div>
    </div>

    <!-- 2. 网盘全盘/暂存区整理 -->
    <div v-if="activeTab === 'organize'" class="space-y-5">
      <div class="rounded-xl border border-border/60 bg-surface/40 p-5 space-y-4">
        <div>
          <h3 class="text-sm font-semibold text-fg">扫描网盘未整理文件</h3>
          <p class="mt-0.5 text-xs text-muted">指定暂存文件夹，系统将自动识别片名季集并预估标准影视库归位路径</p>
        </div>

        <div class="grid gap-4 sm:grid-cols-12 items-end">
          <div class="sm:col-span-4 space-y-1 text-xs">
            <label class="text-muted">选择网盘账号</label>
            <Select
              v-model="selectedAccountId"
              :options="accounts.map((a) => ({ value: String(a.id), label: `${a.name} (${a.provider}网盘)` }))"
            />
          </div>

          <div class="sm:col-span-5 space-y-1 text-xs">
            <label class="text-muted">待整理源文件夹</label>
            <div class="flex gap-2">
              <Input v-model="organizeSourcePath" placeholder="例如 /CSX/_inbox" />
              <Button
                v-if="selectedAccountId"
                variant="outline"
                type="button"
                class="shrink-0"
                @click="dirDialogOpen = true"
              >
                浏览
              </Button>
            </div>
          </div>

          <div class="sm:col-span-3">
            <Button class="w-full" :disabled="scanning" @click="handleScan">
              <RefreshCw v-if="scanning" class="mr-1.5 h-3.5 w-3.5 animate-spin" />
              <Sparkles v-else class="mr-1.5 h-3.5 w-3.5" />
              <span>{{ scanning ? '扫描网盘中…' : '扫描并生成方案' }}</span>
            </Button>
          </div>
        </div>
      </div>

      <!-- 扫描结果预览与一键执行 -->
      <div v-if="scanResult" class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="text-xs text-muted">
            共发现 <strong class="text-fg">{{ scanResult.matched.length }}</strong> 个可整理视频，
            <span v-if="scanResult.unrecognized.length" class="text-subtle">
              {{ scanResult.unrecognized.length }} 个无法识别文件
            </span>
          </div>
          <Button
            size="sm"
            :disabled="executing || !selectedFileIds.length"
            @click="handleExecute"
          >
            <FolderSync class="mr-1.5 h-3.5 w-3.5" />
            <span>{{ executing ? '正在移动归位…' : `确认执行整理 (${selectedFileIds.length})` }}</span>
          </Button>
        </div>

        <div class="rounded-xl border border-border/60 bg-surface/40 overflow-hidden">
          <Table>
            <thead class="border-b border-border/60 text-xs text-subtle bg-surface-2/20">
              <tr>
                <th class="p-3 w-12 text-center">选择</th>
                <th class="p-3">原文件名</th>
                <th class="p-3">识别结果</th>
                <th class="p-3">归位目标路径</th>
                <th class="p-3 w-20">画质</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/30 text-xs">
              <tr v-for="item in scanResult.matched" :key="item.file_id" class="transition-colors hover:bg-surface-2/30">
                <td class="p-3 text-center">
                  <input
                    v-model="selectedFileIds"
                    type="checkbox"
                    :value="item.file_id"
                    class="h-4 w-4 rounded accent-primary"
                  />
                </td>
                <td class="p-3 truncate max-w-[200px]" :title="item.name">{{ item.name }}</td>
                <td class="p-3 whitespace-nowrap">
                  <strong class="text-fg">{{ item.title }}</strong>
                  <span class="ml-1 text-subtle">S{{ String(item.season).padStart(2, '0') }}E{{ String(item.episode).padStart(2, '0') }}</span>
                </td>
                <td class="p-3 truncate max-w-[300px] font-mono text-status-ready" :title="item.target_path">
                  {{ item.target_path }}
                </td>
                <td class="p-3">
                  <Badge tone="info" class="uppercase">{{ item.quality_bucket }}</Badge>
                </td>
              </tr>
            </tbody>
          </Table>
        </div>
      </div>
    </div>

    <!-- 3. 多版本查重与清理 -->
    <div v-if="activeTab === 'duplicates'" class="space-y-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="text-sm font-semibold text-fg">重复版本查重与清理</h3>
          <p class="mt-0.5 text-xs text-muted">同一季集若存在多个画质文件，系统已自动标出最佳版本，支持一键清理冗余释放空间</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          class="text-rose-400 hover:text-rose-300"
          :disabled="!selectedDups.length"
          @click="cleanDuplicates"
        >
          <Trash2 class="mr-1.5 h-3.5 w-3.5" />
          <span>清理选中冗余文件 ({{ selectedDups.length }})</span>
        </Button>
      </div>

      <div v-if="!duplicates.length" class="rounded-xl border border-dashed border-border/60 bg-surface/30 p-12 text-center text-xs text-muted">
        <Sparkles class="mx-auto mb-2 h-7 w-7 text-status-ready" />
        <p class="font-medium text-fg">媒体库非常整洁，没有任何重复版本！</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="group in duplicates"
          :key="`${group.media_id}-${group.season}-${group.episode}`"
          class="rounded-xl border border-border/60 bg-surface/40 p-4 space-y-2.5"
        >
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center gap-2">
              <strong class="text-fg">{{ group.title }}</strong>
              <Badge tone="muted">第 {{ group.season }} 季 第 {{ group.episode }} 集</Badge>
            </div>
            <span class="text-subtle">共 {{ group.files.length }} 个版本</span>
          </div>

          <div class="divide-y divide-border/30 rounded-lg border border-border/40 bg-surface-2/20">
            <div
              v-for="file in group.files"
              :key="file.id"
              class="flex items-center justify-between p-2.5 text-xs"
            >
              <div class="flex items-center gap-2.5 min-w-0 pr-3">
                <input
                  v-if="!file.recommended"
                  v-model="selectedDups"
                  type="checkbox"
                  :value="file.id"
                  class="h-4 w-4 rounded accent-primary shrink-0"
                />
                <span v-else class="h-4 w-4 grid place-items-center text-status-ready">★</span>
                <span class="truncate" :title="file.path">{{ file.path }}</span>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <Badge :tone="file.recommended ? 'good' : 'warn'">
                  {{ file.recommended ? '推荐保留' : '建议清理' }} ({{ file.quality_bucket.toUpperCase() }})
                </Badge>
                <span class="font-mono text-subtle text-[11px]">
                  {{ (file.size / 1024 ** 3).toFixed(2) }} GB
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 目录树弹窗 -->
    <DirectorySelectDialog
      v-if="selectedAccountId"
      :open="dirDialogOpen"
      :accounts="accounts"
      :account-id="Number(selectedAccountId)"
      @close="dirDialogOpen = false"
      @select="(path) => { organizeSourcePath = path; dirDialogOpen = false }"
    />
  </div>
</template>
