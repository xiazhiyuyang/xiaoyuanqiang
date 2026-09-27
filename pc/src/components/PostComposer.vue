<template>
  <Modal
    :model-value="modelValue"
    :title="isEdit ? '编辑动态' : '发布动态'"
    size="lg"
    @update:model-value="onClose"
  >
    <div class="composer">
      <div class="field">
        <input v-model="form.title" class="input" maxlength="100" placeholder="一个吸引人的标题（选填）" />
      </div>
      <div class="field">
        <textarea
          v-model="form.content" class="textarea" rows="6" maxlength="10000"
          placeholder="说点什么吧，校园新鲜事、求助、树洞都可以…"
        />
        <div class="counter faint tabular">{{ form.content.length }}/10000</div>
      </div>

      <div class="composer-row">
        <select v-model="form.category_id" class="select grow">
          <option :value="null">选择分类（选填）</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.icon }} {{ c.name }}</option>
        </select>
        <select v-model="form.visibility" class="select">
          <option value="public">公开</option>
          <option value="private">仅自己可见</option>
        </select>
      </div>

      <!-- 图片上传 -->
      <div v-if="!form.video_url" class="media-area">
        <div v-for="(img, i) in form.images" :key="img" class="media-thumb">
          <img :src="mediaUrl(img)" alt="已上传图片" />
          <button class="media-del" aria-label="移除" @click="removeImage(i)"><Icon name="x" :size="14" /></button>
        </div>
        <button
          v-if="form.images.length < 9 && allowImage"
          class="media-add" :disabled="uploading"
          @click="$refs.imgInput.click()"
        >
          <Icon name="image" :size="22" />
          <span>{{ uploading ? `上传中 ${progress}%` : '添加图片' }}</span>
        </button>
        <input ref="imgInput" type="file" accept="image/*" multiple hidden @change="onPickImages" />
      </div>

      <!-- 视频 -->
      <div v-if="form.video_url" class="video-preview">
        <video :src="mediaUrl(form.video_url)" controls />
        <button class="media-del video-del" @click="form.video_url = null"><Icon name="x" :size="14" /></button>
      </div>

      <div v-if="error" class="field-error">{{ error }}</div>
    </div>

    <template #footer>
      <label v-if="allowVideo && !form.images.length && !form.video_url" class="video-upload">
        <Icon name="video" :size="16" /><span>发视频</span>
        <input type="file" accept="video/*" hidden @change="onPickVideo" />
      </label>
      <label v-if="allowAnonymous" class="anon-check">
        <input type="checkbox" v-model="form.is_anonymous" />
        <Icon name="mask" :size="15" /><span>匿名发布</span>
      </label>
      <span class="grow" />
      <button class="btn btn-ghost" @click="onClose(false)">取消</button>
      <button class="btn btn-primary" :disabled="submitting || uploading" @click="submit">
        {{ submitting ? '发布中…' : (isEdit ? '保存修改' : '发布') }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import api from '../api'
import { mediaUrl } from '../utils/format'
import { useApp } from '../stores/app'
import { toast } from '../utils/toast'

const props = defineProps({
  modelValue: Boolean,
  categories: { type: Array, default: () => [] },
  post: { type: Object, default: null }, // 传入则为编辑
})
const emit = defineEmits(['update:modelValue', 'created', 'updated'])
const app = useApp()

const allowAnonymous = computed(() => app.settings?.allow_anonymous !== false)
const allowVideo = computed(() => app.settings?.allow_video !== false)
const allowImage = computed(() => true)
const isEdit = computed(() => !!props.post)

const empty = () => ({ title: '', content: '', category_id: null, is_anonymous: false, visibility: 'public', images: [], video_url: null })
const form = reactive(empty())
const error = ref('')
const submitting = ref(false)
const uploading = ref(false)
const progress = ref(0)

watch(() => props.modelValue, (v) => {
  if (v) {
    error.value = ''
    if (props.post) {
      Object.assign(form, {
        title: props.post.title || '', content: props.post.content || '',
        category_id: props.post.category?.id ?? null,
        is_anonymous: !!props.post.is_anonymous,
        visibility: props.post.visibility || 'public',
        images: (props.post.images || []).map((x) => x.url || x),
        video_url: props.post.video_url || null,
      })
    } else {
      Object.assign(form, empty())
    }
  }
})

async function onPickImages(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  const room = 9 - form.images.length
  for (const file of files.slice(0, room)) {
    uploading.value = true; progress.value = 0
    try {
      const r = await api.uploadMedia(file, 'image', (p) => (progress.value = p))
      form.images.push(r.url)
    } catch (err) { error.value = err.message } finally { uploading.value = false }
  }
}
function removeImage(i) { form.images.splice(i, 1) }
async function onPickVideo(e) {
  const file = (e.target.files || [])[0]
  e.target.value = ''
  if (!file) return
  uploading.value = true; progress.value = 0
  try {
    const r = await api.uploadMedia(file, 'video', (p) => (progress.value = p))
    form.video_url = r.url
  } catch (err) { error.value = err.message } finally { uploading.value = false }
}

async function submit() {
  error.value = ''
  if (!form.content.trim()) { error.value = '内容不能为空'; return }
  if (form.video_url && form.images.length) { error.value = '视频和图片不能同时发布'; return }
  submitting.value = true
  try {
    if (isEdit.value) {
      const r = await api.updatePost(props.post.id, {
        title: form.title, content: form.content,
        category_id: form.category_id, is_anonymous: form.is_anonymous, visibility: form.visibility,
      })
      emit('updated', r); toast.success('修改已保存')
    } else {
      const r = await api.createPost({ ...form })
      emit('created', r)
      const msg = r?._msg || ''
      if (msg && /审核|复核|打码|等待/.test(msg)) {
        toast.info(msg)
      } else {
        toast.success('发布成功')
      }
    }
    emit('update:modelValue', false)
  } catch (e) {
    error.value = e.message || '发布失败，请稍后再试'
  } finally {
    submitting.value = false
  }
}
function onClose() { emit('update:modelValue', false) }
</script>

<style scoped>
.composer { display: flex; flex-direction: column; gap: 14px; }
.counter { align-self: flex-end; font-size: 12px; margin-top: -8px; }
.composer-row { display: flex; gap: 10px; }
.composer-row .select { flex: 0 0 150px; }
.media-area { display: flex; flex-wrap: wrap; gap: 10px; }
.media-thumb, .media-add {
  position: relative; width: 96px; height: 96px; border-radius: var(--r-md); overflow: hidden;
}
.media-thumb img { width: 100%; height: 100%; object-fit: cover; }
.media-add {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  border: 1.5px dashed var(--line-strong); background: var(--surface-2);
  color: var(--ink-3); font-size: 12px; transition: border-color var(--t-fast), color var(--t-fast);
}
.media-add:hover:not(:disabled) { border-color: var(--brand-500); color: var(--brand-700); }
.media-del {
  position: absolute; top: 5px; right: 5px; width: 22px; height: 22px; border-radius: 50%;
  background: rgba(0,0,0,.55); color: #fff; display: flex; align-items: center; justify-content: center;
}
.video-preview { position: relative; max-width: 360px; }
.video-preview video { width: 100%; border-radius: var(--r-md); background: #000; }
.video-del { top: 8px; right: 8px; }
.video-upload {
  display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--ink-3);
  cursor: pointer; padding: 7px 10px; border-radius: var(--r-pill);
}
.video-upload:hover { color: var(--brand-700); background: var(--brand-50); }
.anon-check { display: inline-flex; align-items: center; gap: 6px; font-size: 13.5px; color: var(--ink-2); cursor: pointer; }
.anon-check input { accent-color: var(--brand-600); width: 15px; height: 15px; }
</style>
