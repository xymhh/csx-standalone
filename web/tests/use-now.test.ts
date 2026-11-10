import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useNow } from '@/composables/useNow'

function mountNow(intervalMs: number) {
  const Comp = defineComponent({
    setup() {
      const now = useNow(intervalMs)
      return () => h('span', String(now.value))
    },
  })
  return mount(Comp)
}

describe('composables/useNow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('挂载后按间隔刷新时间戳，卸载后停止', async () => {
    const start = Date.now()
    const wrapper = mountNow(1000)
    expect(Number(wrapper.text())).toBe(start)

    vi.advanceTimersByTime(3000)
    await nextTick()
    expect(Number(wrapper.text())).toBe(start + 3000)

    wrapper.unmount()
    vi.advanceTimersByTime(5000)
    await nextTick()
    expect(Number(wrapper.text())).toBe(start + 3000)
  })
})
