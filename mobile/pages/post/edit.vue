<template>
  <view class="page" :class="cwRootClass">
    <view v-if="loaded" class="form-card anim-up">
      <view class="window-tip" :class="{ off: !canEdit }">
        <text>{{ canEdit ? '⏱ 发布 3 分钟内可修改内容，请抓紧保存' : 'ℹ️ 已超过 3 分钟，内容不可再改，仍可调整匿名与可见范围' }}</text>
      </view>
      <view class="form-row">
        <picker :range="categoryNames" :value="categoryIndex" :disabled="!canEdit" @change="onCategoryChange">
          <view class="picker" :class="{ placeholder: categoryIndex < 0, disabled: !canEdit }">
            {{ categoryIndex >= 0 ? '📌 ' + categoryNames[categoryIndex] : '选择分类（必选）' }}
            <text class="arrow">›</text>
          </view>
        </picker>
      </view>
      <view class="form-row">
        <input v-model="form.title" :disabled="!canEdit" placeholder="起个标题（必填）" class="title-input" maxlength="100" placeholder-class="ph" />
      </view>
      <view class="form-row">
        <textarea v-model="form.content" :disabled="!canEdit" placeholder="说点什么吧…（必填）" class="content-input"
          maxlength="10000" :auto-height="true" placeholder-class="ph" />
        <text class="word-count">{{ (form.content || '').length }} 字</text>
      </view>
      <!-- 图片（3 分钟内可增删） -->
      <view v-if="!hasVideo" class="form-row">
        <view class="image-grid">
          <view v-for="(img, idx) in form.images" :key="idx" class="image-item anim-pop">
            <image :src="mediaUrl(img)" mode="aspectFill" class="uploaded-image" @click="previewImg(idx)" />
            <view v-if="canEdit" class="image-delete" @click="removeImage(idx)">×</view>
          </view>
          <view v-if="canEdit && form.images.length < 9" class="add-row">
            <view class="image-add hover-press" @click="chooseImage">
              <text class="add-icon">🖼</text>
              <text class="add-text">{{ form.images.length }}/9</text>
            </view>
          </view>
        </view>
      </view>
      <view v-if="hasVideo" class="video-tip">🎬 原帖含视频，视频内容保持不变</view>

      <!-- 匿名 -->
      <view class="form-row opt-row">
        <view>
          <text class="opt-label">匿名发布</text>
          <text class="opt-tip">将以「匿名同学」身份展示</text>
        </view>
        <switch :checked="form.is_anonymous" @change="form.is_anonymous = $event.detail.value" color="#6366f1" />
      </view>

      <!-- 可见范围 -->
      <view class="form-row opt-block">
        <text class="opt-label">可见范围</text>
        <view class="vis-row">
          <view
            v-for="opt in visOptions" :key="opt.key"
            class="vis-item" :class="{ on: form.visibility === opt.key }"
            @click="form.visibility = opt.key"
          >
            <text class="vis-icon">{{ opt.icon }}</text>
            <view class="vis-text">
              <text class="vis-name">{{ opt.label }}</text>
              <text class="vis-desc">{{ opt.desc }}</text>
            </view>
            <text class="vis-check">{{ form.visibility === opt.key ? '✓' : '' }}</text>
          </view>
        </view>
      </view>
    </view>

    <button class="submit-btn hover-press" @click="submit" :loading="submitting" :disabled="uploading">
      {{ uploading ? `上传中 ${progress}%` : (canEdit ? '保存修改' : '保存设置') }}
    </button>
    <view class="tip">内容修改仅限发布后 3 分钟内；删除帖子请在帖子详情页操作</view>
  </view>
</template>
<script setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api, mediaUrl } from '../../utils/api'
const postId = ref(0)
const loaded = ref(false)
const canEdit = ref(false)
const hasVideo = ref(false)
const categories = ref([])
const categoryIndex = ref(-1)
const submitting = ref(false)
const uploading = ref(false)
const progress = ref(0)
const form = ref({ title: '', content: '', category_id: null, is_anonymous: false, visibility: 'public', images: [] })
const visOptions = [
  { key: 'public', label: '公开', icon: '🌐', desc: '所有人在广场可见' },
  { key: 'private', label: '仅自己', icon: '🔒', desc: '只有你自己能看到' },
]
const categoryNames = computed(() => categories.value.map((c) => c.name))
const onCategoryChange = (e) => {
  categoryIndex.value = e.detail.value
  form.value.category_id = categories.value[e.detail.value].id
}
const previewImg = (idx) => uni.previewImage({ current: idx, urls: form.value.images.map(mediaUrl) })
const removeImage = (idx) => form.value.images.splice(idx, 1)
const chooseImage = () => {
  uni.chooseImage({
    count: 9 - form.value.images.length,
    sizeType: ['original'],
    success: async (res) => {
      uploading.value = true
      try {
        for (const path of res.tempFilePaths) {
          const data = await api.uploadImage(path, (p) => (progress.value = p))
          form.value.images.push(data.url)
        }
      } catch (e) {
        uni.showToast({ title: (e && e.msg) || '图片上传失败', icon: 'none' })
      } finally { uploading.value = false; progress.value = 0 }
    },
  })
}
const submit = async () => {
  if (canEdit.value) {
    if (categoryIndex.value < 0) return uni.showToast({ title: '请选择分类', icon: 'none' })
    if (!form.value.title.trim()) return uni.showToast({ title: '请填写标题', icon: 'none' })
    if (!form.value.content.trim()) return uni.showToast({ title: '请填写内容', icon: 'none' })
  }
  submitting.value = true
  try {
    const payload = {
      is_anonymous: form.value.is_anonymous,
      visibility: form.value.visibility,
    }
    if (canEdit.value) {
      payload.title = form.value.title.trim()
      payload.content = form.value.content.trim()
      payload.category_id = form.value.category_id
      if (!hasVideo.value) payload.images = form.value.images
    }
    await api.updatePost(postId.value, payload)
    uni.showToast({ title: '已保存', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 700)
  } catch (e) {} finally { submitting.value = false }
}
onLoad(async (options) => {
  postId.value = parseInt(options.id)
  try {
    const [cats, post] = await Promise.all([
      api.getCategories().catch(() => []),
      api.getPost(postId.value),
    ])
    categories.value = cats || []
    form.value.title = post.title || ''
    form.value.content = post.content || ''
    form.value.is_anonymous = !!post.is_anonymous
    form.value.visibility = post.visibility || 'public'
    form.value.images = (post.images || []).map((i) => i.url || i)
    hasVideo.value = !!post.video_url
    canEdit.value = !!post.can_edit
    const cid = post.category?.id
    if (cid) {
      const idx = categories.value.findIndex((c) => c.id === cid)
      categoryIndex.value = idx
      form.value.category_id = cid
    }
    if (!post.is_owner) {
      uni.showToast({ title: '只能修改自己的帖子', icon: 'none' })
      setTimeout(() => uni.navigateBack(), 800)
      return
    }
    loaded.value = true
  } catch (e) {
    uni.showToast({ title: '帖子加载失败', icon: 'none' })
  }
})
</script>
<style scoped>
.page { padding: 24rpx; min-height: 100vh; background: var(--bg); }
.form-card { background: var(--surface); border-radius: var(--radius-lg); padding: 12rpx 32rpx; box-shadow: var(--shadow-sm); }
.window-tip { background: var(--brand-soft); color: var(--brand-deep); font-size: 23rpx; border-radius: var(--radius-sm);
  padding: 16rpx 20rpx; margin: 20rpx 0 4rpx; line-height: 1.5; }
.window-tip.off { background: var(--track); color: var(--ink-2); }
.form-row { padding: 28rpx 0; border-bottom: 1rpx solid var(--line); position: relative; }
.form-row:last-child { border-bottom: none; }
.picker { display: flex; justify-content: space-between; align-items: center; color: var(--ink); font-size: 29rpx; }
.picker.placeholder { color: var(--ink-3); }
.picker.disabled { opacity: .6; }
.arrow { color: var(--ink-3); font-size: 40rpx; }
.title-input { font-size: 36rpx; font-weight: 700; padding: 8rpx 0; color: var(--ink); }
.content-input { width: 100%; font-size: 29rpx; line-height: 1.7; min-height: 240rpx; padding: 8rpx 0; color: var(--ink); }
.word-count { position: absolute; right: 0; bottom: 16rpx; font-size: 21rpx; color: var(--ink-3); }
.ph { color: var(--ink-3); font-weight: 400; }
.image-grid { display: flex; flex-wrap: wrap; gap: 14rpx; }
.add-row { display: flex; gap: 14rpx; }
.image-item { position: relative; width: 180rpx; height: 180rpx; }
.uploaded-image { width: 100%; height: 100%; border-radius: var(--radius-sm); }
.image-delete { position: absolute; top: -12rpx; right: -12rpx; width: 40rpx; height: 40rpx; background: rgba(27,32,48,.75); color: #fff; border-radius: 50%; text-align: center; line-height: 38rpx; font-size: 28rpx; }
.image-add { width: 180rpx; height: 180rpx; border: 2rpx dashed #d3d7e0; border-radius: var(--radius-sm); display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--ink-3); background: var(--brand-mist); }
.add-icon { font-size: 48rpx; }
.add-text { font-size: 22rpx; margin-top: 8rpx; }
.video-tip { font-size: 23rpx; color: var(--ink-2); background: var(--track); border-radius: var(--radius-sm); padding: 16rpx 20rpx; margin: 20rpx 0; }
.opt-row { display: flex; justify-content: space-between; align-items: center; }
.opt-block { padding-bottom: 32rpx; }
.opt-label { font-size: 29rpx; color: var(--ink); font-weight: 600; }
.opt-tip { font-size: 22rpx; color: var(--ink-3); display: block; margin-top: 6rpx; }
.vis-row { display: flex; flex-direction: column; gap: 16rpx; margin-top: 20rpx; }
.vis-item { display: flex; align-items: center; gap: 18rpx; padding: 22rpx 24rpx; border: 2rpx solid var(--line); border-radius: var(--radius); background: var(--brand-mist); }
.vis-item.on { border-color: var(--brand); background: var(--brand-soft); }
.vis-icon { font-size: 40rpx; }
.vis-text { flex: 1; display: flex; flex-direction: column; }
.vis-name { font-size: 28rpx; font-weight: 600; color: var(--ink); }
.vis-desc { font-size: 22rpx; color: var(--ink-3); margin-top: 4rpx; }
.vis-check { color: var(--brand); font-weight: 700; font-size: 32rpx; }
.submit-btn { margin-top: 40rpx; background: var(--grad); color: #fff; border-radius: 999rpx; height: 96rpx; line-height: 96rpx; font-size: 31rpx; font-weight: 700; letter-spacing: 4rpx; border: none; box-shadow: var(--shadow-brand); }
.submit-btn[disabled] { opacity: .6; }
.submit-btn::after { border: none; }
.tip { text-align: center; color: var(--ink-3); font-size: 21rpx; margin-top: 24rpx; line-height: 1.6; }
</style>
