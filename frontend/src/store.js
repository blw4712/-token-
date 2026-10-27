import { ref } from 'vue'

export const revision = ref(0)
export const scanning = ref(false)

export function bump() {
  revision.value += 1
}
