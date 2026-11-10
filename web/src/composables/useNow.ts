import { onMounted, onUnmounted, ref } from 'vue'

// 每 intervalMs 刷新一次的当前时间戳：给「已等待多久」这类相对时间文案做定时重渲染。
// 这是时钟节拍而非数据轮询，数据刷新一律走 vue-query。
export function useNow(intervalMs = 30_000) {
  const now = ref(Date.now())
  let timer: ReturnType<typeof setInterval> | undefined

  onMounted(() => {
    timer = setInterval(() => {
      now.value = Date.now()
    }, intervalMs)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return now
}
