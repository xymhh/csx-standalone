<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { Cloud, HardDrive, QrCode, RefreshCw } from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import DirectorySelectDialog from '@/components/dialogs/DirectorySelectDialog.vue'
import AccountCard from '@/components/config/AccountCard.vue'
import { useToast } from '@/composables/useToast'
import { type Account, type QrcodeStartResponse, accountsApi } from '@/api/drives'

const { toast } = useToast()

// 目录树选择
const dirDialogOpen = ref(false)
const dirTarget = ref('account_path')

// 账号列表走全局共享查询（与传输页共用 ['accounts']）
const accountsQuery = useQuery({
  queryKey: ['accounts'],
  queryFn: () => accountsApi.list(),
})
const accounts = computed(() => accountsQuery.data.value ?? [])

const newAccountProvider = ref<'115' | 'quark'>('115')
const newAccountName = ref('')
const newAccountCookie = ref('')
const addingAccount = ref(false)

const qrOpen = ref(false)
const qrProvider = ref<'115' | 'quark'>('115')
const qrName = ref('我的115账号')
const qrData = ref<QrcodeStartResponse | null>(null)
const qrStatus = ref<'idle' | 'starting' | 'waiting' | 'scanned' | 'success' | 'expired' | 'error'>('idle')
const qrMessage = ref('')
const qrStarting = ref(false)
const qrPolling = ref(false)
let qrGeneration = 0

// 目录树选择

async function loadAccounts() {
  await accountsQuery.refetch()
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

function stopQrcodePolling() {
  qrPolling.value = false
}

function closeQrcode() {
  qrGeneration += 1
  stopQrcodePolling()
  qrOpen.value = false
  qrData.value = null
  qrStatus.value = 'idle'
}

// 扫码状态轮询：每 2 秒查一次（与改造前的 setInterval 轮询同间隔），
// 会话以 token_data 为查询键，重新生成/关闭弹窗即换键停轮询
const qrCheckQuery = useQuery({
  queryKey: computed(() => ['accounts', 'qrcode', qrData.value?.token_data ?? ''] as const),
  queryFn: () => {
    const session = qrData.value as QrcodeStartResponse
    return accountsApi.checkQrcode({
      provider: session.provider,
      token_data: session.token_data,
      name: qrName.value.trim(),
      auto_save: true,
    })
  },
  enabled: computed(() => qrPolling.value && !!qrData.value && qrOpen.value),
  refetchInterval: 2000,
})

watch(
  () => qrCheckQuery.data.value,
  async (result) => {
    if (!result || !qrOpen.value || !qrData.value) return
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
  },
)

watch(
  () => qrCheckQuery.error.value,
  (cause) => {
    if (cause && qrPolling.value && qrOpen.value) {
      qrMessage.value = '检测重试中…'
    }
  },
)

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
    qrPolling.value = true
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
        a.is_primary = a.id === account.id
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

async function handleAccountDirSelect(path: string) {
  if (dirTarget.value === 'account_path' && targetAccountForBrowse.value) {
    const acc = targetAccountForBrowse.value
    const updatePayload = targetPathType.value === 'transfer' ? { transfer_path: path } : { media_path: path }
    try {
      await accountsApi.update(acc.id, updatePayload)
      if (targetPathType.value === 'transfer') acc.transfer_path = path
      else acc.media_path = path
      toast(`已更新 ${acc.name} 的${targetPathType.value === 'transfer' ? '转存路径' : '媒体库路径'}`, 'success')
    } catch (cause) {
      toast(cause instanceof Error ? cause.message : '更新目录失败', 'error')
    }
  }
  dirDialogOpen.value = false
}
</script>

<template>
  <!-- 1. 网盘账号 (既能输入 Cookie 也能扫码) -->
  <div class="space-y-5">
    <!-- 新增网盘账号卡片：输入框集成扫码 Icon -->
    <div class="apple-glass rounded-2xl p-5 space-y-4">
      <div class="flex items-center justify-between border-b border-primary/[0.06] pb-3">
        <div class="flex items-center gap-2">
          <Cloud class="h-4 w-4 text-blue-400" />
          <h3 class="text-sm font-semibold text-fg">添加网盘账号</h3>
        </div>
        <span class="text-[11px] text-muted">支持直接粘贴 Cookie，或点击右侧扫码图标手机扫码免密登录</span>
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
            class="w-full h-9 rounded-xl border border-primary/10 bg-surface-solid/60 pl-3 pr-10 text-xs text-fg placeholder-subtle outline-none focus:border-primary/20 transition-colors"
          />
          <button
            type="button"
            class="absolute right-1.5 p-1.5 rounded-lg text-muted hover:text-fg hover:bg-primary/10 transition-colors cursor-pointer"
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
      <h4 class="text-xs font-semibold text-muted uppercase tracking-wider">已连接的网盘</h4>

      <div v-if="!accounts.length" class="apple-glass rounded-2xl p-12 text-center space-y-2">
        <HardDrive class="mx-auto h-7 w-7 text-faint" />
        <p class="text-sm font-semibold text-fg">尚未绑定任何网盘</p>
        <p class="text-xs text-subtle">在上方粘贴 Cookie 或点击右侧扫码图标，即可绑定你的 115 或夸克网盘。</p>
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

    <!-- 扫码绑定网盘 Dialog -->
    <Dialog :open="qrOpen" :title="`手机扫码绑定 ${qrProvider === '115' ? '115' : '夸克'} 网盘`" @close="closeQrcode">
      <div class="space-y-4">
        <div class="space-y-1 text-xs">
          <span class="text-muted">账号备注名称</span>
          <Input v-model="qrName" placeholder="例如：我的主号" />
        </div>

        <div
          class="flex flex-col items-center justify-center rounded-2xl border border-primary/10 bg-surface-solid/60 p-6"
        >
          <div v-if="qrData?.qrcode" class="space-y-3 text-center">
            <div class="p-3 bg-primary rounded-2xl inline-block shadow-md">
              <img :src="qrData.qrcode" class="h-44 w-44 object-contain" />
            </div>
            <div class="space-y-1">
              <Badge :tone="qrStatus === 'scanned' ? 'good' : qrStatus === 'expired' ? 'bad' : 'warn'">
                {{
                  qrStatus === 'scanned' ? '已扫码，等待手机端确认' : qrStatus === 'expired' ? '已失效' : '等待手机扫码'
                }}
              </Badge>
              <p class="text-xs text-muted mt-1">{{ qrData.hint }}</p>
            </div>
          </div>
          <div v-else-if="qrStarting" class="py-10 text-center text-xs text-muted space-y-2">
            <RefreshCw class="mx-auto h-5 w-5 animate-spin text-fg" />
            <p>{{ qrMessage }}</p>
          </div>
          <div v-else class="py-10 text-center text-xs text-rose-400">
            <p>{{ qrMessage }}</p>
            <Button variant="outline" size="sm" class="mt-3" @click="startQrcode">重新生成</Button>
          </div>
        </div>

        <Button v-if="qrStatus === 'expired'" class="w-full" @click="startQrcode"> 重新生成二维码 </Button>
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
