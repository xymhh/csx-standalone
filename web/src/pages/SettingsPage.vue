<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Plus, RefreshCw, Trash2, KeyRound, Check, HelpCircle, Code2, Sliders } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useToast } from '@/composables/useToast'
import { accountsApi, settingsApi, type Account, type SettingSection } from '@/lib/api'

const sections: { value: SettingSection; label: string; desc: string }[] = [
  { value: 'baseline', label: '追剧规则', desc: '配置默认检查更新的时间范围与剧集元数据语言' },
  { value: 'sources', label: '搜索找源', desc: '开启或关闭各网盘与磁力资源的搜寻站点' },
  { value: 'transfer', label: '网盘转存', desc: '设置转存的目标网盘、文件夹以及画质洗版偏好' },
  { value: 'strm', label: '直链播放', desc: '配置供 Emby / Jellyfin / 播放器调用的 STRM 或挂载模式' },
  { value: 'notify', label: '消息通知', desc: '转存完成、发现新剧或发生异常时通过微信、飞书或 Telegram 提醒' },
  { value: 'advanced', label: '高级设置', desc: '系统底层运行参数与并发连接控制' },
]

const section = ref<SettingSection>('baseline')
const rawData = ref<Record<string, unknown>>({})
const rawJson = ref('{}')
const showRawJson = ref(false)
const accounts = ref<Account[]>([])
const open = ref(false)
const editing = ref<Account | null>(null)
const provider = ref('115')
const name = ref('')
const credential = ref('')
const { toast } = useToast()

// 图形化表单内部响应式状态
const form = ref<Record<string, any>>({
  // baseline
  window_days: 14,
  language: 'zh-CN',
  scan_interval_seconds: 30,
  // sources
  pansou: true,
  mikan: true,
  piratebay: false,
  search_timeout: 15,
  // transfer
  default_drive: 'quark',
  transfer_root: 'CSX',
  upgrade_enabled: true,
  min_quality: 'hd',
  // strm
  strm_mode: 'local_mount',
  local_mount_root: '/mnt/quark',
  url_template: '',
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

async function loadSettings() {
  rawData.value = await settingsApi.getSection(section.value)
  rawJson.value = JSON.stringify(rawData.value, null, 2)

  // 映射到图形表单字段
  const d = rawData.value || {}
  if (section.value === 'baseline') {
    form.value.window_days = Number(d.window_days ?? 14)
    form.value.language = String(d.language ?? 'zh-CN')
    form.value.scan_interval_seconds = Number(d.scan_interval_seconds ?? 30)
  } else if (section.value === 'sources') {
    form.value.pansou = Boolean(d.pansou ?? true)
    form.value.mikan = Boolean(d.mikan ?? true)
    form.value.piratebay = Boolean(d.piratebay ?? false)
    form.value.search_timeout = Number(d.search_timeout ?? 15)
  } else if (section.value === 'transfer') {
    form.value.default_drive = String(d.default_drive ?? 'quark')
    form.value.transfer_root = String(d.transfer_root ?? 'CSX')
    form.value.upgrade_enabled = Boolean(d.upgrade_enabled ?? true)
    form.value.min_quality = String(d.min_quality ?? 'hd')
  } else if (section.value === 'strm') {
    form.value.strm_mode = String(d.mode ?? 'local_mount')
    form.value.local_mount_root = String(d.local_mount_root ?? '/mnt/quark')
    form.value.url_template = String(d.url_template ?? '')
  } else if (section.value === 'notify') {
    const ch = (d.channels as Record<string, any>) || {}
    form.value.feishu_enabled = Boolean(ch.feishu?.enabled ?? false)
    form.value.feishu_url = String(ch.feishu?.webhook_url ?? '')
    form.value.telegram_enabled = Boolean(ch.telegram?.enabled ?? false)
    form.value.telegram_token = String(ch.telegram?.bot_token ?? '')
    form.value.telegram_chat_id = String(ch.telegram?.chat_id ?? '')
    form.value.webhook_enabled = Boolean(ch.webhook?.enabled ?? false)
    form.value.webhook_url = String(ch.webhook?.url ?? '')
  } else if (section.value === 'advanced') {
    form.value.log_level = String(d.log_level ?? 'INFO')
    form.value.max_workers = Number(d.max_workers ?? 8)
  }
}

async function loadAccounts() {
  accounts.value = await accountsApi.list()
}

async function load() {
  await Promise.all([loadSettings(), loadAccounts()])
}

onMounted(load)
watch(section, loadSettings)

// 组合表单数据提交
async function save() {
  try {
    let payload: Record<string, unknown> = {}

    if (showRawJson.value) {
      const parsed = JSON.parse(rawJson.value)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('JSON 格式不正确')
      }
      payload = parsed as Record<string, unknown>
    } else {
      if (section.value === 'baseline') {
        payload = {
          window_days: Number(form.value.window_days),
          language: form.value.language,
          scan_interval_seconds: Number(form.value.scan_interval_seconds),
        }
      } else if (section.value === 'sources') {
        payload = {
          pansou: Boolean(form.value.pansou),
          mikan: Boolean(form.value.mikan),
          piratebay: Boolean(form.value.piratebay),
          search_timeout: Number(form.value.search_timeout),
        }
      } else if (section.value === 'transfer') {
        payload = {
          default_drive: form.value.default_drive,
          transfer_root: form.value.transfer_root,
          upgrade_enabled: Boolean(form.value.upgrade_enabled),
          min_quality: form.value.min_quality,
        }
      } else if (section.value === 'strm') {
        payload = {
          mode: form.value.strm_mode,
          local_mount_root: form.value.local_mount_root,
          url_template: form.value.url_template,
        }
      } else if (section.value === 'notify') {
        payload = {
          channels: {
            feishu: { enabled: form.value.feishu_enabled, webhook_url: form.value.feishu_url },
            telegram: { enabled: form.value.telegram_enabled, bot_token: form.value.telegram_token, chat_id: form.value.telegram_chat_id },
            webhook: { enabled: form.value.webhook_enabled, url: form.value.webhook_url },
          },
        }
      } else if (section.value === 'advanced') {
        payload = {
          log_level: form.value.log_level,
          max_workers: Number(form.value.max_workers),
        }
      }
    }

    rawData.value = await settingsApi.updateSection(section.value, payload)
    rawJson.value = JSON.stringify(rawData.value, null, 2)
    toast('设置保存成功', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败', 'error')
  }
}

function openAdd() {
  editing.value = null
  provider.value = '115'
  name.value = ''
  credential.value = ''
  open.value = true
}

async function submitAccount() {
  try {
    if (editing.value) {
      await accountsApi.update(editing.value.id, {
        name: name.value,
        credential: credential.value || undefined,
      })
      toast('账号已更新', 'success')
    } else {
      await accountsApi.create({
        provider: provider.value,
        name: name.value,
        credential: credential.value,
      })
      toast('网盘账号添加成功', 'success')
    }
    open.value = false
    await loadAccounts()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '操作失败', 'error')
  }
}

async function removeAccount(id: number) {
  await accountsApi.delete(id)
  await loadAccounts()
  toast('账号已删除', 'info')
}

async function testAccount(id: number) {
  try {
    const res = await accountsApi.test(id)
    toast(`${res.provider}网盘：${res.message}`, res.valid ? 'success' : 'error')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '检测失败', 'error')
  }
}
</script>

<template>
  <div class="space-y-7">
    <div>
      <h2 class="text-2xl font-semibold tracking-tight text-fg">设置</h2>
      <p class="mt-1 text-sm text-muted">配置你的网盘账号、自动追更偏好与播放方式</p>
    </div>

    <!-- 6 大分组 Tab -->
    <Tabs v-model="section" :items="sections" />

    <!-- 图形化配置面板（纯人话交互，拒绝裸 JSON） -->
    <section class="surface-card p-6 sm:p-7">
      <div class="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-border/70 pb-4">
        <div>
          <h3 class="text-base font-semibold text-fg">
            {{ sections.find((x) => x.value === section)?.label }}
          </h3>
          <p class="mt-0.5 text-xs text-muted">
            {{ sections.find((x) => x.value === section)?.desc }}
          </p>
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

      <!-- 高级 JSON 模式（默认隐藏） -->
      <div v-if="showRawJson" class="space-y-3">
        <p class="text-xs text-muted">开发者模式：直接以 JSON 格式编辑底层字段。</p>
        <textarea
          v-model="rawJson"
          rows="12"
          spellcheck="false"
          class="w-full rounded-xl border border-border bg-bg/90 p-4 font-mono text-xs leading-5 text-fg focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
        />
      </div>

      <!-- 100% 用户友好的图形化表单 -->
      <div v-else class="space-y-5">
        <!-- 1. 追剧规则 -->
        <template v-if="section === 'baseline'">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/50 pb-4">
            <div>
              <label class="text-sm font-medium text-fg">检查最近多少天的更新</label>
              <p class="text-xs text-muted mt-0.5">当剧集播出后，系统会在多少天内持续搜寻和补全新集数</p>
            </div>
            <div class="w-full sm:w-48 flex items-center gap-2">
              <Input v-model.number="form.window_days" type="number" min="1" max="365" />
              <span class="text-xs text-muted shrink-0">天</span>
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/50 pb-4">
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

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <label class="text-sm font-medium text-fg">自动检查更新频率</label>
              <p class="text-xs text-muted mt-0.5">后台自动轮询追剧清单与排队任务的间隔秒数</p>
            </div>
            <div class="w-full sm:w-48 flex items-center gap-2">
              <Input v-model.number="form.scan_interval_seconds" type="number" min="5" max="3600" />
              <span class="text-xs text-muted shrink-0">秒</span>
            </div>
          </div>
        </template>

        <!-- 2. 搜索找源 -->
        <template v-if="section === 'sources'">
          <div class="flex items-center justify-between gap-3 border-b border-border/50 pb-4">
            <div>
              <span class="text-sm font-medium text-fg">启用盘搜全网搜索 (PanSou)</span>
              <p class="text-xs text-muted mt-0.5">全网跨网盘聚合搜索引擎，搜寻各类公开分享</p>
            </div>
            <Switch v-model="form.pansou" label="启用盘搜" />
          </div>

          <div class="flex items-center justify-between gap-3 border-b border-border/50 pb-4">
            <div>
              <span class="text-sm font-medium text-fg">启用蜜柑计划 (Mikan Project)</span>
              <p class="text-xs text-muted mt-0.5">专注动漫新番与日剧更新的字幕组资源站</p>
            </div>
            <Switch v-model="form.mikan" label="启用蜜柑计划" />
          </div>

          <div class="flex items-center justify-between gap-3 border-b border-border/50 pb-4">
            <div>
              <span class="text-sm font-medium text-fg">启用海盗湾 (ThePirateBay)</span>
              <p class="text-xs text-muted mt-0.5">海外影视与欧美生肉资源搜索（需海外网络畅通）</p>
            </div>
            <Switch v-model="form.piratebay" label="启用海盗湾" />
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <label class="text-sm font-medium text-fg">单站搜索超时时间</label>
              <p class="text-xs text-muted mt-0.5">单个搜索站响应慢时的最长等待时间</p>
            </div>
            <div class="w-full sm:w-48 flex items-center gap-2">
              <Input v-model.number="form.search_timeout" type="number" min="3" max="120" />
              <span class="text-xs text-muted shrink-0">秒</span>
            </div>
          </div>
        </template>

        <!-- 3. 网盘转存 -->
        <template v-if="section === 'transfer'">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/50 pb-4">
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

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/50 pb-4">
            <div>
              <label class="text-sm font-medium text-fg">网盘转存保存目录</label>
              <p class="text-xs text-muted mt-0.5">存入网盘时的根文件夹名称</p>
            </div>
            <div class="w-full sm:w-48">
              <Input v-model="form.transfer_root" placeholder="例如 CSX" />
            </div>
          </div>

          <div class="flex items-center justify-between gap-3 border-b border-border/50 pb-4">
            <div>
              <span class="text-sm font-medium text-fg">允许自动画质升级（洗版）</span>
              <p class="text-xs text-muted mt-0.5">如果后续搜到了更高清的版本（如 4K HDR），自动替换当前低清文件</p>
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

        <!-- 4. 直链播放 -->
        <template v-if="section === 'strm'">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/50 pb-4">
            <div>
              <label class="text-sm font-medium text-fg">STRM 播放模式</label>
              <p class="text-xs text-muted mt-0.5">Emby、Jellyfin 或播放器读取网盘视频的方式</p>
            </div>
            <div class="w-full sm:w-60">
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
            <div class="w-full sm:w-60">
              <Input v-model="form.local_mount_root" placeholder="例如 /mnt/quark" />
            </div>
          </div>

          <div v-if="form.strm_mode === 'template'" class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <label class="text-sm font-medium text-fg">直链代理 URL 模板</label>
              <p class="text-xs text-muted mt-0.5">支持变量：{path}、{library_file_id}</p>
            </div>
            <div class="w-full sm:w-60">
              <Input v-model="form.url_template" placeholder="http://.../play?id={library_file_id}" />
            </div>
          </div>
        </template>

        <!-- 5. 消息通知 -->
        <template v-if="section === 'notify'">
          <!-- 飞书 -->
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

          <!-- Telegram -->
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

          <!-- 通用 Webhook -->
          <div class="rounded-xl border border-border/60 bg-surface-2/30 p-4 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <strong class="text-sm text-fg">通用自定义 Webhook</strong>
                <p class="text-xs text-muted">发送标准 JSON 事件到你的私有接口或 HomeAssistant</p>
              </div>
              <Switch v-model="form.webhook_enabled" label="启用通用 Webhook" />
            </div>
            <div v-if="form.webhook_enabled" class="pt-2">
              <label class="text-xs text-muted">接口 URL</label>
              <Input v-model="form.webhook_url" class="mt-1" placeholder="https://api.yourdomain.com/csx-webhook" />
            </div>
          </div>
        </template>

        <!-- 6. 高级设置 -->
        <template v-if="section === 'advanced'">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/50 pb-4">
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

    <!-- 网盘账号管理 -->
    <section class="space-y-4 pt-2">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="text-base font-semibold text-fg">我的网盘账号</h3>
          <p class="mt-0.5 text-xs text-muted">绑定你的 115 或夸克网盘，转存的影视将直接保存到你的网盘中</p>
        </div>
        <Button @click="openAdd" class="flex items-center gap-2">
          <Plus class="h-4 w-4" />
          <span>绑定新网盘</span>
        </Button>
      </div>

      <div v-if="!accounts.length" class="surface-card p-8 text-center text-sm text-muted">
        <KeyRound class="mx-auto mb-2 h-6 w-6 text-muted" />
        <p>尚未绑定任何网盘账号。点击右上角「绑定新网盘」添加一个吧。</p>
      </div>

      <div class="grid gap-3 sm:grid-cols-2">
        <article
          v-for="account in accounts"
          :key="account.id"
          class="surface-card flex items-center justify-between gap-3 p-4 transition-all hover:border-zinc-700"
        >
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <strong class="font-medium text-fg text-sm">{{ account.name }}</strong>
              <Badge tone="muted" class="text-[10px] uppercase">{{ account.provider }}网盘</Badge>
            </div>
            <p class="mt-1 text-xs text-muted">
              凭据状态：{{ account.has_credential ? '已高强度加密保存' : '未设置' }}
            </p>
          </div>
          <div class="flex items-center gap-2">
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
    </section>

    <Dialog :open="open" :title="editing ? '修改网盘账号' : '绑定网盘账号'" @close="open = false">
      <form class="space-y-4" @submit.prevent="submitAccount">
        <label class="block space-y-1.5 text-sm">
          <span class="text-xs text-muted">网盘类型</span>
          <Select
            v-model="provider"
            :options="[
              { value: '115', label: '115 网盘' },
              { value: 'quark', label: '夸克网盘' },
            ]"
            :disabled="!!editing"
          />
        </label>
        <label class="block space-y-1.5 text-sm">
          <span class="text-xs text-muted">账号备注名称</span>
          <Input v-model="name" required placeholder="例如：我的主号、夸克SVIP" />
        </label>
        <label class="block space-y-1.5 text-sm">
          <span class="text-xs text-muted">网页端 Cookie 凭据</span>
          <Input
            v-model="credential"
            type="password"
            :required="!editing"
            autocomplete="new-password"
            placeholder="粘贴网盘网页端的 Cookie 字符串"
          />
          <span class="text-[11px] text-muted">
            凭据将直接使用 Fernet 工业级加密后保存，系统绝不输出或回显明文。
          </span>
        </label>
        <Button type="submit" class="w-full">
          {{ editing ? '保存修改' : '确认绑定' }}
        </Button>
      </form>
    </Dialog>
  </div>
</template>
