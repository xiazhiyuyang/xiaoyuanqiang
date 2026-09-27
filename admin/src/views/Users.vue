<template>
  <el-card>
    <div style="margin-bottom:16px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px">
      <el-input v-model="keyword" placeholder="搜索用户名/昵称" style="width:100%;max-width:260px" clearable @clear="loadData" @keyup.enter="loadData">
        <template #append><el-button @click="loadData">搜索</el-button></template>
      </el-input>
    </div>
    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="nickname" label="昵称" />
      <el-table-column prop="role" label="角色" width="80">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : ''">{{ row.role === 'admin' ? '管理员' : '用户' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_banned" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_banned ? 'danger' : 'success'">{{ row.is_banned ? '已封禁' : '正常' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button size="small" :type="row.is_banned ? 'success' : 'danger'" @click="toggleBan(row)">
            {{ row.is_banned ? '解封' : '封禁' }}
          </el-button>
          <el-button
            size="small" :type="row.role === 'admin' ? 'warning' : 'primary'"
            plain
            @click="toggleRole(row)"
          >
            {{ row.role === 'admin' ? '取消管理员' : '设为管理员' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      style="margin-top:16px;justify-content:flex-end;display:flex"
      v-model:current-page="page" v-model:page-size="pageSize" :total="total"
      layout="total, prev, pager, next" @current-change="loadData"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const list = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

const formatDate = (s) => new Date(s).toLocaleString('zh-CN')

const loadData = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/users', { params: { page: page.value, page_size: pageSize.value, keyword: keyword.value } })
    list.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const toggleBan = async (row) => {
  await ElMessageBox.confirm(`确定要${row.is_banned ? '解封' : '封禁'}用户「${row.nickname}」吗？`, '提示', { type: 'warning' })
  await api.post(`/admin/users/${row.id}/ban`)
  ElMessage.success('操作成功')
  loadData()
}

const toggleRole = async (row) => {
  const makeAdmin = row.role !== 'admin'
  await ElMessageBox.confirm(
    `确定要${makeAdmin ? '将「' + row.nickname + '」设为管理员' : '取消「' + row.nickname + '」的管理员身份'}吗？`,
    '权限变更', { type: makeAdmin ? 'info' : 'warning' }
  )
  await api.put(`/admin/users/${row.id}/role`, { role: makeAdmin ? 'admin' : 'user' })
  ElMessage.success('角色已更新')
  loadData()
}
onMounted(loadData)
</script>
