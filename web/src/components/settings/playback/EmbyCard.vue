<script setup lang="ts">
import { Film } from '@lucide/vue'
import Input from '@/components/ui/Input.vue'
import Switch from '@/components/ui/Switch.vue'

// 与 PlaybackSection 共享同一份 form（emby 部分字段）
const form = defineModel<Record<string, any>>('form', { required: true })
</script>

<template>
        <!-- 卡片 B: Emby 与媒体库联动 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
            <Film class="h-4 w-4 text-purple-400" />
            <h3 class="text-sm font-semibold text-fg">Emby / Jellyfin 联动</h3>
          </div>

          <div class="space-y-3.5 text-xs">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-fg">入库自动刷新媒体库</p>
                <p class="text-[11px] text-subtle">新剧入库后触发媒体服务器自动扫描</p>
              </div>
              <Switch v-model="form.emby_refresh_enabled" />
            </div>

            <div class="space-y-1.5">
              <label class="font-medium text-fg">服务器地址</label>
              <Input v-model="form.emby_url" placeholder="http://172.18.0.x:8096" />
            </div>

            <div class="space-y-1.5">
              <label class="font-medium text-fg">API 密钥</label>
              <Input v-model="form.emby_api_key" type="password" placeholder="粘贴 Emby API Key" />
            </div>
          </div>
        </div>
</template>
