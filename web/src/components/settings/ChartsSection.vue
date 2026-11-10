<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Flame } from '@lucide/vue'
import Input from '@/components/ui/Input.vue'
import Switch from '@/components/ui/Switch.vue'
import { settingsApi } from '@/api/settings'

const form = ref<Record<string, any>>({
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
})

const chartTab = ref<'global' | 'douban' | 'tmdb' | 'bangumi' | 'mikan'>('global')

// 15 个搜索源自描述状态

async function loadSettings() {
  try {
    const b = await settingsApi.getSection('baseline')
    Object.assign(form.value, b)
  } catch (cause) {
    console.error(cause)
  }
}

function collectBaseline() {
  return {
    auto_subscribe_enabled: form.value.auto_subscribe_enabled,
    auto_subscribe_min_vote: Number(form.value.auto_subscribe_min_vote),
    auto_subscribe_min_year: Number(form.value.auto_subscribe_min_year),
  }
}

defineExpose({ collectBaseline })

onMounted(() => {
  void loadSettings()
})
</script>

<template>
    <!-- 3. 榜单自动订阅 (移入原 CS 插件榜单订阅能力) -->
    <div class="space-y-5">
      <div class="apple-glass rounded-2xl p-5 space-y-4">
        <div class="flex items-center justify-between border-b border-primary/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Flame class="h-4 w-4 text-orange-400" />
            <h3 class="text-sm font-semibold text-fg">全网榜单自动订阅</h3>
          </div>
          <Switch v-model="form.auto_subscribe_enabled" />
        </div>

        <p class="text-xs text-muted">
          每日定时扫描全网各大流行榜单（豆瓣高分/热门、TMDB 流行剧集、Bangumi 番剧周更与 Mikan 番组），命中高分作品自动建档追更并全网搜源。
        </p>

        <!-- 榜单平台水平小标签 -->
        <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-2 text-xs">
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'global' ? 'bg-primary/10 text-fg' : 'text-muted hover:text-fg'"
            @click="chartTab = 'global'"
          >
            全局调度
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'douban' ? 'bg-primary/10 text-fg' : 'text-muted hover:text-fg'"
            @click="chartTab = 'douban'"
          >
            豆瓣
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'tmdb' ? 'bg-primary/10 text-fg' : 'text-muted hover:text-fg'"
            @click="chartTab = 'tmdb'"
          >
            TMDB
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'bangumi' ? 'bg-primary/10 text-fg' : 'text-muted hover:text-fg'"
            @click="chartTab = 'bangumi'"
          >
            Bangumi 番组
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer"
            :class="chartTab === 'mikan' ? 'bg-primary/10 text-fg' : 'text-muted hover:text-fg'"
            @click="chartTab = 'mikan'"
          >
            Mikan 蜜柑
          </button>
        </div>

        <!-- 榜单各选项卡配置 -->
        <div v-if="chartTab === 'global'" class="grid gap-4 sm:grid-cols-2 text-xs pt-2">
          <div class="space-y-1.5">
            <label class="font-medium text-fg">榜单抓取周期 Cron</label>
            <Input v-model="form.auto_subscribe_cron" placeholder="0 8,20 * * *" />
          </div>

          <div class="space-y-1.5">
            <label class="font-medium text-fg">榜单自动订阅最低评分</label>
            <Input v-model.number="form.auto_subscribe_min_vote" type="number" step="0.1" min="0" max="10" />
          </div>

          <div class="space-y-1.5">
            <label class="font-medium text-fg">影视上映年份门槛</label>
            <Input v-model.number="form.auto_subscribe_min_year" type="number" min="2000" />
          </div>

          <div class="flex items-center justify-between rounded-xl bg-surface-solid/50 p-3 border border-primary/[0.06] mt-auto">
            <div>
              <p class="font-medium text-fg">榜单抓取结果通知</p>
              <p class="text-[11px] text-subtle">发现新高分影视建档后推送到通知渠道</p>
            </div>
            <Switch v-model="form.auto_subscribe_notify" />
          </div>
        </div>

        <div v-else-if="chartTab === 'douban'" class="space-y-3.5 text-xs pt-2">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-fg">启用豆瓣榜单自动订阅</p>
              <p class="text-[11px] text-subtle">定时抓取豆瓣电影热门榜、一周口碑榜与高分榜</p>
            </div>
            <Switch v-model="form.auto_subscribe_douban_enabled" />
          </div>

          <div class="grid gap-3 sm:grid-cols-2 pt-2 border-t border-primary/[0.06]">
            <div class="space-y-1.5">
              <label class="font-medium text-fg">豆瓣最低评分过滤</label>
              <Input v-model.number="form.auto_subscribe_douban_min_vote" type="number" step="0.1" />
            </div>

            <div class="flex items-center justify-between rounded-xl bg-surface-solid/50 p-3 border border-primary/[0.06]">
              <div>
                <p class="font-medium text-fg">豆瓣实时热门影视</p>
                <p class="text-[11px] text-subtle">跟踪最新上映爆款热播剧集</p>
              </div>
              <Switch v-model="form.auto_subscribe_douban_hot" />
            </div>
          </div>
        </div>

        <div v-else-if="chartTab === 'tmdb'" class="space-y-3.5 text-xs pt-2">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-fg">启用 TMDB 全球趋势榜单</p>
              <p class="text-[11px] text-subtle">同步全球流媒体平台（Netflix、HBO、Disney+）今日热度榜</p>
            </div>
            <Switch v-model="form.auto_subscribe_tmdb_enabled" />
          </div>

          <div class="space-y-1.5 pt-2 border-t border-primary/[0.06]">
            <label class="font-medium text-fg">TMDB 最低大众评分</label>
            <Input v-model.number="form.auto_subscribe_tmdb_min_vote" type="number" step="0.1" />
          </div>
        </div>

        <div v-else-if="chartTab === 'bangumi'" class="space-y-3.5 text-xs pt-2">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-fg">启用 Bangumi 每日放送番组榜单</p>
              <p class="text-[11px] text-subtle">自动同步二次元新番排期表与高分新季动画</p>
            </div>
            <Switch v-model="form.auto_subscribe_bangumi_enabled" />
          </div>

          <div class="space-y-1.5 pt-2 border-t border-primary/[0.06]">
            <label class="font-medium text-fg">Bangumi 评分过滤门槛</label>
            <Input v-model.number="form.auto_subscribe_bangumi_min_vote" type="number" step="0.1" />
          </div>
        </div>

        <div v-else-if="chartTab === 'mikan'" class="space-y-3.5 text-xs pt-2">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-fg">启用 Mikan 蜜柑计划当季番剧追踪</p>
              <p class="text-[11px] text-subtle">自动解析蜜柑日历，关联字幕组番组快速转存</p>
            </div>
            <Switch v-model="form.auto_subscribe_mikan_enabled" />
          </div>
        </div>
      </div>
    </div>
</template>
