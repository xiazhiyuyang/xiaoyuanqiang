<template>
  <el-card>
    <div style="margin-bottom:16px">
      <el-button type="primary" @click="dialogVisible = true">添加分类</el-button>
    </div>
    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="icon" label="图标" width="80" />
      <el-table-column prop="name" label="分类名" />
      <el-table-column prop="slug" label="标识" />
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click="deleteCategory(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="添加分类" width="min(400px, 92vw)">
      <el-form :model="form" label-width="80px">
        <el-form-item label="分类名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="标识"><el-input v-model="form.slug" placeholder="英文，如 confession" /></el-form-item>
        <el-form-item label="图标"><el-input v-model="form.icon" placeholder="emoji，如 ❤️" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const form = ref({ name: '', slug: '', icon: '', sort_order: 0 })

const loadData = async () => {
  loading.value = true
  try {
    const res = await api.get('/posts/categories/list')
    list.value = res.data
  } finally {
    loading.value = false
  }
}

const submit = async () => {
  if (!form.value.name || !form.value.slug) {
    ElMessage.warning('请填写分类名和标识')
    return
  }
  await api.post('/admin/categories', form.value)
  ElMessage.success('添加成功')
  dialogVisible.value = false
  form.value = { name: '', slug: '', icon: '', sort_order: 0 }
  loadData()
}

const deleteCategory = async (row) => {
  await ElMessageBox.confirm(`确定删除分类「${row.name}」吗？`, '提示', { type: 'warning' })
  await api.delete(`/admin/categories/${row.id}`)
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>
