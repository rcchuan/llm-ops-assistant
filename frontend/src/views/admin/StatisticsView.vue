<script setup lang="ts">
import { onMounted, ref } from "vue"
import { RefreshRight } from "@element-plus/icons-vue"
import { ElMessage } from "element-plus"

import { getStatistics } from "../../api/statistics"
import { getHealth, type HealthResponse } from "../../api/health"
import { configurationLabel, formatRate, knowledgeLabels, workOrderLabels, type StatisticsOverview } from "../../types/statistics"
import { loadAdminDashboard } from "../../utils/statisticsDashboard"

const statistics = ref<StatisticsOverview | null>(null)
const statisticsLoading = ref(true)
const statisticsError = ref("")
const health = ref<HealthResponse | null>(null)
const healthLoading = ref(true)
const healthError = ref("")

async function load() {
  statisticsLoading.value = true
  healthLoading.value = true
  statisticsError.value = ""
  healthError.value = ""
  const result = await loadAdminDashboard(getStatistics, getHealth)
  statistics.value = result.statistics.data
  statisticsError.value = result.statistics.error || ""
  statisticsLoading.value = false
  health.value = result.health.data
  healthError.value = result.health.error || ""
  healthLoading.value = false
}

async function refresh() {
  await load()
  if (!statisticsError.value && !healthError.value) ElMessage.success("已刷新")
}

onMounted(load)
</script>

<template>
  <div class="page-view">
    <header class="page-titlebar">
      <div><h1>管理员统计看板</h1><p>实时聚合业务数据与基础服务状态</p></div>
      <el-button :icon="RefreshRight" :loading="statisticsLoading || healthLoading" @click="refresh">刷新</el-button>
    </header>
    <el-alert v-if="statisticsError" class="knowledge-alert" title="统计数据加载失败，请刷新重试" type="error" show-icon :closable="false" />
    <template v-if="statistics">
      <section class="statistics-grid">
        <article class="stat-card"><span>问答总数</span><strong>{{ statistics.qa.total_count }}</strong></article>
        <article class="stat-card"><span>运维人员问答</span><strong>{{ statistics.qa.operator_count }}</strong></article>
        <article class="stat-card"><span>已转工单</span><strong>{{ statistics.qa.converted_count }}</strong><small>{{ formatRate(statistics.qa.conversion_rate) }}</small></article>
        <article class="stat-card"><span>已同步知识</span><strong>{{ statistics.knowledge_entries.synced }}</strong></article>
      </section>
      <section class="statistics-columns">
        <article class="content-panel statistics-panel"><div class="panel-heading"><h2>用户反馈</h2></div><dl class="statistics-list"><div><dt>有帮助</dt><dd>{{ statistics.feedback.helpful_count }}</dd></div><div><dt>无帮助</dt><dd>{{ statistics.feedback.unhelpful_count }}</dd></div><div><dt>未评价</dt><dd>{{ statistics.feedback.unrated_count }}</dd></div><div><dt>满意率</dt><dd>{{ formatRate(statistics.feedback.satisfaction_rate) }}</dd></div></dl></article>
        <article class="content-panel statistics-panel"><div class="panel-heading"><h2>工单当前状态</h2></div><dl class="statistics-list"><div v-for="(value, key) in statistics.work_orders" :key="key"><dt>{{ workOrderLabels[key] }}</dt><dd>{{ value }}</dd></div></dl></article>
        <article class="content-panel statistics-panel"><div class="panel-heading"><h2>候选知识状态</h2></div><dl class="statistics-list"><div v-for="(value, key) in statistics.knowledge_entries" :key="key"><dt>{{ knowledgeLabels[key] }}</dt><dd>{{ value }}</dd></div></dl></article>
      </section>
    </template>
    <div v-else-if="statisticsLoading" class="content-panel loading-panel">统计数据加载中...</div>
    <el-empty v-else-if="!statisticsError" description="暂无统计数据" />

    <section class="content-panel health-panel">
      <div class="panel-heading"><h2>服务状态</h2></div>
      <el-alert v-if="healthError" class="health-error" title="健康检查失败，服务状态未知" type="error" show-icon :closable="false" />
      <dl class="statistics-list">
        <div><dt>API</dt><dd>{{ healthLoading ? '检查中' : healthError ? '状态未知' : '正常' }}</dd></div>
        <div><dt>MySQL</dt><dd>{{ healthLoading ? '检查中' : healthError ? '状态未知' : health?.database.status === 'up' ? '正常' : '不可用' }}</dd></div>
        <div><dt>Dify App</dt><dd>{{ healthLoading ? '检查中' : healthError ? '状态未知' : configurationLabel(health?.dify_app.status || 'not_configured') }}</dd></div>
        <div><dt>Dify Dataset</dt><dd>{{ healthLoading ? '检查中' : healthError ? '状态未知' : configurationLabel(health?.dify_dataset.status || 'not_configured') }}</dd></div>
      </dl>
    </section>
  </div>
</template>
