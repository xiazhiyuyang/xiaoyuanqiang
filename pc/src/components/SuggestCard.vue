<template>
  <section v-if="users.length" class="suggest card">
    <header class="sg-head">
      <h3>推荐关注</h3>
      <button class="refresh" title="换一批" @click="load"><Icon name="refresh" :size="15" /></button>
    </header>
    <ul>
      <li v-for="u in users" :key="u.id">
        <RouterLink :to="`/u/${u.id}`" class="sg-user">
          <UserAvatar :src="u.avatar" :name="u.nickname" :size="40" />
          <span class="grow ellipsis">
            <span class="sg-name">
              {{ u.nickname }}
              <span v-for="t in u.perm_tags" :key="t" class="mini-tag">{{ tagLabel(t) }}</span>
            </span>
            <span class="sg-bio faint ellipsis">{{ u.bio || '这位同学还没有简介' }}</span>
          </span>
        </RouterLink>
        <FollowButton :user-id="u.id" :model-value="u.is_following" @update:model-value="(v) => (u.is_following = v)" />
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import UserAvatar from './UserAvatar.vue'
import FollowButton from './FollowButton.vue'
import Icon from './Icon.vue'
import api from '../api'

const users = ref([])
async function load() {
  try { users.value = await api.getSuggestions() } catch { users.value = [] }
}
onMounted(load)
function tagLabel(t) { return { admin: '管理员', content_review: '审核员', report_review: '审查员' }[t] || t }
</script>

<style scoped>
.suggest { padding: 14px 16px; }
.sg-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.sg-head h3 { font-size: 15px; }
.refresh { color: var(--ink-4); width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: transform .5s var(--ease-out), color var(--t-fast); }
.refresh:hover { color: var(--brand-700); transform: rotate(180deg); }
ul { display: flex; flex-direction: column; gap: 12px; }
li { display: flex; align-items: center; gap: 10px; }
.sg-user { display: flex; align-items: center; gap: 10px; min-width: 0; color: inherit; flex: 1; }
.sg-name { font-size: 14px; font-weight: 600; color: var(--ink); display: flex; align-items: center; gap: 5px; }
.sg-bio { font-size: 12.5px; display: block; }
.mini-tag { font-size: 10.5px; color: var(--brand-700); background: var(--brand-50); padding: 0 5px; border-radius: 5px; }
</style>
