import { onMounted, onUnmounted, ref } from 'vue'

export function usePrefersReducedMotion() {
  const reduced = ref(false)
  let mq: MediaQueryList | null = null

  function sync() {
    reduced.value =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  onMounted(() => {
    sync()
    mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    mq.addEventListener('change', sync)
  })

  onUnmounted(() => {
    mq?.removeEventListener('change', sync)
  })

  return reduced
}
