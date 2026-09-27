<template>
  <el-card>
    <el-tabs v-model="activeTab">
      <!-- 广告位 -->
      <el-tab-pane label="广告位" name="banner">
        <div class="toolbar">
          <span class="tip">首页顶部轮播广告，不上传图片时显示渐变主题卡片，最多建议 5 张</span>
          <el-button type="primary" @click="openBannerDialog()">新增广告</el-button>
        </div>
        <el-table :data="banners" v-loading="loading" stripe>
          <el-table-column label="预览" width="220">
            <template #default="{ row }">
              <div class="preview" :class="'theme-' + row.theme">
                <img v-if="row.image_url" :src="row.image_url" alt="" />
                <span v-else>{{ row.title }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="160" />
          <el-table-column label="主题" width="90">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ themeName(row.theme) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="跳转链接" min-width="160">
            <template #default="{ row }">
              <span class="link-text">{{ row.link_url || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="70" />
          <el-table-column label="上架" width="80">
            <template #default="{ row }">
              <el-switch :model-value="row.is_active" @change="(v) => toggleBanner(row, v)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130">
            <template #default="{ row }">
              <el-button size="small" @click="openBannerDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeBanner(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <!-- 公告位 -->
      <el-tab-pane label="公告位" name="announcement">
        <div class="toolbar">
          <span class="tip">首页公告条轮播展示，建议每条不超过 40 字</span>
          <el-button type="primary" @click="openAnnDialog()">新增公告</el-button>
        </div>
        <el-table :data="announcements" v-loading="loading" stripe>
          <el-table-column prop="content" label="公告内容" min-width="260" />
          <el-table-column label="跳转链接" min-width="160">
            <template #default="{ row }">
              <span class="link-text">{{ row.link_url || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="70" />
          <el-table-column label="展示" width="80">
            <template #default="{ row }">
              <el-switch :model-value="row.is_active" @change="(v) => toggleAnn(row, v)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130">
            <template #default="{ row }">
              <el-button size="small" @click="openAnnDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeAnn(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 广告编辑弹窗 -->
    <el-dialog v-model="bannerDialog" :title="bannerForm.id ? '编辑广告' : '新增广告'" width="min(480px, 92vw)">
      <el-form :model="bannerForm" label-width="92px">
        <el-form-item label="标题" required>
          <el-input v-model="bannerForm.title" maxlength="30" show-word-limit placeholder="无图片时展示在渐变卡片上" />
        </el-form-item>
        <el-form-item label="主题色">
          <el-radio-group v-model="bannerForm.theme">
            <el-radio-button value="blue">黛蓝</el-radio-button>
            <el-radio-button value="teal">松青</el-radio-button>
            <el-radio-button value="gold">琥珀</el-radio-button>
            <el-radio-button value="ink">墨灰</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="广告图片">
          <el-upload
            :headers="uploadHeaders"
            action="/api/upload/image"
            :show-file-list="false"
            accept="image/*"
            :on-success="onBannerUploaded"
          >
            <el-button>上传图片</el-button>
          </el-upload>
          <el-input v-model="bannerForm.image_url" placeholder="上传后自动填入，也可粘贴图片 URL" style="margin-top:8px" />
          <div v-if="bannerForm.image_url" class="upload-preview">
            <img :src="bannerForm.image_url" alt="" />
          </div>
        </el-form-item>
        <el-form-item label="跳转链接">
          <el-input v-model="bannerForm.link_url" placeholder="站内如 /pages/post/detail?id=1，或 https 外链，留空不可点" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="bannerForm.sort_order" :min="0" :max="9999" />
          <span class="form-hint">数值越大越靠前</span>
        </el-form-item>
        <el-form-item label="立即上架">
          <el-switch v-model="bannerForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bannerDialog = false">取消</el-button>
        <el-button type="primary" @click="submitBanner">保存</el-button>
      </template>
    </el-dialog>

    <!-- 公告编辑弹窗 -->
    <el-dialog v-model="annDialog" :title="annForm.id ? '编辑公告' : '新增公告'" width="min(480px, 92vw)">
      <el-form :model="annForm" label-width="92px">
        <el-form-item label="公告内容" required>
          <el-input v-model="annForm.content" type="textarea" :rows="3" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="跳转链接">
          <el-input v-model="annForm.link_url" placeholder="选填，站内路径或 https 外链" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="annForm.sort_order" :min="0" :max="9999" />
          <span class="form-hint">数值越大越靠前</span>
        </el-form-item>
        <el-form-item label="立即展示">
          <el-switch v-model="annForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="annDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAnn">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const activeTab = ref('banner')
const loading = ref(false)
const banners = ref([])
const announcements = ref([])

const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('admin_token') || ''}`,
}))
const themeName = (t) => ({ blue: '黛蓝', teal: '松青', gold: '琥珀', ink: '墨灰' }[t] || t)

const loadData = async () => {
  loading.value = true
  try {
    const [b, a] = await Promise.all([
      api.get('/admin/banners'),
      api.get('/admin/announcements'),
    ])
    banners.value = b.data
    announcements.value = a.data
  } finally {
    loading.value = false
  }
}

const bannerDialog = ref(false)
const bannerForm = ref({ id: null, title: '', theme: 'blue', image_url: '', link_url: '', sort_order: 0, is_active: true })
const openBannerDialog = (row) => {
  bannerForm.value = row
    ? { ...row }
    : { id: null, title: '', theme: 'blue', image_url: '', link_url: '', sort_order: 0, is_active: true }
  bannerDialog.value = true
}
const onBannerUploaded = (res) => {
  if (res.code === 0) {
    bannerForm.value.image_url = res.data.url
    ElMessage.success('图片上传成功')
  } else {
    ElMessage.error(res.msg || '上传失败')
  }
}
const submitBanner = async () => {
  if (!bannerForm.value.title?.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  const payload = { ...bannerForm.value }
  delete payload.id
  if (bannerForm.value.id) {
    await api.put(`/admin/banners/${bannerForm.value.id}`, payload)
  } else {
    await api.post('/admin/banners', payload)
  }
  ElMessage.success('已保存')
  bannerDialog.value = false
  loadData()
}
const toggleBanner = async (row, v) => {
  await api.put(`/admin/banners/${row.id}`, { is_active: v })
  row.is_active = v
}
const removeBanner = async (row) => {
  await ElMessageBox.confirm(`确定删除广告「${row.title}」吗？`, '提示', { type: 'warning' })
  await api.delete(`/admin/banners/${row.id}`)
  ElMessage.success('已删除')
  loadData()
}

const annDialog = ref(false)
const annForm = ref({ id: null, content: '', link_url: '', sort_order: 0, is_active: true })
const openAnnDialog = (row) => {
  annForm.value = row
    ? { ...row }
    : { id: null, content: '', link_url: '', sort_order: 0, is_active: true }
  annDialog.value = true
}
const submitAnn = async () => {
  if (!annForm.value.content?.trim()) {
    ElMessage.warning('请填写公告内容')
    return
  }
  const payload = { ...annForm.value }
  delete payload.id
  if (annForm.value.id) {
    await api.put(`/admin/announcements/${annForm.value.id}`, payload)
  } else {
    await api.post('/admin/announcements', payload)
  }
  ElMessage.success('已保存')
  annDialog.value = false
  loadData()
}
const toggleAnn = async (row, v) => {
  await api.put(`/admin/announcements/${row.id}`, { is_active: v })
  row.is_active = v
}
const removeAnn = async (row) => {
  await ElMessageBox.confirm(`确定删除公告「${row.content.slice(0, 20)}」吗？`, '提示', { type: 'warning' })
  await api.delete(`/admin/announcements/${row.id}`)
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>
<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; gap: 12px; flex-wrap: wrap; }
.tip { font-size: 13px; color: var(--ink-3, #9aa1ae); }
.preview {
  width: 190px; height: 64px; border-radius: 8px; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  padding: 0 14px; color: #fff; font-size: 12px; font-weight: 600;
}
.preview.theme-blue { background: linear-gradient(135deg, #6366f1, #a855f7); }
.preview.theme-teal { background: linear-gradient(135deg, #2e6e68, #4b9a90); }
.preview.theme-gold { background: linear-gradient(135deg, #b07d22, #d99a2b); }
.preview.theme-ink { background: linear-gradient(135deg, #333a4a, #5b6270); }
.preview img { width: 100%; height: 100%; object-fit: cover; }
.link-text { font-size: 12px; color: #9aa1ae; word-break: break-all; }
.form-hint { margin-left: 12px; font-size: 12px; color: #9aa1ae; }
.upload-preview { margin-top: 8px; }
.upload-preview img { max-width: 200px; max-height: 90px; border-radius: 6px; border: 1px solid var(--el-border-color-lighter); }
</style>
