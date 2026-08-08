<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute } from "vue-router"
import { ElMessage } from "element-plus"

import {
  confirmWorkOrder,
  getWorkOrder,
  reopenWorkOrder,
  resolveWorkOrder,
  saveProcessingContent,
  startWorkOrder,
} from "../../api/workOrders"
import { getApiErrorMessage } from "../../api/http"
import SourceList from "../../components/chat/SourceList.vue"
import { useAuth } from "../../stores/auth"
import type { WorkOrder } from "../../types/workOrder"
import { runWorkOrderAction } from "../../utils/workOrderRecovery"

const route = useRoute()
const auth = useAuth()
const order = ref<WorkOrder | null>(null)
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref("")
const processing = reactive({ solution: "" })
const unresolvedNote = ref("")
const statusLabels = { pending: "待处理", processing: "处理中", resolved: "已解决", closed: "已关闭" }

const orderId = computed(() => Number(route.params.id))
const displayId = computed(() => order.value ? `WO-${order.value.id.toString().padStart(6, "0")}` : "")

function sync(result: WorkOrder) {
  order.value = result
  processing.solution = result.solution ?? ""
}

async function load() {
  try { sync(await getWorkOrder(orderId.value)) }
  catch (error) { errorMessage.value = getApiErrorMessage(error, "工单详情加载失败") }
  finally { loading.value = false }
}

async function act(action: () => Promise<WorkOrder>, success: string) {
  if (submitting.value) return
  submitting.value = true
  errorMessage.value = ""
  try {
    const outcome = await runWorkOrderAction(action, () => getWorkOrder(orderId.value))
    if (outcome.result) sync(outcome.result)
    if (outcome.error) {
      errorMessage.value = getApiErrorMessage(outcome.error, "操作失败")
    } else {
      ElMessage.success(success)
    }
  }
  finally { submitting.value = false }
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <div class="page-view work-order-view">
    <header class="page-titlebar"><div><h1>{{ displayId || "工单详情" }}</h1><p v-if="order">{{ statusLabels[order.status] }} · 更新于 {{ formatTime(order.updated_at) }}</p></div></header>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
    <section v-loading="loading" class="detail-panel">
      <template v-if="order">
        <dl class="detail-grid">
          <div><dt>原问题</dt><dd>{{ order.qa_record.question }}</dd></div>
          <div><dt>AI 回答</dt><dd class="pre-line">{{ order.qa_record.answer }}</dd></div>
          <div><dt>参考来源</dt><dd><SourceList :sources="order.qa_record.resources" /></dd></div>
          <div><dt>原问答时间</dt><dd><time>{{ formatTime(order.qa_record.created_at) }}</time></dd></div>
          <div><dt>工单创建时间</dt><dd><time>{{ formatTime(order.created_at) }}</time></dd></div>
          <div><dt>最后更新时间</dt><dd><time>{{ formatTime(order.updated_at) }}</time></dd></div>
          <div><dt>故障现象</dt><dd>{{ order.symptom }}</dd></div>
          <div v-if="order.attempted_steps"><dt>已尝试步骤</dt><dd>{{ order.attempted_steps }}</dd></div>
          <div v-if="order.additional_notes"><dt>其他说明</dt><dd>{{ order.additional_notes }}</dd></div>
          <div v-if="order.unresolved_note"><dt>最新未解决说明</dt><dd>{{ order.unresolved_note }}</dd></div>
        </dl>

        <div v-if="auth.isAdmin.value && order.status === 'pending'" class="action-row">
          <el-button type="primary" :loading="submitting" @click="act(() => startWorkOrder(orderId), '已开始处理')">开始处理</el-button>
        </div>

        <el-form v-if="auth.isAdmin.value && order.status === 'processing'" label-position="top" class="processing-form">
          <el-form-item label="解决方案"><el-input v-model="processing.solution" type="textarea" :rows="6" maxlength="8000" show-word-limit /></el-form-item>
          <div class="action-row">
            <el-button :loading="submitting" @click="act(() => saveProcessingContent(orderId, processing.solution), '解决方案已保存')">保存</el-button>
            <el-button type="primary" :loading="submitting" :disabled="!processing.solution.trim()" @click="act(() => resolveWorkOrder(orderId, processing.solution), '已标记为解决')">标记已解决</el-button>
          </div>
        </el-form>

        <dl v-if="order.solution" class="detail-grid result-block">
          <div v-if="order.solution"><dt>解决方案</dt><dd class="pre-line">{{ order.solution }}</dd></div>
        </dl>

        <div v-if="!auth.isAdmin.value && order.status === 'resolved'" class="confirmation-panel">
          <el-input v-model="unresolvedNote" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="问题仍存在时填写说明" />
          <div class="action-row">
            <el-button :loading="submitting" :disabled="!unresolvedNote.trim()" @click="act(() => reopenWorkOrder(orderId, unresolvedNote), '已退回处理中')">问题仍存在</el-button>
            <el-button type="primary" :loading="submitting" @click="act(() => confirmWorkOrder(orderId), '工单已关闭')">确认解决</el-button>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>
