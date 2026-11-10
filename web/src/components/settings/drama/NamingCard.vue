<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Sparkles } from '@lucide/vue'
import { type NamingVariable, type NamingPreview, namingApi } from '@/api/naming'

// 重命名模板（MoviePilot 方案）：状态与预览逻辑自包含，保存由父级 saveAll 编排时调用 saveNaming
const naming = ref({ movie_format: '', tv_format: '', variety_format: '' })
const namingDefaults = ref({ movie_format: '', tv_format: '', variety_format: '' })
const namingVariables = ref<NamingVariable[]>([])
const namingPreview = ref<Record<'movie' | 'tv', NamingPreview>>({
  movie: { valid: true, message: '', relative_path: '' },
  tv: { valid: true, message: '', relative_path: '' },
})
const namingError = ref('')
const activeTemplate = ref<'movie' | 'tv'>('movie')
const movieTemplateEl = ref<HTMLTextAreaElement | null>(null)
const tvTemplateEl = ref<HTMLTextAreaElement | null>(null)
let namingTimer = 0

async function loadNaming() {
  try {
    const data = await namingApi.get()
    naming.value = {
      movie_format: data.movie_format,
      tv_format: data.tv_format,
      variety_format: data.variety_format,
    }
    namingDefaults.value = data.defaults
    namingVariables.value = data.variables
    await refreshNamingPreview()
  } catch (cause) {
    console.error(cause)
  }
}

async function refreshNamingPreview() {
  try {
    const [movie, tv] = await Promise.all([
      namingApi.preview({
        media_type: 'movie',
        title: '示例电影',
        year: 2024,
        extension: 'mkv',
        quality_bucket: '1080p',
        template: naming.value.movie_format,
      }),
      namingApi.preview({
        media_type: 'tv',
        title: '示例剧集',
        year: 2024,
        season: 1,
        episode: 1,
        extension: 'mkv',
        quality_bucket: '4k',
        template: naming.value.tv_format,
      }),
    ])
    namingPreview.value = { movie, tv }
  } catch (cause) {
    console.error(cause)
  }
}

function scheduleNamingPreview() {
  if (namingTimer) window.clearTimeout(namingTimer)
  namingTimer = window.setTimeout(() => {
    void refreshNamingPreview()
  }, 300)
}

function restoreNamingDefaults() {
  naming.value = { ...namingDefaults.value }
  void refreshNamingPreview()
}

function insertNamingVariable(name: string) {
  const key = activeTemplate.value === 'tv' ? 'tv_format' : 'movie_format'
  const el = activeTemplate.value === 'tv' ? tvTemplateEl.value : movieTemplateEl.value
  const token = `{{${name}}}`
  const current = naming.value[key]
  const start = el?.selectionStart ?? current.length
  const end = el?.selectionEnd ?? current.length
  naming.value[key] = current.slice(0, start) + token + current.slice(end)
  scheduleNamingPreview()
  requestAnimationFrame(() => {
    el?.focus()
    el?.setSelectionRange(start + token.length, start + token.length)
  })
}

// 保存重命名模板：失败不抛错，返回错误信息供父级拼提示（与原 saveAll 语义一致）
async function saveNaming(): Promise<string> {
  namingError.value = ''
  try {
    const data = await namingApi.update({
      movie_format: naming.value.movie_format,
      tv_format: naming.value.tv_format,
      variety_format: naming.value.variety_format,
    })
    naming.value = {
      movie_format: data.movie_format,
      tv_format: data.tv_format,
      variety_format: data.variety_format,
    }
    return ''
  } catch (cause) {
    namingError.value = cause instanceof Error ? cause.message : '重命名模板未保存'
    return namingError.value
  }
}

defineExpose({ saveNaming })

onMounted(() => {
  void loadNaming()
})
</script>

<template>
  <!-- 重命名规则（MoviePilot 模板方案） -->
  <div class="apple-glass rounded-2xl p-5 space-y-4 text-xs">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-primary/[0.06] pb-3">
      <div class="flex items-center gap-2">
        <Sparkles class="h-4 w-4 text-sky-400" />
        <h3 class="text-sm font-semibold text-fg">重命名规则</h3>
        <span class="rounded-full bg-sky-500/10 px-2 py-0.5 text-[10px] text-sky-300">MoviePilot 模板</span>
      </div>
      <button
        type="button"
        class="text-[11px] text-muted transition-colors hover:text-fg"
        @click="restoreNamingDefaults"
      >
        恢复 MP 默认
      </button>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <label class="text-fg-2">电影命名模板</label>
          <span class="text-[10px] text-faint">示例：示例电影 (2024)</span>
        </div>
        <textarea
          ref="movieTemplateEl"
          v-model="naming.movie_format"
          rows="3"
          spellcheck="false"
          class="w-full resize-y rounded-xl border border-primary/[0.08] bg-canvas/60 p-3 font-mono text-[11px] leading-relaxed text-emerald-200 outline-none transition-colors focus:border-emerald-500/40"
          @focus="activeTemplate = 'movie'"
          @input="scheduleNamingPreview"
        />
        <p
          class="truncate font-mono text-[11px]"
          :class="namingPreview.movie.valid ? 'text-subtle' : 'text-rose-400'"
        >
          {{
            namingPreview.movie.valid
              ? `媒体库/${namingPreview.movie.relative_path}`
              : namingPreview.movie.message
          }}
        </p>
      </div>

      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <label class="text-fg-2">剧集命名模板</label>
          <span class="text-[10px] text-faint">示例：示例剧集 (2024) S01</span>
        </div>
        <textarea
          ref="tvTemplateEl"
          v-model="naming.tv_format"
          rows="3"
          spellcheck="false"
          class="w-full resize-y rounded-xl border border-primary/[0.08] bg-canvas/60 p-3 font-mono text-[11px] leading-relaxed text-emerald-200 outline-none transition-colors focus:border-emerald-500/40"
          @focus="activeTemplate = 'tv'"
          @input="scheduleNamingPreview"
        />
        <p
          class="truncate font-mono text-[11px]"
          :class="namingPreview.tv.valid ? 'text-subtle' : 'text-rose-400'"
        >
          {{
            namingPreview.tv.valid
              ? `媒体库/${namingPreview.tv.relative_path}`
              : namingPreview.tv.message
          }}
        </p>
      </div>
    </div>

    <div class="space-y-2">
      <p class="text-[11px] text-subtle">
        点击变量插入到光标处 · 当前插入目标：{{ activeTemplate === 'tv' ? '剧集模板' : '电影模板' }}
      </p>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="variable in namingVariables"
          :key="variable.name"
          type="button"
          class="rounded-lg border border-primary/[0.08] bg-surface-solid/60 px-2 py-1 font-mono text-[10px] text-fg-2 transition-colors hover:border-emerald-500/40 hover:text-emerald-300"
          :title="`${variable.label}｜示例：${variable.example}`"
          @click="insertNamingVariable(variable.name)"
        >
          {{ variable.name }}
        </button>
      </div>
    </div>

    <p v-if="namingError" class="text-[11px] text-rose-400">{{ namingError }}</p>
    <p class="text-[11px] leading-relaxed text-subtle">
      <code class="text-muted">/</code> 分隔目录层级，最后一段是文件名；
      <code v-pre class="text-muted">{{fileExt}}</code> 自带点号；变量为空时对应条件段自动消失。
    </p>
  </div>
</template>
