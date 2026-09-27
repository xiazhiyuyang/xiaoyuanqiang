<template>
  <el-card>
    <div style="margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
      <el-radio-group v-model="status" @change="loadData">
        <el-radio-button label="pending">待处理</el-radio-button>
        <el-radio-button label="approved">已通过</el-radio-button>
        <el-radio-button label="rejected">已驳回</el-radio-button>
        <el-radio-button label="">全部</el-radio-button>
      </el-radio-group>
      <el-button @click="loadData">刷新</el-button>
    </div>
    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">
          <el-tag>{{ typeMap[row.target_type] || row.target_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="被举报内容" min-width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="showSnapshot(row)">
            {{ (row.snapshot || '').slice(0, 30) || `对象#${row.target_id}` }}
          </el-button>
          <div style="font-size:12px;color:#999">
            被举报人：{{ row.target_user_name || row.target_user_id || '-' }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="理由" width="110">
        <template #default="{ row }">
          <el-tag type="warning">{{ row.reason_text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reporter_name" label="举报人" width="110" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusType[row.status]">{{ statusMap[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="160">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="230">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button size="small" type="success" @click="handle(row, 'approved', false)">
              {{ row.target_type === 'user' || row.target_type === 'message' ? '属实' : '属实并删除' }}
            </el-button>
            <el-button size="small" type="danger" @click="handle(row, 'approved', true)">封禁用户</el-button>
            <el-button size="small" @click="handle(row, 'rejected', false)">驳回</el-button>
          </template>
          <span v-else style="color:#999;font-size:12px">
            {{ row.handler_name }} {{ row.handled_at ? formatDate(row.handled_at) : '' }}
          </span>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      style="margin-top:16px;justify-content:flex-end;display:flex"
      v-model:current-page="page" v-model:page-size="pageSize" :total="total"
      layout="total, prev, pager, next" @current-change="loadData"
    />

    <el-dialog v-model="dialogVisible" title="举报详情" width="min(520px, 92vw)">
      <div v-if="current" style="line-height:1.8;font-size:14px">
        <p><b>类型：</b>{{ typeMap[current.target_type] }}（对象ID：{{ current.target_id }}）</p>
        <p><b>理由：</b>{{ current.reason_text }}</p>
        <p><b>补充说明：</b>{{ current.detail || '无' }}</p>
        <p><b>被举报内容快照：</b></p>
        <div style="background:#f7f7f7;border-radius:6px;padding:10px;white-space:pre-wrap;max-height:200px;overflow:auto">
{{ current.snapshot || '（原内容已不存在）' }}
        </div>
      </div>
    </el-dialog>
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
const status = ref('pending')
const dialogVisible = ref(false)
const current = ref(null)

const typeMap = { post: '帖子', comment: '评论', user: '用户', message: '私信' }
const statusMap = { pending: '待处理', approved: '已通过', rejected: '已驳回' }
const statusType = { pending: 'danger', approved: 'success', rejected: 'info' }

const formatDate = (s) => new Date(s).toLocaleString('zh-CN')

const loadData = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/reports', {
      params: { page: page.value, page_size: pageSize.value, status: status.value || undefined },
    })
    list.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const showSnapshot = (row) => {
  current.value = row
  dialogVisible.value = true
}

const handle = async (row, statusVal, banUser) => {
  const tips = {
    approved_false: '确定判定举报属实？对应帖子/评论将被删除。',
    approved_true: '确定判定属实并封禁该用户？账号将立即无法登录和发帖。',
    rejected: '确定驳回该举报？举报将标记为不成立。',
  }
  const key = statusVal === 'approved' ? `approved_${banUser}` : 'rejected'
  await ElMessageBox.confirm(tips[key], '举报审核', { type: 'warning' })
  const res = await api.post(`/admin/reports/${row.id}/handle`, {
    status: statusVal, ban_user: banUser,
  })
  ElMessage.success(res.msg || '处理完成')
  loadData()
}

onMounted(loadData)
</script>
