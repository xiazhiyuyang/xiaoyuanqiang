<template>
  <view class="page" :class="cwRootClass">
    <view class="form-card anim-up">
      <view class="form-row">
        <picker :range="categoryNames" :value="categoryIndex" @change="onCategoryChange">
          <view class="picker" :class="{ placeholder: categoryIndex < 0 }">
            {{ categoryIndex >= 0 ? '📌 ' + categoryNames[categoryIndex] : '选择分类（必选）' }}
            <text class="arrow">›</text>
          </view>
        </picker>
      </view>
      <view class="form-row">
        <input v-model="form.title" placeholder="起个标题（必填）" class="title-input" maxlength="100" placeholder-class="ph" />
      </view>
      <view class="form-row">
        <textarea v-model="form.content" placeholder="说点什么吧…（必填）" class="content-input"
          maxlength="10000" :auto-height="true" placeholder-class="ph" />
        <text class="word-count">{{ (form.content || '').length }} 字</text>
      </view>

      <!-- 视频 -->
      <view v-if="videoPath" class="video-box">
        <video :src="videoPath" class="video-el" object-fit="cover" />
        <view class="video-del" @click="removeVideo">×</view>
      </view>

      <!-- 图片 -->
      <view v-if="!videoPath" class="form-row">
        <view class="image-grid">
          <view v-for="(img, idx) in form.images" :key="idx" class="image-item anim-pop">
            <image :src="mediaUrl(img)" mode="aspectFill" class="uploaded-image" @click="previewImg(idx)" />
            <view class="image-delete" @click="removeImage(idx)">×</view>
          </view>
          <view v-if="form.images.length < 9" class="add-row">
            <view class="image-add hover-press" @click="chooseImage">
              <text class="add-icon">🖼</text>
              <text class="add-text">{{ form.images.length }}/9</text>
            </view>
            <view class="image-add hover-press" @click="chooseVideo">
              <text class="add-icon">🎬</text>
              <text class="add-text">视频</text>
            </view>
          </view>
        </view>
      </view>

      <view class="form-row anon-row">
        <view>
          <text class="anon-label">匿名发布</text>
          <text class="anon-tip">将以「匿名同学」身份展示</text>
        </view>
        <switch :checked="form.is_anonymous" @change="form.is_anonymous = $event.detail.value" color="#6366f1" />
      </view>
    </view>

    <button class="submit-btn hover-press" @click="submit" :loading="submitting" :disabled="uploading">
      {{ uploading ? `上传中 ${progress}%` : '发 布' }}
    </button>
    <view class="tip">图片单张不超过 10MB，视频不超过 50MB；视频和图片二选一</view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { api, mediaUrl } from '../../utils/api'
const categories = ref([])
const categoryIndex = ref(-1)
const submitting = ref(false)
const uploading = ref(false)
const progress = ref(0)
const videoPath = ref('')
const form = ref({ title: '', content: '', category_id: null, is_anonymous: false, images: [], video_url: '' })
const categoryNames = computed(() => categories.value.map((c) => c.name))

const loadCategories = async () => { try { categories.value = await api.getCategories() } catch (e) {} }
const onCategoryChange = (e) => { categoryIndex.value = e.detail.value; form.value.category_id = categories.value[e.detail.value].id }

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
const chooseVideo = () => {
  // #ifdef MP-WEIXIN
  uni.chooseMedia({ count: 1, mediaType: ['video'], sourceType: ['album', 'camera'], maxDuration: 60,
    success: (res) => handleVideo(res.tempFiles[0].tempFilePath, res.tempFiles[0].size) })
  // #endif
  // #ifndef MP-WEIXIN
  uni.chooseVideo({ sourceType: ['album', 'camera'], maxDuration: 60, compressed: true,
    success: (res) => handleVideo(res.tempFilePath, res.size) })
  // #endif
}
const handleVideo = async (path, size) => {
  if (size && size > 50 * 1024 * 1024) {
    return uni.showToast({ title: '视频不能超过 50MB', icon: 'none' })
  }
  if (form.value.images.length) form.value.images = []
  videoPath.value = path
  uploading.value = true
  try {
    const data = await api.uploadVideo(path, (p) => (progress.value = p))
    form.value.video_url = data.url
    uni.showToast({ title: '视频已就绪', icon: 'success' })
  } catch (e) {
    videoPath.value = ''
    uni.showToast({ title: (e && e.msg) || '视频上传失败', icon: 'none' })
  } finally { uploading.value = false; progress.value = 0 }
}
const removeVideo = () => { videoPath.value = ''; form.value.video_url = '' }
const previewImg = (idx) => uni.previewImage({ current: idx, urls: form.value.images.map(mediaUrl) })
const removeImage = (idx) => form.value.images.splice(idx, 1)

const submit = async () => {
  if (!uni.getStorageSync('token')) return uni.showToast({ title: '请先登录', icon: 'none' })
  if (categoryIndex.value < 0) return uni.showToast({ title: '请选择分类', icon: 'none' })
  if (!form.value.title.trim()) return uni.showToast({ title: '请填写标题', icon: 'none' })
  if (!form.value.content.trim()) return uni.showToast({ title: '请填写内容', icon: 'none' })
  if (uploading.value) return uni.showToast({ title: '请等待上传完成', icon: 'none' })
  if (videoPath.value && !form.value.video_url) return uni.showToast({ title: '视频还在上传中', icon: 'none' })
  submitting.value = true
  try {
    await api.createPost({ ...form.value, title: form.value.title.trim(), content: form.value.content.trim() })
    uni.showToast({ title: '发布成功', icon: 'success' })
    setTimeout(() => uni.switchTab({ url: '/pages/index/index' }), 800)
  } catch (e) {} finally { submitting.value = false }
}
loadCategories()
</script>

<style scoped>
.page { padding: 24rpx; min-height: 100vh; background: var(--bg); }
.form-card { background: var(--surface); border-radius: var(--radius-lg); padding: 12rpx 32rpx; box-shadow: var(--shadow-sm); }
.form-row { padding: 28rpx 0; border-bottom: 1rpx solid var(--line); position: relative; }
.form-row:last-child { border-bottom: none; }
.picker { display: flex; justify-content: space-between; align-items: center; color: var(--ink); font-size: 29rpx; }
.picker.placeholder { color: var(--ink-3); }
.arrow { color: var(--ink-3); font-size: 40rpx; }
.title-input { font-size: 36rpx; font-weight: 700; padding: 8rpx 0; color: var(--ink); }
.content-input { width: 100%; font-size: 29rpx; line-height: 1.7; min-height: 240rpx; padding: 8rpx 0; color: var(--ink); }
.word-count { position: absolute; right: 0; bottom: 16rpx; font-size: 21rpx; color: var(--ink-3); }
.ph { color: var(--ink-3); font-weight: 400; }
.video-box { position: relative; margin-top: 24rpx; }
.video-el { width: 100%; height: 400rpx; border-radius: var(--radius); background: #000; }
.video-del { position: absolute; top: -16rpx; right: -16rpx; width: 48rpx; height: 48rpx; background: rgba(0,0,0,.7); color: #fff; border-radius: 50%; text-align: center; line-height: 46rpx; font-size: 32rpx; }
.image-grid { display: flex; flex-wrap: wrap; gap: 14rpx; }
.add-row { display: flex; gap: 14rpx; }
.image-item { position: relative; width: 180rpx; height: 180rpx; }
.uploaded-image { width: 100%; height: 100%; border-radius: var(--radius-sm); }
.image-delete { position: absolute; top: -12rpx; right: -12rpx; width: 40rpx; height: 40rpx; background: rgba(27,32,48,.75); color: #fff; border-radius: 50%; text-align: center; line-height: 38rpx; font-size: 28rpx; }
.image-add { width: 180rpx; height: 180rpx; border: 2rpx dashed #d3d7e0; border-radius: var(--radius-sm); display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--ink-3); background: #fafbfc; }
.add-icon { font-size: 48rpx; }
.add-text { font-size: 22rpx; margin-top: 8rpx; }
.anon-row { display: flex; justify-content: space-between; align-items: center; }
.anon-label { font-size: 29rpx; color: var(--ink); }
.anon-tip { font-size: 22rpx; color: var(--ink-3); display: block; margin-top: 6rpx; }
.submit-btn { margin-top: 40rpx; background: var(--grad); color: #fff; border-radius: 999rpx; height: 96rpx; line-height: 96rpx; font-size: 31rpx; font-weight: 700; letter-spacing: 8rpx; border: none; box-shadow: var(--shadow-brand); }
.submit-btn[disabled] { opacity: .6; }
.submit-btn::after { border: none; }
.tip { text-align: center; color: var(--ink-3); font-size: 21rpx; margin-top: 24rpx; line-height: 1.6; }
</style>
