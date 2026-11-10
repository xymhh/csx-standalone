<script setup lang="ts">
import { FolderOpen } from '@lucide/vue'
import Input from '@/components/ui/Input.vue'
import Switch from '@/components/ui/Switch.vue'

// 与 DramaSection 共享同一份 form（分层目录字段）
const form = defineModel<Record<string, any>>('form', { required: true })
const emit = defineEmits<{ navigate: [value: string] }>()
</script>

<template>
  <!-- 存储路径说明卡片 -->
  <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
    <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
      <FolderOpen class="h-4 w-4 text-emerald-400" />
      <h3 class="text-sm font-semibold text-fg">网盘存储位置与分层</h3>
    </div>

    <div class="grid gap-3 sm:grid-cols-2">
      <div class="rounded-xl border border-primary/[0.06] bg-surface-solid/50 p-3 space-y-1">
        <p class="font-medium text-fg">落盘位置由账号卡片决定</p>
        <p class="text-[11px] leading-relaxed text-subtle">
          每个网盘账号各自的「📦 转存暂存路径」与「🎬 媒体库归档路径」就是文件真实落点，
          转存时优先用主号、主号受限自动换已启用的备用号，路径随所用账号生效。
          要改路径请到
          <button type="button" class="text-emerald-400 underline decoration-dotted" @click="emit('navigate', 'accounts')">
            网盘账号
          </button>
          页面点对应账号的「选择目录」，本页不再重复设置根目录。
        </p>
      </div>

      <div class="space-y-3">
        <div class="flex items-center justify-between rounded-xl bg-surface-solid/50 p-3 border border-primary/[0.06]">
          <div>
            <p class="font-medium text-fg">按媒体类型分层</p>
            <p class="text-[11px] text-subtle">在媒体库路径下自动加一级分类目录</p>
          </div>
          <Switch v-model="form.type_folder_enabled" />
        </div>
        <div v-if="form.type_folder_enabled" class="grid grid-cols-2 gap-2">
          <div class="space-y-1">
            <label class="text-[11px] text-muted">电影目录名</label>
            <Input v-model="form.type_folder_movie" placeholder="电影" />
          </div>
          <div class="space-y-1">
            <label class="text-[11px] text-muted">剧集目录名</label>
            <Input v-model="form.type_folder_tv" placeholder="电视剧" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
