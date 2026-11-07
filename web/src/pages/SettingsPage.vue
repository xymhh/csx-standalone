<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { Plus, RefreshCw, Trash2, KeyRound } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useToast } from '@/composables/useToast'
import { accountsApi, settingsApi, type Account, type SettingSection } from '@/lib/api'

const sections: { value: SettingSection; label: string; desc: string; sample: string }[] = [
  { value: 'baseline', label: '追剧规则', desc: '配置默认追更窗口、语言与定时任务偏好。', sample: '{\n  "window_days": 14,\n  "language": "zh-CN"\n}' },
  { value: 'sources', label: '搜索找源', desc: '开启或关闭各大网盘资源搜索站点。', sample: '{\n  "pansou": true,\n  "mikan": true,\n  "piratebay": true\n}' },
  { value: 'transfer', label: '网盘转存', desc: '转存目标路径与画质洗版优先顺序。', sample: '{\n  "default_drive": "quark",\n  "upgrade_enabled": true,\n  "quality_order": ["remux", "dv", "hdr", "4k", "hd"]\n}' },
  { value: 'strm', label: '直链播放', desc: 'STRM 播放模式（直链 / 本地挂载 / 代理）。', sample: '{\n  "mode": "local_mount",\n  "local_mount_root": "/mnt/quark"\n}' },
  { value: 'notify', label: '消息通知', desc: '转存成功、更新与异常时的微信/飞书/TG 通知。', sample: '{\n  "channels": {\n    "feishu": { "enabled": false, "webhook_url": "" },\n    "telegram": { "enabled": false, "bot_token": "", "chat_id": "" }\n  }\n}' },
  { value: 'advanced', label: '高级设置', desc: '系统运行性能与高级调度参数。', sample: '{\n  "log_level": "INFO"\n}' },
]
const section = ref<SettingSection>('baseline')
const data = ref<Record<string, unknown>>({})
const editor = ref('{}')
const accounts = ref<Account[]>([])
const open = ref(false)
const editing = ref<Account | null>(null)
const provider = ref('115')
const name = ref('')
const credential = ref('')
const { toast } = useToast()

async function loadSettings() {
  data.value = await settingsApi.getSection(section.value)
  const current = sections.find((x) => x.value === section.value)
  editor.value = Object.keys(data.value).length ? JSON.stringify(data.value, null, 2) : (current?.sample ?? '{}')
}
async function loadAccounts() {
  accounts.value = await accountsApi.list()
}
async function load() {
  await Promise.all([loadSettings(), loadAccounts()])
}
onMounted(load)
watch(section, loadSettings)

async function save() {
  try {
    const parsed: unknown = JSON.parse(editor.value)
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error('配置内容必须是标准的 JSON 对象格式')
    }
    data.value = await settingsApi.updateSection(section.value, parsed as Record<string, unknown>)
    editor.value = JSON.stringify(data.value, null, 2)
    toast('设置已保存', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败，请检查输入格式', 'error')
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

    <section class="surface-card p-6">
      <div class="grid gap-6 lg:grid-cols-12">
        <div class="lg:col-span-5 space-y-2">
          <p class="font-mono text-[11px] uppercase tracking-wider text-muted">CONFIGURATION</p>
          <h3 class="text-base font-semibold text-fg">{{ sections.find((x) => x.value === section)?.label }}</h3>
          <p class="text-xs leading-5 text-muted">
            {{ sections.find((x) => x.value === section)?.desc }}
          </p>
          <div class="pt-2">
            <span class="inline-block rounded-md bg-surface-2 px-2.5 py-1 font-mono text-[11px] text-muted">
              分组标识: {{ section }}
            </span>
          </div>
        </div>

        <div class="lg:col-span-7 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-muted">配置详情（JSON 对象）</span>
            <Button size="sm" @click="save">保存当前设置</Button>
          </div>
          <textarea
            v-model="editor"
            rows="10"
            spellcheck="false"
            class="w-full rounded-xl border border-border bg-bg/80 p-4 font-mono text-xs leading-5 text-fg focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
          />
        </div>
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
              检测
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
