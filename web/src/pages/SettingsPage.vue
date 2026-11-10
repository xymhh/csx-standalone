<script setup lang="ts">
import { computed, onMounted, ref, watch, type Component } from 'vue'
import {
  Bell,
  Check,
  ChevronDown,
  ChevronRight,
  Anchor,
  Clapperboard,
  Cloud,
  Database,
  Dices,
  FileText,
  Globe,
  Link2,
  MonitorPlay,
  MessagesSquare,
  Network,
  Radar,
  Satellite,
  Snail,
  Cpu,
  Film,
  Flame,
  FolderOpen,
  FolderSync,
  HardDrive,
  Layers,
  List,
  ListOrdered,
  PlaySquare,
  Plus,
  QrCode,
  RotateCcw,
  Radio,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Send,
  Sliders,
  Sparkles,
  Sprout,
  Trash2,
  Tv,
  Workflow,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DirectorySelectDialog from '@/components/dialogs/DirectorySelectDialog.vue'
import AccountCard from '@/components/config/AccountCard.vue'
import SearchSourceField from '@/components/config/SearchSourceField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useToast } from '@/composables/useToast'
import {
  accountsApi,
  autoSearchApi,
  crossTransferApi,
  namingApi,
  searchSourcesApi,
  settingsApi,
  telegramApi,
  type Account,
  type QrcodeCheckResponse,
  type QrcodeStartResponse,
  type NamingPreview,
  type NamingVariable,
  type SearchSourceSchema,
  type SearchSourceTest,
  type SourceMeta,
  type TgClientStatus,
  type CrossTransferSettings,
  type AutoSearchSettings,
} from '@/lib/api'

const navItems = [
  { value: 'accounts', label: '网盘账号' },
  { value: 'drama', label: '追剧与规则' },
  { value: 'charts', label: '榜单自动订阅' },
  { value: 'sources', label: '搜索渠道 (15)' },
  { value: 'playback', label: '播放与整理' },
  { value: 'system', label: '通知与高级' },
]

const currentNav = ref('accounts')
const { toast } = useToast()

const autoCfg = ref<AutoSearchSettings>({
  enabled: false,
  interval_hours: 6,
  auto_transfer: true,
  max_per_round: 10,
  per_subscription_limit: 20,
})
const autoSaving = ref(false)
const autoRunning = ref(false)

async function loadAutoSearch() {
  try {
    autoCfg.value = await autoSearchApi.settings()
  } catch {
    /* 老后端无此接口时静默 */
  }
}

async function saveAutoSearch() {
  autoSaving.value = true
  try {
    autoCfg.value = await autoSearchApi.save({
      enabled: autoCfg.value.enabled,
      interval_hours: Number(autoCfg.value.interval_hours),
      auto_transfer: autoCfg.value.auto_transfer,
      max_per_round: Number(autoCfg.value.max_per_round),
      per_subscription_limit: Number(autoCfg.value.per_subscription_limit),
    })
    toast(autoCfg.value.enabled ? '自动搜源已开启' : '自动搜源已关闭', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败', 'error')
  } finally {
    autoSaving.value = false
  }
}

async function runAutoSearchNow() {
  autoRunning.value = true
  try {
    const response = await autoSearchApi.run({ force: true })
    const result = response.result
    const count = result.total ?? result.processed?.length ?? 0
    const taskCount = Array.isArray(result.tasks) ? result.tasks.length : Number(result.tasks ?? 0)
    toast(`已跑 ${count} 部订阅：新候选 ${result.candidates ?? 0} 个，新建转存 ${taskCount} 个`, 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '触发失败', 'error')
  } finally {
    autoRunning.value = false
  }
}

const accounts = ref<Account[]>([])
const loading = ref(false)
const saving = ref(false)
const crossSaving = ref(false)
const crossCfg = ref<CrossTransferSettings>({
  enabled: true,
  library_drive: '',
  download_threads: 5,
  max_concurrent: 2,
  direct_stream: true,
  cache_dir: '/cache',
  cache_free_gb: 0,
  drive_options: [],
})

// 网盘新增输入框状态
const newAccountProvider = ref<'115' | 'quark'>('115')
const newAccountName = ref('')
const newAccountCookie = ref('')
const addingAccount = ref(false)

// 高级参数折叠状态
const showAdvDrama = ref(false)

// ── 媒体二级分类（对齐 MoviePilot 的 category.yaml） ──
type CategoryRule = { name: string; conditions: Record<string, string> }
const CATEGORY_FIELDS = [
  { value: 'genre_ids', label: '内容类型' },
  { value: 'original_language', label: '语种' },
  { value: 'production_countries', label: '制片国家' },
  { value: 'origin_country', label: '来源国家' },
  { value: 'release_year', label: '发行年份' },
]
const CATEGORY_DEFAULT_MOVIE: CategoryRule[] = [
  { name: '动画电影', conditions: { genre_ids: '16' } },
  { name: '华语电影', conditions: { original_language: 'zh,cn,bo,za' } },
  { name: '外语电影', conditions: {} },
]
const CATEGORY_DEFAULT_TV: CategoryRule[] = [
  { name: '国漫', conditions: { genre_ids: '16', origin_country: 'CN,TW,HK' } },
  { name: '日番', conditions: { genre_ids: '16', origin_country: 'JP' } },
  { name: '纪录片', conditions: { genre_ids: '99' } },
  { name: '儿童', conditions: { genre_ids: '10762' } },
  { name: '综艺', conditions: { genre_ids: '10764,10767' } },
  { name: '国产剧', conditions: { origin_country: 'CN,TW,HK' } },
  { name: '欧美剧', conditions: { origin_country: 'US,FR,GB,DE,ES,IT,NL,PT,RU,UK' } },
  { name: '日韩剧', conditions: { origin_country: 'JP,KP,KR,TH,IN,SG' } },
  { name: '未分类', conditions: {} },
]
const categoryConfig = ref<{ enabled: boolean; movie: CategoryRule[]; tv: CategoryRule[] }>({
  enabled: true,
  movie: JSON.parse(JSON.stringify(CATEGORY_DEFAULT_MOVIE)),
  tv: JSON.parse(JSON.stringify(CATEGORY_DEFAULT_TV)),
})
const categoryTab = ref<'movie' | 'tv'>('movie')
const CATEGORY_TABS = [
  { value: 'movie' as const, label: '电影' },
  { value: 'tv' as const, label: '剧集' },
]

function categoryRules(): CategoryRule[] {
  return categoryConfig.value[categoryTab.value]
}

function addCategoryRule() {
  categoryRules().push({ name: '', conditions: {} })
}

function removeCategoryRule(index: number) {
  categoryRules().splice(index, 1)
}

function moveCategoryRule(index: number, delta: number) {
  const rules = categoryRules()
  const next = index + delta
  if (next < 0 || next >= rules.length) return
  const [item] = rules.splice(index, 1)
  rules.splice(next, 0, item)
}

function addCategoryCondition(rule: CategoryRule) {
  const used = new Set(Object.keys(rule.conditions))
  const field = CATEGORY_FIELDS.find((item) => !used.has(item.value))?.value || 'genre_ids'
  rule.conditions[field] = ''
}

function removeCategoryCondition(rule: CategoryRule, key: string) {
  delete rule.conditions[key]
}

function onCategoryConditionKey(rule: CategoryRule, oldKey: string, event: Event) {
  const target = event.target as HTMLSelectElement | null
  const nextKey = target?.value || oldKey
  if (nextKey === oldKey) return
  const value = rule.conditions[oldKey] ?? ''
  delete rule.conditions[oldKey]
  rule.conditions[nextKey] = value
}

function resetCategoryRules() {
  const source = categoryTab.value === 'movie' ? CATEGORY_DEFAULT_MOVIE : CATEGORY_DEFAULT_TV
  categoryConfig.value[categoryTab.value] = JSON.parse(JSON.stringify(source))
}

// ── 通知消息模板 ──
const NOTIFY_EVENT_LABELS: Record<string, string> = {
  transfer_success: '转存成功',
  upgrade_success: '洗版成功',
  task_dead_letter: '转存失败',
}
const NOTIFY_VARIABLES: Record<string, string[]> = {
  transfer_success: ['title', 'season', 'episode', 'quality', 'duration', 'now'],
  upgrade_success: ['title', 'season', 'episode', 'from_quality', 'to_quality', 'now'],
  task_dead_letter: ['title', 'error', 'share_url', 'now'],
}
const NOTIFY_DEFAULT_TEMPLATES: Record<string, string> = {
  transfer_success:
    '✅ 转存成功\n────────────────\n🎬 {{ title }}{% if season %}  S{{ \'%02d\'|format(season|int) }}E{{ \'%02d\'|format(episode|int) }}{% endif %}\n{% if quality %}💎 画质：{{ quality }}\n{% endif %}{% if duration %}⏱ 时长：{{ duration }}\n{% endif %}🕒 {{ now }}',
  upgrade_success:
    '🔄 洗版成功\n────────────────\n🎬 {{ title }}{% if season %}  S{{ \'%02d\'|format(season|int) }}E{{ \'%02d\'|format(episode|int) }}{% endif %}\n{% if from_quality %}📉 原画质：{{ from_quality }}\n{% endif %}{% if to_quality %}📈 新画质：{{ to_quality }}\n{% endif %}🕒 {{ now }}',
  task_dead_letter:
    '❌ 转存失败\n────────────────\n{% if title %}🎬 {{ title }}\n{% endif %}📄 原因：{{ error }}\n{% if share_url %}🔗 分享：{{ share_url }}\n{% endif %}🕒 {{ now }}',
}
const notifyTemplates = ref<Record<string, string>>({ ...NOTIFY_DEFAULT_TEMPLATES })

function resetNotifyTemplate(event: string) {
  notifyTemplates.value[event] = NOTIFY_DEFAULT_TEMPLATES[event] || ''
}

function insertNotifyVariable(event: string, variable: string) {
  const current = notifyTemplates.value[event] || ''
  notifyTemplates.value[event] = `${current}{{ ${variable} }}`
}

// TG 频道客户端状态
const tgClientStatus = ref<TgClientStatus | null>(null)
const tgScanning = ref(false)
const tgScanSummary = ref('')

// 重命名模板（MoviePilot 方案）
const naming = ref({ movie_format: '', tv_format: '', variety_format: '' })
const namingDefaults = ref({ movie_format: '', tv_format: '', variety_format: '' })
const namingVariables = ref<NamingVariable[]>([])
const namingPreview = ref<Record<'movie' | 'tv', NamingPreview>>({
  movie: { valid: true, message: '', relative_path: '' },
  tv: { valid: true, message: '', relative_path: '' },
})
const namingError = ref('')
const activeTemplate = ref<'movie' | 'tv'>('movie')
const movieTemplateEl = ref<HTMLTextAreaElement | null>(null)
const tvTemplateEl = ref<HTMLTextAreaElement | null>(null)
let namingTimer = 0

// 榜单子 Tab
const chartTab = ref<'global' | 'douban' | 'tmdb' | 'bangumi' | 'mikan'>('global')

// 15 个搜索源自描述状态
const sourceSchemas = ref<SearchSourceSchema[]>([])
const sourceValues = ref<Record<string, Record<string, any>>>({})
const selectedSourceId = ref('general')
const sourceTest = ref<SearchSourceTest | null>(null)
const sourceTestRunning = ref(false)
const sourceMeta = ref<SourceMeta>({ accounts: {}, options: {} })
const sourceMetaLoading = ref(false)
const sourceAccountRefreshing = ref(false)
const sourceOauthBusy = ref<'' | 'start' | 'exchange'>('')
const sourceOauthCallback = ref('')
const pansouMeta = ref<{ channels: { title: string; value: string }[]; plugins: { title: string; value: string }[]; status?: string }>({ channels: [], plugins: [] })
const searchProxy = ref('')
const searchProxySaving = ref(false)
const proxyUsername = ref('')
const proxyPassword = ref('')
const sourceOrder = ref<string[]>([])
const resourceOrder = ref<string[]>([])
const magnetTemplate = ref('')
const sourceOptions = ref<{ id: string; name: string }[]>([])
const resourceOptions = ref<{ id: string; name: string }[]>([])
const orderPicker = ref<'' | 'source' | 'resource'>('')

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
  strm_public_base_url: '',
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
  tg_api_id: '',
  tg_api_hash: '',
  tg_session: '',
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
const dirTarget = ref('account_path')

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
      selectedSourceId.value = 'general'
    }
    void ensureSourceAccount(selectedSourceId.value)
  } catch {}
}

async function loadAllSettings() {
  loading.value = true
  try {
    const [b, t, s, n, a, c] = await Promise.all([
      settingsApi.getSection('baseline'),
      settingsApi.getSection('transfer'),
      settingsApi.getSection('strm'),
      settingsApi.getSection('notify'),
      settingsApi.getSection('advanced'),
      settingsApi.getSection('category'),
    ])
    Object.assign(f.value, b, t, s, n, a)
    const strmSection = s as { mode?: string; public_base_url?: string }
    if (strmSection.mode) f.value.strm_mode = strmSection.mode
    if (strmSection.public_base_url) {
      f.value.strm_public_base_url = String(strmSection.public_base_url)
    }
    const channels = (n as { channels?: Record<string, Record<string, unknown>> }).channels || {}
    const feishu = channels.feishu || {}
    const telegram = channels.telegram || {}
    f.value.feishu_enabled = Boolean(feishu.enabled ?? f.value.feishu_enabled)
    f.value.feishu_url = String(feishu.webhook_url ?? f.value.feishu_url)
    f.value.telegram_enabled = Boolean(telegram.enabled ?? f.value.telegram_enabled)
    f.value.telegram_token = String(telegram.bot_token ?? f.value.telegram_token)
    f.value.telegram_chat_id = String(telegram.chat_id ?? f.value.telegram_chat_id)

    const templates = (n as { templates?: Record<string, string> }).templates
    if (templates && typeof templates === 'object') {
      notifyTemplates.value = { ...NOTIFY_DEFAULT_TEMPLATES, ...templates }
    }

    const category = c as { enabled?: boolean; movie?: CategoryRule[]; tv?: CategoryRule[] }
    if (typeof category.enabled === 'boolean') categoryConfig.value.enabled = category.enabled
    if (Array.isArray(category.movie)) categoryConfig.value.movie = category.movie
    if (Array.isArray(category.tv)) categoryConfig.value.tv = category.tv
  } catch (cause) {
    console.error(cause)
  } finally {
    loading.value = false
  }
}

async function loadCrossSettings() {
  try {
    crossCfg.value = await crossTransferApi.get()
  } catch (cause) {
    console.error(cause)
  }
}

async function saveCrossSettings() {
  crossSaving.value = true
  try {
    crossCfg.value = await crossTransferApi.save({
      enabled: crossCfg.value.enabled,
      library_drive: crossCfg.value.library_drive,
      download_threads: Number(crossCfg.value.download_threads),
      max_concurrent: Number(crossCfg.value.max_concurrent),
      direct_stream: crossCfg.value.direct_stream,
    })
    toast('跨盘转存设置已保存', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败', 'error')
  } finally {
    crossSaving.value = false
  }
}

async function loadNaming() {
  try {
    const data = await namingApi.get()
    naming.value = {
      movie_format: data.movie_format,
      tv_format: data.tv_format,
      variety_format: data.variety_format,
    }
    namingDefaults.value = data.defaults
    namingVariables.value = data.variables
    await refreshNamingPreview()
  } catch (cause) {
    console.error(cause)
  }
}

async function refreshNamingPreview() {
  try {
    const [movie, tv] = await Promise.all([
      namingApi.preview({
        media_type: 'movie',
        title: '示例电影',
        year: 2024,
        extension: 'mkv',
        quality_bucket: '1080p',
        template: naming.value.movie_format,
      }),
      namingApi.preview({
        media_type: 'tv',
        title: '示例剧集',
        year: 2024,
        season: 1,
        episode: 1,
        extension: 'mkv',
        quality_bucket: '4k',
        template: naming.value.tv_format,
      }),
    ])
    namingPreview.value = { movie, tv }
  } catch (cause) {
    console.error(cause)
  }
}

function scheduleNamingPreview() {
  if (namingTimer) window.clearTimeout(namingTimer)
  namingTimer = window.setTimeout(() => {
    void refreshNamingPreview()
  }, 300)
}

function restoreNamingDefaults() {
  naming.value = { ...namingDefaults.value }
  void refreshNamingPreview()
}

function insertNamingVariable(name: string) {
  const key = activeTemplate.value === 'tv' ? 'tv_format' : 'movie_format'
  const el = activeTemplate.value === 'tv' ? tvTemplateEl.value : movieTemplateEl.value
  const token = `{{${name}}}`
  const current = naming.value[key]
  const start = el?.selectionStart ?? current.length
  const end = el?.selectionEnd ?? current.length
  naming.value[key] = current.slice(0, start) + token + current.slice(end)
  scheduleNamingPreview()
  requestAnimationFrame(() => {
    el?.focus()
    el?.setSelectionRange(start + token.length, start + token.length)
  })
}

function formatTgTimestamp(value?: string | null) {
  if (!value) return '暂无'
  const time = new Date(value)
  if (Number.isNaN(time.getTime())) return value
  return time.toLocaleString('zh-CN', { hour12: false })
}

const tgStatusText = computed(() => {
  const status = tgClientStatus.value
  if (!status) return '状态读取中'
  if (!status.configured) return '未配置'
  if (status.last_error) return '连接异常'
  if (!status.enabled) return '监控已关闭'
  return status.running ? '已连接' : '等待后台任务'
})

const tgStatusTone = computed<'good' | 'warn' | 'bad' | 'muted'>(() => {
  const status = tgClientStatus.value
  if (!status || !status.configured) return 'muted'
  if (status.last_error) return 'bad'
  if (!status.enabled || !status.running) return 'warn'
  return 'good'
})

async function loadTgClientStatus() {
  try {
    tgClientStatus.value = await telegramApi.clientStatus()
  } catch {
    tgClientStatus.value = null
  }
}

async function scanTgNow() {
  tgScanning.value = true
  tgScanSummary.value = ''
  try {
    const result = await telegramApi.clientScan()
    const errorText = result.errors.length ? `，${result.errors.length} 个频道异常` : ''
    tgScanSummary.value = `本次扫描 ${result.scanned_channels} 个频道，发现 ${result.new_messages} 条新消息，入库 ${result.ingested} 条${errorText}`
    toast('Telegram 频道扫描完成', 'success')
    await loadTgClientStatus()
  } catch (cause) {
    tgScanSummary.value = cause instanceof Error ? cause.message : '扫描失败'
    toast(tgScanSummary.value, 'error')
  } finally {
    tgScanning.value = false
  }
}

onMounted(() => {
  void loadAccounts()
  void loadAllSettings()
  void loadSources()
  void loadSourceMeta()
  void loadSearchProxy()
  void loadNaming()
  void loadCrossSettings()
  void loadTgClientStatus()
  void loadAutoSearch()
})

async function saveAll() {
  saving.value = true
  try {
    if (currentNav.value === 'sources') {
      await searchSourcesApi.save(sourceValues.value)
      toast('15 个搜索渠道设置已保存', 'success')
      void loadSourceMeta()
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
      type_folder_enabled: f.value.type_folder_enabled,
      type_folder_movie: f.value.type_folder_movie,
      type_folder_tv: f.value.type_folder_tv,
      enable_cloud_upgrade: f.value.enable_cloud_upgrade,
      enable_pt_upgrade: f.value.enable_pt_upgrade,
      min_quality: f.value.min_quality,
      min_episode_size_mb: Number(f.value.min_episode_size_mb),
      organize_source_path: f.value.organize_source_path,
      organize_include_subtitles: f.value.organize_include_subtitles,
      organize_conflict_policy: f.value.organize_conflict_policy,
    }

    const pStrm = {
      strm_generate_enabled: f.value.strm_generate_enabled,
      mode: f.value.strm_mode,
      strm_root: f.value.strm_root,
      public_base_url: f.value.strm_public_base_url,
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
      templates: { ...notifyTemplates.value },
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
      tg_api_id: f.value.tg_api_id,
      tg_api_hash: f.value.tg_api_hash,
      tg_session: f.value.tg_session,
    }

    namingError.value = ''
    const namingSave = namingApi
      .update({
        movie_format: naming.value.movie_format,
        tv_format: naming.value.tv_format,
        variety_format: naming.value.variety_format,
      })
      .then((data) => {
        naming.value = {
          movie_format: data.movie_format,
          tv_format: data.tv_format,
          variety_format: data.variety_format,
        }
      })
      .catch((cause) => {
        namingError.value = cause instanceof Error ? cause.message : '重命名模板未保存'
      })

    await Promise.all([
      settingsApi.updateSection('baseline', pBaseline),
      settingsApi.updateSection('transfer', pTransfer),
      settingsApi.updateSection('strm', pStrm),
      settingsApi.updateSection('notify', pNotify),
      settingsApi.updateSection('advanced', pAdv),
      settingsApi.updateSection('category', {
        enabled: categoryConfig.value.enabled,
        movie: categoryConfig.value.movie,
        tv: categoryConfig.value.tv,
      }),
      namingSave,
    ])

    if (namingError.value) {
      toast(`其余设置已保存；重命名模板未保存：${namingError.value}`, 'error')
    } else {
      toast('设置保存成功', 'success')
    }
    void loadTgClientStatus()
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

const targetAccountForBrowse = ref<Account | null>(null)
const targetPathType = ref<'transfer' | 'media'>('transfer')

function openAccountDirBrowse(acc: Account, target: 'transfer' | 'media') {
  targetAccountForBrowse.value = acc
  targetPathType.value = target
  dirTarget.value = 'account_path'
  dirDialogOpen.value = true
}

async function handleAccountDirSelect(path: string) {
  if (dirTarget.value === 'account_path' && targetAccountForBrowse.value) {
    const acc = targetAccountForBrowse.value
    const updatePayload = targetPathType.value === 'transfer'
      ? { transfer_path: path }
      : { media_path: path }
    try {
      await accountsApi.update(acc.id, updatePayload)
      if (targetPathType.value === 'transfer') acc.transfer_path = path
      else acc.media_path = path
      toast(`已更新 ${acc.name} 的${targetPathType.value === 'transfer' ? '转存路径' : '媒体库路径'}`, 'success')
    } catch (cause) {
      toast(cause instanceof Error ? cause.message : '更新目录失败', 'error')
    }
  } else if (dirTarget.value === 'organize_source_path') {
    f.value.organize_source_path = path
  } else if (dirTarget.value === 'local_mount_root') {
    f.value.local_mount_root = path
  }
  dirDialogOpen.value = false
}

const accountRefreshing = ref<Record<number, boolean>>({})

async function testAccount(id: number) {
  accountRefreshing.value[id] = true
  try {
    const res = await accountsApi.test(id)
    toast(`${res.provider}网盘：${res.message}`, res.valid ? 'success' : 'error')
    if (res.info) {
      const target = accounts.value.find((a) => a.id === id)
      if (target) {
        target.info = { ...(target.info || {}), ...res.info }
      }
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
const currentAccount = computed(() => sourceMeta.value.accounts[selectedSourceId.value] || null)
const sourceMenuOpen = ref(false)
const collapsedGroups = ref<Record<string, boolean>>({})

const SOURCE_ICONS: Record<string, Component> = {
  pansou: Radar,
  hdhive: Dices,
  hdhaven: Clapperboard,
  dian115: Film,
  juying: MonitorPlay,
  woniu: Snail,
  pinglian: Link2,
  mikan: Sparkles,
  animegarden: Sprout,
  seedhub: Sprout,
  tgchannels: MessagesSquare,
  piratebay: Anchor,
  pianku: Database,
  uindex: Globe,
  online_docs: FileText,
}

function sourceIcon(sourceId: string) {
  return SOURCE_ICONS[sourceId] || Satellite
}

const visibleSourceTabs = computed(() => sourceSchemas.value.slice(0, 4))
const hiddenSourceTabs = computed(() => sourceSchemas.value.slice(4))

function pickSource(sourceId: string) {
  selectedSourceId.value = sourceId
  sourceTest.value = null
  sourceMenuOpen.value = false
}

function groupTitle(group: { title?: string }): string {
  const title = String(group.title || '').trim()
  if (!title) return '参数配置'
  if (title === currentSource.value?.name) return '账号与连接'
  return title
}

function toggleGroup(key: string) {
  collapsedGroups.value = { ...collapsedGroups.value, [key]: !collapsedGroups.value[key] }
}

function isGroupCollapsed(key: string): boolean {
  return Boolean(collapsedGroups.value[key])
}

function restoreSourceDefaults() {
  const source = currentSource.value
  if (!source) return
  const values = { ...(sourceValues.value[source.id] || {}) }
  for (const group of source.groups) {
    for (const field of group.fields) {
      if (field.default !== undefined && field.key && !['account', 'test'].some((t) => (field.type || '').includes(t))) {
        values[field.key] = field.default
      }
    }
  }
  sourceValues.value[source.id] = values
  toast(`${source.name} 已恢复为默认值，记得点「保存配置」`, 'success')
}

function accountPoints(card: { points?: unknown } | null): string {
  const points = card?.points
  const raw = points && typeof points === 'object' ? (points as { available?: unknown }).available : points
  const value = Number(raw)
  if (!Number.isFinite(value)) return ''
  return value.toLocaleString('zh-CN')
}

function accountPointsLabel(card: { points?: unknown } | null): string {
  const points = card?.points
  return points && typeof points === 'object' ? String((points as { label?: string }).label || '可用积分') : '可用积分'
}

async function loadSearchProxy() {
  try {
    const result = await searchSourcesApi.getGlobal()
    searchProxy.value = result.search_proxy || ''
    proxyUsername.value = result.search_proxy_username || ''
    proxyPassword.value = result.search_proxy_password || ''
    sourceOrder.value = [...(result.search_source_order || [])]
    resourceOrder.value = [...(result.resource_type_order || [])]
    magnetTemplate.value = result.magnet_metadata_url_template || ''
    sourceOptions.value = result.source_options || []
    resourceOptions.value = result.resource_options || []
  } catch {
    // 忽略
  }
}

function optionName(options: { id: string; name: string }[], id: string): string {
  return options.find((item) => item.id === id)?.name || id
}

function orderCandidates(kind: 'source' | 'resource') {
  const options = kind === 'source' ? sourceOptions.value : resourceOptions.value
  const chosen = kind === 'source' ? sourceOrder.value : resourceOrder.value
  return options.filter((item) => !chosen.includes(item.id))
}

function addOrderItem(kind: 'source' | 'resource', id: string) {
  if (kind === 'source') sourceOrder.value = [...sourceOrder.value, id]
  else resourceOrder.value = [...resourceOrder.value, id]
  orderPicker.value = ''
}

function removeOrderItem(kind: 'source' | 'resource', id: string) {
  if (kind === 'source') sourceOrder.value = sourceOrder.value.filter((item) => item !== id)
  else resourceOrder.value = resourceOrder.value.filter((item) => item !== id)
}

function moveOrderItem(kind: 'source' | 'resource', id: string, delta: number) {
  const list = kind === 'source' ? [...sourceOrder.value] : [...resourceOrder.value]
  const index = list.indexOf(id)
  const target = index + delta
  if (index < 0 || target < 0 || target >= list.length) return
  list.splice(index, 1)
  list.splice(target, 0, id)
  if (kind === 'source') sourceOrder.value = list
  else resourceOrder.value = list
}

async function saveGlobalSettings() {
  if (magnetTemplate.value && !magnetTemplate.value.includes('{info_hash}')) {
    toast('Magnet 元数据地址模板必须包含 {info_hash}', 'error')
    return
  }
  searchProxySaving.value = true
  try {
    const result = await searchSourcesApi.saveGlobal({
      search_proxy: searchProxy.value.trim(),
      search_proxy_username: proxyUsername.value.trim(),
      search_proxy_password: proxyPassword.value,
      search_source_order: sourceOrder.value,
      resource_type_order: resourceOrder.value,
      magnet_metadata_url_template: magnetTemplate.value.trim(),
    })
    searchProxy.value = result.search_proxy || ''
    proxyUsername.value = result.search_proxy_username || ''
    proxyPassword.value = result.search_proxy_password || ''
    sourceOrder.value = [...(result.search_source_order || [])]
    resourceOrder.value = [...(result.resource_type_order || [])]
    magnetTemplate.value = result.magnet_metadata_url_template || ''
    toast('通用设置已保存', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存通用设置失败', 'error')
  } finally {
    searchProxySaving.value = false
  }
}

async function saveSearchProxy() {
  searchProxySaving.value = true
  try {
    const result = await searchSourcesApi.saveGlobal({ search_proxy: searchProxy.value.trim() })
    searchProxy.value = result.search_proxy
    toast(result.search_proxy ? '搜索代理已保存' : '搜索代理已清空', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存搜索代理失败', 'error')
  } finally {
    searchProxySaving.value = false
  }
}

async function loadSourceMeta() {
  sourceMetaLoading.value = true
  try {
    const meta = await searchSourcesApi.meta()
    sourceMeta.value = meta
    const pansou = meta.options?.pansou || {}
    pansouMeta.value = {
      channels: pansou.channels || [],
      plugins: pansou.plugins || [],
      status: pansou.status,
    }
  } catch {
    // 元数据失败不阻塞设置页
  } finally {
    sourceMetaLoading.value = false
  }
}

function sourceFieldVisible(field: { show?: string }) {
  const expr = String(field.show || '').trim()
  if (!expr) return true
  const match = expr.match(/^config\.([A-Za-z0-9_]+)\s*(?:===\s*['"]([^'"]*)['"])?$/)
  if (!match) return true
  const values = sourceValues.value[currentSource.value?.id || '']
  const value = values?.[match[1]]
  if (match[2] === undefined) return Boolean(value)
  return String(value) === match[2]
}

function sourceFieldCols(field: { cols?: number }) {
  const cols = Number(field.cols || 12)
  if (cols <= 3) return 'col-span-12 sm:col-span-3'
  if (cols === 4) return 'col-span-12 sm:col-span-4'
  if (cols === 6) return 'col-span-12 sm:col-span-6'
  if (cols === 8) return 'col-span-12 sm:col-span-8'
  return 'col-span-12'
}

function sourceFieldOptions(field: {
  dynamicOptions?: { scope?: string; key?: string }
  items?: { title?: string; label?: string; value: string | number }[]
}) {
  const dynamic = field.dynamicOptions
  if (dynamic?.scope === 'pansou') {
    return dynamic.key === 'plugins' ? pansouMeta.value.plugins : pansouMeta.value.channels
  }
  return (field.items || []).map((item) => ({
    title: String(item.title ?? item.label ?? item.value),
    value: String(item.value),
  }))
}

async function refreshSourceOptions(field: { key?: string; dynamicOptions?: { scope?: string; key?: string } }) {
  const dynamic = field.dynamicOptions
  if (!dynamic?.scope || !dynamic.key) return
  try {
    const result = await searchSourcesApi.refreshOptions(dynamic.scope, dynamic.key)
    const items = result.items || []
    if (dynamic.scope === 'pansou' && dynamic.key === 'plugins') pansouMeta.value.plugins = items
    else if (dynamic.scope === 'pansou') pansouMeta.value.channels = items
    toast(`已刷新 ${items.length} 个可选项`, items.length ? 'success' : 'error')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '刷新选项失败', 'error')
  }
}

const sourceAccountPending = ref<Set<string>>(new Set())

// 进入某个渠道时静默拉一次账户信息，卡片才能一进页面就显示
async function ensureSourceAccount(sourceId: string) {
  if (!sourceId || sourceId === 'general') return
  if (sourceMeta.value.accounts[sourceId]) return
  if (sourceAccountPending.value.has(sourceId)) return
  const pending = new Set(sourceAccountPending.value)
  pending.add(sourceId)
  sourceAccountPending.value = pending
  try {
    const card = await searchSourcesApi.refreshAccount(sourceId)
    sourceMeta.value.accounts = { ...sourceMeta.value.accounts, [sourceId]: card }
  } catch {
    // 静默失败：卡片位置会提示未连接，不打扰用户
  } finally {
    const next = new Set(sourceAccountPending.value)
    next.delete(sourceId)
    sourceAccountPending.value = next
  }
}

watch([selectedSourceId, currentNav], () => {
  if (currentNav.value === 'sources') void ensureSourceAccount(selectedSourceId.value)
})

async function refreshSourceAccount(sourceId: string) {
  sourceAccountRefreshing.value = true
  try {
    const card = await searchSourcesApi.refreshAccount(sourceId)
    sourceMeta.value.accounts = { ...sourceMeta.value.accounts, [sourceId]: card }
    if (card.connected) toast(`已读取 ${card.name || '账户'} 信息`, 'success')
    else toast(card.error || '账户信息读取失败', 'error')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '账户信息读取失败', 'error')
  } finally {
    sourceAccountRefreshing.value = false
  }
}

function hdhivePayload() {
  const values = sourceValues.value.hdhive || {}
  return {
    client_id: String(values.hdhive_client_id || '').trim(),
    redirect_uri: String(values.hdhive_redirect_uri || '').trim(),
    response_mode: String(values.hdhive_response_mode || 'redirect'),
    scope: 'query unlock write',
  }
}

async function startHdhiveOauth() {
  sourceOauthBusy.value = 'start'
  try {
    const payload = hdhivePayload()
    const result = await searchSourcesApi.hdhiveOauthStart(payload)
    sourceOauthCallback.value = ''
    window.open(result.authorize_url, '_blank', 'noopener')
    toast('已打开授权页，完成后把回调 URL 粘贴回来', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '发起授权失败', 'error')
  } finally {
    sourceOauthBusy.value = ''
  }
}

async function exchangeHdhiveOauth() {
  sourceOauthBusy.value = 'exchange'
  try {
    const payload = hdhivePayload()
    const values = sourceValues.value.hdhive || {}
    const result = await searchSourcesApi.hdhiveOauthExchange({
      ...payload,
      app_secret: String(values.hdhive_api_key || '').trim(),
      callback: sourceOauthCallback.value.trim(),
    })
    values.hdhive_access_token = result.access_token
    values.hdhive_refresh_token = result.refresh_token
    sourceValues.value.hdhive = { ...values }
    sourceOauthCallback.value = ''
    toast(result.warning || 'HDHive 授权成功，Token 已填入，保存后生效', result.warning ? 'error' : 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '授权校验失败', 'error')
  } finally {
    sourceOauthBusy.value = ''
  }
}
</script>

<template>
  <div class="space-y-6 max-w-6xl">
    <!-- 顶部极简标题与全局操作 -->
    <header class="flex items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
      <div>
        <h2 class="text-xl font-bold tracking-tight text-white">系统设置</h2>
        <p class="text-xs text-zinc-400 mt-0.5">调控自动化追更、网盘转存、搜索渠道与播放参数</p>
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
            @browse="openAccountDirBrowse"
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

        <!-- 卡片 A2: 订阅自动搜源 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <Radar class="h-4 w-4 text-emerald-400" />
            <h3 class="text-sm font-semibold text-white">订阅自动搜源</h3>
          </div>

          <div class="space-y-3.5 text-xs">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">自动搜源总开关</p>
                <p class="text-[11px] text-zinc-500">开启后按间隔为每部追剧搜渠道，命中缺失集自动转存</p>
              </div>
              <Switch v-model="autoCfg.enabled" />
            </div>

            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">搜源间隔</p>
                <p class="text-[11px] text-zinc-500">同一部剧多久搜一轮</p>
              </div>
              <Select
                :model-value="String(autoCfg.interval_hours)"
                class="w-28"
                :options="[{ value: '1', label: '1 小时' }, { value: '3', label: '3 小时' }, { value: '6', label: '6 小时' }, { value: '12', label: '12 小时' }, { value: '24', label: '24 小时' }]"
                @update:model-value="(v: string) => (autoCfg.interval_hours = Number(v))"
              />
            </div>

            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">每轮最多订阅</p>
                <p class="text-[11px] text-zinc-500">防止一次搜太多触发渠道限流</p>
              </div>
              <Select
                :model-value="String(autoCfg.max_per_round)"
                class="w-28"
                :options="[{ value: '5', label: '5 部' }, { value: '10', label: '10 部' }, { value: '20', label: '20 部' }, { value: '50', label: '50 部' }]"
                @update:model-value="(v: string) => (autoCfg.max_per_round = Number(v))"
              />
            </div>

            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">每部候选上限</p>
                <p class="text-[11px] text-zinc-500">每次向渠道要多少条结果</p>
              </div>
              <Select
                :model-value="String(autoCfg.per_subscription_limit)"
                class="w-28"
                :options="[{ value: '10', label: '10 条' }, { value: '20', label: '20 条' }, { value: '30', label: '30 条' }, { value: '50', label: '50 条' }]"
                @update:model-value="(v: string) => (autoCfg.per_subscription_limit = Number(v))"
              />
            </div>

            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">命中即自动转存</p>
                <p class="text-[11px] text-zinc-500">关闭时只入「待选资源」，由你手动确认</p>
              </div>
              <Switch v-model="autoCfg.auto_transfer" />
            </div>

            <div class="flex items-center gap-2 pt-1">
              <Button size="sm" :disabled="autoSaving" @click="saveAutoSearch">
                {{ autoSaving ? '保存中…' : '保存设置' }}
              </Button>
              <Button variant="outline" size="sm" :disabled="autoRunning" @click="runAutoSearchNow">
                <RefreshCw class="mr-1.5 h-3.5 w-3.5" :class="autoRunning ? 'animate-spin' : ''" />
                {{ autoRunning ? '搜索中…' : '立即跑一轮' }}
              </Button>
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

      <!-- 存储路径说明卡片 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
          <FolderOpen class="h-4 w-4 text-emerald-400" />
          <h3 class="text-sm font-semibold text-white">网盘存储位置与分层</h3>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="rounded-xl border border-white/[0.06] bg-zinc-900/50 p-3 space-y-1">
            <p class="font-medium text-white">落盘位置由账号卡片决定</p>
            <p class="text-[11px] leading-relaxed text-zinc-500">
              每个网盘账号各自的「📦 转存暂存路径」与「🎬 媒体库归档路径」就是文件真实落点，
              转存时优先用主号、主号受限自动换已启用的备用号，路径随所用账号生效。
              要改路径请到
              <button type="button" class="text-emerald-400 underline decoration-dotted" @click="currentNav = 'accounts'">
                网盘账号
              </button>
              页面点对应账号的「选择目录」，本页不再重复设置根目录。
            </p>
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between rounded-xl bg-zinc-900/50 p-3 border border-white/[0.06]">
              <div>
                <p class="font-medium text-white">按媒体类型分层</p>
                <p class="text-[11px] text-zinc-500">在媒体库路径下自动加一级分类目录</p>
              </div>
              <Switch v-model="f.type_folder_enabled" />
            </div>
            <div v-if="f.type_folder_enabled" class="grid grid-cols-2 gap-2">
              <div class="space-y-1">
                <label class="text-[11px] text-zinc-400">电影目录名</label>
                <Input v-model="f.type_folder_movie" placeholder="电影" />
              </div>
              <div class="space-y-1">
                <label class="text-[11px] text-zinc-400">剧集目录名</label>
                <Input v-model="f.type_folder_tv" placeholder="电视剧" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 重命名规则（MoviePilot 模板方案） -->
      <div class="apple-glass rounded-2xl p-5 space-y-4 text-xs">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Sparkles class="h-4 w-4 text-sky-400" />
            <h3 class="text-sm font-semibold text-white">重命名规则</h3>
            <span class="rounded-full bg-sky-500/10 px-2 py-0.5 text-[10px] text-sky-300">MoviePilot 模板</span>
          </div>
          <button
            type="button"
            class="text-[11px] text-zinc-400 transition-colors hover:text-white"
            @click="restoreNamingDefaults"
          >
            恢复 MP 默认
          </button>
        </div>

        <div class="grid gap-4 lg:grid-cols-2">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-zinc-300">电影命名模板</label>
              <span class="text-[10px] text-zinc-600">示例：示例电影 (2024)</span>
            </div>
            <textarea
              ref="movieTemplateEl"
              v-model="naming.movie_format"
              rows="3"
              spellcheck="false"
              class="w-full resize-y rounded-xl border border-white/[0.08] bg-zinc-950/60 p-3 font-mono text-[11px] leading-relaxed text-emerald-200 outline-none transition-colors focus:border-emerald-500/40"
              @focus="activeTemplate = 'movie'"
              @input="scheduleNamingPreview"
            />
            <p
              class="truncate font-mono text-[11px]"
              :class="namingPreview.movie.valid ? 'text-zinc-500' : 'text-rose-400'"
            >
              {{
                namingPreview.movie.valid
                  ? `媒体库/${namingPreview.movie.relative_path}`
                  : namingPreview.movie.message
              }}
            </p>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-zinc-300">剧集命名模板</label>
              <span class="text-[10px] text-zinc-600">示例：示例剧集 (2024) S01</span>
            </div>
            <textarea
              ref="tvTemplateEl"
              v-model="naming.tv_format"
              rows="3"
              spellcheck="false"
              class="w-full resize-y rounded-xl border border-white/[0.08] bg-zinc-950/60 p-3 font-mono text-[11px] leading-relaxed text-emerald-200 outline-none transition-colors focus:border-emerald-500/40"
              @focus="activeTemplate = 'tv'"
              @input="scheduleNamingPreview"
            />
            <p
              class="truncate font-mono text-[11px]"
              :class="namingPreview.tv.valid ? 'text-zinc-500' : 'text-rose-400'"
            >
              {{
                namingPreview.tv.valid
                  ? `媒体库/${namingPreview.tv.relative_path}`
                  : namingPreview.tv.message
              }}
            </p>
          </div>
        </div>

        <div class="space-y-2">
          <p class="text-[11px] text-zinc-500">
            点击变量插入到光标处 · 当前插入目标：{{ activeTemplate === 'tv' ? '剧集模板' : '电影模板' }}
          </p>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="variable in namingVariables"
              :key="variable.name"
              type="button"
              class="rounded-lg border border-white/[0.08] bg-zinc-900/60 px-2 py-1 font-mono text-[10px] text-zinc-300 transition-colors hover:border-emerald-500/40 hover:text-emerald-300"
              :title="`${variable.label}｜示例：${variable.example}`"
              @click="insertNamingVariable(variable.name)"
            >
              {{ variable.name }}
            </button>
          </div>
        </div>

        <p v-if="namingError" class="text-[11px] text-rose-400">{{ namingError }}</p>
        <p class="text-[11px] leading-relaxed text-zinc-500">
          <code class="text-zinc-400">/</code> 分隔目录层级，最后一段是文件名；
          <code v-pre class="text-zinc-400">{{fileExt}}</code> 自带点号；变量为空时对应条件段自动消失。
        </p>
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

    <!-- 4. 搜索渠道（对齐原版插件：药丸标签 + 账户卡片 + 行式字段 + 底部保存） -->
    <div v-else-if="currentNav === 'sources'" class="space-y-4 pb-28">
      <!-- 渠道切换栏 -->
      <div class="apple-glass relative rounded-2xl px-2 py-2">
        <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          <button
            type="button"
            class="flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-all cursor-pointer whitespace-nowrap"
            :class="selectedSourceId === 'general' ? 'bg-white/15 text-white ring-1 ring-white/20' : 'text-zinc-400 hover:bg-white/[0.05] hover:text-white'"
            @click="pickSource('general')"
          >
            <SlidersHorizontal class="h-3.5 w-3.5 shrink-0" />
            <span>通用设置</span>
          </button>
          <button
            v-for="s in visibleSourceTabs"
            :key="s.id"
            type="button"
            class="flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-all cursor-pointer whitespace-nowrap"
            :class="selectedSourceId === s.id ? 'bg-white/15 text-white ring-1 ring-white/20' : 'text-zinc-400 hover:bg-white/[0.05] hover:text-white'"
            @click="pickSource(s.id)"
          >
            <component :is="sourceIcon(s.id)" class="h-3.5 w-3.5 shrink-0" />
            <span>{{ s.name }}</span>
            <span
              class="h-1.5 w-1.5 rounded-full"
              :class="sourceValues[s.id]?.enabled === false ? 'bg-zinc-600' : 'bg-emerald-400'"
            />
          </button>
          <button
            v-if="hiddenSourceTabs.length"
            type="button"
            class="flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium text-zinc-400 transition-all hover:bg-white/[0.05] hover:text-white cursor-pointer whitespace-nowrap"
            :class="hiddenSourceTabs.some((s) => s.id === selectedSourceId) ? 'bg-white/15 text-white ring-1 ring-white/20' : ''"
            @click="sourceMenuOpen = !sourceMenuOpen"
          >
            <List class="h-3.5 w-3.5 shrink-0" />
            <span>更多 ({{ sourceSchemas.length }})</span>
          </button>
        </div>
        <div
          v-if="sourceMenuOpen"
          class="absolute left-2 right-2 top-full z-30 mt-1 max-h-72 overflow-y-auto rounded-xl border border-white/10 bg-[#121214] p-1.5 shadow-2xl"
        >
          <button
            v-for="s in sourceSchemas"
            :key="s.id"
            type="button"
            class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-zinc-300 hover:bg-white/[0.06] cursor-pointer"
            :class="selectedSourceId === s.id ? 'text-white' : ''"
            @click="pickSource(s.id)"
          >
            <component :is="sourceIcon(s.id)" class="h-3.5 w-3.5 shrink-0 text-zinc-500" />
            <span class="flex-1 text-left">{{ s.name }}</span>
            <span
              v-if="sourceValues[s.id]?.enabled === false"
              class="rounded bg-white/[0.06] px-1 py-0.5 text-[10px] text-zinc-500"
            >停用</span>
            <Check v-else-if="selectedSourceId === s.id" class="h-3.5 w-3.5 text-emerald-400" />
          </button>
        </div>
      </div>

      <!-- 通用设置：搜索顺序 / Magnet 模板 / 搜索代理 -->
      <div v-if="selectedSourceId === 'general'" class="apple-glass overflow-hidden rounded-2xl">
        <div class="flex items-center gap-2 px-4 py-3">
          <SlidersHorizontal class="h-4 w-4 shrink-0 text-emerald-400" />
          <h4 class="text-sm font-semibold text-white">通用设置</h4>
        </div>

        <section class="border-t border-white/[0.06]">
          <div class="flex items-center gap-2 px-4 py-2.5">
            <ListOrdered class="h-3.5 w-3.5 shrink-0 text-zinc-500" />
            <span class="text-xs font-semibold text-zinc-300">搜索顺序</span>
          </div>

          <div class="border-t border-white/[0.04] px-4 py-3 text-xs">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">搜索资源优先级</p>
                <p class="mt-0.5 text-[11px] text-zinc-500">按顺序依次尝试，靠前的渠道先返回结果</p>
              </div>
              <span class="shrink-0 text-[11px] text-zinc-500">共 {{ sourceOptions.length }} 项</span>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <span
                v-for="(id, index) in sourceOrder"
                :key="id"
                class="flex items-center gap-1 rounded-lg bg-white/[0.06] px-2 py-1"
              >
                <span class="text-[10px] font-semibold text-emerald-400">#{{ index + 1 }}</span>
                <span class="text-[11px] text-white">{{ optionName(sourceOptions, id) }}</span>
                <button type="button" class="px-0.5 text-zinc-500 hover:text-white disabled:opacity-30 cursor-pointer" :disabled="index === 0" @click="moveOrderItem('source', id, -1)">‹</button>
                <button type="button" class="px-0.5 text-zinc-500 hover:text-white disabled:opacity-30 cursor-pointer" :disabled="index === sourceOrder.length - 1" @click="moveOrderItem('source', id, 1)">›</button>
                <button type="button" class="px-0.5 text-zinc-500 hover:text-rose-400 cursor-pointer" @click="removeOrderItem('source', id)">✕</button>
              </span>
              <p v-if="!sourceOrder.length" class="text-[11px] text-zinc-500">未设置优先级，按渠道注册顺序搜索</p>
              <div class="relative">
                <button
                  type="button"
                  class="rounded-lg border border-dashed border-white/15 px-2 py-1 text-[11px] text-zinc-400 hover:border-white/30 hover:text-white cursor-pointer"
                  @click="orderPicker = orderPicker === 'source' ? '' : 'source'"
                >+ 添加</button>
                <div
                  v-if="orderPicker === 'source'"
                  class="absolute left-0 top-full z-30 mt-1 max-h-56 w-44 overflow-y-auto rounded-xl border border-white/10 bg-[#121214] p-1 shadow-2xl"
                >
                  <button
                    v-for="opt in orderCandidates('source')"
                    :key="opt.id"
                    type="button"
                    class="flex w-full items-center rounded-lg px-2 py-1.5 text-left text-[11px] text-zinc-300 hover:bg-white/[0.06] cursor-pointer"
                    @click="addOrderItem('source', opt.id)"
                  >{{ opt.name }}</button>
                  <p v-if="!orderCandidates('source').length" class="px-2 py-1.5 text-[11px] text-zinc-500">已全部加入</p>
                </div>
              </div>
            </div>
          </div>

          <div class="border-t border-white/[0.04] px-4 py-3 text-xs">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-white">资源类型优先级</p>
                <p class="mt-0.5 text-[11px] text-zinc-500">同一资源命中多个网盘时，按此顺序选择转存目标</p>
              </div>
              <span class="shrink-0 text-[11px] text-zinc-500">共 {{ resourceOptions.length }} 项</span>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <span
                v-for="(id, index) in resourceOrder"
                :key="id"
                class="flex items-center gap-1 rounded-lg bg-white/[0.06] px-2 py-1"
              >
                <span class="text-[10px] font-semibold text-emerald-400">#{{ index + 1 }}</span>
                <span class="text-[11px] text-white">{{ optionName(resourceOptions, id) }}</span>
                <button type="button" class="px-0.5 text-zinc-500 hover:text-white disabled:opacity-30 cursor-pointer" :disabled="index === 0" @click="moveOrderItem('resource', id, -1)">‹</button>
                <button type="button" class="px-0.5 text-zinc-500 hover:text-white disabled:opacity-30 cursor-pointer" :disabled="index === resourceOrder.length - 1" @click="moveOrderItem('resource', id, 1)">›</button>
                <button type="button" class="px-0.5 text-zinc-500 hover:text-rose-400 cursor-pointer" @click="removeOrderItem('resource', id)">✕</button>
              </span>
              <div class="relative">
                <button
                  type="button"
                  class="rounded-lg border border-dashed border-white/15 px-2 py-1 text-[11px] text-zinc-400 hover:border-white/30 hover:text-white cursor-pointer"
                  @click="orderPicker = orderPicker === 'resource' ? '' : 'resource'"
                >+ 添加</button>
                <div
                  v-if="orderPicker === 'resource'"
                  class="absolute left-0 top-full z-30 mt-1 max-h-56 w-44 overflow-y-auto rounded-xl border border-white/10 bg-[#121214] p-1 shadow-2xl"
                >
                  <button
                    v-for="opt in orderCandidates('resource')"
                    :key="opt.id"
                    type="button"
                    class="flex w-full items-center rounded-lg px-2 py-1.5 text-left text-[11px] text-zinc-300 hover:bg-white/[0.06] cursor-pointer"
                    @click="addOrderItem('resource', opt.id)"
                  >{{ opt.name }}</button>
                  <p v-if="!orderCandidates('resource').length" class="px-2 py-1.5 text-[11px] text-zinc-500">已全部加入</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="flex items-start gap-4 border-t border-white/[0.06] px-4 py-3 text-xs">
          <div class="w-[36%] min-w-[104px] shrink-0">
            <p class="leading-5 font-medium text-white">Magnet 元数据地址模板</p>
            <p class="mt-0.5 text-[11px] leading-relaxed text-zinc-500">必须包含 {info_hash}</p>
          </div>
          <div class="min-w-0 flex-1">
            <Input
              v-model="magnetTemplate"
              class="h-9 text-xs"
              placeholder="https://itorrents.org/torrent/{info_hash}.torrent"
            />
          </div>
        </section>

        <section class="border-t border-white/[0.06]">
          <div class="flex items-center gap-2 px-4 py-2.5">
            <Network class="h-3.5 w-3.5 shrink-0 text-zinc-500" />
            <span class="text-xs font-semibold text-zinc-300">搜索代理</span>
          </div>
          <div class="flex items-start gap-4 border-t border-white/[0.04] px-4 py-3 text-xs">
            <div class="w-[36%] min-w-[104px] shrink-0">
              <p class="leading-5 font-medium text-white">代理地址</p>
              <p class="mt-0.5 text-[11px] leading-relaxed text-zinc-500">留空直连，支持 http / socks5</p>
            </div>
            <div class="min-w-0 flex-1">
              <Input v-model="searchProxy" class="h-9 text-xs" placeholder="http://127.0.0.1:7890 或 socks5h://host:1080" />
            </div>
          </div>
          <div class="flex items-start gap-4 border-t border-white/[0.04] px-4 py-3 text-xs">
            <div class="w-[36%] min-w-[104px] shrink-0">
              <p class="leading-5 font-medium text-white">代理用户名</p>
              <p class="mt-0.5 text-[11px] leading-relaxed text-zinc-500">代理需要认证时填写</p>
            </div>
            <div class="min-w-0 flex-1">
              <Input v-model="proxyUsername" class="h-9 text-xs" placeholder="留空表示无需认证" />
            </div>
          </div>
          <div class="flex items-start gap-4 border-t border-white/[0.04] px-4 py-3 text-xs">
            <div class="w-[36%] min-w-[104px] shrink-0">
              <p class="leading-5 font-medium text-white">代理密码</p>
              <p class="mt-0.5 text-[11px] leading-relaxed text-zinc-500">仅保存在本机数据库</p>
            </div>
            <div class="min-w-0 flex-1">
              <Input v-model="proxyPassword" type="password" class="h-9 text-xs" placeholder="留空表示无需认证" />
            </div>
          </div>
        </section>
      </div>

      <div v-else-if="currentSource" class="apple-glass overflow-hidden rounded-2xl">
        <!-- 渠道标题 -->
        <div class="flex items-center justify-between gap-3 px-4 py-3">
          <div class="flex min-w-0 items-center gap-2">
            <component :is="sourceIcon(currentSource.id)" class="h-4 w-4 shrink-0 text-emerald-400" />
            <h4 class="truncate text-sm font-semibold text-white">{{ currentSource.name }}</h4>
          </div>
          <div class="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              class="flex items-center gap-1 rounded-lg border border-white/10 px-2 py-1 text-[11px] text-zinc-400 hover:border-white/25 hover:text-white cursor-pointer"
              :disabled="sourceTestRunning"
              @click="testSelectedSource"
            >
              <Search class="h-3 w-3" />
              {{ sourceTestRunning ? '测试中…' : '测试' }}
            </button>
            <button
              type="button"
              class="flex items-center gap-1 rounded-lg border border-rose-500/25 px-2 py-1 text-[11px] text-rose-300 hover:bg-rose-500/10 cursor-pointer"
              @click="restoreSourceDefaults"
            >
              <RotateCcw class="h-3 w-3" />
              恢复默认值
            </button>
          </div>
        </div>

        <!-- 账户卡片 -->
        <div v-if="currentAccount" class="flex items-start gap-3 border-t border-white/[0.06] px-4 py-3.5">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white/[0.06]">
            <img v-if="currentAccount.user?.avatar" :src="currentAccount.user.avatar" class="h-full w-full object-cover" alt="" />
            <component :is="sourceIcon(currentSource.id)" v-else class="h-4 w-4 text-zinc-500" />
          </div>
          <div class="min-w-0 flex-1 space-y-1.5">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="truncate text-sm font-medium text-white">
                {{ currentAccount.connected ? currentAccount.user?.name || currentAccount.name || '未知用户' : '账号未连接' }}
              </span>
              <span
                v-if="currentAccount.connected && currentAccount.user?.badge"
                class="rounded-md bg-emerald-500/15 px-1.5 py-0.5 text-[10px] text-emerald-300"
              >{{ currentAccount.user.badge }}</span>
              <span
                v-if="currentAccount.connected && accountPoints(currentAccount)"
                class="rounded-md bg-white/[0.06] px-1.5 py-0.5 text-[10px] text-zinc-300"
              >{{ accountPointsLabel(currentAccount) }} {{ accountPoints(currentAccount) }}</span>
            </div>
            <div v-if="currentAccount.connected && currentAccount.details?.length" class="flex flex-wrap gap-1.5">
              <span
                v-for="item in currentAccount.details"
                :key="item.label"
                class="rounded-md bg-white/[0.05] px-1.5 py-0.5 text-[10px] text-zinc-400"
              >{{ item.label }}：<span class="text-zinc-200">{{ item.value }}</span></span>
            </div>
            <p v-if="!currentAccount.connected" class="text-[11px] leading-relaxed text-amber-400">
              {{ currentAccount.error || '请填写登录凭证并保存配置' }}
            </p>
          </div>
          <button
            type="button"
            class="shrink-0 p-1.5 text-zinc-500 hover:text-emerald-400 cursor-pointer"
            title="刷新账户信息"
            @click="refreshSourceAccount(currentSource.id)"
          >
            <RefreshCw class="h-3.5 w-3.5" :class="sourceAccountRefreshing ? 'animate-spin' : ''" />
          </button>
        </div>

        <!-- 连通性结果 -->
        <div
          v-if="sourceTest"
          class="mx-4 my-2 flex items-center justify-between rounded-xl border px-3 py-2 text-[11px]"
          :class="sourceTest.valid ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-rose-500/30 bg-rose-500/10 text-rose-400'"
        >
          <span class="truncate">{{ sourceTest.valid ? '连通正常' : '连通失败' }}：{{ sourceTest.message }}</span>
          <span class="ml-2 shrink-0 font-mono text-[11px]">{{ sourceTest.elapsed_ms }} ms</span>
        </div>

        <!-- 参数分组 -->
        <section
          v-for="group in currentSource.groups"
          :key="group.title || 'default'"
          class="border-t border-white/[0.06]"
        >
          <button
            type="button"
            class="flex w-full items-center gap-2 px-4 py-2.5 text-left cursor-pointer"
            @click="toggleGroup(groupTitle(group))"
          >
            <ChevronDown
              class="h-3.5 w-3.5 shrink-0 text-zinc-500 transition-transform"
              :class="isGroupCollapsed(groupTitle(group)) ? '-rotate-90' : ''"
            />
            <span class="text-xs font-semibold text-zinc-300">{{ groupTitle(group) }}</span>
          </button>
          <div v-show="!isGroupCollapsed(groupTitle(group))">
            <div
              v-for="field in group.fields"
              :key="field.key"
              v-show="sourceFieldVisible(field) && field.type !== 'account' && !String(field.type || '').startsWith('test')"
              class="flex items-start gap-4 border-t border-white/[0.04] px-4 py-3 text-xs"
            >
              <div class="w-[36%] min-w-[104px] shrink-0">
                <p class="leading-5 font-medium text-white">{{ field.label }}</p>
                <p v-if="field.hint || field.description" class="mt-0.5 text-[11px] leading-relaxed text-zinc-500">
                  {{ field.hint || field.description }}
                </p>
              </div>
              <div class="min-w-0 flex-1">
                <SearchSourceField
                  :field="field"
                  :model-value="sourceValues[currentSource.id][field.key]"
                  :options="sourceFieldOptions(field)"
                  :account="sourceMeta.accounts[currentSource.id]"
                  :busy="sourceTestRunning"
                  :account-refreshing="sourceAccountRefreshing"
                  :oauth-busy="sourceOauthBusy"
                  :oauth-callback="sourceOauthCallback"
                  @update:model-value="sourceValues[currentSource.id][field.key] = $event"
                  @update:oauth-callback="sourceOauthCallback = $event"
                  @test="testSelectedSource()"
                  @refresh-account="refreshSourceAccount(currentSource.id)"
                  @oauth-start="startHdhiveOauth()"
                  @oauth-exchange="exchangeHdhiveOauth()"
                />
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 底部保存 -->
      <div class="sticky bottom-0 z-20 pt-1">
        <div class="apple-glass flex items-center justify-between gap-3 rounded-2xl px-3 py-2.5 shadow-xl">
          <p class="text-[11px] text-zinc-500">
            <template v-if="selectedSourceId === 'general'">通用设置 · 排序 / Magnet / 代理</template>
            <template v-else>共 {{ sourceSchemas.length }} 个渠道 · 当前 {{ currentSource?.name || '—' }}</template>
          </p>
          <Button
            size="sm"
            class="apple-btn-primary px-4 text-xs"
            :disabled="saving || searchProxySaving"
            @click="selectedSourceId === 'general' ? saveGlobalSettings() : saveAll()"
          >
            {{ saving || searchProxySaving ? '保存中…' : '保存配置' }}
          </Button>
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

            <div v-if="f.strm_mode === 'direct_302'" class="space-y-1.5">
              <label class="font-medium text-white">站点公开地址</label>
              <Input v-model="f.strm_public_base_url" placeholder="https://csx.你的域名" />
              <p class="text-[11px] text-zinc-500">
                播放器访问本服务用的地址，302 跳转会拼在这后面；留空则只有手动同步能生成 STRM
              </p>
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

      <!-- 卡片 C2: 跨盘转存 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Link2 class="h-4 w-4 text-sky-400" />
            <h3 class="text-sm font-semibold text-white">跨盘转存</h3>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-[11px] text-zinc-500">缓存剩余 {{ crossCfg.cache_free_gb }} GB</span>
            <Switch v-model="crossCfg.enabled" />
          </div>
        </div>
        <p class="text-[11px] leading-relaxed text-zinc-500">
          资源盘和媒体库盘不是同一个网盘时（例如夸克分享、115 媒体库），先下载到本地缓存，再秒传或上传到媒体库盘；同盘仍然直接转存。
        </p>
        <div v-if="!crossCfg.drive_options.length" class="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[11px] text-amber-300">
          还没有可用的媒体库网盘，先到「网盘账号」绑定 115 或夸克。
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1.5">
            <label class="font-medium text-white">媒体库所在网盘</label>
            <Select
              v-model="crossCfg.library_drive"
              :options="crossCfg.drive_options.map((item) => ({ value: item.value, label: item.primary ? item.label + '（主号）' : item.label }))"
            />
          </div>
          <div class="space-y-1.5">
            <label class="font-medium text-white">下载线程数</label>
            <Input v-model.number="crossCfg.download_threads" type="number" min="1" max="16" />
          </div>
          <div class="space-y-1.5">
            <label class="font-medium text-white">同时中继任务数</label>
            <Input v-model.number="crossCfg.max_concurrent" type="number" min="1" max="4" />
          </div>
          <div class="flex items-center justify-between rounded-xl bg-zinc-900/50 p-3 border border-white/[0.06]">
            <div>
              <p class="font-medium text-white">边下边传</p>
              <p class="text-[11px] text-zinc-500">下载一块上传一块，省等待</p>
            </div>
            <Switch v-model="crossCfg.direct_stream" />
          </div>
        </div>
        <div class="flex items-center justify-between pt-1">
          <p class="text-[11px] text-zinc-500">缓存目录 {{ crossCfg.cache_dir }}</p>
          <Button size="sm" :disabled="crossSaving" @click="saveCrossSettings">
            {{ crossSaving ? '保存中…' : '保存跨盘设置' }}
          </Button>
        </div>
      </div>

      <!-- 卡片 D: 媒体二级分类 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Layers class="h-4 w-4 text-amber-400" />
            <h3 class="text-sm font-semibold text-white">媒体二级分类</h3>
          </div>
          <Switch v-model="categoryConfig.enabled" />
        </div>
        <p class="text-[11px] leading-relaxed text-zinc-500">
          启用后媒体会多建一层分类目录，例如「电影/动画电影/片名 (年份)」。规则自上而下匹配，命中第一条即停止；条件留空表示兜底分类。
        </p>
        <div v-if="categoryConfig.enabled" class="space-y-3">
          <div class="flex items-center gap-2">
            <div class="flex rounded-lg bg-zinc-900/60 p-0.5">
              <button
                v-for="tab in CATEGORY_TABS"
                :key="tab.value"
                class="rounded-md px-3 py-1 text-[11px] transition"
                :class="categoryTab === tab.value ? 'bg-white/10 text-white' : 'text-zinc-500 hover:text-zinc-300'"
                @click="categoryTab = tab.value"
              >
                {{ tab.label }}
              </button>
            </div>
            <span class="ml-auto text-[11px] text-zinc-500">顺序即优先级</span>
          </div>

          <div class="space-y-2">
            <div
              v-for="(rule, index) in categoryRules()"
              :key="`${categoryTab}-${index}`"
              class="rounded-xl border border-white/[0.06] bg-zinc-900/40 p-2.5"
            >
              <div class="flex items-center gap-2">
                <span class="w-4 shrink-0 text-center text-[11px] text-zinc-600">{{ index + 1 }}</span>
                <Input v-model="rule.name" placeholder="分类目录名，如 动画电影" class="h-8 flex-1" />
                <div class="flex shrink-0 items-center gap-0.5">
                  <button
                    class="rounded-md p-1 text-zinc-500 hover:bg-white/5 hover:text-white disabled:opacity-30"
                    :disabled="index === 0"
                    @click="moveCategoryRule(index, -1)"
                  >↑</button>
                  <button
                    class="rounded-md p-1 text-zinc-500 hover:bg-white/5 hover:text-white disabled:opacity-30"
                    :disabled="index === categoryRules().length - 1"
                    @click="moveCategoryRule(index, 1)"
                  >↓</button>
                  <button
                    class="rounded-md p-1 text-zinc-500 hover:bg-rose-500/10 hover:text-rose-400"
                    @click="removeCategoryRule(index)"
                  >
                    <Trash2 class="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <div class="mt-2 flex flex-wrap items-center gap-1.5 pl-6">
                <div
                  v-for="key in Object.keys(rule.conditions)"
                  :key="key"
                  class="flex items-center gap-1 rounded-lg border border-white/[0.06] bg-zinc-800/60 px-1.5 py-1"
                >
                  <select
                    :value="key"
                    class="bg-transparent text-[11px] text-zinc-300 outline-none"
                    @change="onCategoryConditionKey(rule, key, $event)"
                  >
                    <option v-for="field in CATEGORY_FIELDS" :key="field.value" :value="field.value">
                      {{ field.label }}
                    </option>
                  </select>
                  <input
                    v-model="rule.conditions[key]"
                    placeholder="16 / CN,TW / 2020-2024"
                    class="w-32 bg-transparent text-[11px] text-white outline-none placeholder:text-zinc-600"
                  />
                  <button class="text-zinc-500 hover:text-rose-400" @click="removeCategoryCondition(rule, key)">×</button>
                </div>
                <button
                  v-if="Object.keys(rule.conditions).length < 3"
                  class="rounded-lg border border-dashed border-white/10 px-2 py-1 text-[11px] text-zinc-400 hover:border-cyan-400/40 hover:text-cyan-300"
                  @click="addCategoryCondition(rule)"
                >
                  + 条件
                </button>
                <span v-if="!Object.keys(rule.conditions).length" class="text-[11px] text-zinc-600">
                  无条件 → 兜底分类
                </span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" @click="addCategoryRule">
              <Plus class="h-3.5 w-3.5" />添加分类
            </Button>
            <Button variant="ghost" size="sm" @click="resetCategoryRules">
              <RotateCcw class="h-3.5 w-3.5" />恢复 MP 默认
            </Button>
            <span class="ml-auto text-[11px] text-zinc-600">共 {{ categoryRules().length }} 条</span>
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

      <!-- 卡片 D: 通知消息模板 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center gap-2 border-b border-white/[0.06] pb-3">
          <FileText class="h-4 w-4 text-rose-400" />
          <h3 class="text-sm font-semibold text-white">通知消息模板</h3>
        </div>
        <p class="text-[11px] leading-relaxed text-zinc-500">
          用 Jinja2 语法自定义推送文案，变量为空时该行自动隐藏。点击右侧变量名可插入到模板末尾。
        </p>
        <div class="grid gap-3 md:grid-cols-3">
          <div
            v-for="(label, event) in NOTIFY_EVENT_LABELS"
            :key="event"
            class="space-y-2 rounded-xl border border-white/[0.06] bg-zinc-900/40 p-3"
          >
            <div class="flex items-center justify-between">
              <span class="font-medium text-white">{{ label }}</span>
              <button class="text-[11px] text-zinc-500 hover:text-white" @click="resetNotifyTemplate(event)">
                恢复默认
              </button>
            </div>
            <textarea
              v-model="notifyTemplates[event]"
              rows="7"
              class="w-full rounded-lg border border-white/10 bg-zinc-900/60 p-2 font-mono text-[11px] leading-relaxed text-white outline-none"
            />
            <div class="flex flex-wrap gap-1">
              <button
                v-for="variable in NOTIFY_VARIABLES[event]"
                :key="variable"
                class="rounded-md bg-zinc-800/70 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400 hover:text-cyan-300"
                @click="insertNotifyVariable(event, variable)"
              >
                {{ variable }}
              </button>
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
          <div class="space-y-2.5 rounded-xl border border-white/[0.06] bg-zinc-900/40 p-3">
            <div class="flex items-center gap-2">
              <Database class="h-3.5 w-3.5 text-zinc-500" />
              <span class="font-medium text-zinc-300">TG 账号登录（频道监控必需）</span>
            </div>
            <div class="grid gap-2 sm:grid-cols-2">
              <Input v-model="f.tg_api_id" placeholder="API ID，例如 30296810" />
              <Input v-model="f.tg_api_hash" type="password" placeholder="API Hash（32 位十六进制）" />
            </div>
            <textarea
              v-model="f.tg_session"
              rows="3"
              placeholder="Telethon StringSession（从已登录客户端导出）"
              class="w-full rounded-xl border border-white/10 bg-zinc-900/60 p-2.5 font-mono text-[11px] text-white outline-none"
            />
            <p class="text-[11px] leading-relaxed text-zinc-500">
              来自 MoviePilot 插件「频道监控」的登录凭据，用你自己的账号（而非机器人）读取公开与私有频道。会话串等同密码，仅保存在本机数据库。
            </p>
          </div>

          <div class="space-y-2 rounded-xl border border-white/[0.06] bg-zinc-900/40 p-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <Badge :tone="tgStatusTone" :pulse="tgScanning">{{ tgStatusText }}</Badge>
                <span class="text-[11px] text-zinc-500">上次扫描：{{ formatTgTimestamp(tgClientStatus?.last_scan_at) }}</span>
                <span v-if="tgClientStatus?.channels.length" class="text-[11px] text-zinc-500">监控 {{ tgClientStatus.channels.length }} 个频道</span>
              </div>
              <Button variant="secondary" size="sm" :disabled="tgScanning || !tgClientStatus?.configured" @click="scanTgNow">
                <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': tgScanning }" />
                {{ tgScanning ? '扫描中' : '立即扫描' }}
              </Button>
            </div>
            <p v-if="tgClientStatus?.last_error" class="text-[11px] leading-relaxed text-rose-400">
              {{ tgClientStatus.last_error }}
            </p>
            <p v-else-if="tgClientStatus && !tgClientStatus.configured" class="text-[11px] leading-relaxed text-zinc-500">
              请填写并保存 API ID、API Hash 与 StringSession，后台任务会自动开始定时扫描。
            </p>
            <p v-if="tgScanSummary" class="text-[11px] leading-relaxed text-zinc-400">
              {{ tgScanSummary }}
            </p>
          </div>

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
      v-if="dirDialogOpen"
      :open="dirDialogOpen"
      :accounts="accounts"
      :account-id="targetAccountForBrowse?.id ?? accounts[0]?.id"
      @close="dirDialogOpen = false"
      @select="handleAccountDirSelect"
    />
  </div>
</template>
