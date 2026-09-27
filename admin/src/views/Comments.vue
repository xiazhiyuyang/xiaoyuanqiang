<template>
  <el-card>
    <div style="margin-bottom:16px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px">
      <el-input v-model="keyword" placeholder="搜索评论内容" style="width:100%;max-width:260px" clearable @clear="loadData" @keyup.enter="loadData">
        <template #append><el-button @click="loadData">搜索</el-button></template>
      </el-input>
    </div>
    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="author_name" label="评论者" width="140" />
      <el-table-column prop="content" label="内容" show-overflow-tooltip />
      <el-table-column prop="post_id" label="所属帖子" width="100" />
      <el-table-column prop="like_count" label="赞" width="70" />
      <el-table-column prop="created_at" label="时间" width="180">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination style="margin-top:16px;justify-content:flex-end;display:flex"
      v-model:current-page="page" v-model:page-size="pageSize" :total="total"
      layout="total, prev, pager, next" @current-change="loadData" />
  </el-card>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
const list = ref([]); const loading = ref(false); const page = ref(1); const pageSize = ref(20)
const total = ref(0); const keyword = ref('')
const fmt = (s) => new Date(s).toLocaleString('zh-CN')
const loadData = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/comments', { params: { page: page.value, page_size: pageSize.value, keyword: keyword.value } })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}
const remove = async (row) => {
  await ElMessageBox.confirm(`确定删除该评论吗？`, '提示', { type: 'warning' })
  await api.delete(`/admin/comments/${row.id}`)
  ElMessage.success('已删除'); loadData()
}
onMounted(loadData)
</script>
