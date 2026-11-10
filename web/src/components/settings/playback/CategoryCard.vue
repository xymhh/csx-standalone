<script setup lang="ts">
import { ref } from 'vue'
import { Layers, Plus, RotateCcw, Trash2 } from '@lucide/vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Switch from '@/components/ui/Switch.vue'

// ── 媒体二级分类（对齐 MoviePilot 的 category.yaml）：配置自包含，
// 父级加载 settings 时经 applyCategory 回填、保存时经 collectCategory 收集 ──
type CategoryRule = { name: string; conditions: Record<string, string> }
const CATEGORY_FIELDS = [
  { value: 'genre_ids', label: '内容类型' },
  { value: 'original_language', label: '语种' },
  { value: 'production_countries', label: '制片国家' },
  { value: 'origin_country', label: '来源国家' },
  { value: 'release_year', label: '发行年份' },
]
const CATEGORY_DEFAULT_MOVIE: CategoryRule[] = [
  { name: '动画电影', conditions: { genre_ids: '16' } },
  { name: '华语电影', conditions: { original_language: 'zh,cn,bo,za' } },
  { name: '外语电影', conditions: {} },
]
const CATEGORY_DEFAULT_TV: CategoryRule[] = [
  { name: '国漫', conditions: { genre_ids: '16', origin_country: 'CN,TW,HK' } },
  { name: '日番', conditions: { genre_ids: '16', origin_country: 'JP' } },
  { name: '纪录片', conditions: { genre_ids: '99' } },
  { name: '儿童', conditions: { genre_ids: '10762' } },
  { name: '综艺', conditions: { genre_ids: '10764,10767' } },
  { name: '国产剧', conditions: { origin_country: 'CN,TW,HK' } },
  { name: '欧美剧', conditions: { origin_country: 'US,FR,GB,DE,ES,IT,NL,PT,RU,UK' } },
  { name: '日韩剧', conditions: { origin_country: 'JP,KP,KR,TH,IN,SG' } },
  { name: '未分类', conditions: {} },
]
const categoryConfig = ref<{ enabled: boolean; movie: CategoryRule[]; tv: CategoryRule[] }>({
  enabled: true,
  movie: JSON.parse(JSON.stringify(CATEGORY_DEFAULT_MOVIE)),
  tv: JSON.parse(JSON.stringify(CATEGORY_DEFAULT_TV)),
})
const categoryTab = ref<'movie' | 'tv'>('movie')
const CATEGORY_TABS = [
  { value: 'movie' as const, label: '电影' },
  { value: 'tv' as const, label: '剧集' },
]

function categoryRules(): CategoryRule[] {
  return categoryConfig.value[categoryTab.value]
}

function addCategoryRule() {
  categoryRules().push({ name: '', conditions: {} })
}

function removeCategoryRule(index: number) {
  categoryRules().splice(index, 1)
}

function moveCategoryRule(index: number, delta: number) {
  const rules = categoryRules()
  const next = index + delta
  if (next < 0 || next >= rules.length) return
  const [item] = rules.splice(index, 1)
  rules.splice(next, 0, item)
}

function addCategoryCondition(rule: CategoryRule) {
  const used = new Set(Object.keys(rule.conditions))
  const field = CATEGORY_FIELDS.find((item) => !used.has(item.value))?.value || 'genre_ids'
  rule.conditions[field] = ''
}

function removeCategoryCondition(rule: CategoryRule, key: string) {
  delete rule.conditions[key]
}

function onCategoryConditionKey(rule: CategoryRule, oldKey: string, event: Event) {
  const target = event.target as HTMLSelectElement | null
  const nextKey = target?.value || oldKey
  if (nextKey === oldKey) return
  const value = rule.conditions[oldKey] ?? ''
  delete rule.conditions[oldKey]
  rule.conditions[nextKey] = value
}

function resetCategoryRules() {
  const source = categoryTab.value === 'movie' ? CATEGORY_DEFAULT_MOVIE : CATEGORY_DEFAULT_TV
  categoryConfig.value[categoryTab.value] = JSON.parse(JSON.stringify(source))
}

// 回填后端 category section（与原 loadSettings 内的应用逻辑一致）
function applyCategory(category: { enabled?: boolean; movie?: CategoryRule[]; tv?: CategoryRule[] }) {
  if (typeof category.enabled === 'boolean') categoryConfig.value.enabled = category.enabled
  if (Array.isArray(category.movie)) categoryConfig.value.movie = category.movie
  if (Array.isArray(category.tv)) categoryConfig.value.tv = category.tv
}

function collectCategory() {
  return {
    enabled: categoryConfig.value.enabled,
    movie: categoryConfig.value.movie,
    tv: categoryConfig.value.tv,
  }
}

defineExpose({ applyCategory, collectCategory })
</script>

<template>
      <!-- 卡片 D: 媒体二级分类 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center justify-between border-b border-primary/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Layers class="h-4 w-4 text-amber-400" />
            <h3 class="text-sm font-semibold text-fg">媒体二级分类</h3>
          </div>
          <Switch v-model="categoryConfig.enabled" />
        </div>
        <p class="text-[11px] leading-relaxed text-subtle">
          启用后媒体会多建一层分类目录，例如「电影/动画电影/片名 (年份)」。规则自上而下匹配，命中第一条即停止；条件留空表示兜底分类。
        </p>
        <div v-if="categoryConfig.enabled" class="space-y-3">
          <div class="flex items-center gap-2">
            <div class="flex rounded-lg bg-surface-solid/60 p-0.5">
              <button
                v-for="tab in CATEGORY_TABS"
                :key="tab.value"
                class="rounded-md px-3 py-1 text-[11px] transition"
                :class="categoryTab === tab.value ? 'bg-primary/10 text-fg' : 'text-subtle hover:text-fg-2'"
                @click="categoryTab = tab.value"
              >
                {{ tab.label }}
              </button>
            </div>
            <span class="ml-auto text-[11px] text-subtle">顺序即优先级</span>
          </div>

          <div class="space-y-2">
            <div
              v-for="(rule, index) in categoryRules()"
              :key="`${categoryTab}-${index}`"
              class="rounded-xl border border-primary/[0.06] bg-surface-solid/40 p-2.5"
            >
              <div class="flex items-center gap-2">
                <span class="w-4 shrink-0 text-center text-[11px] text-faint">{{ index + 1 }}</span>
                <Input v-model="rule.name" placeholder="分类目录名，如 动画电影" class="h-8 flex-1" />
                <div class="flex shrink-0 items-center gap-0.5">
                  <button
                    class="rounded-md p-1 text-subtle hover:bg-primary/5 hover:text-fg disabled:opacity-30"
                    :disabled="index === 0"
                    @click="moveCategoryRule(index, -1)"
                  >↑</button>
                  <button
                    class="rounded-md p-1 text-subtle hover:bg-primary/5 hover:text-fg disabled:opacity-30"
                    :disabled="index === categoryRules().length - 1"
                    @click="moveCategoryRule(index, 1)"
                  >↓</button>
                  <button
                    class="rounded-md p-1 text-subtle hover:bg-rose-500/10 hover:text-rose-400"
                    @click="removeCategoryRule(index)"
                  >
                    <Trash2 class="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <div class="mt-2 flex flex-wrap items-center gap-1.5 pl-6">
                <div
                  v-for="key in Object.keys(rule.conditions)"
                  :key="key"
                  class="flex items-center gap-1 rounded-lg border border-primary/[0.06] bg-surface-2/60 px-1.5 py-1"
                >
                  <select
                    :value="key"
                    class="bg-transparent text-[11px] text-fg-2 outline-none"
                    @change="onCategoryConditionKey(rule, key, $event)"
                  >
                    <option v-for="field in CATEGORY_FIELDS" :key="field.value" :value="field.value">
                      {{ field.label }}
                    </option>
                  </select>
                  <input
                    v-model="rule.conditions[key]"
                    placeholder="16 / CN,TW / 2020-2024"
                    class="w-32 bg-transparent text-[11px] text-fg outline-none placeholder:text-faint"
                  />
                  <button class="text-subtle hover:text-rose-400" @click="removeCategoryCondition(rule, key)">×</button>
                </div>
                <button
                  v-if="Object.keys(rule.conditions).length < 3"
                  class="rounded-lg border border-dashed border-primary/10 px-2 py-1 text-[11px] text-muted hover:border-cyan-400/40 hover:text-cyan-300"
                  @click="addCategoryCondition(rule)"
                >
                  + 条件
                </button>
                <span v-if="!Object.keys(rule.conditions).length" class="text-[11px] text-faint">
                  无条件 → 兜底分类
                </span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" @click="addCategoryRule">
              <Plus class="h-3.5 w-3.5" />添加分类
            </Button>
            <Button variant="ghost" size="sm" @click="resetCategoryRules">
              <RotateCcw class="h-3.5 w-3.5" />恢复 MP 默认
            </Button>
            <span class="ml-auto text-[11px] text-faint">共 {{ categoryRules().length }} 条</span>
          </div>
        </div>
      </div>
</template>
