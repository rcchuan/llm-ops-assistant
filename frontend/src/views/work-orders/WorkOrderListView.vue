<script setup lang="ts">
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { listWorkOrders } from "../../api/workOrders"
import { getApiErrorMessage } from "../../api/http"
import { useAuth } from "../../stores/auth"
import type { WorkOrder, WorkOrderStatus } from "../../types/workOrder"

const router = useRouter()
const auth = useAuth()
const items = ref<WorkOrder[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const errorMessage = ref("")

const statusLabels = { pending: "待处理", processing: "处理中", resolved: "已解决", closed: "已关闭" }
const statusTypes = { pending: "warning", processing: "primary", resolved: "success", closed: "info" } as const

function statusLabel(status: WorkOrderStatus) {
  return statusLabels[status]
}

function statusType(status: WorkOrderStatus) {
  return statusTypes[status]
}

function formatId(id: number) {
  return `WO-${id.toString().padStart(6, "0")}`
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
}

async function load(target = page.value) {
  loading.value = true
  errorMessage.value = ""
  try {
    const result = await listWorkOrders(target)
    items.value = result.items
    total.value = result.total
    page.value = result.page
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "工单列表加载失败")
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <div class="page-view work-order-view">
    <header class="page-titlebar"><div><h1>{{ auth.isAdmin.value ? "工单管理" : "我的工单" }}</h1><p>问答转人工处理记录</p></div></header>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
    <section v-loading="loading" class="data-panel">
      <el-table :data="items" @row-click="(row: WorkOrder) => router.push(`/work-orders/${row.id}`)">
        <el-table-column label="工单编号" width="130"><template #default="{ row }">{{ formatId(row.id) }}</template></el-table-column>
        <el-table-column prop="qa_record.question" label="关联问题" min-width="320" show-overflow-tooltip />
        <el-table-column v-if="auth.isAdmin.value" label="提交用户" width="160"><template #default="{ row }">{{ row.creator?.display_name }}（{{ row.creator?.username }}）</template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="statusType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
        <el-table-column label="创建时间" width="180"><template #default="{ row }">{{ formatTime(row.created_at) }}</template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && items.length === 0" description="暂无工单" />
      <el-pagination v-if="total > 20" background layout="prev, pager, next" :current-page="page" :page-size="20" :total="total" @current-change="load" />
    </section>
  </div>
</template>
