<template>
  <el-card v-loading="loading" style="max-width:640px">
    <el-form label-width="140px" label-position="right">
      <el-form-item label="站点名称">
        <el-input v-model="form.site_name" placeholder="如：校园墙" maxlength="30" show-word-limit />
      </el-form-item>
      <el-form-item label="开放注册">
        <el-switch v-model="form.allow_register" active-text="允许新用户注册" inactive-text="关闭注册" />
      </el-form-item>
      <el-form-item label="发帖先审核">
        <el-switch v-model="form.post_need_review" active-text="新帖需管理员审核后展示" inactive-text="发帖直接发布" />
      </el-form-item>
      <el-form-item label="页脚备注">
        <el-input v-model="form.footer_note" type="textarea" :rows="3" placeholder="显示在移动端的备注/备案信息" maxlength="200" show-word-limit />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
        <el-button @click="load">重置</el-button>
      </el-form-item>
    </el-form>
    <el-alert type="info" :closable="false" show-icon
      title="关闭注册后，注册接口将拒绝新用户；发帖审核开启后用户新发的帖子进入「待审核」，可在帖子管理中通过或驳回。" />
  </el-card>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
const loading = ref(false); const saving = ref(false)
const form = ref({ site_name: '校园墙', allow_register: true, post_need_review: false, footer_note: '' })
const load = async () => {
  loading.value = true
  try { const res = await api.get('/admin/settings'); form.value = res.data } finally { loading.value = false }
}
const save = async () => {
  saving.value = true
  try { await api.put('/admin/settings', form.value); ElMessage.success('设置已保存') } finally { saving.value = false }
}
onMounted(load)
</script>
