<script setup lang="ts">
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { getChatHistory } from "../api/chat"
import { getApiErrorMessage } from "../api/http"
import { getWorkOrderLinks } from "../api/workOrders"
import SourceList from "../components/chat/SourceList.vue"
import { useAuth } from "../stores/auth"
import type { ChatMessage } from "../types/chat"
import { hasKnownWorkOrderLink } from "../utils/workOrderLinks"

const messages = ref<ChatMessage[]>([])
const workOrderLinks = ref<Record<number, number | null>>({})
const auth = useAuth()
const router = useRouter()
const loading = ref(true)
const errorMessage = ref("")

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}

async function loadHistory() {
  try {
    messages.value = await getChatHistory()
    if (!auth.isAdmin.value) {
      const ids = messages.value.flatMap((message) => message.id === null ? [] : [message.id])
      const links = await getWorkOrderLinks(ids)
      workOrderLinks.value = Object.fromEntries(links.map((item) => [item.qa_record_id, item.work_order_id]))
    }
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "问答历史加载失败")
  } finally {
    loading.value = false
  }
}

function openWorkOrder(message: ChatMessage) {
  if (message.id === null || !hasKnownWorkOrderLink(workOrderLinks.value, message.id)) return
  const orderId = workOrderLinks.value[message.id]
  router.push(orderId ? `/work-orders/${orderId}` : `/work-orders/new/${message.id}`)
}

onMounted(loadHistory)
</script>

<template>
  <div class="page-view history-view">
    <header class="page-titlebar">
      <div>
        <h1>问答历史</h1>
        <p>最近 50 条个人问答记录</p>
      </div>
    </header>

    <section v-loading="loading" class="history-list">
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
      <el-empty v-else-if="!loading && messages.length === 0" description="暂无问答历史" />
      <article v-for="message in messages" :key="message.id ?? message.created_at" class="history-item">
        <header>
          <time>{{ formatTime(message.created_at) }}</time>
          <el-tag v-if="message.feedback === 'helpful'" type="success" effect="plain">有帮助</el-tag>
          <el-tag v-else-if="message.feedback === 'unhelpful'" type="danger" effect="plain">无帮助</el-tag>
          <el-tag v-else type="info" effect="plain">未反馈</el-tag>
        </header>
        <div class="history-question"><strong>问题</strong><p>{{ message.question }}</p></div>
        <div class="history-answer"><strong>回答</strong><p>{{ message.answer }}</p></div>
        <SourceList :sources="message.resources" />
        <el-button
          v-if="!auth.isAdmin.value && message.persisted === true && message.id !== null && hasKnownWorkOrderLink(workOrderLinks, message.id)"
          link
          type="primary"
          @click="openWorkOrder(message)"
        >{{ workOrderLinks[message.id] ? "查看工单" : "转为工单" }}</el-button>
      </article>
    </section>
  </div>
</template>
