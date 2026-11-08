<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  AlertCircle,
  Check,
  Cloud,
  HardDrive,
  RefreshCw,
  Sparkles,
  Trash2,
  User,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Switch from '@/components/ui/Switch.vue'
import type { Account } from '@/lib/api'

const props = defineProps<{
  account: Account
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'refresh', id: number): void
  (e: 'remove', id: number): void
  (e: 'toggle', acc: Account): void
  (e: 'set-primary', acc: Account): void
}>()

const info = computed(() => props.account.info || {})
const isConnected = computed(() => info.value.connected !== false)
const userName = computed(() => info.value.user_name || props.account.name || '已连接账号')
const avatar = computed(() => info.value.avatar || '')

// 计算使用百分比进度条
const usedPct = computed(() => {
  const used = info.value.used_space || ''
  const total = info.value.total_space || ''
  if (!used || !total) return 0
  // 简易正则提取数字与单位换算
  function toGb(str: string): number {
    const m = str.match(/([\d.]+)\s*([KMGTP]?B)/i)
    if (!m) return 0
    const n = parseFloat(m[1])
    const unit = (m[2] || '').toUpperCase()
    if (unit.startsWith('T')) return n * 1024
    if (unit.startsWith('G')) return n
    if (unit.startsWith('M')) return n / 1024
    return n
  }
  const uG = toGb(used)
  const tG = toGb(total)
  if (tG <= 0) return 0
  return Math.min(100, Math.round((uG / tG) * 100))
})
</script>

<template>
  <div
    class="relative overflow-hidden rounded-2xl border transition-all duration-200"
    :class="[
      account.is_enabled
        ? 'border-white/10 bg-zinc-900/70 shadow-sm backdrop-blur-md'
        : 'border-white/5 bg-zinc-950/40 opacity-55',
    ]"
  >
    <!-- 顶部状态指示横条 (启用时微光) -->
    <div
      class="h-0.5 w-full transition-colors"
      :class="account.is_enabled ? (account.provider === '115' ? 'bg-blue-500' : 'bg-emerald-500') : 'bg-zinc-800'"
    />

    <div class="p-4 sm:p-5 space-y-4">
      <!-- 1. 头部信息：头像/品牌标 + 昵称 + VIP/主号胶囊 + 右侧 Switch/刷新 -->
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-3 min-w-0">
          <!-- 真实网盘头像 / 品牌彩色微章 -->
          <div class="relative shrink-0">
            <img
              v-if="avatar"
              :src="avatar"
              :alt="userName"
              class="h-11 w-11 rounded-2xl object-cover ring-1 ring-white/10 shadow-sm"
            />
            <div
              v-else
              class="h-11 w-11 rounded-2xl flex items-center justify-center font-bold text-sm shadow-inner"
              :class="account.provider === '115' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'"
            >
              {{ account.provider === '115' ? '115' : '夸克' }}
            </div>

            <!-- 右下角网盘类型角标 -->
            <span
              class="absolute -bottom-1 -right-1 px-1 py-0.2 rounded text-[9px] font-mono uppercase font-bold tracking-tighter"
              :class="account.provider === '115' ? 'bg-blue-600 text-white' : 'bg-emerald-600 text-white'"
            >
              {{ account.provider }}
            </span>
          </div>

          <div class="min-w-0">
            <!-- 昵称与 VIP 胶囊 -->
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="font-bold text-white text-sm tracking-tight truncate max-w-[140px] sm:max-w-[200px]">
                {{ userName }}
              </span>

              <!-- VIP 胶囊徽章 (忠实还原 CS 插件) -->
              <span
                v-if="info.is_vip"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30"
              >
                <Sparkles class="h-2.5 w-2.5 text-amber-400" />
                <span>VIP {{ info.vip_expire || '已点亮' }}</span>
              </span>

              <!-- 主账号标记按钮 -->
              <button
                type="button"
                class="px-2 py-0.5 rounded-md text-[10px] font-medium transition-colors cursor-pointer"
                :class="account.is_primary ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30 font-semibold' : 'bg-white/5 text-zinc-500 hover:text-zinc-300 border border-white/5'"
                :title="account.is_primary ? '默认转存主账号' : '点击设为此网盘的默认转存主号'"
                @click="emit('set-primary', account)"
              >
                {{ account.is_primary ? '★ 主账号' : '设为主号' }}
              </button>
            </div>

            <!-- 备注别名与连接健康态 -->
            <p class="text-[11px] text-zinc-400 mt-0.5 flex items-center gap-1.5 truncate">
              <span
                class="h-1.5 w-1.5 rounded-full shrink-0"
                :class="account.is_enabled ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]' : 'bg-zinc-600'"
              />
              <span class="truncate">{{ account.name || '我的网盘' }}</span>
              <span class="text-zinc-600">·</span>
              <span :class="account.is_enabled ? 'text-zinc-300' : 'text-zinc-500'">
                {{ account.is_enabled ? '已启用参与调度' : '已暂停' }}
              </span>
            </p>
          </div>
        </div>

        <!-- 右上角：刷新与启闭 Switch -->
        <div class="flex items-center gap-2 shrink-0">
          <button
            type="button"
            class="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            :title="loading ? '正在刷新容量…' : '刷新网盘容量与状态'"
            :disabled="loading"
            @click="emit('refresh', account.id)"
          >
            <RefreshCw class="h-3.5 w-3.5" :class="loading ? 'animate-spin text-blue-400' : ''" />
          </button>

          <Switch
            :model-value="account.is_enabled"
            @update:model-value="emit('toggle', account)"
          />
        </div>
      </div>

      <!-- 2. 中间容量进度条（忠实还原 CS 插件：已用 XX TB / 总 XX TB，剩余 XX TB） -->
      <div v-if="info.total_space" class="space-y-1.5 rounded-xl bg-zinc-950/60 p-3 border border-white/[0.04] text-xs">
        <div class="flex items-center justify-between text-[11px] font-mono">
          <span class="text-zinc-300">已用 {{ info.used_space || '0 GB' }} / {{ info.total_space }}</span>
          <span class="text-zinc-400">剩余 {{ info.remaining_space || '未知' }}</span>
        </div>

        <!-- 拟物微光进度条 -->
        <div class="h-2 w-full rounded-full bg-zinc-800/80 overflow-hidden p-0.5">
          <div
            class="h-full rounded-full transition-all duration-500"
            :class="account.provider === '115' ? 'bg-gradient-to-r from-blue-500 to-indigo-400 shadow-[0_0_8px_rgba(59,130,246,0.5)]' : 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-[0_0_8px_rgba(16,185,129,0.5)]'"
            :style="{ width: `${usedPct}%` }"
          />
        </div>
      </div>

      <!-- 未刷新容量时的提示卡 -->
      <div v-else class="rounded-xl bg-zinc-950/40 p-2.5 border border-white/[0.04] text-[11px] text-zinc-500 flex items-center justify-between">
        <span>凭据已通过 Fernet 工业级加密存储</span>
        <button
          type="button"
          class="text-blue-400 hover:text-blue-300 transition-colors cursor-pointer font-medium flex items-center gap-1"
          :disabled="loading"
          @click="emit('refresh', account.id)"
        >
          <RefreshCw v-if="loading" class="h-3 w-3 animate-spin text-blue-400" />
          <span>{{ loading ? '正在同步中…' : '点击刷新容量信息 →' }}</span>
        </button>
      </div>

      <!-- 3. 底部操作栏 -->
      <div class="flex items-center justify-between pt-2 border-t border-white/[0.04] text-[11px] text-zinc-500">
        <span class="font-mono">ID: {{ account.id }} · {{ account.provider === '115' ? '115 网盘' : '夸克网盘' }}</span>
        <Button
          variant="ghost"
          size="sm"
          class="h-6 px-2 text-[11px] text-zinc-400 hover:text-rose-400 transition-colors"
          @click="emit('remove', account.id)"
        >
          <Trash2 class="mr-1 h-3 w-3" />
          <span>解绑账号</span>
        </Button>
      </div>
    </div>
  </div>
</template>
