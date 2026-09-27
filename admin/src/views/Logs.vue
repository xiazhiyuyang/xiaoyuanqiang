<template>
  <el-card>
    <div style="margin-bottom:16px;display:flex;gap:10px;flex-wrap:wrap">
      <el-select v-model="action" placeholder="全部动作" clearable style="width:200px" @change="reload">
        <el-option v-for="a in actions" :key="a.action" :label="a.label" :value="a.action" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索用户名/详情" style="width:240px" clearable @clear="reload" @keyup.enter="reload">
        <template #append><el-button @click="reload">搜索</el-button></template>
      </el-input>
    </div>
    <el-table :data="list" v-loading="loading" border stripe size="small">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="操作人" width="130" />
      <el-table-column prop="action_text" label="动作" width="150">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'fail' ? 'danger' : row.status === 'success' ? 'success' : 'info'">
            {{ row.action_text }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="detail" label="详情" show-overflow-tooltip />
      <el-table-column prop="ip" label="IP" width="130" />
      <el-table-column prop="created_at" label="时间" width="180">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
    </el-table>
    <el-pagination style="margin-top:16px;justify-content:flex-end;display:flex"
      v-model:current-page="page" v-model:page-size="pageSize" :total="total"
      layout="total, prev, pager, next" @current-change="loadData" />
  </el-card>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
const list = ref([]); const loading = ref(false); const page = ref(1); const pageSize = ref(30)
const total = ref(0); const keyword = ref(''); const action = ref(''); const actions = ref([])
const fmt = (s) => new Date(s).toLocaleString('zh-CN')
const reload = () => { page.value = 1; loadData() }
const loadData = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/logs', { params: { page: page.value, page_size: pageSize.value, action: action.value, keyword: keyword.value } })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}
onMounted(async () => {
  try { const r = await api.get('/admin/logs/actions'); actions.value = r.data } catch (e) {}
  loadData()
})
</script>
