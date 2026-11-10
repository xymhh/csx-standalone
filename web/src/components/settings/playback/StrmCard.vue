<script setup lang="ts">
import { PlaySquare } from '@lucide/vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'

// 与 PlaybackSection 共享同一份 form（strm 部分字段）
const form = defineModel<Record<string, any>>('form', { required: true })
</script>

<template>
        <!-- 卡片 A: STRM 直链播放 -->
        <div class="apple-glass rounded-2xl p-5 space-y-4">
          <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
            <PlaySquare class="h-4 w-4 text-emerald-400" />
            <h3 class="text-sm font-semibold text-fg">STRM 原画直链</h3>
          </div>

          <div class="space-y-3.5 text-xs">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-fg">自动生成 STRM</p>
                <p class="text-[11px] text-subtle">转存后自动为 Emby/Jellyfin 生成播放条目</p>
              </div>
              <Switch v-model="form.strm_generate_enabled" />
            </div>

            <div class="space-y-1.5">
              <label class="font-medium text-fg">播放跳转模式</label>
              <Select
                v-model="form.strm_mode"
                :options="[
                  { value: 'direct_302', label: '302 原画直链跳转 (推荐·零流量)' },
                  { value: 'local_mount', label: '本地挂载路径 (CloudDrive/Alist)' },
                ]"
              />
            </div>

            <div class="space-y-1.5">
              <label class="font-medium text-fg">STRM 文件输出目录</label>
              <Input v-model="form.strm_root" placeholder="/strm" />
            </div>

            <div v-if="form.strm_mode === 'direct_302'" class="space-y-1.5">
              <label class="font-medium text-fg">站点公开地址</label>
              <Input v-model="form.strm_public_base_url" placeholder="https://csx.你的域名" />
              <p class="text-[11px] text-subtle">
                播放器访问本服务用的地址，302 跳转会拼在这后面；留空则只有手动同步能生成 STRM
              </p>
            </div>
          </div>
        </div>
</template>
