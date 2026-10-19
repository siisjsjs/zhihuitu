/** 产线平衡工作台共享状态：当前款式 / 方案 / 步骤选择，跨标签页复用。 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import lb, { type Style, type Plan } from '@/api/lineBalance'

export const useLineBalanceStore = defineStore('lineBalance', () => {
  const currentStyle = ref<Style | null>(null)
  const currentPlan = ref<Plan | null>(null)
  const step = ref(0) // 0 工序 1 编码 2 寻优 3 裁片 4 SOP

  async function setStyle(s: Style | null) {
    currentStyle.value = s
    currentPlan.value = null
    if (s) {
      step.value = Math.max(step.value, 0)
      // 恢复上次选用的方案，免去重新选择
      try {
        const { plan } = await lb.selectedPlan(s.id)
        if (plan) currentPlan.value = plan
      } catch { /* 无选用方案时忽略 */ }
    }
  }

  /** 选用方案并持久化（同款式唯一）。 */
  async function selectPlan(p: Plan) {
    currentPlan.value = p
    try { await lb.selectPlan(p.id) } catch { /* */ }
  }

  function setPlan(p: Plan | null) {
    currentPlan.value = p
  }

  function goStep(n: number) {
    step.value = n
  }

  function reset() {
    currentStyle.value = null
    currentPlan.value = null
    step.value = 0
  }

  return { currentStyle, currentPlan, step, setStyle, selectPlan, setPlan, goStep, reset }
})
