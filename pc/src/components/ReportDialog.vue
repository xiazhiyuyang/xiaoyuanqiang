<template>
  <Modal :model-value="modelValue" title="举报内容" size="sm" @update:model-value="v => emit('update:modelValue', v)">
    <div class="report">
      <p class="report-tip muted">请选择举报原因，我们会尽快核实处理。恶意举报将影响账号信用。</p>
      <div class="reason-grid">
        <button
          v-for="(label, key) in reasons" :key="key" type="button"
          class="reason" :class="{ active: reason === key }"
          @click="reason = key"
        >{{ label }}</button>
      </div>
      <textarea v-model="detail" class="textarea" rows="3" maxlength="500" placeholder="补充说明（选填，最多 500 字）" />
      <p v-if="error" class="field-error">{{ error }}</p>
    </div>
    <template #footer>
      <button class="btn btn-ghost" @click="emit('update:modelValue', false)">取消</button>
      <button class="btn btn-primary" :disabled="submitting" @click="submit">
        {{ submitting ? '提交中…' : '提交举报' }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import Modal from './Modal.vue'
import api from '../api'
import { toast } from '../utils/toast'

const props = defineProps({
  modelValue: Boolean,
  targetType: { type: String, required: true }, // post | comment | user | message
  targetId: { type: [Number, String], required: true },
})
const emit = defineEmits(['update:modelValue', 'done'])

const reasons = {
  spam: '垃圾广告', porn: '色情低俗', abuse: '辱骂/人身攻击', violence: '暴力血腥',
  fraud: '诈骗/虚假信息', privacy: '泄露隐私', illegal: '违法违规', other: '其他',
}
const reason = ref('spam')
const detail = ref('')
const error = ref('')
const submitting = ref(false)

watch(() => props.modelValue, (v) => { if (v) { reason.value = 'spam'; detail.value = ''; error.value = '' } })

async function submit() {
  error.value = ''
  submitting.value = true
  try {
    await api.createReport({
      target_type: props.targetType,
      target_id: Number(props.targetId),
      reason: reason.value,
      detail: detail.value || null,
    })
    toast.success('举报已提交，我们会尽快处理')
    emit('update:modelValue', false)
    emit('done')
  } catch (e) {
    error.value = e.message || '提交失败，请稍后再试'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.report-tip { font-size: 13px; margin-bottom: 14px; }
.reason-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 14px; }
.reason {
  padding: 9px 10px; border-radius: var(--r-sm); font-size: 13.5px;
  border: 1px solid var(--line-strong); background: var(--surface-2);
  color: var(--ink-2); transition: all var(--t-fast) var(--ease-out);
}
.reason:hover { border-color: var(--brand-400); }
.reason.active { border-color: var(--brand-600); background: var(--brand-50); color: var(--brand-700); font-weight: 600; }
.field-error { margin-top: 8px; }
</style>
