<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Bell, Database, FileText, Cpu, Radio, RefreshCw } from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import { useToast } from '@/composables/useToast'
import { settingsApi } from '@/api/settings'
import { type TgClientStatus, telegramApi } from '@/api/telegram'

const { toast } = useToast()

const form = ref<Record<string, any>>({
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

async function loadSettings() {
  try {
    const [n, a] = await Promise.all([
      settingsApi.getSection('notify'),
      settingsApi.getSection('advanced'),
    ])
    Object.assign(form.value, n, a)
    const channels = (n as { channels?: Record<string, Record<string, unknown>> }).channels || {}
    const feishu = channels.feishu || {}
    const telegram = channels.telegram || {}
    form.value.feishu_enabled = Boolean(feishu.enabled ?? form.value.feishu_enabled)
    form.value.feishu_url = String(feishu.webhook_url ?? form.value.feishu_url)
    form.value.telegram_enabled = Boolean(telegram.enabled ?? form.value.telegram_enabled)
    form.value.telegram_token = String(telegram.bot_token ?? form.value.telegram_token)
    form.value.telegram_chat_id = String(telegram.chat_id ?? form.value.telegram_chat_id)

    const templates = (n as { templates?: Record<string, string> }).templates
    if (templates && typeof templates === 'object') {
      notifyTemplates.value = { ...NOTIFY_DEFAULT_TEMPLATES, ...templates }
    }
  } catch (cause) {
    console.error(cause)
  }
}

function collectNotify() {
  return {
    channels: {
      feishu: { enabled: form.value.feishu_enabled, webhook_url: form.value.feishu_url },
      telegram: { enabled: form.value.telegram_enabled, bot_token: form.value.telegram_token, chat_id: form.value.telegram_chat_id },
    },
    templates: { ...notifyTemplates.value },
  }
}

function collectAdvanced() {
  return {
    log_level: form.value.log_level,
    max_workers: Number(form.value.max_workers),
    checkin_cron: form.value.checkin_cron,
    checkin_auto_retry: form.value.checkin_auto_retry,
    p115_checkin_mode: form.value.p115_checkin_mode,
    tg_monitor_enabled: form.value.tg_monitor_enabled,
    tg_channels: form.value.tg_channels,
    tg_auto_transfer: form.value.tg_auto_transfer,
    tg_api_id: form.value.tg_api_id,
    tg_api_hash: form.value.tg_api_hash,
    tg_session: form.value.tg_session,
  }
}

defineExpose({ collectNotify, collectAdvanced, refreshTgStatus: loadTgClientStatus })

onMounted(() => {
  void loadSettings()
  void loadTgClientStatus()
})
</script>

<template>
    <!-- 6. 通知与高级 (紧凑卡片网格) -->
    <div class="space-y-5">
      <div class="grid gap-4 md:grid-cols-2">
        <!-- 卡片 A: 消息通知渠道 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
            <Bell class="h-4 w-4 text-amber-400" />
            <h3 class="text-sm font-semibold text-fg">消息通知推送</h3>
          </div>

          <div class="space-y-3 text-xs">
            <div class="rounded-xl border border-primary/[0.06] bg-surface-solid/40 p-3 space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-medium text-fg">飞书群机器人</span>
                <Switch v-model="form.feishu_enabled" />
              </div>
              <Input v-if="form.feishu_enabled" v-model="form.feishu_url" placeholder="粘贴飞书 Webhook 链接" />
            </div>

            <div class="rounded-xl border border-primary/[0.06] bg-surface-solid/40 p-3 space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-medium text-fg">Telegram 机器人</span>
                <Switch v-model="form.telegram_enabled" />
              </div>
              <div v-if="form.telegram_enabled" class="space-y-1.5 pt-1">
                <Input v-model="form.telegram_token" type="password" placeholder="Bot Token (123456:ABC...)" />
                <Input v-model="form.telegram_chat_id" placeholder="Chat ID (-10012345678)" />
              </div>
            </div>
          </div>
        </div>

        <!-- 卡片 B: 签到与系统参数 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
            <Cpu class="h-4 w-4 text-sky-400" />
            <h3 class="text-sm font-semibold text-fg">自动签到与系统性能</h3>
          </div>

          <div class="space-y-3 text-xs">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-fg">每日自动签到</p>
                <p class="text-[11px] text-subtle">每天凌晨自动为所有网盘签到领空间</p>
              </div>
              <Switch v-model="form.checkin_auto_retry" />
            </div>

            <div class="grid grid-cols-2 gap-2 pt-1">
              <div class="space-y-1">
                <label class="text-muted">日志级别</label>
                <Select
                  v-model="form.log_level"
                  :options="[
                    { value: 'INFO', label: 'INFO 标准' },
                    { value: 'DEBUG', label: 'DEBUG 详细' },
                  ]"
                />
              </div>

              <div class="space-y-1">
                <label class="text-muted">并发任务数</label>
                <Input v-model.number="form.max_workers" type="number" min="1" max="32" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 卡片 D: 通知消息模板 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
          <FileText class="h-4 w-4 text-rose-400" />
          <h3 class="text-sm font-semibold text-fg">通知消息模板</h3>
        </div>
        <p class="text-[11px] leading-relaxed text-subtle">
          用 Jinja2 语法自定义推送文案，变量为空时该行自动隐藏。点击右侧变量名可插入到模板末尾。
        </p>
        <div class="grid gap-3 md:grid-cols-3">
          <div
            v-for="(label, event) in NOTIFY_EVENT_LABELS"
            :key="event"
            class="space-y-2 rounded-xl border border-primary/[0.06] bg-surface-solid/40 p-3"
          >
            <div class="flex items-center justify-between">
              <span class="font-medium text-fg">{{ label }}</span>
              <button class="text-[11px] text-subtle hover:text-fg" @click="resetNotifyTemplate(event)">
                恢复默认
              </button>
            </div>
            <textarea
              v-model="notifyTemplates[event]"
              rows="7"
              class="w-full rounded-lg border border-primary/10 bg-surface-solid/60 p-2 font-mono text-[11px] leading-relaxed text-fg outline-none"
            />
            <div class="flex flex-wrap gap-1">
              <button
                v-for="variable in NOTIFY_VARIABLES[event]"
                :key="variable"
                class="rounded-md bg-surface-2/70 px-1.5 py-0.5 font-mono text-[10px] text-muted hover:text-cyan-300"
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
        <div class="flex items-center justify-between border-b border-primary/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Radio class="h-4 w-4 text-blue-400" />
            <h3 class="text-sm font-semibold text-fg">Telegram 频道实时抓链监控</h3>
          </div>
          <Switch v-model="form.tg_monitor_enabled" />
        </div>

        <div v-if="form.tg_monitor_enabled" class="space-y-3 pt-1">
          <div class="space-y-2.5 rounded-xl border border-primary/[0.06] bg-surface-solid/40 p-3">
            <div class="flex items-center gap-2">
              <Database class="h-3.5 w-3.5 text-subtle" />
              <span class="font-medium text-fg-2">TG 账号登录（频道监控必需）</span>
            </div>
            <div class="grid gap-2 sm:grid-cols-2">
              <Input v-model="form.tg_api_id" placeholder="API ID，例如 30296810" />
              <Input v-model="form.tg_api_hash" type="password" placeholder="API Hash（32 位十六进制）" />
            </div>
            <textarea
              v-model="form.tg_session"
              rows="3"
              placeholder="Telethon StringSession（从已登录客户端导出）"
              class="w-full rounded-xl border border-primary/10 bg-surface-solid/60 p-2.5 font-mono text-[11px] text-fg outline-none"
            />
            <p class="text-[11px] leading-relaxed text-subtle">
              来自 MoviePilot 插件「频道监控」的登录凭据，用你自己的账号（而非机器人）读取公开与私有频道。会话串等同密码，仅保存在本机数据库。
            </p>
          </div>

          <div class="space-y-2 rounded-xl border border-primary/[0.06] bg-surface-solid/40 p-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <Badge :tone="tgStatusTone" :pulse="tgScanning">{{ tgStatusText }}</Badge>
                <span class="text-[11px] text-subtle">上次扫描：{{ formatTgTimestamp(tgClientStatus?.last_scan_at) }}</span>
                <span v-if="tgClientStatus?.channels.length" class="text-[11px] text-subtle">监控 {{ tgClientStatus.channels.length }} 个频道</span>
              </div>
              <Button variant="secondary" size="sm" :disabled="tgScanning || !tgClientStatus?.configured" @click="scanTgNow">
                <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': tgScanning }" />
                {{ tgScanning ? '扫描中' : '立即扫描' }}
              </Button>
            </div>
            <p v-if="tgClientStatus?.last_error" class="text-[11px] leading-relaxed text-rose-400">
              {{ tgClientStatus.last_error }}
            </p>
            <p v-else-if="tgClientStatus && !tgClientStatus.configured" class="text-[11px] leading-relaxed text-subtle">
              请填写并保存 API ID、API Hash 与 StringSession，后台任务会自动开始定时扫描。
            </p>
            <p v-if="tgScanSummary" class="text-[11px] leading-relaxed text-muted">
              {{ tgScanSummary }}
            </p>
          </div>

          <div class="space-y-1">
            <label class="text-fg-2">监控频道（每行一个）</label>
            <textarea
              v-model="form.tg_channels"
              rows="2"
              class="w-full rounded-xl border border-primary/10 bg-surface-solid/60 p-2.5 font-mono text-xs text-fg outline-none"
            />
          </div>

          <div class="flex items-center justify-between">
            <span class="text-muted">识别到新剧后直接转存入库</span>
            <Switch v-model="form.tg_auto_transfer" />
          </div>
        </div>
      </div>
    </div>
</template>
