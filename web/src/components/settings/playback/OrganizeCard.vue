<script setup lang="ts">
import { FolderSync } from '@lucide/vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Switch from '@/components/ui/Switch.vue'
import type { Account } from '@/api/drives'

// 与 PlaybackSection 共享同一份 form（organize 部分字段）；目录浏览弹窗由父级持有，经 browse 事件打开
const form = defineModel<Record<string, any>>('form', { required: true })
defineProps<{ accounts: Account[] }>()
const emit = defineEmits<{ browse: [target: string] }>()
</script>

<template>
      <!-- 卡片 C: 全盘整理与字幕 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
          <FolderSync class="h-4 w-4 text-cyan-400" />
          <h3 class="text-sm font-semibold text-fg">全盘整理规则</h3>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1.5">
            <label class="font-medium text-fg">暂存区扫描目录</label>
            <div class="flex gap-2">
              <Input v-model="form.organize_source_path" placeholder="/CSX/_inbox" />
              <Button
                v-if="accounts.length"
                variant="outline"
                size="sm"
                class="shrink-0 text-xs"
                @click="emit('browse', 'organize_source_path')"
              >
                浏览
              </Button>
            </div>
          </div>

          <div class="flex items-center justify-between rounded-xl bg-surface-solid/50 p-3 border border-primary/[0.06] mt-auto">
            <div>
              <p class="font-medium text-fg">字幕自动跟随归位</p>
              <p class="text-[11px] text-subtle">外挂 .srt/.ass 字幕与视频同步命名移动</p>
            </div>
            <Switch v-model="form.organize_include_subtitles" />
          </div>
        </div>
      </div>
</template>
