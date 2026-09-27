<template>
  <article class="post-card rise" :class="{ pinned: post.is_top, 'menu-open': menuOpen }">
    <div v-if="post.is_top" class="pin-flag"><Icon name="pin" :size="12" /> 置顶</div>

    <header class="pc-head">
      <RouterLink :to="profileUrl" class="pc-user" @click.stop>
        <UserAvatar
          :src="post.author?.avatar" :name="displayName"
          :anonymous="post.is_anonymous" :seed="post.user_id || post.id" :size="42"
        />
        <span class="pc-user-meta">
          <span class="pc-name-row">
            <span class="pc-name">{{ displayName }}</span>
            <LevelBadge v-if="post.level_badge" :badge="post.level_badge" />
            <span v-for="t in staffTags" :key="t" class="staff-tag">{{ staffLabel(t) }}</span>
          </span>
          <span class="pc-sub">
            <span class="tabular">{{ timeAgo(post.created_at) }}</span>
            <span v-if="post.category" class="pc-cat">· {{ post.category.name }}</span>
          </span>
        </span>
      </RouterLink>

      <FollowButton
        v-if="showFollow"
        :user-id="post.author.id"
        :model-value="post.author.is_following"
        @update:model-value="(v) => post.author.is_following = v"
      />
    </header>

    <RouterLink :to="`/post/${post.id}`" class="pc-body">
      <h2 v-if="post.title" class="pc-title">{{ post.title }}</h2>
      <p v-if="post.content" class="pc-text clamp-2">{{ post.content }}</p>
    </RouterLink>

    <ImageGrid v-if="post.images && post.images.length" :images="post.images" />
    <RouterLink v-if="post.video_url" :to="`/post/${post.id}`" class="video-chip">
      <Icon name="video" :size="16" /><span>视频动态，点击查看</span>
    </RouterLink>

    <footer class="pc-foot">
      <button class="act" :class="{ on: liked }" @click="toggleLike">
        <Icon name="heart" :size="18" :filled="liked" />
        <span class="tabular">{{ post.like_count || 0 }}</span>
      </button>
      <RouterLink :to="`/post/${post.id}`" class="act">
        <Icon name="comment" :size="18" /><span class="tabular">{{ post.comment_count || 0 }}</span>
      </RouterLink>
      <button class="act fav" :class="{ on: favorited }" @click="toggleFavorite">
        <Icon name="bookmark" :size="18" :filled="favorited" />
        <span>收藏</span>
      </button>
      <span class="act views"><Icon name="eye" :size="17" /><span class="tabular">{{ post.view_count || 0 }}</span></span>

      <div class="more-wrap" @click.stop>
        <button class="act more-btn" aria-label="更多操作" @click="menuOpen = !menuOpen">
          <Icon name="more" :size="18" />
        </button>
        <Transition name="menu">
          <div v-if="menuOpen" class="menu pop">
            <button v-if="canManage" @click="onEdit"><Icon name="edit" :size="15" /> 编辑</button>
            <button v-if="canManage" class="danger" @click="onDelete"><Icon name="trash" :size="15" /> 删除</button>
            <button @click="copyLink"><Icon name="link" :size="15" /> 复制链接</button>
            <button v-if="!isOwner" class="danger" @click="onReport"><Icon name="flag" :size="15" /> 举报</button>
          </div>
        </Transition>
      </div>
    </footer>

    <ReportDialog v-model="reportOpen" target-type="post" :target-id="post.id" />
  </article>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import Icon from './Icon.vue'
import UserAvatar from './UserAvatar.vue'
import LevelBadge from './LevelBadge.vue'
import ImageGrid from './ImageGrid.vue'
import FollowButton from './FollowButton.vue'
import ReportDialog from './ReportDialog.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { timeAgo } from '../utils/format'
import { toast } from '../utils/toast'

const props = defineProps({ post: { type: Object, required: true } })
const emit = defineEmits(['edit', 'deleted'])
const router = useRouter()
const auth = useAuth()

const liked = ref(!!props.post.is_liked)
const favorited = ref(!!props.post.is_favorited)
const menuOpen = ref(false)
const reportOpen = ref(false)

const isOwner = computed(() =>
  props.post.is_owner || (props.post.author && auth.user && props.post.author.id === auth.user.id)
)
const canManage = computed(() => props.post.can_edit || isOwner.value || auth.isAdmin)
const displayName = computed(() =>
  props.post.is_anonymous ? (props.post.author_name || '匿名同学') : (props.post.author?.nickname || '未知用户')
)
const staffTags = computed(() => (props.post.is_anonymous ? [] : props.post.author?.staff_tags || []))
const profileUrl = computed(() =>
  props.post.is_anonymous || !props.post.author ? '#' : `/u/${props.post.author.id}`
)
const showFollow = computed(() =>
  props.post.author && auth.isLoggedIn && !isOwner.value && props.post.author.is_following === false
)

function staffLabel(t) {
  return { admin: '管理员', content_review: '审核员', report_review: '审查员' }[t] || t
}

async function toggleLike() {
  if (!auth.isLoggedIn) return router.push('/login')
  liked.value = !liked.value
  props.post.like_count += liked.value ? 1 : -1
  try {
    const r = await api.likePost(props.post.id)
    liked.value = r.liked
    props.post.like_count = r.like_count
  } catch { liked.value = !liked.value; props.post.like_count += liked.value ? 1 : -1 }
}
async function toggleFavorite() {
  if (!auth.isLoggedIn) return router.push('/login')
  favorited.value = !favorited.value
  try {
    const r = await api.favoritePost(props.post.id)
    favorited.value = r.favorited
    toast.success(r.favorited ? '已加入收藏' : '已取消收藏')
  } catch { favorited.value = !favorited.value }
}
function copyLink() {
  const url = location.origin + '/pc/post/' + props.post.id
  navigator.clipboard?.writeText(url).then(() => toast.success('链接已复制')).catch(() => toast.info(url))
  menuOpen.value = false
}
function onReport() { menuOpen.value = false; reportOpen.value = true }
function onEdit() { menuOpen.value = false; emit('edit', props.post) }
async function onDelete() {
  menuOpen.value = false
  if (!window.confirm('确定删除这条动态吗？删除后不可恢复。')) return
  try {
    await api.deletePost(props.post.id)
    toast.success('已删除')
    emit('deleted', props.post.id)
  } catch { /* toast handled */ }
}
function onDocClick(e) { if (!e.target.closest('.more-wrap')) menuOpen.value = false }
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.post-card {
  position: relative; background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r-lg); padding: 20px 22px 14px 26px; margin-bottom: 16px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--t-base) var(--ease-out), transform var(--t-base) var(--ease-out), border-color var(--t-base);
  overflow: hidden;
}
/* 左侧编辑感竖线 */
.post-card::before {
  content: ""; position: absolute; left: 0; top: 18px; bottom: 18px;
  width: 3px; border-radius: 0 3px 3px 0; background: var(--brand-200);
  transition: width var(--t-base) var(--ease-out), background var(--t-base);
}
.post-card:hover {
  box-shadow: var(--shadow-md); border-color: var(--line-strong);
  transform: translateY(-2px);
}
.post-card:hover::before { width: 5px; background: var(--brand-500); }
.post-card.menu-open { z-index: 100; }
.post-card.pinned { border-color: color-mix(in srgb, var(--accent) 30%, var(--line)); }
.post-card.pinned::before { background: var(--accent); }
.pin-flag {
  position: absolute; top: 0; right: 18px; transform: translateY(-50%);
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--accent-soft); color: var(--accent-strong);
  font-size: 11.5px; font-weight: 650; padding: 3px 10px; border-radius: 999px;
  letter-spacing: .3px;
}
.pc-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.pc-user { display: flex; align-items: center; gap: 11px; min-width: 0; color: inherit; }
.pc-user:hover .pc-name { color: var(--brand-700); }
.pc-user-meta { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.pc-name-row { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.pc-name { font-weight: 650; color: var(--ink); font-size: 14.5px; }
.staff-tag {
  font-size: 11px; font-weight: 600; color: var(--brand-700);
  background: var(--brand-50); border-radius: 6px; padding: 1px 6px; line-height: 1.5;
}
.pc-sub { font-size: 12.5px; color: var(--ink-4); display: flex; gap: 6px; align-items: center; }
.pc-cat {
  color: var(--accent-strong); background: var(--accent-soft);
  padding: 1px 8px; border-radius: 4px; font-size: 11.5px; font-weight: 550;
}
.pc-body { display: block; margin: 14px 0 10px; color: inherit; }
.pc-title {
  font-family: var(--font-display); font-size: 19px; font-weight: 700;
  color: var(--ink); margin-bottom: 8px; line-height: 1.4;
  letter-spacing: -.01em;
}
.pc-text {
  color: var(--ink-2); font-size: 14.5px; line-height: 1.75;
  white-space: pre-wrap; word-break: break-word;
}
.video-chip {
  display: inline-flex; align-items: center; gap: 8px; margin: 4px 0 10px;
  padding: 8px 14px; border-radius: var(--r-pill); background: var(--surface-3);
  color: var(--ink-2); font-size: 13px;
}
.video-chip:hover { background: var(--brand-50); color: var(--brand-700); }
.pc-foot {
  display: flex; align-items: center; gap: 4px; margin-top: 14px;
  padding-top: 12px; border-top: 1px solid var(--line);
}
.act {
  display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px;
  border-radius: var(--r-pill); color: var(--ink-3); font-size: 13.5px;
  transition: background var(--t-fast), color var(--t-fast), transform var(--t-fast);
}
.act:hover { background: var(--surface-3); color: var(--ink); }
.act:active { transform: scale(.94); }
.act.on { color: var(--danger-strong); }
.act.fav.on { color: var(--brand-700); background: var(--brand-50); }
.act.views { margin-left: auto; pointer-events: none; font-size: 13px; }
.more-wrap { position: relative; margin-left: 4px; }
.menu {
  position: absolute; right: 0; top: calc(100% + 6px); z-index: var(--z-dropdown);
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-md);
  box-shadow: var(--shadow-pop); padding: 6px; min-width: 140px;
}
.menu button {
  display: flex; align-items: center; gap: 9px; width: 100%; text-align: left;
  padding: 8px 10px; border-radius: var(--r-xs); font-size: 13.5px; color: var(--ink-2);
}
.menu button:hover { background: var(--surface-3); }
.menu button.danger { color: var(--danger-strong); }
.menu-enter-active, .menu-leave-active { transition: all var(--t-fast) var(--ease-out); }
.menu-enter-from, .menu-leave-to { opacity: 0; transform: translateY(-5px); }
</style>
