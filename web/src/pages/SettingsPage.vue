<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { accountsApi, settingsApi, type Account, type SettingSection } from '@/lib/api'
import Tabs from '@/components/ui/Tabs.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Badge from '@/components/ui/Badge.vue'
import { useToast } from '@/composables/useToast'

const sections: { value: SettingSection; label: string }[] = [
  { value: 'baseline', label: '基准面' },
  { value: 'sources', label: '双源' },
  { value: 'transfer', label: '转存' },
  { value: 'strm', label: 'STRM' },
  { value: 'notify', label: '通知' },
  { value: 'advanced', label: '高级' },
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
  editor.value = JSON.stringify(data.value, null, 2)
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
      throw new Error('设置内容必须是 JSON 对象')
    }
    data.value = await settingsApi.updateSection(section.value, parsed as Record<string, unknown>)
    editor.value = JSON.stringify(data.value, null, 2)
    toast('设置已保存', 'success')
  } catch (error) {
    toast(error instanceof Error ? error.message : '保存失败', 'error')
  }
}
async function saveAccount() {
  if (editing.value) {
    await accountsApi.update(editing.value.id, { name: name.value, ...(credential.value ? { credential: credential.value } : {}) })
  } else {
    await accountsApi.create({ provider: provider.value, name: name.value, credential: credential.value })
  }
  credential.value = ''
  name.value = ''
  editing.value = null
  open.value = false
  await loadAccounts()
  toast('账号已保存', 'success')
}
function editAccount(account: Account) {
  editing.value = account
  provider.value = account.provider
  name.value = account.name
  credential.value = ''
  open.value = true
}
async function removeAccount(id: number) {
  await accountsApi.delete(id)
  await loadAccounts()
}
async function testAccount(id: number) {
  const result = await accountsApi.test(id)
  toast(`${result.provider}：${result.message}`, result.valid ? 'success' : 'error')
}
</script>
<template>
  <div class="space-y-5">
    <div><h2 class="text-xl font-semibold">系统设置</h2><p class="text-sm text-muted">按职责分组管理系统策略与账号凭据</p></div>
    <Tabs v-model="section" :items="sections" />
    <section class="grid gap-6 rounded-xl border border-border bg-surface p-5 shadow-sm shadow-black/40 lg:grid-cols-[minmax(220px,0.8fr)_minmax(0,1.6fr)] lg:p-6">
      <div class="space-y-2">
        <p class="font-mono text-[10px] uppercase tracking-[0.18em] text-subtle">Configuration</p>
        <h3 class="text-base font-semibold tracking-tight">{{ sections.find((item) => item.value === section)?.label }}设置</h3>
        <p class="text-sm leading-relaxed text-muted">按分组管理系统策略。配置以 JSON 对象保存，可包含布尔值、数字、数组与嵌套字段。</p>
        <Badge tone="muted">{{ section }}</Badge>
      </div>
      <div class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <span class="text-xs text-muted">本组设置数据</span>
          <Button size="sm" @click="save">保存本组</Button>
        </div>
        <textarea v-model="editor" spellcheck="false" aria-label="设置 JSON" class="min-h-72 w-full bg-bg/70 p-4 font-mono text-sm leading-6 text-fg focus-visible:ring-1 focus-visible:ring-focus" />
      </div>
    </section>
    <section class="space-y-3">
      <div class="flex items-center justify-between"><h3 class="font-semibold">网盘账号</h3><Button variant="outline" @click="open = true">添加账号</Button></div>
      <article v-for="account in accounts" :key="account.id" class="flex flex-wrap items-center gap-3 rounded-card border border-border bg-surface p-4">
        <div class="min-w-0 flex-1"><p class="font-medium">{{ account.name }}</p><p class="text-xs text-muted">{{ account.provider }} · {{ account.has_credential ? account.masked : '未配置凭据' }}</p></div>
        <Badge :tone="account.has_credential ? 'good' : 'warn'">凭据{{ account.has_credential ? '已设置' : '缺失' }}</Badge>
        <Button variant="outline" size="sm" @click="testAccount(account.id)">测试</Button><Button variant="outline" size="sm" @click="editAccount(account)">编辑</Button><Button variant="ghost" size="sm" @click="removeAccount(account.id)">删除</Button>
      </article>
      <p v-if="!accounts.length" class="text-sm text-muted">尚未添加网盘账号</p>
    </section>
    <Dialog :open="open" :title="editing ? '编辑网盘账号' : '添加网盘账号'" @close="open = false; editing = null">
      <form class="space-y-3" @submit.prevent="saveAccount">
        <label v-if="!editing" class="block space-y-1 text-sm">服务商<Select v-model="provider" :options="[{ value: '115', label: '115 网盘' }, { value: 'quark', label: '夸克网盘' }]" /></label>
        <label class="block space-y-1 text-sm">账号名称<Input v-model="name" required placeholder="家庭账号" /></label>
        <label class="block space-y-1 text-sm">凭据<Input v-model="credential" type="password" autocomplete="new-password" :placeholder="editing ? '留空则保留原凭据' : '只在提交时发送，不会回显'" :required="!editing" /></label>
        <Button type="submit" class="w-full">{{ editing ? '保存修改' : '添加并加密保存' }}</Button>
      </form>
    </Dialog>
  </div>
</template>
