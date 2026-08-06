<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { getChatHistory } from "../../api/chat"
import { createWorkOrder, getWorkOrderLinks } from "../../api/workOrders"
import { getApiErrorMessage } from "../../api/http"
import SourceList from "../../components/chat/SourceList.vue"
import type { ChatMessage } from "../../types/chat"
import { findExistingWorkOrderAfterConflict } from "../../utils/workOrderRecovery"

const route = useRoute()
const router = useRouter()
const qaRecordId = computed(() => Number(route.params.qaRecordId))
const record = ref<ChatMessage | null>(null)
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref("")
const form = reactive({ symptom: "", attempted_steps: "", additional_notes: "" })

async function load() {
  try {
    record.value = (await getChatHistory()).find((item) => item.id === qaRecordId.value) ?? null
    if (!record.value) errorMessage.value = "问答记录不存在或不在最近历史中"
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "问答记录加载失败")
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!record.value || !form.symptom.trim() || submitting.value) return
  submitting.value = true
  errorMessage.value = ""
  try {
    const order = await createWorkOrder({ qa_record_id: qaRecordId.value, ...form })
    await router.replace(`/work-orders/${order.id}`)
  } catch (error) {
    const originalMessage = getApiErrorMessage(error, "工单创建失败")
    const existingOrderId = await findExistingWorkOrderAfterConflict(
      error,
      qaRecordId.value,
      getWorkOrderLinks,
    )
    if (existingOrderId !== null) {
      await router.replace(`/work-orders/${existingOrderId}`)
      return
    }
    errorMessage.value = originalMessage
  } finally {
    submitting.value = false
  }
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <div class="page-view work-order-view">
    <header class="page-titlebar"><div><h1>创建工单</h1><p>补充需要人工处理的信息</p></div></header>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
    <section v-loading="loading" class="form-panel">
      <template v-if="record">
        <div class="source-question">
          <strong>原问题</strong><p>{{ record.question }}</p>
          <strong>AI 回答</strong><p>{{ record.answer }}</p>
          <SourceList :sources="record.resources" />
          <p class="source-time">原问答时间：{{ formatTime(record.created_at) }}</p>
        </div>
        <el-form label-position="top" @submit.prevent="submit">
          <el-form-item label="故障现象" required><el-input v-model="form.symptom" type="textarea" :rows="4" maxlength="2000" show-word-limit /></el-form-item>
          <el-form-item label="已尝试步骤"><el-input v-model="form.attempted_steps" type="textarea" :rows="4" maxlength="4000" show-word-limit /></el-form-item>
          <el-form-item label="其他说明"><el-input v-model="form.additional_notes" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item>
          <el-button type="primary" native-type="submit" :loading="submitting" :disabled="!form.symptom.trim()">提交工单</el-button>
        </el-form>
      </template>
    </section>
  </div>
</template>
