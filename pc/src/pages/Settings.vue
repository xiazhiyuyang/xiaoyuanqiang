<template>
  <div class="settings">
    <h1 class="page-title">设置</h1>

    <!-- 资料 -->
    <section class="card set-card">
      <h2>个人资料</h2>
      <div class="avatar-row">
        <UserAvatar :src="form.avatar" :name="form.nickname" :size="72" />
        <div>
          <button class="btn btn-soft btn-sm" :disabled="uploading" @click="$refs.avatarInput.click()">
            {{ uploading ? '上传中…' : '更换头像' }}
          </button>
          <p class="faint tip">支持 JPG/PNG，建议正方形图片</p>
        </div>
        <input ref="avatarInput" type="file" accept="image/*" hidden @change="onAvatar" />
      </div>
      <div class="cover-row">
        <div class="cover-preview" :style="{ background: form.cover_image ? `url(${form.cover_image}) center/cover` : 'linear-gradient(120deg,#bd7b1f,#9a5f12)' }">
          <span v-if="!form.cover_image" class="cover-placeholder">默认封面</span>
        </div>
        <div>
          <button class="btn btn-soft btn-sm" :disabled="uploadingCover" @click="$refs.coverInput.click()">
            {{ uploadingCover ? '上传中…' : '更换封面' }}
          </button>
          <button v-if="form.cover_image" class="btn btn-ghost btn-sm" @click="removeCover">移除封面</button>
          <p class="faint tip">支持 JPG/PNG，建议宽幅图片（1200×400）</p>
        </div>
        <input ref="coverInput" type="file" accept="image/*" hidden @change="onCover" />
      </div>
      <div class="form-grid">
        <div class="field"><label>昵称</label><input v-model.trim="form.nickname" class="input" maxlength="32" /></div>
        <div class="field">
          <label>性别</label>
          <select v-model="form.gender" class="select">
            <option value="unknown">保密</option><option value="male">男</option><option value="female">女</option>
          </select>
        </div>
        <div class="field field-wide"><label>个人简介</label><textarea v-model="form.bio" class="textarea" rows="2" maxlength="200" /></div>
        <div class="field"><label>年级</label><input v-model.trim="form.grade" class="input" placeholder="如 2024 级" /></div>
        <div class="field"><label>生日</label><input v-model="form.birthday" class="input" type="date" /></div>
        <div class="field"><label>学院</label><input v-model.trim="form.college" class="input" /></div>
        <div class="field"><label>专业</label><input v-model.trim="form.major" class="input" /></div>
        <div class="field"><label>所在地</label><input v-model.trim="form.location" class="input" /></div>
        <div class="field"><label>学号</label><input v-model.trim="form.student_id" class="input" /></div>
        <div class="field"><label>手机号</label><input v-model.trim="form.phone" class="input" maxlength="11" /></div>
      </div>
      <p v-if="errors.profile" class="field-error">{{ errors.profile }}</p>
      <div class="set-actions">
        <button class="btn btn-primary" :disabled="saving.profile" @click="saveProfile">{{ saving.profile ? '保存中…' : '保存资料' }}</button>
      </div>
    </section>

    <!-- 隐私 -->
    <section class="card set-card">
      <h2>隐私设置</h2>
      <p class="muted set-desc">控制其他同学能看到你的哪些信息。手机号、学号始终仅自己可见。</p>
      <div class="privacy-list">
        <label v-for="row in privacyRows" :key="row.key" class="privacy-row">
          <span class="grow"><strong>{{ row.label }}</strong></span>
          <select v-model="privacy[row.key]" class="select privacy-select">
            <option value="public">所有人</option><option value="members">仅登录用户</option><option value="private">仅自己</option>
          </select>
        </label>
      </div>
      <div class="set-actions"><button class="btn btn-primary" :disabled="saving.privacy" @click="savePrivacy">{{ saving.privacy ? '保存中…' : '保存隐私设置' }}</button></div>
    </section>

    <!-- 通知偏好 -->
    <section class="card set-card">
      <h2>通知偏好</h2>
      <div class="switch-list">
        <label v-for="row in notifyRows" :key="row.key" class="switch-row">
          <span class="grow"><strong>{{ row.label }}</strong></span>
          <input type="checkbox" v-model="prefs[row.key]" class="switch" />
        </label>
      </div>
      <div class="set-actions"><button class="btn btn-primary" :disabled="saving.prefs" @click="savePrefs">{{ saving.prefs ? '保存中…' : '保存通知设置' }}</button></div>
    </section>

    <!-- 安全 -->
    <section class="card set-card">
      <h2>账号安全</h2>
      <div class="form-grid">
        <div class="field field-wide"><label>当前密码</label><input v-model="pwd.old_password" class="input" type="password" autocomplete="current-password" /></div>
        <div class="field"><label>新密码</label><input v-model="pwd.new_password" class="input" type="password" placeholder="≥8 位" /></div>
        <div class="field"><label>确认新密码</label><input v-model="pwd.confirm" class="input" type="password" /></div>
      </div>
      <p v-if="errors.pwd" class="field-error">{{ errors.pwd }}</p>
      <div class="set-actions"><button class="btn btn-primary" :disabled="saving.pwd" @click="savePwd">{{ saving.pwd ? '提交中…' : '修改密码' }}</button></div>

      <div class="divider" />
      <h3 class="sub-title">密保问题（用于找回密码）</h3>
      <div class="form-grid">
        <div class="field">
          <label>密保问题</label>
          <select v-model="sq.question" class="select">
            <option value="">请选择</option>
            <option>你的小学校名是？</option><option>你最喜欢的一本书是？</option>
            <option>你出生地的地名是？</option><option>你宠物的名字是？</option>
          </select>
        </div>
        <div class="field"><label>答案</label><input v-model.trim="sq.answer" class="input" /></div>
      </div>
      <div class="set-actions"><button class="btn btn-soft" :disabled="saving.sq" @click="saveSq">{{ saving.sq ? '保存中…' : '保存密保' }}</button></div>

      <div class="divider" />
      <h3 class="sub-title danger-title">注销账号</h3>
      <p class="muted-text">注销后将进入 7 天冷静期，期间可撤销；到期后账号将被永久注销，UID 封存不再启用。</p>
      <div class="deletion-area">
        <div v-if="deletionStatus.has_request" class="deletion-pending">
          <p><strong>注销申请处理中</strong></p>
          <p>申请时间：{{ formatTime(deletionStatus.requested_at) }}</p>
          <p>计划注销时间：<span class="danger-text">{{ formatTime(deletionStatus.scheduled_at) }}</span></p>
          <button class="btn btn-soft" :disabled="canceling" @click="cancelDeletion">{{ canceling ? '撤销中…' : '撤销注销申请' }}</button>
        </div>
        <div v-else class="deletion-form">
          <input v-model="deletionPwd" class="input" type="password" placeholder="输入登录密码确认身份" style="max-width:320px" />
          <button class="btn btn-danger" :disabled="!deletionPwd || requesting" @click="requestDeletion">{{ requesting ? '提交中…' : '提交注销申请' }}</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import UserAvatar from '../components/UserAvatar.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { toast } from '../utils/toast'

const auth = useAuth()
const form = reactive({ nickname: '', avatar: '', cover_image: '', bio: '', gender: 'unknown', grade: '', college: '', major: '', location: '', birthday: '', student_id: '', phone: '' })
const privacy = reactive({ gender: 'public', school: 'public', location: 'members', birthday: 'private' })
const prefs = reactive({ notify_like: true, notify_comment: true, notify_follow: true, notify_system: true })
const pwd = reactive({ old_password: '', new_password: '', confirm: '' })
const sq = reactive({ question: '', answer: '' })
const saving = reactive({ profile: false, privacy: false, prefs: false, pwd: false, sq: false })
const errors = reactive({ profile: '', pwd: '' })
const uploading = ref(false)
const uploadingCover = ref(false)

const privacyRows = [
  { key: 'gender', label: '性别' },
  { key: 'school', label: '年级 / 学院 / 专业' },
  { key: 'location', label: '所在地' },
  { key: 'birthday', label: '生日' },
]
const notifyRows = [
  { key: 'notify_like', label: '收到点赞时通知我' },
  { key: 'notify_comment', label: '收到评论 / 回复时通知我' },
  { key: 'notify_follow', label: '被关注时通知我' },
  { key: 'notify_system', label: '接收系统通知' },
]

onMounted(async () => {
  try {
    const me = await api.getUser(auth.user.id)
    Object.assign(form, {
      nickname: me.nickname || '', avatar: me.avatar || '', cover_image: me.cover_image || '', bio: me.bio || '',
      gender: me.gender || 'unknown', grade: me.grade || '', college: me.college || '',
      major: me.major || '', location: me.location || '', birthday: me.birthday || '',
      student_id: auth.user.student_id || '', phone: me.phone || '',
    })
    if (me.privacy) Object.assign(privacy, me.privacy)
    const overview = await api.getOverview().catch(() => null)
    if (overview?.user?.preferences) Object.assign(prefs, overview.user.preferences)
  } catch { /* */ }
})

async function onAvatar(e) {
  const file = (e.target.files || [])[0]
  e.target.value = ''
  if (!file) return
  uploading.value = true
  try {
    const r = await api.uploadMedia(file, 'image')
    form.avatar = r.url
    await api.updateMe({ avatar: r.url })
    await auth.fetchMe()
    toast.success('头像已更新')
  } catch (err) { toast.error(err.message || '上传失败') } finally { uploading.value = false }
}
async function onCover(e) {
  const file = (e.target.files || [])[0]
  e.target.value = ''
  if (!file) return
  uploadingCover.value = true
  try {
    const r = await api.uploadMedia(file, 'image')
    form.cover_image = r.url
    await api.updateMe({ cover_image: r.url })
    toast.success('封面已更新')
  } catch (err) { toast.error(err.message || '上传失败') } finally { uploadingCover.value = false }
}
async function removeCover() {
  form.cover_image = ''
  await api.updateMe({ cover_image: '' })
  toast.success('封面已移除')
}
async function saveProfile() {
  errors.profile = ''
  if (!form.nickname.trim()) { errors.profile = '昵称不能为空'; return }
  saving.profile = true
  try {
    const payload = { ...form }
    Object.keys(payload).forEach((k) => { if (payload[k] === '') payload[k] = null })
    await api.updateMe(payload)
    await auth.fetchMe()
    toast.success('资料已保存')
  } catch (e) { errors.profile = e.response?.data?.detail || e.message } finally { saving.profile = false }
}
async function savePrivacy() {
  saving.privacy = true
  try { await api.updateMe({ privacy: { ...privacy } }); toast.success('隐私设置已保存') }
  catch (e) { toast.error(e.message) } finally { saving.privacy = false }
}
async function savePrefs() {
  saving.prefs = true
  try { await api.updateMe({ preferences: { ...prefs } }); toast.success('通知设置已保存') }
  catch (e) { toast.error(e.message) } finally { saving.prefs = false }
}
async function savePwd() {
  errors.pwd = ''
  if (!pwd.old_password || !pwd.new_password) { errors.pwd = '请填写完整'; return }
  if (pwd.new_password.length < 8) { errors.pwd = '新密码至少 8 位'; return }
  if (pwd.new_password !== pwd.confirm) { errors.pwd = '两次新密码不一致'; return }
  saving.pwd = true
  try {
    await api.changePassword({ old_password: pwd.old_password, new_password: pwd.new_password })
    toast.success('密码已修改，请重新登录')
    pwd.old_password = pwd.new_password = pwd.confirm = ''
  } catch (e) { errors.pwd = e.response?.data?.detail || e.message } finally { saving.pwd = false }
}
async function saveSq() {
  if (!sq.question || !sq.answer) { toast.error('请选择问题并填写答案'); return }
  saving.sq = true
  try { await api.setSecurityQuestion({ question: sq.question, answer: sq.answer }); toast.success('密保已保存'); sq.answer = '' }
  catch (e) { toast.error(e.message) } finally { saving.sq = false }
}

// ===== 账号注销 =====
const deletionPwd = ref('')
const requesting = ref(false)
const canceling = ref(false)
const deletionStatus = reactive({ has_request: false, requested_at: '', scheduled_at: '' })

function formatTime(iso) {
  if (!iso) return ''
  try { return new Date(iso.replace(' ', 'T')).toLocaleString('zh-CN', { hour12: false }) } catch (e) { return iso }
}

async function loadDeletionStatus() {
  try {
    const res = await api.getDeletionStatus()
    deletionStatus.has_request = res.has_request
    deletionStatus.requested_at = res.requested_at
    deletionStatus.scheduled_at = res.scheduled_at
  } catch (e) {}
}

async function requestDeletion() {
  if (!deletionPwd.value) { toast.error('请输入登录密码'); return }
  if (!confirm('提交注销申请后将进入7天冷静期，期间可撤销。确认提交吗？')) return
  requesting.value = true
  try {
    const res = await api.requestDeletion(deletionPwd.value)
    deletionStatus.has_request = true
    deletionStatus.requested_at = res.requested_at
    deletionStatus.scheduled_at = res.scheduled_at
    deletionPwd.value = ''
    toast.success('注销申请已提交')
  } catch (e) { toast.error(e.response?.data?.detail || e.message) } finally { requesting.value = false }
}

async function cancelDeletion() {
  if (!confirm('确认撤销注销申请？')) return
  canceling.value = true
  try {
    await api.cancelDeletion()
    deletionStatus.has_request = false
    deletionStatus.requested_at = ''
    deletionStatus.scheduled_at = ''
    toast.success('已撤销注销申请')
  } catch (e) { toast.error(e.message) } finally { canceling.value = false }
}

onMounted(() => { loadDeletionStatus() })
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 16px; }
.set-card { padding: 22px 24px; margin-bottom: 16px; }
.set-card h2 { font-size: 16.5px; margin-bottom: 16px; }
.sub-title { font-size: 14.5px; margin: 4px 0 14px; }
.set-desc { font-size: 13px; margin-bottom: 16px; }
.avatar-row { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
.cover-row { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.cover-preview { width: 200px; height: 64px; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; flex: none; }
.cover-placeholder { color: #fff; font-size: 13px; opacity: 0.85; }
.tip { font-size: 12px; margin-top: 6px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.field-wide { grid-column: 1 / -1; }
.set-actions { display: flex; justify-content: flex-end; margin-top: 14px; }
.divider { height: 1px; background: var(--line); margin: 26px 0 18px; }
.privacy-list, .switch-list { display: flex; flex-direction: column; }
.privacy-row, .switch-row { display: flex; align-items: center; gap: 12px; padding: 12px 4px; border-bottom: 1px solid var(--line); }
.privacy-row:last-child, .switch-row:last-child { border-bottom: none; }
.privacy-row strong, .switch-row strong { font-size: 14px; font-weight: 560; color: var(--ink); }
.privacy-select { width: 150px; }
.switch { appearance: none; width: 44px; height: 25px; border-radius: 999px; background: var(--line-strong); position: relative; cursor: pointer; transition: background var(--t-base); flex: none; }
.switch::after { content: ''; position: absolute; top: 3px; left: 3px; width: 19px; height: 19px; border-radius: 50%; background: #fff; transition: transform var(--t-base) var(--ease-out); box-shadow: var(--shadow-xs); }
.switch:checked { background: var(--brand-600); }
.switch:checked::after { transform: translateX(19px); }
@media (max-width: 560px) { .form-grid { grid-template-columns: 1fr; } }
.danger-title { color: var(--danger, #ef4444); }
.danger-text { color: var(--danger, #ef4444); font-weight: 600; }
.muted-text { font-size: 13px; color: var(--ink-2, #6b7280); margin-bottom: 14px; line-height: 1.6; }
.deletion-area { margin-top: 8px; }
.deletion-form { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.deletion-pending { background: var(--bg-soft, #f9fafb); padding: 16px; border-radius: 10px; border: 1px solid var(--line, #e5e7eb); }
.deletion-pending p { margin: 4px 0; font-size: 13.5px; }
.btn-danger { background: linear-gradient(135deg, #fb7185, #f43f5e); color: #fff; border: none; }
.btn-danger:hover { opacity: .9; }
</style>
