<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  Code2,
  HardDrive,
  KeyRound,
  Plus,
  QrCode,
  RefreshCw,
  Search,
  Sliders,
  Trash2,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DirectorySelectDialog from '@/components/dialogs/DirectorySelectDialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useToast } from '@/composables/useToast'
import {
  accountsApi,
  ApiError,
  searchSourcesApi,
  settingsApi,
  type Account,
  type QrcodeCheckResponse,
  type QrcodeStartResponse,
  type SearchSourceSchema,
  type SearchSourceTest,
  type SettingSection,
} from '@/lib/api'

// 设置 7 大顶级选项卡（网盘账号作为独立第一项，其他页面底部彻底去除硬塞）
const tabs = [
  { value: 'accounts', label: '网盘账号' },
  { value: 'baseline', label: '追剧规则' },
  { value: 'sources', label: '搜索找源' },
  { value: 'transfer', label: '网盘转存' },
  { value: 'strm', label: '直链播放' },
  { value: 'notify', label: '消息通知' },
  { value: 'advanced', label: '高级设置' },
]

const activeTab = ref('accounts')
const sectionDesc: Record<string, string> = {
  accounts: '绑定你的 115 或夸克网盘账号，支持手机 App 一键扫码免抓 Cookie 快速绑定',
  baseline: '配置默认检查更新的时间范围与剧集元数据语言偏好',
  sources: '配置全网 15 个搜索源的独立开关、凭据与专属参数，支持实时连通检测',
  transfer: '设置转存的目标网盘、文件夹以及画质洗版偏好',
  strm: '配置供 Emby / Jellyfin / 播放器调用的 STRM 本地挂载或 302 直链模式',
  notify: '转存完成、发现新剧或发生异常时通过微信、飞书或 Telegram 提醒',
  advanced: '系统底层运行参数与并发连接控制',
}

const rawData = ref<Record<string, unknown>>({})
const rawJson = ref('{}')
const showRawJson = ref(false)
const accounts = ref<Account[]>([])
const { toast } = useToast()

// 15 个搜索源状态
const sourceSchemas = ref<SearchSourceSchema[]>([])
const sourceValues = ref<Record<string, Record<string, any>>>({})
const selectedSourceId = ref('pansou')
const sourceTest = ref<SearchSourceTest | null>(null)
const sourceTestRunning = ref(false)

// 扫码弹窗状态
const qrOpen = ref(false)
const qrProvider = ref<'115' | 'quark'>('115')
const qrName = ref('我的网盘账号')
const qrData = ref<QrcodeStartResponse | null>(null)
const qrStatus = ref<'idle' | 'starting' | 'waiting' | 'scanned' | 'success' | 'expired' | 'error'>('idle')
const qrMessage = ref('')
const qrStarting = ref(false)
let qrPollTimer = 0
let qrCheckInFlight = false
let qrGeneration = 0

// 手动账号弹窗
const manualOpen = ref(false)
const manualEditing = ref<Account | null>(null)
const manualProvider = ref('115')
const manualName = ref('')
const manualCredential = ref('')

// 目录树弹窗
const dirDialogOpen = ref(false)
const dirTargetField = ref<'transfer' | 'mount'>('transfer')

// 图形化表单状态
const form = ref<Record<string, any>>({
  window_days: 14,
  language: 'zh-CN',
  scan_interval_seconds: 30,
  tmdb_api_key: '',
  default_drive: 'quark',
  transfer_root: 'CSX',
  upgrade_enabled: true,
  min_quality: 'hd',
  strm_mode: 'local_mount',
  local_mount_root: '/mnt/quark',
  url_template: '',
  feishu_enabled: false,
  feishu_url: '',
  telegram_enabled: false,
  telegram_token: '',
  telegram_chat_id: '',
  webhook_enabled: false,
  webhook_url: '',
  log_level: 'INFO',
  max_workers: 8,
})

async function loadSettings() {
  if (activeTab.value === 'accounts') return
  if (activeTab.value === 'sources') {
    await loadSources()
    return
  }
  const sec = activeTab.value as SettingSection
  rawData.value = await settingsApi.getSection(sec)
  rawJson.value = JSON.stringify(rawData.value, null, 2)
  const d = rawData.value || {}
  if (sec === 'baseline') {
    form.value.window_days = Number(d.window_days ?? 14)
    form.value.language = String(d.language ?? 'zh-CN')
    form.value.scan_interval_seconds = Number(d.scan_interval_seconds ?? 30)
    form.value.tmdb_api_key = String(d.tmdb_api_key ?? '')
  } else if (sec === 'transfer') {
    form.value.default_drive = String(d.default_drive ?? 'quark')
    form.value.transfer_root = String(d.transfer_root ?? 'CSX')
    form.value.upgrade_enabled = Boolean(d.upgrade_enabled ?? true)
    form.value.min_quality = String(d.min_quality ?? 'hd')
  } else if (sec === 'strm') {
    form.value.strm_mode = String(d.mode ?? 'local_mount')
    form.value.local_mount_root = String(d.local_mount_root ?? '/mnt/quark')
    form.value.url_template = String(d.url_template ?? '')
  } else if (sec === 'notify') {
    const ch = (d.channels as Record<string, any>) || {}
    form.value.feishu_enabled = Boolean(ch.feishu?.enabled ?? false)
    form.value.feishu_url = String(ch.feishu?.webhook_url ?? '')
    form.value.telegram_enabled = Boolean(ch.telegram?.enabled ?? false)
    form.value.telegram_token = String(ch.telegram?.bot_token ?? '')
    form.value.telegram_chat_id = String(ch.telegram?.chat_id ?? '')
    form.value.webhook_enabled = Boolean(ch.webhook?.enabled ?? false)
    form.value.webhook_url = String(ch.webhook?.url ?? '')
  } else if (sec === 'advanced') {
    form.value.log_level = String(d.log_level ?? 'INFO')
    form.value.max_workers = Number(d.max_workers ?? 8)
  }
}

async function loadSources() {
  try {
    const schemas = await searchSourcesApi.schema()
    sourceSchemas.value = schemas
    const values: Record<string, Record<string, unknown>> = {}
    for (const schema of schemas) {
      const current: Record<string, unknown> = { enabled: schema.enabled }
      for (const group of schema.groups) {
        for (const field of group.fields) {
          current[field.key] = field.value ?? field.default ?? ''
        }
      }
      values[schema.id] = current
    }
    sourceValues.value = values
    if (!selectedSourceId.value || !schemas.some((s) => s.id === selectedSourceId.value)) {
      selectedSourceId.value = schemas[0]?.id ?? 'pansou'
    }
  } catch (cause) {
    toast('加载搜索源配置失败', 'error')
  }
}

async function loadAccounts() {
  try {
    accounts.value = await accountsApi.list()
  } catch {}
}

onMounted(() => {
  void loadAccounts()
})

watch(activeTab, () => {
  if (activeTab.value === 'accounts') void loadAccounts()
  else void loadSettings()
})

async function save() {
  try {
    if (activeTab.value === 'sources') {
      await searchSourcesApi.save(sourceValues.value)
      toast('搜索源设置已保存', 'success')
      return
    }

    const sec = activeTab.value as SettingSection
    let payload: Record<string, unknown> = {}

    if (showRawJson.value) {
      payload = JSON.parse(rawJson.value)
    } else if (sec === 'baseline') {
      payload = {
        window_days: Number(form.value.window_days),
        language: form.value.language,
        scan_interval_seconds: Number(form.value.scan_interval_seconds),
        tmdb_api_key: String(form.value.tmdb_api_key || '').trim(),
      }
    } else if (sec === 'transfer') {
      payload = {
        default_drive: form.value.default_drive,
        transfer_root: form.value.transfer_root,
        upgrade_enabled: Boolean(form.value.upgrade_enabled),
        min_quality: form.value.min_quality,
      }
    } else if (sec === 'strm') {
      payload = {
        mode: form.value.strm_mode,
        local_mount_root: form.value.local_mount_root,
        url_template: form.value.url_template,
      }
    } else if (sec === 'notify') {
      payload = {
        channels: {
          feishu: { enabled: form.value.feishu_enabled, webhook_url: form.value.feishu_url },
          telegram: { enabled: form.value.telegram_enabled, bot_token: form.value.telegram_token, chat_id: form.value.telegram_chat_id },
          webhook: { enabled: form.value.webhook_enabled, url: form.value.webhook_url },
        },
      }
    } else if (sec === 'advanced') {
      payload = {
        log_level: form.value.log_level,
        max_workers: Number(form.value.max_workers),
      }
    }

    rawData.value = await settingsApi.updateSection(sec, payload)
    rawJson.value = JSON.stringify(rawData.value, null, 2)
    toast('设置保存成功', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败', 'error')
  }
}

// 扫码相关
function stopQrcodePolling() {
  if (qrPollTimer) {
    window.clearInterval(qrPollTimer)
    qrPollTimer = 0
  }
}

function closeQrcode() {
  qrGeneration += 1
  stopQrcodePolling()
  qrOpen.value = false
  qrData.value = null
  qrStatus.value = 'idle'
}

async function pollQrcode() {
  if (!qrData.value || qrCheckInFlight || !qrOpen.value) return
  const generation = qrGeneration
  const session = qrData.value
  qrCheckInFlight = true
  try {
    const result = await accountsApi.checkQrcode({
      provider: session.provider,
      token_data: session.token_data,
      name: qrName.value.trim(),
      auto_save: true,
    })
    if (generation !== qrGeneration) return
    qrStatus.value = result.status
    qrMessage.value = result.status === 'waiting'
      ? '等待手机扫码…'
      : result.status === 'scanned'
        ? '已扫码，请在手机上点击确认登录…'
        : result.message
    if (result.status === 'expired') {
      stopQrcodePolling()
      return
    }
    if (result.status === 'success' && result.account) {
      stopQrcodePolling()
      toast('网盘账号绑定成功！', 'success')
      closeQrcode()
      await loadAccounts()
    }
  } catch (cause) {
    if (generation !== qrGeneration) return
    qrMessage.value = '状态检测暂时失败，正在重试…'
  } finally {
    qrCheckInFlight = false
  }
}

async function startQrcode() {
  qrGeneration += 1
  stopQrcodePolling()
  qrData.value = null
  qrStatus.value = 'starting'
  qrStarting.value = true
  qrMessage.value = '正在向网盘官方申请登录二维码…'
  try {
    qrData.value = await accountsApi.startQrcode(qrProvider.value)
    qrStatus.value = 'waiting'
    qrMessage.value = '等待手机扫码…'
    qrPollTimer = window.setInterval(() => void pollQrcode(), 2000)
  } catch (cause) {
    qrStatus.value = 'error'
    qrMessage.value = cause instanceof Error ? cause.message : '二维码生成失败'
  } finally {
    qrStarting.value = false
  }
}

function openScanDialog() {
  qrProvider.value = '115'
  qrName.value = '我的115账号'
  qrOpen.value = true
  void startQrcode()
}

// 搜索源测试
async function testSelectedSource() {
  if (!selectedSourceId.value) return
  sourceTestRunning.value = true
  sourceTest.value = null
  try {
    sourceTest.value = await searchSourcesApi.test(selectedSourceId.value)
  } catch (cause) {
    sourceTest.value = {
      valid: false,
      elapsed_ms: 0,
      message: cause instanceof Error ? cause.message : '连通测试失败',
    }
  } finally {
    sourceTestRunning.value = false
  }
}

async function removeAccount(id: number) {
  await accountsApi.delete(id)
  await loadAccounts()
  toast('账号已解绑', 'info')
}

async function testAccount(id: number) {
  try {
    const res = await accountsApi.test(id)
    toast(`${res.provider}网盘：${res.message}`, res.valid ? 'success' : 'error')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '检测失败', 'error')
  }
}

const currentSource = computed(() => sourceSchemas.value.find((s) => s.id === selectedSourceId.value))
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-xl font-semibold tracking-tight text-fg">系统设置</h2>
      <p class="mt-0.5 text-xs text-muted">管理你的网盘账号、追更规则、全网搜索站点与播放方式</p>
    </div>

    <!-- 7 大顶级选项卡（网盘账号为专属第一 Tab） -->
    <Tabs v-model="activeTab" :items="tabs" />

    <!-- Tab 1: 网盘账号专属管理区（彻底解耦） -->
    <div v-if="activeTab === 'accounts'" class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/60 bg-surface/40 p-5">
        <div>
          <h3 class="text-base font-semibold text-fg">网盘账号管理</h3>
          <p class="mt-0.5 text-xs text-muted">绑定你的 115 或夸克网盘，转存的影视将直接保存到你的网盘中（已采用 Fernet 高度加密保存）</p>
        </div>
        <div class="flex items-center gap-2">
          <Button size="sm" class="flex items-center gap-1.5 shadow-sm shadow-white/10" @click="openScanDialog">
            <QrCode class="h-4 w-4" />
            <span>扫码绑定新网盘</span>
          </Button>
        </div>
      </div>

      <div v-if="!accounts.length" class="rounded-2xl border border-dashed border-border/60 bg-surface/30 p-16 text-center text-xs text-muted">
        <HardDrive class="mx-auto mb-2 h-8 w-8 text-subtle/50" />
        <p class="font-medium text-fg">尚未绑定任何网盘账号</p>
        <p class="mt-1 text-subtle">点击右上角「扫码绑定新网盘」，使用手机 App 扫码即可 10 秒免抓包自动绑定。</p>
      </div>

      <div v-else class="grid gap-3.5 sm:grid-cols-2">
        <article
          v-for="account in accounts"
          :key="account.id"
          class="rounded-xl border border-border/60 bg-surface/40 flex items-center justify-between gap-4 p-4.5 transition-all hover:border-zinc-700"
        >
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <strong class="font-semibold text-fg text-sm">{{ account.name }}</strong>
              <Badge tone="muted" class="text-[10px] uppercase font-mono">{{ account.provider }}网盘</Badge>
            </div>
            <p class="mt-1.5 text-xs text-subtle">
              {{ account.has_credential ? '凭据状态：Fernet 工业级加密保存' : '凭据状态：未设置' }}
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <Button variant="outline" size="sm" @click="testAccount(account.id)">
              <RefreshCw class="mr-1 h-3.5 w-3.5" />
              检测连通
            </Button>
            <Button variant="ghost" size="sm" class="text-rose-400 hover:text-rose-300" @click="removeAccount(account.id)">
              <Trash2 class="h-3.5 w-3.5" />
            </Button>
          </div>
        </article>
      </div>
    </div>

    <!-- Tab 2: 搜索找源 15 源全量自描述配置 -->
    <div v-else-if="activeTab === 'sources'" class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border/60 bg-surface/40 p-4">
        <div>
          <h3 class="text-sm font-semibold text-fg">搜索找源</h3>
          <p class="mt-0.5 text-xs text-muted">配置全网 15 个搜索源的专属参数与独立连通性测试</p>
        </div>
        <Button size="sm" @click="save">保存所有搜索源设置</Button>
      </div>

      <div class="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
        <!-- 左侧 15 源垂直列表 -->
        <nav class="space-y-1 rounded-xl border border-border/60 bg-surface/30 p-2 max-h-[640px] overflow-y-auto">
          <button
            v-for="s in sourceSchemas"
            :key="s.id"
            type="button"
            class="flex min-h-10 w-full items-center justify-between rounded-lg px-3 text-left text-xs font-medium transition-colors"
            :class="selectedSourceId === s.id ? 'bg-surface-2 text-fg ring-1 ring-border' : 'text-muted hover:bg-surface-2/60'"
            @click="selectedSourceId = s.id; sourceTest = null"
          >
            <span>{{ s.name }}</span>
            <span
              class="h-2 w-2 rounded-full"
              :class="sourceValues[s.id]?.enabled === false ? 'bg-zinc-600' : 'bg-status-ready shadow-[0_0_8px_var(--color-status-ready)]'"
            />
          </button>
        </nav>

        <!-- 右侧当前源专属自描述表单 -->
        <div v-if="currentSource" class="space-y-4">
          <div class="flex items-center justify-between rounded-xl border border-border/60 bg-surface/40 p-4">
            <div>
              <h4 class="text-sm font-semibold text-fg">{{ currentSource.name }}</h4>
              <p class="mt-0.5 text-xs text-muted">排序权重：{{ currentSource.order }}</p>
            </div>
            <Button variant="outline" size="sm" :disabled="sourceTestRunning" @click="testSelectedSource">
              <Search class="mr-1.5 h-3.5 w-3.5" />
              <span>{{ sourceTestRunning ? '检测中…' : '测试该搜索源' }}</span>
            </Button>
          </div>

          <div
            v-if="sourceTest"
            class="rounded-xl border p-3.5 text-xs flex items-center justify-between"
            :class="sourceTest.valid ? 'border-status-ready/30 bg-status-ready/10 text-status-ready' : 'border-status-missing/30 bg-status-missing/10 text-status-missing'"
          >
            <span>{{ sourceTest.valid ? '连通正常' : '连通失败' }}：{{ sourceTest.message }}</span>
            <span class="font-mono">{{ sourceTest.elapsed_ms }} ms</span>
          </div>

          <div v-for="(group, gIndex) in currentSource.groups" :key="gIndex" class="rounded-xl border border-border/60 bg-surface/40 p-5 space-y-4">
            <h5 class="text-xs font-semibold text-fg uppercase tracking-wider text-muted">{{ group.title || '基本配置' }}</h5>
            <div class="grid gap-4 sm:grid-cols-2">
              <div v-for="field in group.fields" :key="field.key" class="space-y-1.5 text-xs">
                <label class="font-medium text-fg flex items-center justify-between">
                  <span>{{ field.label }}</span>
                  <Switch
                    v-if="field.type === 'switch'"
                    v-model="sourceValues[currentSource.id][field.key]"
                  />
                </label>
                <p v-if="field.description" class="text-[11px] text-muted">{{ field.description }}</p>
                <Input
                  v-if="field.type === 'text' || field.type === 'number'"
                  v-model="sourceValues[currentSource.id][field.key]"
                  :type="field.type === 'number' ? 'number' : 'text'"
                />
                <Input
                  v-else-if="field.type === 'password'"
                  v-model="sourceValues[currentSource.id][field.key]"
                  type="password"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 3-7: 普通设置项（纯图形化表单，彻底无底部网盘硬塞） -->
    <div v-else class="space-y-4">
      <section class="rounded-2xl border border-border/60 bg-surface/40 p-6 sm:p-7 space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-4">
          <div>
            <h3 class="text-base font-semibold text-fg">
              {{ tabs.find((x) => x.value === activeTab)?.label }}
            </h3>
            <p class="mt-0.5 text-xs text-muted">{{ sectionDesc[activeTab] }}</p>
          </div>
          <div class="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              class="text-xs text-muted hover:text-fg"
              @click="showRawJson = !showRawJson"
            >
              <component :is="showRawJson ? Sliders : Code2" class="mr-1.5 h-3.5 w-3.5" />
              {{ showRawJson ? '切回普通模式' : '代码编辑模式' }}
            </Button>
            <Button size="sm" @click="save">保存当前设置</Button>
          </div>
        </div>

        <div v-if="showRawJson" class="space-y-3">
          <textarea
            v-model="rawJson"
            rows="10"
            spellcheck="false"
            class="w-full rounded-xl border border-border bg-bg/90 p-4 font-mono text-xs leading-5 text-fg focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
          />
        </div>

        <div v-else class="space-y-5">
          <!-- 追剧规则 -->
          <template v-if="activeTab === 'baseline'">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-4">
              <div>
                <label class="text-sm font-medium text-fg">检查最近多少天的更新</label>
                <p class="text-xs text-muted mt-0.5">当剧集播出后，系统会在多少天内持续搜寻和补全新集数</p>
              </div>
              <div class="w-full sm:w-48 flex items-center gap-2">
                <Input v-model.number="form.window_days" type="number" min="1" max="365" />
                <span class="text-xs text-muted shrink-0">天</span>
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-4">
              <div>
                <label class="text-sm font-medium text-fg">影视标题与简介语言</label>
                <p class="text-xs text-muted mt-0.5">自动获取剧集介绍与季集标题时的首选语言</p>
              </div>
              <div class="w-full sm:w-48">
                <Select
                  v-model="form.language"
                  :options="[
                    { value: 'zh-CN', label: '简体中文 (zh-CN)' },
                    { value: 'en-US', label: 'English (en-US)' },
                  ]"
                />
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-4">
              <div>
                <label class="text-sm font-medium text-fg">自动检查更新频率</label>
                <p class="text-xs text-muted mt-0.5">后台自动轮询追剧清单与排队任务的间隔秒数</p>
              </div>
              <div class="w-full sm:w-48 flex items-center gap-2">
                <Input v-model.number="form.scan_interval_seconds" type="number" min="5" max="3600" />
                <span class="text-xs text-muted shrink-0">秒</span>
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <label class="text-sm font-medium text-fg">TMDB API 密钥 (选填)</label>
                <p class="text-xs text-muted mt-0.5">用于获取官方影视海报墙、剧情简介与热播榜单（留空则使用系统预设）</p>
              </div>
              <div class="w-full sm:w-64">
                <Input v-model="form.tmdb_api_key" type="password" placeholder="留空默认使用系统自带密钥" />
              </div>
            </div>
          </template>

          <!-- 网盘转存 -->
          <template v-if="activeTab === 'transfer'">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-4">
              <div>
                <label class="text-sm font-medium text-fg">首选转存网盘</label>
                <p class="text-xs text-muted mt-0.5">当自动搜寻到资源时，默认转存到哪个网盘账号</p>
              </div>
              <div class="w-full sm:w-48">
                <Select
                  v-model="form.default_drive"
                  :options="[
                    { value: 'quark', label: '夸克网盘' },
                    { value: '115', label: '115 网盘' },
                  ]"
                />
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-4">
              <div>
                <label class="text-sm font-medium text-fg">网盘转存保存目录</label>
                <p class="text-xs text-muted mt-0.5">存入网盘时的根文件夹名称</p>
              </div>
              <div class="w-full sm:w-64 flex gap-2">
                <Input v-model="form.transfer_root" placeholder="例如 CSX" />
                <Button
                  v-if="accounts.length"
                  variant="outline"
                  size="sm"
                  class="shrink-0"
                  @click="dirTargetField = 'transfer'; dirDialogOpen = true"
                >
                  浏览
                </Button>
              </div>
            </div>

            <div class="flex items-center justify-between gap-3 border-b border-border/40 pb-4">
              <div>
                <span class="text-sm font-medium text-fg">允许自动画质升级（洗版）</span>
                <p class="text-xs text-muted mt-0.5">如果后续搜到了更高清的版本，自动替换当前低清文件</p>
              </div>
              <Switch v-model="form.upgrade_enabled" label="允许洗版升级" />
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <label class="text-sm font-medium text-fg">最低接受画质</label>
                <p class="text-xs text-muted mt-0.5">低于此画质的资源将自动被忽略，不进行转存</p>
              </div>
              <div class="w-full sm:w-48">
                <Select
                  v-model="form.min_quality"
                  :options="[
                    { value: 'sd', label: '标清 720p 及以上' },
                    { value: 'hd', label: '高清 1080p 及以上 (推荐)' },
                    { value: '4k', label: '仅限 4K 超高清' },
                  ]"
                />
              </div>
            </div>
          </template>

          <!-- 直链播放 -->
          <template v-if="activeTab === 'strm'">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-4">
              <div>
                <label class="text-sm font-medium text-fg">STRM 播放模式</label>
                <p class="text-xs text-muted mt-0.5">Emby、Jellyfin 或播放器读取网盘视频的方式</p>
              </div>
              <div class="w-full sm:w-64">
                <Select
                  v-model="form.strm_mode"
                  :options="[
                    { value: 'local_mount', label: '本地挂载模式 (CloudDrive / Alist)' },
                    { value: 'direct', label: '网盘官方直链模式' },
                    { value: 'template', label: '自定义直链代理模板' },
                  ]"
                />
              </div>
            </div>

            <div v-if="form.strm_mode === 'local_mount'" class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <label class="text-sm font-medium text-fg">本地挂载根路径</label>
                <p class="text-xs text-muted mt-0.5">网盘通过工具挂载到服务器本地的文件目录路径</p>
              </div>
              <div class="w-full sm:w-64 flex gap-2">
                <Input v-model="form.local_mount_root" placeholder="例如 /mnt/quark" />
                <Button
                  v-if="accounts.length"
                  variant="outline"
                  size="sm"
                  class="shrink-0"
                  @click="dirTargetField = 'mount'; dirDialogOpen = true"
                >
                  浏览
                </Button>
              </div>
            </div>
          </template>

          <!-- 消息通知 -->
          <template v-if="activeTab === 'notify'">
            <div class="rounded-xl border border-border/60 bg-surface-2/30 p-4 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <strong class="text-sm text-fg">飞书群机器人通知</strong>
                  <p class="text-xs text-muted">在飞书群添加自定义机器人，接收转存和更新卡片</p>
                </div>
                <Switch v-model="form.feishu_enabled" label="启用飞书通知" />
              </div>
              <div v-if="form.feishu_enabled" class="pt-2">
                <label class="text-xs text-muted">Webhook 地址</label>
                <Input v-model="form.feishu_url" class="mt-1" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
              </div>
            </div>

            <div class="rounded-xl border border-border/60 bg-surface-2/30 p-4 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <strong class="text-sm text-fg">Telegram 机器人通知</strong>
                  <p class="text-xs text-muted">通过 Telegram Bot 向你私聊或频道推送更新</p>
                </div>
                <Switch v-model="form.telegram_enabled" label="启用 Telegram 通知" />
              </div>
              <div v-if="form.telegram_enabled" class="grid sm:grid-cols-2 gap-3 pt-2">
                <div>
                  <label class="text-xs text-muted">Bot Token</label>
                  <Input v-model="form.telegram_token" class="mt-1" type="password" placeholder="123456:ABC-DEF..." />
                </div>
                <div>
                  <label class="text-xs text-muted">Chat ID</label>
                  <Input v-model="form.telegram_chat_id" class="mt-1" placeholder="例如 -10012345678" />
                </div>
              </div>
            </div>
          </template>

          <!-- 高级设置 -->
          <template v-if="activeTab === 'advanced'">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-4">
              <div>
                <label class="text-sm font-medium text-fg">系统运行日志级别</label>
                <p class="text-xs text-muted mt-0.5">控制后台服务输出日志的详细程度</p>
              </div>
              <div class="w-full sm:w-48">
                <Select
                  v-model="form.log_level"
                  :options="[
                    { value: 'INFO', label: '正常记录 (INFO)' },
                    { value: 'DEBUG', label: '详细调试 (DEBUG)' },
                    { value: 'WARNING', label: '仅记录警告与错误' },
                  ]"
                />
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <label class="text-sm font-medium text-fg">转存并发任务上限</label>
                <p class="text-xs text-muted mt-0.5">同时进行的网盘转存与整理任务的最大线程数（默认 8）</p>
              </div>
              <div class="w-full sm:w-48 flex items-center gap-2">
                <Input v-model.number="form.max_workers" type="number" min="1" max="32" />
                <span class="text-xs text-muted shrink-0">并发</span>
              </div>
            </div>
          </template>
        </div>
      </section>
    </div>

    <!-- 扫码绑定网盘 Dialog -->
    <Dialog :open="qrOpen" title="扫码绑定网盘" @close="closeQrcode">
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <label class="block space-y-1 text-xs">
            <span class="text-muted">网盘类型</span>
            <Select
              v-model="qrProvider"
              :options="[
                { value: '115', label: '115 网盘' },
                { value: 'quark', label: '夸克网盘' },
              ]"
              @update:model-value="startQrcode"
            />
          </label>
          <label class="block space-y-1 text-xs">
            <span class="text-muted">账号备注</span>
            <Input v-model="qrName" placeholder="例如：我的主号" />
          </label>
        </div>

        <div class="flex flex-col items-center justify-center rounded-2xl border border-border/70 bg-surface-2/30 p-6">
          <div v-if="qrData?.qrcode" class="space-y-3 text-center">
            <div class="p-3 bg-white rounded-xl inline-block shadow-md">
              <img :src="qrData.qrcode" class="h-48 w-48 object-contain" />
            </div>
            <div class="space-y-1">
              <Badge :tone="qrStatus === 'scanned' ? 'good' : qrStatus === 'expired' ? 'bad' : 'warn'">
                {{ qrStatus === 'scanned' ? '已扫码，等待确认' : qrStatus === 'expired' ? '已失效' : '等待扫码' }}
              </Badge>
              <p class="text-xs text-muted mt-1">{{ qrData.hint }}</p>
            </div>
          </div>
          <div v-else-if="qrStarting" class="py-12 text-center text-xs text-muted space-y-2">
            <RefreshCw class="mx-auto h-6 w-6 animate-spin text-primary" />
            <p>{{ qrMessage }}</p>
          </div>
          <div v-else class="py-12 text-center text-xs text-status-missing">
            <p>{{ qrMessage }}</p>
            <Button variant="outline" size="sm" class="mt-3" @click="startQrcode">重新生成</Button>
          </div>
        </div>

        <Button
          v-if="qrStatus === 'expired'"
          class="w-full"
          @click="startQrcode"
        >
          重新生成二维码
        </Button>
      </div>
    </Dialog>

    <!-- 目录树弹窗 -->
    <DirectorySelectDialog
      :open="dirDialogOpen"
      :accounts="accounts"
      :account-id="accounts[0]?.id"
      @close="dirDialogOpen = false"
      @select="(path) => {
        if (dirTargetField === 'transfer') form.transfer_root = path;
        else form.local_mount_root = path;
        dirDialogOpen = false;
      }"
    />
  </div>
</template>
