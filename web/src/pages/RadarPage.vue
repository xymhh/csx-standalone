<script setup lang="ts">
import { onMounted, ref } from 'vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Switch from '@/components/ui/Switch.vue'
import { useToast } from '@/composables/useToast'
import {
  doctorApi,
  searchSourcesApi,
  settingsApi,
  telegramApi,
  type DoctorReport,
  type TelegramParseResult,
  type TelegramStatus,
} from '@/lib/api'

const report = ref<DoctorReport | null>(null)
const checks = ref<Record<string, string>>({})
const tgStatus = ref<TelegramStatus>({ enabled: false, channels: [], auto_transfer: true, ingested_count: 0 })
const channelsText = ref('')
const autoTransfer = ref(true)
const telegramEnabled = ref(false)
const savingConfig = ref(false)
const messageText = ref('')
const parseResult = ref<TelegramParseResult | null>(null)
const parsing = ref(false)
const { toast } = useToast()

onMounted(async () => {
  try {
    const [diagnostics, status] = await Promise.all([doctorApi.diagnose(), telegramApi.status()])
    report.value = diagnostics
    tgStatus.value = status
    channelsText.value = status.channels.join('\n')
    autoTransfer.value = status.auto_transfer
    telegramEnabled.value = status.enabled
  } catch (error) {
    toast(error instanceof Error ? error.message : '读取监控状态失败', 'error')
  }
})

async function test(provider: string) {
  try {
    const result = await settingsApi.testProvider(provider)
    checks.value[provider] = result.message
    toast(`${provider}：${result.message}`, result.valid ? 'success' : 'error')
  } catch (error) {
    toast(error instanceof Error ? error.message : '检测失败', 'error')
  }
}

async function saveTelegramConfig() {
  savingConfig.value = true
  try {
    await searchSourcesApi.save({
      tgchannels: {
        enabled: telegramEnabled.value,
        channels: channelsText.value.split('\n').map((value) => value.trim()).filter(Boolean),
        auto_transfer: autoTransfer.value,
      },
    })
    tgStatus.value = await telegramApi.status()
    toast('Telegram 频道配置已保存', 'success')
  } catch (error) {
    toast(error instanceof Error ? error.message : '保存频道配置失败', 'error')
  } finally {
    savingConfig.value = false
  }
}

async function parseMessage() {
  if (!messageText.value.trim()) {
    toast('请先粘贴一段频道消息', 'error')
    return
  }
  parsing.value = true
  parseResult.value = null
  try {
    parseResult.value = await telegramApi.parse(messageText.value)
  } catch (error) {
    toast(error instanceof Error ? error.message : '解析失败', 'error')
  } finally {
    parsing.value = false
  }
}

const providerNames: Record<string, string> = {
  '115': '115 网盘', quark: '夸克网盘', alipan: '阿里云盘', baidu: '百度网盘',
  tianyi: '天翼云盘', '123pan': '123 云盘', uc: 'UC 网盘', lanzou: '蓝奏云',
  wenshushu: '文叔叔',
}
</script>

<template>
  <div class="space-y-5">
    <div>
      <h2 class="text-xl font-semibold text-fg">双源雷达</h2>
      <p class="text-sm text-muted">搜索源连通性、Telegram 频道抓链与运行诊断</p>
    </div>

    <Card class="space-y-5 p-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 class="font-semibold text-fg">Telegram 频道自动抓链</h3>
          <p class="mt-1 text-sm text-muted">配置频道名单，并将命中的缺失剧集放入候选队列。</p>
        </div>
        <Badge :tone="telegramEnabled ? 'good' : 'muted'">{{ telegramEnabled ? '已启用' : '已停用' }}</Badge>
      </div>

      <div class="grid gap-5 lg:grid-cols-2">
        <label class="space-y-2 text-sm">
          <span class="font-medium text-fg">监控频道（每行一个）</span>
          <textarea
            v-model="channelsText"
            rows="5"
            placeholder="@Quark_Share_Group&#10;@share115"
            class="w-full rounded-xl border border-border bg-surface/80 px-3 py-2 text-sm text-fg placeholder:text-subtle focus-visible:border-focus focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-focus"
          />
        </label>
        <div class="space-y-4">
          <div class="flex min-h-12 items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-2">
            <span class="text-sm text-fg">启用频道监控</span>
            <Switch v-model="telegramEnabled" label="启用频道监控" />
          </div>
          <div class="flex min-h-12 items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-2">
            <span class="text-sm text-fg">收到新资源后自动转存</span>
            <Switch v-model="autoTransfer" label="收到新资源后自动转存" />
          </div>
          <div class="rounded-xl border border-border/70 bg-surface/40 px-3 py-3 text-sm text-muted">
            <div class="flex justify-between"><span>已配置频道</span><span class="tabular-nums text-fg">{{ tgStatus.channels.length }}</span></div>
            <div class="mt-1 flex justify-between"><span>已入库候选</span><span class="tabular-nums text-fg">{{ tgStatus.ingested_count }}</span></div>
            <p v-if="tgStatus.channels.length" class="mt-3 flex flex-wrap gap-2">
              <Badge v-for="channel in tgStatus.channels" :key="channel" tone="muted">{{ channel }}</Badge>
            </p>
          </div>
          <Button :disabled="savingConfig" @click="saveTelegramConfig">{{ savingConfig ? '保存中…' : '保存频道配置' }}</Button>
        </div>
      </div>
    </Card>

    <Card class="space-y-4 p-5">
      <div>
        <h3 class="font-semibold text-fg">📱 消息解析测试器</h3>
        <p class="mt-1 text-sm text-muted">粘贴频道消息，预览片名、季集、分享链接、提取码和订阅匹配结果。</p>
      </div>
      <textarea
        v-model="messageText"
        rows="7"
        placeholder="粘贴 Telegram 频道消息正文…"
        class="w-full rounded-xl border border-border bg-surface/80 px-3 py-2 text-sm text-fg placeholder:text-subtle focus-visible:border-focus focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-focus"
      />
      <Button :disabled="parsing" @click="parseMessage">{{ parsing ? '解析中…' : '解析测试' }}</Button>

      <div v-if="parseResult" class="space-y-4 rounded-xl border border-border/70 bg-surface/40 p-4">
        <div class="flex flex-wrap items-center gap-2">
          <Badge tone="info">{{ parseResult.title || '未识别片名' }}</Badge>
          <Badge tone="muted">{{ parseResult.season == null ? '季数未识别' : `第 ${parseResult.season} 季` }}</Badge>
          <Badge tone="muted">{{ parseResult.episode == null ? '集数未识别' : `第 ${parseResult.episode} 集` }}</Badge>
          <Badge :tone="parseResult.matched_subscription_id ? 'good' : 'warn'">
            {{ parseResult.matched_subscription_id ? `命中订阅 #${parseResult.matched_subscription_id}` : '未命中追剧订阅' }}
          </Badge>
        </div>
        <div v-if="parseResult.links.length" class="space-y-2">
          <article v-for="(link, index) in parseResult.links" :key="`${link.url}-${index}`" class="rounded-lg border border-border/70 bg-surface/50 p-3">
            <div class="flex flex-wrap items-center gap-2">
              <Badge tone="info">{{ providerNames[link.provider] ?? link.provider }}</Badge>
              <span class="text-xs text-muted">提取码：{{ link.password || '无' }}</span>
            </div>
            <a :href="link.url" target="_blank" rel="noreferrer" class="mt-2 block break-all text-sm text-fg underline decoration-border underline-offset-4">{{ link.url }}</a>
          </article>
        </div>
        <p v-else class="text-sm text-muted">没有识别到支持的网盘分享链接。</p>
      </div>
    </Card>

    <div class="grid gap-4 sm:grid-cols-2">
      <Card v-for="provider in ['115', 'quark', 'telegram', 'manual']" :key="provider" class="p-4">
        <div class="flex items-center justify-between">
          <h3 class="font-semibold text-fg">{{ provider }}</h3>
          <Badge :tone="checks[provider] ? 'good' : 'muted'">{{ checks[provider] ?? '未检测' }}</Badge>
        </div>
        <p class="my-3 text-xs text-muted">由搜索源与账号配置管理</p>
        <Button variant="outline" size="sm" @click="test(provider)">测试连通</Button>
      </Card>
    </div>

    <Card class="p-5">
      <h3 class="mb-3 font-semibold text-fg">诊断状态</h3>
      <pre class="overflow-auto whitespace-pre-wrap text-xs text-muted">{{ JSON.stringify(report, null, 2) }}</pre>
    </Card>
  </div>
</template>
