<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="modal-mask" @click.self="onMask" role="dialog" aria-modal="true">
        <div class="modal-panel" :class="sizeClass" :style="panelStyle">
          <header v-if="title || $slots.header" class="modal-head">
            <slot name="header"><h3>{{ title }}</h3></slot>
            <button v-if="closable" class="modal-close" aria-label="关闭" @click="close"><Icon name="x" :size="18" /></button>
          </header>
          <div class="modal-body" :class="{ 'no-pad': bodyPad === false }">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="modal-foot"><slot name="footer" /></footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  modelValue: Boolean,
  title: { type: String, default: '' },
  size: { type: String, default: 'md' }, // sm md lg
  closable: { type: Boolean, default: true },
  closeOnMask: { type: Boolean, default: true },
  bodyPad: { type: Boolean, default: true },
  width: { type: [Number, String], default: null },
})
const emit = defineEmits(['update:modelValue', 'close'])

const sizeClass = { sm: 'm-sm', md: 'm-md', lg: 'm-lg' }[props.size]
const panelStyle = props.width ? { maxWidth: typeof props.width === 'number' ? props.width + 'px' : props.width } : {}

function close() { emit('update:modelValue', false); emit('close') }
function onMask() { if (props.closeOnMask && props.closable) close() }
function onKey(e) { if (e.key === 'Escape' && props.closable) close() }

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', onKey)
    } else {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKey)
    }
  }
)
onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.modal-mask {
  position: fixed; inset: 0; z-index: var(--z-modal);
  background: color-mix(in srgb, var(--ink) 42%, transparent);
  backdrop-filter: blur(3px); -webkit-backdrop-filter: blur(3px);
  display: flex; align-items: flex-start; justify-content: center;
  padding: 6vh 20px; overflow-y: auto;
}
.modal-panel {
  width: 100%; background: var(--surface); border-radius: var(--r-lg);
  box-shadow: var(--shadow-lg); margin: auto; overflow: hidden;
  display: flex; flex-direction: column; max-height: 88vh;
}
.m-sm { max-width: 420px; }
.m-md { max-width: 560px; }
.m-lg { max-width: 760px; }
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px 12px;
}
.modal-head h3 { font-size: 17px; }
.modal-close {
  width: 32px; height: 32px; border-radius: 50%; color: var(--ink-3);
  display: flex; align-items: center; justify-content: center;
  transition: background var(--t-fast), color var(--t-fast);
}
.modal-close:hover { background: var(--surface-3); color: var(--ink); }
.modal-body { padding: 4px 20px 20px; overflow-y: auto; }
.modal-body.no-pad { padding: 0; }
.modal-foot {
  display: flex; justify-content: flex-end; gap: 10px;
  padding: 14px 20px; border-top: 1px solid var(--line); background: var(--surface-2);
}
.modal-enter-active, .modal-leave-active { transition: opacity var(--t-base) var(--ease-out); }
.modal-enter-active .modal-panel, .modal-leave-active .modal-panel {
  transition: transform var(--t-base) var(--ease-out), opacity var(--t-base) var(--ease-out);
}
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-panel, .modal-leave-to .modal-panel {
  opacity: 0; transform: translateY(14px) scale(.985);
}
</style>
