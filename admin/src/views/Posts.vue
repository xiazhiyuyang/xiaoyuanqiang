<template>
  <el-card>
    <div style="margin-bottom:16px;display:flex;gap:12px;flex-wrap:wrap">
      <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width:140px" @change="loadData">
        <el-option label="已发布" value="published" />
        <el-option label="待审核" value="pending" />
        <el-option label="已删除" value="deleted" />
      </el-select>
    </div>
    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <el-table-column prop="author_name" label="作者" width="120" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column label="匿名" width="70">
        <template #default="{ row }">{{ row.is_anonymous ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="置顶" width="70">
        <template #default="{ row }"><el-tag v-if="row.is_top" type="warning" size="small">置顶</el-tag></template>
      </el-table-column>
      <el-table-column prop="view_count" label="浏览" width="70" />
      <el-table-column prop="like_count" label="点赞" width="70" />
      <el-table-column prop="comment_count" label="评论" width="70" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="toggleTop(row)">{{ row.is_top ? '取消置顶' : '置顶' }}</el-button>
          <el-button size="small" type="danger" @click="deletePost(row)" v-if="row.status !== 'deleted'">删除</el-button>
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
const statusFilter = ref('')

const statusText = (s) => ({ published: '已发布', pending: '待审核', deleted: '已删除' }[s] || s)
const statusType = (s) => ({ published: 'success', pending: 'warning', deleted: 'danger' }[s] || '')

const loadData = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/posts', { params: { page: page.value, page_size: pageSize.value, status: statusFilter.value } })
    list.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const toggleTop = async (row) => {
  await api.post(`/admin/posts/${row.id}/top`)
  ElMessage.success('操作成功')
  loadData()
}

const deletePost = async (row) => {
  await ElMessageBox.confirm(`确定删除帖子「${row.title}」吗？`, '提示', { type: 'warning' })
  await api.delete(`/admin/posts/${row.id}`)
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>
