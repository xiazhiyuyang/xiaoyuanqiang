<template>
  <view class="page" :class="cwRootClass">
    <view class="avatar-row cw-card anim-up" @click="chooseAvatar">
      <text class="row-label">头像</text>
      <view class="row-right">
        <cw-avatar :src="form.avatar" :size="96" />
        <text class="arrow">›</text>
      </view>
    </view>

    <view class="form cw-card anim-up delay-1">
      <view class="row">
        <text class="row-label">昵称</text>
        <input v-model="form.nickname" class="row-input" placeholder="填写昵称" maxlength="32" />
      </view>
      <view class="row">
        <text class="row-label">性别</text>
        <view class="seg">
          <text class="seg-item" :class="{ on: form.gender === 'male' }" @click="form.gender='male'">男</text>
          <text class="seg-item" :class="{ on: form.gender === 'female' }" @click="form.gender='female'">女</text>
          <text class="seg-item" :class="{ on: form.gender === 'unknown' }" @click="form.gender='unknown'">保密</text>
        </view>
      </view>
      <view class="row">
        <text class="row-label">年级</text>
        <picker mode="selector" :range="grades" @change="(e)=>form.grade=grades[e.detail.value]">
          <view class="picker">{{ form.grade || '请选择' }}<text class="arrow">›</text></view>
        </picker>
      </view>
      <view class="row">
        <text class="row-label">学院</text>
        <input v-model="form.college" class="row-input" placeholder="如：计算机学院" maxlength="32" />
      </view>
      <view class="row">
        <text class="row-label">专业</text>
        <input v-model="form.major" class="row-input" placeholder="如：软件工程" maxlength="32" />
      </view>
      <view class="row">
        <text class="row-label">所在地</text>
        <input v-model="form.location" class="row-input" placeholder="如：广州" maxlength="32" />
      </view>
      <view class="row">
        <text class="row-label">生日</text>
        <picker mode="date" :value="form.birthday" :end="today" @change="(e)=>form.birthday=e.detail.value">
          <view class="picker">{{ form.birthday || '请选择' }}<text class="arrow">›</text></view>
        </picker>
      </view>
    </view>

    <view class="bio-box cw-card anim-up delay-2">
      <text class="row-label">个性签名</text>
      <textarea v-model="form.bio" class="bio" placeholder="介绍一下自己吧～" maxlength="200" />
      <text class="bio-count">{{ (form.bio || '').length }}/200</text>
    </view>

    <button class="save hover-press" @click="save" :loading="saving">保存资料</button>
    <view class="tip">资料的「谁可以看」可在「我的 - 可见范围」里单独设置</view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { api } from '../../utils/api'
const userStore = useUserStore()
const saving = ref(false)
const grades = ['大一', '大二', '大三', '大四', '研一', '研二', '研三', '博士生', '其他']
const today = new Date().toISOString().slice(0, 10)
const form = ref({
  avatar: '', nickname: '', gender: 'unknown', grade: '', college: '',
  major: '', location: '', birthday: '', bio: '',
})
onLoad(async () => {
  try {
    const me = await api.getMe()
    form.value = {
      avatar: me.avatar || '', nickname: me.nickname || '', gender: me.gender || 'unknown',
      grade: me.grade || '', college: me.college || '', major: me.major || '',
      location: me.location || '', birthday: me.birthday || '', bio: me.bio || '',
    }
  } catch (e) {}
})
const chooseAvatar = () => {
  uni.chooseImage({
    count: 1, sizeType: ['original'],
    success: async (res) => {
      uni.showLoading({ title: '上传中', mask: true })
      try {
        const data = await api.uploadImage(res.tempFilePaths[0])
        form.value.avatar = data.url || data
      } catch (e) { uni.showToast({ title: (e && e.msg) || '上传失败', icon: 'none' }) } finally { uni.hideLoading() }
    },
  })
}
const save = async () => {
  if (!form.value.nickname.trim()) return uni.showToast({ title: '昵称不能为空', icon: 'none' })
  saving.value = true
  try {
    const me = await api.updateMe({ ...form.value, nickname: form.value.nickname.trim() })
    userStore.setUser(me)
    uni.showToast({ title: '已保存', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 600)
  } catch (e) {} finally { saving.value = false }
}
</script>

<style scoped>
.page { padding: 24rpx; }
.avatar-row { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 28rpx; margin-bottom: 22rpx; }
.row-label { font-size: 28rpx; color: var(--ink); font-weight: 600; }
.row-right { display: flex; align-items: center; }
.arrow { color: var(--ink-3); font-size: 36rpx; margin-left: 10rpx; }
.form { padding: 0 28rpx; margin-bottom: 22rpx; }
.row { display: flex; align-items: center; justify-content: space-between; min-height: 100rpx; border-bottom: 1rpx solid var(--line); }
.row:last-child { border-bottom: none; }
.row-input { flex: 1; text-align: right; font-size: 27rpx; color: var(--ink-2); }
.picker { display: flex; align-items: center; font-size: 27rpx; color: var(--ink-2); }
.seg { display: flex; background: #f1f2f8; border-radius: 999rpx; padding: 4rpx; }
.seg-item { font-size: 24rpx; color: var(--ink-2); padding: 10rpx 26rpx; border-radius: 999rpx; }
.seg-item.on { background: var(--grad); color: #fff; font-weight: 700; }
.bio-box { padding: 24rpx 28rpx; position: relative; margin-bottom: 40rpx; }
.bio { width: 100%; height: 160rpx; margin-top: 18rpx; font-size: 27rpx; color: var(--ink-2); }
.bio-count { position: absolute; right: 28rpx; bottom: 20rpx; font-size: 22rpx; color: var(--ink-3); }
.save { height: 92rpx; line-height: 92rpx; background: var(--grad); color: #fff; border-radius: 999rpx; font-size: 30rpx; font-weight: 700; border: none; box-shadow: var(--shadow-brand); }
.save::after { border: none; }
.tip { text-align: center; color: var(--ink-3); font-size: 22rpx; margin-top: 24rpx; }
</style>
