<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Bell,
  Check,
  ChevronDown,
  ChevronRight,
  Clapperboard,
  Cloud,
  Cpu,
  Film,
  Flame,
  FolderOpen,
  FolderSync,
  HardDrive,
  Layers,
  PlaySquare,
  Plus,
  QrCode,
  Radio,
  RefreshCw,
  Search,
  Send,
  Sliders,
  Sparkles,
  Trash2,
  Tv,
  Workflow,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DirectorySelectDialog from '@/components/dialogs/DirectorySelectDialog.vue'
import AccountCard from '@/components/config/AccountCard.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useToast } from '@/composables/useToast'
import {
  accountsApi,
  searchSourcesApi,
  settingsApi,
  type Account,
  type QrcodeCheckResponse,
  type QrcodeStartResponse,
  type SearchSourceSchema,
  type SearchSourceTest,
} from '@/lib/api'

const navItems = [
  { value: 'accounts', label: '网盘账号' },
  { value: 'drama', label: '追剧与规则' },
  { value: 'charts', label: '榜单自动订阅' },
  { value: 'sources', label: '搜源站点 (15)' },
  { value: 'playback', label: '播放与整理' },
  { value: 'system', label: '通知与高级' },
]

const currentNav = ref('accounts')
const { toast } = useToast()

const accounts = ref<Account[]>([])
const loading = ref(false)
const saving = ref(false)

// 网盘新增输入框状态
const newAccountProvider = ref<'115' | 'quark'>('115')
const newAccountName = ref('')
const newAccountCookie = ref('')
const addingAccount = ref(false)

// 高级参数折叠状态
const showAdvDrama = ref(false)

// 榜单子 Tab
const chartTab = ref<'global' | 'douban' | 'tmdb' | 'bangumi' | 'mikan'>('global')

// 15 个搜索源自描述状态
const sourceSchemas = ref<SearchSourceSchema[]>([])
const sourceValues = ref<Record<string, Record<string, any>>>({})
const selectedSourceId = ref('pansou')
const sourceTest = ref<SearchSourceTest | null>(null)
const sourceTestRunning = ref(false)

// 表单全量响应式字段
const f = ref<Record<string, any>>({
  // 追剧与规则
  enabled: true,
  title_subscribe_enabled: true,
  subscribe_all_missing_seasons: false,
  subscribe_skip_season_zero: true,
  subscribe_season_limit: 0,
  window_days: 14,
  language: 'zh-CN',
  tmdb_api_key: '',

  // 榜单自动订阅 (对齐原 CS 插件)
  auto_subscribe_enabled: true,
  auto_subscribe_cron: '0 8,20 * * *',
  auto_subscribe_notify: true,
  auto_subscribe_min_vote: 7.0,
  auto_subscribe_min_year: 2024,
  // 豆瓣
  auto_subscribe_douban_enabled: true,
  auto_subscribe_douban_min_vote: 7.5,
  auto_subscribe_douban_top250: false,
  auto_subscribe_douban_hot: true,
  // TMDB
  auto_subscribe_tmdb_enabled: true,
  auto_subscribe_tmdb_min_vote: 7.0,
  auto_subscribe_tmdb_trending: true,
  // Bangumi
  auto_subscribe_bangumi_enabled: true,
  auto_subscribe_bangumi_min_vote: 7.0,
  // Mikan
  auto_subscribe_mikan_enabled: true,

  // 网盘转存与画质
  default_drive: 'quark',
  transfer_root: 'CSX',
  type_folder_enabled: false,
  type_folder_movie: '电影',
  type_folder_tv: '电视剧',
  enable_cloud_upgrade: true,
  enable_pt_upgrade: false,
  min_quality: 'hd',
  min_episode_size_mb: 100,
  cross_transfer_enabled: true,
  cross_transfer_threads: 3,
  cross_transfer_direct_stream: false,

  // 播放与媒体整理
  strm_generate_enabled: true,
  strm_mode: 'direct_302',
  strm_root: '/strm',
  local_mount_root: '/mnt/quark',
  strm_increment_enabled: false,
  emby_url: '',
  emby_api_key: '',
  emby_refresh_enabled: true,
  organize_source_path: '/CSX/_inbox',
  organize_include_subtitles: true,
  organize_conflict_policy: 'largest',

  // 通知与高级
  feishu_enabled: false,
  feishu_url: '',
  telegram_enabled: false,
  telegram_token: '',
  telegram_chat_id: '',
  checkin_cron: '30 0 * * *',
  checkin_auto_retry: true,
  p115_checkin_mode: 'normal',
  tg_monitor_enabled: false,
  tg_channels: '@Quark_Share_Group\n@share115',
  tg_auto_transfer: true,
  log_level: 'INFO',
  max_workers: 8,
})

// 扫码弹窗
const qrOpen = ref(false)
const qrProvider = ref<'115' | 'quark'>('115')
const qrName = ref('我的115账号')
const qrData = ref<QrcodeStartResponse | null>(null)
const qrStatus = ref<'idle' | 'starting' | 'waiting' | 'scanned' | 'success' | 'expired' | 'error'>('idle')
const qrMessage = ref('')
const qrStarting = ref(false)
let qrPollTimer = 0
let qrCheckInFlight = false
let qrGeneration = 0

// 目录树选择
const dirDialogOpen = ref(false)
const dirTarget = ref('transfer_root')

async function loadAccounts() {
  try {
    accounts.value = await accountsApi.list()
  } catch {}
}

async function handleAddAccountByCookie() {
  if (!newAccountCookie.value.trim()) {
    toast('请输入网盘 Cookie 或凭据', 'info')
    return
  }
  addingAccount.value = true
  try {
    const finalName = newAccountName.value.trim() || `${newAccountProvider.value === '115' ? '115' : '夸克'}账号`
    await accountsApi.create({
      provider: newAccountProvider.value,
      name: finalName,
      credential: newAccountCookie.value.trim(),
    })
    toast('网盘账号添加成功！', 'success')
    newAccountCookie.value = ''
    newAccountName.value = ''
    await loadAccounts()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '添加失败', 'error')
  } finally {
    addingAccount.value = false
  }
}

async function loadSources() {
  try {
    const schemas = await searchSourcesApi.schema()
    sourceSchemas.value = schemas
    const values: Record<string, Record<string, any>> = {}
    for (const schema of schemas) {
      const current: Record<string, any> = { enabled: schema.enabled ?? true }
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
  } catch {}
}

async function loadAllSettings() {
  loading.value = true
  try {
    const [b, t, s, n, a] = await Promise.all([
      settingsApi.getSection('baseline'),
      settingsApi.getSection('transfer'),
      settingsApi.getSection('strm'),
      settingsApi.getSection('notify'),
      settingsApi.getSection('advanced'),
    ])
    Object.assign(f.value, b, t, s, n, a)
  } catch (cause) {
    console.error(cause)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadAccounts()
  void loadAllSettings()
  void loadSources()
})

async function saveAll() {
  saving.value = true
  try {
    if (currentNav.value === 'sources') {
      await searchSourcesApi.save(sourceValues.value)
      toast('全网 15 搜索源设置已保存', 'success')
      return
    }

    const pBaseline = {
      enabled: f.value.enabled,
      title_subscribe_enabled: f.value.title_subscribe_enabled,
      subscribe_all_missing_seasons: f.value.subscribe_all_missing_seasons,
      subscribe_skip_season_zero: f.value.subscribe_skip_season_zero,
      subscribe_season_limit: Number(f.value.subscribe_season_limit),
      window_days: Number(f.value.window_days),
      language: f.value.language,
      auto_subscribe_enabled: f.value.auto_subscribe_enabled,
      auto_subscribe_min_vote: Number(f.value.auto_subscribe_min_vote),
      auto_subscribe_min_year: Number(f.value.auto_subscribe_min_year),
      tmdb_api_key: f.value.tmdb_api_key,
    }

    const pTransfer = {
      default_drive: f.value.default_drive,
      transfer_root: f.value.transfer_root,
      type_folder_enabled: f.value.type_folder_enabled,
      type_folder_movie: f.value.type_folder_movie,
      type_folder_tv: f.value.type_folder_tv,
      enable_cloud_upgrade: f.value.enable_cloud_upgrade,
      enable_pt_upgrade: f.value.enable_pt_upgrade,
      min_quality: f.value.min_quality,
      min_episode_size_mb: Number(f.value.min_episode_size_mb),
      cross_transfer_enabled: f.value.cross_transfer_enabled,
      cross_transfer_threads: Number(f.value.cross_transfer_threads),
      cross_transfer_direct_stream: f.value.cross_transfer_direct_stream,
      organize_source_path: f.value.organize_source_path,
      organize_include_subtitles: f.value.organize_include_subtitles,
      organize_conflict_policy: f.value.organize_conflict_policy,
    }

    const pStrm = {
      strm_generate_enabled: f.value.strm_generate_enabled,
      mode: f.value.strm_mode,
      strm_root: f.value.strm_root,
      local_mount_root: f.value.local_mount_root,
      strm_increment_enabled: f.value.strm_increment_enabled,
      emby_url: f.value.emby_url,
      emby_api_key: f.value.emby_api_key,
      emby_refresh_enabled: f.value.emby_refresh_enabled,
    }

    const pNotify = {
      channels: {
        feishu: { enabled: f.value.feishu_enabled, webhook_url: f.value.feishu_url },
        telegram: { enabled: f.value.telegram_enabled, bot_token: f.value.telegram_token, chat_id: f.value.telegram_chat_id },
      },
    }

    const pAdv = {
      log_level: f.value.log_level,
      max_workers: Number(f.value.max_workers),
      checkin_cron: f.value.checkin_cron,
      checkin_auto_retry: f.value.checkin_auto_retry,
      p115_checkin_mode: f.value.p115_checkin_mode,
      tg_monitor_enabled: f.value.tg_monitor_enabled,
      tg_channels: f.value.tg_channels,
      tg_auto_transfer: f.value.tg_auto_transfer,
    }

    await Promise.all([
      settingsApi.updateSection('baseline', pBaseline),
      settingsApi.updateSection('transfer', pTransfer),
      settingsApi.updateSection('strm', pStrm),
      settingsApi.updateSection('notify', pNotify),
      settingsApi.updateSection('advanced', pAdv),
    ])

    toast('设置保存成功', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 扫码绑定
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
    qrMessage.value =
      result.status === 'waiting'
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
  } catch {
    if (generation !== qrGeneration) return
    qrMessage.value = '检测重试中…'
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
  qrMessage.value = '正在生成二维码…'
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

function openScanDialog(provider: '115' | 'quark' = '115') {
  qrProvider.value = provider
  qrName.value = `我的${provider === '115' ? '115' : '夸克'}账号`
  qrOpen.value = true
  void startQrcode()
}

async function toggleAccountEnabled(account: Account) {
  try {
    await accountsApi.update(account.id, { is_enabled: !account.is_enabled })
    account.is_enabled = !account.is_enabled
    toast(account.is_enabled ? '已启用该账号' : '已暂停该账号', 'info')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '更新状态失败', 'error')
  }
}

async function setAccountPrimary(account: Account) {
  if (account.is_primary) return
  try {
    await accountsApi.update(account.id, { is_primary: true })
    for (const a of accounts.value) {
      if (a.provider === account.provider) {
        a.is_primary = (a.id === account.id)
      }
    }
    toast(`已将 ${account.name} 设为默认${account.provider === '115' ? '115' : '夸克'}主号`, 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '设置主号失败', 'error')
  }
}

async function removeAccount(id: number) {
  await accountsApi.delete(id)
  await loadAccounts()
  toast('账号已解绑', 'info')
}

const accountRefreshing = ref<Record<number, boolean>>({})

async function testAccount(id: number) {
  accountRefreshing.value[id] = true
  try {
    const res = await accountsApi.test(id)
    toast(`${res.provider}网盘：${res.message}`, res.valid ? 'success' : 'error')
    if (res.info) {
      const target = accounts.value.find((a) => a.id === id)
      if (target) target.info = res.info
    }
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '检测失败', 'error')
  } finally {
    accountRefreshing.value[id] = false
  }
}

// 搜索源单源测试
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
      message: cause instanceof Error ? cause.message : '测试失败',
    }
  } finally {
    sourceTestRunning.value = false
  }
}

const currentSource = computed(() => sourceSchemas.value.find((s) => s.id === selectedSourceId.value))
</script>

<template>
  <div class="space-y-6 max-w-6xl">
    <!-- 顶部极简标题与全局操作 -->
    <header class="flex items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
      <div>
        <h2 class="text-xl font-bold tracking-tight text-white">系统设置</h2>
        <p class="text-xs text-zinc-400 mt-0.5">调控自动化追更、网盘转存、搜源站点与播放参数</p>
      </div>

      <div class="flex items-center gap-2.5">
        <Button size="sm" class="apple-btn-primary px-4 font-medium" :disabled="saving" @click="saveAll">
          {{ saving ? '保存中…' : '保存设置' }}
        </Button>
      </div>
    </header>

    <!-- 紧凑药丸分类导航 -->
    <Tabs v-model="currentNav" :items="navItems" />

    <!-- 1. 网盘账号 (既能输入 Cookie 也能扫码) -->
    <div v-if="currentNav === 'accounts'" class="space-y-5">
      <!-- 新增网盘账号卡片：输入框集成扫码 Icon -->
      <div class="apple-glass rounded-2xl p-5 space-y-4">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Cloud class="h-4 w-4 text-blue-400" />
            <h3 class="text-sm font-semibold text-white">添加网盘账号</h3>
          </div>
          <span class="text-[11px] text-zinc-400">支持直接粘贴 Cookie，或点击右侧扫码图标手机扫码免密登录</span>
        </div>

        <div class="grid gap-3 sm:grid-cols-12 items-center">
          <div class="sm:col-span-3">
            <Select
              v-model="newAccountProvider"
              :options="[
                { value: '115', label: '115 网盘' },
                { value: 'quark', label: '夸克网盘' },
              ]"
            />
          </div>

          <div class="sm:col-span-3">
            <Input v-model="newAccountName" placeholder="账号备注 (如: 我的主号)" />
          </div>

          <!-- 核心：输入框内置扫码图标 -->
          <div class="sm:col-span-4 relative flex items-center">
            <input
              v-model="newAccountCookie"
              type="password"
              placeholder="粘贴 Cookie / Token 凭据"
              class="w-full h-9 rounded-xl border border-white/10 bg-zinc-900/60 pl-3 pr-10 text-xs text-white placeholder-zinc-500 outline-none focus:border-white/20 transition-colors"
            />
            <button
              type="button"
              class="absolute right-1.5 p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
              title="手机扫码快速登录"
              @click="openScanDialog(newAccountProvider)"
            >
              <QrCode class="h-4 w-4 text-blue-400" />
            </button>
          </div>

          <div class="sm:col-span-2">
            <Button
              size="sm"
              class="apple-btn-primary w-full h-9 text-xs"
              :disabled="addingAccount"
              @click="handleAddAccountByCookie"
            >
              {{ addingAccount ? '添加中…' : '添加网盘' }}
            </Button>
          </div>
        </div>
      </div>

      <!-- 已绑定网盘列表 -->
      <div class="space-y-3">
        <h4 class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">已连接的网盘</h4>

        <div v-if="!accounts.length" class="apple-glass rounded-2xl p-12 text-center space-y-2">
          <HardDrive class="mx-auto h-7 w-7 text-zinc-600" />
          <p class="text-sm font-semibold text-white">尚未绑定任何网盘</p>
          <p class="text-xs text-zinc-500">在上方粘贴 Cookie 或点击右侧扫码图标，即可绑定你的 115 或夸克网盘。</p>
        </div>

        <div v-else class="grid gap-4 sm:grid-cols-2">
          <AccountCard
            v-for="acc in accounts"
            :key="acc.id"
            :account="acc"
            :loading="Boolean(accountRefreshing[acc.id])"
            @refresh="testAccount"
            @remove="removeAccount"
            @toggle="toggleAccountEnabled"
            @set-primary="setAccountPrimary"
          />
        </div>
      </div>
    </div>

    <!-- 2. 追剧与规则 (紧凑卡片网格 Bento Grid) -->
    <div v-else-if="currentNav === 'drama'" class="space-y-5">
      <div class="grid gap-4 md:grid-cols-2">
        <!-- 卡片 A: 自动化追剧 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <Tv class="h-4 w-4 text-blue-400" />
            <h3 class="text-sm font-semibold text-white">自动追更调度</h3>
          </div>

          <div class="space-y-3.5 text-xs">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">自动化总开关</p>
                <p class="text-[11px] text-zinc-500">开启后定时轮询全网抓取追更</p>
              </div>
              <Switch v-model="f.enabled" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">片名智能订阅</p>
                <p class="text-[11px] text-zinc-500">频道抓取新剧自动加入追剧单</p>
              </div>
              <Switch v-model="f.title_subscribe_enabled" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">缺集全季补齐</p>
                <p class="text-[11px] text-zinc-500">追新集时同时回溯补全前面漏下的所有集</p>
              </div>
              <Switch v-model="f.subscribe_all_missing_seasons" />
            </div>
          </div>
        </div>

        <!-- 卡片 B: 转存与画质门槛 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <Clapperboard class="h-4 w-4 text-indigo-400" />
            <h3 class="text-sm font-semibold text-white">网盘转存与洗版</h3>
          </div>

          <div class="space-y-3.5 text-xs">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">首选转存网盘</p>
                <p class="text-[11px] text-zinc-500">多源并存时优先存入此网盘</p>
              </div>
              <div class="w-36">
                <Select
                  v-model="f.default_drive"
                  :options="[
                    { value: 'quark', label: '夸克网盘' },
                    { value: '115', label: '115 网盘' },
                  ]"
                />
              </div>
            </div>

            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">最低画质门槛</p>
                <p class="text-[11px] text-zinc-500">低于此规格资源直接忽略</p>
              </div>
              <div class="w-36">
                <Select
                  v-model="f.min_quality"
                  :options="[
                    { value: 'sd', label: '720p 标清' },
                    { value: 'hd', label: '1080p 高清' },
                    { value: '4k', label: '4K 超高清' },
                  ]"
                />
              </div>
            </div>

            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">画质自动洗版</p>
                <p class="text-[11px] text-zinc-500">搜寻到更高画质时自动替换旧版</p>
              </div>
              <Switch v-model="f.enable_cloud_upgrade" />
            </div>
          </div>
        </div>
      </div>

      <!-- 存储路径卡片 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
          <FolderOpen class="h-4 w-4 text-emerald-400" />
          <h3 class="text-sm font-semibold text-white">网盘存储位置与分层</h3>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="space-y-1.5">
            <label class="font-medium text-white">网盘保存根目录</label>
            <div class="flex gap-2">
              <Input v-model="f.transfer_root" placeholder="例如 CSX" />
              <Button
                v-if="accounts.length"
                variant="outline"
                size="sm"
                class="shrink-0 text-xs"
                @click="dirTarget = 'transfer_root'; dirDialogOpen = true"
              >
                浏览
              </Button>
            </div>
          </div>

          <div class="flex items-center justify-between rounded-xl bg-zinc-900/50 p-3 border border-white/[0.06] mt-auto">
            <div>
              <p class="font-medium text-white">按媒体类型分层</p>
              <p class="text-[11px] text-zinc-500">自动建「电影/电视剧」一级子目录</p>
            </div>
            <Switch v-model="f.type_folder_enabled" />
          </div>
        </div>
      </div>

      <!-- 进阶高级参数折叠区 -->
      <div class="rounded-2xl border border-white/[0.08] bg-zinc-950/40 overflow-hidden">
        <button
          type="button"
          class="flex w-full items-center justify-between p-4 text-left text-xs font-medium text-zinc-400 hover:text-white transition-colors cursor-pointer"
          @click="showAdvDrama = !showAdvDrama"
        >
          <span class="flex items-center gap-2">
            <Sliders class="h-3.5 w-3.5" />
            <span>进阶追剧与中继参数（跨盘搬运、防假种、TMDB 密钥）</span>
          </span>
          <ChevronDown class="h-4 w-4 transition-transform" :class="showAdvDrama ? 'rotate-180' : ''" />
        </button>

        <div v-if="showAdvDrama" class="p-5 border-t border-white/[0.06] space-y-4 text-xs">
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <label class="text-zinc-300">防假种体积门槛 (MB)</label>
              <Input v-model.number="f.min_episode_size_mb" type="number" min="10" />
            </div>
            <div class="space-y-1.5">
              <label class="text-zinc-300">更新搜索窗口 (天)</label>
              <Input v-model.number="f.window_days" type="number" min="1" />
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-2 pt-2 border-t border-white/[0.04]">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">跳过特别篇 (S00)</p>
                <p class="text-[11px] text-zinc-500">不抓取预告、花絮与采访</p>
              </div>
              <Switch v-model="f.subscribe_skip_season_zero" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">跨盘直传搬运</p>
                <p class="text-[11px] text-zinc-500">夸克与 115 间直接流式中继</p>
              </div>
              <Switch v-model="f.cross_transfer_enabled" />
            </div>
          </div>

          <div class="space-y-1.5 pt-2">
            <label class="text-zinc-300">TMDB API 密钥 (用于补齐官方高清海报与演职员，留空使用内置密钥)</label>
            <Input v-model="f.tmdb_api_key" type="password" placeholder="留空使用系统预设密钥" />
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 榜单自动订阅 (移入原 CS 插件榜单订阅能力) -->
    <div v-else-if="currentNav === 'charts'" class="space-y-5">
      <div class="apple-glass rounded-2xl p-5 space-y-4">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Flame class="h-4 w-4 text-orange-400" />
            <h3 class="text-sm font-semibold text-white">全网榜单自动订阅</h3>
          </div>
          <Switch v-model="f.auto_subscribe_enabled" />
        </div>

        <p class="text-xs text-zinc-400">
          每日定时扫描全网各大流行榜单（豆瓣高分/热门、TMDB 流行剧集、Bangumi 番剧周更与 Mikan 番组），命中高分作品自动建档追更并全网搜源。
        </p>

        <!-- 榜单平台水平小标签 -->
        <div class="flex items-center gap-2 border-b border-white/[0.06] pb-2 text-xs">
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'global' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white'"
            @click="chartTab = 'global'"
          >
            全局调度
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'douban' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white'"
            @click="chartTab = 'douban'"
          >
            豆瓣
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'tmdb' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white'"
            @click="chartTab = 'tmdb'"
          >
            TMDB
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'bangumi' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white'"
            @click="chartTab = 'bangumi'"
          >
            Bangumi 番组
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'mikan' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white'"
            @click="chartTab = 'mikan'"
          >
            Mikan 蜜柑
          </button>
        </div>

        <!-- 榜单各选项卡配置 -->
        <div v-if="chartTab === 'global'" class="grid gap-4 sm:grid-cols-2 text-xs pt-2">
          <div class="space-y-1.5">
            <label class="font-medium text-white">榜单抓取周期 Cron</label>
            <Input v-model="f.auto_subscribe_cron" placeholder="0 8,20 * * *" />
          </div>

          <div class="space-y-1.5">
            <label class="font-medium text-white">榜单自动订阅最低评分</label>
            <Input v-model.number="f.auto_subscribe_min_vote" type="number" step="0.1" min="0" max="10" />
          </div>

          <div class="space-y-1.5">
            <label class="font-medium text-white">影视上映年份门槛</label>
            <Input v-model.number="f.auto_subscribe_min_year" type="number" min="2000" />
          </div>

          <div class="flex items-center justify-between rounded-xl bg-zinc-900/50 p-3 border border-white/[0.06] mt-auto">
            <div>
              <p class="font-medium text-white">榜单抓取结果通知</p>
              <p class="text-[11px] text-zinc-500">发现新高分影视建档后推送到通知渠道</p>
            </div>
            <Switch v-model="f.auto_subscribe_notify" />
          </div>
        </div>

        <div v-else-if="chartTab === 'douban'" class="space-y-3.5 text-xs pt-2">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-white">启用豆瓣榜单自动订阅</p>
              <p class="text-[11px] text-zinc-500">定时抓取豆瓣电影热门榜、一周口碑榜与高分榜</p>
            </div>
            <Switch v-model="f.auto_subscribe_douban_enabled" />
          </div>

          <div class="grid gap-3 sm:grid-cols-2 pt-2 border-t border-white/[0.06]">
            <div class="space-y-1.5">
              <label class="font-medium text-white">豆瓣最低评分过滤</label>
              <Input v-model.number="f.auto_subscribe_douban_min_vote" type="number" step="0.1" />
            </div>

            <div class="flex items-center justify-between rounded-xl bg-zinc-900/50 p-3 border border-white/[0.06]">
              <div>
                <p class="font-medium text-white">豆瓣实时热门影视</p>
                <p class="text-[11px] text-zinc-500">跟踪最新上映爆款热播剧集</p>
              </div>
              <Switch v-model="f.auto_subscribe_douban_hot" />
            </div>
          </div>
        </div>

        <div v-else-if="chartTab === 'tmdb'" class="space-y-3.5 text-xs pt-2">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-white">启用 TMDB 全球趋势榜单</p>
              <p class="text-[11px] text-zinc-500">同步全球流媒体平台（Netflix、HBO、Disney+）今日热度榜</p>
            </div>
            <Switch v-model="f.auto_subscribe_tmdb_enabled" />
          </div>

          <div class="space-y-1.5 pt-2 border-t border-white/[0.06]">
            <label class="font-medium text-white">TMDB 最低大众评分</label>
            <Input v-model.number="f.auto_subscribe_tmdb_min_vote" type="number" step="0.1" />
          </div>
        </div>

        <div v-else-if="chartTab === 'bangumi'" class="space-y-3.5 text-xs pt-2">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-white">启用 Bangumi 每日放送番组榜单</p>
              <p class="text-[11px] text-zinc-500">自动同步二次元新番排期表与高分新季动画</p>
            </div>
            <Switch v-model="f.auto_subscribe_bangumi_enabled" />
          </div>

          <div class="space-y-1.5 pt-2 border-t border-white/[0.06]">
            <label class="font-medium text-white">Bangumi 评分过滤门槛</label>
            <Input v-model.number="f.auto_subscribe_bangumi_min_vote" type="number" step="0.1" />
          </div>
        </div>

        <div v-else-if="chartTab === 'mikan'" class="space-y-3.5 text-xs pt-2">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-white">启用 Mikan 蜜柑计划当季番剧追踪</p>
              <p class="text-[11px] text-zinc-500">自动解析蜜柑日历，关联字幕组番组快速转存</p>
            </div>
            <Switch v-model="f.auto_subscribe_mikan_enabled" />
          </div>
        </div>
      </div>
    </div>

    <!-- 4. 搜源站点 (15 源：横向可滚动选项栏) -->
    <div v-else-if="currentNav === 'sources'" class="space-y-4">
      <!-- 核心改变：水平滚动单行选项导航栏 -->
      <div class="apple-glass rounded-2xl p-2.5">
        <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
          <button
            v-for="s in sourceSchemas"
            :key="s.id"
            type="button"
            class="flex items-center gap-1.5 shrink-0 px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer whitespace-nowrap"
            :class="selectedSourceId === s.id ? 'bg-white/15 text-white ring-1 ring-white/20' : 'text-zinc-400 hover:text-white hover:bg-white/[0.05]'"
            @click="selectedSourceId = s.id; sourceTest = null"
          >
            <span>{{ s.name }}</span>
            <span
              class="h-1.5 w-1.5 rounded-full"
              :class="sourceValues[s.id]?.enabled === false ? 'bg-zinc-600' : 'bg-emerald-400'"
            />
          </button>
        </div>
      </div>

      <!-- 选中源的参数配置卡片 -->
      <div v-if="currentSource" class="space-y-4">
        <div class="apple-glass rounded-2xl p-4 flex items-center justify-between gap-4">
          <div>
            <div class="flex items-center gap-2">
              <h4 class="text-sm font-semibold text-white">{{ currentSource.name }}</h4>
              <Badge tone="muted" class="text-[10px]">权重 {{ currentSource.order }}</Badge>
            </div>
            <p class="text-xs text-zinc-400 mt-0.5">自描述参数调整与在线网络测试</p>
          </div>

          <Button variant="outline" size="sm" class="h-8 text-xs shrink-0" :disabled="sourceTestRunning" @click="testSelectedSource">
            <Search class="mr-1.5 h-3.5 w-3.5" />
            <span>{{ sourceTestRunning ? '测试中…' : '测试连通性' }}</span>
          </Button>
        </div>

        <div
          v-if="sourceTest"
          class="rounded-xl border p-3 text-xs flex items-center justify-between"
          :class="sourceTest.valid ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-rose-500/30 bg-rose-500/10 text-rose-400'"
        >
          <span>{{ sourceTest.valid ? '连通正常' : '连通失败' }}：{{ sourceTest.message }}</span>
          <span class="font-mono text-[11px]">{{ sourceTest.elapsed_ms }} ms</span>
        </div>

        <div v-for="(group, gIndex) in currentSource.groups" :key="gIndex" class="apple-glass rounded-2xl p-5 space-y-4">
          <h5 class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ group.title || '参数配置' }}</h5>
          <div class="grid gap-4 sm:grid-cols-2">
            <div v-for="field in group.fields" :key="field.key" class="space-y-1.5 text-xs">
              <label class="font-medium text-white flex items-center justify-between">
                <span>{{ field.label }}</span>
                <Switch
                  v-if="field.type === 'switch'"
                  v-model="sourceValues[currentSource.id][field.key]"
                />
              </label>
              <p v-if="field.description" class="text-[11px] text-zinc-500">{{ field.description }}</p>
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

    <!-- 5. 播放与整理 (紧凑卡片网格) -->
    <div v-else-if="currentNav === 'playback'" class="space-y-5">
      <div class="grid gap-4 md:grid-cols-2">
        <!-- 卡片 A: STRM 直链播放 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <PlaySquare class="h-4 w-4 text-emerald-400" />
            <h3 class="text-sm font-semibold text-white">STRM 原画直链</h3>
          </div>

          <div class="space-y-3.5 text-xs">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">自动生成 STRM</p>
                <p class="text-[11px] text-zinc-500">转存后自动为 Emby/Jellyfin 生成播放条目</p>
              </div>
              <Switch v-model="f.strm_generate_enabled" />
            </div>

            <div class="space-y-1.5">
              <label class="font-medium text-white">播放跳转模式</label>
              <Select
                v-model="f.strm_mode"
                :options="[
                  { value: 'direct_302', label: '302 原画直链跳转 (推荐·零流量)' },
                  { value: 'local_mount', label: '本地挂载路径 (CloudDrive/Alist)' },
                ]"
              />
            </div>

            <div class="space-y-1.5">
              <label class="font-medium text-white">STRM 文件输出目录</label>
              <Input v-model="f.strm_root" placeholder="/strm" />
            </div>
          </div>
        </div>

        <!-- 卡片 B: Emby 与媒体库联动 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <Film class="h-4 w-4 text-purple-400" />
            <h3 class="text-sm font-semibold text-white">Emby / Jellyfin 联动</h3>
          </div>

          <div class="space-y-3.5 text-xs">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">入库自动刷新媒体库</p>
                <p class="text-[11px] text-zinc-500">新剧入库后触发媒体服务器自动扫描</p>
              </div>
              <Switch v-model="f.emby_refresh_enabled" />
            </div>

            <div class="space-y-1.5">
              <label class="font-medium text-white">服务器地址</label>
              <Input v-model="f.emby_url" placeholder="http://172.18.0.x:8096" />
            </div>

            <div class="space-y-1.5">
              <label class="font-medium text-white">API 密钥</label>
              <Input v-model="f.emby_api_key" type="password" placeholder="粘贴 Emby API Key" />
            </div>
          </div>
        </div>
      </div>

      <!-- 卡片 C: 全盘整理与字幕 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
          <FolderSync class="h-4 w-4 text-cyan-400" />
          <h3 class="text-sm font-semibold text-white">全盘整理规则</h3>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1.5">
            <label class="font-medium text-white">暂存区扫描目录</label>
            <div class="flex gap-2">
              <Input v-model="f.organize_source_path" placeholder="/CSX/_inbox" />
              <Button
                v-if="accounts.length"
                variant="outline"
                size="sm"
                class="shrink-0 text-xs"
                @click="dirTarget = 'organize_source_path'; dirDialogOpen = true"
              >
                浏览
              </Button>
            </div>
          </div>

          <div class="flex items-center justify-between rounded-xl bg-zinc-900/50 p-3 border border-white/[0.06] mt-auto">
            <div>
              <p class="font-medium text-white">字幕自动跟随归位</p>
              <p class="text-[11px] text-zinc-500">外挂 .srt/.ass 字幕与视频同步命名移动</p>
            </div>
            <Switch v-model="f.organize_include_subtitles" />
          </div>
        </div>
      </div>
    </div>

    <!-- 6. 通知与高级 (紧凑卡片网格) -->
    <div v-else-if="currentNav === 'system'" class="space-y-5">
      <div class="grid gap-4 md:grid-cols-2">
        <!-- 卡片 A: 消息通知渠道 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <Bell class="h-4 w-4 text-amber-400" />
            <h3 class="text-sm font-semibold text-white">消息通知推送</h3>
          </div>

          <div class="space-y-3 text-xs">
            <div class="rounded-xl border border-white/[0.06] bg-zinc-900/40 p-3 space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-medium text-white">飞书群机器人</span>
                <Switch v-model="f.feishu_enabled" />
              </div>
              <Input v-if="f.feishu_enabled" v-model="f.feishu_url" placeholder="粘贴飞书 Webhook 链接" />
            </div>

            <div class="rounded-xl border border-white/[0.06] bg-zinc-900/40 p-3 space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-medium text-white">Telegram 机器人</span>
                <Switch v-model="f.telegram_enabled" />
              </div>
              <div v-if="f.telegram_enabled" class="space-y-1.5 pt-1">
                <Input v-model="f.telegram_token" type="password" placeholder="Bot Token (123456:ABC...)" />
                <Input v-model="f.telegram_chat_id" placeholder="Chat ID (-10012345678)" />
              </div>
            </div>
          </div>
        </div>

        <!-- 卡片 B: 签到与系统参数 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <Cpu class="h-4 w-4 text-sky-400" />
            <h3 class="text-sm font-semibold text-white">自动签到与系统性能</h3>
          </div>

          <div class="space-y-3 text-xs">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-white">每日自动签到</p>
                <p class="text-[11px] text-zinc-500">每天凌晨自动为所有网盘签到领空间</p>
              </div>
              <Switch v-model="f.checkin_auto_retry" />
            </div>

            <div class="grid grid-cols-2 gap-2 pt-1">
              <div class="space-y-1">
                <label class="text-zinc-400">日志级别</label>
                <Select
                  v-model="f.log_level"
                  :options="[
                    { value: 'INFO', label: 'INFO 标准' },
                    { value: 'DEBUG', label: 'DEBUG 详细' },
                  ]"
                />
              </div>

              <div class="space-y-1">
                <label class="text-zinc-400">并发任务数</label>
                <Input v-model.number="f.max_workers" type="number" min="1" max="32" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 卡片 C: Telegram 抓链监控 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Radio class="h-4 w-4 text-blue-400" />
            <h3 class="text-sm font-semibold text-white">Telegram 频道实时抓链监控</h3>
          </div>
          <Switch v-model="f.tg_monitor_enabled" />
        </div>

        <div v-if="f.tg_monitor_enabled" class="space-y-3 pt-1">
          <div class="space-y-1">
            <label class="text-zinc-300">监控频道（每行一个）</label>
            <textarea
              v-model="f.tg_channels"
              rows="2"
              class="w-full rounded-xl border border-white/10 bg-zinc-900/60 p-2.5 font-mono text-xs text-white outline-none"
            />
          </div>

          <div class="flex items-center justify-between">
            <span class="text-zinc-400">识别到新剧后直接转存入库</span>
            <Switch v-model="f.tg_auto_transfer" />
          </div>
        </div>
      </div>
    </div>

    <!-- 扫码绑定网盘 Dialog -->
    <Dialog :open="qrOpen" :title="`手机扫码绑定 ${qrProvider === '115' ? '115' : '夸克'} 网盘`" @close="closeQrcode">
      <div class="space-y-4">
        <div class="space-y-1 text-xs">
          <span class="text-zinc-400">账号备注名称</span>
          <Input v-model="qrName" placeholder="例如：我的主号" />
        </div>

        <div class="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-zinc-900/60 p-6">
          <div v-if="qrData?.qrcode" class="space-y-3 text-center">
            <div class="p-3 bg-white rounded-2xl inline-block shadow-md">
              <img :src="qrData.qrcode" class="h-44 w-44 object-contain" />
            </div>
            <div class="space-y-1">
              <Badge :tone="qrStatus === 'scanned' ? 'good' : qrStatus === 'expired' ? 'bad' : 'warn'">
                {{ qrStatus === 'scanned' ? '已扫码，等待手机端确认' : qrStatus === 'expired' ? '已失效' : '等待手机扫码' }}
              </Badge>
              <p class="text-xs text-zinc-400 mt-1">{{ qrData.hint }}</p>
            </div>
          </div>
          <div v-else-if="qrStarting" class="py-10 text-center text-xs text-zinc-400 space-y-2">
            <RefreshCw class="mx-auto h-5 w-5 animate-spin text-white" />
            <p>{{ qrMessage }}</p>
          </div>
          <div v-else class="py-10 text-center text-xs text-rose-400">
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

    <!-- 目录树选择弹窗 -->
    <DirectorySelectDialog
      :open="dirDialogOpen"
      :accounts="accounts"
      :account-id="accounts[0]?.id"
      @close="dirDialogOpen = false"
      @select="(path) => {
        if (dirTarget === 'transfer_root') f.transfer_root = path;
        else if (dirTarget === 'organize_source_path') f.organize_source_path = path;
        else if (dirTarget === 'local_mount_root') f.local_mount_root = path;
        dirDialogOpen = false;
      }"
    />
  </div>
</template>
