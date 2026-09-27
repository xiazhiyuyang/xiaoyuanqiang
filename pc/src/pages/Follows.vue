<template>
  <div class="follows">
    <header class="follows-head card">
      <button class="back" @click="$router.back()"><Icon name="arrow-left" :size="17" /></button>
      <h2 class="grow">{{ title }}</h2>
      <div class="seg-group">
        <button :class="{ on: type === 'following' }" @click="setType('following')">关注 {{ counts.following }}</button>
        <button :class="{ on: type === 'followers' }" @click="setType('followers')">粉丝 {{ counts.followers }}</button>
      </div>
    </header>

    <div v-if="loading" class="card" style="padding:8px 18px">
      <div v-for="i in 5" :key="i" class="sk-row">
        <div class="skeleton" style="width:44px;height:44px;border-radius:50%"></div>
        <div class="grow"><div class="skeleton" style="width:150px;height:13px;margin-bottom:8px"></div><div class="skeleton" style="width:230px;height:11px"></div></div>
      </div>
    </div>

    <template v-else>
      <div class="flist card">
        <div v-for="f in items" :key="f.id" class="f-item">
          <RouterLink :to="`/u/${f.id}`" class="f-user">
            <UserAvatar :src="f.avatar" :name="f.nickname" :size="44" />
            <span class="grow">
              <span class="f-name">{{ f.nickname }}
                <span v-for="t in f.perm_tags" :key="t" class="mini-tag">{{ tagLabel(t) }}</span>
              </span>
              <span class="f-bio faint ellipsis">{{ f.bio || '这位同学还没有简介' }}</span>
            </span>
          </RouterLink>
          <FollowButton v-if="f.id !== auth.user?.id" :user-id="f.id" :model-value="f.is_following" @update:model-value="(v) => (f.is_following = v)" />
          <span v-else class="self-tag">这是你</span>
        </div>
        <EmptyState v-if="!items.length" :icon="type === 'following' ? 'users' : 'user'" :title="type === 'following' ? '还没有关注任何人' : '还没有粉丝'" description="多去互动，认识更多同校同学吧" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import UserAvatar from '../components/UserAvatar.vue'
import FollowButton from '../components/FollowButton.vue'
import EmptyState from '../components/EmptyState.vue'
import api from '../api'
import { useAuth } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()

const type = ref(route.query.type === 'followers' ? 'followers' : 'following')
const items = ref([])
const loading = ref(true)
const counts = ref({ following: 0, followers: 0 })

const isSelf = computed(() => route.meta.selfFollows || route.path === '/me/follows')
const userId = computed(() => (isSelf.value ? auth.user?.id : route.params.id))
const title = computed(() => (type.value === 'following' ? 'TA 的关注' : 'TA 的粉丝'))

function tagLabel(t) { return { admin: '管理员', content_review: '审核员', report_review: '审查员' }[t] || t }

async function load() {
  loading.value = true
  try {
    const id = userId.value
    if (!id) return
    const [r, status] = await Promise.all([
      api.getFollows(id, { type: type.value }),
      api.getFollowStatus(id).catch(() => null),
    ])
    items.value = r.items
    if (status) counts.value = { following: status.following_count || 0, followers: status.followers_count || 0 }
  } catch { items.value = [] } finally { loading.value = false }
}
function setType(t) {
  type.value = t
  router.replace({ query: { type: t } })
  load()
}
watch(() => route.params.id, load)
onMounted(load)
</script>

<style scoped>
.follows-head { display: flex; align-items: center; gap: 12px; padding: 14px 18px; margin-bottom: 16px; }
.follows-head h2 { font-size: 17px; }
.back { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--ink-3); }
.back:hover { background: var(--surface-3); color: var(--ink); }
.seg-group { display: inline-flex; border-radius: 999px; overflow: hidden; border: 1px solid var(--line-strong); background: var(--surface-2); }
.seg-group button { padding: 7px 15px; font-size: 13px; font-weight: 540; color: var(--ink-3); }
.seg-group button.on { background: var(--brand-50); color: var(--brand-700); }
.seg-group button + button { border-left: 1px solid var(--line); }
.flist { padding: 6px 10px; }
.f-item { display: flex; align-items: center; gap: 12px; padding: 12px 8px; border-radius: var(--r-md); }
.f-item:hover { background: var(--surface-2); }
.f-user { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; color: inherit; }
.f-name { font-size: 14.5px; font-weight: 620; color: var(--ink); display: flex; align-items: center; gap: 6px; }
.f-bio { font-size: 12.5px; display: block; margin-top: 2px; }
.mini-tag { font-size: 10.5px; color: var(--brand-700); background: var(--brand-50); padding: 0 5px; border-radius: 5px; }
.self-tag { font-size: 12.5px; color: var(--ink-4); padding-right: 8px; }
.sk-row { display: flex; gap: 12px; align-items: center; padding: 13px 0; }
</style>
