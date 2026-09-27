<template>
  <div class="comment" :class="{ reply: depth > 0 }">
    <RouterLink :to="comment.author ? `/u/${comment.author.id}` : '#'">
      <UserAvatar :src="comment.author?.avatar" :name="comment.author?.nickname" :anonymous="!comment.author"
        :seed="comment.id" :size="depth ? 34 : 40" />
    </RouterLink>
    <div class="c-body">
      <div class="c-bubble">
        <div class="c-name">
          {{ comment.author?.nickname || comment.author_name || '匿名同学' }}
          <span v-if="replyName" class="c-reply">回复 <em>@{{ replyName }}</em></span>
        </div>
        <p class="c-text">{{ comment.content }}</p>
      </div>
      <div class="c-meta">
        <span class="c-time faint">{{ timeAgo(comment.created_at) }}</span>
        <button class="c-act" :class="{ on: comment.is_liked }" @click="onLike">
          <Icon name="heart" :size="14" :filled="comment.is_liked" /> {{ comment.like_count || 0 }}
        </button>
        <button v-if="auth.isLoggedIn" class="c-act" @click="replying = !replying"><Icon name="comment" :size="14" /> 回复</button>
        <button v-if="canDelete" class="c-act danger" @click="onDelete"><Icon name="trash" :size="14" /> 删除</button>
        <button v-if="!isMine && auth.isLoggedIn" class="c-act danger" @click="reportOpen = true">举报</button>
      </div>

      <div v-if="replying" class="c-reply-box">
        <textarea v-model="replyText" class="textarea" rows="2" :placeholder="`回复 @${comment.author?.nickname || '同学'}`" />
        <div class="c-reply-actions">
          <button class="btn btn-ghost btn-sm" @click="replying = false; replyText = ''">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="submitting || !replyText.trim()" @click="submitReply">回复</button>
        </div>
      </div>

      <div v-if="comment.replies && comment.replies.length" class="replies">
        <CommentItem
          v-for="r in comment.replies" :key="r.id"
          :comment="r" :post-id="postId" :root-id="rootId" :depth="depth + 1"
          :name-map="nameMap"
          @changed="$emit('changed')"
        />
      </div>
    </div>

    <ReportDialog v-model="reportOpen" target-type="comment" :target-id="comment.id" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Icon from './Icon.vue'
import UserAvatar from './UserAvatar.vue'
import ReportDialog from './ReportDialog.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { timeAgo } from '../utils/format'
import { toast } from '../utils/toast'

const props = defineProps({
  comment: { type: Object, required: true },
  postId: { type: [Number, String], required: true },
  rootId: { type: [Number, String], default: null },
  depth: { type: Number, default: 0 },
  nameMap: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['changed'])
const router = useRouter()
const auth = useAuth()

const replying = ref(false)
const replyText = ref('')
const submitting = ref(false)
const reportOpen = ref(false)

const isMine = computed(() => props.comment.author && auth.user && props.comment.author.id === auth.user.id)
const canDelete = computed(() => isMine.value || auth.isAdmin)
const replyName = computed(() =>
  props.comment.reply_to_user_id ? props.nameMap[props.comment.reply_to_user_id] : ''
)

async function onLike() {
  if (!auth.isLoggedIn) return router.push('/login')
  const prev = props.comment.is_liked
  props.comment.is_liked = !prev
  props.comment.like_count += props.comment.is_liked ? 1 : -1
  try {
    await api.likeComment(props.postId, props.comment.id)
  } catch { props.comment.is_liked = prev; props.comment.like_count += prev ? 1 : -1 }
}
async function submitReply() {
  const text = replyText.value.trim()
  if (!text) return
  submitting.value = true
  try {
    const res = await api.createComment(props.postId, {
      content: text,
      parent_id: props.rootId || props.comment.id,
      reply_to_user_id: props.comment.author?.id,
    })
    replyText.value = ''; replying.value = false
    const msg = res?._msg || ''
    if (msg && /审核|复核|打码|等待/.test(msg)) {
      toast.info(msg)
    } else {
      toast.success('回复成功')
    }
    emit('changed')
  } catch { /* handled */ } finally { submitting.value = false }
}
async function onDelete() {
  if (!window.confirm('删除这条评论？')) return
  try { await api.deleteComment(props.postId, props.comment.id); toast.success('已删除'); emit('changed') } catch { /* */ }
}
</script>

<style scoped>
.comment { display: flex; gap: 12px; padding: 16px 0; }
.comment.reply { padding: 12px 0 0; }
.c-body { flex: 1; min-width: 0; }
.c-bubble { background: var(--surface-2); border-radius: 4px 14px 14px 14px; padding: 10px 14px; display: inline-block; max-width: 100%; }
.comment.reply .c-bubble { background: var(--surface-3); }
.c-name { font-size: 13px; font-weight: 650; color: var(--brand-700); margin-bottom: 3px; }
.c-reply { font-weight: 500; color: var(--ink-4); margin-left: 6px; }
.c-reply em { font-style: normal; color: var(--ink-3); }
.c-text { font-size: 14.5px; line-height: 1.7; color: var(--ink); white-space: pre-wrap; word-break: break-word; }
.c-meta { display: flex; align-items: center; gap: 14px; margin-top: 7px; padding-left: 4px; }
.c-time { font-size: 12px; }
.c-act { display: inline-flex; align-items: center; gap: 4px; font-size: 12.5px; color: var(--ink-4); transition: color var(--t-fast); padding: 2px 4px; border-radius: 6px; }
.c-act:hover { color: var(--ink-2); background: var(--surface-3); }
.c-act.on { color: var(--danger-strong); }
.c-act.danger:hover { color: var(--danger-strong); }
.c-reply-box { margin-top: 10px; }
.c-reply-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
.replies { margin-top: 4px; padding-left: 16px; border-left: 2px solid var(--line); margin-left: 21px; }
</style>
