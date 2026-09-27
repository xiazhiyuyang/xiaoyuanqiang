<template>
  <el-card>
    <div style="margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <el-input v-model="keyword" placeholder="搜索敏感词" style="width:180px" clearable
                  @clear="loadData" @keyup.enter="reload">
          <template #append><el-button @click="reload">搜索</el-button></template>
        </el-input>
        <el-select v-model="category" placeholder="全部分类" clearable style="width:150px" @change="reload">
          <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
        </el-select>
        <el-select v-model="action" placeholder="全部动作" clearable style="width:130px" @change="reload">
          <el-option label="直接拦截" value="block" />
          <el-option label="转人工复核" value="review" />
          <el-option label="打码" value="mask" />
          <el-option label="白名单" value="allow" />
        </el-select>
      </div>
      <div>
        <el-button type="success" @click="batchVisible = true">批量导入</el-button>
        <el-button type="primary" @click="openAdd">添加词条</el-button>
      </div>
    </div>

    <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px"
              title="动作优先级：拦截 > 转人工复核 > 打码。词条自带的动作优先于「AI 审查配置」里的分类策略，改动即时生效。" />

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="word" label="词条" min-width="140" />
      <el-table-column label="分类" width="120">
        <template #default="{ row }">
          <el-tag>{{ categoryMap[row.category] || row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="等级" width="130">
        <template #default="{ row }">
          <el-rate :model-value="row.severity || 3" disabled :max="5" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="处置动作" width="130">
        <template #default="{ row }">
          <el-tag :type="actionType(row.action)">{{ actionLabel(row.action) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="来源" width="100">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ sourceLabel(row.source) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-switch :model-value="row.is_enabled" @change="(v) => toggleEnabled(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      style="margin-top:16px;justify-content:flex-end;display:flex"
      v-model:current-page="page" v-model:page-size="pageSize" :total="total"
      layout="total, prev, pager, next" @current-change="loadData"
    />

    <!-- 新增 -->
    <el-dialog v-model="addVisible" title="添加词条" width="min(460px, 92vw)">
      <el-form label-width="90px">
        <el-form-item label="词条">
          <el-input v-model="form.word" placeholder="支持中英文，自动识别插符号/全角/繁体变体" />
        </el-form-item>
        <el-form-item label="违规分类">
          <el-select v-model="form.category" style="width:100%">
            <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="危险等级">
          <el-rate v-model="form.severity" :max="5" show-score score-template="{value} / 5" />
          <div class="hint">等级越高，风险分权重越大，越容易触发拦截</div>
        </el-form-item>
        <el-form-item label="处置动作">
          <el-radio-group v-model="form.action">
            <el-radio label="mask">打码</el-radio>
            <el-radio label="review">转人工复核</el-radio>
            <el-radio label="block">直接拦截</el-radio>
            <el-radio label="allow">白名单</el-radio>
          </el-radio-group>
          <div class="hint">白名单：命中该词的区间内，其他词条一律忽略（用于压掉正常词汇的误伤）</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" maxlength="120" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAdd">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入 -->
    <el-dialog v-model="batchVisible" title="批量导入词条" width="min(560px, 92vw)">
      <el-alert type="info" :closable="false" style="margin-bottom:12px"
                title="一行一个词（也支持逗号分隔），已存在的词自动跳过" />
      <el-input v-model="batchText" type="textarea" :rows="10"
                :placeholder="'一行一个词，例如：\n违禁词A\n违禁词B'" />
      <div style="display:flex;gap:16px;margin-top:12px;flex-wrap:wrap;align-items:center">
        <el-select v-model="batchCategory" style="width:150px">
          <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
        </el-select>
        <el-radio-group v-model="batchAction">
          <el-radio label="mask">打码</el-radio>
          <el-radio label="review">复核</el-radio>
          <el-radio label="block">拦截</el-radio>
          <el-radio label="allow">白名单</el-radio>
        </el-radio-group>
        <span class="hint">等级</span>
        <el-input-number v-model="batchSeverity" :min="1" :max="5" size="small" />
      </div>
      <template #footer>
        <el-button @click="batchVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBatch">导入</el-button>
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
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const keyword = ref('')
const category = ref('')
const action = ref('')

const addVisible = ref(false)
const form = ref({ word: '', category: 'other', action: 'mask', severity: 3, note: '' })
const batchVisible = ref(false)
const batchText = ref('')
const batchCategory = ref('other')
const batchAction = ref('review')
const batchSeverity = ref(3)

const categoryMap = {
  politics: '政治敏感', terror: '暴恐极端', illegal: '违法犯罪', porn: '色情低俗',
  minor: '涉未成年人', fraud: '诈骗赌博', privacy: '隐私侵害', academic: '学术不端',
  violence: '暴力威胁', self_harm: '轻生倾向', ad: '广告引流', abuse: '辱骂攻击',
  spam: '刷屏灌水', other: '其他',
}
const actionLabel = (a) => ({ mask: '打码', review: '转人工复核', block: '直接拦截', allow: '白名单' }[a] || a)
const actionType = (a) => ({ mask: 'warning', review: 'warning', block: 'danger', allow: 'success' }[a] || 'info')
const sourceLabel = (s) => ({ manual: '手工', builtin: '内置', lexicon: '开源词库' }[s] || '手工')

const reload = () => { page.value = 1; loadData() }

const loadData = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/sensitive-words', {
      params: {
        page: page.value, page_size: pageSize.value,
        keyword: keyword.value || undefined, category: category.value || undefined,
        action: action.value || undefined,
      },
    })
    list.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const openAdd = () => {
  form.value = { word: '', category: 'other', action: 'mask', severity: 3, note: '' }
  addVisible.value = true
}

const submitAdd = async () => {
  if (!form.value.word.trim()) return ElMessage.warning('请输入词条')
  await api.post('/admin/sensitive-words', form.value)
  ElMessage.success('已添加，即时生效')
  addVisible.value = false
  loadData()
}

const toggleEnabled = async (row, v) => {
  await api.put(`/admin/sensitive-words/${row.id}`, { is_enabled: v })
  row.is_enabled = v
  ElMessage.success(v ? '已启用' : '已停用')
}

const remove = async (row) => {
  await ElMessageBox.confirm(`确定删除词条「${row.word}」吗？`, '提示', { type: 'warning' })
  await api.delete(`/admin/sensitive-words/${row.id}`)
  ElMessage.success('已删除')
  loadData()
}

const submitBatch = async () => {
  if (!batchText.value.trim()) return ElMessage.warning('请输入要导入的词')
  const res = await api.post('/admin/sensitive-words/batch', {
    text: batchText.value, category: batchCategory.value,
    action: batchAction.value, severity: batchSeverity.value,
  })
  ElMessage.success(res.msg)
  batchVisible.value = false
  batchText.value = ''
  reload()
}

onMounted(loadData)
</script>

<style scoped>
.hint { color: #909399; font-size: 12px; margin-left: 4px; }
</style>
