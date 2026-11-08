<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Bell,
  Check,
  Clapperboard,
  Cloud,
  FolderOpen,
  FolderSync,
  HardDrive,
  PlaySquare,
  Plus,
  QrCode,
  Radio,
  RefreshCw,
  Search,
  Sliders,
  Sparkles,
  Trash2,
  Tv,
  Workflow,
  ShieldCheck,
  Send,
  Calendar,
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
  searchSourcesApi,
  settingsApi,
  type Account,
  type QrcodeCheckResponse,
  type QrcodeStartResponse,
  type SearchSourceSchema,
  type SearchSourceTest,
  type SettingSection,
} from '@/lib/api'

// 5 大聚合选项卡
const mainTabs = [
  { value: 'accounts', label: '网盘账号' },
  { value: 'automation', label: '追剧与规则' },
  { value: 'sources', label: '搜源站点 (15)' },
  { value: 'playback', label: '播放与入库' },
  { value: 'system', label: '通知与高级' },
]

const activeTab = ref('accounts')
const { toast } = useToast()

const accounts = ref<Account[]>([])
const loading = ref(false)
const saving = ref(false)

// 15 个搜索源自描述状态
const sourceSchemas = ref<SearchSourceSchema[]>([])
const sourceValues = ref<Record<string, Record<string, any>>>({})
const selectedSourceId = ref('pansou')
const sourceTest = ref<SearchSourceTest | null>(null)
const sourceTestRunning = ref(false)

// 表单全量响应式字段（原版 12 模块完整补全）
const f = ref<Record<string, any>>({
  // 1. 基础运行与订阅
  enabled: true,
  title_subscribe_enabled: true,
  subscribe_all_missing_seasons: false,
  subscribe_skip_season_zero: true,
  subscribe_season_limit: 0,
  direct_transfer_enabled: true,
  agent_enabled: true,
  auto_subscribe_enabled: true,
  window_days: 14,
  language: 'zh-CN',
  auto_subscribe_min_vote: 7.0,
  auto_subscribe_min_year: 2024,
  tmdb_api_key: '',
  // 2. 转存与中继
  default_drive: 'quark',
  cross_transfer_enabled: true,
  cross_transfer_threads: 3,
  cross_transfer_direct_stream: false,
  cross_transfer_rapid_miss_action: 'abort',
  cross_transfer_upload_concurrency: 0,
  cross_transfer_aria2_enabled: false,
  cross_transfer_aria2_connections: 48,
  cross_transfer_residue_cleanup: true,
  transfer_root: 'CSX',
  type_folder_enabled: false,
  type_folder_movie: '电影',
  type_folder_tv: '电视剧',
  // 3. 画质洗版
  enable_cloud_upgrade: true,
  enable_pt_upgrade: false,
  upgrade_mode: 'largest',
  min_quality: 'hd',
  min_episode_size_mb: 100,
  episode_dedup_enabled: true,
  verify_landed_enabled: true,
  prefer_template_named_version: true,
  // 4. 全盘整理
  organize_source_path: '/CSX/_inbox',
  organize_max_files: 100,
  organize_max_depth: 5,
  organize_include_subtitles: true,
  organize_conflict_policy: 'largest',
  organize_schedule_enabled: false,
  organize_schedule_cron: '0 4 * * *',
  organize_schedule_auto_execute: false,
  // 5. STRM 播放与媒体服务
  strm_generate_enabled: true,
  strm_mode: 'direct_302',
  strm_root: '/strm',
  strm_base_url: '',
  local_mount_root: '/mnt/quark',
  url_template: '',
  strm_increment_enabled: false,
  strm_increment_minutes: 30,
  strm_full_scan_overwrite: false,
  emby_url: '',
  emby_api_key: '',
  emby_refresh_enabled: true,
  emby_mediainfo_enabled: false,
  media_server_refresh_delay: 0,
  // 6. Telegram 监控
  tg_monitor_enabled: false,
  tg_api_id: '',
  tg_api_hash: '',
  tg_session: '',
  tg_channels: '@Quark_Share_Group\n@share115',
  tg_auto_transfer: true,
  tg_monitor_interval_minutes: 5,
  tg_monitor_keep_unmatched: false,
  // 7. 每日签到
  checkin_cron: '30 0 * * *',
  checkin_auto_retry: true,
  checkin_retry_count: 2,
  p115_checkin_mode: 'normal',
  // 8. 通知与系统高级
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
    if (activeTab.value === 'sources') {
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
      direct_transfer_enabled: f.value.direct_transfer_enabled,
      agent_enabled: f.value.agent_enabled,
      auto_subscribe_enabled: f.value.auto_subscribe_enabled,
      window_days: Number(f.value.window_days),
      language: f.value.language,
      auto_subscribe_min_vote: Number(f.value.auto_subscribe_min_vote),
      auto_subscribe_min_year: Number(f.value.auto_subscribe_min_year),
      tmdb_api_key: f.value.tmdb_api_key,
    }

    const pTransfer = {
      default_drive: f.value.default_drive,
      transfer_root: f.value.transfer_root,
      cross_transfer_enabled: f.value.cross_transfer_enabled,
      cross_transfer_threads: Number(f.value.cross_transfer_threads),
      cross_transfer_direct_stream: f.value.cross_transfer_direct_stream,
      cross_transfer_rapid_miss_action: f.value.cross_transfer_rapid_miss_action,
      cross_transfer_upload_concurrency: Number(f.value.cross_transfer_upload_concurrency),
      cross_transfer_aria2_enabled: f.value.cross_transfer_aria2_enabled,
      cross_transfer_aria2_connections: Number(f.value.cross_transfer_aria2_connections),
      cross_transfer_residue_cleanup: f.value.cross_transfer_residue_cleanup,
      type_folder_enabled: f.value.type_folder_enabled,
      type_folder_movie: f.value.type_folder_movie,
      type_folder_tv: f.value.type_folder_tv,
      enable_cloud_upgrade: f.value.enable_cloud_upgrade,
      enable_pt_upgrade: f.value.enable_pt_upgrade,
      upgrade_mode: f.value.upgrade_mode,
      min_quality: f.value.min_quality,
      min_episode_size_mb: Number(f.value.min_episode_size_mb),
      episode_dedup_enabled: f.value.episode_dedup_enabled,
      verify_landed_enabled: f.value.verify_landed_enabled,
      prefer_template_named_version: f.value.prefer_template_named_version,
      organize_source_path: f.value.organize_source_path,
      organize_max_files: Number(f.value.organize_max_files),
      organize_max_depth: Number(f.value.organize_max_depth),
      organize_include_subtitles: f.value.organize_include_subtitles,
      organize_conflict_policy: f.value.organize_conflict_policy,
      organize_schedule_enabled: f.value.organize_schedule_enabled,
      organize_schedule_cron: f.value.organize_schedule_cron,
      organize_schedule_auto_execute: f.value.organize_schedule_auto_execute,
    }

    const pStrm = {
      strm_generate_enabled: f.value.strm_generate_enabled,
      mode: f.value.strm_mode,
      strm_root: f.value.strm_root,
      strm_base_url: f.value.strm_base_url,
      local_mount_root: f.value.local_mount_root,
      url_template: f.value.url_template,
      strm_increment_enabled: f.value.strm_increment_enabled,
      strm_increment_minutes: Number(f.value.strm_increment_minutes),
      strm_full_scan_overwrite: f.value.strm_full_scan_overwrite,
      emby_url: f.value.emby_url,
      emby_api_key: f.value.emby_api_key,
      emby_refresh_enabled: f.value.emby_refresh_enabled,
      emby_mediainfo_enabled: f.value.emby_mediainfo_enabled,
      media_server_refresh_delay: Number(f.value.media_server_refresh_delay),
    }

    const pNotify = {
      channels: {
        feishu: { enabled: f.value.feishu_enabled, webhook_url: f.value.feishu_url },
        telegram: { enabled: f.value.telegram_enabled, bot_token: f.value.telegram_token, chat_id: f.value.telegram_chat_id },
        webhook: { enabled: f.value.webhook_enabled, url: f.value.webhook_url },
      },
    }

    const pAdv = {
      log_level: f.value.log_level,
      max_workers: Number(f.value.max_workers),
      checkin_cron: f.value.checkin_cron,
      checkin_auto_retry: f.value.checkin_auto_retry,
      checkin_retry_count: Number(f.value.checkin_retry_count),
      p115_checkin_mode: f.value.p115_checkin_mode,
      tg_monitor_enabled: f.value.tg_monitor_enabled,
      tg_api_id: f.value.tg_api_id,
      tg_api_hash: f.value.tg_api_hash,
      tg_session: f.value.tg_session,
      tg_channels: f.value.tg_channels,
      tg_auto_transfer: f.value.tg_auto_transfer,
      tg_monitor_interval_minutes: Number(f.value.tg_monitor_interval_minutes),
      tg_monitor_keep_unmatched: f.value.tg_monitor_keep_unmatched,
    }

    await Promise.all([
      settingsApi.updateSection('baseline', pBaseline),
      settingsApi.updateSection('transfer', pTransfer),
      settingsApi.updateSection('strm', pStrm),
      settingsApi.updateSection('notify', pNotify),
      settingsApi.updateSection('advanced', pAdv),
    ])

    toast('全量设置已保存并即时生效', 'success')
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
  } catch (cause) {
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
  qrMessage.value = '正在向官方申请登录二维码…'
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
  <div class="space-y-6">
    <!-- 顶部统一大标题与全局保存 -->
    <header class="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
      <div>
        <h2 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <span>系统设置</span>
          <Badge tone="muted" class="text-[10px] font-mono">Apple HIG</Badge>
        </h2>
        <p class="mt-1 text-xs text-zinc-400">细致调控网盘账号、自动追剧规则、全网搜索站点、画质洗版与播放模式</p>
      </div>

      <div class="flex items-center gap-3">
        <Button size="sm" class="apple-btn-primary px-5 shadow-sm" :disabled="saving" @click="saveAll">
          <span>{{ saving ? '正在保存…' : '保存设置' }}</span>
        </Button>
      </div>
    </header>

    <!-- 苹果经典药丸分段选择器 (横向 Segmented Control) -->
    <Tabs v-model="activeTab" :items="mainTabs" />

    <!-- 1. 网盘账号管理 (饱满、精致、零空洞) -->
    <div v-if="activeTab === 'accounts'" class="space-y-5">
      <div class="apple-glass rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 class="text-base font-semibold text-white flex items-center gap-2">
            <Cloud class="h-4.5 w-4.5 text-blue-400" />
            <span>网盘账号管理</span>
          </h3>
          <p class="mt-1 text-xs text-zinc-400 max-w-xl">
            绑定你的 115 或夸克网盘账号，自动转存的影视将直接保存到你的网盘中。所有登录凭据均通过 Fernet 工业级加密存储。
          </p>
        </div>

        <Button size="sm" class="apple-btn-primary flex items-center gap-1.5 shadow-sm" @click="openScanDialog">
          <QrCode class="h-4 w-4" />
          <span>📱 手机扫码绑定新网盘</span>
        </Button>
      </div>

      <!-- 账号卡片流 -->
      <div v-if="!accounts.length" class="apple-glass rounded-2xl p-16 text-center text-xs text-zinc-400 space-y-3">
        <HardDrive class="mx-auto h-8 w-8 text-zinc-600" />
        <p class="text-sm font-semibold text-white">尚未绑定任何网盘账号</p>
        <p class="text-xs text-zinc-500 max-w-sm mx-auto">
          点击右上角「手机扫码绑定新网盘」，使用 115 或夸克手机 App 扫码即可 10 秒免抓包自动绑定。
        </p>
      </div>

      <div v-else class="grid gap-4 sm:grid-cols-2">
        <article
          v-for="account in accounts"
          :key="account.id"
          class="apple-glass rounded-2xl p-5 flex items-center justify-between gap-4"
        >
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <strong class="font-semibold text-white text-sm">{{ account.name }}</strong>
              <Badge tone="muted" class="font-mono uppercase text-[10px]">{{ account.provider }}网盘</Badge>
            </div>
            <p class="mt-2 text-xs text-zinc-400 flex items-center gap-1.5">
              <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]"></span>
              <span>已通过 Fernet 高度加密保护</span>
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <Button variant="outline" size="sm" class="h-8 text-xs" @click="testAccount(account.id)">
              <RefreshCw class="mr-1 h-3 w-3" />
              检测连通
            </Button>
            <Button variant="ghost" size="sm" class="h-8 w-8 p-0 text-rose-400 hover:text-rose-300" @click="removeAccount(account.id)">
              <Trash2 class="h-3.5 w-3.5" />
            </Button>
          </div>
        </article>
      </div>
    </div>

    <!-- 2. 追剧与规则 (整合：基础运行 + 自动追剧 + 转存洗版，细粒度配置全补齐) -->
    <div v-else-if="activeTab === 'automation'" class="apple-glass rounded-3xl p-6 sm:p-8 space-y-8">
      <!-- 2.1 基础与调度 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">基础运行与自动追更</h3>
          <p class="mt-0.5 text-xs text-zinc-400">控制系统调度总开关、片名自动订阅与补更规则</p>
        </div>

        <div class="divide-y divide-white/[0.06] text-xs">
          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">全自动追剧与监控总开关</p>
              <p class="text-zinc-500 mt-0.5">关闭后系统将暂停所有后台自动化找源与转存任务</p>
            </div>
            <Switch v-model="f.enabled" />
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">片名智能自动订阅</p>
              <p class="text-zinc-500 mt-0.5">当频道抓取或手动转存时，若遇到未关注剧集自动加入追剧清单</p>
            </div>
            <Switch v-model="f.title_subscribe_enabled" />
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">缺集全季自动补齐</p>
              <p class="text-zinc-500 mt-0.5">发现剧集更新时，不仅追更最新一集，同时自动补齐整季前面缺失的所有剧集</p>
            </div>
            <Switch v-model="f.subscribe_all_missing_seasons" />
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">跳过第 0 季 (特别篇 S00)</p>
              <p class="text-zinc-500 mt-0.5">默认不订阅剧集特辑、采访与预告等第 0 季内容</p>
            </div>
            <Switch v-model="f.subscribe_skip_season_zero" />
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">最多补建季数上限</p>
              <p class="text-zinc-500 mt-0.5">限制单次自动补齐的最大季数（0 表示不限制）</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.subscribe_season_limit" type="number" min="0" max="50" />
              <span class="text-zinc-500 shrink-0">季</span>
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">检查最近多少天的更新</p>
              <p class="text-zinc-500 mt-0.5">剧集播出后，系统在多少天窗口内持续全网搜寻并补齐缺失集</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.window_days" type="number" min="1" max="365" />
              <span class="text-zinc-500 shrink-0">天</span>
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">榜单自动订阅最低评分门槛</p>
              <p class="text-zinc-500 mt-0.5">仅当全网影视评分大于等于此门槛时才自动订阅（默认 7.0 分）</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.auto_subscribe_min_vote" type="number" step="0.1" min="0" max="10" />
              <span class="text-zinc-500 shrink-0">分</span>
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">TMDB API 官方密钥</p>
              <p class="text-zinc-500 mt-0.5">用于渲染高清电影海报墙、剧情简介与热播榜单（留空自动使用系统内置密钥）</p>
            </div>
            <div class="w-full sm:w-72">
              <Input v-model="f.tmdb_api_key" type="password" placeholder="留空使用系统预设密钥" />
            </div>
          </div>
        </div>
      </div>

      <!-- 2.2 转存与洗版控制 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">网盘转存、中继与洗版偏好</h3>
          <p class="mt-0.5 text-xs text-zinc-400">首选网盘、跨盘直传搬运、画质阶梯与防假种限制</p>
        </div>

        <div class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">首选默认转存网盘</p>
              <p class="text-zinc-500 mt-0.5">搜寻到多个网盘链接时，优先存入哪个网盘账号</p>
            </div>
            <div class="w-full sm:w-56">
              <Select
                v-model="f.default_drive"
                :options="[
                  { value: 'quark', label: '夸克网盘 (默认)' },
                  { value: '115', label: '115 网盘' },
                ]"
              />
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">网盘转存保存根目录</p>
              <p class="text-zinc-500 mt-0.5">存入网盘时的根文件夹路径（默认 CSX）</p>
            </div>
            <div class="w-full sm:w-72 flex gap-2">
              <Input v-model="f.transfer_root" placeholder="例如 CSX" />
              <Button
                v-if="accounts.length"
                variant="outline"
                size="sm"
                class="shrink-0"
                @click="dirTarget = 'transfer_root'; dirDialogOpen = true"
              >
                浏览网盘
              </Button>
            </div>
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">按媒体类型建一级目录</p>
              <p class="text-zinc-500 mt-0.5">在网盘转存目录和媒体库下自动建立「电影 / 电视剧」分层子目录</p>
            </div>
            <Switch v-model="f.type_folder_enabled" />
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">启用跨网盘中继自动转存 (Cross Transfer)</p>
              <p class="text-zinc-500 mt-0.5">例如将夸克分享资源自动下载并高速转存至你的 115 网盘</p>
            </div>
            <Switch v-model="f.cross_transfer_enabled" />
          </div>

          <div v-if="f.cross_transfer_enabled" class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">跨盘转存并行并发线程数</p>
              <p class="text-zinc-500 mt-0.5">中继搬运时同时进行下载和分片上传的连接数（默认 3）</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.cross_transfer_threads" type="number" min="1" max="8" />
              <span class="text-zinc-500 shrink-0">线程</span>
            </div>
          </div>

          <div v-if="f.cross_transfer_enabled" class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">跨盘直传（边下边传）</p>
              <p class="text-zinc-500 mt-0.5">从源盘 Range 直传目标盘，不落本地硬盘（源盘单连接慢时建议关闭）</p>
            </div>
            <Switch v-model="f.cross_transfer_direct_stream" />
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">启用网盘自动画质升级 (洗版)</p>
              <p class="text-zinc-500 mt-0.5">当后续搜寻到更高规格的画质时，自动替换网盘中的低画质旧版</p>
            </div>
            <Switch v-model="f.enable_cloud_upgrade" />
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">最低接受画质门槛</p>
              <p class="text-zinc-500 mt-0.5">低于此规格的资源将被自动忽略，绝不浪费网盘空间</p>
            </div>
            <div class="w-full sm:w-56">
              <Select
                v-model="f.min_quality"
                :options="[
                  { value: 'sd', label: '标清 720p 及以上' },
                  { value: 'hd', label: '高清 1080p 及以上 (推荐)' },
                  { value: '4k', label: '仅限 4K 超高清' },
                ]"
              />
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">单集视频最小体积门槛 (防假种)</p>
              <p class="text-zinc-500 mt-0.5">低于此体积的单集视频将被当成预告/花絮直接丢弃（默认 100MB，字幕不受限制）</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.min_episode_size_mb" type="number" min="10" max="2000" />
              <span class="text-zinc-500 shrink-0">MB</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 搜源站点 (全量 15 源自描述面板) -->
    <div v-else-if="activeTab === 'sources'" class="space-y-4">
      <div class="apple-glass rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 class="text-base font-semibold text-white">全网 15 个搜索源自描述配置</h3>
          <p class="mt-0.5 text-xs text-zinc-400">各源自带独立开关、服务地址、专属 Token 与单源在线网络测速</p>
        </div>
      </div>

      <div class="grid gap-5 lg:grid-cols-[220px_minmax(0,1fr)] items-start">
        <!-- 15 源垂直导航 -->
        <nav class="apple-glass rounded-2xl p-2 max-h-[640px] overflow-y-auto space-y-1">
          <button
            v-for="s in sourceSchemas"
            :key="s.id"
            type="button"
            class="flex min-h-10 w-full items-center justify-between rounded-xl px-3 text-left text-xs font-medium transition-colors cursor-pointer"
            :class="selectedSourceId === s.id ? 'bg-white/10 text-white ring-1 ring-white/15' : 'text-zinc-400 hover:bg-white/[0.04]'"
            @click="selectedSourceId = s.id; sourceTest = null"
          >
            <span>{{ s.name }}</span>
            <span
              class="h-2 w-2 rounded-full"
              :class="sourceValues[s.id]?.enabled === false ? 'bg-zinc-600' : 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]'"
            />
          </button>
        </nav>

        <!-- 当前源专属表单 -->
        <div v-if="currentSource" class="space-y-4 min-w-0">
          <div class="apple-glass rounded-2xl p-4 flex items-center justify-between">
            <div>
              <h4 class="text-sm font-semibold text-white">{{ currentSource.name }}</h4>
              <p class="mt-0.5 text-xs text-zinc-500">排序权重：{{ currentSource.order }}</p>
            </div>
            <Button variant="outline" size="sm" :disabled="sourceTestRunning" @click="testSelectedSource">
              <Search class="mr-1.5 h-3.5 w-3.5" />
              <span>{{ sourceTestRunning ? '检测中…' : '测试该搜索源连通性' }}</span>
            </Button>
          </div>

          <div
            v-if="sourceTest"
            class="rounded-xl border p-3.5 text-xs flex items-center justify-between"
            :class="sourceTest.valid ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-rose-500/30 bg-rose-500/10 text-rose-400'"
          >
            <span>{{ sourceTest.valid ? '连通正常' : '连通失败' }}：{{ sourceTest.message }}</span>
            <span class="font-mono">{{ sourceTest.elapsed_ms }} ms</span>
          </div>

          <div v-for="(group, gIndex) in currentSource.groups" :key="gIndex" class="apple-glass rounded-2xl p-5 space-y-4">
            <h5 class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ group.title || '基本配置' }}</h5>
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
    </div>

    <!-- 4. 播放与入库 (整合：STRM 与原画播放 + Emby 媒体服务 + 整理归位) -->
    <div v-else-if="activeTab === 'playback'" class="apple-glass rounded-3xl p-6 sm:p-8 space-y-8">
      <!-- 4.1 STRM 与 302 播放 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">STRM 原画播放与媒体库</h3>
          <p class="mt-0.5 text-xs text-zinc-400">配置 Emby/Jellyfin 直链播放模式与网盘整理归位策略</p>
        </div>

        <div class="divide-y divide-white/[0.06] text-xs">
          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">转存入库后自动生成 STRM 播放文件</p>
              <p class="text-zinc-500 mt-0.5">让 Emby / Jellyfin 无需下载实体大文件即可秒开播放网盘原画视频</p>
            </div>
            <Switch v-model="f.strm_generate_enabled" />
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">STRM 播放模式</p>
              <p class="text-zinc-500 mt-0.5">选择 Emby 读取网盘视频的具体实现路径</p>
            </div>
            <div class="w-full sm:w-64">
              <Select
                v-model="f.strm_mode"
                :options="[
                  { value: 'direct_302', label: '302 原画直链跳转模式 (推荐·零流量)' },
                  { value: 'local_mount', label: '本地挂载路径模式 (CloudDrive / Alist)' },
                  { value: 'template', label: '自定义直链代理 URL 模板' },
                ]"
              />
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">STRM 本地导出根目录</p>
              <p class="text-zinc-500 mt-0.5">生成的 .strm 文件存放在服务器的物理路径</p>
            </div>
            <div class="w-full sm:w-64">
              <Input v-model="f.strm_root" placeholder="例如 /strm" />
            </div>
          </div>

          <div v-if="f.strm_mode === 'local_mount'" class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">网盘本地挂载根目录</p>
              <p class="text-zinc-500 mt-0.5">CloudDrive2 或 Alist 挂载到宿主机的文件目录</p>
            </div>
            <div class="w-full sm:w-64 flex gap-2">
              <Input v-model="f.local_mount_root" placeholder="例如 /mnt/quark" />
              <Button variant="outline" size="sm" @click="dirTarget = 'local_mount_root'; dirDialogOpen = true">浏览</Button>
            </div>
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">定时增量补齐缺失 STRM</p>
              <p class="text-zinc-500 mt-0.5">定期比对网盘文件，自动为漏建的文件补齐 .strm</p>
            </div>
            <Switch v-model="f.strm_increment_enabled" />
          </div>
        </div>
      </div>

      <!-- 4.2 Emby 媒体服务器配置 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">Emby / Jellyfin 媒体服务器设置</h3>
          <p class="mt-0.5 text-xs text-zinc-400">配置服务器地址与 API 密钥，新剧入库后自动刷新海报与片单</p>
        </div>

        <div class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">Emby / Jellyfin 服务器地址</p>
              <p class="text-zinc-500 mt-0.5">你的媒体服务器内网或公网访问 URL</p>
            </div>
            <div class="w-full sm:w-72">
              <Input v-model="f.emby_url" placeholder="http://172.18.0.x:8096" />
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">API 密钥 (API Key)</p>
              <p class="text-zinc-500 mt-0.5">在 Emby 控制台「高级 → API 密钥」中生成的令牌</p>
            </div>
            <div class="w-full sm:w-72">
              <Input v-model="f.emby_api_key" type="password" placeholder="粘贴 Emby API 密钥" />
            </div>
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">转存入库后自动刷新 Emby 媒体库</p>
              <p class="text-zinc-500 mt-0.5">新剧入库后立即命令 Emby 扫描更新，客户端立即可见正片</p>
            </div>
            <Switch v-model="f.emby_refresh_enabled" />
          </div>
        </div>
      </div>

      <!-- 4.3 全盘整理规则 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">全盘整理规则</h3>
          <p class="mt-0.5 text-xs text-zinc-400">暂存源文件夹、递归深度与字幕跟随策略</p>
        </div>

        <div class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">网盘暂存区扫描目录</p>
              <p class="text-zinc-500 mt-0.5">整理台扫描散落未分类视频的暂存文件夹</p>
            </div>
            <div class="w-full sm:w-72 flex gap-2">
              <Input v-model="f.organize_source_path" placeholder="例如 /CSX/_inbox" />
              <Button
                v-if="accounts.length"
                variant="outline"
                size="sm"
                class="shrink-0"
                @click="dirTarget = 'organize_source_path'; dirDialogOpen = true"
              >
                浏览网盘
              </Button>
            </div>
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">字幕文件随视频自动归位</p>
              <p class="text-zinc-500 mt-0.5">整理视频时自动将同目录下的 .srt/.ass 外挂字幕改名并移动</p>
            </div>
            <Switch v-model="f.organize_include_subtitles" />
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">目标同名文件冲突策略</p>
              <p class="text-zinc-500 mt-0.5">当影视库中已存在同名集数文件时的处理方式</p>
            </div>
            <div class="w-full sm:w-56">
              <Select
                v-model="f.organize_conflict_policy"
                :options="[
                  { value: 'largest', label: '保留体积较大版本 (推荐)' },
                  { value: 'replace', label: '直接覆盖旧文件' },
                  { value: 'skip', label: '跳过不处理' },
                ]"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 5. 通知与高级 (整合：多渠道通知 + TG监控 + 每日签到 + 高级运维) -->
    <div v-else-if="activeTab === 'system'" class="apple-glass rounded-3xl p-6 sm:p-8 space-y-8">
      <!-- 5.1 消息通知通道 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">多渠道消息通知推送</h3>
          <p class="mt-0.5 text-xs text-zinc-400">转存完成、发现新剧或发生异常时通过机器人即时提醒</p>
        </div>

        <div class="space-y-3.5 text-xs">
          <!-- 飞书 -->
          <div class="rounded-2xl border border-white/[0.08] bg-zinc-900/60 p-4 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <strong class="text-sm font-semibold text-white">飞书群机器人通知</strong>
                <p class="text-zinc-500 mt-0.5">在飞书群添加自定义机器人，接收转存和更新卡片</p>
              </div>
              <Switch v-model="f.feishu_enabled" />
            </div>
            <div v-if="f.feishu_enabled" class="pt-2">
              <label class="text-zinc-400">Webhook 地址</label>
              <Input v-model="f.feishu_url" class="mt-1" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
            </div>
          </div>

          <!-- Telegram -->
          <div class="rounded-2xl border border-white/[0.08] bg-zinc-900/60 p-4 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <strong class="text-sm font-semibold text-white">Telegram 机器人通知</strong>
                <p class="text-zinc-500 mt-0.5">通过 Telegram Bot 向你私聊或频道推送更新</p>
              </div>
              <Switch v-model="f.telegram_enabled" />
            </div>
            <div v-if="f.telegram_enabled" class="grid sm:grid-cols-2 gap-3 pt-2">
              <div>
                <label class="text-zinc-400">Bot Token</label>
                <Input v-model="f.telegram_token" class="mt-1" type="password" placeholder="123456:ABC-DEF..." />
              </div>
              <div>
                <label class="text-zinc-400">Chat ID</label>
                <Input v-model="f.telegram_chat_id" class="mt-1" placeholder="例如 -10012345678" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 5.2 每日签到与定时任务 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">网盘每日自动签到</h3>
          <p class="mt-0.5 text-xs text-zinc-400">为所有已绑定网盘自动签到领空间积分</p>
        </div>

        <div class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">签到执行周期 Cron 表达式</p>
              <p class="text-zinc-500 mt-0.5">默认每日凌晨 00:30 执行</p>
            </div>
            <div class="w-full sm:w-48">
              <Input v-model="f.checkin_cron" placeholder="30 0 * * *" />
            </div>
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">签到失败自动重试</p>
              <p class="text-zinc-500 mt-0.5">遇到网盘网络抖动时在白天自动重试</p>
            </div>
            <Switch v-model="f.checkin_auto_retry" />
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">115 网盘签到模式</p>
              <p class="text-zinc-500 mt-0.5">普通签到领枫叶，或自动参与空间抽取</p>
            </div>
            <div class="w-full sm:w-56">
              <Select
                v-model="f.p115_checkin_mode"
                :options="[
                  { value: 'normal', label: '普通日常签到' },
                  { value: 'lottery', label: '自动参与空间抽奖' },
                ]"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 5.3 Telegram 频道监控 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">Telegram 频道监控配置</h3>
          <p class="mt-0.5 text-xs text-zinc-400">监听 TG 频道消息自动提取夸克/115分享链接并转存</p>
        </div>

        <div class="divide-y divide-white/[0.06] text-xs">
          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">启用 Telegram 频道消息实时抓链监控</p>
              <p class="text-zinc-500 mt-0.5">监听频道新消息并自动抽取网盘分享</p>
            </div>
            <Switch v-model="f.tg_monitor_enabled" />
          </div>

          <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">监控频道名单 (每行一个)</p>
              <p class="text-zinc-500 mt-0.5">如 @Quark_Share_Group、@share115</p>
            </div>
            <div class="w-full sm:w-80">
              <textarea
                v-model="f.tg_channels"
                rows="3"
                class="w-full rounded-xl border border-white/10 bg-zinc-900/60 p-3 font-mono text-xs text-white outline-none"
              />
            </div>
          </div>

          <div class="flex items-center justify-between py-3.5">
            <div>
              <p class="font-medium text-white text-sm">识别到新剧集后自动转存入库</p>
              <p class="text-zinc-500 mt-0.5">命中追剧缺集时直接建立转存任务转入网盘</p>
            </div>
            <Switch v-model="f.tg_auto_transfer" />
          </div>
        </div>
      </div>

      <!-- 5.4 系统高级运行参数 -->
      <div class="space-y-4">
        <div class="border-b border-white/[0.08] pb-3">
          <h3 class="text-base font-semibold text-white">系统高级运行参数</h3>
          <p class="mt-0.5 text-xs text-zinc-400">日志等级、并发任务数与核心性能调控</p>
        </div>

        <div class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">系统运行日志输出级别</p>
              <p class="text-zinc-500 mt-0.5">控制后台服务在控制台输出日志的详细程度</p>
            </div>
            <div class="w-full sm:w-48">
              <Select
                v-model="f.log_level"
                :options="[
                  { value: 'INFO', label: '标准记录 (INFO)' },
                  { value: 'DEBUG', label: '详细调试 (DEBUG)' },
                  { value: 'WARNING', label: '仅警告与错误' },
                ]"
              />
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3.5">
            <div>
              <p class="font-medium text-white text-sm">转存任务最大并发上限</p>
              <p class="text-zinc-500 mt-0.5">同时进行的网盘转存与整理任务的最大线程数（默认 8）</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.max_workers" type="number" min="1" max="32" />
              <span class="text-zinc-500 shrink-0">并发</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 扫码绑定网盘 Dialog -->
    <Dialog :open="qrOpen" title="扫码绑定网盘" @close="closeQrcode">
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <label class="block space-y-1 text-xs">
            <span class="text-zinc-400">网盘类型</span>
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
            <span class="text-zinc-400">账号备注名称</span>
            <Input v-model="qrName" placeholder="例如：我的主号" />
          </label>
        </div>

        <div class="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-zinc-900/60 p-6">
          <div v-if="qrData?.qrcode" class="space-y-3 text-center">
            <div class="p-3 bg-white rounded-2xl inline-block shadow-md">
              <img :src="qrData.qrcode" class="h-48 w-48 object-contain" />
            </div>
            <div class="space-y-1">
              <Badge :tone="qrStatus === 'scanned' ? 'good' : qrStatus === 'expired' ? 'bad' : 'warn'">
                {{ qrStatus === 'scanned' ? '已扫码，等待手机端确认' : qrStatus === 'expired' ? '已失效' : '等待手机扫码' }}
              </Badge>
              <p class="text-xs text-zinc-400 mt-1">{{ qrData.hint }}</p>
            </div>
          </div>
          <div v-else-if="qrStarting" class="py-12 text-center text-xs text-zinc-400 space-y-2">
            <RefreshCw class="mx-auto h-6 w-6 animate-spin text-white" />
            <p>{{ qrMessage }}</p>
          </div>
          <div v-else class="py-12 text-center text-xs text-rose-400">
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
