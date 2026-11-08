<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  Bell,
  Check,
  Clapperboard,
  Cloud,
  Code2,
  FolderOpen,
  FolderSync,
  HardDrive,
  KeyRound,
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

// macOS Sequoia 系统设置 12 大分类
interface SettingCategory {
  id: string
  name: string
  desc: string
  icon: any
  badge?: string
  color: string // 图标底色
}

const categories: SettingCategory[] = [
  { id: 'accounts', name: '网盘账号', desc: '绑定你的 115、夸克等网盘账号，支持手机 App 一键扫码免抓 Cookie 快速绑定', icon: Cloud, color: 'bg-blue-500' },
  { id: 'basic', name: '基础运行', desc: '控制全自动追剧总开关、片名自动订阅与链接直达转存偏好', icon: Workflow, color: 'bg-zinc-600' },
  { id: 'transfer', name: '转存搬运', desc: '首选转存网盘、跨网盘中继转存通道与订阅白名单/黑名单过滤', icon: FolderSync, color: 'bg-purple-500' },
  { id: 'organize', name: '全盘整理', desc: '暂存区目录全盘扫描、智能片名识别与目标标准影视库归位策略', icon: FolderOpen, color: 'bg-amber-500' },
  { id: 'subscribe', name: '自动追剧', desc: '配置检查追更回溯天数、TMDB / 豆瓣 / 蜜柑 / Bangumi 榜单自动追剧与评分门槛', icon: Tv, color: 'bg-rose-500' },
  { id: 'checkin', name: '每日签到', desc: '配置每日自动签到定时周期、失败重试与空间抽奖偏好', icon: Calendar, color: 'bg-yellow-500' },
  { id: 'tg', name: 'TG 监控', desc: '配置 Telegram 用户会话、频道监听名单与自动提取转存规则', icon: Send, color: 'bg-sky-500' },
  { id: 'strm', name: 'STRM 播放', desc: '配置供 Emby / Jellyfin / 播放器调用的本地挂载或 302 原画直链跳转', icon: PlaySquare, color: 'bg-emerald-500' },
  { id: 'emby', name: 'Emby 服务', desc: '配置 Emby / Jellyfin 媒体服务器地址、API 密钥与入库后自动刷新命令', icon: Clapperboard, color: 'bg-teal-600' },
  { id: 'sources', name: '搜索找源', desc: '全网 15 个搜索源独立开关、服务地址、专属 Token 与单源在线测速', icon: Search, color: 'bg-cyan-500' },
  { id: 'upgrade', name: '画质洗版', desc: '网盘自动洗版、画质优先等级阶梯（REMUX > DV > HDR）与防假种门槛', icon: Sparkles, color: 'bg-indigo-500' },
  { id: 'notify', name: '消息通知', desc: '转存成功、洗版更新或异常时通过飞书群机器人、Telegram Bot、Webhook 提醒', icon: Bell, color: 'bg-pink-500' },
  { id: 'advanced', name: '高级运维', desc: '系统底层运行日志等级、并发任务数限制与 SQLite 在线无锁热备', icon: ShieldCheck, color: 'bg-neutral-600' },
]

const activeCat = ref('accounts')
const currentCat = computed(() => categories.find((c) => c.id === activeCat.value) || categories[0])
const { toast } = useToast()

// 各分类通用数据
const accounts = ref<Account[]>([])
const loading = ref(false)
const saving = ref(false)

// 15 个搜索源自描述状态
const sourceSchemas = ref<SearchSourceSchema[]>([])
const sourceValues = ref<Record<string, Record<string, any>>>({})
const selectedSourceId = ref('pansou')
const sourceTest = ref<SearchSourceTest | null>(null)
const sourceTestRunning = ref(false)

// 表单全量响应式字段（严格对齐 12 大模块）
const f = ref<Record<string, any>>({
  // basic
  enabled: true,
  title_subscribe_enabled: true,
  subscribe_all_missing_seasons: false,
  direct_transfer_enabled: true,
  agent_enabled: true,
  // transfer
  default_drive: 'quark',
  cross_transfer_enabled: true,
  cross_transfer_threads: 3,
  transfer_root: 'CSX',
  // organize
  organize_source_path: '/CSX/_inbox',
  organize_max_files: 100,
  organize_max_depth: 3,
  organize_include_subtitles: true,
  organize_conflict_policy: 'largest',
  // subscribe
  auto_subscribe_enabled: true,
  window_days: 14,
  language: 'zh-CN',
  auto_subscribe_min_vote: 7.0,
  auto_subscribe_min_year: 2024,
  tmdb_api_key: '',
  // checkin
  checkin_cron: '30 0 * * *',
  checkin_retry_count: 2,
  p115_checkin_mode: 'normal',
  // tg
  tg_monitor_enabled: false,
  tg_api_id: '',
  tg_api_hash: '',
  tg_session: '',
  tg_channels: '@Quark_Share_Group\n@share115',
  tg_auto_transfer: true,
  // strm
  strm_generate_enabled: true,
  strm_mode: 'direct_302',
  strm_root: '/strm',
  strm_base_url: '',
  local_mount_root: '/mnt/quark',
  url_template: '',
  // emby
  emby_url: '',
  emby_api_key: '',
  emby_refresh_enabled: true,
  // upgrade
  enable_cloud_upgrade: true,
  min_episode_size_mb: 100,
  min_quality: 'hd',
  // notify
  feishu_enabled: false,
  feishu_url: '',
  telegram_enabled: false,
  telegram_token: '',
  telegram_chat_id: '',
  webhook_enabled: false,
  webhook_url: '',
  // advanced
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

// 加载当前设置项
async function loadCurrent() {
  loading.value = true
  try {
    if (activeCat.value === 'accounts') {
      await loadAccounts()
    } else if (activeCat.value === 'sources') {
      await loadSources()
    } else {
      // 映射到后端 6 大标准 section
      const secMap: Record<string, SettingSection> = {
        basic: 'baseline',
        subscribe: 'baseline',
        transfer: 'transfer',
        upgrade: 'transfer',
        organize: 'transfer',
        strm: 'strm',
        emby: 'strm',
        checkin: 'advanced',
        tg: 'sources',
        notify: 'notify',
        advanced: 'advanced',
      }
      const targetSec = secMap[activeCat.value] || 'baseline'
      const res = await settingsApi.getSection(targetSec)
      // 深度回填
      Object.assign(f.value, res)
    }
  } catch (cause) {
    console.error(cause)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadAccounts()
  void loadCurrent()
})

watch(activeCat, () => {
  void loadCurrent()
})

// 保存当前设置
async function handleSave() {
  saving.value = true
  try {
    if (activeCat.value === 'sources') {
      await searchSourcesApi.save(sourceValues.value)
      toast('全网 15 搜索源配置已保存', 'success')
      return
    }

    const secMap: Record<string, SettingSection> = {
      basic: 'baseline',
      subscribe: 'baseline',
      transfer: 'transfer',
      upgrade: 'transfer',
      organize: 'transfer',
      strm: 'strm',
      emby: 'strm',
      checkin: 'advanced',
      tg: 'sources',
      notify: 'notify',
      advanced: 'advanced',
    }
    const targetSec = secMap[activeCat.value] || 'baseline'

    // 根据分类组装标准 payload
    let payload: Record<string, any> = {}
    if (activeCat.value === 'basic' || activeCat.value === 'subscribe') {
      payload = {
        enabled: f.value.enabled,
        title_subscribe_enabled: f.value.title_subscribe_enabled,
        subscribe_all_missing_seasons: f.value.subscribe_all_missing_seasons,
        direct_transfer_enabled: f.value.direct_transfer_enabled,
        agent_enabled: f.value.agent_enabled,
        window_days: Number(f.value.window_days),
        language: f.value.language,
        auto_subscribe_min_vote: Number(f.value.auto_subscribe_min_vote),
        auto_subscribe_min_year: Number(f.value.auto_subscribe_min_year),
        tmdb_api_key: f.value.tmdb_api_key,
      }
    } else if (activeCat.value === 'transfer' || activeCat.value === 'upgrade' || activeCat.value === 'organize') {
      payload = {
        default_drive: f.value.default_drive,
        cross_transfer_enabled: f.value.cross_transfer_enabled,
        cross_transfer_threads: Number(f.value.cross_transfer_threads),
        transfer_root: f.value.transfer_root,
        enable_cloud_upgrade: f.value.enable_cloud_upgrade,
        min_quality: f.value.min_quality,
        min_episode_size_mb: Number(f.value.min_episode_size_mb),
        organize_source_path: f.value.organize_source_path,
        organize_max_files: Number(f.value.organize_max_files),
        organize_include_subtitles: f.value.organize_include_subtitles,
        organize_conflict_policy: f.value.organize_conflict_policy,
      }
    } else if (activeCat.value === 'strm' || activeCat.value === 'emby') {
      payload = {
        strm_generate_enabled: f.value.strm_generate_enabled,
        mode: f.value.strm_mode,
        strm_root: f.value.strm_root,
        strm_base_url: f.value.strm_base_url,
        local_mount_root: f.value.local_mount_root,
        url_template: f.value.url_template,
        emby_url: f.value.emby_url,
        emby_api_key: f.value.emby_api_key,
        emby_refresh_enabled: f.value.emby_refresh_enabled,
      }
    } else if (activeCat.value === 'notify') {
      payload = {
        channels: {
          feishu: { enabled: f.value.feishu_enabled, webhook_url: f.value.feishu_url },
          telegram: { enabled: f.value.telegram_enabled, bot_token: f.value.telegram_token, chat_id: f.value.telegram_chat_id },
          webhook: { enabled: f.value.webhook_enabled, url: f.value.webhook_url },
        },
      }
    } else {
      payload = {
        log_level: f.value.log_level,
        max_workers: Number(f.value.max_workers),
        checkin_cron: f.value.checkin_cron,
        checkin_retry_count: Number(f.value.checkin_retry_count),
      }
    }

    await settingsApi.updateSection(targetSec, payload)
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
    <!-- 顶部标题 -->
    <div>
      <h2 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
        <span>系统设置</span>
        <Badge tone="muted" class="text-[10px] font-mono">macOS HIG</Badge>
      </h2>
      <p class="mt-1 text-xs text-zinc-400">细致调控网盘账号、自动追剧规则、全网搜索站点、画质洗版与播放模式</p>
    </div>

    <!-- macOS Sequoia 经典双栏布局 (左侧 240px 分类导航 + 右侧毛玻璃面板) -->
    <div class="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)] items-start">
      <!-- 左侧分类侧栏 (macOS System Settings 风格) -->
      <aside class="apple-glass rounded-2xl p-2.5 space-y-1">
        <button
          v-for="cat in categories"
          :key="cat.id"
          type="button"
          class="flex w-full min-h-[42px] items-center gap-3 rounded-xl px-3 py-2 text-left text-xs font-medium transition-all duration-150 cursor-pointer"
          :class="
            activeCat === cat.id
              ? 'bg-white/10 text-white shadow-sm ring-1 ring-white/15'
              : 'text-zinc-400 hover:bg-white/[0.04] hover:text-white'
          "
          @click="activeCat = cat.id"
        >
          <!-- 经典彩色圆角小图标 (SF Symbols 风格) -->
          <div class="grid h-6 w-6 shrink-0 place-items-center rounded-lg text-white shadow-sm" :class="cat.color">
            <component :is="cat.icon" class="h-3.5 w-3.5 text-white" />
          </div>
          <span class="truncate tracking-tight flex-1">{{ cat.name }}</span>
          <span
            v-if="cat.id === 'accounts' && accounts.length"
            class="rounded-full bg-white/10 px-1.5 py-0.2 font-mono text-[10px] text-zinc-300"
          >
            {{ accounts.length }}
          </span>
          <span
            v-if="cat.id === 'sources' && sourceSchemas.length"
            class="rounded-full bg-white/10 px-1.5 py-0.2 font-mono text-[10px] text-zinc-300"
          >
            15
          </span>
        </button>
      </aside>

      <!-- 右侧设置面板 (高质感苹果毛玻璃卡片) -->
      <main class="apple-glass rounded-3xl p-6 sm:p-8 space-y-6 min-w-0">
        <!-- 头部说明与纯白胶囊保存按钮 -->
        <header class="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
          <div class="space-y-1">
            <h3 class="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              <span>{{ currentCat.name }}</span>
            </h3>
            <p class="text-xs text-zinc-400 leading-relaxed max-w-xl">{{ currentCat.desc }}</p>
          </div>
          <div v-if="activeCat !== 'accounts'" class="flex items-center gap-3">
            <Button size="sm" class="apple-btn-primary px-5 shadow-sm" :disabled="saving" @click="handleSave">
              <span>{{ saving ? '正在保存…' : '保存本项设置' }}</span>
            </Button>
          </div>
        </header>

        <!-- 1. 网盘账号专属管理模块 (完全解耦，零硬塞) -->
        <section v-if="activeCat === 'accounts'" class="space-y-5">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-semibold text-white">已绑定的网盘列表</h4>
            <Button size="sm" class="apple-btn-primary flex items-center gap-1.5 shadow-sm" @click="openScanDialog">
              <QrCode class="h-4 w-4" />
              <span>📱 手机扫码绑定新网盘</span>
            </Button>
          </div>

          <div v-if="!accounts.length" class="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-16 text-center text-xs text-zinc-400 space-y-2">
            <HardDrive class="mx-auto h-8 w-8 text-zinc-600" />
            <p class="text-sm font-semibold text-white">尚未绑定任何网盘</p>
            <p class="text-xs text-zinc-500 max-w-sm mx-auto">点击右上角「手机扫码绑定新网盘」，使用 115 或夸克手机 App 扫一扫即可免抓 Cookie 快速入库。</p>
          </div>

          <div v-else class="grid gap-3.5 sm:grid-cols-2">
            <article
              v-for="account in accounts"
              :key="account.id"
              class="rounded-2xl border border-white/[0.08] bg-zinc-900/60 p-5 flex items-center justify-between gap-4 shadow-sm"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <strong class="font-semibold text-white text-sm">{{ account.name }}</strong>
                  <Badge tone="muted" class="font-mono uppercase text-[10px]">{{ account.provider }}网盘</Badge>
                </div>
                <p class="mt-1.5 text-xs text-zinc-500 flex items-center gap-1">
                  <span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                  <span>凭据已通过 Fernet 工业级加密安全存储</span>
                </p>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <Button variant="outline" size="sm" class="h-8 text-xs" @click="testAccount(account.id)">
                  <RefreshCw class="mr-1 h-3 w-3" />
                  检测
                </Button>
                <Button variant="ghost" size="sm" class="h-8 w-8 p-0 text-rose-400 hover:text-rose-300" @click="removeAccount(account.id)">
                  <Trash2 class="h-3.5 w-3.5" />
                </Button>
              </div>
            </article>
          </div>
        </section>

        <!-- 2. 基础运行 (Basic) -->
        <section v-else-if="activeCat === 'basic'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">启用全自动追剧与监控总开关</p>
              <p class="text-zinc-500 mt-0.5">关闭后系统将暂停所有后台自动化找源与转存任务</p>
            </div>
            <Switch v-model="f.enabled" />
          </div>
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">片名智能自动订阅</p>
              <p class="text-zinc-500 mt-0.5">当频道抓取或手动转存时，若遇到未关注剧集自动加入追剧清单</p>
            </div>
            <Switch v-model="f.title_subscribe_enabled" />
          </div>
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">缺集全季自动补齐</p>
              <p class="text-zinc-500 mt-0.5">发现剧集更新时，不仅追更最新一集，同时自动补齐整季前面缺失的所有剧集</p>
            </div>
            <Switch v-model="f.subscribe_all_missing_seasons" />
          </div>
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">链接直达快速转存</p>
              <p class="text-zinc-500 mt-0.5">允许通过顶栏快捷入口直接粘贴分享链接快速提交转存</p>
            </div>
            <Switch v-model="f.direct_transfer_enabled" />
          </div>
        </section>

        <!-- 3. 转存搬运 (Transfer) -->
        <section v-else-if="activeCat === 'transfer'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">首选默认转存网盘</p>
              <p class="text-zinc-500 mt-0.5">当搜寻到多个网盘链接时，优先存入哪个网盘账号</p>
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
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">网盘转存保存根目录</p>
              <p class="text-zinc-500 mt-0.5">自动转存进网盘时存放的根文件夹路径</p>
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
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">启用跨网盘中继搬运 (Cross Transfer)</p>
              <p class="text-zinc-500 mt-0.5">例如将夸克分享资源自动下载并高速转存至你的 115 网盘</p>
            </div>
            <Switch v-model="f.cross_transfer_enabled" />
          </div>
          <div v-if="f.cross_transfer_enabled" class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">跨盘转存并行并发线程数</p>
              <p class="text-zinc-500 mt-0.5">中继搬运时同时进行下载和分片上传的连接数（默认 3）</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.cross_transfer_threads" type="number" min="1" max="8" />
              <span class="text-zinc-500 shrink-0">线程</span>
            </div>
          </div>
        </section>

        <!-- 4. 全盘整理 (Organize) -->
        <section v-else-if="activeCat === 'organize'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">网盘暂存区扫描目录</p>
              <p class="text-zinc-500 mt-0.5">手动或自动整理时读取散落视频的暂存文件夹</p>
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
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">字幕文件随视频自动归位</p>
              <p class="text-zinc-500 mt-0.5">整理视频时自动将同目录下的 .srt/.ass 等外挂字幕一并改名移动</p>
            </div>
            <Switch v-model="f.organize_include_subtitles" />
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
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
        </section>

        <!-- 5. 自动追剧 (Subscribe) -->
        <section v-else-if="activeCat === 'subscribe'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">启用榜单全自动订阅追剧</p>
              <p class="text-zinc-500 mt-0.5">自动从 TMDB / 豆瓣 / 蜜柑新番榜单发现热门好剧并自动加入追更</p>
            </div>
            <Switch v-model="f.auto_subscribe_enabled" />
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">检查最近多少天的更新</p>
              <p class="text-zinc-500 mt-0.5">剧集播出后，系统在多少天窗口内持续全网搜寻并补齐缺失集</p>
            </div>
            <div class="w-full sm:w-40 flex items-center gap-2">
              <Input v-model.number="f.window_days" type="number" min="1" max="365" />
              <span class="text-zinc-500 shrink-0">天</span>
            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">影视标题与简介语言</p>
              <p class="text-zinc-500 mt-0.5">自动获取剧集介绍与季集标题时的首选语言偏好</p>
            </div>
            <div class="w-full sm:w-56">
              <Select
                v-model="f.language"
                :options="[
                  { value: 'zh-CN', label: '简体中文 (zh-CN)' },
                  { value: 'en-US', label: 'English (en-US)' },
                ]"
              />
            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">榜单自动订阅最低评分门槛</p>
              <p class="text-zinc-500 mt-0.5">仅当全网影视评分大于等于此门槛时才自动订阅（默认 7.0 分）</p>
            </div>
            <div class="w-full sm:w-40 flex items-center gap-2">
              <Input v-model.number="f.auto_subscribe_min_vote" type="number" step="0.1" min="0" max="10" />
              <span class="text-zinc-500 shrink-0">分</span>
            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">TMDB API 官方密钥 (选填)</p>
              <p class="text-zinc-500 mt-0.5">用于渲染高清电影海报墙、剧情简介与热播榜（留空自动使用系统内置密钥）</p>
            </div>
            <div class="w-full sm:w-72">
              <Input v-model="f.tmdb_api_key" type="password" placeholder="留空使用系统预设密钥" />
            </div>
          </div>
        </section>

        <!-- 6. 每日签到 (Checkin) -->
        <section v-else-if="activeCat === 'checkin'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">网盘每日自动签到 Cron 表达式</p>
              <p class="text-zinc-500 mt-0.5">系统全自动为所有已绑定网盘签到获取空间积分的定时任务（默认每日凌晨 00:30）</p>
            </div>
            <div class="w-full sm:w-48">
              <Input v-model="f.checkin_cron" placeholder="30 0 * * *" />
            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">签到失败自动重试次数</p>
              <p class="text-zinc-500 mt-0.5">遇到网盘接口网络抖动时自动重新尝试的次数</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.checkin_retry_count" type="number" min="0" max="10" />
              <span class="text-zinc-500 shrink-0">次</span>
            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">115 签到模式</p>
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
        </section>

        <!-- 7. Telegram 监控 (TgMonitor) -->
        <section v-else-if="activeCat === 'tg'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">启用 Telegram 频道消息实时抓链监控</p>
              <p class="text-zinc-500 mt-0.5">使用你自己的 Telegram 会话监听频道消息并自动抓取网盘分享</p>
            </div>
            <Switch v-model="f.tg_monitor_enabled" />
          </div>
          <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">监控频道名单 (每行一个)</p>
              <p class="text-zinc-500 mt-0.5">输入公开频道用户名或私有频道名称（如 @Quark_Share_Group）</p>
            </div>
            <div class="w-full sm:w-80">
              <textarea
                v-model="f.tg_channels"
                rows="4"
                class="w-full rounded-xl border border-white/10 bg-zinc-900/60 p-3 font-mono text-xs text-white outline-none"
              />
            </div>
          </div>
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">识别到频道新影视后自动转存入库</p>
              <p class="text-zinc-500 mt-0.5">命中你的追剧订阅缺失集时，自动建立转存任务转入网盘</p>
            </div>
            <Switch v-model="f.tg_auto_transfer" />
          </div>
        </section>

        <!-- 8. STRM 与原画播放 (STRM) -->
        <section v-else-if="activeCat === 'strm'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">转存入库后自动生成 STRM 播放文件</p>
              <p class="text-zinc-500 mt-0.5">让 Emby / Jellyfin / 播放器无需下载实体大文件即可秒开播放网盘原画视频</p>
            </div>
            <Switch v-model="f.strm_generate_enabled" />
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
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
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">STRM 文件本地导出根目录</p>
              <p class="text-zinc-500 mt-0.5">系统把生成的 .strm 文件存放在服务器的物理路径</p>
            </div>
            <div class="w-full sm:w-64">
              <Input v-model="f.strm_root" placeholder="例如 /strm" />
            </div>
          </div>
          <div v-if="f.strm_mode === 'local_mount'" class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">网盘本地挂载根目录</p>
              <p class="text-zinc-500 mt-0.5">CloudDrive2 或 Alist 挂载到宿主机的文件目录</p>
            </div>
            <div class="w-full sm:w-64 flex gap-2">
              <Input v-model="f.local_mount_root" placeholder="例如 /mnt/quark" />
              <Button variant="outline" size="sm" @click="dirTarget = 'local_mount_root'; dirDialogOpen = true">浏览</Button>
            </div>
          </div>
        </section>

        <!-- 9. Emby 媒体服务器 (MediaServer) -->
        <section v-else-if="activeCat === 'emby'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">Emby / Jellyfin 服务器地址</p>
              <p class="text-zinc-500 mt-0.5">你的媒体服务器内网或公网访问 URL</p>
            </div>
            <div class="w-full sm:w-72">
              <Input v-model="f.emby_url" placeholder="http://172.18.0.x:8096" />
            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">API 密钥 (API Key)</p>
              <p class="text-zinc-500 mt-0.5">在 Emby 控制台「高级 → API 密钥」中生成的令牌</p>
            </div>
            <div class="w-full sm:w-72">
              <Input v-model="f.emby_api_key" type="password" placeholder="粘贴 Emby API 密钥" />
            </div>
          </div>
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">转存与整理成功后自动刷新 Emby 媒体库</p>
              <p class="text-zinc-500 mt-0.5">新剧入库后立即命令 Emby 扫描更新，客户端立即可见海报与正片</p>
            </div>
            <Switch v-model="f.emby_refresh_enabled" />
          </div>
        </section>

        <!-- 10. 搜索找源 15 源自描述面板 (Sources) -->
        <section v-else-if="activeCat === 'sources'" class="space-y-4">
          <div class="grid gap-4 lg:grid-cols-[200px_minmax(0,1fr)]">
            <!-- 15 源列表 -->
            <nav class="space-y-1 rounded-2xl border border-white/[0.08] bg-zinc-950/60 p-2 max-h-[600px] overflow-y-auto">
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

            <!-- 选中源专属表单 -->
            <div v-if="currentSource" class="space-y-4 min-w-0">
              <div class="flex items-center justify-between rounded-2xl border border-white/[0.08] bg-zinc-900/60 p-4">
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

              <div v-for="(group, gIndex) in currentSource.groups" :key="gIndex" class="rounded-2xl border border-white/[0.08] bg-zinc-900/60 p-5 space-y-4">
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
        </section>

        <!-- 11. 画质洗版升级 (Upgrade) -->
        <section v-else-if="activeCat === 'upgrade'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex items-center justify-between py-4">
            <div>
              <p class="font-medium text-white text-sm">启用网盘自动画质升级 (洗版)</p>
              <p class="text-zinc-500 mt-0.5">当后续搜寻到更高规格的画质时，自动替换网盘中的低画质旧版</p>
            </div>
            <Switch v-model="f.enable_cloud_upgrade" />
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
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
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">单集视频最小体积门槛 (防假种)</p>
              <p class="text-zinc-500 mt-0.5">低于此体积的单集视频将被当成预告/花絮/假种直接丢弃（默认 100MB，字幕不受限制）</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.min_episode_size_mb" type="number" min="10" max="2000" />
              <span class="text-zinc-500 shrink-0">MB</span>
            </div>
          </div>
        </section>

        <!-- 12. 消息通知 (Notify) -->
        <section v-else-if="activeCat === 'notify'" class="space-y-4 text-xs">
          <!-- 飞书 -->
          <div class="rounded-2xl border border-white/[0.08] bg-zinc-900/60 p-5 space-y-3">
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
          <div class="rounded-2xl border border-white/[0.08] bg-zinc-900/60 p-5 space-y-3">
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

          <!-- 通用 Webhook -->
          <div class="rounded-2xl border border-white/[0.08] bg-zinc-900/60 p-5 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <strong class="text-sm font-semibold text-white">通用自定义 Webhook</strong>
                <p class="text-zinc-500 mt-0.5">发送标准 JSON 事件到你的私有接口或 HomeAssistant</p>
              </div>
              <Switch v-model="f.webhook_enabled" />
            </div>
            <div v-if="f.webhook_enabled" class="pt-2">
              <label class="text-zinc-400">接口 URL</label>
              <Input v-model="f.webhook_url" class="mt-1" placeholder="https://api.yourdomain.com/csx-webhook" />
            </div>
          </div>
        </section>

        <!-- 13. 高级运维 (Advanced) -->
        <section v-else-if="activeCat === 'advanced'" class="divide-y divide-white/[0.06] text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
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
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <p class="font-medium text-white text-sm">转存任务最大并发上限</p>
              <p class="text-zinc-500 mt-0.5">同时进行的网盘转存与整理任务的最大线程数（默认 8）</p>
            </div>
            <div class="w-full sm:w-36 flex items-center gap-2">
              <Input v-model.number="f.max_workers" type="number" min="1" max="32" />
              <span class="text-zinc-500 shrink-0">并发</span>
            </div>
          </div>
        </section>
      </main>
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
