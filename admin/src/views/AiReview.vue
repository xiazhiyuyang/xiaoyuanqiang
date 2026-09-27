<template>
  <div class="ai-review">
    <!-- 状态条 -->
    <el-card shadow="never" class="status-card">
      <div class="status-row">
        <div class="status-left">
          <el-tag :type="overview.enabled ? 'success' : 'info'" effect="dark" size="large">
            {{ overview.enabled ? 'AI 审查已开启' : 'AI 审查已关闭' }}
          </el-tag>
          <el-tag v-if="overview.dry_run" type="warning" effect="plain">观察模式（只记录不处置）</el-tag>
          <el-tag :type="overview.llm_enabled ? 'success' : 'info'" effect="plain">
            大模型：{{ llmTriggerLabel }}
          </el-tag>
          <el-tag :type="overview.image_enabled ? 'success' : 'info'" effect="plain">
            图片审查：{{ overview.image_enabled ? '已开启' : '未开启' }}
          </el-tag>
        </div>
        <div class="status-right">
          <el-statistic title="待人工复核" :value="overview.pending_records || 0" />
          <el-statistic title="待处理申诉" :value="overview.pending_appeals || 0" />
          <el-statistic title="24h 拦截" :value="overview.blocked_24h || 0" />
        </div>
      </div>
    </el-card>

    <el-tabs v-model="tab" class="main-tabs" @tab-change="onTabChange">
      <!-- ================= 复核队列 ================= -->
      <el-tab-pane name="queue">
        <template #label>
          <span>复核队列<el-badge v-if="overview.pending_records" :value="overview.pending_records" class="tab-badge" /></span>
        </template>
        <el-card shadow="never">
          <div class="toolbar">
            <el-button type="primary" :icon="Refresh" @click="loadRecords">刷新</el-button>
            <span class="tip">点击任意一行查看 AI 判定依据，再决定通过或驳回。</span>
          </div>
          <el-table :data="records" v-loading="loading" border stripe @row-click="openDetail" class="clickable">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">{{ typeLabel(row.target_type) }}</template>
            </el-table-column>
            <el-table-column label="风险" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.risk_level)" size="small">{{ row.risk_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="风险分" width="80" />
            <el-table-column label="分类" width="170">
              <template #default="{ row }">
                <el-tag v-for="c in row.category_labels" :key="c" size="small" class="mini-tag">{{ c }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="130" show-overflow-tooltip />
            <el-table-column prop="content" label="内容摘要" min-width="220" show-overflow-tooltip />
            <el-table-column label="作者" width="100">
              <template #default="{ row }">{{ row.author_name || '-' }}</template>
            </el-table-column>
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" @click.stop="quick(row, 'approve')">通过</el-button>
                <el-button size="small" type="danger" @click.stop="quick(row, 'reject')">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pager" v-model:current-page="page" :page-size="pageSize"
                         :total="total" layout="total, prev, pager, next" @current-change="loadRecords" />
        </el-card>
      </el-tab-pane>

      <!-- ================= 审查记录 ================= -->
      <el-tab-pane label="审查记录" name="records">
        <el-card shadow="never">
          <div class="toolbar wrap">
            <el-select v-model="filters.status" placeholder="全部状态" clearable style="width:130px" @change="reloadRecords">
              <el-option label="待复核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="已拦截" value="blocked" />
              <el-option label="自动通过" value="auto" />
            </el-select>
            <el-select v-model="filters.action" placeholder="全部动作" clearable style="width:130px" @change="reloadRecords">
              <el-option label="通过" value="pass" />
              <el-option label="打码" value="mask" />
              <el-option label="人工复核" value="review" />
              <el-option label="拦截" value="block" />
            </el-select>
            <el-select v-model="filters.target_type" placeholder="全部类型" clearable style="width:120px" @change="reloadRecords">
              <el-option label="帖子" value="post" />
              <el-option label="评论" value="comment" />
              <el-option label="私信" value="message" />
              <el-option label="资料" value="profile" />
            </el-select>
            <el-select v-model="filters.risk_level" placeholder="全部等级" clearable style="width:120px" @change="reloadRecords">
              <el-option label="极高" value="critical" />
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
            <el-select v-model="filters.category" placeholder="全部分类" clearable style="width:150px" @change="reloadRecords">
              <el-option v-for="c in categories" :key="c.key" :label="c.label" :value="c.key" />
            </el-select>
            <el-input v-model="filters.keyword" placeholder="搜索内容" clearable style="width:180px"
                      @clear="reloadRecords" @keyup.enter="reloadRecords" />
            <el-button type="primary" @click="reloadRecords">查询</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </div>
          <el-table :data="records" v-loading="loading" border stripe @row-click="openDetail" class="clickable">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">{{ typeLabel(row.target_type) }}</template>
            </el-table-column>
            <el-table-column label="风险" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.risk_level)" size="small">{{ row.risk_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="分" width="60" />
            <el-table-column label="动作" width="100">
              <template #default="{ row }">
                <el-tag :type="actionType(row.requested_action)" size="small">{{ actionLabel(row.requested_action) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="分类" width="170">
              <template #default="{ row }">
                <el-tag v-for="c in row.category_labels" :key="c" size="small" class="mini-tag">{{ c }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="120" show-overflow-tooltip />
            <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
            <el-table-column label="耗时" width="80">
              <template #default="{ row }">{{ row.latency_ms }}ms</template>
            </el-table-column>
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-pagination class="pager" v-model:current-page="page" :page-size="pageSize"
                         :total="total" layout="total, prev, pager, next" @current-change="loadRecords" />
        </el-card>
      </el-tab-pane>

      <!-- ================= 在线试审 ================= -->
      <el-tab-pane label="在线试审" name="test">
        <el-card shadow="never">
          <el-alert type="info" :closable="false" show-icon class="mb12"
                    title="试审不会落库、不影响线上内容，也不会受「审查范围」开关限制，用于上线前调参与验证误报。" />
          <el-form label-width="90px">
            <el-form-item label="场景">
              <el-radio-group v-model="testForm.target_type">
                <el-radio-button label="post">帖子</el-radio-button>
                <el-radio-button label="comment">评论</el-radio-button>
                <el-radio-button label="message">私信</el-radio-button>
                <el-radio-button label="profile">资料</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="标题">
              <el-input v-model="testForm.title" placeholder="可选（帖子标题）" maxlength="100" />
            </el-form-item>
            <el-form-item label="正文">
              <el-input v-model="testForm.content" type="textarea" :rows="5"
                        placeholder="粘贴一段内容，例如：加我微信abc123，兼职刷单日结，一天三百" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="testing" @click="runTest">开始试审</el-button>
              <el-button @click="fillSample('ad')">填广告样本</el-button>
              <el-button @click="fillSample('abuse')">填辱骂样本</el-button>
              <el-button @click="fillSample('normal')">填正常样本</el-button>
              <el-button @click="fillSample('academic')">填代写样本</el-button>
            </el-form-item>
          </el-form>

          <el-card v-if="testResult" shadow="never" class="result-card">
            <div class="result-head">
              <el-tag :type="actionType(testResult.requested_action)" effect="dark" size="large">
                {{ testResult.action_label }}（{{ testResult.requested_action }}）
              </el-tag>
              <el-tag :type="levelType(testResult.risk_level)" size="large">
                {{ testResult.risk_label }} · {{ testResult.score }} 分
              </el-tag>
              <el-tag v-for="c in testResult.category_labels" :key="c" type="warning" size="large">{{ c }}</el-tag>
              <span class="latency">耗时 {{ testResult.latency_ms }}ms</span>
            </div>
            <div class="reasons">
              <p v-for="(r, i) in testResult.reasons" :key="i">· {{ r }}</p>
            </div>
            <el-collapse>
              <el-collapse-item title="查看完整证据链（词库命中 / 规则命中 / 特征分 / 大模型 / 图片）">
                <pre class="evidence">{{ pretty(testResult.evidence) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </el-card>
        </el-card>
      </el-tab-pane>

      <!-- ================= 审查配置 ================= -->
      <el-tab-pane label="审查配置" name="config">
        <el-card shadow="never" v-loading="configLoading">
          <el-alert v-if="!isAdmin" type="warning" :closable="false" show-icon class="mb12"
                    title="仅管理员可以修改 AI 审查配置。" />
          <el-form label-width="150px" :disabled="!isAdmin">
            <el-divider content-position="left">总开关</el-divider>
            <el-form-item label="启用 AI 审查">
              <el-switch v-model="config.enabled" />
              <span class="tip">关闭后所有内容不再经过 AI 审查，仅保留原有敏感词引擎。</span>
            </el-form-item>
            <el-form-item label="观察模式">
              <el-switch v-model="config.dry_run" />
              <span class="tip">只记录判定结果、不实际拦截或打码。建议上线首周开启，先看误报率。</span>
            </el-form-item>
            <el-form-item label="本地引擎">
              <el-switch v-model="config.local_enabled" />
              <span class="tip">词库 + 规则 + 特征打分，零成本、无外网依赖。</span>
            </el-form-item>

            <el-divider content-position="left">审查范围</el-divider>
            <el-form-item label="生效场景">
              <el-checkbox v-model="config.scope_post">帖子（标题+正文+图片）</el-checkbox>
              <el-checkbox v-model="config.scope_comment">评论 / 回复</el-checkbox>
              <el-checkbox v-model="config.scope_message">私信</el-checkbox>
              <el-checkbox v-model="config.scope_profile">昵称 / 简介</el-checkbox>
            </el-form-item>

            <el-divider content-position="left">大模型语义审查（可选，不填 Key 自动降级）</el-divider>
            <el-form-item label="调用时机">
              <el-select v-model="config.llm_trigger" style="width:340px">
                <el-option v-for="(label, key) in config.llm_trigger_modes" :key="key" :label="label" :value="key" />
              </el-select>
            </el-form-item>
            <el-form-item label="服务商">
              <el-select v-model="config.llm_provider" style="width:340px" @change="onProviderChange">
                <el-option v-for="(p, key) in config.llm_presets" :key="key" :label="p.label" :value="key" />
              </el-select>
            </el-form-item>
            <el-form-item label="接口地址">
              <el-input v-model="config.llm_base_url" placeholder="https://open.bigmodel.cn/api/paas/v4" />
            </el-form-item>
            <el-form-item label="模型名">
              <el-input v-model="config.llm_model" placeholder="glm-4-flash" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="config.llm_api_key" type="password" show-password
                        :placeholder="config.llm_api_key_set ? '已配置，留空表示不修改' : '粘贴你的 API Key'" />
              <el-button v-if="config.llm_api_key_set" link type="danger" @click="clearKey('llm_api_key')">清除已保存的 Key</el-button>
            </el-form-item>
            <el-form-item label="测试连接">
              <el-button :loading="testingLlm" @click="testLlm">测试大模型连通性</el-button>
              <span v-if="llmTestMsg" :class="['test-msg', llmTestOk ? 'ok' : 'bad']">{{ llmTestMsg }}</span>
            </el-form-item>
            <el-form-item label="送审门槛 / 抽样">
              <span class="tip">本地风险分 ≥</span>
              <el-input-number v-model="config.llm_min_score" :min="0" :max="100" size="small" />
              <span class="tip">才送大模型；抽样模式比例</span>
              <el-input-number v-model="config.llm_sample_rate" :min="0" :max="100" size="small" />
              <span class="tip">%</span>
            </el-form-item>
            <el-form-item label="超时 / 截断 / 日限">
              <el-input-number v-model="config.llm_timeout" :min="2" :max="60" size="small" />
              <span class="tip">秒 · 截断</span>
              <el-input-number v-model="config.llm_max_len" :min="100" :max="8000" :step="100" size="small" />
              <span class="tip">字 · 每日上限</span>
              <el-input-number v-model="config.llm_daily_limit" :min="0" :max="1000000" :step="100" size="small" />
              <span class="tip">次（0=不限）</span>
            </el-form-item>

            <el-divider content-position="left">图片审查（可选）</el-divider>
            <el-form-item label="启用图片审查">
              <el-switch v-model="config.image_enabled" />
            </el-form-item>
            <el-form-item label="服务商">
              <el-select v-model="config.image_provider" style="width:340px">
                <el-option v-for="(label, key) in config.image_presets" :key="key" :label="label" :value="key" />
              </el-select>
            </el-form-item>
            <template v-if="config.image_provider === 'sightengine'">
              <el-form-item label="api_user">
                <el-input v-model="config.image_api_user" />
              </el-form-item>
              <el-form-item label="api_secret">
                <el-input v-model="config.image_api_secret" type="password" show-password
                          :placeholder="config.image_api_key_set ? '已配置，留空表示不修改' : ''" />
              </el-form-item>
            </template>
            <template v-else-if="config.image_provider === 'generic'">
              <el-form-item label="接口地址">
                <el-input v-model="config.image_api_url" placeholder="https://your-api/check" />
              </el-form-item>
              <el-form-item label="接口 Key">
                <el-input v-model="config.image_api_key" type="password" show-password
                          :placeholder="config.image_api_key_set ? '已配置，留空表示不修改' : ''" />
              </el-form-item>
            </template>
            <el-alert v-else-if="config.image_provider === 'local'" type="warning" :closable="false" show-icon class="mb12"
                      title="本地启发式通过「肤色占比 + 纹理方差」粗筛，沙滩、泳装、木地板都会误报，因此只作为「疑似」提示转人工复核，永远不会自动拦截。追求准确率请接入 Sightengine 或自建图片审核接口。" />
            <el-form-item label="测试图片审查">
              <el-input v-model="imageSample" placeholder="填一张图片 URL（可留空测本地）" style="width:300px" />
              <el-button :loading="testingImage" @click="testImage">测试</el-button>
              <span v-if="imageTestMsg" class="test-msg">{{ imageTestMsg }}</span>
            </el-form-item>

            <el-divider content-position="left">处置门槛</el-divider>
            <el-form-item label="自动拦截分">
              <el-input-number v-model="config.block_score" :min="0" :max="100" />
              <span class="tip">风险分 ≥ 该值直接拦截</span>
            </el-form-item>
            <el-form-item label="人工复核分">
              <el-input-number v-model="config.review_score" :min="0" :max="100" />
              <span class="tip">风险分 ≥ 该值转人工复核（不公开）</span>
            </el-form-item>
            <el-form-item label="打码分">
              <el-input-number v-model="config.mask_score" :min="0" :max="100" />
              <span class="tip">风险分 ≥ 该值打码后发布</span>
            </el-form-item>

            <el-divider content-position="left">分类处置策略</el-divider>
            <el-alert type="info" :closable="false" show-icon class="mb12"
                      title="每个违规分类对应一个默认动作。带有「法定」标记的分类属于法律明确禁止的信息，无论如何设置都会被拦截。" />
            <el-table :data="categoryRows" border size="small">
              <el-table-column prop="label" label="违规分类" width="140" />
              <el-table-column label="说明" min-width="220">
                <template #default="{ row }">
                  <span class="tip">{{ row.hint }}</span>
                </template>
              </el-table-column>
              <el-table-column label="法定" width="70">
                <template #default="{ row }">
                  <el-tag v-if="row.legal" type="danger" size="small">法定</el-tag>
                  <span v-else class="tip">—</span>
                </template>
              </el-table-column>
              <el-table-column label="危险等级" width="90">
                <template #default="{ row }">{{ row.severity }} / 5</template>
              </el-table-column>
              <el-table-column label="处置动作" width="180">
                <template #default="{ row }">
                  <el-select v-model="config.category_actions[row.key]" size="small" style="width:150px"
                             :disabled="!isAdmin">
                    <el-option label="放行（不处置）" value="pass" />
                    <el-option label="打码后发布" value="mask" />
                    <el-option label="转人工复核" value="review" />
                    <el-option label="直接拦截" value="block" />
                  </el-select>
                </template>
              </el-table-column>
            </el-table>

            <el-divider content-position="left">其他</el-divider>
            <el-form-item label="违规累积自动封禁">
              <el-input-number v-model="config.auto_ban_threshold" :min="0" :max="1000" />
              <span class="tip">近 7 天被拦截次数达到该值自动封禁；0 = 关闭（建议先关）</span>
            </el-form-item>
            <el-form-item label="通知作者">
              <el-switch v-model="config.notify_author" />
            </el-form-item>
            <el-form-item label="工作人员豁免">
              <el-switch v-model="config.exempt_staff" />
              <span class="tip">管理员/审查员自己的内容只记录不自动处置</span>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="saving" :disabled="!isAdmin" @click="saveConfig">保存配置</el-button>
              <el-button @click="loadConfig">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- ================= 词库与规则 ================= -->
      <el-tab-pane label="词库与规则" name="lexicon">
        <el-card shadow="never">
          <el-descriptions :column="3" border class="mb12">
            <el-descriptions-item label="已启用词条">{{ config.lexicon_size || 0 }}</el-descriptions-item>
            <el-descriptions-item label="域名黑名单">{{ config.blocked_domains_size || 0 }}</el-descriptions-item>
            <el-descriptions-item label="内置规则">{{ rules.length }}</el-descriptions-item>
          </el-descriptions>
          <el-alert type="info" :closable="false" show-icon class="mb12">
            <template #title>
              开源词库：<a :href="lexiconRepo" target="_blank" rel="noreferrer">{{ lexiconRepo }}</a>
              （{{ lexiconLicense }} 许可）。原始词库 8.7 万行含大量噪音，导入时会按来源映射分类、
              过滤校园正常词汇并按长度清洗。
            </template>
          </el-alert>
          <div class="toolbar">
            <el-button type="primary" :loading="importing" :disabled="!isAdmin" @click="importLexicon">
              一键导入 / 更新开源词库
            </el-button>
            <el-checkbox v-model="importOpts.include_domains">同时导入违规域名黑名单</el-checkbox>
            <el-checkbox v-model="importOpts.include_noisy">包含噪音较大的词库（GFW 补充等）</el-checkbox>
          </div>
          <el-alert v-if="importResult" type="success" :closable="false" class="mb12">
            <pre class="evidence">{{ pretty(importResult) }}</pre>
          </el-alert>

          <el-divider content-position="left">导入来源映射</el-divider>
          <el-table :data="lexiconSources" border size="small">
            <el-table-column prop="file" label="词库文件" min-width="180" />
            <el-table-column label="违规分类" width="120">
              <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
            </el-table-column>
            <el-table-column label="动作" width="110">
              <template #default="{ row }">{{ actionLabel(row.action) }}</template>
            </el-table-column>
            <el-table-column prop="severity" label="等级" width="70" />
            <el-table-column prop="min_len" label="最短" width="70" />
            <el-table-column prop="note" label="说明" min-width="200" />
          </el-table>

          <el-divider content-position="left">内置审查规则</el-divider>
          <el-table :data="rules" border size="small" max-height="360">
            <el-table-column prop="name" label="规则" width="130" />
            <el-table-column label="分类" width="110">
              <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
            </el-table-column>
            <el-table-column prop="severity" label="等级" width="70" />
            <el-table-column prop="weight" label="权重" width="70" />
            <el-table-column label="动作" width="100">
              <template #default="{ row }">{{ actionLabel(row.action) }}</template>
            </el-table-column>
            <el-table-column prop="note" label="说明" min-width="180" />
            <el-table-column prop="pattern" label="匹配模式" min-width="240" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ================= 申诉 ================= -->
      <el-tab-pane name="appeals">
        <template #label>
          <span>申诉<el-badge v-if="overview.pending_appeals" :value="overview.pending_appeals" class="tab-badge" /></span>
        </template>
        <el-card shadow="never">
          <div class="toolbar">
            <el-select v-model="appealStatus" style="width:140px" @change="loadAppeals">
              <el-option label="待处理" value="pending" />
              <el-option label="已通过" value="accepted" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="全部" value="" />
            </el-select>
            <el-button @click="loadAppeals">刷新</el-button>
          </div>
          <el-table :data="appeals" v-loading="loading" border stripe>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="user_name" label="申诉人" width="120" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">{{ typeLabel(row.target_type) }}</template>
            </el-table-column>
            <el-table-column prop="reason" label="申诉理由" min-width="220" show-overflow-tooltip />
            <el-table-column label="原判定" min-width="180">
              <template #default="{ row }">
                <template v-if="row.record_summary">
                  <el-tag size="small" type="warning">{{ row.record_summary.action_label }}</el-tag>
                  <span class="tip">{{ (row.record_summary.reasons || []).join('；') }}</span>
                </template>
                <span v-else class="tip">—</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'pending' ? 'warning' : (row.status === 'accepted' ? 'success' : 'info')">
                  {{ row.status === 'pending' ? '待处理' : (row.status === 'accepted' ? '已通过' : '已驳回') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status === 'pending'">
                  <el-button size="small" type="success" @click="handleAppeal(row, 'accepted')">接受</el-button>
                  <el-button size="small" type="danger" @click="handleAppeal(row, 'rejected')">驳回</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="审查详情与判定依据" size="52%">
      <div v-if="detail" class="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="记录 ID">{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="场景">{{ typeLabel(detail.target_type) }}</el-descriptions-item>
          <el-descriptions-item label="作者">{{ detail.author_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="内容 ID">{{ detail.target_id ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="levelType(detail.risk_level)" size="small">{{ detail.risk_label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险分">{{ detail.score }}</el-descriptions-item>
          <el-descriptions-item label="AI 建议动作">
            <el-tag :type="actionType(detail.requested_action)" size="small">{{ actionLabel(detail.requested_action) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="实际动作">{{ actionLabel(detail.action) }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ detail.latency_ms }}ms</el-descriptions-item>
          <el-descriptions-item label="观察模式">{{ detail.dry_run ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="时间" :span="2">{{ fmt(detail.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <h4>判定理由</h4>
        <ul class="reasons">
          <li v-for="(r, i) in detail.reasons" :key="i">{{ r }}</li>
        </ul>

        <h4>内容原文</h4>
        <pre class="evidence">{{ detail.content }}</pre>

        <h4>完整证据链</h4>
        <pre class="evidence">{{ pretty(detail.evidence) }}</pre>

        <h4>作者风险画像（近 30 天）</h4>
        <pre class="evidence">{{ pretty(detail.author_stats) }}</pre>

        <el-input v-model="handleRemark" type="textarea" :rows="2" placeholder="处理备注（会写进操作日志并通知作者）" />

        <div class="drawer-actions">
          <el-button type="success" @click="doHandle('approve')">通过（恢复展示）</el-button>
          <el-button type="warning" @click="doHandle('mask')">通过（保留打码）</el-button>
          <el-button type="danger" @click="doHandle('reject')">驳回（删除内容）</el-button>
          <el-button type="danger" plain @click="doHandle('ban')">驳回并封禁作者</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '../api'

const tab = ref('queue')
const loading = ref(false)
const configLoading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testingLlm = ref(false)
const testingImage = ref(false)
const importing = ref(false)

const overview = ref({})
const records = ref([])
const appeals = ref([])
const appealStatus = ref('pending')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filters = ref({ status: 'pending', action: '', target_type: '', risk_level: '', category: '', keyword: '' })
const config = ref({ category_actions: {} })
const rules = ref([])
const categories = ref([])
const lexiconSources = ref([])
const lexiconRepo = ref('')
const lexiconLicense = ref('')

const testForm = ref({ target_type: 'post', title: '', content: '' })
const testResult = ref(null)
const imageSample = ref('')
const llmTestMsg = ref('')
const llmTestOk = ref(false)
const imageTestMsg = ref('')
const importResult = ref(null)
const importOpts = ref({ include_domains: true, include_noisy: false })

const detailVisible = ref(false)
const detail = ref(null)
const handleRemark = ref('')

const isAdmin = computed(() => overview.value.is_admin !== false)
const llmTriggerLabel = computed(() => {
  const map = { off: '未启用', suspect: '可疑内容送审', sampled: '抽样送审', always: '全量送审' }
  return map[overview.value.llm_trigger] || '未启用'
})
const categoryRows = computed(() => config.value.category_catalog || [])

const typeLabel = (t) => ({ post: '帖子', comment: '评论', message: '私信', profile: '资料' }[t] || t)
const actionLabel = (a) => ({ pass: '通过', mask: '打码', review: '人工复核', block: '拦截', allow: '白名单' }[a] || a)
const actionType = (a) => ({ pass: 'success', mask: 'warning', review: 'warning', block: 'danger' }[a] || 'info')
const levelType = (l) => ({ safe: 'success', low: 'info', medium: 'warning', high: 'danger', critical: 'danger' }[l] || 'info')
const statusLabel = (s) => ({
  pending: '待复核', approved: '已通过', rejected: '已驳回',
  blocked: '已拦截', auto: '自动通过',
}[s] || s)
const categoryLabel = (k) => (categories.value.find((c) => c.key === k) || {}).label || k
const fmt = (s) => (s ? new Date(s).toLocaleString('zh-CN') : '-')
const pretty = (o) => (o == null ? '-' : JSON.stringify(o, null, 2))

const loadOverview = async () => {
  const res = await api.get('/ai-review/overview')
  overview.value = res.data
}

const loadRecords = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    Object.entries(filters.value).forEach(([k, v]) => { if (v) params[k] = v })
    const res = await api.get('/ai-review/records', { params })
    records.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

const reloadRecords = () => { page.value = 1; loadRecords() }
const resetFilters = () => {
  filters.value = { status: '', action: '', target_type: '', risk_level: '', category: '', keyword: '' }
  reloadRecords()
}

const openDetail = async (row) => {
  const res = await api.get(`/ai-review/records/${row.id}`)
  detail.value = res.data
  handleRemark.value = ''
  detailVisible.value = true
}

const quick = async (row, action) => {
  const res = await api.post(`/ai-review/records/${row.id}/handle`, { action })
  ElMessage.success(res.msg || '已处理')
  await Promise.all([loadOverview(), loadRecords()])
  if (detailVisible.value) detailVisible.value = false
}

const doHandle = async (action) => {
  if (action === 'reject' || action === 'ban') {
    try {
      await ElMessageBox.confirm(
        action === 'ban' ? '将删除该内容并封禁作者，确定继续？' : '将删除该内容，确定继续？',
        '确认', { type: 'warning' },
      )
    } catch { return }
  }
  const res = await api.post(`/ai-review/records/${detail.value.id}/handle`, {
    action, remark: handleRemark.value,
  })
  ElMessage.success(res.msg || '已处理')
  detailVisible.value = false
  await Promise.all([loadOverview(), loadRecords()])
}

const loadConfig = async () => {
  configLoading.value = true
  try {
    const res = await api.get('/ai-review/config')
    const data = res.data
    data.llm_api_key = ''
    data.image_api_key = ''
    data.image_api_secret = ''
    data.lexicon_size = data.lexicon_size
    config.value = data
    if (!data.category_actions) config.value.category_actions = {}
  } finally { configLoading.value = false }
}

const onProviderChange = (key) => {
  const p = (config.value.llm_presets || {})[key]
  if (p) {
    if (p.base_url) config.value.llm_base_url = p.base_url
    if (p.model) config.value.llm_model = p.model
  }
}

const clearKey = (field) => { config.value[field] = '__CLEAR__'; ElMessage.info('保存后生效') }

const saveConfig = async () => {
  saving.value = true
  try {
    const payload = { ...config.value }
    delete payload.category_catalog
    delete payload.llm_presets
    delete payload.image_presets
    delete payload.llm_trigger_modes
    delete payload.llm_runtime
    delete payload.lexicon_size
    delete payload.blocked_domains_size
    delete payload.llm_api_key_set
    delete payload.image_api_key_set
    const res = await api.put('/ai-review/config', payload)
    ElMessage.success(res.msg || '已保存')
    await loadConfig()
    await loadOverview()
  } finally { saving.value = false }
}

const testLlm = async () => {
  testingLlm.value = true
  llmTestMsg.value = ''
  try {
    const res = await api.post('/ai-review/config/test-llm', {
      llm_base_url: config.value.llm_base_url,
      llm_model: config.value.llm_model,
      llm_api_key: config.value.llm_api_key || '',
      llm_timeout: config.value.llm_timeout,
    })
    llmTestOk.value = !!res.data?.ok
    llmTestMsg.value = res.data?.ok
      ? `成功，耗时 ${res.data.latency_ms}ms，示例判定：${res.data.sample_verdict?.risk_level}`
      : (res.data?.msg || '失败')
  } catch (e) {
    llmTestOk.value = false
    llmTestMsg.value = e?.message || '测试失败'
  } finally { testingLlm.value = false }
}

const testImage = async () => {
  testingImage.value = true
  imageTestMsg.value = ''
  try {
    const res = await api.post('/ai-review/config/test-image', {
      image_provider: config.value.image_provider,
      image_api_url: config.value.image_api_url,
      image_api_user: config.value.image_api_user,
      image_api_key: config.value.image_api_key || '',
      image_api_secret: config.value.image_api_secret || '',
      sample_url: imageSample.value,
    })
    imageTestMsg.value = res.data?.msg || ''
  } catch (e) {
    imageTestMsg.value = e?.message || '测试失败'
  } finally { testingImage.value = false }
}

const SAMPLE = {
  ad: { title: '出售闲置', content: '低价出一批货，需要的同学加我微信 abc123456，还有兼职刷单日结一天三百，无门槛躺赚' },
  abuse: { title: '吐槽', content: '楼上那个傻逼真是狗东西，你妈死了吧，滚出学校' },
  normal: { title: '失物招领', content: '今天在三教 302 捡到一张校园卡，姓名王同学，请失主联系我，我在班群里等你' },
  academic: { title: 'help', content: '有偿代写毕业论文，包过不过退款，还可以代考四六级，需要私聊价格好谈' },
}
const fillSample = (k) => { testForm.value = { ...testForm.value, ...SAMPLE[k] } }

const runTest = async () => {
  testing.value = true
  testResult.value = null
  try {
    const res = await api.post('/ai-review/test', testForm.value)
    testResult.value = res.data
  } finally { testing.value = false }
}

const loadRules = async () => {
  const res = await api.get('/ai-review/rules')
  rules.value = res.data.rules || []
  categories.value = res.data.categories || []
  lexiconSources.value = res.data.lexicon_sources || []
  lexiconRepo.value = res.data.lexicon_repo || ''
  lexiconLicense.value = res.data.lexicon_license || ''
}

const importLexicon = async () => {
  importing.value = true
  importResult.value = null
  try {
    const res = await api.post('/ai-review/lexicon/import', importOpts.value)
    importResult.value = res.data
    ElMessage.success(res.msg || '导入完成')
    await loadConfig()
  } finally { importing.value = false }
}

const loadAppeals = async () => {
  loading.value = true
  try {
    const params = { page: 1, page_size: 50 }
    if (appealStatus.value) params.status = appealStatus.value
    const res = await api.get('/ai-review/appeals', { params })
    appeals.value = res.data.items
  } finally { loading.value = false }
}

const handleAppeal = async (row, action) => {
  let remark = ''
  try {
    const r = await ElMessageBox.prompt('处理说明（会通知用户）', '处理申诉', {
      inputType: 'textarea', inputPlaceholder: '可选',
    })
    remark = r.value || ''
  } catch { return }
  await api.post(`/ai-review/appeals/${row.id}/handle`, { action, remark })
  ElMessage.success('已处理')
  await Promise.all([loadAppeals(), loadOverview()])
}

const onTabChange = (name) => {
  if (name === 'queue' || name === 'records') loadRecords()
  if (name === 'config') loadConfig()
  if (name === 'lexicon') loadRules()
  if (name === 'appeals') loadAppeals()
}

onMounted(async () => {
  await Promise.all([loadOverview(), loadRules(), loadConfig()])
  loadRecords()
})
</script>

<style scoped>
.status-card { margin-bottom: 12px; }
.status-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.status-left { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.status-right { display: flex; gap: 28px; }
.toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.toolbar.wrap { flex-wrap: wrap; }
.tip { color: #909399; font-size: 12px; margin: 0 4px; }
.mb12 { margin-bottom: 12px; }
.pager { margin-top: 14px; justify-content: flex-end; display: flex; }
.mini-tag { margin: 1px 2px; }
.clickable :deep(.el-table__row) { cursor: pointer; }
.result-card { margin-top: 12px; background: #fafafa; }
.result-head { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
.latency { color: #909399; font-size: 12px; margin-left: auto; }
.reasons { margin: 0; padding-left: 4px; }
.reasons li, .reasons p { margin: 4px 0; color: #303133; font-size: 13px; }
.evidence { background: #1e1e2e; color: #cdd6f4; padding: 12px; border-radius: 8px;
            font-size: 12px; max-height: 320px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
.detail h4 { margin: 16px 0 8px; font-size: 14px; }
.drawer-actions { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.test-msg { margin-left: 10px; font-size: 12px; }
.test-msg.ok { color: #67c23a; }
.test-msg.bad { color: #f56c6c; }
.tab-badge { margin-left: 6px; }
</style>
