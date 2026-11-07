import { onMounted, onUnmounted, ref } from 'vue'

export interface StreamEvent {
  type: string
  data: Record<string, unknown>
}

type Listener = (event: StreamEvent) => void
const connected = ref(false)
const listeners = new Set<Listener>()
let source: EventSource | null = null
let consumers = 0

function connect() {
  if (source) return
  source = new EventSource('/api/v1/events', { withCredentials: true })
  source.onopen = () => (connected.value = true)
  source.onerror = () => (connected.value = false)
  for (const type of ['task_status', 'candidate_found', 'heartbeat']) {
    source.addEventListener(type, (event) => {
      try {
        const message = event as MessageEvent<string>
        const parsed: StreamEvent = { type, data: JSON.parse(message.data) as Record<string, unknown> }
        listeners.forEach((listener) => listener(parsed))
      } catch {
        // Ignore malformed events; EventSource will keep the stream alive.
      }
    })
  }
}

export function useEvents(onEvent?: Listener) {
  onMounted(() => {
    consumers += 1
    if (onEvent) listeners.add(onEvent)
    connect()
  })
  onUnmounted(() => {
    if (onEvent) listeners.delete(onEvent)
    consumers -= 1
    if (consumers <= 0) {
      source?.close()
      source = null
      connected.value = false
      consumers = 0
    }
  })
  return { connected }
}
