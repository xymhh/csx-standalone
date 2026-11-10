// ESLint flat config：务实档位——只拦真实问题（未定义、未使用、Vue 易错用法），
// 不开启与现存代码风格大面积冲突的格式/排序类规则（格式归 Prettier，但不强制全仓执行）。
import js from '@eslint/js'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'

export default defineConfigWithVueTs(
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  js.configs.recommended,
  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      // 项目内 Record<string, any> 是既定的表单/配置载荷写法，不逐处收紧
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      // ui/ 下组件按设计单文件单词命名（Dialog/Button/…）
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    // .vue 模板里用到的变量对脚本作用域分析不可见，SFC 的死代码由 vue-tsc 把关
    files: ['**/*.vue'],
    rules: {
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },
)
