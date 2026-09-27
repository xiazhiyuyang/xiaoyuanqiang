<template>
  <view class="page" :class="cwRootClass">
    <view v-if="post" class="post-detail">
      <view class="post-header">
        <cw-avatar
          :src="post.is_anonymous ? '' : (post.author?.avatar || '')"
          :user-id="post.is_anonymous ? 0 : post.author?.id"
          :size="84"
        />
        <view class="meta">
          <view class="name-row">
            <text class="name">{{ post.is_anonymous ? '匿名同学' : (post.author?.nickname || '同学') }}</text>
            <text
              v-for="t in staffLabels" :key="t.label"
              class="staff-tag" :class="t.cls"
            >{{ t.label }}</text>
          </view>
          <text class="time">{{ formatTime(post.created_at) }}</text>
        </view>
        <view
          v-if="canFollow" class="follow-btn" :class="{ on: post.author?.is_following }"
          @click="toggleFollowAuthor"
        >{{ post.author?.is_following ? '已关注' : '+ 关注' }}</view>
      </view>
      <view class="title">{{ post.title }}</view>
      <view class="content">{{ post.content }}</view>
      <view v-if="post.video_url" class="video-wrap">
        <video :src="mediaUrl(post.video_url)" class="video" controls show-center-play-btn object-fit="contain" />
      </view>
      <view v-if="post.images && post.images.length" class="images">
        <image
          v-for="(img, idx) in post.images"
          :key="idx"
          class="image"
          :src="mediaUrl(img.url || img)"
          mode="widthFix"
          @click="previewImage(idx)"
        />
      </view>
      <view class="actions">
        <view class="action" @click="toggleLike">
          <text class="action-icon" :class="{ active: post.is_liked }">{{ post.is_liked ? '♥' : '♡' }}</text>
          <text>{{ post.like_count }}</text>
        </view>
        <view class="action" @click="toggleFavorite">
          <text class="action-icon" :class="{ active: post.is_favorited }">{{ post.is_favorited ? '★' : '☆' }}</text>
          <text>收藏</text>
        </view>
        <!-- 本人：编辑 / 删除 -->
        <template v-if="isOwner">
          <view class="action" @click="editPost">
            <text class="action-icon">✏️</text><text>编辑</text>
          </view>
          <view class="action action-danger" @click="confirmDelete">
            <text class="action-icon">🗑</text><text>删除</text>
          </view>
        </template>
        <!-- 他人：私信 / 举报 -->
        <template v-else>
          <view
            v-if="!post.is_anonymous && post.author && post.author.id !== myId"
            class="action" @click="chatAuthor"
          >
            <text class="action-icon">✉</text><text>私信TA</text>
          </view>
          <view class="action action-danger" @click="reportTarget('post', post.id)">
            <text>举报</text>
          </view>
        </template>
      </view>
    </view>
    <!-- 评论区 -->
    <view class="comments-section">
      <view class="section-title">评论 {{ post?.comment_count || 0 }}</view>
      <view v-for="comment in comments" :key="comment.id" class="comment-item">
        <cw-avatar :src="comment.author?.avatar || ''" :user-id="comment.author?.id || comment.user_id || 0" :size="60" />
        <view class="comment-body">
          <view class="comment-head">
            <text class="comment-name">{{ comment.author_name || comment.author?.nickname }}</text>
            <text class="comment-time">{{ formatTime(comment.created_at) }}</text>
          </view>
          <view class="comment-content">{{ comment.content }}</view>
          <view class="comment-footer">
            <view class="cf-item" @click="likeComment(comment)">
              <text :class="{ liked: comment.is_liked }">{{ comment.is_liked ? '♥' : '♡' }} {{ comment.like_count }}</text>
            </view>
            <view class="cf-item" @click="replyTo(comment)"><text>回复</text></view>
            <view class="cf-item" @click="reportTarget('comment', comment.id)"><text>举报</text></view>
          </view>
          <view v-if="comment.replies && comment.replies.length" class="replies">
            <view v-for="reply in comment.replies" :key="reply.id" class="reply-item">
              <text class="reply-name">{{ reply.author_name || reply.author?.nickname }}</text>
              <text class="reply-content">：{{ reply.content }}</text>
              <text class="reply-action" @click="reportTarget('comment', reply.id)">举报</text>
            </view>
          </view>
        </view>
      </view>
      <view v-if="comments.length === 0" class="empty">还没有评论，来说两句吧</view>
    </view>
    <!-- 底部评论输入 -->
    <view class="comment-bar safe-bottom">
      <view class="bar-inner">
        <input
          v-model="commentText"
          :placeholder="replyTarget ? `回复 ${replyTargetName}` : '说点什么…'"
          class="comment-input"
          confirm-type="send"
          @confirm="sendComment"
        />
        <button class="send-btn" @click="sendComment">发送</button>
      </view>
    </view>
  </view>
</template>
<script setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api, mediaUrl } from '../../utils/api'
const postId = ref(0)
const post = ref(null)
const myId = ref(0)
const STAFF_MAP = {
  admin: { label: '管理员', cls: 'st-admin' },
  content_review: { label: '审核员', cls: 'st-review' },
  report_review: { label: '审查员', cls: 'st-audit' },
}
const staffLabels = computed(() => {
  const p = post.value
  if (!p || p.is_anonymous) return []
  const tags = p.author?.staff_tags || (p.author?.role === 'admin' ? ['admin'] : [])
  return tags.map((t) => STAFF_MAP[t]).filter(Boolean)
})
const canFollow = computed(() => {
  const a = post.value?.author
  return !!(a && a.id && !post.value.is_anonymous && a.id !== myId.value)
})
// 是否为本人帖子（匿名帖后端不下发 author，用 user_id 兜底）
const isOwner = computed(() => {
  if (!myId.value) return false
  const ownerId = post.value?.author?.id ?? post.value?.user_id
  return ownerId === myId.value
})
const comments = ref([])
const commentText = ref('')
const replyTarget = ref(null)
const replyTargetName = ref('')
const AVATAR_COLORS = ['#e7ddf0', '#d9e6ef', '#dde8dc', '#f2e0d2', '#efdce0', '#d6e8e6']
const avatarColor = (name) => {
  const s = String(name || '匿')
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 997
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}
const REPORT_REASONS = [
  { key: 'spam', label: '垃圾广告' },
  { key: 'porn', label: '色情低俗' },
  { key: 'abuse', label: '辱骂/人身攻击' },
  { key: 'fraud', label: '诈骗/虚假信息' },
  { key: 'illegal', label: '违法违规' },
  { key: 'other', label: '其他' },
]
const requireLogin = () => {
  if (!uni.getStorageSync('token')) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return false
  }
  return true
}
const reportTarget = (type, id) => {
  if (!requireLogin()) return
  uni.showActionSheet({
    itemList: REPORT_REASONS.map((r) => r.label),
    success: async ({ tapIndex }) => {
      try {
        await api.createReport({ target_type: type, target_id: id, reason: REPORT_REASONS[tapIndex].key })
        uni.showToast({ title: '举报已提交', icon: 'success' })
      } catch (e) {}
    },
  })
}
const chatAuthor = async () => {
  if (!requireLogin()) return
  const conv = await api.createConversation(post.value.author.id)
  uni.navigateTo({
    url: `/pages/message/chat?id=${conv.id}&peerId=${conv.peer_id}&peerName=${encodeURIComponent(conv.peer_nickname)}`,
  })
}
const formatTime = (t) => {
  const d = new Date(t)
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
  return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
const loadPost = async () => {
  post.value = await api.getPost(postId.value)
}
const loadComments = async () => {
  const data = await api.getComments(postId.value, { page: 1, page_size: 50 })
  comments.value = data.items
}
const previewImage = (idx) => {
  const urls = post.value.images.map((i) => mediaUrl(i.url || i))
  uni.previewImage({ current: urls[idx], urls })
}
const toggleLike = async () => {
  const data = await api.likePost(postId.value)
  post.value.is_liked = data.liked
  post.value.like_count = data.like_count
}
const toggleFavorite = async () => {
  const data = await api.favoritePost(postId.value)
  post.value.is_favorited = data.favorited
  uni.showToast({ title: data.favorited ? '已收藏' : '已取消收藏', icon: 'none' })
}
const editPost = () => uni.navigateTo({ url: `/pages/post/edit?id=${postId.value}` })
const confirmDelete = () => {
  uni.showModal({
    title: '删除帖子',
    content: '确定删除这条动态吗？删除后不可恢复。',
    confirmText: '删除',
    confirmColor: '#f43f5e',
    success: async (r) => {
      if (!r.confirm) return
      try {
        await api.deletePost(postId.value)
        uni.$emit('campus:post-deleted', postId.value)
        uni.showToast({ title: '已删除', icon: 'none' })
        setTimeout(() => uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/index/index' }) }), 500)
      } catch (e) { /* request 已统一提示 */ }
    },
  })
}
const toggleFollowAuthor = async () => {
  if (!requireLogin()) return
  const data = await api.toggleFollow(post.value.author.id)
  post.value.author.is_following = data.following
  uni.showToast({ title: data.following ? '已关注' : '已取消关注', icon: 'none' })
}
const likeComment = async (comment) => {
  const data = await api.likeComment(postId.value, comment.id)
  comment.is_liked = data.liked
  comment.like_count = data.like_count
}
const replyTo = (comment) => {
  replyTarget.value = comment.id
  replyTargetName.value = comment.author_name || comment.author?.nickname
}
const sendComment = async () => {
  if (!commentText.value.trim()) return
  if (!requireLogin()) return
  await api.createComment(postId.value, {
    content: commentText.value,
    parent_id: replyTarget.value,
  })
  commentText.value = ''
  replyTarget.value = null
  uni.showToast({ title: '评论成功', icon: 'success' })
  loadComments()
  loadPost()
}
onLoad((options) => {
  postId.value = parseInt(options.id)
  const userInfo = uni.getStorageSync('userInfo')
  myId.value = userInfo ? JSON.parse(userInfo).id : 0
  loadPost()
  loadComments()
})
</script>
<style scoped>
.page { padding-bottom: 140rpx; background: var(--bg); min-height: 100vh; }
.post-detail { background: var(--surface); padding: 32rpx; margin-bottom: 20rpx; }
.post-header { display: flex; align-items: center; margin-bottom: 24rpx; }
.avatar, .comment-avatar {
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  color: #4a5160; font-weight: 600; flex-shrink: 0;
}
.avatar { width: 84rpx; height: 84rpx; margin-right: 18rpx; font-size: 34rpx; }
.meta { flex: 1; }
.name-row { display: flex; align-items: center; gap: 10rpx; flex-wrap: wrap; }
.name { font-size: 28rpx; color: var(--ink); font-weight: 600; }
.staff-tag { font-size: 18rpx; font-weight: 700; padding: 4rpx 12rpx; border-radius: 999rpx; border: 1rpx solid; }
.st-admin { color: #fde68a; background: rgba(251,191,36,.16); border-color: rgba(251,191,36,.4); }
.st-review { color: #a5b4fc; background: rgba(139,124,246,.16); border-color: rgba(139,124,246,.4); }
.st-audit { color: #67e8f9; background: rgba(103,232,249,.12); border-color: rgba(103,232,249,.35); }
.follow-btn { flex-shrink: 0; font-size: 23rpx; font-weight: 700; color: #fff; background: var(--grad); padding: 12rpx 28rpx; border-radius: 999rpx; }
.follow-btn.on { background: rgba(255,255,255,.08); color: var(--ink-3); border: 1rpx solid var(--line); }
.time { font-size: 22rpx; color: var(--ink-3); margin-top: 6rpx; display: block; }
.title { font-size: 42rpx; font-weight: 700; color: var(--ink); margin-bottom: 20rpx; line-height: 1.35; }
.content { font-size: 30rpx; color: var(--ink-2); line-height: 1.8; }
.video-wrap { margin-top: 20rpx; border-radius: var(--radius); overflow: hidden; background: #000; }
.video { width: 100%; height: 420rpx; }
.images { margin-top: 20rpx; }
.image { width: 100%; border-radius: var(--radius); margin-bottom: 12rpx; }
.actions {
  display: flex; align-items: center; gap: 48rpx; margin-top: 28rpx;
  padding-top: 24rpx; border-top: 1rpx solid var(--line);
  color: var(--ink-2); font-size: 26rpx;
}
.action { display: flex; align-items: center; }
.action-icon { margin-right: 8rpx; font-size: 32rpx; color: var(--ink-3); }
.action-icon.active { color: var(--danger); }
.action-danger { margin-left: auto; color: var(--ink-3); font-size: 24rpx; }
.comments-section { background: var(--surface); padding: 32rpx; }
.section-title { font-size: 30rpx; font-weight: 700; margin-bottom: 12rpx; color: var(--ink); }
.comment-item { display: flex; padding: 24rpx 0; border-bottom: 1rpx solid var(--line); }
.comment-avatar { width: 60rpx; height: 60rpx; margin-right: 16rpx; font-size: 24rpx; }
.comment-body { flex: 1; min-width: 0; }
.comment-head { display: flex; align-items: baseline; }
.comment-name { font-size: 26rpx; color: var(--brand); font-weight: 500; }
.comment-time { font-size: 20rpx; color: var(--ink-3); margin-left: 16rpx; }
.comment-content { font-size: 28rpx; color: var(--ink); line-height: 1.6; margin-top: 8rpx; }
.comment-footer { display: flex; gap: 36rpx; margin-top: 12rpx; font-size: 23rpx; color: var(--ink-3); }
.cf-item .liked { color: var(--danger); }
.replies { background: rgba(255,255,255,.05); border-radius: var(--radius-sm); padding: 16rpx 20rpx; margin-top: 14rpx; }
.reply-item { font-size: 25rpx; line-height: 1.7; }
.reply-name { color: var(--brand); font-weight: 500; }
.reply-content { color: var(--ink-2); }
.reply-action { color: var(--ink-3); font-size: 22rpx; margin-left: 16rpx; }
.empty { text-align: center; padding: 60rpx; color: var(--ink-3); font-size: 26rpx; }
.comment-bar {
  position: fixed; bottom: 0; left: 0; right: 0; background: var(--surface);
  border-top: 1rpx solid var(--line); padding: 14rpx 24rpx; z-index: 99;
}
.bar-inner { display: flex; align-items: center; gap: 16rpx; }
.comment-input {
  flex: 1; height: 72rpx; background: rgba(255,255,255,.08); border-radius: 999rpx;
  padding: 0 28rpx; font-size: 27rpx; color: var(--text);
}
.send-btn {
  background: var(--brand); color: #fff; font-size: 26rpx; height: 72rpx;
  line-height: 72rpx; padding: 0 40rpx; border-radius: 999rpx; margin: 0;
}
/* #ifdef H5 */
@media (min-width: 768px) {
  .comment-bar { max-width: 720px; margin: 0 auto; }
}
@media (min-width: 1100px) {
  .comment-bar { max-width: 780px; }
}
/* #endif */
</style>
